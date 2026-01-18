# Acceptance Checklist - MyBB Ecosystem Enhancement
**Author:** ArchitectAgent
**Version:** v1.0
**Status:** Approved
**Last Updated:** 2026-01-17 14:32 UTC

> Implementation checklist for MyBB MCP enhancement. Each task includes acceptance criteria and verification method.

---

## Documentation Hygiene
<!-- ID: documentation_hygiene -->

- [x] Architecture guide updated (proof: ARCHITECTURE_GUIDE.md v1.0, 775 lines)
- [x] Phase plan current (proof: PHASE_PLAN.md v1.0, 409 lines)
- [x] Research documents reviewed (proof: 8 research docs synthesized)
- [ ] README.md updated with new tools
- [ ] CHANGELOG.md updated with version history

---

## Phase 0: Security Remediation (BLOCKING)
<!-- ID: phase_0 -->

### TP-0.1: Asyncio Threading Fix
**Source:** RESEARCH_MyBB_MCP_Security_Audit_20260117_1405.md (Finding #1)
**Confidence:** 0.95

- [ ] Replace asyncio.run() at watcher.py:150 with run_coroutine_threadsafe
- [ ] Replace asyncio.run() at watcher.py:180 with run_coroutine_threadsafe
- [ ] Replace asyncio.run() at watcher.py:189 with run_coroutine_threadsafe
- [ ] Implement dedicated event loop on worker thread
- [ ] Add cleanup logic for worker thread on shutdown
- [ ] **Verification:** Unit test with 10+ rapid file modifications passes
- [ ] **Verification:** No RuntimeError on concurrent file changes

### TP-0.2: Database Password Security
**Source:** RESEARCH_MyBB_MCP_Security_Audit_20260117_1405.md (Finding #2)
**Confidence:** 0.90

- [ ] Remove empty password default at config.py:45
- [ ] Add ValueError with clear message if password not set
- [ ] Update .env.example to document MYBB_DB_PASS requirement
- [ ] **Verification:** MCP server fails to start without MYBB_DB_PASS
- [ ] **Verification:** Error message clearly states password is required

### TP-0.3: Connection Pooling
**Source:** RESEARCH_MyBB_MCP_Security_Audit_20260117_1405.md (Finding #3)
**Confidence:** 0.85

- [ ] Import MySQLConnectionPool from mysql.connector.pooling
- [ ] Replace single connection with pool (pool_size=5)
- [ ] Add context manager for connection borrowing
- [ ] Configure timeouts (connect: 10s, read: 30s)
- [ ] Add retry logic for transient failures
- [ ] **Verification:** Connection pool creates 5 connections
- [ ] **Verification:** Concurrent operations work without conflicts

### TP-0.4: Error Handling Enhancement
**Source:** RESEARCH_MyBB_MCP_Security_Audit_20260117_1405.md (Finding #4)
**Confidence:** 0.80

- [ ] Create custom exception hierarchy (MCPError, DatabaseError, ValidationError)
- [ ] Replace generic Exception catches with specific types
- [ ] Add error codes and structured error responses
- [ ] Preserve stack traces for debugging
- [ ] **Verification:** Database errors return DatabaseError with code

### TP-0.5: Security Test Suite
**Source:** All security research findings

- [ ] Create tests/test_security.py
- [ ] Test password requirement enforcement
- [ ] Test connection pool behavior under load
- [ ] Test thread-safe async operations
- [ ] Test error handling for edge cases
- [ ] Test SQL injection vectors (parameterized queries)
- [ ] **Verification:** All security tests pass
- [ ] **Verification:** Coverage > 80% for security-critical paths

### Phase 0 Gate
- [ ] All 5 task packages completed
- [ ] All security tests pass
- [ ] No critical/high severity issues in code review
- [ ] MCP server starts and basic operations work
- [ ] Performance regression < 10%

---

## Phase 1: Foundation Enhancement
<!-- ID: phase_1 -->

### TP-1.1: Plugin Creator - Settings Enhancement
**Source:** RESEARCH_MYBB_PLUGIN_PATTERNS_20260117_1405.md (Finding #1)
**Confidence:** 0.98

- [ ] Add rebuild_settings() call in generated activate() function
- [ ] Add rebuild_settings() call in generated uninstall() function (after deleting settings)
- [ ] Generate proper settings group creation with disporder
- [ ] Add setting type validation (text, numeric, select, etc.)
- [ ] **Verification:** Generated plugin includes rebuild_settings() calls
- [ ] **Verification:** Settings properly created on activate

### TP-1.2: Plugin Creator - Multi-DB Support
**Source:** RESEARCH_MYBB_PLUGIN_PATTERNS_20260117_1405.md (Finding #2)
**Confidence:** 0.90

- [ ] Add db_support parameter (default: ["mysql", "pgsql", "sqlite"])
- [ ] Generate switch statement for db_type in install() function
- [ ] Include proper syntax for MySQL (AUTO_INCREMENT)
- [ ] Include proper syntax for PostgreSQL (SERIAL)
- [ ] Include proper syntax for SQLite (AUTOINCREMENT)
- [ ] **Verification:** Generated plugin includes multi-DB switch statement

### TP-1.3: Plugin Creator - Security Boilerplate
**Source:** RESEARCH_MYBB_PLUGIN_PATTERNS_20260117_1405.md (Finding #3)
**Confidence:** 0.95

- [ ] Add IN_MYBB check at file start (always generated)
- [ ] Add security_level parameter ("minimal", "standard", "strict")
- [ ] Standard level: Add verify_post_check() template for forms
- [ ] Strict level: Add input validation helpers
- [ ] **Verification:** Generated plugin includes IN_MYBB check

### TP-1.4: Plugin Creator - Template Caching
**Source:** RESEARCH_MYBB_PLUGIN_PATTERNS_20260117_1405.md (Finding #4)
**Confidence:** 0.92

- [ ] When has_templates=True, generate $templatelist hook at file level
- [ ] Include comma-separated template names in global_start hook
- [ ] Document template caching benefit in generated comments
- [ ] **Verification:** Generated plugin includes $templatelist assignment

### TP-1.5: Plugin Creator - Hook Priority
**Source:** RESEARCH_MyBB_Hooks_System_20260117_1406.md
**Confidence:** 0.95

- [ ] Change hooks parameter to accept objects: [{"name": "hook_name", "priority": 10}]
- [ ] Maintain backward compatibility with string array
- [ ] Generate add_hook() calls with priority parameter
- [ ] **Verification:** String array still works (backward compatible)
- [ ] **Verification:** Object array generates correct priority

### TP-1.6: Template Tools - find_replace
**Source:** RESEARCH_MyBB_Template_System_20260117_1407.md (Finding #7)
**Confidence:** 0.97

- [ ] Create tools/templates.py module
- [ ] Implement mybb_find_replace_template(title, find_regex, replace, autocreate, sid)
- [ ] Support regex patterns for find
- [ ] Auto-create custom template if not exists (when autocreate=True)
- [ ] Apply to all template sets or specific sid
- [ ] **Verification:** Find and replace works with simple strings
- [ ] **Verification:** Regex patterns work correctly

### TP-1.7: Template Tools - Batch Operations
**Source:** RESEARCH_MyBB_Template_System_20260117_1407.md (Finding #5)
**Confidence:** 0.90

- [ ] Add mybb_batch_write_templates(templates: list) tool
- [ ] Use single transaction for atomicity
- [ ] Return detailed results per template
- [ ] Limit batch size (max 100 templates)
- [ ] **Verification:** Batch of 10 templates writes in single transaction
- [ ] **Verification:** Failure rolls back all changes

### TP-1.8: Template Tools - Diff/Outdated
**Source:** RESEARCH_MyBB_Template_System_20260117_1407.md (Finding #6)
**Confidence:** 0.85

- [ ] Add mybb_diff_template(title, sid) tool
- [ ] Add mybb_list_outdated_templates(sid) tool
- [ ] Use unified diff format for output
- [ ] Include line numbers and context
- [ ] **Verification:** Diff shows additions/removals clearly

### TP-1.9: Hook System - Dynamic Discovery
**Source:** RESEARCH_MyBB_Hooks_System_20260117_1406.md
**Confidence:** 0.95

- [ ] Create tools/hooks.py module
- [ ] Implement mybb_discover_hooks(mybb_root) tool
- [ ] Parse all PHP files for $plugins->run_hooks() calls
- [ ] Extract hook name, file, line number
- [ ] Categorize hooks by file/module
- [ ] Cache results (refresh on demand)
- [ ] **Verification:** Discovers 200+ hooks from MyBB codebase
- [ ] **Verification:** Performance < 5s for full scan

### TP-1.10: Hook System - Enhanced Categories
**Source:** RESEARCH_MyBB_Hooks_System_20260117_1406.md
**Confidence:** 1.0

- [ ] Add editpost category (7 hooks)
- [ ] Add parser category (6 hooks)
- [ ] Add moderation category (30+ hooks)
- [ ] Update list_hooks to use discovered hooks as source
- [ ] **Verification:** All 15 categories available

### Phase 1 Gate
- [ ] All 10 task packages completed
- [ ] Plugin creator generates complete, working plugins
- [ ] Template tools work for find/replace and batch operations
- [ ] Hook discovery returns 200+ hooks
- [ ] All tests pass (unit + integration)

---

## Phase 2: Content Management
<!-- ID: phase_2 -->

### TP-2.1: Forums CRUD
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority: 9)
**Confidence:** 0.95

- [ ] Create tools/content.py module
- [ ] Implement mybb_list_forums(parent_id, include_categories)
- [ ] Implement mybb_read_forum(fid)
- [ ] Implement mybb_create_forum(name, description, type, parent_id, disporder, properties)
- [ ] Implement mybb_update_forum(fid, name, description, properties)
- [ ] Respect forum hierarchy (parent_id relationships)
- [ ] **Verification:** List returns all forums with hierarchy
- [ ] **Verification:** Create works for both forums and categories

### TP-2.2: Threads CRUD
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority: 11)
**Confidence:** 0.90

- [ ] Implement mybb_list_threads(fid, filters, limit)
- [ ] Implement mybb_read_thread(tid) (includes first post)
- [ ] Implement mybb_create_thread(fid, subject, message, author_uid, options)
- [ ] Implement mybb_update_thread(tid, subject, options)
- [ ] Use PostDataHandler validation pattern for creation
- [ ] **Verification:** Thread and first post created atomically
- [ ] **Verification:** Create thread validates all required fields

### TP-2.3: Posts CRUD
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority: 11)
**Confidence:** 0.90

- [ ] Implement mybb_list_posts(tid, filters, limit)
- [ ] Implement mybb_read_post(pid)
- [ ] Implement mybb_create_post(tid, message, author_uid, options)
- [ ] Implement mybb_update_post(pid, message, options)
- [ ] Use PostDataHandler validation (flooding, permissions, merge)
- [ ] **Verification:** Create post validates all required fields
- [ ] **Verification:** Post appears in thread correctly

### TP-2.4: Search Functionality
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority: 8)
**Confidence:** 0.85

- [ ] Implement mybb_search_posts(query, fid, uid, filters)
- [ ] Implement mybb_search_threads(query, fid, filters)
- [ ] Implement mybb_search_users(query, filters)
- [ ] Respect permission system in results
- [ ] Use cursor-based pagination
- [ ] **Verification:** Permissions respected (no private content leaked)

### TP-2.5: Content Integration Tests
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md

- [ ] Create tests/test_content.py
- [ ] Test full workflow: create forum -> create thread -> create post
- [ ] Test search after content creation
- [ ] Test permission enforcement
- [ ] Test error handling for invalid data
- [ ] Test concurrent operations
- [ ] **Verification:** Workflow tests complete in < 10s

### Phase 2 Gate
- [ ] All 5 task packages completed
- [ ] Forum/thread/post CRUD works correctly
- [ ] Search returns relevant results
- [ ] Permission system respected
- [ ] All tests pass (unit + integration + security)

---

## Phase 3: Admin Operations
<!-- ID: phase_3 -->

### TP-3.1: Settings Management
**Source:** RESEARCH_AdminCP_MCP_Expansion_20260117_1404.md (Tier 1)
**Confidence:** 0.95

- [ ] Create tools/admin.py module
- [ ] Implement mybb_list_setting_groups()
- [ ] Implement mybb_create_setting_group(name, title, description, disporder)
- [ ] Implement mybb_list_settings(gid)
- [ ] Implement mybb_get_setting(name)
- [ ] Implement mybb_update_setting(name, value)
- [ ] Trigger cache rebuild after setting changes
- [ ] **Verification:** Get/update setting works
- [ ] **Verification:** Cache properly rebuilt

### TP-3.2: Cache Management
**Source:** RESEARCH_AdminCP_MCP_Expansion_20260117_1404.md (Tier 1)
**Confidence:** 0.95

- [ ] Implement mybb_list_caches()
- [ ] Implement mybb_view_cache(cache_name)
- [ ] Implement mybb_rebuild_cache(cache_name)
- [ ] Implement mybb_rebuild_all_caches()
- [ ] Use MyBB datacache table
- [ ] **Verification:** Rebuild all caches works

### TP-3.3: Plugin Lifecycle
**Source:** RESEARCH_AdminCP_MCP_Expansion_20260117_1404.md (Tier 1)
**Confidence:** 0.95

- [ ] Implement mybb_activate_plugin(codename)
- [ ] Implement mybb_deactivate_plugin(codename)
- [ ] Implement mybb_install_plugin(codename)
- [ ] Implement mybb_uninstall_plugin(codename)
- [ ] Implement mybb_get_plugin_status(codename)
- [ ] Call appropriate plugin hooks on lifecycle changes
- [ ] **Verification:** Activate enables plugin hooks

### TP-3.4: Database Backup
**Source:** RESEARCH_AdminCP_MCP_Expansion_20260117_1404.md (Tier 1)
**Confidence:** 0.95

- [ ] Implement mybb_create_backup(tables, compress, method)
- [ ] Implement mybb_list_backups()
- [ ] Implement mybb_download_backup(filename)
- [ ] Implement mybb_delete_backup(filename)
- [ ] Store in admin/backups/ directory
- [ ] Support gzip compression
- [ ] **Verification:** Create backup generates valid SQL dump

### TP-3.5: Scheduled Tasks
**Source:** RESEARCH_AdminCP_MCP_Expansion_20260117_1404.md (Tier 2)
**Confidence:** 0.90

- [ ] Implement mybb_list_tasks()
- [ ] Implement mybb_create_task(file, title, interval, enabled, properties)
- [ ] Implement mybb_update_task(tid, interval, enabled, properties)
- [ ] Implement mybb_delete_task(tid)
- [ ] Implement mybb_run_task(tid)
- [ ] **Verification:** Run task executes immediately

### TP-3.6: Moderation Tools
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority: 6)
**Confidence:** 0.85

- [ ] Create tools/moderation.py module
- [ ] Implement mybb_moderate_close_thread(tid)
- [ ] Implement mybb_moderate_open_thread(tid)
- [ ] Implement mybb_moderate_stick_thread(tid)
- [ ] Implement mybb_moderate_move_thread(tid, fid)
- [ ] Implement mybb_moderate_delete_post(pid, soft)
- [ ] Implement mybb_moderate_approve_thread(tid)
- [ ] Wrap class_moderation.php methods
- [ ] **Verification:** All operations logged to modlog

### TP-3.7: User Management (Basic)
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority: 7)
**Confidence:** 0.80

- [ ] Create tools/users.py module
- [ ] Implement mybb_list_users(filters, limit)
- [ ] Implement mybb_read_user(uid)
- [ ] Implement mybb_create_user(username, email, password, usergroup_id, properties)
- [ ] Implement mybb_update_user(uid, email, usergroup, properties)
- [ ] Implement mybb_list_usergroups()
- [ ] Use UserDataHandler for validation
- [ ] **Verification:** Password properly hashed

### TP-3.8: Statistics Tools
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority: 5)
**Confidence:** 0.85

- [ ] Implement mybb_get_forum_stats()
- [ ] Implement mybb_get_thread_stats(tid)
- [ ] Implement mybb_get_user_stats(uid)
- [ ] Cache results for performance
- [ ] **Verification:** Forum stats returns accurate counts

### Phase 3 Gate
- [ ] All 8 task packages completed
- [ ] Settings management works correctly
- [ ] Plugin lifecycle works correctly
- [ ] Backup/cache/task tools work correctly
- [ ] Basic moderation and user tools work correctly
- [ ] All tests pass

---

## Phase 4: Advanced Features (Optional)
<!-- ID: phase_4 -->

### TP-4.1: Testing & Validation Tools
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority: 4)
**Confidence:** 0.75

- [ ] Create tools/testing.py module
- [ ] Implement mybb_validate_plugin(plugin_name)
- [ ] Implement mybb_validate_template(template_content)
- [ ] Implement mybb_validate_permissions(uid, fid, action)
- [ ] Implement mybb_run_integrity_check()
- [ ] **Verification:** Plugin validation catches common errors

### TP-4.2: Migration Tools
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority: 3)
**Confidence:** 0.70

- [ ] Create tools/migration.py module
- [ ] Implement mybb_import_users(data, mapping)
- [ ] Implement mybb_import_threads(data, mapping)
- [ ] Implement mybb_export_forum_structure()
- [ ] Support JSON and CSV formats
- [ ] **Verification:** Import validates all data

### TP-4.3: Performance Monitoring
**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority: 2)
**Confidence:** 0.70

- [ ] Create tools/monitoring.py module
- [ ] Implement mybb_get_query_log(limit)
- [ ] Implement mybb_get_cache_stats()
- [ ] Implement mybb_get_connection_stats()
- [ ] **Verification:** Query log captures recent queries

### TP-4.4: VSCode Integration Alignment
**Source:** RESEARCH_VSCode_Extension_Audit_20260117_1406.md
**Confidence:** 0.80

- [ ] Ensure cache refresh works for all template/stylesheet changes
- [ ] Add HTTP request logging for debugging
- [ ] Document VSCode extension integration patterns
- [ ] Test with VSCode extension if available
- [ ] **Verification:** Template changes refresh MyBB cache

### Phase 4 Gate
- [ ] All Phase 4 task packages completed (optional)
- [ ] All documentation updated
- [ ] Full test coverage maintained
- [ ] Performance benchmarks met
- [ ] No regression from prior phases

---

## Final Verification
<!-- ID: final_verification -->

- [ ] All phase gate criteria met
- [ ] All checklist items checked with proofs attached
- [ ] All tests pass (unit, integration, security)
- [ ] Documentation complete and accurate
- [ ] Stakeholder sign-off recorded (name + date)
- [ ] Retro completed and lessons learned documented

---

## Summary Statistics

| Phase | Task Packages | Total Tasks | Estimated Effort |
|-------|---------------|-------------|------------------|
| Phase 0 | 5 | 28 | 5-7 days |
| Phase 1 | 10 | 45 | 10-15 days |
| Phase 2 | 5 | 26 | 10-15 days |
| Phase 3 | 8 | 42 | 15-20 days |
| Phase 4 | 4 | 18 | 10-20 days (optional) |
| **Total** | **32** | **159** | **10-14 weeks** |

---

## Source References

All checklist items trace back to one of 8 research documents:

1. RESEARCH_MyBB_MCP_Security_Audit_20260117_1405.md (Phase 0)
2. RESEARCH_MYBB_PLUGIN_PATTERNS_20260117_1405.md (Phase 1)
3. RESEARCH_MyBB_Template_System_20260117_1407.md (Phase 1)
4. RESEARCH_MyBB_Hooks_System_20260117_1406.md (Phase 1)
5. RESEARCH_MYBB_DATABASE_SCHEMA_20260117_1410.md (Phase 2-3)
6. RESEARCH_AdminCP_MCP_Expansion_20260117_1404.md (Phase 3)
7. RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Phase 2-4)
8. RESEARCH_VSCode_Extension_Audit_20260117_1406.md (Phase 4)

---

**Document Status:** Approved for Implementation
**Implementation Ready:** Yes - begin with Phase 0
