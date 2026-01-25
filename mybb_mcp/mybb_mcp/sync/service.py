"""DiskSync service orchestrator - manages all sync components.

Extended to also support plugin_manager workspace sync operations.
"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, List

from ..db import MyBBDatabase
from ..bridge import MyBBBridgeClient
from .config import SyncConfig
from .router import PathRouter
from .groups import TemplateGroupManager
from .templates import TemplateExporter, TemplateImporter
from .stylesheets import StylesheetExporter, StylesheetImporter
from .plugin_templates import PluginTemplateImporter
from .cache import CacheRefresher
from .watcher import FileWatcher
from .manifest import SyncManifest


class DiskSyncService:
    """Main orchestrator for disk synchronization.

    Manages the lifecycle of all sync components:
    - Template and stylesheet exporters (DB -> Disk)
    - Template and stylesheet importers (Disk -> DB)
    - File watcher for automatic sync
    - Cache refresher for stylesheet updates

    Extended to support plugin_manager workspace sync:
    - sync_plugin() for plugin template/PHP/lang sync
    - sync_theme() for theme stylesheet/template sync
    """

    def __init__(
        self,
        db: MyBBDatabase,
        config: SyncConfig,
        mybb_url: str,
        workspace_root: Optional[Path] = None,
        mybb_root: Optional[Path] = None
    ):
        """Initialize DiskSync service.

        Args:
            db: MyBBDatabase instance for database operations
            config: SyncConfig with sync_root path
            mybb_url: MyBB installation URL (for cache refresh)
            workspace_root: Optional plugin_manager workspace root (for extended sync)
            mybb_root: Optional MyBB installation root (for PHP file copying)
        """
        self.db = db
        self.config = config
        self.mybb_url = mybb_url
        self.workspace_root = workspace_root
        self.mybb_root = mybb_root

        # Initialize core components with optional workspace_root
        self.router = PathRouter(config.sync_root, workspace_root)
        self.group_manager = TemplateGroupManager(db)

        # Initialize exporters
        self.template_exporter = TemplateExporter(db, self.router, self.group_manager)
        self.stylesheet_exporter = StylesheetExporter(db, self.router)

        # Initialize importers and cache refresher
        self.cache_refresher = CacheRefresher(mybb_url)
        self.template_importer = TemplateImporter(db)
        self.stylesheet_importer = StylesheetImporter(db)
        self.plugin_template_importer = PluginTemplateImporter(db)

        # Initialize file watcher (not started by default)
        self.watcher = FileWatcher(
            config.sync_root,
            self.template_importer,
            self.stylesheet_importer,
            self.plugin_template_importer,
            self.cache_refresher,
            self.router,
            workspace_root=workspace_root
        )

    async def export_template_set(self, set_name: str) -> dict[str, Any]:
        """Export all templates from a template set to disk.

        Stops watcher during export to prevent race conditions.

        Args:
            set_name: Template set name (e.g., "Default Templates")

        Returns:
            Export statistics with files_exported, directory, template_set, groups

        Raises:
            ValueError: If template set not found
        """
        was_running = self.watcher.is_running
        if was_running:
            await self.watcher.stop()
        try:
            return await self.template_exporter.export_template_set(set_name)
        finally:
            if was_running:
                self.watcher.start()

    async def export_theme(self, theme_name: str) -> dict[str, Any]:
        """Export all stylesheets from a theme to disk.

        Stops watcher during export to prevent race conditions.

        Args:
            theme_name: Theme name (e.g., "Default")

        Returns:
            Export statistics with files_exported, directory, theme_name

        Raises:
            ValueError: If theme not found
        """
        was_running = self.watcher.is_running
        if was_running:
            await self.watcher.stop()
        try:
            return await self.stylesheet_exporter.export_theme_stylesheets(theme_name)
        finally:
            if was_running:
                self.watcher.start()

    def start_watcher(self) -> bool:
        """Start the file watcher for automatic sync.

        Monitors sync_root directory for .html and .css file changes
        and automatically imports them to the database.

        Returns:
            True if watcher started successfully, False if already running
        """
        if self.watcher.is_running:
            return False

        self.watcher.start()
        return True

    def stop_watcher(self) -> bool:
        """Stop the file watcher.

        Returns:
            True if watcher stopped successfully, False if not running
        """
        if not self.watcher.is_running:
            return False

        self.watcher.stop()
        return True

    def get_status(self) -> dict[str, Any]:
        """Get current sync service status.

        Returns:
            Status dictionary with:
            - watcher_running: bool
            - sync_root: str (absolute path)
            - mybb_url: str
            - workspace_root: str (if configured)
        """
        status = {
            "watcher_running": self.watcher.is_running,
            "sync_root": str(self.config.sync_root.absolute()),
            "mybb_url": self.mybb_url
        }
        if self.workspace_root:
            status["workspace_root"] = str(self.workspace_root.absolute())
        return status

    # -------------------------------------------------------------------------
    # Extended: Plugin/Theme Workspace Sync Operations
    # -------------------------------------------------------------------------

    def sync_plugin(
        self,
        codename: str,
        workspace_path: Path,
        visibility: str = "public",
        direction: str = "to_db"
    ) -> dict[str, Any]:
        """Sync plugin files between workspace and TestForum/database.

        For direction='to_db':
        - Copy PHP files to TestForum/inc/plugins/
        - Copy language files to TestForum/inc/languages/english/
        - Sync templates to database (master templates, sid=-2)

        For direction='from_db':
        - Export templates from database to workspace

        Args:
            codename: Plugin codename
            workspace_path: Path to plugin workspace directory
            visibility: 'public' or 'private'
            direction: 'to_db' (workspace -> MyBB) or 'from_db' (MyBB -> workspace)

        Returns:
            Dict with sync results including files_synced, templates_synced, warnings
        """
        if self.mybb_root is None and direction == 'to_db':
            return {
                "success": False,
                "error": "mybb_root not configured - cannot sync PHP files",
                "plugin": codename
            }

        result = {
            "success": True,
            "plugin": codename,
            "direction": direction,
            "files_synced": [],
            "files_skipped": [],
            "templates_synced": [],
            "warnings": []
        }

        try:
            if direction == 'to_db':
                # Sync PHP and language files to TestForum (files ONLY, no DB writes)
                # Templates are copied as regular files - DB sync happens via full_pipeline
                php_result = self._sync_plugin_php(codename, workspace_path)
                result["files_synced"].extend(php_result.get("files", []))
                result["files_skipped"].extend(php_result.get("skipped", []))
                if php_result.get("warnings"):
                    result["warnings"].extend(php_result["warnings"])

                # NOTE: Template DB sync REMOVED from incremental mode.
                # Incremental sync copies files ONLY. To update templates in DB,
                # use full_pipeline=True which runs proper PHP lifecycle (_activate).
                # This prevents bypassing Bridge/MCP/PHP infrastructure.

            elif direction == 'from_db':
                # Export templates from database to workspace
                templates_result = self._sync_plugin_templates_from_db(
                    codename, workspace_path
                )
                result["templates_synced"] = templates_result.get("templates", [])
                if templates_result.get("warnings"):
                    result["warnings"].extend(templates_result["warnings"])

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    # Files/directories that are workspace-only and should NOT be deployed to TestForum
    # Mirrors PluginInstaller.WORKSPACE_ONLY from plugin_manager/installer.py
    # NOTE: templates/ and templates_themes/ ARE copied to TestForum in incremental mode.
    # They're regular files on disk. DB sync happens only via full_pipeline (PHP lifecycle).
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
        # templates and templates_themes are NOT excluded - they get copied as regular files
    }

    # Prefixes for files that should never be synced (checked via startswith)
    WORKSPACE_ONLY_PREFIXES = (
        ".sync_manifest",  # Sync manifest files
    )

    def _sync_plugin_php(self, codename: str, workspace_path: Path) -> dict[str, Any]:
        """Sync entire plugin workspace to TestForum via directory overlay.

        Copies ALL workspace contents to TestForum, except workspace-only files
        (meta.json, README.md, tests/, .git/, etc.). The workspace structure
        mirrors MyBB's layout, so most directories overlay directly:
        - workspace/inc/ -> TestForum/inc/
        - workspace/admin/ -> TestForum/admin/
        - workspace/jscripts/ -> TestForum/jscripts/
        - workspace/images/ -> TestForum/images/
        - workspace/*.php -> TestForum/*.php (root-level PHP files)

        Special handling for plugin-specific directories (via PluginInstaller.SPECIAL_DEST_DIRS):
        - workspace/templates/ -> TestForum/inc/plugins/{codename}/templates/
        - workspace/templates_themes/ -> TestForum/inc/plugins/{codename}/templates_themes/

        Uses PluginInstaller.SPECIAL_DEST_DIRS as canonical source for destination routing.

        Args:
            codename: Plugin codename
            workspace_path: Path to plugin workspace

        Returns:
            Dict with synced files, directories created, and warnings
        """
        result = {"files": [], "dirs_created": [], "warnings": []}

        # Initialize manifest for change detection
        manifest = SyncManifest(workspace_path / ".sync_manifest_plugins.json")
        result["skipped"] = []

        if not self.mybb_root:
            result["warnings"].append("mybb_root not configured")
            return result

        # Import PluginInstaller for SPECIAL_DEST_DIRS (canonical source)
        from plugin_manager.installer import PluginInstaller

        # Iterate over ALL items in workspace and deploy them
        for item in workspace_path.iterdir():
            item_name = item.name

            # Skip workspace-only files/directories
            if item_name in self.WORKSPACE_ONLY:
                continue

            # Skip files with workspace-only prefixes (e.g., .sync_manifest*)
            if item_name.startswith(self.WORKSPACE_ONLY_PREFIXES):
                continue

            # Handle directories
            if item.is_dir():
                # Check if any files exist in the directory
                if not any(item.rglob("*")):
                    continue  # Skip empty directories

                # Determine destination based on special handling or direct overlay
                # Use PluginInstaller.SPECIAL_DEST_DIRS as canonical source
                if item_name in PluginInstaller.SPECIAL_DEST_DIRS:
                    dest_dir = PluginInstaller.SPECIAL_DEST_DIRS[item_name](self.mybb_root, codename)
                else:
                    # Direct overlay: workspace/X/ -> TestForum/X/
                    dest_dir = self.mybb_root / item_name

                self._overlay_directory(item, dest_dir, result, manifest)
                # Note: result is modified in-place by _overlay_directory

            # Handle root-level files (e.g., standalone PHP pages)
            elif item.is_file():
                # Deploy root-level files directly to MyBB root
                self._overlay_file(item, self.mybb_root, result, manifest)
                # Note: result is modified in-place by _overlay_file

        # Verify at least one file was synced
        if not result["files"]:
            result["warnings"].append(
                f"No files synced for plugin '{codename}'. "
                f"Workspace may be empty or contain only workspace-only files."
            )

        # Save manifest after all files processed
        manifest.save()

        return result

    def _overlay_directory(
        self,
        src_dir: Path,
        dest_dir: Path,
        result: dict,
        manifest: Optional[SyncManifest] = None
    ) -> None:
        """Copy directory contents recursively to destination.

        Args:
            src_dir: Source directory to copy from
            dest_dir: Destination directory to copy to
            result: Result dict to update in-place (files, dirs_created, skipped)
            manifest: Optional SyncManifest for change detection

        Returns:
            None (modifies result dict in-place)
        """
        files_deployed: list[str] = []
        dirs_created: list[str] = []

        # Ensure base dest exists
        dest_dir.mkdir(parents=True, exist_ok=True)

        for src_file in src_dir.rglob("*"):
            if src_file.is_file():
                # Check if file changed (if manifest provided)
                if manifest:
                    current_hash = manifest.compute_file_hash(src_file)
                    if not manifest.file_changed(src_file, current_hash):
                        result.get("skipped", []).append(str(src_file.name))
                        continue

                # Calculate relative path and destination
                rel_path = src_file.relative_to(src_dir)
                dest_file = dest_dir / rel_path

                # Track directories we create
                for parent in reversed(dest_file.parents):
                    if parent == dest_dir:
                        continue
                    if not parent.exists():
                        parent_str = str(parent)
                        if parent_str not in dirs_created:
                            dirs_created.append(parent_str)

                # Create parent directories
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Backup existing file
                if dest_file.exists():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup = dest_file.with_suffix(
                        f"{dest_file.suffix}.backup.{timestamp}"
                    )
                    shutil.copy2(dest_file, backup)

                # Copy file
                shutil.copy2(src_file, dest_file)

                # Update manifest after successful copy
                if manifest:
                    manifest.update_file(src_file, current_hash=current_hash, sync_direction="to_db")

                # Record relative path from MyBB root
                try:
                    files_deployed.append(str(dest_file.relative_to(self.mybb_root)))
                except ValueError:
                    # If not relative to mybb_root, use absolute path
                    files_deployed.append(str(dest_file))

        # Update result dict in-place
        result["files"].extend(files_deployed)
        result["dirs_created"].extend(dirs_created)

    def _overlay_file(
        self,
        src_file: Path,
        dest_dir: Path,
        result: dict,
        manifest: Optional[SyncManifest] = None
    ) -> None:
        """Copy a single file to destination.

        Args:
            src_file: Source file to copy
            dest_dir: Destination directory to copy to
            result: Result dict to update in-place (files, skipped)
            manifest: Optional SyncManifest for change detection

        Returns:
            None (modifies result dict in-place)
        """
        # Check if file changed (if manifest provided)
        if manifest:
            current_hash = manifest.compute_file_hash(src_file)
            if not manifest.file_changed(src_file, current_hash):
                result.get("skipped", []).append(str(src_file.name))
                return

        files_deployed: list[str] = []

        dest_file = dest_dir / src_file.name

        # Backup existing file
        if dest_file.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup = dest_file.with_suffix(
                f"{dest_file.suffix}.backup.{timestamp}"
            )
            shutil.copy2(dest_file, backup)

        # Copy file
        shutil.copy2(src_file, dest_file)

        # Update manifest after successful copy
        if manifest:
            manifest.update_file(src_file, current_hash=current_hash, sync_direction="to_db")

        # Record relative path from MyBB root
        try:
            files_deployed.append(str(dest_file.relative_to(self.mybb_root)))
        except ValueError:
            files_deployed.append(str(dest_file))

        # Update result dict in-place
        result["files"].extend(files_deployed)

    def _sync_plugin_templates_to_db(
        self,
        codename: str,
        workspace_path: Path
    ) -> dict[str, Any]:
        """Sync plugin templates from workspace to database via bridge.

        Plugin templates use {codename}_{template_name} naming convention
        and are stored in master templates (sid=-2).

        Uses bridge template:batch_write for efficient bulk upsert.

        Args:
            codename: Plugin codename
            workspace_path: Path to plugin workspace

        Returns:
            Dict with synced templates and warnings
        """
        result = {"templates": [], "warnings": []}

        templates_dir = workspace_path / "templates"
        if not templates_dir.exists():
            return result

        # Collect all templates for batch write
        templates_batch = []
        for template_file in templates_dir.glob("*.html"):
            content = template_file.read_text(encoding='utf-8')
            if not content.strip():
                result["warnings"].append(f"Skipping empty template: {template_file.name}")
                continue

            # Plugin templates use {codename}_{name} convention
            full_template_name = f"{codename}_{template_file.stem}"
            templates_batch.append({
                "title": full_template_name,
                "template": content
            })

        if not templates_batch:
            return result

        # Use bridge for template writes (CLAUDE.md compliance)
        if not self.mybb_root:
            result["warnings"].append("mybb_root not configured - cannot use bridge for templates")
            return result

        try:
            import json
            bridge = MyBBBridgeClient(self.mybb_root)

            # Use batch_write for efficiency - writes to master templates (sid=-2)
            bridge_result = bridge.call(
                "template:batch_write",
                templates_json=json.dumps(templates_batch),
                sid=-2  # Master templates
            )

            if bridge_result.success:
                # All templates in batch were written
                for t in templates_batch:
                    result["templates"].append(t["title"])
            else:
                result["warnings"].append(
                    f"Bridge template:batch_write failed: {bridge_result.error}"
                )
        except Exception as e:
            result["warnings"].append(f"Template sync via bridge failed: {e}")

        return result

    def _sync_plugin_templates_from_db(
        self,
        codename: str,
        workspace_path: Path
    ) -> dict[str, Any]:
        """Export plugin templates from database to workspace via bridge.

        Uses bridge template:list endpoint to query templates with codename prefix.

        Args:
            codename: Plugin codename
            workspace_path: Path to plugin workspace

        Returns:
            Dict with exported templates and warnings
        """
        result = {"templates": [], "warnings": []}

        templates_dir = workspace_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Use bridge for template reads (CLAUDE.md compliance)
        if not self.mybb_root:
            result["warnings"].append("mybb_root not configured - cannot use bridge for templates")
            return result

        try:
            bridge = MyBBBridgeClient(self.mybb_root)

            # Use template:list with sid and title prefix filter
            bridge_result = bridge.call(
                "template:list",
                sid=-2,  # Master templates
                title=f"{codename}_"  # Plugin template prefix
            )

            if bridge_result.success:
                templates = bridge_result.data.get('templates', [])
                for template in templates:
                    title = template['title']
                    content = template['template']

                    # Remove codename prefix for local file name
                    local_name = title[len(codename) + 1:]  # Remove "{codename}_"
                    file_path = templates_dir / f"{local_name}.html"

                    file_path.write_text(content, encoding='utf-8')
                    result["templates"].append(title)
            else:
                result["warnings"].append(
                    f"Bridge template:list failed: {bridge_result.error}"
                )
        except Exception as e:
            result["warnings"].append(f"Template export via bridge failed: {e}")

        return result

    def sync_theme(
        self,
        codename: str,
        workspace_path: Path,
        visibility: str = "public",
        direction: str = "to_db",
        theme_tid: int = 1,
        template_set_sid: int = 1
    ) -> dict[str, Any]:
        """Sync theme files between workspace and database.

        For direction='to_db':
        - Sync stylesheets to database
        - Sync template overrides to database

        For direction='from_db':
        - Export stylesheets from database to workspace
        - Export template overrides from database to workspace

        Args:
            codename: Theme codename
            workspace_path: Path to theme workspace directory
            visibility: 'public' or 'private'
            direction: 'to_db' (workspace -> MyBB) or 'from_db' (MyBB -> workspace)
            theme_tid: Theme ID in MyBB (default 1 = Default)
            template_set_sid: Template set ID (default 1 = Default Templates)

        Returns:
            Dict with sync results including stylesheets_synced, templates_synced, warnings
        """
        result = {
            "success": True,
            "theme": codename,
            "direction": direction,
            "stylesheets_synced": [],
            "stylesheets_skipped": [],
            "templates_synced": [],
            "templates_skipped": [],
            "warnings": []
        }

        try:
            if direction == 'to_db':
                # Sync stylesheets to database
                stylesheet_result = self._sync_theme_stylesheets_to_db(
                    workspace_path, theme_tid
                )
                result["stylesheets_synced"] = stylesheet_result.get("stylesheets", [])
                result["stylesheets_skipped"] = stylesheet_result.get("skipped", [])
                if stylesheet_result.get("warnings"):
                    result["warnings"].extend(stylesheet_result["warnings"])

                # Sync template overrides to database
                templates_result = self._sync_theme_templates_to_db(
                    workspace_path, template_set_sid
                )
                result["templates_synced"] = templates_result.get("templates", [])
                result["templates_skipped"] = templates_result.get("skipped", [])
                if templates_result.get("warnings"):
                    result["warnings"].extend(templates_result["warnings"])

            elif direction == 'from_db':
                # Export stylesheets from database
                stylesheet_result = self._sync_theme_stylesheets_from_db(
                    workspace_path, theme_tid
                )
                result["stylesheets_synced"] = stylesheet_result.get("stylesheets", [])
                result["stylesheets_skipped"] = stylesheet_result.get("skipped", [])
                if stylesheet_result.get("warnings"):
                    result["warnings"].extend(stylesheet_result["warnings"])

                # Export template overrides from database
                templates_result = self._sync_theme_templates_from_db(
                    workspace_path, template_set_sid
                )
                result["templates_synced"] = templates_result.get("templates", [])
                result["templates_skipped"] = templates_result.get("skipped", [])
                if templates_result.get("warnings"):
                    result["warnings"].extend(templates_result["warnings"])

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def _sync_theme_stylesheets_to_db(
        self,
        workspace_path: Path,
        theme_tid: int
    ) -> dict[str, Any]:
        """Sync theme stylesheets from workspace to database via bridge.

        Uses bridge stylesheet:create which handles upsert logic internally.

        Args:
            workspace_path: Path to theme workspace
            theme_tid: Theme ID in MyBB

        Returns:
            Dict with synced stylesheets and warnings
        """
        result = {"stylesheets": [], "warnings": []}

        # Initialize manifest for change detection
        manifest = SyncManifest(workspace_path / ".sync_manifest.json")
        result["skipped"] = []

        stylesheets_dir = workspace_path / "stylesheets"
        if not stylesheets_dir.exists():
            return result

        # Use bridge for stylesheet writes (CLAUDE.md compliance)
        if not self.mybb_root:
            result["warnings"].append("mybb_root not configured - cannot use bridge for stylesheets")
            return result

        bridge = MyBBBridgeClient(self.mybb_root)

        for css_file in stylesheets_dir.glob("*.css"):
            # Check if file changed before reading content
            current_hash = manifest.compute_file_hash(css_file)
            if not manifest.file_changed(css_file, current_hash):
                result["skipped"].append(css_file.name)
                continue

            content = css_file.read_text(encoding='utf-8')
            if not content.strip():
                result["warnings"].append(f"Skipping empty stylesheet: {css_file.name}")
                continue

            try:
                # Bridge stylesheet:create handles upsert (create or update)
                bridge_result = bridge.call(
                    "stylesheet:create",
                    tid=theme_tid,
                    name=css_file.name,
                    content=content
                )

                if bridge_result.success:
                    result["stylesheets"].append(css_file.name)
                    # Update manifest with synced file
                    manifest.update_file(
                        css_file,
                        current_hash=current_hash,
                        sync_direction="to_db",
                        db_entity_type="stylesheet",
                        db_sid=theme_tid
                    )
                else:
                    result["warnings"].append(
                        f"Bridge stylesheet:create failed for {css_file.name}: {bridge_result.error}"
                    )
            except Exception as e:
                result["warnings"].append(f"Stylesheet sync via bridge failed: {css_file.name} - {e}")

        manifest.save()
        return result

    def _sync_theme_stylesheets_from_db(
        self,
        workspace_path: Path,
        theme_tid: int
    ) -> dict[str, Any]:
        """Export theme stylesheets from database to workspace via bridge.

        Uses bridge stylesheet:list endpoint to query stylesheets for theme.

        Args:
            workspace_path: Path to theme workspace
            theme_tid: Theme ID in MyBB

        Returns:
            Dict with exported stylesheets and warnings
        """
        result = {"stylesheets": [], "warnings": []}

        # Initialize manifest for change detection
        manifest = SyncManifest(workspace_path / ".sync_manifest.json")
        result["skipped"] = []

        stylesheets_dir = workspace_path / "stylesheets"
        stylesheets_dir.mkdir(parents=True, exist_ok=True)

        # Use bridge for stylesheet reads (CLAUDE.md compliance)
        if not self.mybb_root:
            result["warnings"].append("mybb_root not configured - cannot use bridge for stylesheets")
            return result

        try:
            bridge = MyBBBridgeClient(self.mybb_root)

            # Use stylesheet:list with tid filter
            bridge_result = bridge.call(
                "stylesheet:list",
                tid=theme_tid
            )

            if bridge_result.success:
                stylesheets = bridge_result.data.get('stylesheets', [])
                for stylesheet in stylesheets:
                    name = stylesheet['name']
                    content = stylesheet['stylesheet']
                    db_dateline = stylesheet.get('lastmodified', 0)  # MyBB uses 'lastmodified' for stylesheets

                    file_path = stylesheets_dir / name

                    # Check if DB has newer data (only if file already exists)
                    if file_path.exists() and not manifest.db_changed(file_path, db_dateline):
                        result["skipped"].append(name)
                        continue

                    # Write file
                    file_path.write_text(content, encoding='utf-8')
                    result["stylesheets"].append(name)

                    # Update manifest with from_db sync info
                    current_hash = manifest.compute_string_hash(content)
                    manifest.update_file(
                        file_path,
                        current_hash=current_hash,
                        sync_direction="from_db",
                        db_entity_type="stylesheet",
                        db_sid=theme_tid,
                        db_dateline=db_dateline
                    )
            else:
                result["warnings"].append(
                    f"Bridge stylesheet:list failed: {bridge_result.error}"
                )
        except Exception as e:
            result["warnings"].append(f"Stylesheet export via bridge failed: {e}")

        manifest.save()
        return result

    def _sync_theme_templates_to_db(
        self,
        workspace_path: Path,
        template_set_sid: int
    ) -> dict[str, Any]:
        """Sync theme template overrides from workspace to database via bridge.

        Template overrides are stored in the theme's template set (not master).
        Uses bridge template:batch_write for efficient bulk upsert.

        Args:
            workspace_path: Path to theme workspace
            template_set_sid: Template set ID

        Returns:
            Dict with synced templates and warnings
        """
        result = {"templates": [], "warnings": []}

        # Initialize manifest for change detection
        manifest = SyncManifest(workspace_path / ".sync_manifest.json")
        result["skipped"] = []

        templates_dir = workspace_path / "templates"
        if not templates_dir.exists():
            return result

        # Collect all templates for batch write
        templates_batch = []
        for template_file in templates_dir.glob("**/*.html"):  # Recursive glob
            # Check if file changed before reading content
            current_hash = manifest.compute_file_hash(template_file)
            if not manifest.file_changed(template_file, current_hash):
                result["skipped"].append(template_file.stem)
                continue

            content = template_file.read_text(encoding='utf-8')
            if not content.strip():
                result["warnings"].append(f"Skipping empty template: {template_file.name}")
                continue

            template_name = template_file.stem
            templates_batch.append({
                "title": template_name,
                "template": content,
                "_hash": current_hash,  # Store for manifest update
                "_path": template_file   # Store for manifest update
            })

        if not templates_batch:
            return result

        # Use bridge for template writes (CLAUDE.md compliance)
        if not self.mybb_root:
            result["warnings"].append("mybb_root not configured - cannot use bridge for templates")
            return result

        try:
            import json
            bridge = MyBBBridgeClient(self.mybb_root)

            # Clean batch for bridge (remove internal keys)
            clean_batch = [{"title": t["title"], "template": t["template"]} for t in templates_batch]

            # Use batch_write for efficiency - writes to the specified template set
            bridge_result = bridge.call(
                "template:batch_write",
                templates_json=json.dumps(clean_batch),
                sid=template_set_sid  # Theme's template set (not master)
            )

            if bridge_result.success:
                # All templates in batch were written
                for t in templates_batch:
                    result["templates"].append(t["title"])
                    # Update manifest with synced file
                    manifest.update_file(
                        t["_path"],
                        current_hash=t["_hash"],
                        sync_direction="to_db",
                        db_entity_type="template",
                        db_sid=template_set_sid
                    )
                manifest.save()
            else:
                result["warnings"].append(
                    f"Bridge template:batch_write failed: {bridge_result.error}"
                )
        except Exception as e:
            result["warnings"].append(f"Template sync via bridge failed: {e}")

        return result

    def _sync_theme_templates_from_db(
        self,
        workspace_path: Path,
        template_set_sid: int
    ) -> dict[str, Any]:
        """Export theme template overrides from database to workspace via bridge.

        Uses bridge template:list endpoint to query templates for the template set.

        Args:
            workspace_path: Path to theme workspace
            template_set_sid: Template set ID

        Returns:
            Dict with exported templates and warnings
        """
        result = {"templates": [], "warnings": []}

        # Initialize manifest for change detection
        manifest = SyncManifest(workspace_path / ".sync_manifest.json")
        result["skipped"] = []

        # Initialize group manager for categorization
        group_manager = TemplateGroupManager(self.db)

        templates_dir = workspace_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Use bridge for template reads (CLAUDE.md compliance)
        if not self.mybb_root:
            result["warnings"].append("mybb_root not configured - cannot use bridge for templates")
            return result

        try:
            bridge = MyBBBridgeClient(self.mybb_root)

            # Use template:list with sid filter (no title prefix for theme templates)
            bridge_result = bridge.call(
                "template:list",
                sid=template_set_sid
            )

            if bridge_result.success:
                templates = bridge_result.data.get('templates', [])
                for template in templates:
                    title = template['title']
                    content = template['template']
                    db_dateline = template.get('dateline', 0)

                    # Build grouped path directly from workspace_path
                    group_name = group_manager.get_group_name(title, sid=template_set_sid)
                    file_path = workspace_path / "templates" / group_name / f"{title}.html"

                    # Check if DB has newer data (only if file already exists)
                    if file_path.exists() and not manifest.db_changed(file_path, db_dateline):
                        result["skipped"].append(title)
                        continue

                    # Create group directory if needed
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    # Write file
                    file_path.write_text(content, encoding='utf-8')
                    result["templates"].append(title)

                    # Update manifest with from_db sync info
                    current_hash = manifest.compute_string_hash(content)
                    manifest.update_file(
                        file_path,
                        current_hash=current_hash,
                        sync_direction="from_db",
                        db_entity_type="template",
                        db_sid=template_set_sid,
                        db_dateline=db_dateline
                    )

                # Save manifest after processing all templates
                manifest.save()
            else:
                result["warnings"].append(
                    f"Bridge template:list failed: {bridge_result.error}"
                )
        except Exception as e:
            result["warnings"].append(f"Template export via bridge failed: {e}")

        return result
