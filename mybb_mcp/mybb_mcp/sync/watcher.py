"""File system watcher for disk-sync.

Monitors sync directory for file changes and triggers appropriate import operations.
Handles both regular writes and atomic writes (used by Claude Code and other editors).
"""

import asyncio
import time
from pathlib import Path
from threading import Lock
from typing import Dict, Literal, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from mybb_mcp.sync.templates import TemplateImporter
from mybb_mcp.sync.stylesheets import StylesheetImporter
from mybb_mcp.sync.plugin_templates import PluginTemplateImporter
from mybb_mcp.sync.cache import CacheRefresher
from mybb_mcp.sync.router import PathRouter


class SyncEventHandler(FileSystemEventHandler):
    """Handles file system events for template and stylesheet changes.

    Supports multiple write strategies:
    - Direct writes: triggers on_modified
    - Atomic writes (temp + rename): triggers on_moved or on_created

    Uses debouncing to prevent duplicate syncs when editors fire multiple events.
    Queues work items directly to asyncio queue for async processing.
    """

    # Debounce window in seconds - ignore duplicate events within this time
    DEBOUNCE_SECONDS = 0.1

    def __init__(
        self,
        template_importer: TemplateImporter,
        stylesheet_importer: StylesheetImporter,
        plugin_template_importer: PluginTemplateImporter,
        cache_refresher: CacheRefresher,
        router: PathRouter,
        work_queue: asyncio.Queue,
        watcher: 'FileWatcher' = None
    ):
        """Initialize sync event handler.

        Args:
            template_importer: (Unused, kept for compatibility with FileWatcher)
            stylesheet_importer: (Unused, kept for compatibility with FileWatcher)
            plugin_template_importer: (Unused, kept for compatibility with FileWatcher)
            cache_refresher: (Unused, kept for compatibility with FileWatcher)
            router: PathRouter instance for path parsing
            work_queue: Asyncio queue for thread-safe work submission
            watcher: FileWatcher instance for accessing workspace_root
        """
        super().__init__()
        # Note: importer params kept in signature for FileWatcher compatibility
        # but not stored - handler only queues work, doesn't process it
        self.router = router
        self.work_queue = work_queue
        self.watcher = watcher

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

        # Handle plugin template changes (.html files in plugins/*/templates/)
        elif path.suffix == '.html' and 'plugins' in path.parts and 'templates' in path.parts:
            self._handle_plugin_template_change(path)

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

            # Queue work item directly to async processor
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

            # Queue work item directly to async processor
            self.work_queue.put_nowait({
                "type": "stylesheet",
                "theme_name": parsed.theme_name,
                "stylesheet_name": parsed.stylesheet_name,
                "content": content
            })

        except Exception as e:
            print(f"[disk-sync] Stylesheet sync error: {e}")

    def _handle_plugin_template_change(self, path: Path) -> None:
        """Handle plugin template file changes.

        Plugin templates can be in two locations:
        - Default: plugin_manager/plugins/{visibility}/{codename}/templates/{name}.html
          → syncs to sid=-2 (master templates)
        - Theme-specific: plugin_manager/plugins/{visibility}/{codename}/templates_themes/{theme_name}/{name}.html
          → syncs to specific template set sid

        Args:
            path: Path to changed plugin template file
        """
        try:
            # Use router to parse the path - need to make path relative to workspace_root
            if not self.watcher or not self.watcher.workspace_root:
                return  # No workspace_root means we shouldn't be here

            try:
                rel_path = path.relative_to(self.watcher.workspace_root)
            except ValueError:
                return  # Path not under workspace_root

            parsed = self.router.parse(str(rel_path))

            if parsed.type != 'plugin_template' or not parsed.project_name or not parsed.template_name:
                return

            # Prevent empty file corruption
            try:
                file_size = path.stat().st_size
                if file_size == 0:
                    print(f"[disk-sync] WARNING: Skipping empty file: {path}")
                    return
            except FileNotFoundError:
                # File was deleted between event and processing
                return

            # Read content
            content = path.read_text(encoding='utf-8')

            # Queue work item directly to async processor
            # Include theme_name from parsed path (can be None for default templates)
            self.work_queue.put_nowait({
                "type": "plugin_template",
                "codename": parsed.project_name,
                "template_name": parsed.template_name,
                "content": content,
                "theme_name": parsed.theme_name  # None for default templates, theme name for theme-specific
            })

            # Enhanced logging to show theme-specific vs default
            if parsed.theme_name:
                print(f"[disk-sync] Plugin template queued: {parsed.project_name}_{parsed.template_name} (theme: {parsed.theme_name})")
            else:
                print(f"[disk-sync] Plugin template queued: {parsed.project_name}_{parsed.template_name}")

        except Exception as e:
            print(f"[disk-sync] Plugin template sync error: {e}")


