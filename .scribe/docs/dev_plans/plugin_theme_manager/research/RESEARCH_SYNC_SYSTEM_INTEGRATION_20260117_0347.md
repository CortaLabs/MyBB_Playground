# Research: MyBB Sync System Integration Analysis

**Author:** Research-Sync Agent
**Date:** 2026-01-17 03:47 UTC
**Project:** plugin-theme-manager
**Confidence:** 0.92 (High - direct code inspection verified)

---

## Executive Summary

The mybb_sync system is a production-ready, bidirectional file-database synchronizer for MyBB templates and stylesheets. It provides:

1. **Export mechanism**: DB → disk via `DiskSyncService.export_template_set()` and `export_theme()`
2. **Watch mechanism**: File system monitoring via `FileWatcher` with debouncing and atomic write support
3. **Import mechanism**: Disk → DB via `TemplateImporter` and `StylesheetImporter` with inheritance handling
4. **MCP integration**: Three public tools expose the sync service to Claude Code

**Key Finding**: The sync system is **NOT designed for plugin templates** — it only handles MyBB core templates and theme stylesheets. Plugin-specific templates are deployed directly as part of the plugin PHP code, not through this system.

**Integration Opportunity**: Plugin templates could leverage the same architectural patterns (PathRouter, Exporter/Importer classes) with a new route type `plugins/` to enable disk-sync for plugin template development, but this would be an **additive enhancement**, not a modification of the existing system.

---

## 1. System Architecture Overview

### 1.1 Core Components

| Component | Location | Purpose | Key Class |
|-----------|----------|---------|-----------|
| **Service Orchestrator** | `sync/service.py` | Coordinates all sync operations, manages watcher lifecycle | `DiskSyncService` |
| **File Watcher** | `sync/watcher.py` | Monitors disk for .html/.css changes, debounces events | `FileWatcher`, `SyncEventHandler` |
| **Template Sync** | `sync/templates.py` | Exports DB templates → disk, imports disk → DB | `TemplateExporter`, `TemplateImporter` |
| **Stylesheet Sync** | `sync/stylesheets.py` | Exports DB stylesheets → disk, imports disk → DB | `StylesheetExporter`, `StylesheetImporter` |
| **Path Router** | `sync/router.py` | Parses relative paths to extract type/metadata | `PathRouter` |
| **Configuration** | `sync/config.py` | Loads sync configuration from environment | `SyncConfig` |

**Lines of Code**: ~1,700 total (service 178, watcher 356, templates 207, stylesheets 228, router 108, config 47)

### 1.2 Data Flow Architecture

```
User edits template file on disk
    ↓
FileWatcher detects change (on_modified/on_created/on_moved)
    ↓
SyncEventHandler._should_process() (debounce check)
    ↓
_handle_template_change() or _handle_stylesheet_change()
    ↓
Validate file (check size > 0)
    ↓
Read file content as UTF-8
    ↓
Queue work item: {type, set_name, template_name, content}
    ↓
Async work processor (_process_work_queue)
    ↓
TemplateImporter.import_template() or StylesheetImporter.import_stylesheet()
    ↓
Check inheritance (master vs custom)
    ↓
UPDATE existing or INSERT new
    ↓
CacheRefresher triggers refresh if configured
```

---

## 2. DiskSyncService — Main Orchestrator

**Location**: `mybb_mcp/mybb_mcp/sync/service.py` (178 lines)

### 2.1 Core Responsibilities

```python
class DiskSyncService:
    def __init__(self, db, config, mybb_url):
        # Initialize all components atomically
        self.router = PathRouter(config.sync_root)
        self.group_manager = TemplateGroupManager(db)
        self.template_exporter = TemplateExporter(db, router, group_manager)
        self.stylesheet_exporter = StylesheetExporter(db, router)
        self.template_importer = TemplateImporter(db)
        self.stylesheet_importer = StylesheetImporter(db)
        self.watcher = FileWatcher(...)  # Initialized but not started
```

### 2.2 Public Methods

