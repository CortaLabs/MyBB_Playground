# Research: MCP Tool Inventory & Prior Audits

## Executive Summary

Comprehensive catalog of 60+ MCP tools in MyBB MCP server across 12 categories. Prior ecosystem audit (390 entries) documented comprehensive MyBB hooks, plugin patterns, and database schema. Plugin-theme-manager can leverage all existing tools for plugin creation, deployment, and theme management—**zero new MCP tools required**.

**Key Findings:**
- **60+ verified MCP tools:** Templates (9), Themes (4), Plugins (11), Analysis (1), Tasks (6), Database (1), Content (16), Sync (5), Search (4), Admin (10), Moderation (8), Users (7)
- **Prior research complete:** MyBB hooks system, plugin patterns, admin modules, VSCode extension, MCP server, database schema all audited
- **Disk sync operational:** File watcher running, templates/stylesheets synced to disk automatically
- **Plugin lifecycle limitation documented:** Activation/deactivation via MCP manages cache only; full hook execution requires ACP intervention

---

## 1. Complete Tool Inventory

### Templates (9 tools)
`mybb_list_template_sets`, `mybb_list_templates`, `mybb_read_template`, `mybb_write_template`, `mybb_list_template_groups`, `mybb_template_find_replace`, `mybb_template_batch_read`, `mybb_template_batch_write`, `mybb_template_outdated`

**Relevance:** Template injection is core plugin deployment step. All template management automated.

### Themes/Stylesheets (4 tools)
`mybb_list_themes`, `mybb_list_stylesheets`, `mybb_read_stylesheet`, `mybb_write_stylesheet`

**Relevance:** Theme customization without manual ACP intervention.

### Plugin Development (6 tools)
`mybb_list_plugins`, `mybb_read_plugin`, `mybb_create_plugin`, `mybb_list_hooks`, `mybb_hooks_discover`, `mybb_hooks_usage`

**Relevance:** Core plugin scaffolding and hook integration. `mybb_create_plugin` is critical dependency.

### Plugin Analysis (1 tool)
`mybb_analyze_plugin`

**Relevance:** Audit plugin structure before management operations.

### Plugin Lifecycle (4 tools)
`mybb_plugin_list_installed`, `mybb_plugin_info`, `mybb_plugin_activate`, `mybb_plugin_deactivate`, `mybb_plugin_is_installed`

**Limitation:** Cache management only. Full hook execution requires manual ACP activation.

### Scheduled Tasks (6 tools)
`mybb_task_list`, `mybb_task_get`, `mybb_task_enable`, `mybb_task_disable`, `mybb_task_update_nextrun`, `mybb_task_run_log`

### Database (1 tool)
`mybb_db_query` (read-only SELECT queries)

### Content CRUD (16 tools)
Forums (5): `mybb_forum_list`, `mybb_forum_read`, `mybb_forum_create`, `mybb_forum_update`, `mybb_forum_delete`

Threads (6): `mybb_thread_list`, `mybb_thread_read`, `mybb_thread_create`, `mybb_thread_update`, `mybb_thread_delete`, `mybb_thread_move`

Posts (5): `mybb_post_list`, `mybb_post_read`, `mybb_post_create`, `mybb_post_update`, `mybb_post_delete`

### Disk Sync (5 tools)
`mybb_sync_export_templates`, `mybb_sync_export_stylesheets`, `mybb_sync_start_watcher`, `mybb_sync_stop_watcher`, `mybb_sync_status`

**Status:** Already implemented, file watcher running in development.

### Search (4 tools)
`mybb_search_posts`, `mybb_search_threads`, `mybb_search_users`, `mybb_search_advanced`

### Admin (10 tools)
Settings (4): `mybb_setting_get`, `mybb_setting_set`, `mybb_setting_list`, `mybb_settinggroup_list`

Cache (4): `mybb_cache_read`, `mybb_cache_rebuild`, `mybb_cache_list`, `mybb_cache_clear`

Statistics (2): `mybb_stats_forum`, `mybb_stats_board`

### Moderation (8 tools)
`mybb_mod_close_thread`, `mybb_mod_stick_thread`, `mybb_mod_approve_thread`, `mybb_mod_approve_post`, `mybb_mod_soft_delete_thread`, `mybb_mod_soft_delete_post`, `mybb_modlog_list`, `mybb_modlog_add`

### User Management (7 tools)
`mybb_user_get`, `mybb_user_list`, `mybb_user_update_group`, `mybb_user_ban`, `mybb_user_unban`, `mybb_usergroup_list`

---

## 2. Prior Research Findings Summary

### MyBB Ecosystem Audit (390 entries)
Comprehensive investigation completed 13+ hours ago covering:
1. **Hooks System** - Hook categories, execution lifecycle, plugin attachment patterns
2. **Admin CP** - Module structure, settings, user/forum/plugin/theme management
3. **Plugin Patterns** - Structure compliance, APIs (settings, templates, database, tasks)
4. **VSCode Extension** - Feature parity comparison with MCP tools
5. **MCP Server** - 20+ tools audited, architecture, security measures
6. **Database Schema** - Complete table structure, relationships, MCP coverage gaps
7. **Admin Modules** - Directory organization (index.php, modules/, inc/, styles/)

