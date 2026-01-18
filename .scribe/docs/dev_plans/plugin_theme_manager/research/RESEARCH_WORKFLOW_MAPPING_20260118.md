# Plugin Manager Workflow Composition Research

**Date**: 2026-01-18
**Agent**: Research-Workflows
**Project**: plugin-theme-manager
**Confidence**: 0.87 (average across all findings)

## Research Goal

Map the 5 plugin manager workflows (Create, Install, Sync, Export, Import) to existing MCP tools and identify capability gaps, constraints, and orchestration requirements.

## Executive Summary

The plugin manager specification proposes composing 5 workflows from **existing MCP tools without creating new tools**. This research validates that claim and identifies:

- **What works**: 60+ existing MCP tools can support workflows
- **Critical gaps**: File operations (copy/move), ZIP handling, test execution, and plugin workspace management are NOT in MCP
- **Orchestration layer needed**: Most workflows require Python/CLI orchestration ABOVE the MCP layer, not new MCP tools

The spec's claim of "No New Tools Needed" is **partially correct** - no *new MCP tools* are needed, but significant *orchestration logic* must be implemented.

## Workflow Analysis

### Workflow 1: Create Plugin

**User Intent**: "Create a new private plugin called 'my_notifications'"

**Spec Steps**:
1. Creates directory: `plugins/private/my_notifications/`
2. Scaffolds structure using existing `mybb_create_plugin` patterns
3. Creates `meta.json` with defaults
4. Registers in `projects.db`
5. Links to Scribe project for development tracking

**MCP Tools Used**:
- `mybb_create_plugin` — Generates PHP plugin file + language file

**Actual Tool Behavior**:
- Writes directly to `TestForum/inc/plugins/{codename}.php`
- Writes language file to `TestForum/inc/languages/english/{codename}.lang.php`
- Returns confirmation with file paths

**Gap Analysis**:

| Requirement | Tool Support | Issue |
|-----------|------------|-------|
| Create workspace dir `plugins/private/my_plugin/` | MISSING | No file ops in MCP |
| Generate PHP scaffold | ✓ `mybb_create_plugin` | Works as-is |
| Generate meta.json | MISSING | No JSON generation tool |
| Register in projects.db | MISSING | SQLite write tool needed (only SELECT available) |
| Link to Scribe project | MISSING | Requires Scribe API integration |

**Confidence**: 0.95
**Verdict**: Tool exists but orchestration wrapper required for full workflow

---

### Workflow 2: Install Plugin to TestForum

**User Intent**: "Install my_notifications to the forum"

**Spec Steps**:
1. Reads `meta.json` for file mappings
2. Copies `src/my_notifications.php` → `TestForum/inc/plugins/`
3. Copies `languages/*` → `TestForum/inc/languages/english/`
4. Uses `mybb_plugin_activate` to enable in cache
5. Updates `projects.db` status = 'installed'
6. Warns: "Remember to activate in ACP to run _activate() hooks"

**MCP Tools Used**:
- `mybb_plugin_activate` — Updates plugin cache
- `mybb_template_batch_write` — Deploy templates (if plugin has them)

**Actual Tool Behavior**:
- `mybb_plugin_activate`: Adds plugin codename to active plugins cache only
- `mybb_template_batch_write`: Creates/updates multiple templates atomically
- No equivalent tool for stylesheets batch operations

**Gap Analysis**:

| Requirement | Tool Support | Issue |
|-----------|------------|-------|
| Copy plugin file from workspace to TestForum | MISSING | **CRITICAL**: No file copy tool in MCP |
| Copy language files | MISSING | **CRITICAL**: No file copy tool in MCP |
| Deploy plugin templates | ✓ `mybb_template_batch_write` | Works as-is |
| Deploy plugin stylesheets | ✗ `mybb_write_stylesheet` | Only single file at a time, not batch |
| Activate plugin cache | ✓ `mybb_plugin_activate` | Works but only updates cache, not _activate() hooks |
| Update projects.db | MISSING | No SQLite write access |

**Confidence**: 0.90
**Verdict**: **CRITICAL GAP** — File copy operations not available. CLI/bash must handle or new orchestration tool needed.

---

### Workflow 3: Sync Development Changes

**User Intent**: "Sync my plugin changes to the forum"

**Spec Steps**:
1. Detects modified files in `plugins/private/my_notifications/`
2. Copies updated files to `TestForum` locations
3. If templates changed, uses `mybb_template_batch_write`
4. If stylesheets changed, uses `mybb_write_stylesheet` + cache refresh
5. Logs sync in history table

**Existing Infrastructure**:
- `FileWatcher` class (watchdog-based monitoring) in `sync/service.py`
- `DiskSyncService` orchestrates watches
- Currently monitors `mybb_sync/` directory for template/stylesheet changes

**MCP Tools Used**:
- `mybb_template_batch_write` — Sync template changes to DB
- `mybb_write_stylesheet` — Sync stylesheet changes to DB
- File watcher (not an MCP tool)

