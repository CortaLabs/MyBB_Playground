"""DiskSync service orchestrator - manages all sync components."""

from pathlib import Path
from typing import Any

from ..db import MyBBDatabase
from .config import SyncConfig
from .router import PathRouter
from .groups import TemplateGroupManager
from .templates import TemplateExporter, TemplateImporter
from .stylesheets import StylesheetExporter, StylesheetImporter
from .cache import CacheRefresher
from .watcher import FileWatcher


class DiskSyncService:
    """Main orchestrator for disk synchronization.

    Manages the lifecycle of all sync components:
    - Template and stylesheet exporters (DB -> Disk)
    - Template and stylesheet importers (Disk -> DB)
    - File watcher for automatic sync
    - Cache refresher for stylesheet updates
    """

    def __init__(self, db: MyBBDatabase, config: SyncConfig, mybb_url: str):
        """Initialize DiskSync service.

        Args:
            db: MyBBDatabase instance for database operations
            config: SyncConfig with sync_root path
            mybb_url: MyBB installation URL (for cache refresh)
        """
        self.db = db
        self.config = config
        self.mybb_url = mybb_url

        # Initialize core components
        self.router = PathRouter(config.sync_root)
        self.group_manager = TemplateGroupManager(db)

        # Initialize exporters
        self.template_exporter = TemplateExporter(db, self.router, self.group_manager)
        self.stylesheet_exporter = StylesheetExporter(db, self.router)

        # Initialize importers and cache refresher
        self.cache_refresher = CacheRefresher(mybb_url)
        self.template_importer = TemplateImporter(db)
        self.stylesheet_importer = StylesheetImporter(db)

        # Initialize file watcher (not started by default)
        self.watcher = FileWatcher(
            config.sync_root,
            self.template_importer,
            self.stylesheet_importer,
            self.cache_refresher,
            self.router
        )

    async def export_template_set(self, set_name: str) -> dict[str, Any]:
        """Export all templates from a template set to disk.

        Args:
            set_name: Template set name (e.g., "Default Templates")

        Returns:
            Export statistics with files_exported, directory, template_set, groups

        Raises:
            ValueError: If template set not found
        """
        return await self.template_exporter.export_template_set(set_name)

    async def export_theme(self, theme_name: str) -> dict[str, Any]:
        """Export all stylesheets from a theme to disk.

        Args:
            theme_name: Theme name (e.g., "Default")

        Returns:
            Export statistics with files_exported, directory, theme_name

        Raises:
            ValueError: If theme not found
        """
        return await self.stylesheet_exporter.export_theme_stylesheets(theme_name)

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
        """
        return {
            "watcher_running": self.watcher.is_running,
            "sync_root": str(self.config.sync_root.absolute()),
            "mybb_url": self.mybb_url
        }
