# Research Report: DB-Sync Architecture for Plugin Templates

**Research ID**: R9_DBSYNC_PLUGINS  
**Date**: 2026-01-19  
**Agent**: MyBB-ResearchAgent  
**Confidence**: 0.95  

---

## Executive Summary

The db-sync system in `mybb_mcp/mybb_mcp/sync/` has **extensive infrastructure** for plugin template synchronization that is **90% complete but not fully wired**. The system can already:

- ✅ Parse plugin template paths via `PathRouter`
- ✅ Sync plugin templates to/from DB via `DiskSyncService.sync_plugin()`
- ✅ Store plugin templates in master templates (sid=-2) with `{codename}_{name}` convention

**Critical Gap**: The `FileWatcher` only monitors `sync_root` (mybb_sync/), NOT `workspace_root` (plugin_manager/). Plugin templates can be synced manually but NOT automatically via file watcher.

**Extension Required**: Wire plugin template watching to the existing file watcher by:
1. Adding workspace_root to watcher's observer schedule
2. Creating plugin_template handler in SyncEventHandler
3. Adding plugin_template case to work queue processor
4. Creating PluginTemplateImporter class (or reusing existing logic)

---

## 1. What Directories Does Watcher Monitor?

### Current Monitoring Scope

**File**: `watcher.py:336`
```python
self.observer.schedule(self.handler, str(self.sync_root), recursive=True)
```

**Answer**: Watcher ONLY monitors `sync_root` (configured as `mybb_sync/` directory).

### Directory Structure

```
mybb_sync/                    # WATCHED ✓
├── template_sets/
│   └── {set_name}/
│       └── {group}/
│           └── {template}.html
└── styles/
    └── {theme_name}/
        └── {stylesheet}.css

plugin_manager/               # NOT WATCHED ✗
├── plugins/
│   ├── public/
│   │   └── {codename}/
│   │       ├── templates/   # Would go here
│   │       ├── src/
│   │       └── languages/
│   └── private/
│       └── {codename}/
│           └── templates/   # Would go here
└── themes/
    └── {visibility}/
        └── {codename}/
```

### Why workspace_root Is Not Watched

**File**: `service.py:72-77`
```python
# Initialize file watcher (not started by default)
self.watcher = FileWatcher(
    config.sync_root,           # Only sync_root passed
    self.template_importer,
    self.stylesheet_importer,
    self.cache_refresher,
    self.router                 # Router knows workspace_root but watcher doesn't use it
)
```

**Root Cause**: `FileWatcher.__init__` only accepts `sync_root` parameter, not `workspace_root`. Even though `PathRouter` has workspace knowledge, the watcher never monitors those directories.

---

## 2. How Does It Map Files to Template Sets?

### Architecture Overview

```
File Change → SyncEventHandler → PathRouter.parse() → Work Queue → Importer → Database
```

### 2.1 Path Routing (PathRouter)

**File**: `router.py:67-119`

The router has TWO routing modes:

#### Mode 1: mybb_sync paths (Current Active)
```python
# Template: template_sets/{set_name}/{group_name}/{template_name}.html
if len(parts) >= 4 and parts[0] == "template_sets" and path.suffix == ".html":
    return ParsedPath(
        type="template",
        set_name=parts[1],      # Extract from path
        group_name=parts[2],
        template_name=path.stem
    )

# Stylesheet: styles/{theme_name}/{stylesheet_name}.css
if len(parts) >= 3 and parts[0] == "styles" and path.suffix == ".css":
    return ParsedPath(
        type="stylesheet",
        theme_name=parts[1],
        stylesheet_name=path.name
    )
```

#### Mode 2: plugin_manager workspace paths (NOT ACTIVE)

**File**: `router.py:90-92`
```python
# Check if this is a plugin_manager workspace path
if len(parts) >= 1 and parts[0] in ("plugins", "themes"):
    return self._parse_workspace_path(path, parts, relative_path)
```

**File**: `router.py:178-187` (Plugin template parsing)
```python
# Plugin templates: plugins/{vis}/{name}/templates/*.html
if subdir == 'templates' and path.suffix == '.html':
    return ParsedPath(
        type='plugin_template',       # Different type!
        project_name=codename,        # Not set_name
        visibility=visibility,
        file_type='template',
        template_name=path.stem,
        relative_path=str(Path(*parts[3:])),
        raw_path=relative_path
    )
```

