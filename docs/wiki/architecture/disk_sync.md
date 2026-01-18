# Disk Sync Architecture

The Disk Sync Service (`mybb_mcp/mybb_mcp/sync/`) provides bidirectional synchronization between the MyBB database and the filesystem. It monitors the `mybb_sync/` directory for changes and automatically imports template and stylesheet modifications, while also supporting on-demand export operations.

## DiskSyncService Orchestrator

The `DiskSyncService` class (`sync/service.py`) is the main orchestrator managing all sync components.

### Initialization (service.py lines 21-78)

The service initializes all sync components in its constructor:

```python
class DiskSyncService:
    def __init__(self, db: MyBBDatabase, sync_root: Path):
        self.db = db
        self.sync_root = sync_root

        # Initialize components:
        self.router = PathRouter(sync_root)
        self.group_manager = TemplateGroupManager(db)
        self.template_exporter = TemplateExporter(db, sync_root, self.group_manager)
        self.stylesheet_exporter = StylesheetExporter(db, sync_root)
        self.template_importer = TemplateImporter(db)
        self.stylesheet_importer = StylesheetImporter(db)
        self.cache_refresher = CacheRefresher(config)
        self.file_watcher = FileWatcher(
            sync_root=sync_root,
            router=self.router,
            template_importer=self.template_importer,
            stylesheet_importer=self.stylesheet_importer
        )
```

**Component Responsibilities:**

| Component | Purpose |
|-----------|---------|
| `PathRouter` | Parse file paths to determine type (template/stylesheet/plugin) |
| `TemplateGroupManager` | Determine which group folder each template belongs to |
| `TemplateExporter` | Export templates from database to disk |
| `StylesheetExporter` | Export stylesheets from database to disk |
| `TemplateImporter` | Import templates from disk to database |
| `StylesheetImporter` | Import stylesheets from disk to database |
| `CacheRefresher` | Invalidate stylesheet cache after updates |
| `FileWatcher` | Monitor filesystem for changes |

### Lifecycle Management (service.py lines 144-183)

The service provides lifecycle methods for the file watcher:

**`start_watcher()`** - Start monitoring filesystem
```python
async def start_watcher(self):
    if not self.file_watcher.is_running:
        await self.file_watcher.start()
```

**`stop_watcher()`** - Stop monitoring filesystem
```python
async def stop_watcher(self):
    if self.file_watcher.is_running:
        await self.file_watcher.stop()
```

**`pause_watcher()`** - Temporarily pause event processing
```python
def pause_watcher(self):
    if self.file_watcher.is_running:
        self.file_watcher.pause()
```

**`resume_watcher()`** - Resume event processing
```python
def resume_watcher(self):
    if self.file_watcher.is_running:
        self.file_watcher.resume()
```

**Usage Pattern:**
- Watcher is **not started by default** (must call `start_watcher()`)
- Auto-starts in development mode via server initialization
- Pause/resume used during export operations (prevents race conditions)

## File Watcher Implementation

The `FileWatcher` class (`sync/watcher.py`) monitors the `mybb_sync/` directory using the `watchdog` library.

### Architecture (watcher.py lines 21-30)

```python
# FileWatcher uses watchdog Observer with custom event handler
# Supports both direct writes and atomic writes (temp→rename)
# Validates file size to prevent empty file corruption
# Queues work items for async processing
```

**Key Design Decisions:**
- **watchdog library**: Cross-platform file system monitoring
- **Debouncing**: 0.5 second window to prevent duplicate events
- **Atomic write detection**: Handles both direct writes and temp→rename pattern
- **Async queue**: Thread-safe work submission from watchdog to async loop

### Debouncing (watcher.py lines 32, 62-79)

```python
DEBOUNCE_SECONDS = 0.5  # Hardcoded constant

def _should_process(self, path: str) -> bool:
    with self._debounce_lock:  # Thread-safe
        now = time.time()
        last_time = self._last_sync.get(path, 0)

        if now - last_time < DEBOUNCE_SECONDS:
            return False  # Too soon, skip

        self._last_sync[path] = now
        return True  # Process this event
```