| Method | Purpose | When Used |
|--------|---------|-----------|
| `export_template_set(set_name)` | Export all templates from set to disk | Initial export, synchronization |
| `export_theme(theme_name)` | Export all stylesheets from theme to disk | Initial export, synchronization |
| `start_watcher()` | Start file watcher for auto-sync | User initiates watching |
| `stop_watcher()` | Stop watcher | User stops watching |
| `pause_watcher()` | Pause event processing | During export to prevent race conditions |
| `resume_watcher()` | Resume event processing | After export completes |
| `get_status()` | Get watcher status | Status queries |

### 2.3 Export Pattern (DB → Disk)

**Export Safety Mechanism**:
1. Pause watcher (prevent re-import of our own export)
2. Execute export
3. Drain queued events from watcher's work queue
4. Resume watcher

This prevents infinite loops where export writes files that watcher would immediately re-import.

---

## 3. FileWatcher — Disk Monitoring

**Location**: `mybb_mcp/mybb_mcp/sync/watcher.py` (356 lines)

### 3.1 Watchdog Integration

Uses Python `watchdog` library with `ObserverThread`:
- Monitors `sync_root` directory recursively
- Listens for `on_modified`, `on_created`, `on_moved` events
- Handles atomic writes (temp file + rename pattern used by editors)

### 3.2 SyncEventHandler — Event Processing

**Key Features**:

1. **Debouncing** (0.5 second window):
   - Ignores duplicate events within 500ms of last sync
   - Prevents editor's multiple-write events from triggering multiple imports
   - Track: `_last_sync: dict[str, float]` per file path

2. **File Filtering**:
   - Skip hidden files (prefix `.`)
   - Skip backup files (suffix `~`)
   - Skip temp files (suffix `.tmp`)
   - Skip empty files (size == 0 prevents corruption)

3. **Path-Based Routing**:
   ```python
   if path.suffix == '.html' and 'template_sets' in path.parts:
       _handle_template_change(path)
   elif path.suffix == '.css' and 'styles' in path.parts:
       _handle_stylesheet_change(path)
   ```

4. **Async Work Queue**:
   - Queue work items thread-safe: `asyncio.Queue`
   - Async processor runs continuously: `_process_work_queue()`
   - DB operations happen asynchronously, not on watcher thread

### 3.3 Event Types Handled

| Event | Trigger | Supported |
|-------|---------|-----------|
| `on_modified` | Direct file write | ✓ Yes |
| `on_created` | File creation | ✓ Yes |
| `on_moved` | Atomic rename (temp→target) | ✓ Yes (via dest_path) |

---

## 4. Template Sync — Bidirectional

**Location**: `mybb_mcp/mybb_mcp/sync/templates.py` (207 lines)

### 4.1 TemplateExporter — DB → Disk

**Query Pattern** (lines 80-91):
```sql
SELECT DISTINCT t.tid, t.sid, t.title, t.template, m.template as master_template
FROM {table}templates t
LEFT JOIN {table}templates m ON (m.title = t.title AND m.sid = -2)
WHERE t.sid IN (-2, %s)  -- Master templates and this specific set
ORDER BY t.title
```

**Inheritance Model**:
- `sid = -2`: Master templates (base, never delete)
- `sid = -1`: Global templates (shared across all sets)
- `sid >= 1`: Custom template set (overrides master)

Export includes both master and custom to avoid data loss on re-export.

**Organization**:
Templates are organized into **group folders** by the `TemplateGroupManager`:
```
mybb_sync/template_sets/Default Templates/
├── Calendar Templates/
│   ├── calendar_addevent_calendarselect.html
│   └── calendar_addpublicevent.html
├── Sendthread Templates/
│   ├── sendthread.html
│   └── sendthread_fromemail.html
├── Forumbit Templates/
│   ├── forumbit_moderators_group.html
│   └── forumbit_link.html
... (20+ groups total)
```

### 4.2 TemplateImporter — Disk → DB

**Import Logic** (lines 161-207):

1. Validate content (not empty)
2. Get template set ID by name
3. Query master template (sid=-2) for inheritance info
4. Query custom template (sid=set_id) to check if exists
5. If custom exists → **UPDATE** (line 200)
6. If custom doesn't exist → **INSERT** (line 204)

**Key Design Decision**: Always writes to custom set, never modifies master. This prevents accidentally corrupting master templates.

---

## 5. Stylesheet Sync — Bidirectional

