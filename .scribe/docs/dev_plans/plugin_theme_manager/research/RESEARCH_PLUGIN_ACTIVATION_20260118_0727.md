# Research: MyBB Plugin Activation Flow

**Date:** 2026-01-18 07:27 UTC
**Scoped to:** plugin-theme-manager
**Research Goal:** Understand MyBB plugin activation flow, existing MCP capabilities, plugin lifecycle requirements, and safety considerations for automated plugin activation.

---

## Executive Summary

MyBB plugin activation is a two-stage process triggered through the Admin CP (`TestForum/admin/modules/config/plugins.php`). The activation flow calls PHP functions in sequence: first `_install()` (if not already installed), then `_activate()`. Deactivation optionally calls `_uninstall()`. All changes are tracked via cache updates.

**Key Finding:** Existing MCP tools support template and settings management but NOT direct database table creation (db_query is read-only). Full plugin activation requires executing PHP functions through MyBB's infrastructure.

---

## 1. MyBB Plugin Activation Flow

### Source Code Reference
**File:** `TestForum/admin/modules/config/plugins.php` (lines 376-482)

### Activation Process (Action == "activate")

1. **Verification**: Post key verification (CSRF protection)
2. **Hook Execution**: `admin_config_plugins_activate` hook runs
3. **File Validation**: Plugin file existence check in `/inc/plugins/`
4. **Cache Loading**: Read current active plugins from cache
5. **Plugin Inclusion**: `require_once` the plugin PHP file
6. **Installation Check**: Call `{codename}_is_installed()` to determine if plugin has been installed before
7. **Conditional Installation**: If NOT installed AND `{codename}_install()` exists:
   - Call `{codename}_install()`
   - Sets message to "success_plugin_installed"
   - Sets `$install_uninstall = true` for logging
8. **Activation**: If `{codename}_activate()` exists:
   - Call `{codename}_activate()`
9. **Cache Update**: Add plugin to active_plugins array, update plugins_cache
10. **Logging**: `log_admin_action()` logs the action
11. **Post-Activation Hook**: `admin_config_plugins_activate_commit` hook runs
12. **Redirect**: Flash success message and redirect to plugins list

### Deactivation Process (Action == "deactivate")

1. **Verification**: Post key verification (CSRF protection)
2. **Hook Execution**: `admin_config_plugins_deactivate` hook runs
3. **Deactivation**: If `{codename}_deactivate()` exists:
   - Call `{codename}_deactivate()`
4. **Conditional Uninstallation**: If `uninstall=1` parameter AND `{codename}_uninstall()` exists:
   - Call `{codename}_uninstall()`
   - Sets message to "success_plugin_uninstalled"
   - Sets `$install_uninstall = true` for logging
5. **Cache Update**: Remove plugin from active_plugins array
6. **Logging**: `log_admin_action()` logs the action
7. **Post-Deactivation Hook**: `admin_config_plugins_deactivate_commit` hook runs
8. **Redirect**: Flash message and redirect

### Relevant MyBB Hooks

- `admin_config_plugins_activate` - Before activation begins
- `admin_config_plugins_activate_commit` - After cache update, before redirect
- `admin_config_plugins_deactivate` - Before deactivation begins
- `admin_config_plugins_deactivate_commit` - After cache update, before redirect

---

## 2. Plugin Lifecycle Functions

Examined two example plugins: `hello.php` (589 lines, comprehensive) and `hello_banner.php` (118 lines, minimal).

### 2.1 Required Function: `{codename}_info()`

**Purpose:** Metadata about the plugin
**Return:** Array with keys:
- `name` - Display name
- `description` - What plugin does
- `website` - Optional
- `author` - Plugin creator
- `authorsite` - Optional
- `version` - Version number
- `compatibility` - CSV of supported MyBB versions (e.g., '18*')
- `codename` - Unique identifier

**Note:** This function is called to get plugin metadata but is NOT part of the activation flow.

### 2.2 Required Function: `{codename}_is_installed()`

**Purpose:** Determine if plugin needs installation
**Behavior:**
- Called during activation to check if `_install()` should be executed
- Return `true` if plugin is installed, `false` otherwise
- Typically checks for database table existence or other permanent markers
- **Example:** `hello.php` checks if table `mybb_hello_messages` exists

**Implementation Pattern:**
```php
function hello_is_installed()
{
    global $db;
    return $db->table_exists('hello_messages');
}
```