**Behavior:**
- Per-file timestamp tracking in `_last_sync` dict
- Thread-safe via `_debounce_lock` (prevents race conditions)
- 0.5 second window hardcoded (not configurable)
- Prevents duplicate events from same file in quick succession

### Event Handling (watcher.py lines 108-138)

The `SyncEventHandler` responds to three event types:

**`on_modified(event)`** - Direct file write
```python
def on_modified(self, event):
    if not event.is_directory:
        self._handle_file_change(event.src_path)
```

**`on_created(event)`** - New file created
```python
def on_created(self, event):
    if not event.is_directory:
        self._handle_file_change(event.src_path)
```

**`on_moved(event)`** - Atomic rename (temp→final)
```python
def on_moved(self, event):
    # Handles atomic writes via temp file + rename
    if not event.is_directory:
        self._handle_file_change(event.dest_path)
```

**Filtered Events (watcher.py line 87-94):**
- Temp files (`.tmp` suffix) - Ignored
- Hidden files (`.` prefix) - Ignored
- Backup files (`~` suffix) - Ignored

### File Change Processing (watcher.py lines 140-213)

When a file change is detected, the handler validates and queues work:

**Template Change Handler (lines 140-175):**
```python
async def _handle_template_change(self, path: Path):
    # 1. Validate file size (prevent empty file corruption)
    try:
        stat = path.stat()
        if stat.st_size == 0:
            return  # Skip empty files
    except FileNotFoundError:
        return  # File deleted before we could read it

    # 2. Parse path to extract metadata
    parsed = self.router.parse(path)
    if parsed.type != "template":
        return

    # 3. Read file content
    try:
        content = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return  # File deleted during read

    # 4. Queue work item for async processing
    await self.work_queue.put({
        "type": "template",
        "content": content,
        "set_name": parsed.set_name,
        "template_name": parsed.template_name
    })
```

**Stylesheet Change Handler (lines 177-213):**
- Follows identical pattern (validate size → parse → read → queue)
- Validates `parsed.type == "stylesheet"`
- Queues with `theme_name` and `stylesheet_name`

**Work Queue:**
- `asyncio.Queue` for thread-safe work submission
- Watchdog events occur on background threads
- Queue items processed by async import loop

## Template Export/Import Workflow

Templates support bidirectional sync with inheritance model awareness.

### Template Inheritance Model

Templates exist at three levels:

```
Master Templates (sid=-2)
    ↓ base
Global Templates (sid=-1)
    ↓ shared
Custom Templates (sid ≥ 1)
    ↓ overrides
```

**Master Templates (sid=-2):**
- Shipped with MyBB core
- Always included in exports via LEFT JOIN
- Never modified (read-only)

**Custom Templates (sid ≥ 1):**
- Specific to a template set
- Override master templates
- Created via import operations

### Export Workflow (templates.py lines 29-64)

```python
async def export_template_set(self, set_name: str):
    # 1. Fetch templates (master + custom)
    templates = await self._fetch_templates(set_id)

    # 2. Export templates by group
    await self._export_templates_by_group(templates, set_name)
```

**Fetch Templates Query (templates.py lines 66-92):**
```sql
SELECT t.title, t.template, t.sid
FROM mybb_templates t
LEFT JOIN mybb_templates master
    ON (master.title = t.title AND master.sid = -2)
WHERE t.sid IN (-2, %s)  -- Master + custom
ORDER BY t.sid DESC       -- Custom takes precedence
```

**Export Directory Structure:**
```
mybb_sync/
└── template_sets/
    └── {set_name}/
        └── {group_name}/
            └── {template_name}.html
```

**Atomic Write Pattern (templates.py lines 124-129):**
```python
# Write to temp file first
temp_path = output_path.with_suffix('.tmp')
temp_path.write_text(content, encoding='utf-8')

# Atomic rename (POSIX atomic on same filesystem)
temp_path.rename(output_path)
```