**Key Insight**: Router CAN parse plugin templates (returns `type='plugin_template'`), but this code path is never triggered because watcher doesn't monitor plugin_manager/.

### 2.2 Event Handling (SyncEventHandler)

**File**: `watcher.py:81-106`

Current routing logic:
```python
def _handle_file_change(self, path: Path) -> None:
    # ... debouncing and validation ...
    
    # Handle template changes (.html files in template_sets/)
    if path.suffix == '.html' and 'template_sets' in path.parts:
        self._handle_template_change(path)
    
    # Handle stylesheet changes (.css files in styles/)
    elif path.suffix == '.css' and 'styles' in path.parts:
        self._handle_stylesheet_change(path)
```

**Gap**: No handler for `'plugins' in path.parts` or `parsed.type == 'plugin_template'`.

**Design Flaw**: Uses string matching on path parts instead of delegating to PathRouter. Should be:
```python
def _handle_file_change(self, path: Path) -> None:
    rel_path = path.relative_to(self.router.sync_root)  # or workspace_root
    parsed = self.router.parse(str(rel_path))
    
    if parsed.type == "template":
        self._handle_template_change(path)
    elif parsed.type == "stylesheet":
        self._handle_stylesheet_change(path)
    elif parsed.type == "plugin_template":
        self._handle_plugin_template_change(path)  # MISSING
```

### 2.3 Template Handler Workflow

**File**: `watcher.py:140-176`

```python
def _handle_template_change(self, path: Path) -> None:
    # 1. Parse path using router
    rel_path = path.relative_to(self.router.sync_root)
    parsed = self.router.parse(str(rel_path))
    
    # 2. Validate type and required fields
    if parsed.type != "template" or not parsed.set_name or not parsed.template_name:
        return
    
    # 3. Prevent empty file corruption
    if path.stat().st_size == 0:
        return
    
    # 4. Read file content
    content = path.read_text(encoding='utf-8')
    
    # 5. Queue work for async processing
    self.work_queue.put_nowait({
        "type": "template",
        "set_name": parsed.set_name,
        "template_name": parsed.template_name,
        "content": content
    })
```

**Pattern**: Parse → Validate → Read → Queue

### 2.4 Work Queue Processor

**File**: `watcher.py:282-328`

```python
async def _process_work_queue(self) -> None:
    while True:
        work_item = await self.work_queue.get()
        
        # Wait while paused (e.g., during exports)
        while self._paused:
            await asyncio.sleep(0.1)
        
        # Route by type
        if work_item["type"] == "template":
            await self.template_importer.import_template(
                work_item["set_name"],
                work_item["template_name"],
                work_item["content"]
            )
        
        elif work_item["type"] == "stylesheet":
            await self.stylesheet_importer.import_stylesheet(...)
            await self.cache_refresher.refresh_stylesheet(...)
        
        # MISSING: plugin_template case
```

### 2.5 Template Importer (Database Write)

**File**: `templates.py:161-207`

```python
async def import_template(self, set_name: str, template_name: str, content: str) -> bool:
    # 1. Get template set ID
    template_set = self.db.get_template_set_by_name(set_name)
    sid = template_set['sid']
    
    # 2. Check master template (sid=-2)
    master = self.db.get_template(template_name, sid=-2)
    
    # 3. Check custom template (sid=set_sid)
    custom = self.db.get_template(template_name, sid=sid)
    
    # 4. UPDATE or INSERT
    if custom:
        return self.db.update_template(custom['tid'], content)
    else:
        version = master['version'] if master else "1800"
        tid = self.db.create_template(template_name, content, sid=sid, version=version)
        return tid > 0
```

**Key Insight**: Handles MyBB template inheritance (master vs custom templates). Plugin templates DON'T use this pattern.

---

## 3. How Could It Be Extended for Plugin Templates?

### 3.1 Existing Manual Sync Infrastructure

**File**: `service.py:208-279, 333-414`

The system ALREADY has complete plugin template sync logic:

