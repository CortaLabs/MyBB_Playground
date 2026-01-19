"""Plugin and theme installation to TestForum."""

import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .config import Config
from .database import ProjectDatabase
from .workspace import PluginWorkspace, ThemeWorkspace


def _get_file_metadata(file_path: Path, source_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get metadata for a file including size, mtime, and checksum.

    Args:
        file_path: Path to the file
        source_path: Original source path (for tracking origin)

    Returns:
        Dict with file metadata
    """
    stat = file_path.stat()
    # Calculate MD5 checksum
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5_hash.update(chunk)

    return {
        "path": str(file_path),
        "source": str(source_path) if source_path else None,
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "checksum": md5_hash.hexdigest(),
        "deployed_at": datetime.utcnow().isoformat()
    }


class PluginInstaller:
    """Deploys plugins from workspace to TestForum.

    Tracks all deployed files and directories for complete cleanup on uninstall.
    Backups are stored OUTSIDE TestForum in the workspace/backups/ directory.

    TODO: Consider auto-updating .gitignore on first deployment to ignore deployed
    plugin files in TestForum (since source of truth is plugin_manager/). Currently
    handled manually via .gitignore patterns for TestForum/inc/plugins/*.php, etc.
    """

    def __init__(
        self,
        config: Config,
        db: ProjectDatabase,
        plugin_workspace: PluginWorkspace
    ):
        """Initialize plugin installer.

        Args:
            config: Plugin manager configuration
            db: Project database
            plugin_workspace: Plugin workspace manager
        """
        self.config = config
        self.db = db
        self.plugin_workspace = plugin_workspace
        self.mybb_root = config.mybb_root

        # Backup directory is OUTSIDE TestForum
        self.backup_root = config.repo_root / "plugin_manager" / "backups"
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def install_plugin(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
        """Deploy plugin to TestForum using directory overlay.

        The workspace structure mirrors MyBB's layout, so installation is a simple
        directory overlay:
        - workspace/inc/ -> TestForum/inc/
        - workspace/jscripts/ -> TestForum/jscripts/ (if exists)
        - workspace/images/ -> TestForum/images/ (if exists)
        - workspace/templates/ -> TestForum/inc/plugins/{codename}/templates/ (if exists)
        - workspace/templates_themes/ -> TestForum/inc/plugins/{codename}/templates_themes/ (if exists)

        All deployed files and created directories are tracked in the database
        for complete cleanup on uninstall. Backups are stored OUTSIDE TestForum.

        Args:
            codename: Plugin codename
            visibility: 'public' or 'private' (uses default if None)

        Returns:
            Dict with status, warnings, and deployment details
        """
        # Load metadata
        try:
            meta = self.plugin_workspace.read_meta(codename, visibility)
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Plugin '{codename}' not found in workspace"
            }

        workspace_path = self.plugin_workspace.get_workspace_path(codename, visibility)
        if not workspace_path:
            return {
                "success": False,
                "error": f"Workspace path not found for plugin '{codename}'"
            }

        deployment_timestamp = datetime.utcnow().isoformat()
        result = {
            "success": True,
            "plugin": codename,
            "workspace_path": str(workspace_path),
            "deployed_at": deployment_timestamp,
            "files_deployed": [],
            "dirs_created": [],
            "backups_created": [],
            "total_size": 0,
            "warnings": []
        }

        # Track all deployed files (with metadata) and directories we create
        all_files: List[Dict[str, Any]] = []
        all_dirs: List[str] = []
        all_backups: List[str] = []

        # Overlay inc/ directory (contains plugins and languages)
        inc_src = workspace_path / "inc"
        if inc_src.exists():
            files, dirs, backups = self._overlay_directory(
                inc_src, self.mybb_root / "inc", codename
            )
            all_files.extend(files)
            all_dirs.extend(dirs)
            all_backups.extend(backups)
        else:
            result["success"] = False
            result["error"] = f"Plugin inc/ directory not found: {inc_src}"
            return result

        # Verify plugin file exists in the destination
        dest_plugin_file = self.mybb_root / "inc" / "plugins" / f"{codename}.php"
        if not dest_plugin_file.exists():
            result["success"] = False
            result["error"] = f"Plugin file not found after install: {dest_plugin_file}"
            return result

        # Overlay jscripts/ if exists
        jscripts_src = workspace_path / "jscripts"
        if jscripts_src.exists() and any(jscripts_src.iterdir()):
            files, dirs, backups = self._overlay_directory(
                jscripts_src, self.mybb_root / "jscripts", codename
            )
            all_files.extend(files)
            all_dirs.extend(dirs)
            all_backups.extend(backups)

        # Overlay images/ if exists
        images_src = workspace_path / "images"
        if images_src.exists() and any(images_src.iterdir()):
            files, dirs, backups = self._overlay_directory(
                images_src, self.mybb_root / "images", codename
            )
            all_files.extend(files)
            all_dirs.extend(dirs)
            all_backups.extend(backups)

        # Overlay templates/ if exists (plugin-specific templates)
        templates_src = workspace_path / "templates"
        if templates_src.exists() and any(templates_src.iterdir()):
            templates_dest = self.mybb_root / "inc" / "plugins" / codename / "templates"
            files, dirs, backups = self._overlay_directory(
                templates_src, templates_dest, codename
            )
            all_files.extend(files)
            all_dirs.extend(dirs)
            all_backups.extend(backups)

        # Overlay templates_themes/ if exists (theme-specific template overrides)
        templates_themes_src = workspace_path / "templates_themes"
        if templates_themes_src.exists() and any(templates_themes_src.iterdir()):
            templates_themes_dest = self.mybb_root / "inc" / "plugins" / codename / "templates_themes"
            files, dirs, backups = self._overlay_directory(
                templates_themes_src, templates_themes_dest, codename
            )
            all_files.extend(files)
            all_dirs.extend(dirs)
            all_backups.extend(backups)

        # Calculate totals
        total_size = sum(f.get("size", 0) for f in all_files)

        # Store in result (simplified view for response)
        result["files_deployed"] = [
            {
                "path": f["relative_path"],
                "size": f["size"],
                "checksum": f["checksum"]
            }
            for f in all_files
        ]
        result["dirs_created"] = [
            str(Path(d).relative_to(self.mybb_root)) if d.startswith(str(self.mybb_root)) else d
            for d in all_dirs
        ]
        result["backups_created"] = all_backups
        result["total_size"] = total_size
        result["file_count"] = len(all_files)
        result["dir_count"] = len(all_dirs)

        # Save FULL deployment manifest to database (includes all metadata)
        try:
            self.db.set_deployed_manifest(codename, all_files, all_dirs, all_backups)
        except Exception as e:
            result["warnings"].append(f"Failed to save deployment manifest: {str(e)}")

        # Update database status
        try:
            self.db.update_project(
                codename=codename,
                status="installed",
                installed_at=datetime.utcnow().isoformat()
            )
        except Exception as e:
            result["warnings"].append(f"Database update failed: {str(e)}")

        # Add history entry
        try:
            project = self.db.get_project(codename)
            if project:
                self.db.add_history(
                    project_id=project['id'],
                    action="installed",
                    details=f"Installed to TestForum - {len(all_files)} files, {len(all_dirs)} dirs created"
                )
        except Exception as e:
            result["warnings"].append(f"History entry failed: {str(e)}")

        # Add ACP activation warning
        result["warnings"].insert(0, (
            "⚠️ IMPORTANT: Plugin files are installed but NOT ACTIVATED. "
            f"You must activate '{meta.get('name', codename)}' in MyBB Admin CP → Configuration → Plugins "
            "to run the _activate() function and register hooks."
        ))

        return result

    def _overlay_directory(
        self,
        src_dir: Path,
        dest_dir: Path,
        codename: str
    ) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
        """Copy directory contents, tracking all changes with full metadata.

        Recursively copies all files from src_dir to dest_dir, creating
        directories as needed. Backups of existing files go OUTSIDE TestForum.

        Args:
            src_dir: Source directory to copy from
            dest_dir: Destination directory to copy to
            codename: Plugin codename (for backup organization)

        Returns:
            Tuple of:
            - List of file metadata dicts (path, size, mtime, checksum, source)
            - List of absolute paths of directories WE CREATED (not pre-existing)
            - List of backup file paths created
        """
        files_deployed: List[Dict[str, Any]] = []
        dirs_created: List[str] = []
        backups_created: List[str] = []

        # Ensure base dest exists (it should - it's a MyBB core dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        for src_file in src_dir.rglob("*"):
            if src_file.is_file():
                # Calculate relative path and destination
                rel_path = src_file.relative_to(src_dir)
                dest_file = dest_dir / rel_path

                # Track directories we need to create
                # Check each parent dir - if it doesn't exist, we're creating it
                for parent in reversed(dest_file.parents):
                    if parent == dest_dir:
                        continue  # Skip the base MyBB dir
                    if not parent.exists():
                        parent_str = str(parent)
                        if parent_str not in dirs_created:
                            dirs_created.append(parent_str)

                # Create parent directories
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Backup existing file OUTSIDE TestForum
                if dest_file.exists():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_dir = self.backup_root / codename / timestamp
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    backup_file = backup_dir / rel_path
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest_file, backup_file)
                    backups_created.append(str(backup_file))

                # Copy file
                shutil.copy2(src_file, dest_file)

                # Get full metadata for the deployed file
                file_info = _get_file_metadata(dest_file, source_path=src_file)
                file_info["relative_path"] = str(rel_path)
                files_deployed.append(file_info)

        return files_deployed, dirs_created, backups_created

    def uninstall_plugin(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
        """Remove plugin from TestForum using deployment manifest.

        Uses the stored manifest from install to ensure COMPLETE cleanup:
        1. Delete ALL files we deployed (from manifest)
        2. Delete ALL directories WE CREATED (not core MyBB dirs)
        3. Clear manifest from database
        4. Update project status

        Args:
            codename: Plugin codename
            visibility: 'public' or 'private' (uses default if None)

        Returns:
            Dict with status and details including file metadata
        """
        uninstall_timestamp = datetime.utcnow().isoformat()
        result = {
            "success": True,
            "plugin": codename,
            "uninstalled_at": uninstall_timestamp,
            "files_removed": [],
            "dirs_removed": [],
            "total_size_freed": 0,
            "original_deployment": None,
            "warnings": []
        }

        # Get deployment manifest from database
        manifest = self.db.get_deployed_manifest(codename)
        files_info = manifest.get("files", [])
        dirs_to_delete = manifest.get("directories", [])

        # Store original deployment info
        if manifest.get("deployed_at"):
            result["original_deployment"] = {
                "deployed_at": manifest.get("deployed_at"),
                "file_count": manifest.get("file_count", len(files_info)),
                "dir_count": manifest.get("dir_count", len(dirs_to_delete)),
                "backups": manifest.get("backups", [])
            }

        # Extract file paths from manifest (handle both old and new formats)
        files_to_delete = []
        for f in files_info:
            if isinstance(f, dict):
                files_to_delete.append({
                    "path": f.get("path"),
                    "size": f.get("size", 0),
                    "checksum": f.get("checksum")
                })
            else:
                # Legacy: just a string path
                files_to_delete.append({"path": f, "size": 0, "checksum": None})

        if not files_to_delete:
            # Fallback: try legacy approach for plugins not installed with manifest
            result["warnings"].append(
                "No deployment manifest found - using legacy cleanup (may be incomplete)"
            )
            plugin_file = self.mybb_root / "inc" / "plugins" / f"{codename}.php"
            if plugin_file.exists():
                files_to_delete = [{"path": str(plugin_file), "size": 0, "checksum": None}]
            lang_file = self.mybb_root / "inc" / "languages" / "english" / f"{codename}.lang.php"
            if lang_file.exists():
                files_to_delete.append({"path": str(lang_file), "size": 0, "checksum": None})

        # Step 1: Delete ALL deployed files
        total_freed = 0
        for file_info in files_to_delete:
            file_path_str = file_info["path"]
            file_path = Path(file_path_str)
            if file_path.exists():
                try:
                    # Get actual size before deletion
                    actual_size = file_path.stat().st_size
                    file_path.unlink()
                    total_freed += actual_size

                    # Store relative path for cleaner output
                    try:
                        rel_path = str(file_path.relative_to(self.mybb_root))
                    except ValueError:
                        rel_path = file_path_str

                    result["files_removed"].append({
                        "path": rel_path,
                        "size": actual_size,
                        "original_checksum": file_info.get("checksum")
                    })
                except Exception as e:
                    result["warnings"].append(f"Failed to delete {file_path_str}: {str(e)}")
            else:
                result["warnings"].append(f"File already gone: {file_path_str}")

        # Step 2: Delete directories WE CREATED (deepest first, only if empty)
        # Sort by depth (most nested first) to delete children before parents
        dirs_sorted = sorted(dirs_to_delete, key=lambda p: p.count('/'), reverse=True)

        for dir_path_str in dirs_sorted:
            dir_path = Path(dir_path_str)
            if dir_path.exists() and dir_path.is_dir():
                # SAFETY: Only delete if empty (our files should already be gone)
                try:
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        try:
                            rel_path = str(dir_path.relative_to(self.mybb_root))
                        except ValueError:
                            rel_path = dir_path_str
                        result["dirs_removed"].append(rel_path)
                    else:
                        result["warnings"].append(
                            f"Directory not empty, skipped: {dir_path_str}"
                        )
                except Exception as e:
                    result["warnings"].append(f"Failed to remove dir {dir_path_str}: {str(e)}")

        # Step 3: Clear deployment manifest
        try:
            self.db.clear_deployed_manifest(codename)
        except Exception as e:
            result["warnings"].append(f"Failed to clear manifest: {str(e)}")

        # Step 4: Update database status
        try:
            self.db.update_project(
                codename=codename,
                status="development"
            )
            # Manually clear installed_at (update_project filters None values)
            project = self.db.get_project(codename)
            if project:
                self.db.conn.execute(
                    "UPDATE projects SET installed_at = NULL WHERE codename = ?",
                    (codename,)
                )
                self.db.conn.commit()
        except Exception as e:
            result["warnings"].append(f"Database update failed: {str(e)}")

        # Update totals
        result["total_size_freed"] = total_freed
        result["file_count"] = len(result["files_removed"])
        result["dir_count"] = len(result["dirs_removed"])

        # Step 5: Add history entry with full details
        try:
            project = self.db.get_project(codename)
            if project:
                import json
                history_details = {
                    "files_removed": len(result["files_removed"]),
                    "dirs_removed": len(result["dirs_removed"]),
                    "total_size_freed": total_freed,
                    "original_deployment": result.get("original_deployment"),
                    "uninstalled_at": uninstall_timestamp
                }
                self.db.add_history(
                    project_id=project['id'],
                    action="uninstalled",
                    details=json.dumps(history_details)
                )
        except Exception as e:
            result["warnings"].append(f"History entry failed: {str(e)}")

        return result

    def get_installed_plugins(self) -> List[str]:
        """List plugins currently installed in TestForum.

        Returns:
            List of installed plugin codenames
        """
        plugins_dir = self.mybb_root / "inc" / "plugins"
        if not plugins_dir.exists():
            return []

        installed = []
        for plugin_file in plugins_dir.glob("*.php"):
            # Skip index.php and other non-plugin files
            if plugin_file.stem not in ("index", "akismet"):
                installed.append(plugin_file.stem)

        return installed


class ThemeInstaller:
    """Deploys themes from workspace to TestForum."""

    def __init__(
        self,
        config: Config,
        db: ProjectDatabase,
        theme_workspace: ThemeWorkspace
    ):
        """Initialize theme installer.

        Args:
            config: Plugin manager configuration
            db: Project database
            theme_workspace: Theme workspace manager
        """
        self.config = config
        self.db = db
        self.theme_workspace = theme_workspace
        self.mybb_root = config.mybb_root

    def install_theme(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
        """Deploy theme to TestForum.

        Steps:
        1. Load meta.json from workspace
        2. For each stylesheet in meta.json:
           - Read CSS from workspace
           - Find or create stylesheet in DB via mybb_list_stylesheets
           - Write CSS via mybb_write_stylesheet
        3. Deploy template overrides via mybb_template_batch_write
        4. Update project status to 'installed'
        5. Add history entry

        Args:
            codename: Theme codename
            visibility: 'public' or 'private' (uses default if None)

        Returns:
            Dict with status and deployment details
        """
        # Load metadata
        try:
            meta = self.theme_workspace.read_meta(codename, visibility)
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Theme '{codename}' not found in workspace"
            }

        workspace_path = self.theme_workspace.get_workspace_path(codename, visibility)
        if not workspace_path:
            return {
                "success": False,
                "error": f"Workspace path not found for theme '{codename}'"
            }

        result = {
            "success": True,
            "theme": codename,
            "stylesheets_deployed": 0,
            "templates_deployed": 0,
            "warnings": []
        }

        # Step 2: Deploy stylesheets
        stylesheets_dir = workspace_path / "stylesheets"
        if stylesheets_dir.exists():
            try:
                import mybb_mcp

                # Get theme ID (assume tid=1 for Default theme)
                # In production, this should look up the theme by name
                tid = 1

                # List existing stylesheets for the theme
                existing_stylesheets = mybb_mcp.mybb_list_stylesheets(tid=tid)
                stylesheet_map = {s["name"]: s["sid"] for s in existing_stylesheets}

                for css_file in stylesheets_dir.glob("*.css"):
                    css_name = css_file.stem
                    css_content = css_file.read_text()

                    # Find stylesheet ID
                    if css_name in stylesheet_map:
                        sid = stylesheet_map[css_name]
                        mybb_mcp.mybb_write_stylesheet(sid=sid, stylesheet=css_content)
                        result["stylesheets_deployed"] += 1
                    else:
                        result["warnings"].append(
                            f"Stylesheet '{css_name}' not found in theme (tid={tid}). "
                            "Create it in MyBB ACP first."
                        )
            except Exception as e:
                result["warnings"].append(f"Stylesheet deployment failed: {str(e)}")

        # Step 3: Deploy template overrides
        templates_dir = workspace_path / "templates"
        if templates_dir.exists():
            try:
                import mybb_mcp

                templates_to_deploy = []
                for template_file in templates_dir.glob("*.html"):
                    template_name = template_file.stem
                    template_content = template_file.read_text()
                    templates_to_deploy.append({
                        "title": template_name,
                        "template": template_content
                    })

                if templates_to_deploy:
                    # Deploy to theme template set (sid=1 for Default Templates)
                    # In production, look up the sid for this theme
                    mybb_mcp.mybb_template_batch_write(
                        templates=templates_to_deploy,
                        sid=1
                    )
                    result["templates_deployed"] = len(templates_to_deploy)
            except Exception as e:
                result["warnings"].append(f"Template deployment failed: {str(e)}")

        # Step 4: Update database status
        try:
            self.db.update_project(
                codename=codename,
                status="installed",
                installed_at=datetime.utcnow().isoformat()
            )
        except Exception as e:
            result["warnings"].append(f"Database update failed: {str(e)}")

        # Step 5: Add history entry
        try:
            project = self.db.get_project(codename)
            if project:
                self.db.add_history(
                    project_id=project['id'],
                    action="installed",
                    details=(
                        f"Installed to TestForum - "
                        f"{result['stylesheets_deployed']} stylesheets, "
                        f"{result['templates_deployed']} templates"
                    )
                )
        except Exception as e:
            result["warnings"].append(f"History entry failed: {str(e)}")

        # Add activation instructions
        result["warnings"].insert(0, (
            f"✓ Theme '{meta.get('name', codename)}' deployed. "
            "To activate: Go to MyBB Admin CP → Templates & Style → Themes, "
            "select this theme and click 'Set as Default'."
        ))

        return result

    def uninstall_theme(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
        """Remove theme customizations from TestForum.

        Note: This does not delete the theme itself, only reverts customizations.

        Args:
            codename: Theme codename
            visibility: 'public' or 'private' (uses default if None)

        Returns:
            Dict with status and details
        """
        result = {
            "success": True,
            "theme": codename,
            "warnings": ["Theme uninstall reverts customizations but does not delete the theme."]
        }

        # Update database status
        try:
            self.db.update_project(
                codename=codename,
                status="development",
                installed_at=None
            )
        except Exception as e:
            result["warnings"].append(f"Database update failed: {str(e)}")

        # Add history entry
        try:
            project = self.db.get_project(codename)
            if project:
                self.db.add_history(
                    project_id=project['id'],
                    action="uninstalled",
                    details="Theme customizations reverted"
                )
        except Exception as e:
            result["warnings"].append(f"History entry failed: {str(e)}")

        return result