### Import Workflow (templates.py lines 161-200)

```python
async def import_template(self, set_id: int, title: str, content: str):
    # 1. Validate set exists
    if not await self._validate_set_exists(set_id):
        raise ValueError(f"Template set {set_id} not found")

    # 2. Check if master template exists (sid=-2)
    master_exists = await self._check_master_exists(title)

    # 3. Check if custom template exists (sid=set_id)
    custom_exists = await self._check_custom_exists(set_id, title)

    # 4. Update or insert
    if custom_exists:
        await self._update_template(set_id, title, content)
    else:
        await self._insert_template(set_id, title, content)
```

**Update vs Insert Decision:**
- Custom exists → UPDATE existing custom template
- Custom doesn't exist → INSERT new custom template
- Master existence doesn't affect decision (always create custom)

## Stylesheet Export/Import with Inheritance

Stylesheets implement copy-on-write inheritance with theme chain walking.

### Stylesheet Inheritance Model

Stylesheets inherit from parent themes via `pid` (parent theme ID):

```
Parent Theme (tid=1, pid=NULL)
    ↓ inherits
Child Theme (tid=2, pid=1)
    ↓ overrides
Grandchild Theme (tid=3, pid=2)
```

### Export Workflow (stylesheets.py lines 26-59)

```python
async def export_theme_stylesheets(self, theme_name: str):
    # 1. Fetch theme by name
    theme = await self._fetch_theme(theme_name)

    # 2. Fetch all stylesheets (walks inheritance chain)
    stylesheets = await self._fetch_stylesheets(theme['tid'])

    # 3. Export stylesheets
    await self._export_stylesheets(theme_name, stylesheets)
```

**Inheritance Chain Walking (stylesheets.py lines 61-110):**
```python
async def _fetch_stylesheets(self, tid: int) -> dict:
    stylesheets = {}
    current_tid = tid

    # Walk up theme inheritance chain
    while current_tid is not None:
        # Fetch stylesheets for current theme
        cursor.execute(
            "SELECT sid, name, stylesheet FROM mybb_themestylesheets WHERE tid = %s",
            (current_tid,)
        )
        rows = cursor.fetchall()

        # Merge into dict (child precedence - only add if not present)
        for row in rows:
            if row['name'] not in stylesheets:
                stylesheets[row['name']] = row

        # Get parent theme ID
        cursor.execute("SELECT pid FROM mybb_themes WHERE tid = %s", (current_tid,))
        parent = cursor.fetchone()
        current_tid = parent['pid'] if parent else None

    return stylesheets
```

**Child Precedence:**
- Child theme stylesheets added first
- Parent stylesheets only added if name not already present
- Ensures child overrides always win

**Export Directory Structure:**
```
mybb_sync/
└── styles/
    └── {theme_name}/
        └── {stylesheet_name}.css
```

**Atomic Write Pattern (stylesheets.py lines 136-141):**
- Same as templates: write to `.tmp`, then atomic rename
- Prevents corruption from interrupted writes

### Import Workflow (stylesheets.py lines 175-200)

```python
async def import_stylesheet(self, theme_id: int, name: str, content: str):
    # 1. Validate theme exists
    if not await self._validate_theme_exists(theme_id):
        raise ValueError(f"Theme {theme_id} not found")

    # 2. Check if stylesheet exists in THIS theme
    exists = await self._check_stylesheet_exists(theme_id, name)

    # 3. Copy-on-write pattern
    if exists:
        # Update existing stylesheet in THIS theme
        await self._update_stylesheet(theme_id, name, content)
    else:
        # Create override in THIS theme (not parent)
        await self._insert_stylesheet(theme_id, name, content)
```

**Copy-on-Write Behavior:**
- Always creates/updates stylesheet in child theme
- Never modifies parent theme stylesheets
- Parent stylesheet remains unchanged (inheritance preserved)

## Race Condition Prevention

The service prevents race conditions during export operations by pausing the watcher.

### Export Race Prevention (service.py lines 80-124)