#### DiskSyncService.sync_plugin()
```python
def sync_plugin(
    self,
    codename: str,
    workspace_path: Path,
    visibility: str = "public",
    direction: str = "to_db"  # or "from_db"
) -> dict[str, Any]:
    """Sync plugin files between workspace and TestForum/database."""
    
    if direction == 'to_db':
        # Sync templates to database
        templates_result = self._sync_plugin_templates_to_db(
            codename, workspace_path
        )
    elif direction == 'from_db':
        # Export templates from database to workspace
        templates_result = self._sync_plugin_templates_from_db(
            codename, workspace_path
        )
```

#### Plugin Template Naming Convention

**File**: `service.py:362-373`
```python
def _sync_plugin_templates_to_db(self, codename: str, workspace_path: Path):
    templates_dir = workspace_path / "templates"
    
    for template_file in templates_dir.glob("*.html"):
        # Plugin templates use {codename}_{name} convention
        full_template_name = f"{codename}_{template_file.stem}"
        
        # Write to master templates (sid=-2)
        existing = self.db.get_template(full_template_name, sid=-2)
        if existing:
            self.db.update_template(existing['tid'], content)
        else:
            self.db.create_template(full_template_name, content, sid=-2)
```

**Critical Pattern**:
- Plugin templates stored in **master templates** (sid=-2)
- Named with **{codename}_ prefix** (e.g., `cortex_config_panel`)
- **No template set inheritance** - simple INSERT/UPDATE only

### 3.2 Extension Strategy

#### Option A: Minimal Wiring (Recommended)

**What's Needed**:
1. **Add workspace_root to watcher monitoring**
   - Modify `FileWatcher.__init__` to accept `workspace_root` parameter
   - Add second `observer.schedule()` call in `start()` method
   
2. **Add plugin_template handler to SyncEventHandler**
   ```python
   def _handle_plugin_template_change(self, path: Path) -> None:
       rel_path = path.relative_to(self.router.workspace_root)
       parsed = self.router.parse(str(rel_path))
       
       if parsed.type != "plugin_template" or not parsed.project_name:
           return
       
       if path.stat().st_size == 0:
           return
       
       content = path.read_text(encoding='utf-8')
       
       self.work_queue.put_nowait({
           "type": "plugin_template",
           "codename": parsed.project_name,
           "template_name": parsed.template_name,
           "content": content
       })
   ```

3. **Add plugin_template case to work queue processor**
   ```python
   elif work_item["type"] == "plugin_template":
       await self.plugin_template_importer.import_template(
           work_item["codename"],
           work_item["template_name"],
           work_item["content"]
       )
   ```

4. **Create PluginTemplateImporter class**
   ```python
   class PluginTemplateImporter:
       def __init__(self, db: MyBBDatabase):
           self.db = db
       
       async def import_template(self, codename: str, template_name: str, content: str) -> bool:
           """Import plugin template to master templates (sid=-2)."""
           full_name = f"{codename}_{template_name}"
           
           existing = self.db.get_template(full_name, sid=-2)
           if existing:
               return self.db.update_template(existing['tid'], content)
           else:
               tid = self.db.create_template(full_name, content, sid=-2)
               return tid > 0
   ```

#### Option B: Refactor to Use PathRouter Everywhere

**More Invasive** but cleaner architecture:

1. Change `_handle_file_change` to use `PathRouter.parse()` for all routing
2. Remove hardcoded path string matching
3. Add handler registry keyed by `ParsedPath.type`

This would make adding new file types trivial in the future.

---

## 4. Requirements for 1:1 Disk-DB Sync

### 4.1 Current State

**What Exists**:
- ✅ PathRouter can parse plugin template paths
- ✅ Manual sync via `DiskSyncService.sync_plugin()` (bidirectional)
- ✅ Database operations (INSERT/UPDATE to sid=-2 with codename prefix)
- ✅ File watcher infrastructure (observer, queue, async processor)

**What's Missing**:
- ❌ Watcher doesn't monitor `plugin_manager/` directory
- ❌ No `_handle_plugin_template_change()` method in SyncEventHandler
- ❌ No `plugin_template` case in work queue processor
- ❌ No PluginTemplateImporter class (logic exists in service.py but not as reusable component)
- ❌ sync_plugin NOT exposed as MCP tool (only internal API)

