"""File system watcher for disk-sync.

Monitors sync directory for file changes and triggers appropriate import operations.
Handles both regular writes and atomic writes (used by Claude Code and other editors).
"""

import time
from pathlib import Path
from threading import Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from mybb_mcp.sync.templates import TemplateImporter
from mybb_mcp.sync.stylesheets import StylesheetImporter
from mybb_mcp.sync.cache import CacheRefresher
from mybb_mcp.sync.router import PathRouter


class SyncEventHandler(FileSystemEventHandler):
    """Handles file system events for template and stylesheet changes.

    Supports multiple write strategies:
    - Direct writes: triggers on_modified
    - Atomic writes (temp + rename): triggers on_moved or on_created

    Uses debouncing to prevent duplicate syncs when editors fire multiple events.
    """

    # Debounce window in seconds - ignore duplicate events within this time
    DEBOUNCE_SECONDS = 0.5

    def __init__(
        self,
        template_importer: TemplateImporter,
        stylesheet_importer: StylesheetImporter,
        cache_refresher: CacheRefresher,
        router: PathRouter
    ):
        """Initialize sync event handler.

        Args:
            template_importer: TemplateImporter instance for template updates
            stylesheet_importer: StylesheetImporter instance for stylesheet updates
            cache_refresher: CacheRefresher instance for cache refresh
            router: PathRouter instance for path parsing
        """
        super().__init__()
        self.template_importer = template_importer
        self.stylesheet_importer = stylesheet_importer
        self.cache_refresher = cache_refresher
        self.router = router

        # Debouncing: track last sync time per file
        self._last_sync: dict[str, float] = {}
        self._lock = Lock()

    def _should_process(self, path: Path) -> bool:
        """Check if file should be processed (debounce check).

        Args:
            path: File path to check

        Returns:
            True if enough time has passed since last sync for this file
        """
        path_str = str(path)
        now = time.time()

        with self._lock:
            last_time = self._last_sync.get(path_str, 0)
            if now - last_time < self.DEBOUNCE_SECONDS:
                return False
            self._last_sync[path_str] = now
            return True

    def _handle_file_change(self, path: Path) -> None:
        """Route file change to appropriate handler.

        Args:
            path: Path to changed file
        """
        # Ignore non-files and temp files
        if not path.is_file():
            return
        if path.name.startswith('.') or path.name.endswith('~'):
            return

        # Debounce check
        if not self._should_process(path):
            return

        # Handle template changes (.html files in template_sets/)
        if path.suffix == '.html' and 'template_sets' in path.parts:
            self._handle_template_change(path)

        # Handle stylesheet changes (.css files in styles/)
        elif path.suffix == '.css' and 'styles' in path.parts:
            self._handle_stylesheet_change(path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events (direct writes).

        Args:
            event: File system event from watchdog
        """
        if event.is_directory:
            return
        self._handle_file_change(Path(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events (some atomic writes).

        Args:
            event: File system event from watchdog
        """
        if event.is_directory:
            return
        self._handle_file_change(Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename events (atomic writes: temp -> target).

        Args:
            event: File system event from watchdog
        """
        if event.is_directory:
            return
        # For moves, we care about the destination (the final file)
        if hasattr(event, 'dest_path'):
            self._handle_file_change(Path(event.dest_path))

    def _handle_template_change(self, path: Path) -> None:
        """Handle template file change.

        Args:
            path: Path to changed template file
        """
        try:
            # Get relative path from sync_root
            rel_path = path.relative_to(self.router.sync_root)
            parsed = self.router.parse(str(rel_path))
            if parsed.type != "template" or not parsed.set_name or not parsed.template_name:
                return

            # Read file content
            content = path.read_text(encoding='utf-8')

            # Import template to database
            import asyncio
            asyncio.run(
                self.template_importer.import_template(
                    parsed.set_name,
                    parsed.template_name,
                    content
                )
            )
            print(f"[disk-sync] Template synced: {parsed.template_name}")

        except Exception as e:
            print(f"[disk-sync] Template sync error: {e}")

    def _handle_stylesheet_change(self, path: Path) -> None:
        """Handle stylesheet file change.

        Args:
            path: Path to changed stylesheet file
        """
        try:
            # Get relative path from sync_root
            rel_path = path.relative_to(self.router.sync_root)
            parsed = self.router.parse(str(rel_path))
            if parsed.type != "stylesheet" or not parsed.theme_name or not parsed.stylesheet_name:
                return

            # Read file content
            content = path.read_text(encoding='utf-8')

            # Import stylesheet to database
            import asyncio
            asyncio.run(
                self.stylesheet_importer.import_stylesheet(
                    parsed.theme_name,
                    parsed.stylesheet_name,
                    content
                )
            )

            # Refresh cache
            asyncio.run(
                self.cache_refresher.refresh_stylesheet(
                    parsed.theme_name,
                    parsed.stylesheet_name
                )
            )
            print(f"[disk-sync] Stylesheet synced: {parsed.stylesheet_name}")

        except Exception as e:
            print(f"[disk-sync] Stylesheet sync error: {e}")


class FileWatcher:
    """Watches sync directory for file changes."""

    def __init__(
        self,
        sync_root: Path,
        template_importer: TemplateImporter,
        stylesheet_importer: StylesheetImporter,
        cache_refresher: CacheRefresher,
        router: PathRouter
    ):
        """Initialize file watcher.

        Args:
            sync_root: Root directory to watch
            template_importer: TemplateImporter instance
            stylesheet_importer: StylesheetImporter instance
            cache_refresher: CacheRefresher instance
            router: PathRouter instance
        """
        self.sync_root = sync_root
        self.observer = Observer()
        self.handler = SyncEventHandler(
            template_importer,
            stylesheet_importer,
            cache_refresher,
            router
        )

    def start(self) -> None:
        """Start watching the sync directory."""
        self.observer.schedule(self.handler, str(self.sync_root), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        """Stop watching the sync directory."""
        self.observer.stop()
        self.observer.join()

    @property
    def is_running(self) -> bool:
        """Check if watcher is currently running.

        Returns:
            True if observer is alive, False otherwise
        """
        return self.observer.is_alive()