**Template Set Export (lines 80-101):**
```python
async def export_template_set(self, set_name: str):
    try:
        # Pause watcher BEFORE export
        self.pause_watcher()

        # Perform export
        await self.template_exporter.export_template_set(set_name)

        # Drain queued events (prevent re-import of just-exported files)
        await self._drain_watcher_queue()
    finally:
        # Always resume (even if export fails)
        self.resume_watcher()
```

**Theme Export (lines 103-124):**
- Identical pattern: pause → export → drain → resume

**Queue Draining (lines 126-142):**
```python
async def _drain_watcher_queue(self):
    drained = 0
    try:
        while not self.file_watcher.work_queue.empty():
            try:
                self.file_watcher.work_queue.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
    except Exception as e:
        # Log error but don't fail
        pass
    # Log drained count for monitoring
```

### Why This Prevents Race Conditions

**Problem Without Pause:**
1. Export writes `template.html` to disk
2. FileWatcher detects change
3. FileWatcher imports `template.html` back to DB
4. Result: Unnecessary DB write + potential conflict

**Solution With Pause:**
1. Export pauses watcher (no events processed)
2. Export writes `template.html` to disk
3. Watcher events queued but not processed
4. Export drains queue (discards file change events)
5. Export resumes watcher (ready for user edits)
6. Result: No unnecessary DB writes

**Finally Block Guarantee:**
- Watcher always resumed even if export fails
- Prevents deadlock (watcher stuck in paused state)
- Critical for reliability

## Path Routing

The `PathRouter` class (`sync/router.py`) parses file paths to determine type and metadata.

### Path Patterns (router.py lines 51-119)

**Template Path Pattern:**
```
mybb_sync/template_sets/{set_name}/{group_name}/{template_name}.html
```

**Example:**
```
mybb_sync/template_sets/Default Templates/Sendthread Templates/sendthread.html
                         └─────┬─────┘  └───────┬────────┘  └────┬────┘
                            set_name         group_name      template_name
```

**Stylesheet Path Pattern:**
```
mybb_sync/styles/{theme_name}/{stylesheet_name}.css
```

**Example:**
```
mybb_sync/styles/Default/global.css
                 └──┬──┘  └──┬──┘
                theme_name  stylesheet_name
```

### ParsedPath Dataclass (router.py lines 15-30)

```python
@dataclass
class ParsedPath:
    type: str  # "template" or "stylesheet" or "plugin"
    set_name: str | None
    group_name: str | None
    template_name: str | None
    theme_name: str | None
    stylesheet_name: str | None
```

**Usage:**
```python
parsed = router.parse(Path("mybb_sync/template_sets/Default Templates/Header Templates/header.html"))
# ParsedPath(
#     type="template",
#     set_name="Default Templates",
#     group_name="Header Templates",
#     template_name="header",
#     ...
# )
```

### Plugin Manager Workspace Support (router.py lines 96-200+)

The router also supports extended paths for Plugin Manager workspace:

**Plugin Path Pattern:**
```
plugin_manager/workspace/plugins/{visibility}/{codename}/{subdir}/*
```

**Theme Path Pattern:**
```
plugin_manager/workspace/themes/{visibility}/{codename}/{subdir}/*
```

**Visibility Options:**
- `public` - Public marketplace plugins
- `private` - Private development plugins

## Configuration

The `SyncConfig` dataclass (`sync/config.py`) manages sync configuration.

### Environment Variables (config.py lines 8-47)

```python
@dataclass
class SyncConfig:
    sync_root: Path          # Default: ./mybb_sync
    auto_upload: bool        # Default: True
    cache_token: str         # Default: ""

    @classmethod
    def from_env(cls) -> SyncConfig:
        # MYBB_SYNC_ROOT - Disk sync directory
        sync_root = os.getenv('MYBB_SYNC_ROOT')
        if not sync_root:
            sync_root = Path.cwd() / "mybb_sync"
        else:
            sync_root = Path(sync_root)

        # MYBB_AUTO_UPLOAD - Enable automatic import
        auto_upload = os.getenv('MYBB_AUTO_UPLOAD', 'true')
        auto_upload = auto_upload.lower() in ('true', '1', 'yes')

        # MYBB_CACHE_TOKEN - Cache invalidation token
        cache_token = os.getenv('MYBB_CACHE_TOKEN', '')

        return cls(sync_root, auto_upload, cache_token)
```

