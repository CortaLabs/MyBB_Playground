# Acceptance Checklist - MyBB Forge v2

**Author:** MyBB-ArchitectAgent
**Version:** v1.0
**Status:** Ready for Implementation
**Last Updated:** 2026-01-19
**Confidence:** 0.92

> Verification checklist for MyBB Forge v2 refactoring. Each item requires explicit proof before marking complete.

---

## Phase 1: Foundation & Configuration
<!-- ID: phase_1 -->

### Task 1.1: ForgeConfig Class
- [ ] `plugin_manager/forge_config.py` exists
- [ ] `ForgeConfig` class has `__init__(repo_root: Path)`
- [ ] `_load()` method handles YAML and ENV files
- [ ] `developer_name` property returns string
- [ ] `get_subtree_remote()` resolves ENV variable references
- [ ] **PROOF**: `pytest tests/plugin_manager/test_forge_config.py -v` passes

### Task 1.2: Configuration Example Files
- [ ] `.mybb-forge.yaml.example` exists at repo root
- [ ] `.mybb-forge.env.example` exists at repo root
- [ ] `.gitignore` contains `.mybb-forge.env`
- [ ] YAML example has all sections: developer, defaults, subtrees, sync
- [ ] **PROOF**: `cat .mybb-forge.yaml.example` shows valid YAML

### Task 1.3: ForgeConfig Unit Tests
- [ ] `tests/plugin_manager/test_forge_config.py` exists
- [ ] Test coverage >90% for forge_config.py
- [ ] Tests use `tmp_path` fixture for isolation
- [ ] **PROOF**: `pytest tests/plugin_manager/test_forge_config.py -v --cov=plugin_manager.forge_config`

### Task 1.4: Plugin Manager Integration
- [ ] `PluginManager` instantiates `ForgeConfig`
- [ ] `create_plugin()` uses config for author auto-fill
- [ ] Works without config files (graceful fallback)
- [ ] **PROOF**: `mybb_create_plugin` auto-fills author when config exists

---

## Phase 2: Server Modularization (Simple)
<!-- ID: phase_2 -->

### Task 2.1: Handler Infrastructure
- [ ] `mybb_mcp/mybb_mcp/handlers/__init__.py` exists
- [ ] `mybb_mcp/mybb_mcp/handlers/common.py` exists
- [ ] `mybb_mcp/mybb_mcp/handlers/dispatcher.py` exists
- [ ] `format_markdown_table()` function works
- [ ] `dispatch_tool()` returns "Unknown tool" for unregistered tools
- [ ] **PROOF**: `from mybb_mcp.handlers import dispatch_tool` succeeds

### Task 2.2: Database Query Handler
- [ ] `mybb_mcp/mybb_mcp/handlers/database.py` exists
- [ ] `DATABASE_HANDLERS` dict exported
- [ ] `mybb_db_query` tool works via dispatcher
- [ ] **PROOF**: MCP tool `mybb_db_query` returns results

### Task 2.3: Task Handlers
- [ ] `mybb_mcp/mybb_mcp/handlers/tasks.py` exists
- [ ] `TASK_HANDLERS` dict contains 6 entries
- [ ] All task tools work: list, get, enable, disable, update_nextrun, run_log
- [ ] **PROOF**: `mybb_task_list` returns scheduled tasks

### Task 2.4: Admin/Cache Handlers
- [ ] `mybb_mcp/mybb_mcp/handlers/admin.py` exists
- [ ] `ADMIN_HANDLERS` dict contains 11 entries
- [ ] Settings and cache tools work correctly
- [ ] **PROOF**: `mybb_setting_list` returns settings

---

## Phase 3: Server Modularization (Complex)
<!-- ID: phase_3 -->

### Task 3.1: Template Handlers
- [ ] `mybb_mcp/mybb_mcp/handlers/templates.py` exists
- [ ] `TEMPLATE_HANDLERS` dict contains 9 entries
- [ ] Template read/write tools work correctly
- [ ] **PROOF**: `mybb_read_template title="header"` returns template

### Task 3.2: Theme/Stylesheet Handlers
- [ ] `mybb_mcp/mybb_mcp/handlers/themes.py` exists
- [ ] `THEME_HANDLERS` dict contains 6 entries
- [ ] Stylesheet read/write tools work correctly
- [ ] **PROOF**: `mybb_list_stylesheets` returns stylesheets

### Task 3.3: Content CRUD Handlers
- [ ] `mybb_mcp/mybb_mcp/handlers/content.py` exists
- [ ] `CONTENT_HANDLERS` dict contains 17 entries
- [ ] Forum, thread, post CRUD all work
- [ ] **PROOF**: `mybb_forum_list` returns forums

### Task 3.4: Remaining Handlers
- [ ] `handlers/search.py` exists with 4 handlers
- [ ] `handlers/moderation.py` exists with 8 handlers
- [ ] `handlers/users.py` exists with 7 handlers
- [ ] `handlers/sync.py` exists with 5 handlers
- [ ] `handlers/plugins.py` exists with 12 handlers
- [ ] **PROOF**: `len(HANDLER_REGISTRY) == 85`

### Task 3.5: Server.py Cleanup
- [ ] `mybb_mcp/mybb_mcp/tools_registry.py` exists
- [ ] `ALL_TOOLS` list exported from tools_registry
- [ ] `server.py` reduced to ~150 lines
- [ ] All 85 MCP tools work via `claude mcp get mybb`
- [ ] **PROOF**: `wc -l mybb_mcp/mybb_mcp/server.py` shows <200 lines
- [ ] **PROOF**: `pytest tests/` passes

---

## Phase 4: Plugin Architecture v2
<!-- ID: phase_4 -->