**Confidence Levels:**
- Hook system: 0.90+
- Plugin patterns: 0.92+
- Database schema: 0.95+

---

## 3. Critical Tools for Plugin-Theme Manager

| Tool | Purpose | Priority |
|------|---------|----------|
| `mybb_create_plugin` | Scaffold plugins | CRITICAL |
| `mybb_list_plugins` | Enumerate plugins | CRITICAL |
| `mybb_analyze_plugin` | Audit structure | CRITICAL |
| `mybb_plugin_activate` | Enable plugins | CRITICAL |
| `mybb_plugin_deactivate` | Disable plugins | CRITICAL |
| `mybb_list_templates` | Find templates | HIGH |
| `mybb_write_template` | Deploy templates | HIGH |
| `mybb_read_stylesheet` | Inspect CSS | HIGH |
| `mybb_write_stylesheet` | Deploy CSS | HIGH |
| `mybb_setting_set` | Configure settings | HIGH |
| `mybb_cache_rebuild` | Verify deployment | HIGH |

---

## 4. Plugin Deployment Workflow

1. Create plugin scaffold via `mybb_create_plugin`
2. Inject templates via `mybb_write_template`
3. Inject CSS via `mybb_write_stylesheet`
4. Configure settings via `mybb_setting_set`
5. Add to cache via `mybb_plugin_activate`
6. **MANUAL:** Activate through ACP to trigger `_activate()` hooks
7. Verify via `mybb_cache_rebuild` and `mybb_stats_board`

---

## 5. Plugin Structure Compliance (from prior audit)

Required functions:
- `{codename}_info()` - Metadata
- `{codename}_activate()` - Called via ACP only
- `{codename}_deactivate()` - Called via ACP only
- `{codename}_install()` - Setup (tables, settings, templates)
- `{codename}_uninstall()` - Cleanup
- `{codename}_is_installed()` - Status check

Template inheritance (SID model):
- SID = -2: Master templates (base)
- SID = -1: Global templates (shared)
- SID >= 1: Custom overrides

---

## 6. Limitations & Constraints

**Activation Limitation:**
- MCP tools manage cache only
- Full hook execution requires manual ACP intervention
- `_activate()` and `_deactivate()` PHP functions NOT invoked via MCP

**Database Access:**
- `mybb_db_query` is read-only
- Custom plugin tables created during installation only
- No ALTER TABLE support via MCP

**Template Deployment:**
- Must match existing template sets (SID)
- Template inheritance managed automatically
- Custom templates override master versions

---

## 7. Architecture Opportunity: Public/Private Isolation

Current MCP tools lack repository-level isolation. Plugin-theme-manager should add:
- **Public registry:** Curated, vetted plugins
- **Private storage:** Internal plugins only
- **SQLite metadata:** Versions, dependencies, status

**Implementation:** Build on existing tools—zero new MCP tools required.

---

## 8. Code References

| File | Purpose | Lines |
|------|---------|-------|
| `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/server.py` | All 60+ MCP tool definitions | 2839 |
| `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/db/connection.py` | Database layer | TBD |
| `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/sync/service.py` | Disk sync implementation | TBD |
| `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/tools/plugins.py` | Plugin scaffolding templates | TBD |

---

## 9. Unverified Findings

- **UNVERIFIED:** Exact ecosystem audit research document locations
- **UNVERIFIED:** Complete MyBB hooks list (discovery tools exist)
- **UNVERIFIED:** VSCode extension vs MCP feature parity details
- **UNVERIFIED:** Performance implications of bulk template operations

---

## 10. Confidence Assessment

| Finding | Confidence | Evidence |
|---------|-----------|----------|
| 60+ tools available | 0.99 | Direct server.py inspection |
| Tool categories | 0.98 | Tool definitions extracted |
| Activation limitation | 0.95 | Documented in tool descriptions |
| Ecosystem audit scope | 0.90 | 390 log entries reviewed |
| Plugin patterns | 0.92 | Prior audit findings |
| Database schema mapped | 0.95 | Prior audit research |

---

## 11. Handoff for Architect

**Critical Design Points:**
1. **Activation Limitation is Real:** Plan for manual ACP step or investigate hook invocation patterns
2. **Disk Sync Works Now:** Leverage existing file watcher for git integration
3. **Template SID Model:** Public/private isolation must work within existing constraints
4. **Zero New Tools Required:** All functionality builds on 60+ existing tools

**Recommended Architecture:**
1. Build SQLite metadata layer on existing tools
2. Implement public/private registry as file-based storage
3. Create orchestration layer combining MCP tools into workflows
4. Leverage disk sync for file-based versioning

---

**Created:** 2026-01-18 03:47 UTC
**Agent:** Research-Audits
**Project:** plugin-theme-manager
**Status:** COMPLETE
**Next:** Architect phase