**Actual Tool Behavior**:
- File watcher listens on `mybb_sync/` exported files
- Detects modifications, creates batches
- Sends updates to DB via `mybb_template_batch_write`

**Gap Analysis**:

| Requirement | Tool Support | Issue |
|-----------|------------|-------|
| Detect file changes in `plugins/private/` | PARTIAL | FileWatcher exists but watches `mybb_sync/`, not plugin source |
| Copy changed files to TestForum | MISSING | **CRITICAL**: No file ops in MCP |
| Template sync | ✓ `mybb_template_batch_write` | Works for DB sync |
| Stylesheet sync | ✓ `mybb_write_stylesheet` | Works for DB sync |
| History logging | MISSING | No history table tool |

**Confidence**: 0.85
**Verdict**: Existing FileWatcher is scope mismatch (templates/stylesheets, not plugins). File copy operations still missing.

---

### Workflow 4: Export Plugin for Distribution

**User Intent**: "Package my_notifications for release"

**Spec Steps**:
1. Validates `meta.json` completeness
2. Runs any tests in `tests/` folder
3. Creates distributable ZIP with PHP, languages, templates, README
4. Generates install instructions from hooks/settings

**MCP Tools Used**:
- `mybb_analyze_plugin` — Extract hooks/settings from PHP (can be used to generate README)

**Actual Tool Behavior**:
- `mybb_analyze_plugin`: Parses PHP file, extracts hooks, functions, features
- Returns markdown summary suitable for documentation

**Gap Analysis**:

| Requirement | Tool Support | Issue |
|-----------|------------|-------|
| Validate meta.json | MISSING | No JSON schema validation tool |
| Run tests | MISSING | No test execution framework |
| Create ZIP archive | MISSING | **CRITICAL**: No ZIP creation tool in MCP |
| Generate README from analysis | ✓ (via `mybb_analyze_plugin`) | Can extract content for README |
| Install instructions | ✓ (via `mybb_analyze_plugin`) | Can analyze hooks/settings |

**Confidence**: 0.90
**Verdict**: Export is fully custom orchestration. Only `mybb_analyze_plugin` is reusable for README generation.

---

### Workflow 5: Import External Plugin

**User Intent**: "Import this plugin ZIP for development"

**Spec Steps**:
1. Extracts ZIP to `plugins/public/imported_plugin/`
2. Analyzes PHP for hooks, settings, templates
3. Generates `meta.json` from analysis
4. Registers in `projects.db`
5. Links to Scribe for development tracking

**MCP Tools Used**:
- `mybb_analyze_plugin` — Parse PHP structure (hooks, settings, templates)

**Actual Tool Behavior**:
- `mybb_analyze_plugin`: Parses existing plugin files
- Extracts hooks, functions, features
- Returns structured markdown

**Gap Analysis**:

| Requirement | Tool Support | Issue |
|-----------|------------|-------|
| Extract ZIP file | MISSING | **CRITICAL**: No ZIP extraction tool in MCP |
| Analyze plugin structure | ✓ `mybb_analyze_plugin` | Works for parsing hooks/settings |
| Generate meta.json | MISSING | No JSON generation tool |
| Register in projects.db | MISSING | No SQLite write access |
| Create Scribe project | MISSING | Requires Scribe API integration |

**Confidence**: 0.85
**Verdict**: `mybb_analyze_plugin` is reusable, but ZIP handling and project setup missing.

---

## Tool Inventory Summary

### Existing MCP Tools (60+)

**Template Management (8)**
- `mybb_list_template_sets`, `mybb_list_templates`, `mybb_read_template`
- `mybb_write_template`, `mybb_list_template_groups`, `mybb_template_find_replace`
- `mybb_template_batch_read`, `mybb_template_batch_write`, `mybb_template_outdated`

**Theme/Stylesheet (4)**
- `mybb_list_themes`, `mybb_list_stylesheets`
- `mybb_read_stylesheet`, `mybb_write_stylesheet`

**Plugin Management (11)**
- `mybb_list_plugins`, `mybb_read_plugin`, `mybb_create_plugin`
- `mybb_list_hooks`, `mybb_hooks_discover`, `mybb_hooks_usage`
- `mybb_analyze_plugin` ← Reusable for metadata generation
- `mybb_plugin_list_installed`, `mybb_plugin_info`
- `mybb_plugin_activate`, `mybb_plugin_deactivate`, `mybb_plugin_is_installed`

**Disk Sync (4)**
- `mybb_sync_export_templates`, `mybb_sync_export_stylesheets`
- `mybb_sync_start_watcher`, `mybb_sync_stop_watcher`

**Content CRUD (12)** — Forums, threads, posts

**Scheduled Tasks (6)**

**Database Query (1)**
- `mybb_db_query` — SELECT only, read-only

### Missing Capabilities

**File Operations**
- No copy/move/delete files
- No directory creation
- No file read/write outside MCP API

**Archive Operations**
- No ZIP creation
- No ZIP extraction

**Database Write**
- `mybb_db_query` is SELECT-only
- Cannot write to `projects.db` (SQLite)

**Metadata Management**
- No JSON schema validation
- No meta.json generation