class FileWatcher:
    """Watches sync directory for file changes."""

    # Batching configuration
    BATCH_WINDOW_SECONDS = 0.1
    MAX_BATCH_SIZE = 50

    def __init__(
        self,
        sync_root: Path,
        template_importer: TemplateImporter,
        stylesheet_importer: StylesheetImporter,
        plugin_template_importer: PluginTemplateImporter,
        cache_refresher: CacheRefresher,
        router: PathRouter,
        workspace_root: Optional[Path] = None
    ):
        """Initialize file watcher.

        Args:
            sync_root: Root directory to watch
            template_importer: TemplateImporter instance
            stylesheet_importer: StylesheetImporter instance
            plugin_template_importer: PluginTemplateImporter instance for workspace templates
            cache_refresher: CacheRefresher instance
            router: PathRouter instance
            workspace_root: Optional workspace root to watch for plugin template changes
        """
        self.sync_root = sync_root
        self.workspace_root = workspace_root
        self.template_importer = template_importer
        self.stylesheet_importer = stylesheet_importer
        self.plugin_template_importer = plugin_template_importer
        self.cache_refresher = cache_refresher

        # Thread-safe queue for passing work from watchdog threads to async context
        self.work_queue: asyncio.Queue = asyncio.Queue()

        self.observer = Observer()
        self.handler = SyncEventHandler(
            template_importer,
            stylesheet_importer,
            plugin_template_importer,
            cache_refresher,
            router,
            self.work_queue,
            watcher=self
        )

        # Background task for processing queued work
        self._processor_task: Optional[asyncio.Task] = None

    def _make_dedup_key(self, item: dict) -> str:
        """Create a deduplication key for a work item.

        Args:
            item: Work item dictionary

        Returns:
            String key that uniquely identifies this work item
        """
        if item["type"] == "template":
            return f"template:{item['set_name']}:{item['template_name']}"
        elif item["type"] == "stylesheet":
            return f"stylesheet:{item['theme_name']}:{item['stylesheet_name']}"
        elif item["type"] == "plugin_template":
            theme = item.get('theme_name', 'master')
            return f"plugin_template:{item['codename']}:{item['template_name']}:{theme}"
        else:
            # Fallback for unknown types
            return f"{item['type']}:{hash(str(item))}"

    async def _process_batch(self, items: list[dict]) -> None:
        """Process a batch of work items.

        Args:
            items: List of work item dictionaries to process
        """
        print(f"[disk-sync] Processing batch of {len(items)} items")

        for item in items:
            try:
                if item["type"] == "template":
                    await self.template_importer.import_template(
                        item["set_name"],
                        item["template_name"],
                        item["content"]
                    )
                    print(f"[disk-sync] Template synced: {item['template_name']}")

                elif item["type"] == "stylesheet":
                    await self.stylesheet_importer.import_stylesheet(
                        item["theme_name"],
                        item["stylesheet_name"],
                        item["content"]
                    )
                    await self.cache_refresher.refresh_stylesheet(
                        item["theme_name"],
                        item["stylesheet_name"]
                    )
                    print(f"[disk-sync] Stylesheet synced: {item['stylesheet_name']}")

                elif item["type"] == "plugin_template":
                    await self.plugin_template_importer.import_template(
                        item["codename"],
                        item["template_name"],
                        item["content"],
                        item.get("theme_name")
                    )
                    # Enhanced logging for theme-specific templates
                    if item.get("theme_name"):
                        print(f"[disk-sync] Plugin template synced: {item['codename']}_{item['template_name']} (theme: {item['theme_name']})")
                    else:
                        print(f"[disk-sync] Plugin template synced: {item['codename']}_{item['template_name']}")

            except Exception as e:
                # Log error and continue processing remaining items
                print(f"[disk-sync] Error processing {item.get('type', 'unknown')} item: {e}")

    async def _process_work_queue(self) -> None:
        """Background task that processes queued file changes with batching.

        Collects items within BATCH_WINDOW_SECONDS using asyncio.wait_for(),
        deduplicates by key, and processes in batches up to MAX_BATCH_SIZE.
        """
        pending: dict[str, dict] = {}

        while True:
            try:
                # Wait for first item to start a new batch
                item = await self.work_queue.get()
                self.work_queue.task_done()
                pending[self._make_dedup_key(item)] = item

                # Collect more items within the batch window
                deadline = time.monotonic() + self.BATCH_WINDOW_SECONDS
                while len(pending) < self.MAX_BATCH_SIZE:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break

                    try:
                        item = await asyncio.wait_for(
                            self.work_queue.get(),
                            timeout=remaining
                        )
                        self.work_queue.task_done()
                        pending[self._make_dedup_key(item)] = item
                    except asyncio.TimeoutError:
                        # Batch window expired, process what we have
                        break

                # Process the collected batch
                await self._process_batch(list(pending.values()))
                pending.clear()

            except asyncio.CancelledError:
                # Task cancelled during shutdown
                break
            except Exception as e:
                print(f"[disk-sync] Processor error: {e}")
                # Clear pending batch on error to avoid getting stuck
                pending.clear()

    def start(self) -> None:
        """Start watching the sync directory and optional workspace."""
        # Start background processor task
        if self._processor_task is None or self._processor_task.done():
            self._processor_task = asyncio.create_task(self._process_work_queue())

        # Create new observer if previous was stopped (observers cannot be restarted)
        if not self.observer.is_alive():
            self.observer = Observer()

        # Start file system observer for sync directory
        self.observer.schedule(self.handler, str(self.sync_root), recursive=True)

        # Also watch workspace if provided
        if self.workspace_root and self.workspace_root.exists():
            self.observer.schedule(self.handler, str(self.workspace_root), recursive=True)
            print(f"[disk-sync] Watching workspace: {self.workspace_root}")

        self.observer.start()

    async def stop(self) -> None:
        """Stop watching the sync directory and wait for processor to finish."""
        # Stop file system observer
        self.observer.stop()
        self.observer.join()

        # Cancel background processor task and wait for it
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                # Expected when cancelling
                pass

    @property
    def is_running(self) -> bool:
        """Check if watcher is currently running.

        Returns:
            True if observer is alive, False otherwise
        """
        return self.observer.is_alive()
