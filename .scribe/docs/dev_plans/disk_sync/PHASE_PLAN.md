---
id: disk_sync-phase-plan
title: "\u2699\uFE0F Phase Plan \u2014 disk-sync"
doc_name: PHASE_PLAN
category: engineering
status: draft
version: '0.1'
last_updated: '2026-01-17'
maintained_by: Corta Labs
created_by: Corta Labs
owners: []
related_docs: []
tags: []
summary: ''
---

# ⚙️ Phase Plan — disk-sync
**Author:** Scribe
**Version:** Draft v0.1
**Status:** active
**Last Updated:** 2026-01-17 11:30:14 UTC

> Execution roadmap for disk-sync.

---
## Phase Overview
<!-- ID: phase_overview -->
## Phase Overview
<!-- ID: phase_overview -->

| Phase | Goal | Key Deliverables | Est. Effort | Confidence |
|-------|------|------------------|-------------|------------|
| Phase 1 - Foundation | Core infrastructure and path routing | SyncConfig, PathRouter, DB methods | 2-3 hours | 0.95 |
| Phase 2 - Export | DB to Disk synchronization | TemplateExporter, StylesheetExporter, TemplateGroupManager | 3-4 hours | 0.90 |
| Phase 3 - Import & Watch | Disk to DB sync with file watching | Importers, FileWatcher, CacheRefresher | 4-5 hours | 0.85 |
| Phase 4 - Integration | MCP tools and polish | MCP tool handlers, error handling, tests | 2-3 hours | 0.90 |

**Total Estimated Effort:** 11-15 hours

**Dependencies:**
- Phase 2 depends on Phase 1 (PathRouter, DB methods)
- Phase 3 depends on Phase 2 (uses same DB patterns)
- Phase 4 depends on all previous phases
<!-- ID: phase_0 -->
## Phase 1 - Foundation
<!-- ID: phase_0 -->

**Objective:** Create core infrastructure for disk-sync module.

**Task Packages:**

### Task 1.1: Create sync module structure
**Scope:** Create `mybb_mcp/sync/` directory with `__init__.py`
**Files:** `mybb_mcp/sync/__init__.py`
**Verification:** Module importable: `from mybb_mcp.sync import *`

### Task 1.2: Implement SyncConfig
**Scope:** Add configuration dataclass for sync settings
**Files:** `mybb_mcp/sync/config.py`
**Specifications:**
```python
@dataclass
class SyncConfig:
    sync_root: Path          # Directory for synced files
    auto_upload: bool = True # Enable file watching
    cache_token: str = ""    # Optional auth token
```
**Verification:** Config loads from .env variables

### Task 1.3: Implement PathRouter
**Scope:** Parse file paths and route to handlers
**Files:** `mybb_mcp/sync/router.py`
**Specifications:**
- `parse(relative_path: str) -> ParsedPath`
- `build_template_path(set_name, group, title) -> Path`
- `build_stylesheet_path(theme_name, name) -> Path`
**Verification:** Unit tests pass for valid/invalid paths

### Task 1.4: Add database helper methods
**Scope:** Add new methods to MyBBDatabase
**Files:** `mybb_mcp/db/connection.py`
**Specifications:**
- `get_template_set_by_name(name: str) -> dict | None`
- `list_template_groups() -> list[dict]`
- `get_theme_by_name(name: str) -> dict | None`
- `get_stylesheet_by_name(tid: int, name: str) -> dict | None`
**Verification:** Methods return correct data from test database

**Acceptance Criteria:**
- [ ] sync/ module structure created
- [ ] SyncConfig loads from environment
- [ ] PathRouter parses all path patterns correctly
- [ ] All new DB methods work against test database
<!-- ID: phase_1 -->
## Phase 2 - Export (DB to Disk)
<!-- ID: phase_1 -->

**Objective:** Implement database to disk export for templates and stylesheets.

**Task Packages:**

### Task 2.1: Implement TemplateGroupManager
**Scope:** Determine template group from prefix using multi-strategy matching
**Files:** `mybb_mcp/sync/groups.py`
**Specifications:**
- Load groups from database (templategroups table)
- Hardcoded pattern matching (header_, footer_, usercp_, etc.)
- Fallback to capitalized prefix
- Handle language strings (<lang:group_xyz>)
**Verification:** All matching strategies tested

### Task 2.2: Implement TemplateExporter
**Scope:** Export all templates from a template set to disk
**Files:** `mybb_mcp/sync/templates.py`
**Specifications:**
- `export(set_name: str) -> ExportResult`
- Fetch templates WHERE sid IN (-2, target_sid)
- Use TemplateGroupManager for folder assignment
- Write to `sync_root/template_sets/{set}/{group}/{template}.html`
**Verification:** Export creates correct directory structure

### Task 2.3: Implement StylesheetExporter
**Scope:** Export all stylesheets from a theme to disk
**Files:** `mybb_mcp/sync/stylesheets.py`
**Specifications:**
- `export(theme_name: str) -> ExportResult`
- Fetch stylesheets WHERE tid = theme_tid
- Write to `sync_root/styles/{theme}/{stylesheet}.css`
**Verification:** Export creates correct file structure