### Task 4.1: Enhanced meta.json Schema
- [ ] `plugin_manager/schema.py` validates templates array
- [ ] `plugin_manager/schema.py` validates manifest object
- [ ] `PluginWorkspace.scan_templates()` method exists
- [ ] `PluginWorkspace.compute_manifest()` generates SHA512 hashes
- [ ] **PROOF**: Schema validates sample enhanced meta.json

### Task 4.2: Plugin Scaffold Updates
- [ ] New plugins have `templates/` directory
- [ ] New plugins have `styles/` directory
- [ ] `meta.json` includes templates array
- [ ] Template stub file `{codename}_main.html` created
- [ ] **PROOF**: `mybb_create_plugin codename="test_v2"` creates new structure

### Task 4.3: PHP Template Helpers
- [ ] `plugin_manager/templates/plugin_helpers.php.template` exists
- [ ] Helper reads meta.json for template list
- [ ] `_install()` calls load helper
- [ ] `_uninstall()` calls remove helper
- [ ] **PROOF**: Generated PHP is syntactically valid

### Task 4.4: Installer Disk Templates
- [ ] `install_plugin()` copies templates/ directory
- [ ] Manifest includes template file hashes
- [ ] `uninstall_plugin()` removes template files
- [ ] **PROOF**: Templates appear in TestForum after deploy

### Task 4.5: Integration Test
- [ ] `tests/plugin_manager/test_disk_templates.py` exists
- [ ] Full lifecycle test passes
- [ ] **PROOF**: `pytest tests/plugin_manager/test_disk_templates.py -v` passes

---

## Phase 5: DB-Sync Optimizations
<!-- ID: phase_5 -->

### Task 5.1: Smart Batching
- [ ] `DEBOUNCE_SECONDS` changed to 0.1
- [ ] `BATCH_WINDOW_SECONDS` added (0.1)
- [ ] `_queue_for_batch()` method exists
- [ ] `_flush_batch()` method exists
- [ ] Multiple rapid changes batched together
- [ ] **PROOF**: Editing 3 templates in 200ms results in single DB transaction

### Task 5.2: Template Set Caching
- [ ] `TemplateImporter._set_cache` dict exists
- [ ] `_get_template_set_id()` uses cache
- [ ] Cache expires after 5 minutes
- [ ] **PROOF**: Second template sync uses cached set ID (log inspection)

### Task 5.3: Bulk Update Methods
- [ ] `MyBBDatabase.update_post_field()` method exists
- [ ] `MyBBDatabase.update_posts_by_thread()` method exists
- [ ] Invalid field raises ValueError
- [ ] **PROOF**: Unit tests for both methods pass

---

## Phase 6: Git Subtree & Finalization
<!-- ID: phase_6 -->

### Task 6.1: Subtree Handlers
- [ ] `handlers/subtrees.py` exists
- [ ] `SUBTREE_HANDLERS` dict contains 4 entries
- [ ] Tool definitions added to tools_registry
- [ ] **PROOF**: `mybb_subtree_list` returns configured subtrees

### Task 6.2: Direct SQL Replacement
- [ ] `handle_thread_create` uses `db.update_post_field()`
- [ ] `handle_thread_move` uses `db.update_posts_by_thread()`
- [ ] No `cur.execute()` in handlers (except mybb_db_query)
- [ ] **PROOF**: `grep -r "cur.execute" handlers/` returns only database.py

### Task 6.3: Documentation Updates
- [ ] `CLAUDE.md` has .mybb-forge.yaml section
- [ ] `CLAUDE.md` documents new plugin structure
- [ ] Wiki workspace docs updated
- [ ] Wiki subtree tools documented
- [ ] **PROOF**: Grep CLAUDE.md for "mybb-forge.yaml"

### Task 6.4: Final Integration Testing
- [ ] `tests/integration/test_forge_v2.py` exists
- [ ] All 89 MCP tools work (85 + 4 subtree)
- [ ] Sync latency <200ms measured
- [ ] **PROOF**: `pytest tests/integration/test_forge_v2.py -v` passes

---

## Success Criteria Summary
<!-- ID: success_criteria -->

| Criterion | Target | Verification Method |
|-----------|--------|---------------------|
| MCP Tools Count | 89 (85 + 4 subtree) | `len(HANDLER_REGISTRY)` |
| Server.py Lines | <200 | `wc -l server.py` |
| Test Coverage | >85% | pytest --cov |
| Sync Latency | <200ms | Timing measurement |
| Config Auto-fill | Working | Manual test with config |
| Disk Templates | Working | Plugin deploy test |
| Direct SQL | Eliminated | grep check |

---

## Final Sign-Off
<!-- ID: final_signoff -->

### Review Agent Verification

- [ ] All Phase 1 checklist items verified with proof
- [ ] All Phase 2 checklist items verified with proof
- [ ] All Phase 3 checklist items verified with proof
- [ ] All Phase 4 checklist items verified with proof
- [ ] All Phase 5 checklist items verified with proof
- [ ] All Phase 6 checklist items verified with proof

### Quality Gates

- [ ] No regressions in existing MCP tools
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Code follows project conventions
- [ ] Documentation is accurate and complete

### Sign-Off Record

| Role | Name | Date | Grade |
|------|------|------|-------|
| Architect | MyBB-ArchitectAgent | 2026-01-19 | N/A |
| Coder | | | |
| Review Agent | | | |
| Orchestrator | | | |

---

## Retro Notes
<!-- ID: retro_notes -->

*To be filled after project completion*

### What Went Well
-

### What Could Be Improved
-

### Lessons Learned
-

---

*Checklist created by MyBB-ArchitectAgent based on PHASE_PLAN.md task packages.*
