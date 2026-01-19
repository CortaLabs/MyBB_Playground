"""DiskSync service orchestrator - manages all sync components.

Extended to also support plugin_manager workspace sync operations.
"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, List

from ..db import MyBBDatabase
from .config import SyncConfig
from .router import PathRouter
from .groups import TemplateGroupManager
from .templates import TemplateExporter, TemplateImporter
from .stylesheets import StylesheetExporter, StylesheetImporter
from .plugin_templates import PluginTemplateImporter
from .cache import CacheRefresher
from .watcher import FileWatcher


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

        Pauses watcher during export to prevent race conditions.

        Args:
            set_name: Template set name (e.g., "Default Templates")

        Returns:
            Export statistics with files_exported, directory, template_set, groups

        Raises:
            ValueError: If template set not found
        """
        try:
            self.pause_watcher()
            result = await self.template_exporter.export_template_set(set_name)
            # Clear any queued events from our own export
            self._drain_watcher_queue()
            return result
        finally:
            self.resume_watcher()

    async def export_theme(self, theme_name: str) -> dict[str, Any]:
        """Export all stylesheets from a theme to disk.

        Pauses watcher during export to prevent race conditions.

        Args:
            theme_name: Theme name (e.g., "Default")

        Returns:
            Export statistics with files_exported, directory, theme_name

        Raises:
            ValueError: If theme not found
        """
        try:
            self.pause_watcher()
            result = await self.stylesheet_exporter.export_theme_stylesheets(theme_name)
            # Clear any queued events from our own export
            self._drain_watcher_queue()
            return result
        finally:
            self.resume_watcher()

    def _drain_watcher_queue(self) -> int:
        """Clear queued watcher events (after export to prevent re-import).

        Returns:
            Number of events drained
        """
        drained = 0
        while not self.watcher.work_queue.empty():
            try:
                self.watcher.work_queue.get_nowait()
                self.watcher.work_queue.task_done()
                drained += 1
            except Exception:
                break
        if drained > 0:
            print(f"[disk-sync] Drained {drained} queued events after export")
        return drained

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

    def pause_watcher(self) -> None:
        """Pause watcher event processing.

        Used during export operations to prevent race conditions.
        """
        self.watcher.pause()

    def resume_watcher(self) -> None:
        """Resume watcher event processing.

        Should be called after export operations complete.
        """
        self.watcher.resume()

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
            "templates_synced": [],
            "warnings": []
        }

        try:
            if direction == 'to_db':
                # Sync PHP and language files to TestForum
                php_result = self._sync_plugin_php(codename, workspace_path)
                result["files_synced"].extend(php_result.get("files", []))
                if php_result.get("warnings"):
                    result["warnings"].extend(php_result["warnings"])

                # Sync templates to database
                templates_result = self._sync_plugin_templates_to_db(
                    codename, workspace_path
                )
                result["templates_synced"] = templates_result.get("templates", [])
                if templates_result.get("warnings"):
                    result["warnings"].extend(templates_result["warnings"])

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

    def _sync_plugin_php(self, codename: str, workspace_path: Path) -> dict[str, Any]:
        """Sync plugin PHP and language files to TestForum.

        Args:
            codename: Plugin codename
            workspace_path: Path to plugin workspace

        Returns:
            Dict with synced files and warnings
        """
        result = {"files": [], "warnings": []}

        if not self.mybb_root:
            result["warnings"].append("mybb_root not configured")
            return result

        # Copy main PHP file
        src_php = workspace_path / "src" / f"{codename}.php"
        if src_php.exists():
            dest_php = self.mybb_root / "inc" / "plugins" / f"{codename}.php"
            dest_php.parent.mkdir(parents=True, exist_ok=True)

            # Backup if exists
            if dest_php.exists():
                backup = dest_php.with_suffix(
                    f".php.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                shutil.copy2(dest_php, backup)

            shutil.copy2(src_php, dest_php)
            result["files"].append(str(dest_php.relative_to(self.mybb_root)))
        else:
            result["warnings"].append(f"Plugin PHP not found: {src_php}")

        # Copy language files
        lang_src_dir = workspace_path / "languages" / "english"
        if lang_src_dir.exists():
            lang_dest_dir = self.mybb_root / "inc" / "languages" / "english"
            lang_dest_dir.mkdir(parents=True, exist_ok=True)

            for lang_file in lang_src_dir.glob("*.php"):
                dest = lang_dest_dir / lang_file.name
                if dest.exists():
                    backup = dest.with_suffix(
                        f".php.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )
                    shutil.copy2(dest, backup)
                shutil.copy2(lang_file, dest)
                result["files"].append(str(dest.relative_to(self.mybb_root)))

        return result

    def _sync_plugin_templates_to_db(
        self,
        codename: str,
        workspace_path: Path
    ) -> dict[str, Any]:
        """Sync plugin templates from workspace to database.

        Plugin templates use {codename}_{template_name} naming convention
        and are stored in master templates (sid=-2).

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

        for template_file in templates_dir.glob("*.html"):
            content = template_file.read_text(encoding='utf-8')
            if not content.strip():
                result["warnings"].append(f"Skipping empty template: {template_file.name}")
                continue

            # Plugin templates use {codename}_{name} convention
            full_template_name = f"{codename}_{template_file.stem}"

            # Write to master templates (sid=-2)
            try:
                # Check if template exists in master
                existing = self.db.get_template(full_template_name, sid=-2)
                if existing:
                    self.db.update_template(existing['tid'], content)
                else:
                    self.db.create_template(full_template_name, content, sid=-2)
                result["templates"].append(full_template_name)
            except Exception as e:
                result["warnings"].append(f"Template sync failed: {full_template_name} - {e}")

        return result

    def _sync_plugin_templates_from_db(
        self,
        codename: str,
        workspace_path: Path
    ) -> dict[str, Any]:
        """Export plugin templates from database to workspace.

        Args:
            codename: Plugin codename
            workspace_path: Path to plugin workspace

        Returns:
            Dict with exported templates and warnings
        """
        result = {"templates": [], "warnings": []}

        templates_dir = workspace_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Search for templates with codename prefix in master templates
        try:
            templates = self.db.search_templates(f"{codename}_", sid=-2)
            for template in templates:
                title = template['title']
                content = template['template']

                # Remove codename prefix for local file name
                local_name = title[len(codename) + 1:]  # Remove "{codename}_"
                file_path = templates_dir / f"{local_name}.html"

                file_path.write_text(content, encoding='utf-8')
                result["templates"].append(title)
        except Exception as e:
            result["warnings"].append(f"Template export failed: {e}")

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
            "templates_synced": [],
            "warnings": []
        }

        try:
            if direction == 'to_db':
                # Sync stylesheets to database
                stylesheet_result = self._sync_theme_stylesheets_to_db(
                    workspace_path, theme_tid
                )
                result["stylesheets_synced"] = stylesheet_result.get("stylesheets", [])
                if stylesheet_result.get("warnings"):
                    result["warnings"].extend(stylesheet_result["warnings"])

                # Sync template overrides to database
                templates_result = self._sync_theme_templates_to_db(
                    workspace_path, template_set_sid
                )
                result["templates_synced"] = templates_result.get("templates", [])
                if templates_result.get("warnings"):
                    result["warnings"].extend(templates_result["warnings"])

            elif direction == 'from_db':
                # Export stylesheets from database
                stylesheet_result = self._sync_theme_stylesheets_from_db(
                    workspace_path, theme_tid
                )
                result["stylesheets_synced"] = stylesheet_result.get("stylesheets", [])
                if stylesheet_result.get("warnings"):
                    result["warnings"].extend(stylesheet_result["warnings"])

                # Export template overrides from database
                templates_result = self._sync_theme_templates_from_db(
                    workspace_path, template_set_sid
                )
                result["templates_synced"] = templates_result.get("templates", [])
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
        """Sync theme stylesheets from workspace to database.

        Args:
            workspace_path: Path to theme workspace
            theme_tid: Theme ID in MyBB

        Returns:
            Dict with synced stylesheets and warnings
        """
        result = {"stylesheets": [], "warnings": []}

        stylesheets_dir = workspace_path / "stylesheets"
        if not stylesheets_dir.exists():
            return result

        for css_file in stylesheets_dir.glob("*.css"):
            content = css_file.read_text(encoding='utf-8')
            if not content.strip():
                result["warnings"].append(f"Skipping empty stylesheet: {css_file.name}")
                continue

            try:
                # Check if stylesheet exists for this theme
                existing = self.db.get_stylesheet_by_name(theme_tid, css_file.name)
                if existing:
                    self.db.update_stylesheet(existing['sid'], content)
                else:
                    self.db.create_stylesheet(theme_tid, css_file.name, content)
                result["stylesheets"].append(css_file.name)
            except Exception as e:
                result["warnings"].append(f"Stylesheet sync failed: {css_file.name} - {e}")

        return result

    def _sync_theme_stylesheets_from_db(
        self,
        workspace_path: Path,
        theme_tid: int
    ) -> dict[str, Any]:
        """Export theme stylesheets from database to workspace.

        Args:
            workspace_path: Path to theme workspace
            theme_tid: Theme ID in MyBB

        Returns:
            Dict with exported stylesheets and warnings
        """
        result = {"stylesheets": [], "warnings": []}

        stylesheets_dir = workspace_path / "stylesheets"
        stylesheets_dir.mkdir(parents=True, exist_ok=True)

        try:
            stylesheets = self.db.list_stylesheets(theme_tid)
            for stylesheet in stylesheets:
                name = stylesheet['name']
                content = stylesheet['stylesheet']

                file_path = stylesheets_dir / name
                file_path.write_text(content, encoding='utf-8')
                result["stylesheets"].append(name)
        except Exception as e:
            result["warnings"].append(f"Stylesheet export failed: {e}")

        return result

    def _sync_theme_templates_to_db(
        self,
        workspace_path: Path,
        template_set_sid: int
    ) -> dict[str, Any]:
        """Sync theme template overrides from workspace to database.

        Template overrides are stored in the theme's template set (not master).

        Args:
            workspace_path: Path to theme workspace
            template_set_sid: Template set ID

        Returns:
            Dict with synced templates and warnings
        """
        result = {"templates": [], "warnings": []}

        templates_dir = workspace_path / "templates"
        if not templates_dir.exists():
            return result

        for template_file in templates_dir.glob("*.html"):
            content = template_file.read_text(encoding='utf-8')
            if not content.strip():
                result["warnings"].append(f"Skipping empty template: {template_file.name}")
                continue

            template_name = template_file.stem

            try:
                # Check if template exists in this template set
                existing = self.db.get_template(template_name, sid=template_set_sid)
                if existing:
                    self.db.update_template(existing['tid'], content)
                else:
                    # Create as override in this template set
                    self.db.create_template(template_name, content, sid=template_set_sid)
                result["templates"].append(template_name)
            except Exception as e:
                result["warnings"].append(f"Template sync failed: {template_name} - {e}")

        return result

    def _sync_theme_templates_from_db(
        self,
        workspace_path: Path,
        template_set_sid: int
    ) -> dict[str, Any]:
        """Export theme template overrides from database to workspace.

        Args:
            workspace_path: Path to theme workspace
            template_set_sid: Template set ID

        Returns:
            Dict with exported templates and warnings
        """
        result = {"templates": [], "warnings": []}

        templates_dir = workspace_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Get templates from this specific template set (not master)
            templates = self.db.list_templates_by_set(template_set_sid)
            for template in templates:
                title = template['title']
                content = template['template']

                file_path = templates_dir / f"{title}.html"
                file_path.write_text(content, encoding='utf-8')
                result["templates"].append(title)
        except Exception as e:
            result["warnings"].append(f"Template export failed: {e}")

        return result