**Test Execution**
- No test runner integration

**Scribe Integration**
- No direct Scribe project creation from MCP

---

## Architecture Implications

### Current Design (Spec Assumption)

```
User Request
    ↓
Claude (Claude Code)
    ↓
MCP Tool Call (e.g., mybb_create_plugin)
    ↓
Immediate Result
```

### Required Design (Actual Implementation)

```
User Request
    ↓
Claude (Claude Code)
    ↓
Orchestration Layer (Python/CLI)
    ├─ File operations (copy, move, extract)
    ├─ Metadata management (meta.json generation)
    ├─ Archive handling (ZIP)
    └─ MCP Tool Calls (templates, plugin activation)
    ↓
Database Updates (if applicable)
    ↓
Result
```

### Implementation Options

**Option A: New MCP Tools** (Violates spec intent)
- Add `mybb_file_copy`, `mybb_create_archive`, `mybb_extract_archive` tools
- Con: Violates "No New Tools Needed" requirement
- Pro: Clean MCP integration

**Option B: Claude Code + Bash** (Spec's intent)
- Claude Code orchestrates workflows in natural language
- Uses bash for file ops, Python subprocess for archive handling
- Con: Harder to track in MCP auditing
- Pro: Fulfills "No New Tools Needed" constraint

**Option C: Hybrid Skill** (Recommended)
- Create `/tools/plugin_manager.skill` or similar
- Encapsulates orchestration logic
- Calls existing MCP tools as needed
- Can be invoked from Claude Code naturally

---

## Gap Summary by Severity

### CRITICAL (Blocks Workflows)

| Gap | Impact | Affected Workflows |
|-----|--------|-------------------|
| File copy/move operations | Cannot install or sync plugins | Install, Sync |
| ZIP extraction | Cannot import external plugins | Import |
| ZIP creation | Cannot export plugins for distribution | Export |
| SQLite write (projects.db) | Cannot track plugin metadata | Create, Install, Import |

### HIGH (Degrades Workflows)

| Gap | Impact | Affected Workflows |
|-----|--------|-------------------|
| JSON generation/validation | Cannot generate meta.json reliably | Create, Import, Export |
| Test execution | Cannot validate before export | Export |
| History logging | Cannot audit sync operations | Sync |

### MEDIUM (Requires Workarounds)

| Gap | Impact | Affected Workflows |
|-----|--------|-------------------|
| Scribe integration | Manual project creation needed | Create, Import |
| Stylesheet batch ops | Single-file limits scalability | Install, Sync |

---

## Recommendations

### For Plugin Manager Implementation

1. **Use Option C (Hybrid Skill)** for orchestration
   - Implement file operations via Python `pathlib`
   - Use `zipfile` module for archives
   - Call existing MCP tools as functions
   - Can be wrapped as a Claude Code skill

2. **Implement metadata store** (SQLite `projects.db`)
   - Track plugin workspace paths, versions, status
   - Query existing schema before new implementation

3. **Extend FileWatcher scope**
   - Current implementation watches `mybb_sync/` (templates/stylesheets)
   - Consider separate watcher for `plugins/private/` workspace
   - Or unify into single service with multiple watch paths

4. **Leverage existing tools**
   - `mybb_create_plugin` for PHP scaffolding
   - `mybb_analyze_plugin` for import analysis and README generation
   - `mybb_template_batch_write` for template deployment
   - `mybb_hooks_discover` for hook discovery

5. **Constraints to document**
   - File operations are out-of-scope for MCP (correct design)
   - But orchestration layer CAN use file operations
   - Document this separation clearly

---

## Verification References

| Finding | Source | Lines | Confidence |
|---------|--------|-------|-----------|
| mybb_create_plugin implementation | plugins.py | 161-382 | 0.95 |
| mybb_plugin_activate cache only | server.py | 1511-1531 | 0.99 |
| mybb_template_batch_write works | server.py | 1269-1317 | 0.98 |
| FileWatcher watches mybb_sync/ | watcher.py, service.py | 21-212, 60-81 | 0.92 |
| mybb_analyze_plugin exists | server.py | 1430-1463 | 0.99 |
| No ZIP tools in MCP | server.py | 50-700 (all tools) | 0.98 |
| No file copy tools in MCP | server.py | 50-700 (all tools) | 0.99 |
| No SQLite write access | server.py | 424-436 | 0.99 |

---

## Next Steps for Architect

1. **Design orchestration layer** that composes MCP tools + file operations
2. **Implement projects.db schema** for plugin metadata tracking
3. **Create meta.json schema** for plugin configuration
4. **Plan skill/CLI interface** for workflow invocation
5. **Define error handling strategy** for file operations

---

## Conclusion

The spec's claim of "no new MCP tools needed" is **technically correct but incomplete**.

- No new *MCP tools* are required ✓
- Significant *orchestration layer* is required ✓
- File operations must happen outside MCP (correct design) ✓
- Implementation complexity is higher than a single tool ⚠️

The workflow composition is **feasible with existing tools**, but the orchestration layer is the real work item, not the tools themselves.
