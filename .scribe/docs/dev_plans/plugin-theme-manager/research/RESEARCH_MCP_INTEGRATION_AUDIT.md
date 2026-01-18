# MCP Integration Audit: Plugin & Theme Manager Tools

**Date**: 2026-01-18 | **Status**: Complete | **Confidence**: 98%

## Executive Summary

The MyBB MCP server exposes 20 plugin and theme-related tools via `mybb_mcp/server.py`. These tools currently operate independently using direct file I/O and database access. The plugin_manager system (in `plugin_manager/manager.py`) provides a unified, structured API for plugin/theme creation, management, and export with workspace management, meta.json handling, and database integration.

**Key Finding**: Most MCP tools should be refactored to delegate to plugin_manager methods rather than duplicating functionality.

---

## Part 1: Current MCP Tools (20 Total)

### Plugin Creation & Analysis Tools (7 tools)

| Tool Name | Current Implementation | Location | Functionality |
|-----------|------------------------|----------|---|
| `mybb_create_plugin` | Direct PHP scaffolding, writes to `TestForum/inc/plugins/` | `tools/plugins.py:161-382` | Creates basic plugin PHP file with hooks/settings/templates |
| `mybb_list_plugins` | File glob on plugins directory | `server.py:1393-1400` | Lists .php files in plugins directory |
| `mybb_read_plugin` | Direct file read | `server.py:1402-1407` | Returns plugin PHP source code |
| `mybb_analyze_plugin` | Regex parsing of PHP file | `server.py:1430-1463` | Extracts hooks, functions, features via pattern matching |
| `mybb_list_hooks` | Hardcoded hooks reference dict | `tools/plugins.py:27-56` | Returns filtered list of available MyBB hooks |
| `mybb_hooks_discover` | Scans MyBB core files for `$plugins->run_hooks()` calls | `tools/hooks_expanded.py` | Dynamically discovers hooks in installation |
| `mybb_hooks_usage` | Scans plugin files for `$plugins->add_hook()` calls | `tools/hooks_expanded.py` | Finds which plugins use which hooks |

**Issues Identified**:
- `mybb_create_plugin` writes directly to filesystem, bypassing plugin_manager's workspace system
- No meta.json generation (plugin_manager creates comprehensive meta.json)
- No project registration in plugin_manager's database
- No hooks validation against plugin_manager's hook registry
- Limited structured output (returns markdown strings, not JSON metadata)

### Plugin Lifecycle Tools (4 tools)

| Tool Name | Current Implementation | Location | What It Does |
|-----------|------------------------|----------|---|
| `mybb_plugin_list_installed` | Reads `plugins` from MyBB datacache | `server.py:1467-1477` | Lists active plugins from DB cache |
| `mybb_plugin_info` | Parses `_info()` function from PHP | `server.py:1479-1509` | Extracts plugin metadata via regex |
| `mybb_plugin_activate` | Updates plugins cache in DB | `server.py:1511-1531` | Adds plugin codename to active list (cache only) |
| `mybb_plugin_deactivate` | Updates plugins cache in DB | `server.py:1533+` | Removes from active list (cache only) |

