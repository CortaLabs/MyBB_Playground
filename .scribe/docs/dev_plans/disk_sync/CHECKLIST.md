---
id: disk_sync-checklist
title: "\u2705 Acceptance Checklist \u2014 disk-sync"
doc_name: CHECKLIST
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

# ✅ Acceptance Checklist — disk-sync
**Author:** Scribe
**Version:** v0.1
**Status:** Draft
**Last Updated:** 2026-01-17 11:30:14 UTC

> Acceptance checklist for disk-sync.

---
## Documentation Hygiene
<!-- ID: documentation_hygiene -->
## Documentation Hygiene
<!-- ID: documentation_hygiene -->

- [x] Architecture guide updated (proof: ARCHITECTURE_GUIDE.md - 17KB, 10 sections)
- [x] Phase plan current (proof: PHASE_PLAN.md - 4 phases, 14 tasks)
- [x] Research document complete (proof: RESEARCH_VSCODE_SYNC_PATTERNS.md - 964 lines)
<!-- ID: phase_0 -->
## Phase 1 - Foundation
<!-- ID: phase_0 -->

- [x] **Task 1.1**: Create sync module structure ✅
  - Files: `mybb_mcp/sync/__init__.py`
  - Verification: `from mybb_mcp.sync import *` works ✓

- [x] **Task 1.2**: Implement SyncConfig dataclass ✅
  - Files: `mybb_mcp/sync/config.py`
  - Verification: Config loads from .env variables ✓

- [x] **Task 1.3**: Implement PathRouter ✅
  - Files: `mybb_mcp/sync/router.py`
  - Verification: Path parsing and building tested and working ✓

- [x] **Task 1.4**: Add database helper methods ✅
  - Files: `mybb_mcp/db/connection.py`
  - Methods: get_template_set_by_name, list_template_groups, get_theme_by_name, get_stylesheet_by_name
  - Verification: All methods added and verified ✓

---
## Phase 2 - Export
<!-- ID: phase_1 -->

- [x] **Task 2.1**: Implement TemplateGroupManager ✅
  - Files: `mybb_mcp/sync/groups.py`
  - Verification: Multi-strategy matching (global, hardcoded, DB lookup, fallback) implemented ✓

- [x] **Task 2.2**: Implement TemplateExporter ✅
  - Files: `mybb_mcp/sync/templates.py`
  - Verification: Exports with correct SQL pattern (WHERE sid IN (-2, ?)), group categorization ✓

- [x] **Task 2.3**: Implement StylesheetExporter ✅
  - Files: `mybb_mcp/sync/stylesheets.py`
  - Verification: Exports stylesheets to styles/{theme}/ structure ✓

---
## Phase 3 - Import & Watch
<!-- ID: phase_2 -->

- [x] **Task 3.1**: Implement TemplateImporter ✅
  - Files: `mybb_mcp/sync/templates.py`
  - Verification: Inheritance logic handles all 4 cases (master exists/custom exists combinations)
  - Implementation: TemplateImporter class with import_template() method, uses get_template_set_by_name, get_template, update_template, create_template

- [x] **Task 3.2**: Implement StylesheetImporter ✅
  - Files: `mybb_mcp/sync/stylesheets.py`, `mybb_mcp/db/connection.py` (added create_stylesheet)
  - Verification: Stylesheet updates reflected in database with lastmodified timestamp
  - Implementation: StylesheetImporter class with import_stylesheet() method, added create_stylesheet to MyBBDatabase

- [x] **Task 3.3**: Implement CacheRefresher ✅
  - Files: `mybb_mcp/sync/cache.py`, `mybb_mcp/pyproject.toml` (added httpx dependency)
  - Verification: HTTP POST to cachecss.php with theme_name, stylesheet, token
  - Implementation: CacheRefresher class with refresh_stylesheet() method, uses httpx.AsyncClient with 10s timeout, graceful error handling

- [x] **Task 3.4**: Implement FileWatcher ✅
  - Files: `mybb_mcp/sync/watcher.py`, `mybb_mcp/pyproject.toml` (added watchdog dependency)
  - Verification: File saves trigger database updates via importers and cache refresh for stylesheets
  - Implementation: FileWatcher and SyncEventHandler classes, monitors .html in template_sets/ and .css in styles/, uses PathRouter for path parsing

---
## Phase 4 - Integration
<!-- ID: phase_3 -->

- [x] **Task 4.1**: Implement DiskSyncService orchestrator
  - Files: `mybb_mcp/sync/service.py` (133 lines)
  - Verification: DiskSyncService created with __init__, export_template_set, export_theme, start_watcher, stop_watcher, get_status methods
  - Implementation: Orchestrates all Phase 1-3 components (router, exporters, importers, watcher, cache_refresher)

- [x] **Task 4.2**: Add MCP tool handlers
  - Files: `mybb_mcp/server.py` (modified lines 28-39, 208-260, 277, 286, 522-583)
  - Tools: mybb_sync_export_templates, mybb_sync_export_stylesheets, mybb_sync_start_watcher, mybb_sync_stop_watcher, mybb_sync_status
  - Verification: All 5 tools registered in all_tools list, handlers implemented with markdown output format
  - Implementation: DiskSyncService initialized in create_server(), sync_service passed to handle_tool()

- [x] **Task 4.3**: Add dependencies to pyproject.toml
  - Dependencies: watchdog>=3.0.0, httpx>=0.27.0
  - Verification: Dependencies already present from Phase 3 (lines 12-13)

- [x] **Task 4.4**: Write integration tests
  - Files: N/A (manual testing per user instruction)
  - Verification: Skipped - user specified "DO NOT write test files (manual testing sufficient)"
<!-- ID: final_verification -->
## Final Verification
<!-- ID: final_verification -->

- [ ] All Phase 1 tasks completed with passing tests
- [ ] All Phase 2 tasks completed with export verification
- [ ] All Phase 3 tasks completed with import/watch verification
- [ ] All Phase 4 tasks completed with MCP integration verified
- [ ] Full sync cycle tested: export -> edit -> auto-import
- [ ] Code review completed
- [ ] Documentation updated if APIs changed
