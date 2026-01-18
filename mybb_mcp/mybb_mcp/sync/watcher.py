"""File system watcher for disk-sync.

Monitors sync directory for file changes and triggers appropriate import operations.
Handles both regular writes and atomic writes (used by Claude Code and other editors).
"""

import asyncio
import time
from pathlib import Path
from threading import Lock
from typing import Literal, Optional
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
        router: PathRouter,
        work_queue: asyncio.Queue
    ):
        """Initialize sync event handler.

        Args:
            template_importer: TemplateImporter instance for template updates
            stylesheet_importer: StylesheetImporter instance for stylesheet updates
            cache_refresher: CacheRefresher instance for cache refresh
            router: PathRouter instance for path parsing
            work_queue: Asyncio queue for thread-safe work submission
        """
        super().__init__()
        self.template_importer = template_importer
        self.stylesheet_importer = stylesheet_importer
        self.cache_refresher = cache_refresher
        self.router = router
        self.work_queue = work_queue

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
        # Ignore .tmp files used for atomic writes
        if path.suffix == '.tmp':
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

            # Validate file size before reading (prevent empty file corruption)
            try:
                file_size = path.stat().st_size
                if file_size == 0:
                    print(f"[disk-sync] WARNING: Skipping empty file: {path}")
                    return
            except FileNotFoundError:
                # File was deleted between event and processing
                return

            # Read file content
            content = path.read_text(encoding='utf-8')

            # Queue work for async processing (thread-safe)
            self.work_queue.put_nowait({
                "type": "template",
                "set_name": parsed.set_name,
                "template_name": parsed.template_name,
                "content": content
            })

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

            # Validate file size before reading (prevent empty file corruption)
            try:
                file_size = path.stat().st_size
                if file_size == 0:
                    print(f"[disk-sync] WARNING: Skipping empty file: {path}")
                    return
            except FileNotFoundError:
                # File was deleted between event and processing
                return

            # Read file content
            content = path.read_text(encoding='utf-8')

            # Queue work for async processing (thread-safe)
            self.work_queue.put_nowait({
                "type": "stylesheet",
                "theme_name": parsed.theme_name,
                "stylesheet_name": parsed.stylesheet_name,
                "content": content
            })

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
        self.template_importer = template_importer
        self.stylesheet_importer = stylesheet_importer
        self.cache_refresher = cache_refresher

        # Thread-safe queue for passing work from watchdog threads to async context
        self.work_queue: asyncio.Queue = asyncio.Queue()

        self.observer = Observer()
        self.handler = SyncEventHandler(
            template_importer,
            stylesheet_importer,
            cache_refresher,
            router,
            self.work_queue
        )

        # Background task for processing queued work
        self._processor_task: Optional[asyncio.Task] = None

        # Pause mechanism for export operations
        self._paused = False
        self._pause_lock = Lock()

    def pause(self) -> None:
        """Pause watcher event processing. Idempotent.

        Used during export operations to prevent race conditions.
        Queued events will wait until resume() is called.
        """
        with self._pause_lock:
            if self._paused:
                return
            self._paused = True
            print("[disk-sync] Watcher paused")

    def resume(self) -> None:
        """Resume watcher event processing. Idempotent.

        Allows queued events to be processed after exports complete.
        """
        with self._pause_lock:
            if not self._paused:
                return
            self._paused = False
            print("[disk-sync] Watcher resumed")

    async def _process_work_queue(self) -> None:
        """Background task that processes queued file changes.

        Runs in the main asyncio event loop and processes work items
        queued by watchdog worker threads.
        """
        while True:
            try:
                # Get work item from queue
                work_item = await self.work_queue.get()

                # Wait while paused (e.g., during export operations)
                while self._paused:
                    await asyncio.sleep(0.1)

                # Process based on type
                if work_item["type"] == "template":
                    await self.template_importer.import_template(
                        work_item["set_name"],
                        work_item["template_name"],
                        work_item["content"]
                    )
                    print(f"[disk-sync] Template synced: {work_item['template_name']}")

                elif work_item["type"] == "stylesheet":
                    await self.stylesheet_importer.import_stylesheet(
                        work_item["theme_name"],
                        work_item["stylesheet_name"],
                        work_item["content"]
                    )
                    await self.cache_refresher.refresh_stylesheet(
                        work_item["theme_name"],
                        work_item["stylesheet_name"]
                    )
                    print(f"[disk-sync] Stylesheet synced: {work_item['stylesheet_name']}")

                # Mark task as done
                self.work_queue.task_done()

            except asyncio.CancelledError:
                # Task cancelled during shutdown
                break
            except Exception as e:
                print(f"[disk-sync] Queue processor error: {e}")
                # Mark task as done even on error to prevent queue blocking
                self.work_queue.task_done()

    def start(self) -> None:
        """Start watching the sync directory."""
        # Start background processor task
        if self._processor_task is None or self._processor_task.done():
            self._processor_task = asyncio.create_task(self._process_work_queue())

        # Start file system observer
        self.observer.schedule(self.handler, str(self.sync_root), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        """Stop watching the sync directory."""
        # Stop file system observer
        self.observer.stop()
        self.observer.join()

        # Cancel background processor task
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()

    @property
    def is_running(self) -> bool:
        """Check if watcher is currently running.

        Returns:
            True if observer is alive, False otherwise
        """
        return self.observer.is_alive()