### 2.3 Installation Function: `{codename}_install()`

**Purpose:** Set up plugin infrastructure (database tables, initial data)
**Executed:** Only on first activation, if `_is_installed()` returns false
**Typical Tasks:**
- Create database tables with collation (`$db->build_create_table_collation()`)
- Handle database type differences (MySQL, PostgreSQL, SQLite)
- Create initial records or configuration

**Example from hello.php (lines 353-387):**
```php
function hello_install()
{
    global $db;
    $collation = $db->build_create_table_collation();

    if(!$db->table_exists('hello_messages'))
    {
        switch($db->type) {
            case "pgsql":
                // PostgreSQL syntax
            case "sqlite":
                // SQLite syntax
            default:
                // MySQL syntax
                $db->write_query("CREATE TABLE ...");
        }
    }
}
```

**Critical Detail:** Uses `$db->write_query()` directly for DDL, not through parameterized queries (standard for DDL in MyBB).

### 2.4 Activation Function: `{codename}_activate()`

**Purpose:** Make plugin visible/functional (enable features, add templates, add settings)
**Executed:** After successful installation (or if already installed), on every activation
**Typical Tasks:**
- Insert/update templates via `$db->insert_query('templates', $template_array)` or `$db->update_query()`
- Create template groups via `$db->insert_query('templategroups', $group)`
- Create settings via `$db->insert_query('settings', $setting_array)`
- Create setting groups via `$db->insert_query('settinggroups', $group)`

**Example from hello.php (lines 91-220):**
- Inserts or updates template group `hello`
- Creates/updates master templates (sid=-2): `hello`, `hello_index`, `hello_post`, `hello_message`
- Template version handling: Sets `version=0` for custom templates to mark them outdated

**Important Pattern:** Checks for existing templates and handles duplicates (due to PluginLibrary bugs).

### 2.5 Deactivation Function: `{codename}_deactivate()`

**Purpose:** Hide/disable plugin features
**Executed:** When plugin is deactivated
**Typical Tasks:**
- Remove/revert template changes using `find_replace_templatesets()`
- Update templates to remove plugin modifications
- Clear plugin-specific data (though usually not database cleanup)

**Note:** Typically does NOT delete templates or data - that's for uninstall.

### 2.6 Uninstallation Function: `{codename}_uninstall()`

**Purpose:** Complete cleanup - remove all plugin traces
**Executed:** Only when deactivating WITH uninstall=1 parameter
**Typical Tasks:**
- Delete template groups: `$db->delete_query('templategroups', "prefix='hello'")`
- Delete templates: `$db->delete_query('templates', "title LIKE 'hello_%'")`
- Delete setting groups: `$db->delete_query('settinggroups', "name='hello'")`
- Delete settings: `$db->delete_query('settings', "name IN (...)")`
- Drop database tables: `$db->write_query("DROP TABLE ...")`

**Example from hello.php (lines 408-432):**
```php
function hello_uninstall()
{
    // Delete template groups
    $db->delete_query('templategroups', "prefix='hello'");

    // Delete all hello templates
    $db->delete_query('templates', "title='hello' OR title LIKE 'hello_%'");

    // Delete settings
    $db->delete_query('settinggroups', "name='hello'");
    $db->delete_query('settings', "name IN ('hello_display1','hello_display2')");

    // Drop database table
    $db->write_query("DROP TABLE ".TABLE_PREFIX."hello_messages");
}
```

---

## 3. Existing MCP Tools Audit

### Template Management Tools (9 tools)

| Tool | Purpose | MCP-Integrated | Notes |
|------|---------|---|---|
| `mybb_write_template` | Create/update templates | YES | Auto-handles sid=-2 vs custom inheritance |
| `mybb_read_template` | Read template content | YES | Shows both master and custom versions |
| `mybb_list_templates` | Query templates by sid/search | YES | Filter by template set |
| `mybb_list_template_groups` | List template group categories | YES | Basic listing |
| `mybb_template_find_replace` | Regex find/replace across sets | YES | Mirrors MyBB's find_replace_templatesets() |
| `mybb_template_batch_read` | Read multiple templates at once | YES | Efficiency tool |
| `mybb_template_batch_write` | Write multiple templates atomically | YES | All-or-nothing operation |
| `mybb_template_outdated` | Find templates differing from master | YES | After MyBB upgrades |
| `mybb_sync_export_templates` | Export templates to disk | YES | For disk-sync feature |