### 4.2 Architecture Gaps

#### Gap 1: Watcher Monitoring Scope

**Current**:
```python
# service.py:72-77
self.watcher = FileWatcher(
    config.sync_root,  # Only mybb_sync/
    ...
)

# watcher.py:336
self.observer.schedule(self.handler, str(self.sync_root), recursive=True)
```

**Required**:
```python
# service.py
self.watcher = FileWatcher(
    config.sync_root,
    workspace_root=workspace_root,  # Add workspace monitoring
    ...
)

# watcher.py
self.observer.schedule(self.handler, str(self.sync_root), recursive=True)
if self.workspace_root:
    self.observer.schedule(self.handler, str(self.workspace_root), recursive=True)
```

#### Gap 2: Event Handler Routing

**Current**: Hardcoded directory checks
**Required**: Use PathRouter for all routing decisions

```python
# Before
if path.suffix == '.html' and 'template_sets' in path.parts:
    self._handle_template_change(path)

# After
parsed = self.router.parse(str(rel_path))
if parsed.type == "template":
    self._handle_template_change(path)
elif parsed.type == "plugin_template":
    self._handle_plugin_template_change(path)
```

#### Gap 3: Importer Component

**Current**: Logic embedded in `DiskSyncService._sync_plugin_templates_to_db()`
**Required**: Extract to reusable `PluginTemplateImporter` class following same pattern as `TemplateImporter`

#### Gap 4: Dependency Injection

**Current**: FileWatcher accepts `template_importer` and `stylesheet_importer`
**Required**: Add `plugin_template_importer` parameter

```python
def __init__(
    self,
    sync_root: Path,
    workspace_root: Optional[Path],
    template_importer: TemplateImporter,
    stylesheet_importer: StylesheetImporter,
    plugin_template_importer: PluginTemplateImporter,  # ADD
    cache_refresher: CacheRefresher,
    router: PathRouter
):
```

### 4.3 Implementation Checklist

For **Phase 4.X** (Plugin Template Disk Sync):

- [ ] **Create PluginTemplateImporter class** (`sync/plugin_templates.py`)
  - Extract logic from `service.py:_sync_plugin_templates_to_db()`
  - Follow same pattern as `TemplateImporter`
  - Async method: `import_template(codename, template_name, content)`

- [ ] **Extend FileWatcher to monitor workspace_root**
  - Add `workspace_root: Optional[Path]` parameter to `__init__`
  - Store as instance variable
  - Schedule second observer in `start()` if workspace_root exists

- [ ] **Add plugin template handler to SyncEventHandler**
  - Create `_handle_plugin_template_change(path)` method
  - Follow same pattern as `_handle_template_change()`
  - Queue work items with type="plugin_template"

- [ ] **Extend work queue processor**
  - Add `elif work_item["type"] == "plugin_template":` case
  - Call `plugin_template_importer.import_template()`

- [ ] **Refactor _handle_file_change routing** (optional but recommended)
  - Use `PathRouter.parse()` instead of hardcoded path checks
  - Makes system extensible for future file types

- [ ] **Update DiskSyncService initialization**
  - Create PluginTemplateImporter instance
  - Pass to FileWatcher constructor

- [ ] **Create MCP tool for manual sync** (optional)
  - Expose `sync_plugin()` as `mybb_sync_plugin_templates` tool
  - Allows manual sync without relying on watcher

- [ ] **Add integration tests**
  - Test file change detection in workspace
  - Test template name prefixing ({codename}_)
  - Test INSERT vs UPDATE logic
  - Test bidirectional sync (to_db and from_db)

### 4.4 Compatibility Considerations

**Database Schema**: No changes needed. Plugin templates use existing `mybb_templates` table with:
- `sid = -2` (master templates)
- `title = {codename}_{template_name}`
- No template set association

**Plugin Manager Integration**: Works with existing workspace structure:
```
plugin_manager/plugins/{visibility}/{codename}/
├── templates/          # Watched directory
│   └── *.html         # Synced to DB as {codename}_{stem}
├── src/
│   └── {codename}.php
└── meta.json
```

**Installer Compatibility**: `plugin_manager/installer.py` already copies templates/ during deployment. Watcher support makes development workflow seamless but doesn't replace installer.