**Acceptance Criteria:**
- [ ] TemplateGroupManager correctly categorizes all template types
- [ ] Template export creates vscode-mybbbridge compatible structure
- [ ] Stylesheet export creates correct file hierarchy
- [ ] Both exporters handle empty sets gracefully
<!-- ID: milestone_tracking -->
## Phase 3 - Import & Watch (Disk to DB)
<!-- ID: milestone_tracking -->

**Objective:** Implement disk to database sync with file watching.

**Task Packages:**

### Task 3.1: Implement TemplateImporter
**Scope:** Import template changes from disk to database
**Files:** `mybb_mcp/sync/templates.py`
**Specifications:**
- `import_template(set_name: str, template_name: str, content: str) -> bool`
- Check master template exists (sid=-2)
- Check custom template exists (sid=target_sid)
- UPDATE existing or INSERT new custom version
**Verification:** Inheritance logic handles all 4 cases correctly

### Task 3.2: Implement StylesheetImporter
**Scope:** Import stylesheet changes from disk to database
**Files:** `mybb_mcp/sync/stylesheets.py`
**Specifications:**
- `import_stylesheet(theme_name: str, stylesheet_name: str, content: str) -> bool`
- Verify theme exists
- UPDATE existing or INSERT new stylesheet
**Verification:** Stylesheet updates reflected in database

### Task 3.3: Implement CacheRefresher
**Scope:** Trigger MyBB stylesheet cache refresh via HTTP
**Files:** `mybb_mcp/sync/cache.py`
**Specifications:**
- `async refresh(theme_name: str, stylesheet_name: str) -> bool`
- POST to {mybb_url}/cachecss.php
- Handle HTTP errors gracefully
**Verification:** Cache refresh returns success JSON

### Task 3.4: Implement FileWatcher
**Scope:** Monitor sync directory for file changes
**Files:** `mybb_mcp/sync/watcher.py`
**Specifications:**
- Extend watchdog.events.FileSystemEventHandler
- Filter for .html in template_sets/ and .css in styles/
- Route events to appropriate importers
- Start/stop methods for lifecycle management
**Verification:** File saves trigger database updates

**Acceptance Criteria:**
- [ ] Template import handles all inheritance cases
- [ ] Stylesheet import triggers cache refresh
- [ ] FileWatcher detects all file modifications
- [ ] No crashes on invalid file paths
<!-- ID: retro_notes -->
## Phase 4 - Integration & Polish
<!-- ID: retro_notes -->

**Objective:** Add MCP tools and finalize the feature.

**Task Packages:**

### Task 4.1: Implement DiskSyncService
**Scope:** Main orchestrator class that ties everything together
**Files:** `mybb_mcp/sync/service.py`
**Specifications:**
- Initialize all components (router, exporters, importers, watcher)
- Provide public API: export_templates(), export_stylesheets(), start_watcher(), stop_watcher()
- Handle errors and logging
**Verification:** Service lifecycle works correctly

### Task 4.2: Add MCP Tool Handlers
**Scope:** Register sync tools with MCP server
**Files:** `mybb_mcp/server.py`
**Specifications:**
- `mybb_sync_export_templates` - Export template set to disk
- `mybb_sync_export_stylesheets` - Export theme stylesheets to disk
- `mybb_sync_start_watcher` - Start file watching
- `mybb_sync_stop_watcher` - Stop file watching
- `mybb_sync_status` - Show sync status
**Verification:** All tools callable via MCP

### Task 4.3: Add dependencies to pyproject.toml
**Scope:** Add watchdog and httpx dependencies
**Files:** `mybb_mcp/pyproject.toml`
**Specifications:**
- watchdog>=3.0
- httpx>=0.25
**Verification:** `pip install -e .` succeeds

### Task 4.4: Write integration tests
**Scope:** End-to-end tests for sync functionality
**Files:** `tests/test_sync_integration.py`
**Specifications:**
- Test export -> edit -> import cycle
- Test FileWatcher event handling
- Test error handling paths
**Verification:** All tests pass

**Acceptance Criteria:**
- [ ] DiskSyncService orchestrates all components
- [ ] All 5 MCP tools registered and functional
- [ ] Dependencies installed without errors
- [ ] Integration tests pass

---
## Milestone Tracking

| Milestone | Target Date | Owner | Status | Evidence/Link |
|-----------|-------------|-------|--------|---------------|
| Phase 1 Complete | TBD | Coder | Planned | Task 1.1-1.4 |
| Phase 2 Complete | TBD | Coder | Planned | Task 2.1-2.3 |
| Phase 3 Complete | TBD | Coder | Planned | Task 3.1-3.4 |
| Phase 4 Complete | TBD | Coder | Planned | Task 4.1-4.4 |
| Feature Ready | TBD | Review | Planned | All tests pass |