**Capability Summary:** FULL template management available via MCP. Plugins can insert/modify templates reliably.

### Settings Management Tools (4 tools)

| Tool | Purpose | Available | Notes |
|------|---------|---|---|
| `mybb_setting_get` | Retrieve single setting | YES | By name |
| `mybb_setting_set` | Update single setting | YES | Auto-rebuilds settings cache |
| `mybb_setting_list` | List all/filtered settings | YES | Filter by group ID |
| `mybb_settinggroup_list` | List setting groups | YES | Category listing |

**Capability Summary:** Settings RETRIEVAL available, but NO MCP tool for creating NEW settings or setting groups. Plugin activation creates settings via `_activate()` function.

### Cache Management Tools (4 tools)

| Tool | Purpose | Available | Notes |
|------|---------|---|---|
| `mybb_cache_read` | Read cache entry | YES | Returns serialized PHP data |
| `mybb_cache_rebuild` | Rebuild specific cache type | YES | Defaults to 'all' |
| `mybb_cache_list` | List all cache entries | YES | With sizes |
| `mybb_cache_clear` | Clear specific/all cache | YES | Generic clear operation |

**Capability Summary:** Cache management available. Critical cache: `plugins` cache updated during activation.

### Database Tools (1 tool)

| Tool | Purpose | Limitation |
|------|---------|---|
| `mybb_db_query` | Execute SQL query | **READ-ONLY, SELECT-only** |

**Critical Limitation:** No MCP tool exists for:
- CREATE TABLE statements
- INSERT/UPDATE/DELETE queries
- ALTER TABLE operations
- Database DDL/DML

**Implication:** Database table creation and modification MUST occur through plugin's `_install()` and `_uninstall()` PHP functions via MyBB infrastructure.

### Plugin Management Tools (7 tools)

| Tool | Purpose | Limitation |
|------|---------|---|
| `mybb_list_plugins` | List all plugins | Query only |
| `mybb_create_plugin` | Create new plugin scaffolding | Creates filesystem only |
| `mybb_plugin_list_installed` | List active plugins | Cache-based query |
| `mybb_plugin_info` | Get plugin metadata | Parsing only |
| `mybb_plugin_activate` | Activate plugin | **CACHE-ONLY, does NOT execute PHP** |
| `mybb_plugin_deactivate` | Deactivate plugin | **CACHE-ONLY, does NOT execute PHP** |
| `mybb_plugin_is_installed` | Check installation status | Queries cache |

**Critical Limitation:** `mybb_plugin_activate` and `mybb_plugin_deactivate` only manipulate the cache. They do NOT:
- Execute `_install()` function
- Execute `_activate()` or `_deactivate()` function
- Execute `_uninstall()` function
- Create templates
- Create database tables
- Update settings

**Implication:** These tools cannot fully activate/deactivate a plugin. Full activation requires PHP execution through MyBB's Admin CP or custom PHP code that calls the plugin functions directly.

---

## 4. Plugin Activation Requirements Summary

Based on `hello.php` analysis, a complete plugin activation typically:

### At Installation (`_install()`)
1. Check database type (MySQL, PostgreSQL, SQLite)
2. Build collation string
3. Create necessary database tables
4. Create initial data records

### At Activation (`_activate()`)
1. Create or update template groups in `templategroups` table
2. Query existing templates to handle deduplication
3. Insert/update templates in `templates` table with proper sid values:
   - sid=-2: Master template (core)
   - sid=0: Global template (shared across all sets)
   - sid=1+: Template set override
4. Set version=0 for custom templates to mark as outdated
5. Create settings groups in `settinggroups` table
6. Create settings in `settings` table
7. Add hooks via `$plugins->add_hook()`

### At Deactivation (`_deactivate()`)
1. Optionally revert template changes using find_replace_templatesets()
2. Update templates to remove plugin references
3. NOT typically full cleanup - that's for uninstall

### At Uninstallation (`_uninstall()`)
1. Delete template groups
2. Delete all plugin templates
3. Delete setting groups
4. Delete settings
5. Drop database tables
6. Remove any custom data

---

## 5. Safety Considerations

### Backup/Snapshot Approach

**Current Capability Gap:** No MCP tool exists to snapshot database state before activation.

**Recommended Safeguards:**
1. **Pre-activation snapshot** - Need custom tool to:
   - Export templates table (for affected plugin templates)
   - Export settings table (for affected plugin settings)
   - Export database schema info
   - Record plugin cache state