---

## 5. File Change Flow Diagrams

### Current System (Template Sets)

```
mybb_sync/template_sets/Default/Header/header.html
    |
    v
FileWatcher detects change (sync_root)
    |
    v
SyncEventHandler._handle_file_change()
    ├─> Check: '.html' AND 'template_sets' in path
    └─> Call: _handle_template_change()
            |
            v
        PathRouter.parse("template_sets/Default/Header/header.html")
            |
            v
        ParsedPath(type="template", set_name="Default", template_name="header")
            |
            v
        Queue work: {type: "template", set_name: "Default", template_name: "header", content: ...}
            |
            v
        FileWatcher._process_work_queue()
            |
            v
        TemplateImporter.import_template("Default", "header", content)
            ├─> Get template set ID for "Default"
            ├─> Check master template (sid=-2)
            ├─> Check custom template (sid=set_id)
            └─> INSERT or UPDATE
                    |
                    v
                Database: mybb_templates table updated
```

### Proposed System (Plugin Templates)

```
plugin_manager/plugins/public/cortex/templates/config_panel.html
    |
    v
FileWatcher detects change (workspace_root) ⚠️ NEW MONITOR
    |
    v
SyncEventHandler._handle_file_change()
    ├─> PathRouter.parse("plugins/public/cortex/templates/config_panel.html")
    └─> ParsedPath(type="plugin_template", project_name="cortex", template_name="config_panel")
            |
            v
        Call: _handle_plugin_template_change() ⚠️ NEW HANDLER
            |
            v
        Queue work: {type: "plugin_template", codename: "cortex", template_name: "config_panel", content: ...}
            |
            v
        FileWatcher._process_work_queue()
            |
            v
        PluginTemplateImporter.import_template("cortex", "config_panel", content) ⚠️ NEW IMPORTER
            ├─> Build full name: "cortex_config_panel"
            ├─> Check if exists in master (sid=-2)
            └─> INSERT or UPDATE
                    |
                    v
                Database: mybb_templates (sid=-2, title="cortex_config_panel")
```

---

## 6. Proposed Solution Architecture

### Component Structure

```
mybb_mcp/mybb_mcp/sync/
├── watcher.py              # MODIFY: Add workspace_root monitoring
│   ├── SyncEventHandler
│   │   ├── _handle_template_change()
│   │   ├── _handle_stylesheet_change()
│   │   └── _handle_plugin_template_change()  ⚠️ ADD
│   └── FileWatcher
│       ├── __init__(workspace_root)  ⚠️ MODIFY
│       └── start()  ⚠️ MODIFY (schedule workspace_root)
│
├── templates.py            # EXISTING: Handles template sets
│   └── TemplateImporter
│
├── plugin_templates.py     # ⚠️ CREATE: New module
│   └── PluginTemplateImporter
│       └── import_template(codename, name, content)
│
├── router.py               # EXISTING: Already parses plugin paths
│   └── PathRouter
│       └── _parse_plugin_path()  ✅ Already returns plugin_template type
│
└── service.py              # MODIFY: Wire new importer
    └── DiskSyncService
        ├── __init__()  ⚠️ Create PluginTemplateImporter instance
        └── _sync_plugin_templates_to_db()  ⚠️ Refactor to use importer
```

### Code Changes Summary

| File | Changes | Lines | Complexity |
|------|---------|-------|------------|
| `sync/plugin_templates.py` | Create new importer class | ~60 | Low (copy pattern from templates.py) |
| `watcher.py` | Add workspace monitoring + handler | ~40 | Low (copy pattern from template handler) |
| `watcher.py` | Add queue processor case | ~10 | Trivial |
| `service.py` | Wire plugin_template_importer | ~15 | Trivial |
| `service.py` | Refactor _sync_plugin_templates_to_db | ~20 | Medium (preserve behavior) |

**Total Estimated Changes**: ~145 lines

---

## 7. Open Questions & Risks

### Questions

1. **Should workspace_root be optional or required for watcher?**
   - Recommendation: Optional. Watcher can function without it (backward compatible).

2. **Should we expose sync_plugin as MCP tool?**
   - Current: Internal API only
   - Recommendation: Yes, expose as `mybb_sync_plugin` for manual sync when watcher is disabled