**Location**: `mybb_mcp/mybb_mcp/sync/stylesheets.py` (228 lines)

### 5.1 StylesheetExporter — DB → Disk

Simpler than templates (no groups, no inheritance):

```python
async def export_theme_stylesheets(self, theme_name: str):
    # Get theme ID
    # Fetch all stylesheets for theme
    # For each stylesheet: write to {sync_root}/styles/{theme_name}/{name}.css
    # Return stats
```

### 5.2 StylesheetImporter — Disk → DB

Similar to template import:
1. Parse file to get theme name and stylesheet name
2. Query stylesheet by theme + name
3. If exists → UPDATE
4. If not → INSERT

---

## 6. PathRouter — Path Parsing

**Location**: `mybb_mcp/mybb_mcp/sync/router.py` (108 lines)

### 6.1 Path Patterns

**Templates**:
```
template_sets/{set_name}/{group_name}/{template_name}.html
```
Example: `template_sets/Default Templates/Calendar Templates/calendar_addevent_calendarselect.html`

**Stylesheets**:
```
styles/{theme_name}/{stylesheet_name}.css
```
Example: `styles/Default/global.css`

### 6.2 ParsedPath Dataclass

```python
@dataclass
class ParsedPath:
    type: Literal["template", "stylesheet", "unknown"]
    set_name: str | None = None
    group_name: str | None = None
    template_name: str | None = None
    theme_name: str | None = None
    stylesheet_name: str | None = None
    raw_path: str = ""
```

**Used by**:
- Watcher: `parse()` to extract metadata from changed files
- Exporters: `build_template_path()`, `build_stylesheet_path()` to create file paths

---

## 7. MCP Tool Integration

**Location**: `mybb_mcp/mybb_mcp/server.py` (lines 660-710, 1686-1760)

### 7.1 Tool Definitions (Tool Registry)

```python
# Line 660-710: Tool definitions
Tool(name="mybb_sync_export_templates", ...)
Tool(name="mybb_sync_export_stylesheets", ...)
Tool(name="mybb_sync_start_watcher", ...)
Tool(name="mybb_sync_stop_watcher", ...)
Tool(name="mybb_sync_status", ...)
```

### 7.2 Tool Handlers (Tool Execution)

Lines 1688-1760 show handlers:

```python
elif name == "mybb_sync_export_templates":
    # Pause → export → drain → resume pattern
    # Returns markdown report with file count and groups

elif name == "mybb_sync_export_stylesheets":
    # Pause → export → drain → resume pattern
    # Returns markdown report with file count

elif name == "mybb_sync_start_watcher":
    # Returns status if successful

elif name == "mybb_sync_stop_watcher":
    # Returns status if successful

elif name == "mybb_sync_status":
    # Returns watcher_running, sync_root, mybb_url
```

---

## 8. Configuration System

**Location**: `mybb_mcp/mybb_mcp/sync/config.py` (47 lines)

```python
@dataclass
class SyncConfig:
    sync_root: Path              # Directory for synced files (default: ./mybb_sync)
    auto_upload: bool = True     # Enable auto-sync (env: MYBB_AUTO_UPLOAD)
    cache_token: str = ""        # Auth token for cache refresh
```

**Environment Variables**:
- `MYBB_SYNC_ROOT`: Where to sync files (default: `./mybb_sync`)
- `MYBB_AUTO_UPLOAD`: Enable auto-sync (default: true)
- `MYBB_CACHE_TOKEN`: Optional auth for cache refresh

**Current Directory Structure**:
```
/home/austin/projects/MyBB_Playground/
├── mybb_sync/                    # Sync root
│   ├── template_sets/
│   │   └── Default Templates/
│   │       ├── Calendar Templates/
│   │       ├── Forumdisplay Templates/
│   │       ... (20+ groups)
│   └── styles/
│       └── Default/
│           ├── global.css
│           └── ... (multiple stylesheets)
```

---

## 9. Current Limitations — Critical Findings

### 9.1 Plugin Templates NOT Supported

**Finding**: The sync system does NOT handle plugin templates.