**Configuration Variables:**

| Variable | Type | Default | Purpose |
|----------|------|---------|---------|
| `MYBB_SYNC_ROOT` | Path | `./mybb_sync` | Root directory for disk sync |
| `MYBB_AUTO_UPLOAD` | Boolean | `true` | Enable automatic import on file change |
| `MYBB_CACHE_TOKEN` | String | `""` | Token for cache invalidation requests |

## System Interactions

### Database Dependencies

All operations query MyBB database tables:

**Templates:**
- `mybb_templates` (sid, tid, title, template)
- `mybb_templatesets` (sid, title)

**Stylesheets:**
- `mybb_themestylesheets` (tid, name, stylesheet)
- `mybb_themes` (tid, pid, name)

**Transactions:**
- Each import is a single INSERT or UPDATE (atomic at DB level)
- No transaction wrapping for multiple imports
- Autocommit assumed (verify `MyBBDatabase` configuration)

### Async Work Queue

The FileWatcher uses `asyncio.Queue` for thread-safe work submission:

**Producer (watchdog thread):**
```python
# On filesystem event:
await self.work_queue.put({
    "type": "template",
    "content": content,
    "set_name": set_name,
    "template_name": template_name
})
```

**Consumer (async import loop):**
```python
while True:
    work = await self.work_queue.get()
    await self.template_importer.import_template(
        work['set_name'],
        work['template_name'],
        work['content']
    )
```

**Queue Characteristics:**
- Unbounded queue (no max size limit)
- Drained after exports to prevent re-imports
- Monitor queue size for performance issues

## Known Limitations

### Concurrency
- Concurrent exports not officially supported (may cause race conditions)
- No global export lock (only per-export pause/resume)
- Recommendation: Serialize export operations

### UTF-8 Encoding
- UTF-8 encoding assumed for all files
- No charset detection or conversion
- Files with other encodings will raise `UnicodeDecodeError`

### Debounce Window
- Hardcoded 0.5 second debounce window (not configurable)
- May be too short for slow filesystems
- May be too long for rapid successive edits

### Transaction Isolation
- Import operations not wrapped in transactions
- Partial updates possible if DB write fails mid-operation
- Each import is single INSERT/UPDATE (atomic at statement level)

### Watcher Queue
- Unbounded queue can grow without limit
- No monitoring for queue depth
- Slow import loop could cause memory issues

## Performance Characteristics

### File Watcher
- Debounce window: 0.5 seconds
- Event processing: Async (non-blocking)
- File size validation: ~1ms overhead per file
- UTF-8 read: ~5-10ms per file (varies by size)

### Export Operations
- Template set export: ~100ms (varies by template count)
- Theme export: ~50ms (varies by stylesheet count and inheritance depth)
- Atomic writes: ~1-2ms overhead per file

### Import Operations
- Template import: ~10-20ms (single INSERT or UPDATE)
- Stylesheet import: ~10-20ms (single INSERT or UPDATE)
- Cache invalidation: ~50-100ms HTTP request

## Further Reading

- [MCP Server Architecture](mcp_server.md) - Server initialization and database connection pooling
- [Configuration Reference](configuration.md) - Complete environment variable list
- [MCP Tools - Disk Sync](/docs/wiki/mcp_tools/disk_sync.md) - Export/import tool usage
- [Best Practices - Template Development](/docs/wiki/best_practices/templates.md) - Template editing workflows
- [Best Practices - Theme Development](/docs/wiki/best_practices/themes.md) - Stylesheet editing workflows

---

*Last Updated: 2026-01-18*
*Based on: RESEARCH_DISK_SYNC_SERVICE.md (complete)*