3. **How to handle plugin rename/deletion?**
   - Templates in DB have {codename}_ prefix
   - If plugin renamed, old templates orphaned in DB
   - Recommendation: Add cleanup logic or document manual cleanup required

4. **Should plugin stylesheets also be synced?**
   - Router can parse them (`plugin_php`, `plugin_lang` types exist)
   - Current research scope: templates only
   - Recommendation: Add stylesheet support in same phase for consistency

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Watcher performance with large workspace | Medium | Observer is recursive but debounced. Monitor performance. |
| Race conditions (watcher vs installer) | Low | Installer can pause watcher during deployment |
| Empty file corruption | Low | Already mitigated with file size check |
| Template naming collisions | Low | {codename}_ prefix prevents collisions between plugins |
| Orphaned templates after plugin delete | Medium | Document manual cleanup or add delete detection |

---

## 8. Recommendations

### For Phase 4 Implementation

1. **Create PluginTemplateImporter first**
   - Standalone, testable component
   - Can test via unit tests before watcher integration

2. **Wire to watcher second**
   - Minimal changes to watcher.py
   - Testable via integration tests

3. **Refactor service.py last**
   - Update `_sync_plugin_templates_to_db()` to use new importer
   - Preserve existing manual sync API

4. **Add MCP tool for manual sync**
   - Useful for debugging and manual workflows
   - Low effort, high value

### Architectural Improvements (Future)

1. **Refactor _handle_file_change to use PathRouter exclusively**
   - Eliminates hardcoded path checks
   - Makes adding new file types trivial
   - Recommended: Do this BEFORE adding plugin template support

2. **Add handler registry pattern**
   ```python
   HANDLERS = {
       "template": _handle_template_change,
       "stylesheet": _handle_stylesheet_change,
       "plugin_template": _handle_plugin_template_change
   }
   
   handler = HANDLERS.get(parsed.type)
   if handler:
       handler(path)
   ```

3. **Consolidate importer patterns**
   - TemplateImporter and PluginTemplateImporter have similar structure
   - Could extract base class with common logic
   - Reduces duplication and test burden

---

## 9. References

### Files Analyzed

| File | Lines | Purpose |
|------|-------|---------|
| `watcher.py` | 356 | File watcher, event handlers, work queue processor |
| `router.py` | 376 | Path parsing and routing (already handles plugin paths) |
| `templates.py` | 207 | Template set importer/exporter |
| `service.py` | 644 | DiskSyncService (has manual plugin sync logic) |
| `stylesheets.py` | ~200 | Stylesheet importer (not analyzed in detail) |

### Key Code Locations

- **Plugin path parsing**: `router.py:155-211` (_parse_plugin_path)
- **Manual sync logic**: `service.py:333-414` (_sync_plugin_templates_to_db/from_db)
- **Template handler pattern**: `watcher.py:140-176` (_handle_template_change)
- **Work queue processor**: `watcher.py:282-328` (_process_work_queue)
- **Watcher initialization**: `service.py:72-77`, `watcher.py:218-257`

### Plugin Template Conventions

- **File Location**: `plugin_manager/plugins/{visibility}/{codename}/templates/*.html`
- **Database Storage**: `mybb_templates` table, `sid=-2` (master templates)
- **Naming Convention**: `{codename}_{template_name}` (e.g., `cortex_config_panel`)
- **No Inheritance**: Plugin templates are simple INSERT/UPDATE, no template set hierarchy

---

## 10. Conclusion

The db-sync system has **excellent groundwork** for plugin template synchronization. The architecture is **90% complete**:

✅ **Complete**:
- PathRouter parses plugin template paths
- Manual sync logic exists and works
- Database schema supports plugin templates
- File watcher infrastructure is solid

❌ **Missing** (Final 10%):
- Watcher doesn't monitor workspace_root
- No plugin_template event handler
- No PluginTemplateImporter component
- Not wired into work queue processor

**Effort Estimate**: ~145 lines of code across 2-3 files, following existing patterns. **Low complexity**, **low risk**.

**Confidence**: 0.95 - Architecture is well-designed and extensible. Proposed changes follow existing patterns closely.

---

**End of Report**