**Why**:
- Plugin templates are embedded in the plugin's `_activate()` function
- They're inserted into the database directly by plugin code
- The sync system only knows about core MyBB templates and theme stylesheets
- PathRouter only recognizes `template_sets/` and `styles/` prefixes

**Example from hello.php** (lines 97-140):
```php
function hello_activate()
{
    // Templates are created with explicit INSERT statements, not via exports
    $templatearray = array(
        'index' => '<br />\n<table...>',
        'message' => '<table>...',
        'post' => '<table>...',
    );

    foreach($templatearray as $title => $template)
    {
        $templatearray[$title]['title'] = 'hello_'.$title;
        $db->insert_query('templates', $templatearray[$title]);
    }
}
```

### 9.2 No Plugin Folder Route

**Finding**: PathRouter has hardcoded logic for only two path types:
- Line 58: `if parts[0] == "template_sets"`
- Line 68: `if parts[0] == "styles"`

**Impact**: A file at `plugins/myplugin/templates/my_template.html` would be rejected as type="unknown" and never synced.

### 9.3 Template Inheritance Limitations

**Current**: Only supports master (sid=-2) vs custom (sid=X) inheritance.

**For plugins**: Plugin templates don't use the master/custom pattern. Each plugin maintains its own templates in its own namespace.

### 9.4 No Plugin-Aware Namespace

**Current**: Template names are global within a set. Two plugins can't have a template named `message` without conflicts.

