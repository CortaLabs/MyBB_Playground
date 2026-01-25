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

    def _is_safe_to_track(self, dir_path: Path, codename: str) -> bool:
        """Check if a directory is safe to track for later deletion.

        A directory is safe to track ONLY if it is plugin-specific, meaning:
        1. It contains the plugin codename in its path
        2. It is NOT a protected core MyBB directory

        This prevents tracking (and later deleting) core MyBB directories.

        Args:
            dir_path: Absolute path to the directory
            codename: Plugin codename

        Returns:
            True if directory is safe to track, False otherwise
        """
        try:
            rel_path = dir_path.relative_to(self.mybb_root)
            rel_str = str(rel_path)
        except ValueError:
            # Path is not under mybb_root - definitely not safe
            return False

        # Check if this is a protected directory
        if rel_str in self.PROTECTED_DIRECTORIES:
            return False

        # Check if this directory is plugin-specific (contains codename)
        # A directory like "inc/plugins/myplugin" or "admin/modules/user/myplugin"
        # should be trackable, but "admin/modules/user" should not
        parts = rel_path.parts
        if codename in parts:
            return True

        # If the path doesn't contain the codename, it's likely a core directory
        # that we should NOT track, even if it's not explicitly in PROTECTED_DIRECTORIES
        return False

    def _is_protected_directory(self, dir_path: Path) -> bool:
        """Check if a directory is a protected core MyBB directory.

        Args:
            dir_path: Absolute path to the directory

        Returns:
            True if directory is protected, False otherwise
        """
        try:
            rel_path = str(dir_path.relative_to(self.mybb_root))
            return rel_path in self.PROTECTED_DIRECTORIES
        except ValueError:
            return False

    # Files/directories that are workspace-only and should NOT be deployed
    WORKSPACE_ONLY = {
        "meta.json",      # Plugin metadata file
        "README.md",      # Documentation
        "readme.md",      # Documentation (lowercase)
        "README.txt",     # Documentation
        "readme.txt",     # Documentation (lowercase)
        "tests",          # Test directory
        ".git",           # Git repository
        ".gitignore",     # Git ignore file
        ".gitkeep",       # Git keep file
        "__pycache__",    # Python cache
        ".DS_Store",      # macOS metadata
    }

    # Directories that need special destination handling (not direct overlay to MyBB root)
    SPECIAL_DEST_DIRS = {
        "templates": lambda mybb_root, codename: mybb_root / "inc" / "plugins" / codename / "templates",
        "templates_themes": lambda mybb_root, codename: mybb_root / "inc" / "plugins" / codename / "templates_themes",
    }

    # PROTECTED DIRECTORIES - These paths relative to MyBB root can NEVER be deleted.
    # They are core MyBB directories that exist regardless of any plugins.
    # This is a CRITICAL safety measure to prevent catastrophic data loss.
    PROTECTED_DIRECTORIES = {
        # Core top-level directories
        "admin",
        "admin/modules",
        "admin/modules/config",
        "admin/modules/forum",
        "admin/modules/home",
        "admin/modules/style",
        "admin/modules/tools",
        "admin/modules/user",
        "archive",
        "cache",
        "images",
        "inc",
        "inc/cachehandlers",
        "inc/datahandlers",
        "inc/languages",
        "inc/languages/english",
        "inc/languages/english/admin",
        "inc/mailhandlers",
        "inc/plugins",
        "inc/tasks",
        "install",
        "jscripts",
        "uploads",
        "uploads/avatars",
    }

    def install_plugin(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
        """Deploy plugin to TestForum using directory overlay.

        Copies ALL workspace contents to TestForum, except workspace-only files
        (meta.json, README.md, tests/, .git/, etc.). The workspace structure
        mirrors MyBB's layout, so most directories overlay directly:
        - workspace/inc/ -> TestForum/inc/
        - workspace/admin/ -> TestForum/admin/
        - workspace/uploads/ -> TestForum/uploads/
        - workspace/*.php -> TestForum/*.php (root-level PHP files)
        - etc.

        Special handling for plugin-specific directories:
        - workspace/templates/ -> TestForum/inc/plugins/{codename}/templates/
        - workspace/templates_themes/ -> TestForum/inc/plugins/{codename}/templates_themes/

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

        # Verify inc/ directory exists (required for all plugins)
        inc_src = workspace_path / "inc"
        if not inc_src.exists():
            result["success"] = False
            result["error"] = f"Plugin inc/ directory not found: {inc_src}"
            return result

        # Iterate over ALL items in workspace and deploy them
        for item in workspace_path.iterdir():
            item_name = item.name

            # Skip workspace-only files/directories
            if item_name in self.WORKSPACE_ONLY:
                continue

            # Handle directories
            if item.is_dir():
                # Check if any files exist in the directory
                if not any(item.rglob("*")):
                    continue  # Skip empty directories

                # Determine destination based on special handling or direct overlay
                if item_name in self.SPECIAL_DEST_DIRS:
                    dest_dir = self.SPECIAL_DEST_DIRS[item_name](self.mybb_root, codename)
                else:
                    # Direct overlay: workspace/X/ -> TestForum/X/
                    dest_dir = self.mybb_root / item_name

                files, dirs, backups = self._overlay_directory(item, dest_dir, codename)
                all_files.extend(files)
                all_dirs.extend(dirs)
                all_backups.extend(backups)

            # Handle root-level files (e.g., standalone PHP pages)
            elif item.is_file():
                # Deploy root-level files directly to MyBB root
                files, dirs, backups = self._overlay_file(item, self.mybb_root, codename)
                all_files.extend(files)
                all_dirs.extend(dirs)
                all_backups.extend(backups)

        # Verify plugin file exists in the destination
        dest_plugin_file = self.mybb_root / "inc" / "plugins" / f"{codename}.php"
        if not dest_plugin_file.exists():
            result["success"] = False
            result["error"] = f"Plugin file not found after install: {dest_plugin_file}"
            return result

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
                # SAFETY: Only track plugin-specific directories, never core MyBB dirs
                for parent in reversed(dest_file.parents):
                    if parent == dest_dir:
                        continue  # Skip the base MyBB dir
                    if not parent.exists():
                        parent_str = str(parent)
                        # CRITICAL: Only track if this is a plugin-specific directory
                        if parent_str not in dirs_created and self._is_safe_to_track(parent, codename):
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

    def _overlay_file(
        self,
        src_file: Path,
        dest_dir: Path,
        codename: str
    ) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
        """Copy a single file to destination, tracking changes with full metadata.

        Used for root-level files in the workspace (e.g., standalone PHP pages).

        Args:
            src_file: Source file to copy
            dest_dir: Destination directory to copy to
            codename: Plugin codename (for backup organization)

        Returns:
            Tuple of:
            - List of file metadata dicts (single file)
            - List of directories created (empty for root files)
            - List of backup file paths created
        """
        files_deployed: List[Dict[str, Any]] = []
        dirs_created: List[str] = []
        backups_created: List[str] = []

        dest_file = dest_dir / src_file.name

        # Backup existing file OUTSIDE TestForum
        if dest_file.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = self.backup_root / codename / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backup_dir / src_file.name
            shutil.copy2(dest_file, backup_file)
            backups_created.append(str(backup_file))

        # Copy file
        shutil.copy2(src_file, dest_file)

        # Get full metadata for the deployed file
        file_info = _get_file_metadata(dest_file, source_path=src_file)
        file_info["relative_path"] = src_file.name
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

            # CRITICAL SAFETY CHECK: Never delete protected directories
            if self._is_protected_directory(dir_path):
                result["warnings"].append(
                    f"BLOCKED: Attempted to delete protected directory: {dir_path_str}"
                )
                continue

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
    """Deploys themes from workspace to TestForum.

    Like PluginInstaller, this tracks all deployed files and directories for
    complete cleanup on uninstall. Theme workspaces can contain any files that
    mirror MyBB's structure (jscripts/, images/, etc.) in addition to stylesheets
    and templates which are deployed to the database.
    """

    # Files/directories that are workspace-only and should NOT be deployed to TestForum
    WORKSPACE_ONLY = {
        "meta.json",      # Theme metadata file
        "README.md",      # Documentation
        "readme.md",      # Documentation (lowercase)
        "README.txt",     # Documentation
        "readme.txt",     # Documentation (lowercase)
        "DESIGN_GUIDE.md",  # Design documentation
        "stylesheets",    # Deployed to database, not filesystem
        "templates",      # Deployed to database, not filesystem
        "tests",          # Test directory
        ".git",           # Git repository
        ".gitignore",     # Git ignore file
        ".gitkeep",       # Git keep file
        "__pycache__",    # Python cache
        ".DS_Store",      # macOS metadata
    }

    # PROTECTED DIRECTORIES - These paths relative to MyBB root can NEVER be deleted.
    # They are core MyBB directories that exist regardless of any themes.
    PROTECTED_DIRECTORIES = {
        "admin",
        "archive",
        "cache",
        "images",
        "inc",
        "inc/plugins",
        "inc/languages",
        "install",
        "jscripts",
        "uploads",
    }

    def __init__(
        self,
        config: Config,
        db: ProjectDatabase,
        theme_workspace: ThemeWorkspace,
        mybb_db: Optional[Any] = None
    ):
        """Initialize theme installer.

        Args:
            config: Plugin manager configuration
            db: Project database
            theme_workspace: Theme workspace manager
            mybb_db: MyBBDatabase instance (optional, created if None)
        """
        self.config = config
        self.db = db
        self.theme_workspace = theme_workspace
        self.mybb_root = config.mybb_root

        # Backup directory is OUTSIDE TestForum (same pattern as PluginInstaller)
        self.backup_root = config.repo_root / "plugin_manager" / "backups"
        self.backup_root.mkdir(parents=True, exist_ok=True)

        # Initialize MyBB database if not provided
        if mybb_db is None:
            from mybb_mcp.config import load_config
            from mybb_mcp.db import MyBBDatabase
            # Load DB config from .env via mybb_mcp.config
            mybb_config = load_config()
            self.mybb_db = MyBBDatabase(mybb_config.db)
        else:
            self.mybb_db = mybb_db

    def _bridge_call(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Call the MCP bridge with the given action and parameters.
        Returns parsed JSON response dict.
        """
        import subprocess
        import json

        bridge_path = self.mybb_root / "mcp_bridge.php"
        if not bridge_path.exists():
            return {"success": False, "error": "Bridge not found"}

        cmd = ["php", str(bridge_path), f"--action={action}", "--json"]

        for key, value in kwargs.items():
            if value is not None:
                # Handle content that may have special characters
                cmd.append(f"--{key}={value}")

        # DEBUG: Log bridge calls for theme operations
        if "theme" in action or "templateset" in action:
            import sys
            print(f"[DEBUG _bridge_call] {' '.join(cmd[:6])}...", file=sys.stderr)

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.mybb_root),
                capture_output=True,
                text=True,
                timeout=60
            )

            # Parse JSON response
            if result.stdout.strip():
                return json.loads(result.stdout.strip())
            elif result.stderr.strip():
                return {"success": False, "error": result.stderr.strip()}
            else:
                return {"success": False, "error": "Empty response from bridge"}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Bridge call timed out"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON response: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _is_protected_directory(self, dir_path: Path) -> bool:
        """Check if a directory is a protected core MyBB directory.

        Args:
            dir_path: Absolute path to the directory

        Returns:
            True if directory is protected, False otherwise
        """
        try:
            rel_path = str(dir_path.relative_to(self.mybb_root))
            return rel_path in self.PROTECTED_DIRECTORIES
        except ValueError:
            return False

    def _is_safe_to_track(self, dir_path: Path, codename: str) -> bool:
        """Check if a directory is safe to track for later deletion.

        A directory is safe to track ONLY if it is theme-specific, meaning:
        1. It contains the theme codename in its path
        2. It is NOT a protected core MyBB directory

        This prevents tracking (and later deleting) core MyBB directories.

        Args:
            dir_path: Absolute path to the directory
            codename: Theme codename

        Returns:
            True if directory is safe to track, False otherwise
        """
        try:
            rel_path = dir_path.relative_to(self.mybb_root)
            rel_str = str(rel_path)
        except ValueError:
            return False

        if rel_str in self.PROTECTED_DIRECTORIES:
            return False

        # Check if this directory is theme-specific (contains codename)
        parts = rel_path.parts
        if codename in parts:
            return True

        # If the path doesn't contain the codename, it's likely a core directory
        return False

    def _overlay_directory(
        self,
        src_dir: Path,
        dest_dir: Path,
        codename: str
    ) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
        """Copy directory contents to TestForum, tracking all changes.

        Recursively copies all files from src_dir to dest_dir, creating
        directories as needed. Backups of existing files go OUTSIDE TestForum.

        Args:
            src_dir: Source directory to copy from
            dest_dir: Destination directory to copy to
            codename: Theme codename (for backup organization)

        Returns:
            Tuple of:
            - List of file metadata dicts (path, size, mtime, checksum, source)
            - List of absolute paths of directories WE CREATED (not pre-existing)
            - List of backup file paths created
        """
        files_deployed: List[Dict[str, Any]] = []
        dirs_created: List[str] = []
        backups_created: List[str] = []

        # Ensure base dest exists
        dest_dir.mkdir(parents=True, exist_ok=True)

        for src_file in src_dir.rglob("*"):
            if src_file.is_file():
                # Calculate relative path and destination
                rel_path = src_file.relative_to(src_dir)
                dest_file = dest_dir / rel_path

                # Track directories we need to create
                for parent in reversed(dest_file.parents):
                    if parent == dest_dir:
                        continue
                    if not parent.exists():
                        parent_str = str(parent)
                        if parent_str not in dirs_created and self._is_safe_to_track(parent, codename):
                            dirs_created.append(parent_str)

                # Create parent directories
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Backup existing file OUTSIDE TestForum
                if dest_file.exists():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_dir = self.backup_root / f"theme_{codename}" / timestamp
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

    def install_theme(
        self,
        codename: str,
        visibility: Optional[str] = None,
        set_default: bool = False
    ) -> Dict[str, Any]:
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
        6. Optionally set as default theme

        Args:
            codename: Theme codename
            visibility: 'public' or 'private' (uses default if None)
            set_default: Set as default/active theme after install

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

        deployment_timestamp = datetime.utcnow().isoformat()
        result = {
            "success": True,
            "theme": codename,
            "workspace_path": str(workspace_path),
            "deployed_at": deployment_timestamp,
            "stylesheets_deployed": 0,
            "templates_deployed": 0,
            "files_deployed": [],
            "dirs_created": [],
            "backups_created": [],
            "warnings": []
        }

        # Track all deployed files (with metadata) and directories we create
        all_files: List[Dict[str, Any]] = []
        all_dirs: List[str] = []
        all_backups: List[str] = []

        # Step 2: Deploy stylesheets
        stylesheets_dir = workspace_path / "stylesheets"
        if stylesheets_dir.exists():
            try:
                # Create new theme in MyBB database
                theme_name = meta.get("name", codename.title())

                # Check if theme already exists using bridge
                existing = self._bridge_call("theme:get", name=theme_name)
                if existing.get("success"):
                    tid = existing["data"]["tid"]
                    existing_templateset = existing["data"]["properties"].get("templateset")
                    theme_exists = True
                else:
                    # Theme doesn't exist - will create below
                    tid = None
                    existing_templateset = None
                    theme_exists = False

                # Step 1: Always ensure we have a proper templateset for this theme
                # Create or get "{Theme Name} Templates" templateset
                templateset_result = self._bridge_call(
                    "templateset:create",
                    title=f"{theme_name} Templates"
                )
                if not templateset_result.get("success"):
                    return f"Failed to create templateset: {templateset_result.get('error', 'Unknown error')}"

                templateset_sid = templateset_result["data"]["sid"]
                templateset_existed = templateset_result["data"].get("existed", False)

                # Step 2: Copy master templates if templateset is new
                if not templateset_existed:
                    copy_result = self._bridge_call(
                        "templateset:copy_master",
                        sid=templateset_sid
                    )
                    if not copy_result.get("success"):
                        return f"Failed to copy master templates: {copy_result.get('error', 'Unknown error')}"
                    templates_copied = copy_result["data"].get("templates_copied", 0)
                else:
                    templates_copied = 0  # Already has templates

                # Step 3: Create theme if it doesn't exist, or update templateset if needed
                if not theme_exists:
                    theme_result = self._bridge_call(
                        "theme:create",
                        name=theme_name,
                        pid=1,  # Parent is Master Style
                        templateset=templateset_sid
                    )
                    if not theme_result.get("success"):
                        return f"Failed to create theme: {theme_result.get('error', 'Unknown error')}"

                    tid = theme_result["data"]["tid"]
                elif existing_templateset != templateset_sid:
                    # Theme exists but has wrong/no templateset - update it
                    update_result = self._bridge_call(
                        "theme:set_property",
                        tid=tid,
                        key="templateset",
                        value=str(templateset_sid)
                    )
                    if not update_result.get("success"):
                        result["warnings"].append(
                            f"Failed to update templateset: {update_result.get('error', 'Unknown')}"
                        )

                # Deploy stylesheets from workspace
                for css_file in stylesheets_dir.glob("*.css"):
                    css_name = css_file.name
                    css_content = css_file.read_text(encoding='utf-8')

                    stylesheet_result = self._bridge_call(
                        "stylesheet:create",
                        tid=tid,
                        name=css_name,
                        content=css_content
                    )

                    if not stylesheet_result.get("success"):
                        # Log warning but continue - stylesheet failure shouldn't stop theme install
                        result["warnings"].append(
                            f"Failed to deploy stylesheet {css_name}: {stylesheet_result.get('error', 'Unknown')}"
                        )
                    else:
                        result["stylesheets_deployed"] += 1

                # CRITICAL: Call bridge to update theme's stylesheet list
                # This rebuilds disporder and stylesheets arrays in theme properties
                if result["stylesheets_deployed"] > 0:
                    try:
                        import subprocess
                        bridge_path = self.mybb_root / "mcp_bridge.php"
                        if bridge_path.exists():
                            cmd = [
                                "php",
                                str(bridge_path),
                                "--action=theme:update_stylesheet_list",
                                f"--tid={tid}",
                                "--json"
                            ]
                            bridge_proc = subprocess.run(
                                cmd,
                                cwd=str(self.mybb_root),
                                capture_output=True,
                                text=True,
                                timeout=30
                            )
                            if bridge_proc.returncode == 0:
                                result["theme_id"] = tid
                            else:
                                result["warnings"].append(
                                    f"Bridge update_stylesheet_list failed: {bridge_proc.stderr}"
                                )
                    except Exception as bridge_error:
                        result["warnings"].append(
                            f"Bridge call failed (stylesheets may not display): {str(bridge_error)}"
                        )

                # Set logo AFTER update_stylesheet_list (which rebuilds properties)
                logo_path = meta.get("logo")
                if logo_path:
                    try:
                        import subprocess
                        bridge_path = self.mybb_root / "mcp_bridge.php"
                        if bridge_path.exists():
                            logo_cmd = [
                                "php",
                                str(bridge_path),
                                "--action=theme:set_property",
                                f"--tid={tid}",
                                "--key=logo",
                                f"--value={logo_path}",
                                "--json"
                            ]
                            logo_proc = subprocess.run(
                                logo_cmd,
                                cwd=str(self.mybb_root),
                                capture_output=True,
                                text=True,
                                timeout=30
                            )
                            if logo_proc.returncode == 0:
                                result["logo_set"] = logo_path
                            else:
                                result["warnings"].append(
                                    f"Logo setting failed: {logo_proc.stderr}"
                                )
                    except Exception as logo_error:
                        result["warnings"].append(f"Logo setting failed: {str(logo_error)}")

            except Exception as e:
                result["warnings"].append(f"Stylesheet deployment failed: {str(e)}")

        # Step 3: Deploy template overrides to theme's templateset
        templates_dir = workspace_path / "templates"
        if templates_dir.exists():
            try:
                for template_file in templates_dir.glob("*.html"):
                    template_name = template_file.stem
                    template_content = template_file.read_text(encoding='utf-8')

                    template_result = self._bridge_call(
                        "template:write",
                        title=template_name,
                        template=template_content,
                        sid=templateset_sid  # Use theme's templateset, not hardcoded 1
                    )

                    if not template_result.get("success"):
                        result["warnings"].append(
                            f"Failed to deploy template {template_name}: {template_result.get('error', 'Unknown')}"
                        )
                    else:
                        result["templates_deployed"] = result.get("templates_deployed", 0) + 1
            except Exception as e:
                result["warnings"].append(f"Template deployment failed: {str(e)}")

        # Step 3.5: Deploy workspace files to TestForum filesystem
        # Themes can contain jscripts/, images/, or any other MyBB-structure directories
        # that need to be copied to TestForum (unlike stylesheets/templates which go to DB)
        for item in workspace_path.iterdir():
            item_name = item.name

            # Skip workspace-only files/directories (including stylesheets/templates)
            if item_name in self.WORKSPACE_ONLY:
                continue

            # Handle directories that mirror MyBB structure
            if item.is_dir():
                # Check if any files exist in the directory
                if not any(item.rglob("*")):
                    continue  # Skip empty directories

                # Direct overlay: workspace/jscripts/ -> TestForum/jscripts/
                dest_dir = self.mybb_root / item_name
                files, dirs, backups = self._overlay_directory(item, dest_dir, codename)
                all_files.extend(files)
                all_dirs.extend(dirs)
                all_backups.extend(backups)

            # Handle root-level files (if any)
            elif item.is_file():
                # Copy root-level files directly to MyBB root
                dest_file = self.mybb_root / item_name
                if dest_file.exists():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_dir = self.backup_root / f"theme_{codename}" / timestamp
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    backup_file = backup_dir / item_name
                    shutil.copy2(dest_file, backup_file)
                    all_backups.append(str(backup_file))
                shutil.copy2(item, dest_file)
                file_info = _get_file_metadata(dest_file, source_path=item)
                file_info["relative_path"] = item_name
                all_files.append(file_info)

        # Store deployment results
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
        result["file_count"] = len(all_files)
        result["dir_count"] = len(all_dirs)

        # Save deployment manifest to database for complete cleanup on uninstall
        if all_files:
            try:
                self.db.set_deployed_manifest(codename, all_files, all_dirs, all_backups)
            except Exception as e:
                result["warnings"].append(f"Failed to save deployment manifest: {str(e)}")

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
                file_info = f", {len(all_files)} files" if all_files else ""
                self.db.add_history(
                    project_id=project['id'],
                    action="installed",
                    details=(
                        f"Installed to TestForum - "
                        f"{result['stylesheets_deployed']} stylesheets, "
                        f"{result['templates_deployed']} templates{file_info}"
                    )
                )
        except Exception as e:
            result["warnings"].append(f"History entry failed: {str(e)}")

        # Step 6: Set as default theme if requested
        if set_default and result.get("theme_id"):
            try:
                tid = result["theme_id"]
                # Use bridge to set default theme
                # Note: theme:set_default action handles resetting other themes and setting this one
                default_result = self._bridge_call("theme:set_default", tid=tid)
                if default_result.get("success"):
                    result["set_as_default"] = True
                    result["warnings"].insert(0, f"✓ Theme '{meta.get('display_name', codename)}' set as default.")
                else:
                    result["warnings"].append(
                        f"Failed to set as default: {default_result.get('error', 'Unknown error')}"
                    )
            except Exception as e:
                result["warnings"].append(f"Failed to set as default: {str(e)}")

        # Add activation instructions (only if not already set as default)
        if not result.get("set_as_default"):
            result["warnings"].insert(0, (
                f"✓ Theme '{meta.get('display_name', codename)}' deployed. "
                "To activate: Go to MyBB Admin CP → Templates & Style → Themes, "
                "select this theme and click 'Set as Default'."
            ))

        return result

    def uninstall_theme(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
        """Remove theme files from TestForum using deployment manifest.

        Uses the stored manifest from install to ensure complete cleanup:
        1. Delete ALL files we deployed (from manifest)
        2. Delete ALL directories WE CREATED (not core MyBB dirs)
        3. Clear manifest from database
        4. Update project status

        Note: This removes deployed files but does NOT delete the theme record
        from MyBB database (stylesheets/templates remain).

        Args:
            codename: Theme codename
            visibility: 'public' or 'private' (uses default if None)

        Returns:
            Dict with status and details including removed files
        """
        uninstall_timestamp = datetime.utcnow().isoformat()
        result = {
            "success": True,
            "theme": codename,
            "uninstalled_at": uninstall_timestamp,
            "files_removed": [],
            "dirs_removed": [],
            "total_size_freed": 0,
            "original_deployment": None,
            "warnings": ["Theme uninstall removes deployed files but does not delete the theme record."]
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

        # Extract file paths from manifest
        files_to_delete = []
        for f in files_info:
            if isinstance(f, dict):
                files_to_delete.append({
                    "path": f.get("path"),
                    "size": f.get("size", 0),
                    "checksum": f.get("checksum")
                })
            else:
                files_to_delete.append({"path": f, "size": 0, "checksum": None})

        if not files_to_delete:
            result["warnings"].append(
                "No deployment manifest found - no files to remove"
            )

        # Step 1: Delete ALL deployed files
        total_freed = 0
        for file_info in files_to_delete:
            file_path_str = file_info["path"]
            file_path = Path(file_path_str)
            if file_path.exists():
                try:
                    actual_size = file_path.stat().st_size
                    file_path.unlink()
                    total_freed += actual_size

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
        dirs_sorted = sorted(dirs_to_delete, key=lambda p: p.count('/'), reverse=True)

        for dir_path_str in dirs_sorted:
            dir_path = Path(dir_path_str)

            # CRITICAL SAFETY CHECK: Never delete protected directories
            if self._is_protected_directory(dir_path):
                result["warnings"].append(
                    f"BLOCKED: Attempted to delete protected directory: {dir_path_str}"
                )
                continue

            if dir_path.exists() and dir_path.is_dir():
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
            # Manually clear installed_at
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

        # Step 5: Add history entry
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