2. **Activation transaction isolation** - Would require:
   - MyBB database transaction support (CHECK: Does MyBB support transactions?)
   - Or manual rollback function that:
     - Restores templates from snapshot
     - Restores settings from snapshot
     - Clears plugin cache

3. **Log all changes** - Document:
   - What functions were called
   - What database operations occurred
   - What errors occurred
   - Rollback capability

### Rollback Capability

**Current Tools Supporting Rollback:**
- `mybb_write_template` - Can restore from snapshot
- `mybb_setting_set` - Can restore from snapshot
- Database snapshots could restore settings/templates

**NOT Available for Rollback:**
- Database table deletion (would need DROP TABLE execution)
- Custom table data (no access to plugin-specific tables)

### Key Risk Areas

1. **No read-only mode** - Cannot test plugin activation without actually executing it
2. **No transaction support** - Changes are not atomic (cache updates commit even if functions error)
3. **No undo capability** - Once activated, uninstallation is the only full cleanup
4. **Database access limitation** - Cannot create tables via MCP, must execute PHP

---

## 6. Architectural Handoff Notes for Architect

### Critical Design Constraints

1. **PHP Execution Required**: Full plugin activation MUST execute PHP functions. Cannot be done purely through MCP/SQL.

2. **Two-Phase Activation**: Must implement:
   - Phase 1: Create plugin on filesystem (via `mybb_create_plugin` MCP tool)
   - Phase 2: Execute PHP activation (must be done through MyBB infrastructure or custom PHP bridge)

3. **Limited Safety Tools**: Current MCP tools support:
   - Template pre/post snapshots (possible)
   - Settings pre/post snapshots (possible)
   - Cache management (available)
   - BUT NOT: Atomic transactions, rollback, or database DDL

4. **Missing Tools Needed**:
   - Snapshot export tool (templates + settings + cache)
   - Rollback tool (restore from snapshot)
   - Database table creation tool (for direct table creation)
   - PHP function execution tool (call _install/_activate/_uninstall directly)

### Recommended Approach

**For MVP (Phase 7):**
- Create `mybb_plugin_install` tool that:
  1. Checks if plugin file exists
  2. Checks if `_is_installed()` returns false
  3. Executes PHP to call `_install()` directly (via PHP script execution, not MCP)
  4. Logs results

- Create `mybb_plugin_uninstall` tool that:
  1. Checks if `_uninstall()` exists
  2. Executes PHP to call `_uninstall()` directly
  3. Logs results

- Create snapshot/restore tools:
  1. Pre-activation snapshot (templates, settings, cache)
  2. Post-error rollback capability

**For Phase 8+:**
- Add transactional support if possible
- Add template/settings batch validation
- Add plugin conflict detection

---

## 7. Confidence Assessment

| Finding | Confidence | Evidence |
|---------|------------|----------|
| MyBB activation flow (2-stage, _install then _activate) | 95% | Source code inspection (lines 376-482) + 2 plugin examples |
| Existing MCP tools (templates, settings, cache) | 95% | Direct tool definition review in server.py |
| Cache-only limitation of current activate/deactivate tools | 95% | Tool descriptions explicitly state "does NOT execute PHP" |
| Database table creation NOT available via MCP | 95% | db_query marked read-only, no DDL tools found |
| Plugin lifecycle functions (install/activate/deactivate/uninstall) | 95% | Source code examples from hello.php and hello_banner.php |
| Required safeguards for activation | 85% | Based on what SHOULD be needed, but untested with actual tools |

---

## 8. Open Questions for Architect

1. Does MyBB support database transactions? (Needed for atomic activation)
2. How should PHP function execution be triggered?
   - Via custom PHP script in TestForum/?
   - Via webhook/HTTP endpoint?
   - Via direct PHP function calls in Python (if possible)?
3. Should snapshot tool be part of core activation or separate?
4. What should rollback do if database operations have occurred? (Some non-reversible)

---

## Research Files Referenced

- `TestForum/admin/modules/config/plugins.php` - lines 376-482 (activation/deactivation logic)
- `TestForum/inc/plugins/hello.php` - comprehensive plugin example
- `TestForum/inc/plugins/hello_banner.php` - minimal plugin example
- `mybb_mcp/mybb_mcp/server.py` - Tool definitions and MCP interface

---

**Status:** Research complete. Ready for architectural analysis and Phase 7 implementation planning.