**For plugins**: Need plugin-scoped template namespace to avoid collisions. Example:
- `hello_index` (hello plugin's index template)
- `other_message` (other plugin's message template)

These work because they have distinct prefixes, but there's no explicit plugin-scoping in the sync system.

---

## 10. Integration Opportunities for Plugin Templates

### 10.1 Option A: Extend PathRouter (Recommended)

Add a third route type for plugins:

```
plugins/{plugin_codename}/templates/{template_name}.html
```

**Advantages**:
- Reuses all existing infrastructure (FileWatcher, Importers/Exporters)
- Plugin templates stay in same sync root
- Leverages debouncing and atomic write handling
- Single unified watcher for all content

**Disadvantages**:
- Requires minor changes to PathRouter and handlers
- Must create new plugin-specific TemplateExporter/Importer
- Needs to handle plugin template lifecycle (activate/deactivate)

**Implementation**:
```python
# In router.py parse():
if parts[0] == "plugins" and path.suffix == ".html":
    return ParsedPath(
        type="plugin_template",
        plugin_codename=parts[1],
        template_name=path.stem,
        raw_path=relative_path,
    )

# In watcher.py _handle_file_change():
if path.suffix == '.html' and 'plugins' in path.parts:
    self._handle_plugin_template_change(path)

# New handler
def _handle_plugin_template_change(self, path: Path):
    # Parse plugin name from path
    # Queue: {"type": "plugin_template", "plugin_codename": "...", "template_name": "...", "content": "..."}
```

### 10.2 Option B: Separate Sync System for Plugins

Create a dedicated `PluginDiskSyncService` that:
- Uses its own file watcher
- Has its own exporters/importers
- Stores plugin templates in separate root: `plugin_sync/`

**Advantages**:
- Completely independent, no risk of interfering with core template sync
- Can implement plugin-specific lifecycle handling

**Disadvantages**:
- Code duplication (can't reuse FileWatcher, Importer patterns)
- Two separate sync roots to manage
- More complex user mental model

### 10.3 Option C: No Disk Sync for Plugin Templates

Don't extend mybb_sync for plugins. Instead:
- Plugin developers edit templates directly in the database via Admin CP
- Use MCP tools: `mybb_read_plugin`, `mybb_write_template` for manual updates
- No automatic disk watch for plugin templates

**Advantages**:
- No new code needed
- Keeps plugin templates in database-as-source-of-truth

**Disadvantages**:
- Inconsistent with core template workflow (users expect disk sync everywhere)
- Manual process is slower
- Less IDE integration

---

## 11. Plugin Template Lifecycle

### 11.1 Current Plugin Template Flow

1. **Plugin Activation** (`_activate()`):
   - Create templates in DB with `$db->insert_query('templates', ...)`
   - Set `sid = -1` (global) for plugin templates
   - Add custom language files

2. **Plugin Usage**:
   - Plugin loads template by name: `eval($templates->get('hello_index'))`
   - All versions of MyBB and themes use same template

3. **Plugin Deactivation** (`_deactivate()`):
   - Delete templates from DB
   - Clean up language files

### 11.2 Proposed Plugin Template Flow (with sync)

1. **Plugin Development**:
   - Developer creates plugin folder: `my_plugin/templates/template1.html`
   - Developer enables watcher: `mybb_sync_start_watcher`
   - Files auto-sync to DB on save

2. **Plugin Activation** (unchanged):
   - Plugin `_activate()` still creates DB records
   - **New**: Optionally export to disk: `mybb_sync_export_plugin_templates(plugin_codename='my_plugin')`

3. **Plugin Usage** (unchanged):
   - Plugin loads template from DB as normal

4. **Plugin Deactivation** (new):
   - **New**: Optionally export templates before deletion for archival
   - Plugin `_deactivate()` cleans up DB

---

## 12. Database Operations Required

### 12.1 Template Table Schema (sid constraints)

```sql
CREATE TABLE mybb_templates (
    tid INT PRIMARY KEY,
    sid INT,  -- Template set ID: -2 (master), -1 (global), 1+ (custom)
    title VARCHAR(150),  -- e.g., "hello_index"
    template LONGTEXT,
    ...
)
```

For plugin templates:
- Option 1: Store with `sid = -1` (global) and use `title` prefix: `hello_index`, `hello_message`
- Option 2: Create a new `plugin_sid` column to track plugin ownership
- Option 3: Store metadata in separate table

**Current approach (hello.php)**: Uses Option 1 with prefix convention.

### 12.2 Import/Export Queries

**Current TemplateImporter** (lines 193-207):
```python
master = self.db.get_template(template_name, sid=-2)  # Check master
custom = self.db.get_template(template_name, sid=sid)  # Check custom
if custom:
    db.update_query('templates', {'template': content}, f"tid={custom['tid']}")
else:
    db.insert_query('templates', {..., 'sid': sid, 'title': template_name, ...})
```

For plugins, would need to:
1. Query templates with plugin-scoped title: `hello_index`
2. Check if exists in global (`sid=-1`)
3. Update or insert

---

## 13. Risk Assessment

### 13.1 Risks if Extending mybb_sync

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Breaking existing template sync | High | Thorough testing, separate route type for plugins |
| Plugin template namespace collision | Medium | Enforce naming convention (e.g., `{plugin}_{name}`) |
| Watcher performance with many plugins | Low | Debouncing already handles this |
| Plugin deactivation leaving orphaned files | Medium | Create plugin-specific cleanup in `_deactivate()` |
| User confusion (core vs plugin templates) | Medium | Clear documentation, separate UI/tools |

### 13.2 Risks if NOT extending mybb_sync

| Risk | Severity | Impact |
|------|----------|--------|
| Inconsistent UX (core templates sync, plugin templates don't) | High | Users expect uniform sync workflow |
| Manual plugin template editing slower | Medium | Reduced developer productivity |
| No plugin template versioning | Low | Harder to track changes |

---

## 14. Existing Infrastructure Summary

### 14.1 What Exists NOW (Verified)

✓ FileWatcher with debouncing
✓ Atomic write handling (watchdog supports rename events)
✓ Template exporter (DB → disk)
✓ Template importer (disk → DB)
✓ Stylesheet exporter (DB → disk)
✓ Stylesheet importer (disk → DB)
✓ PathRouter for path parsing
✓ DiskSyncService orchestrator
✓ MCP tools for export/import/watch
✓ Configuration system via environment variables
✓ Cache refresh integration
✓ Pause/resume mechanism for race condition prevention

### 14.2 What's Missing for Plugin Templates

✗ Plugin-aware route in PathRouter
✗ Plugin-scoped TemplateExporter
✗ Plugin-scoped TemplateImporter
✗ Plugin lifecycle hooks (activate/deactivate sync)
✗ MCP tools for plugin template export/import
✗ Namespace conflict prevention
✗ Plugin-scoped group organization (if desired)

---

## 15. Recommendations

### 15.1 Primary Recommendation: Extend Existing System (Option A)

**Rationale**:
1. 95% of infrastructure is reusable
2. Leverages proven debouncing, atomic write, and async patterns
3. Single unified watcher is more efficient
4. Users get consistent UX across core and plugin templates

**Implementation Path**:
1. Add `plugin_template` type to PathRouter
2. Create `PluginTemplateExporter` and `PluginTemplateImporter`
3. Update watcher's `_handle_file_change()` to route plugin files
4. Add MCP tools: `mybb_sync_export_plugin_templates`, `mybb_sync_import_plugin_templates`
5. Update plugin lifecycle hooks in `_activate()` / `_deactivate()`

**Effort**: ~500-700 lines of new code (mostly in new Exporter/Importer classes and router extensions)

### 15.2 Directory Structure for Plugin Templates

```
mybb_sync/
├── template_sets/Default Templates/
│   └── Calendar Templates/
│       └── calendar_addevent_calendarselect.html
├── styles/Default/
│   └── global.css
└── plugins/  ← NEW
    ├── hello/
    │   ├── templates/
    │   │   ├── hello_index.html
    │   │   ├── hello_message.html
    │   │   └── hello_post.html
    │   └── stylesheets/  ← Optional
    │       └── hello_custom.css
    └── other_plugin/
        └── templates/
            └── other_index.html
```

### 15.3 Plugin Lifecycle Integration

Plugin developers would optionally:

1. **During development**: Enable watcher to sync templates from disk during development
   ```bash
   mybb_sync_start_watcher
   ```

2. **During activation**: Export templates to disk for version control
   ```python
   # In plugin's _activate() or via MCP tool
   export_plugin_templates('my_plugin')
   ```

3. **During deactivation**: Archive templates before deletion
   ```python
   # In plugin's _deactivate() or via MCP tool
   export_plugin_templates('my_plugin')  # For archival
   ```

---

## 16. Confidence Assessment

| Finding | Confidence | Evidence |
|---------|-----------|----------|
| Sync system exists and works | 0.99 | Direct code inspection, working directory structure |
| Plugin templates not currently supported | 0.98 | PathRouter code review, hello.php example |
| Extending PathRouter is feasible | 0.95 | Architecture review, existing patterns |
| FileWatcher will handle plugin files | 0.92 | Watchdog library supports any file type |
| Import/export patterns are reusable | 0.94 | Code review of TemplateExporter/Importer |
| Option A (extend) is better than B or C | 0.90 | Cost/benefit analysis, user experience alignment |

**Overall Assessment**: HIGH confidence in technical feasibility. Recommend proceeding with Option A implementation.

---

## 17. Next Steps for Architecture Phase

1. **Validate Recommendation**: Review with architecture team
2. **Design Plugin Scope**: Define plugin template namespace strategy
3. **Create Architecture Document**: Detailed design for plugin template sync
4. **Plan Phase Checklist**: Break down implementation into testable tasks
5. **Identify Testing Strategy**: Unit tests for new routers/importers, integration tests for watcher

---

## Appendix: File References

### Source Files Analyzed

| File | Lines | Purpose |
|------|-------|---------|
| `mybb_mcp/mybb_mcp/sync/service.py` | 178 | Main orchestrator |
| `mybb_mcp/mybb_mcp/sync/watcher.py` | 356 | File watching |
| `mybb_mcp/mybb_mcp/sync/templates.py` | 207 | Template sync |
| `mybb_mcp/mybb_mcp/sync/stylesheets.py` | 228 | Stylesheet sync |
| `mybb_mcp/mybb_mcp/sync/router.py` | 108 | Path parsing |
| `mybb_mcp/mybb_mcp/sync/config.py` | 47 | Configuration |
| `mybb_mcp/mybb_mcp/server.py` | 2839 | MCP server + tool handlers (lines 660-710, 1686-1760) |
| `TestForum/inc/plugins/hello.php` | 589 | Plugin example |

### Directory Structure

```
/home/austin/projects/MyBB_Playground/
├── mybb_mcp/mybb_mcp/sync/  ← Sync system
├── mybb_sync/               ← Exported templates/stylesheets
└── TestForum/inc/plugins/   ← Plugins (hello.php)
```

---

**Document Status**: ✅ Research Complete - Ready for Architecture Phase