**Issues Identified**:
- Cache-only updates (doesn't trigger MyBB activation hooks)
- No integration with plugin_manager's install/uninstall workflows
- No history tracking or rollback capability
- Limited validation of plugin state

### Theme Tools (5 tools)

| Tool Name | Current Implementation | Location | What It Does |
|-----------|------------------------|----------|---|
| `mybb_list_themes` | Direct DB query for themes | `server.py:1351+` | Lists all themes from MyBB database |
| `mybb_list_stylesheets` | Direct DB query filtered by theme ID | `server.py:1360+` | Lists stylesheets, optionally for specific theme |
| `mybb_read_stylesheet` | Direct DB query by stylesheet ID | `server.py:~1368` | Returns CSS content of stylesheet |
| `mybb_write_stylesheet` | Direct DB update + cache clear | `server.py:~1380` | Updates CSS and refreshes theme cache |

**Issues Identified**:
- Direct DB manipulation without workspace integration
- No meta.json management for themes
- No version tracking or history
- Cannot export themes as packages

### Sync & Export Tools (4 tools)

| Tool Name | Current Implementation | Location | What It Does |
|-----------|------------------------|----------|---|
| `mybb_sync_export_templates` | Calls `DiskSyncService.export_template_set()` | `server.py:~1724` | Exports template set to disk files |
| `mybb_sync_export_stylesheets` | Calls `DiskSyncService.export_theme()` | `server.py:~1733` | Exports theme stylesheets to disk files |
| `mybb_sync_start_watcher` | Starts file watcher service | `server.py:~1743` | Begins watching template/stylesheet files |
| `mybb_sync_stop_watcher` | Stops file watcher service | `server.py:~1753` | Ends file watcher |
| `mybb_sync_status` | Gets watcher state and stats | `server.py:~1763` | Returns current sync service status |

**Good News**: These already use `DiskSyncService`, which can be extended to support plugin_manager workspaces.

---

## Part 2: Plugin Manager API (Target State)

### PluginManager Class (`plugin_manager/manager.py`)

**Core Methods** (signatures extracted):

```python
class PluginManager:
    def __init__(self, config: Optional[Config] = None)
    
    # Creation
    def create_plugin(
        codename: str, display_name: str, description: str = "",
        author: Optional[str] = None, version: str = "1.0.0",
        visibility: str = "public",
        hooks: Optional[List[Dict[str, str]]] = None,
        settings: Optional[List[Dict[str, Any]]] = None,
        has_templates: bool = False,
        has_database: bool = False,
        mybb_compatibility: str = "18*"
    ) -> Dict[str, Any]
    
    def create_theme(
        codename: str, display_name: str, description: str = "",
        author: Optional[str] = None, version: str = "1.0.0",
        visibility: str = "public",
        parent_theme: Optional[str] = None,
        color_scheme: Optional[Dict[str, str]] = None,
        stylesheets: Optional[List[str]] = None,
        template_overrides: Optional[List[str]] = None,
        mybb_compatibility: str = "18*"
    ) -> Dict[str, Any]
    
    # Installation
    def install_plugin(codename: str, visibility: Optional[str] = None) -> Dict[str, Any]
    def uninstall_plugin(codename: str, visibility: Optional[str] = None) -> Dict[str, Any]
    def install_theme(codename: str, visibility: Optional[str] = None) -> Dict[str, Any]
    def uninstall_theme(codename: str, visibility: Optional[str] = None) -> Dict[str, Any]
    
    # Export
    def export_plugin(
        codename: str,
        output_dir: Optional[Path] = None,
        visibility: Optional[str] = None,
        include_tests: bool = False
    ) -> Dict[str, Any]
    
    def export_theme(
        codename: str,
        output_dir: Optional[Path] = None,
        visibility: Optional[str] = None
    ) -> Dict[str, Any]
```

**What plugin_manager Provides**:
1. ✅ Workspace management (plugin_workspace, theme_workspace)
2. ✅ meta.json generation and persistence
3. ✅ PHP scaffolding with proper hook/setting/template support
4. ✅ Language file generation
5. ✅ README generation
6. ✅ Database registration via ProjectDatabase
7. ✅ ZIP export for distribution
8. ✅ Version tracking and history
9. ✅ Validation before operations
10. ✅ Proper error handling with rollback

---

## Part 3: Integration Matrix

### Tool-by-Tool Integration Plan

| MCP Tool | Current | Should Delegate To | Changes Required |
|----------|---------|-------------------|---|
| `mybb_create_plugin` | Writes to `TestForum/inc/plugins/` directly | `PluginManager.create_plugin()` | Parse args, extract hook list, pass to manager, return structured response |
| `mybb_list_plugins` | File glob | `PluginWorkspace.list_workspaces()` | Query plugin_manager DB instead |
| `mybb_read_plugin` | File read | `PluginWorkspace.get_workspace_path()` + file read | Navigate through workspace structure |
| `mybb_analyze_plugin` | Regex parsing | `PluginWorkspace.read_meta()` | Load meta.json, provide structured analysis |
| `mybb_plugin_activate` | Cache update only | `PluginManager.install_plugin()` | Call manager's install method |
| `mybb_plugin_deactivate` | Cache delete only | `PluginManager.uninstall_plugin()` | Call manager's uninstall method |
| `mybb_list_themes` | Direct DB query | `ThemeWorkspace.list_workspaces()` | Query plugin_manager DB |
| `mybb_list_stylesheets` | Direct DB query | `ThemeWorkspace.read_meta()` | Extract stylesheets from meta.json |
| `mybb_read_stylesheet` | Direct DB query | `ThemeWorkspace.read_stylesheet()` | Use workspace file API |
| `mybb_write_stylesheet` | Direct DB update | `ThemeWorkspace.write_stylesheet()` | Use workspace file API |
| `mybb_sync_export_templates` | Uses DiskSyncService (OK) | Enhance: integrate with plugin_manager | Extend to export plugin templates via plugin_manager |
| `mybb_sync_export_stylesheets` | Uses DiskSyncService (OK) | Keep, integrate with plugin_manager | Extend to export theme stylesheets via plugin_manager |
| `mybb_sync_start_watcher` | DiskSyncService.start_watcher() | Keep as-is, add plugin_manager plugin sync | Watch plugin workspace directories |
| `mybb_sync_stop_watcher` | DiskSyncService.stop_watcher() | Keep as-is | No changes needed |
| `mybb_sync_status` | DiskSyncService.get_status() | Enhance with plugin_manager state | Include plugin_manager workspace info |

### Hook Tools (No Integration Needed)

| Tool | Status | Reason |
|------|--------|--------|
| `mybb_list_hooks` | Keep | Provides reference only, not integrated |
| `mybb_hooks_discover` | Keep | Discovers core MyBB hooks, not plugin-specific |
| `mybb_hooks_usage` | Keep | Analyzes existing plugins, useful standalone |

---

## Part 4: Implementation Priorities

### Phase 1: Core Plugin Creation (HIGH PRIORITY)

**Goal**: Make `mybb_create_plugin` use plugin_manager

**Changes**:
1. Refactor `mybb_create_plugin` handler in `server.py:1409-1411`
   - Parse args into plugin_manager.create_plugin() call
   - Map MCP args to manager parameters:
     - `codename` → codename
     - `name` → display_name
     - `description` → description
     - `author` → author (optional)
     - `version` → version (optional)
     - `hooks` → List[Dict[str, str]] with `name` key
     - `has_settings` → settings parameter (if true, create empty list)
     - `has_templates` → has_templates
     - `has_database` → has_database
   - Return manager's response JSON directly (not markdown)

2. Update response format to include:
   - workspace_path (for subsequent operations)
   - files_created list
   - project_id (for tracking)

**Files to Modify**:
- `mybb_mcp/mybb_mcp/server.py` line 1409-1411

### Phase 2: Plugin Lifecycle (HIGH PRIORITY)

**Goal**: Integrate install/uninstall with plugin_manager

**Changes**:
1. Refactor `mybb_plugin_activate` → call `PluginManager.install_plugin()`
2. Refactor `mybb_plugin_deactivate` → call `PluginManager.uninstall_plugin()`

**Files to Modify**:
- `mybb_mcp/mybb_mcp/server.py` lines 1511-1531, 1533+

### Phase 3: Theme Tools (MEDIUM PRIORITY)

**Goal**: Integrate theme creation and stylesheet management

**Changes**:
1. Add `mybb_create_theme` tool if missing (should call PluginManager.create_theme())
2. Refactor stylesheet read/write to use ThemeWorkspace
3. Update list operations to query plugin_manager DB

**Files to Modify**:
- `mybb_mcp/mybb_mcp/server.py` theme handlers

### Phase 4: List/Query Tools (MEDIUM PRIORITY)

**Goal**: Query plugin_manager DB instead of direct filesystem/DB access

**Changes**:
1. `mybb_list_plugins` → query ProjectDatabase for plugins
2. `mybb_list_themes` → query ProjectDatabase for themes
3. `mybb_analyze_plugin` → load meta.json instead of parsing PHP

**Files to Modify**:
- `mybb_mcp/mybb_mcp/server.py` list/query handlers

### Phase 5: Sync Service Integration (MEDIUM PRIORITY)

**Goal**: Extend DiskSyncService to work with plugin_manager workspaces

**Changes**:
1. Add plugin workspace watching to DiskSyncService
2. Enhance export functions to use plugin_manager.export_plugin()
3. Update sync_plugin() in DiskSyncService to work bidirectionally

**Files to Modify**:
- `mybb_mcp/mybb_mcp/sync/service.py`

---

## Part 5: Files Requiring Modifications

### Primary Changes

| File | Changes Required | Scope |
|------|------------------|-------|
| `mybb_mcp/mybb_mcp/server.py` | Update 12 tool handlers to delegate to plugin_manager | 150-200 lines total |
| `mybb_mcp/mybb_mcp/tools/plugins.py` | Remove `create_plugin()` function (move to plugin_manager) | Delete 220 lines |
| `mybb_mcp/mybb_mcp/sync/service.py` | Add plugin workspace sync, enhance export methods | 100-150 lines |

### New Files (If Needed)

| File | Purpose |
|------|---------|
| `mybb_mcp/mybb_mcp/adapters/plugin_manager_bridge.py` | Optional: Wrapper class to bridge MCP tools with PluginManager |

---

## Part 6: Key Insights & Constraints

### Design Principles

1. **No Duplication**: If plugin_manager does it, MCP tools should call plugin_manager
2. **Workspace Awareness**: All operations should respect workspace structure and meta.json
3. **Database Integration**: Use ProjectDatabase for all state tracking
4. **Backward Compatibility**: Keep hook discovery/reference tools unchanged
5. **Structured Response**: Return JSON/dict, not markdown (for tool chaining)

### Constraints

| Constraint | Impact | Solution |
|-----------|--------|----------|
| MCP tools return strings, not JSON | API mismatch with plugin_manager | Wrap plugin_manager results in formatted strings for user readability |
| Existing plugins created with old tools | No workspace structure | Create migration strategy (future) or accept legacy support |
| DiskSyncService uses different workspace structure | Sync incompatibility | Extend DiskSyncService.sync_plugin() to support plugin_manager workspaces |

---

## Part 7: Risk Assessment

### High Risk

- **Plugin creation bypass**: Developers could still create plugins directly without using manager
  - *Mitigation*: Update documentation, deprecate old `mybb_create_plugin` implementation

- **Database state inconsistency**: Cache vs. DB sync issues if not careful
  - *Mitigation*: Always use plugin_manager for state updates, avoid direct cache manipulation

### Medium Risk

- **Hook validation**: plugin_manager may have different hook registry than MyBB core
  - *Mitigation*: Review hook list integration before deployment

### Low Risk

- **Backward compatibility**: Old tools still work but are deprecated
  - *Mitigation*: Gradual deprecation with warnings

---

## Part 8: Open Questions & Gaps

### UNVERIFIED Items

1. **Hook Registry in plugin_manager** — Does plugin_manager have a hook registry? Or does it just pass hook names through?
   - Impact: May need to extend plugin_manager with hook validation
   - Status: UNVERIFIED (searched manager.py, found hook handling but not registry)

2. **Theme creation workflow** — Is there a `mybb_create_theme` MCP tool?
   - Impact: May need to create this tool
   - Status: UNVERIFIED (found theme tools but no create_theme in MCP)

3. **Setting/Template structure** — Does plugin_manager's meta.json match MCP tool expectations?
   - Impact: May need to adapt between formats
   - Status: UNVERIFIED (saw meta.json generation but need full schema validation)

4. **Export validation** — What does plugin_manager validate before export?
   - Impact: May need to validate in MCP layer as well
   - Status: UNVERIFIED (saw validation call but not full validation rules)

### Proposed Solutions

1. **Hook Registry**: Review `plugin_manager/` for hook validation. If missing, create `HookValidator` class
2. **Theme Tool**: Add `mybb_create_theme` MCP tool using `PluginManager.create_theme()`
3. **Schema Alignment**: Create test comparing plugin_manager meta.json with MCP expectations
4. **Export Validation**: Extract plugin_manager validation rules, expose via MCP tools

---

## Deliverables & Next Steps

### For Architect Phase

1. Design tool handler adapter strategy (direct calls vs. wrapper class)
2. Define JSON response format for MCP tools (currently markdown)
3. Plan deprecation strategy for old implementation
4. Design hook validation integration

### For Coder Phase

1. Update `mybb_create_plugin` handler to use PluginManager
2. Add `mybb_create_theme` handler
3. Refactor `mybb_plugin_activate`/`_deactivate` to use install/uninstall
4. Update list/query tools to use ProjectDatabase
5. Extend DiskSyncService for plugin_manager workspaces

### Testing Strategy

1. Unit tests: Each MCP tool handler works correctly
2. Integration tests: Tool output matches expected schemas
3. Database tests: ProjectDatabase state is correct after operations
4. Workspace tests: Files exist in expected locations
5. Sync tests: Watcher works with plugin_manager workspaces

---

## Conclusion

The plugin_manager system provides a superior, unified API for plugin/theme management. The MCP tools should be refactored to delegate to plugin_manager rather than duplicating its functionality. This improves maintainability, ensures consistency, and enables features like workspace management, version tracking, and proper packaging.

**Estimated Integration Effort**: 2-3 days for complete refactoring across all 12 tools (once architecture is approved).

**Success Criteria**: 
- All plugin/theme MCP tools delegate to plugin_manager
- No file I/O or database access in tool handlers except via plugin_manager/DiskSyncService
- All operations create proper workspace structure and meta.json
- All state tracked in ProjectDatabase
- Sync service can watch and sync plugin_manager workspaces
