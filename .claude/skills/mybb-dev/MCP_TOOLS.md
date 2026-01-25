# MyBB MCP Tools Reference

This guide helps you choose the right tool for your task. For detailed parameter documentation, see [docs/wiki/mcp_tools/](../../../docs/wiki/mcp_tools/index.md).

## Tool Categories Overview

**103 total tools organized into 14 categories:**

| Category | Tools | Primary Use Cases |
|----------|-------|-------------------|
| **Templates** | 9 | Read/modify MyBB templates, batch operations, inheritance |
| **Themes & Stylesheets** | 5 | Manage themes and CSS files |
| **Plugins** | 16 | Create, deploy, analyze plugins; hook discovery |
| **Content (Forums/Threads/Posts)** | 17 | CRUD operations for forum content |
| **Users & Moderation** | 14 | User management, moderation actions, logging |
| **Search** | 4 | Search posts, threads, users with filters |
| **Admin & Settings** | 11 | Settings, cache, statistics |
| **Tasks** | 6 | Scheduled task management |
| **Disk Sync** | 5 | Template/stylesheet file watching |
| **Server Orchestration** | 5 | Start/stop PHP server, query logs |
| **Plugin Git** | 6 | Nested git repos for plugins/themes |
| **Language Validation** | 3 | Validate/generate language files |
| **Database** | 1 | Read-only SQL queries |

---

## Decision Trees

### "I need to work with templates..."

```
Are you editing plugin-specific templates?
├─ YES → Edit in workspace: plugin_manager/plugins/{visibility}/{codename}/templates/
│         Then: mybb_plugin_uninstall(remove_files=True) + mybb_plugin_install()
│
└─ NO → Are you editing core MyBB templates?
    ├─ YES → Do templates exist on disk?
    │   ├─ NO → mybb_sync_export_templates("Default Templates")
    │   └─ YES → mybb_sync_start_watcher() + edit files in mybb_sync/
    │
    └─ NO → Need to find a template?
        ├─ By name → mybb_list_templates(search="postbit")
        ├─ By set → mybb_list_templates(sid=1)
        └─ Read content → mybb_read_template("header")
```

**Key Tools:**
- `mybb_sync_export_templates` - Get templates onto disk
- `mybb_sync_start_watcher` - Enable auto-sync from disk to DB
- `mybb_list_templates` - Find templates by name/set
- `mybb_read_template` - View template content
- `mybb_template_batch_read` - Read multiple templates at once

**Critical Rule:** NEVER use `mybb_write_template` or `mybb_template_find_replace` during development. Always edit files on disk with the watcher running.

---

### "I need to manage plugins..."

```
What stage are you at?

CREATE → mybb_create_plugin(codename, name, description, hooks=[...], has_settings=True)
│        Creates workspace at plugin_manager/plugins/{visibility}/{codename}/
│
DEVELOP → Edit files in workspace
│         ├─ {codename}.php - Main plugin file
│         ├─ templates/{name}.html - Plugin templates
│         └─ inc/languages/english/{codename}.lang.php - Language file
│
DEPLOY → mybb_plugin_install(codename)
│        Copies files to TestForum + runs _install() + _activate()
│
UPDATE TEMPLATES/LANGUAGE → Full reinstall required:
│                           mybb_plugin_uninstall(codename, remove_files=True)
│                           mybb_plugin_install(codename)
│
DEBUG → What's wrong?
│       ├─ Plugin not found → mybb_plugin_status(codename)
│       ├─ Hook not firing → mybb_hooks_discover(search="hook_name")
│       ├─ PHP errors → mybb_server_logs(errors_only=True)
│       └─ Structure issues → mybb_analyze_plugin(codename)
│
DELETE → mybb_delete_plugin(codename, archive=True, force=True if installed)
```

**Key Tools:**
- `mybb_create_plugin` - Scaffold new plugin
- `mybb_plugin_install` - Deploy to TestForum (runs PHP lifecycle)
- `mybb_plugin_uninstall` - Remove plugin (optionally run _uninstall())
- `mybb_plugin_status` - Check installation/activation state
- `mybb_analyze_plugin` - Inspect plugin structure
- `mybb_list_hooks` - Find available hooks
- `mybb_hooks_discover` - Scan MyBB for hooks in specific files
- `mybb_hooks_usage` - See which plugins use a hook

**Critical Rules:**
1. Templates updated → MUST do full uninstall/reinstall
2. Never copy files manually → Use install/uninstall tools
3. Check workspace exists before assuming plugin is missing

---

### "I need to debug something..."

```
What type of problem?

PHP ERRORS → mybb_server_logs(errors_only=True, limit=50)
│            Look for: fatal, parse, warning, notice
│            Then: mybb_server_logs(filter_keyword="Fatal error in...")
│
PLUGIN NOT WORKING → Step-by-step diagnosis:
│                    1. mybb_plugin_status(codename) - Is it installed/active?
│                    2. mybb_plugin_is_installed(codename) - Double-check
│                    3. mybb_analyze_plugin(codename) - Structure OK?
│                    4. mybb_server_logs(errors_only=True) - Any PHP errors?
│
HOOK NOT FIRING → 1. mybb_hooks_discover(search="hook_name") - Does hook exist?
│                 2. mybb_hooks_usage("hook_name") - Other plugins using it?
│                 3. Check function name matches: hookname_hookfunction
│
TEMPLATE NOT SHOWING → 1. Did you restart after template changes?
│                       2. Is watcher running? mybb_sync_status()
│                       3. Check template name: mybb_list_templates(search="...")
│
DATABASE ISSUES → mybb_db_query("SELECT * FROM mybb_plugins WHERE active=1")
│                 Check table prefix in .env (MYBB_DB_PREFIX)
│
SERVER DOWN → mybb_server_status() - Is it running?
│             mybb_server_start() - Start if needed
│             mybb_server_logs() - Check startup errors
```

**Key Tools:**
- `mybb_server_logs` - **MOST IMPORTANT** for debugging
- `mybb_plugin_status` - Check plugin state
- `mybb_hooks_discover` - Verify hook exists
- `mybb_sync_status` - Check file watcher
- `mybb_db_query` - Inspect database

**Pro Tips:**
- Always check logs FIRST with `errors_only=True`
- Use `filter_keyword` to narrow down issues
- Use `since_minutes=5` for recent errors only

---

### "I need to work with content..."

```
What content type?

FORUMS → Create test forum structure
│        ├─ List → mybb_forum_list()
│        ├─ Create → mybb_forum_create(name, type="f", pid=0)
│        ├─ Update → mybb_forum_update(fid, name="New Name")
│        └─ Delete → mybb_forum_delete(fid) ⚠️ Ensure empty first
│
THREADS → Test thread operations
│         ├─ List → mybb_thread_list(fid=2, limit=10)
│         ├─ Create → mybb_thread_create(fid, subject, message)
│         ├─ Update → mybb_thread_update(tid, closed=1, sticky=1)
│         ├─ Move → mybb_thread_move(tid, new_fid)
│         └─ Delete → mybb_thread_delete(tid, soft=True)
│
POSTS → Reply to threads
│       ├─ List → mybb_post_list(tid=5, limit=20)
│       ├─ Create → mybb_post_create(tid, message, replyto=0)
│       ├─ Update → mybb_post_update(pid, message="Edited", editreason="typo")
│       └─ Delete → mybb_post_delete(pid, soft=True)
│
SEARCH → Find content
│        ├─ Posts → mybb_search_posts("keyword", forums=[2,3], limit=25)
│        ├─ Threads → mybb_search_threads("keyword", author="admin")
│        └─ Combined → mybb_search_advanced("keyword", content_type="both")
```

**Key Tools:**
- `mybb_forum_create` - Set up test forums
- `mybb_thread_create` - Create threads with first post (atomic)
- `mybb_post_create` - Add replies
- `mybb_search_posts` - Search post content
- `mybb_search_advanced` - Combined search

**Important Notes:**
- Thread/post create automatically updates counters
- Soft delete sets visible=-1 (recoverable)
- Use search tools to find content instead of raw queries

---

### "I need admin/config operations..."

```
What do you need?

SETTINGS → Read/modify MyBB settings
│          ├─ Get → mybb_setting_get("bbname")
│          ├─ Set → mybb_setting_set("bbname", "My Forum")
│          ├─ List all → mybb_setting_list()
│          └─ List by group → mybb_setting_list(gid=2)
│
CACHE → Clear caches after changes
│       ├─ Rebuild all → mybb_cache_rebuild("all")
│       ├─ Rebuild specific → mybb_cache_rebuild("settings")
│       ├─ Read cache → mybb_cache_read("plugins")
│       └─ List caches → mybb_cache_list()
│
STATISTICS → Get forum stats
│            ├─ Forum stats → mybb_stats_forum()
│            └─ Board stats → mybb_stats_board()
│
TASKS → Manage scheduled tasks
│       ├─ List → mybb_task_list(enabled_only=True)
│       ├─ Enable → mybb_task_enable(tid)
│       ├─ Disable → mybb_task_disable(tid)
│       └─ View log → mybb_task_run_log(tid, limit=50)
```

**Key Tools:**
- `mybb_setting_set` - Modify settings (rebuilds cache automatically)
- `mybb_cache_rebuild` - Clear caches after DB changes
- `mybb_stats_board` - Get comprehensive stats

**Critical Rule:** Always rebuild cache after direct DB modifications

---

## Complete Tool Reference by Category

### 1. Templates (9 tools)

#### Core Template Operations

**`mybb_list_template_sets`**
- **Purpose:** List all template sets (themes)
- **When to use:** Finding template set IDs or available sets
- **Example:** `mybb_list_template_sets()`
- **Related:** `mybb_list_templates`

**`mybb_list_templates(sid, search)`**
- **Purpose:** Find templates by set ID or name
- **When to use:** Locating specific templates before reading/editing
- **Key params:** `sid=-2` (master), `sid=-1` (global), `sid=1+` (custom), `search` (name filter)
- **Example:** `mybb_list_templates(search="postbit")`
- **Related:** `mybb_read_template`

**`mybb_read_template(title, sid)`**
- **Purpose:** Read template HTML content
- **When to use:** Viewing template code, checking inheritance
- **Key params:** `title` (required), `sid` (optional, checks master + custom)
- **Example:** `mybb_read_template("header")`
- **Related:** `mybb_template_batch_read`

**`mybb_write_template(title, template, sid)`**
- **Purpose:** Create/update template in database
- **When to use:** ⚠️ **AVOID during development** - use disk sync instead
- **Use case:** Plugin _activate() hooks that inject templates programmatically
- **Example:** Should rarely use directly
- **Related:** `mybb_sync_export_templates`, `mybb_sync_start_watcher`

**`mybb_list_template_groups()`**
- **Purpose:** List template categories (calendar, forum, usercp, etc.)
- **When to use:** Understanding template organization
- **Example:** `mybb_list_template_groups()`

#### Batch Operations

**`mybb_template_batch_read(templates, sid)`**
- **Purpose:** Read multiple templates in one call
- **When to use:** Analyzing related templates efficiently
- **Key params:** `templates` (array of names), `sid=-2` (default: master)
- **Example:** `mybb_template_batch_read(["header", "footer", "index"], sid=-2)`
- **Related:** `mybb_read_template`

**`mybb_template_batch_write(templates, sid)`**
- **Purpose:** Write multiple templates atomically
- **When to use:** Plugin installation that needs to create many templates
- **Key params:** `templates` (array of {title, template}), `sid=1` (default)
- **Example:** Primarily used in plugin scaffolding
- **Related:** `mybb_write_template`

#### Advanced Template Tools

**`mybb_template_find_replace(title, find, replace, template_sets, regex, limit)`**
- **Purpose:** Find/replace within templates (mirrors MyBB's find_replace_templatesets)
- **When to use:** Plugin _activate() to inject code; **NOT for development**
- **Key params:** `regex=True` (default), `template_sets=[]` (all sets), `limit=-1` (unlimited)
- **Example:** Used in plugin lifecycle hooks
- **Related:** `mybb_write_template`

**`mybb_template_outdated(sid)`**
- **Purpose:** Find templates that differ from master after MyBB upgrade
- **When to use:** After upgrading MyBB to find templates needing updates
- **Key params:** `sid` (template set ID to check)
- **Example:** `mybb_template_outdated(sid=1)`
- **Related:** `mybb_list_templates`

---

### 2. Themes & Stylesheets (5 tools)

**`mybb_list_themes()`**
- **Purpose:** List all installed themes
- **When to use:** Finding theme IDs or available themes
- **Example:** `mybb_list_themes()`
- **Related:** `mybb_list_stylesheets`

**`mybb_list_stylesheets(tid)`**
- **Purpose:** List stylesheets for a theme
- **When to use:** Finding stylesheet IDs before editing
- **Key params:** `tid` (theme ID, optional)
- **Example:** `mybb_list_stylesheets(tid=1)`
- **Related:** `mybb_read_stylesheet`

**`mybb_read_stylesheet(sid)`**
- **Purpose:** Read CSS content of a stylesheet
- **When to use:** Viewing stylesheet code
- **Key params:** `sid` (stylesheet ID, required)
- **Example:** `mybb_read_stylesheet(sid=5)`
- **Related:** `mybb_write_stylesheet`

**`mybb_write_stylesheet(sid, stylesheet)`**
- **Purpose:** Update stylesheet CSS and refresh cache
- **When to use:** ⚠️ **AVOID during development** - use disk sync instead
- **Key params:** `sid` (stylesheet ID), `stylesheet` (CSS content)
- **Example:** Should rarely use directly
- **Related:** `mybb_sync_export_stylesheets`, `mybb_sync_start_watcher`

**`mybb_create_theme(codename, name, description, author, version, parent_theme, stylesheets)`**
- **Purpose:** Create new theme in plugin_manager workspace
- **When to use:** Starting theme development
- **Key params:** `codename` (required), `name` (required), `parent_theme` (inheritance)
- **Example:** `mybb_create_theme(codename="my_theme", name="My Theme", parent_theme="Default")`
- **Related:** `mybb_delete_theme`

---

### 3. Plugins (16 tools)

#### Plugin Listing & Inspection

**`mybb_list_plugins()`**
- **Purpose:** List all plugins in TestForum/inc/plugins/
- **When to use:** Seeing what's deployed (not workspace)
- **Example:** `mybb_list_plugins()`
- **Related:** `mybb_plugin_list_installed`

**`mybb_read_plugin(name)`**
- **Purpose:** Read plugin PHP source code
- **When to use:** Viewing plugin code for analysis
- **Key params:** `name` (without .php)
- **Example:** `mybb_read_plugin("hello_banner")`
- **Related:** `mybb_analyze_plugin`

**`mybb_plugin_info(name)`**
- **Purpose:** Read plugin metadata from _info() function
- **When to use:** Getting plugin name, version, compatibility
- **Key params:** `name` (codename without .php)
- **Example:** `mybb_plugin_info("hello_banner")`
- **Related:** `mybb_analyze_plugin`

**`mybb_plugin_list_installed()`**
- **Purpose:** List active plugins from datacache
- **When to use:** Checking which plugins are currently active
- **Example:** `mybb_plugin_list_installed()`
- **Related:** `mybb_plugin_is_installed`, `mybb_plugin_status`

**`mybb_plugin_is_installed(name)`**
- **Purpose:** Check if specific plugin is installed/active
- **When to use:** Quick yes/no check before operations
- **Key params:** `name` (codename)
- **Example:** `mybb_plugin_is_installed("hello_banner")`
- **Related:** `mybb_plugin_status`

**`mybb_plugin_status(codename)`**
- **Purpose:** Get comprehensive plugin status via PHP bridge
- **When to use:** **PRIMARY DIAGNOSTIC TOOL** - shows installation, activation, compatibility, info
- **Key params:** `codename` (without .php)
- **Example:** `mybb_plugin_status("my_plugin")`
- **Related:** `mybb_analyze_plugin`

**`mybb_analyze_plugin(name)`**
- **Purpose:** Deep analysis of plugin structure (hooks, settings, templates, tables)
- **When to use:** Understanding plugin architecture, debugging
- **Key params:** `name` (without .php)
- **Example:** `mybb_analyze_plugin("hello_banner")`
- **Related:** `mybb_plugin_status`

#### Plugin Creation & Management

**`mybb_create_plugin(codename, name, description, author, version, visibility, hooks, has_settings, has_templates, has_database)`**
- **Purpose:** **PRIMARY TOOL** for creating new plugins with scaffolding
- **When to use:** Starting any new plugin
- **Key params:** `codename` (required), `name` (required), `description` (required), `hooks=[]`, `has_settings=False`, `has_templates=False`
- **Example:** `mybb_create_plugin(codename="welcome_msg", name="Welcome Message", description="Greets users", hooks=["index_start"], has_settings=True)`
- **Related:** `mybb_plugin_install`, `mybb_delete_plugin`

**`mybb_delete_plugin(codename, archive, force)`**
- **Purpose:** Delete plugin from workspace and database
- **When to use:** Removing failed/test plugins
- **Key params:** `archive=True` (default, moves to archive), `force=True` (required if installed)
- **Example:** `mybb_delete_plugin(codename="test_plugin", force=True)`
- **Related:** `mybb_delete_theme`

#### Plugin Lifecycle (Critical for Deployment)

**`mybb_plugin_install(codename, force)`**
- **Purpose:** **FULL INSTALLATION** - deploy files from workspace + run _install() + _activate()
- **When to use:** First deployment, after major changes
- **Key params:** `codename` (required), `force=False` (skip compatibility check)
- **Example:** `mybb_plugin_install("my_plugin")`
- **Related:** `mybb_plugin_uninstall`, `mybb_plugin_deploy`

**`mybb_plugin_uninstall(codename, uninstall, remove_files)`**
- **Purpose:** **FULL UNINSTALLATION** - run _deactivate() + optionally _uninstall() + remove files
- **When to use:** Before reinstalling (template updates), cleanup
- **Key params:** `uninstall=False` (run _uninstall), `remove_files=False` (delete from TestForum)
- **Example:** `mybb_plugin_uninstall("my_plugin", remove_files=True)`  # Before reinstall
- **Related:** `mybb_plugin_install`

**`mybb_plugin_activate(name, force)`**
- **Purpose:** Activate plugin via _activate() (requires already installed)
- **When to use:** Reactivating after deactivation
- **Key params:** `name` (codename), `force=False`
- **Example:** `mybb_plugin_activate("my_plugin")`
- **Related:** `mybb_plugin_deactivate`, `mybb_plugin_install`

**`mybb_plugin_deactivate(name)`**
- **Purpose:** Deactivate plugin via _deactivate()
- **When to use:** Temporarily disabling plugin
- **Key params:** `name` (codename)
- **Example:** `mybb_plugin_deactivate("my_plugin")`
- **Related:** `mybb_plugin_activate`

**`mybb_plugin_deploy(codename, action, force)`**
- **Purpose:** Lifecycle wrapper for common operations
- **When to use:** Quick activate/deactivate/reinstall
- **Key params:** `action` ("activate", "deactivate", "reinstall")
- **Example:** `mybb_plugin_deploy("my_plugin", "reinstall")`  # = uninstall + remove + install
- **Related:** `mybb_plugin_install`, `mybb_plugin_uninstall`

#### Hook Discovery

**`mybb_list_hooks(category, search)`**
- **Purpose:** List known MyBB hooks from built-in reference
- **When to use:** Finding available hooks for plugin development
- **Key params:** `category` (index, showthread, member, admin, global), `search` (filter)
- **Example:** `mybb_list_hooks(category="admin")`
- **Related:** `mybb_hooks_discover`

**`mybb_hooks_discover(path, category, search)`**
- **Purpose:** **DYNAMIC DISCOVERY** - scan MyBB source for $plugins->run_hooks() calls
- **When to use:** Finding hooks in specific files, discovering undocumented hooks
- **Key params:** `path` (PHP file to scan), `category` (filter prefix), `search` (filter name)
- **Example:** `mybb_hooks_discover(path="showthread.php")` or `mybb_hooks_discover(category="admin")`
- **Related:** `mybb_list_hooks`, `mybb_hooks_usage`

**`mybb_hooks_usage(hook_name)`**
- **Purpose:** Find which plugins use a specific hook
- **When to use:** Learning hook patterns, debugging hook conflicts
- **Key params:** `hook_name` (required)
- **Example:** `mybb_hooks_usage("index_start")`
- **Related:** `mybb_hooks_discover`

---

### 4. Content (Forums/Threads/Posts) - 17 tools

#### Forum Management (5 tools)

**`mybb_forum_list()`**
- **Purpose:** List all forums with hierarchy
- **When to use:** Finding forum IDs, understanding structure
- **Example:** `mybb_forum_list()`
- **Related:** `mybb_forum_read`

**`mybb_forum_read(fid)`**
- **Purpose:** Get forum details by ID
- **When to use:** Inspecting forum properties
- **Key params:** `fid` (forum ID)
- **Example:** `mybb_forum_read(fid=2)`
- **Related:** `mybb_forum_update`

**`mybb_forum_create(name, description, type, pid, parentlist, disporder)`**
- **Purpose:** Create new forum or category
- **When to use:** Setting up test forums
- **Key params:** `name` (required), `type="f"` (forum) or `"c"` (category), `pid=0` (parent)
- **Example:** `mybb_forum_create(name="Test Forum", type="f")`
- **Related:** `mybb_forum_delete`

**`mybb_forum_update(fid, name, description, type, disporder, active, open)`**
- **Purpose:** Modify forum properties
- **When to use:** Changing forum settings
- **Key params:** `fid` (required), other params optional
- **Example:** `mybb_forum_update(fid=2, name="Updated Name", open=0)`
- **Related:** `mybb_forum_read`

**`mybb_forum_delete(fid)`**
- **Purpose:** Delete a forum ⚠️ **WARNING: No content migration**
- **When to use:** Only on EMPTY forums
- **Key params:** `fid` (forum ID)
- **Example:** Ensure forum is empty first
- **Related:** `mybb_thread_move`

#### Thread Management (6 tools)

**`mybb_thread_list(fid, limit, offset)`**
- **Purpose:** List threads with pagination
- **When to use:** Finding threads in a forum
- **Key params:** `fid` (optional, omit for all), `limit=50`, `offset=0`
- **Example:** `mybb_thread_list(fid=2, limit=10)`
- **Related:** `mybb_thread_read`

**`mybb_thread_read(tid)`**
- **Purpose:** Get thread details
- **When to use:** Inspecting thread properties
- **Key params:** `tid` (thread ID)
- **Example:** `mybb_thread_read(tid=5)`
- **Related:** `mybb_thread_update`

**`mybb_thread_create(fid, subject, message, uid, username, prefix)`**
- **Purpose:** **ATOMIC OPERATION** - create thread with first post
- **When to use:** Creating test threads
- **Key params:** `fid` (required), `subject` (required), `message` (required), `uid=1`, `username="Admin"`
- **Example:** `mybb_thread_create(fid=2, subject="Test Thread", message="First post content")`
- **Related:** `mybb_post_create`

**`mybb_thread_update(tid, subject, prefix, closed, sticky, visible)`**
- **Purpose:** Modify thread properties
- **When to use:** Changing thread status/title
- **Key params:** `tid` (required), other params optional
- **Example:** `mybb_thread_update(tid=5, closed=1, sticky=1)`
- **Related:** `mybb_mod_close_thread`, `mybb_mod_stick_thread`

**`mybb_thread_delete(tid, soft)`**
- **Purpose:** Delete thread (soft or permanent)
- **When to use:** Removing test threads
- **Key params:** `tid` (required), `soft=True` (default, sets visible=-1)
- **Example:** `mybb_thread_delete(tid=5, soft=True)`
- **Related:** `mybb_mod_soft_delete_thread`

**`mybb_thread_move(tid, new_fid)`**
- **Purpose:** Move thread to different forum (updates counters)
- **When to use:** Reorganizing content
- **Key params:** `tid` (required), `new_fid` (required)
- **Example:** `mybb_thread_move(tid=5, new_fid=3)`
- **Related:** `mybb_thread_update`

#### Post Management (6 tools)

**`mybb_post_list(tid, limit, offset)`**
- **Purpose:** List posts with pagination
- **When to use:** Finding posts in a thread
- **Key params:** `tid` (optional, omit for all), `limit=50`, `offset=0`
- **Example:** `mybb_post_list(tid=5, limit=20)`
- **Related:** `mybb_post_read`

**`mybb_post_read(pid)`**
- **Purpose:** Get post details
- **When to use:** Inspecting post content/metadata
- **Key params:** `pid` (post ID)
- **Example:** `mybb_post_read(pid=10)`
- **Related:** `mybb_post_update`

**`mybb_post_create(tid, subject, message, uid, username, replyto)`**
- **Purpose:** Create new post (reply) in thread
- **When to use:** Adding replies, testing
- **Key params:** `tid` (required), `message` (required), `subject` (optional), `replyto=0` (threading)
- **Example:** `mybb_post_create(tid=5, message="Reply content")`
- **Related:** `mybb_thread_create`

**`mybb_post_update(pid, message, subject, edituid, editreason, signature, disablesmilies)`**
- **Purpose:** Edit post (tracks edit history)
- **When to use:** Modifying post content
- **Key params:** `pid` (required), other params optional
- **Example:** `mybb_post_update(pid=10, message="Updated content", editreason="typo fix")`
- **Related:** `mybb_post_read`

**`mybb_post_delete(pid, soft, restore)`**
- **Purpose:** Delete or restore post
- **When to use:** Removing posts, undoing deletions
- **Key params:** `pid` (required), `soft=True` (default), `restore=False`
- **Example:** `mybb_post_delete(pid=10, soft=True)` or `mybb_post_delete(pid=10, restore=True)`
- **Related:** `mybb_mod_soft_delete_post`

---

### 5. Users & Moderation (14 tools)

#### User Management (6 tools)

**`mybb_user_get(uid, username)`**
- **Purpose:** Get user by UID or username (excludes sensitive fields)
- **When to use:** Looking up user info
- **Key params:** Either `uid` OR `username`
- **Example:** `mybb_user_get(username="admin")` or `mybb_user_get(uid=1)`
- **Related:** `mybb_user_list`

**`mybb_user_list(usergroup, limit, offset)`**
- **Purpose:** List users with filters (always excludes sensitive fields)
- **When to use:** Finding users by group
- **Key params:** `usergroup` (optional), `limit=50`, `offset=0`
- **Example:** `mybb_user_list(usergroup=4, limit=10)`
- **Related:** `mybb_usergroup_list`

**`mybb_user_update_group(uid, usergroup, additionalgroups)`**
- **Purpose:** Change user's primary and additional groups
- **When to use:** Testing permissions, modifying access
- **Key params:** `uid` (required), `usergroup` (required), `additionalgroups` (optional CSV)
- **Example:** `mybb_user_update_group(uid=5, usergroup=4, additionalgroups="3,6")`
- **Related:** `mybb_usergroup_list`

**`mybb_user_ban(uid, gid, admin, dateline, bantime, reason)`**
- **Purpose:** Add user to banned list
- **When to use:** Testing ban functionality
- **Key params:** `uid`, `gid`, `admin`, `dateline` (all required)
- **Example:** `mybb_user_ban(uid=5, gid=7, admin=1, dateline=1234567890, reason="Spamming")`
- **Related:** `mybb_user_unban`

**`mybb_user_unban(uid)`**
- **Purpose:** Remove user from banned list
- **When to use:** Unbanning users
- **Key params:** `uid` (required)
- **Example:** `mybb_user_unban(uid=5)`
- **Related:** `mybb_user_ban`

**`mybb_usergroup_list()`**
- **Purpose:** List all usergroups
- **When to use:** Finding group IDs for permissions
- **Example:** `mybb_usergroup_list()`
- **Related:** `mybb_user_update_group`

#### Moderation Tools (8 tools)

**`mybb_mod_close_thread(tid, closed)`**
- **Purpose:** Close or open a thread
- **When to use:** Testing thread moderation
- **Key params:** `tid` (required), `closed=True` (default)
- **Example:** `mybb_mod_close_thread(tid=5, closed=True)` or `mybb_mod_close_thread(tid=5, closed=False)`
- **Related:** `mybb_thread_update`

**`mybb_mod_stick_thread(tid, sticky)`**
- **Purpose:** Stick or unstick a thread
- **When to use:** Testing sticky functionality
- **Key params:** `tid` (required), `sticky=True` (default)
- **Example:** `mybb_mod_stick_thread(tid=5, sticky=True)`
- **Related:** `mybb_thread_update`

**`mybb_mod_approve_thread(tid, approve)`**
- **Purpose:** Approve or unapprove thread (visible=1 or 0)
- **When to use:** Testing moderation queue
- **Key params:** `tid` (required), `approve=True` (default)
- **Example:** `mybb_mod_approve_thread(tid=5, approve=True)`
- **Related:** `mybb_thread_update`

**`mybb_mod_approve_post(pid, approve)`**
- **Purpose:** Approve or unapprove post (visible=1 or 0)
- **When to use:** Testing post moderation
- **Key params:** `pid` (required), `approve=True` (default)
- **Example:** `mybb_mod_approve_post(pid=10, approve=True)`
- **Related:** `mybb_post_update`

**`mybb_mod_soft_delete_thread(tid, delete)`**
- **Purpose:** Soft delete or restore thread
- **When to use:** Testing soft delete functionality
- **Key params:** `tid` (required), `delete=True` (default)
- **Example:** `mybb_mod_soft_delete_thread(tid=5, delete=True)` or `mybb_mod_soft_delete_thread(tid=5, delete=False)`
- **Related:** `mybb_thread_delete`

**`mybb_mod_soft_delete_post(pid, delete)`**
- **Purpose:** Soft delete or restore post
- **When to use:** Testing post deletion
- **Key params:** `pid` (required), `delete=True` (default)
- **Example:** `mybb_mod_soft_delete_post(pid=10, delete=True)`
- **Related:** `mybb_post_delete`

**`mybb_modlog_list(uid, fid, tid, limit)`**
- **Purpose:** List moderation log entries with filters
- **When to use:** Viewing mod actions, auditing
- **Key params:** All optional filters, `limit=50`
- **Example:** `mybb_modlog_list(uid=1, limit=20)`
- **Related:** `mybb_modlog_add`

**`mybb_modlog_add(uid, fid, tid, pid, action, data, ipaddress)`**
- **Purpose:** Add moderation log entry
- **When to use:** Custom mod actions in plugins
- **Key params:** `uid` (required), `action` (required), others optional
- **Example:** `mybb_modlog_add(uid=1, action="Custom mod action", fid=2, tid=5)`
- **Related:** `mybb_modlog_list`

---

### 6. Search (4 tools)

**`mybb_search_posts(query, forums, author, date_from, date_to, limit, offset)`**
- **Purpose:** Search post content with filters
- **When to use:** Finding posts by keyword/author/forum
- **Key params:** `query` (required), `forums=[]` (IDs), `author`, `date_from/to` (Unix timestamps), `limit=25`, `offset=0`
- **Example:** `mybb_search_posts("keyword", forums=[2,3], author="admin", limit=10)`
- **Related:** `mybb_search_advanced`

**`mybb_search_threads(query, forums, author, prefix, limit, offset)`**
- **Purpose:** Search thread subjects with filters
- **When to use:** Finding threads by title/author/prefix
- **Key params:** `query` (required), `forums=[]`, `author`, `prefix` (ID), `limit=25`, `offset=0`
- **Example:** `mybb_search_threads("announcement", forums=[2], prefix=1)`
- **Related:** `mybb_search_advanced`

**`mybb_search_users(query, field, limit, offset)`**
- **Purpose:** Search users by username or email (safe, excludes passwords)
- **When to use:** Finding users
- **Key params:** `query` (required), `field="username"` or `"email"`, `limit=25`, `offset=0`
- **Example:** `mybb_search_users("admin", field="username")`
- **Related:** `mybb_user_list`

**`mybb_search_advanced(query, content_type, forums, date_from, date_to, sort_by, limit, offset)`**
- **Purpose:** Combined search across posts/threads with multiple filters
- **When to use:** Complex searches needing both post and thread results
- **Key params:** `query` (required), `content_type="both"` (or "posts"/"threads"), `sort_by="date"` or `"relevance"`, `limit=25`
- **Example:** `mybb_search_advanced("keyword", content_type="both", forums=[2,3], sort_by="relevance")`
- **Related:** `mybb_search_posts`, `mybb_search_threads`

---

### 7. Admin & Settings (11 tools)

#### Settings Management (4 tools)

**`mybb_setting_get(name)`**
- **Purpose:** Get setting value by name
- **When to use:** Reading current settings
- **Key params:** `name` (setting name like "bbname", "boardclosed")
- **Example:** `mybb_setting_get("bbname")`
- **Related:** `mybb_setting_set`

**`mybb_setting_set(name, value)`**
- **Purpose:** Update setting value (auto-rebuilds cache)
- **When to use:** Modifying forum settings
- **Key params:** `name` (required), `value` (required, string)
- **Example:** `mybb_setting_set("bbname", "My Forum")`
- **Related:** `mybb_setting_get`, `mybb_cache_rebuild`

**`mybb_setting_list(gid)`**
- **Purpose:** List all settings or by group
- **When to use:** Finding setting names, browsing options
- **Key params:** `gid` (optional, group ID filter)
- **Example:** `mybb_setting_list()` or `mybb_setting_list(gid=2)`
- **Related:** `mybb_settinggroup_list`

**`mybb_settinggroup_list()`**
- **Purpose:** List setting groups (categories)
- **When to use:** Understanding setting organization
- **Example:** `mybb_settinggroup_list()`
- **Related:** `mybb_setting_list`

#### Cache Management (4 tools)

**`mybb_cache_read(title)`**
- **Purpose:** Read cache entry by title (returns serialized PHP)
- **When to use:** Inspecting cache contents
- **Key params:** `title` (e.g., "settings", "plugins", "usergroups", "forums")
- **Example:** `mybb_cache_read("plugins")`
- **Related:** `mybb_cache_list`

**`mybb_cache_rebuild(cache_type)`**
- **Purpose:** Rebuild (clear) cache entries (MyBB regenerates on access)
- **When to use:** After direct DB modifications, fixing cache issues
- **Key params:** `cache_type="all"` (default) or specific type
- **Example:** `mybb_cache_rebuild("settings")` or `mybb_cache_rebuild("all")`
- **Related:** `mybb_cache_clear`

**`mybb_cache_list()`**
- **Purpose:** List all cache entries with sizes
- **When to use:** Understanding cache structure
- **Example:** `mybb_cache_list()`
- **Related:** `mybb_cache_read`

**`mybb_cache_clear(title)`**
- **Purpose:** Clear specific cache or all caches
- **When to use:** Similar to rebuild, clearing stale cache
- **Key params:** `title` (optional, omit for all)
- **Example:** `mybb_cache_clear("plugins")` or `mybb_cache_clear()`
- **Related:** `mybb_cache_rebuild`

#### Statistics (3 tools)

**`mybb_stats_forum()`**
- **Purpose:** Get forum statistics (users, threads, posts, newest member)
- **When to use:** Dashboard info, testing counters
- **Example:** `mybb_stats_forum()`
- **Related:** `mybb_stats_board`

**`mybb_stats_board()`**
- **Purpose:** Comprehensive board stats (forums, users, threads, posts, latest post, most active forum)
- **When to use:** Full statistics overview
- **Example:** `mybb_stats_board()`
- **Related:** `mybb_stats_forum`

---

### 8. Tasks (6 tools)

**`mybb_task_list(enabled_only)`**
- **Purpose:** List all scheduled tasks
- **When to use:** Finding task IDs, checking status
- **Key params:** `enabled_only=False` (default: show all)
- **Example:** `mybb_task_list(enabled_only=True)`
- **Related:** `mybb_task_get`

**`mybb_task_get(tid)`**
- **Purpose:** Get detailed task information
- **When to use:** Inspecting task configuration
- **Key params:** `tid` (task ID, required)
- **Example:** `mybb_task_get(tid=1)`
- **Related:** `mybb_task_list`

**`mybb_task_enable(tid)`**
- **Purpose:** Enable a scheduled task
- **When to use:** Activating disabled tasks
- **Key params:** `tid` (required)
- **Example:** `mybb_task_enable(tid=5)`
- **Related:** `mybb_task_disable`

**`mybb_task_disable(tid)`**
- **Purpose:** Disable a scheduled task
- **When to use:** Temporarily stopping tasks
- **Key params:** `tid` (required)
- **Example:** `mybb_task_disable(tid=5)`
- **Related:** `mybb_task_enable`

**`mybb_task_update_nextrun(tid, nextrun)`**
- **Purpose:** Update next run time for a task
- **When to use:** Forcing task to run sooner/later
- **Key params:** `tid` (required), `nextrun` (Unix timestamp, required)
- **Example:** `mybb_task_update_nextrun(tid=1, nextrun=1234567890)`
- **Related:** `mybb_task_get`

**`mybb_task_run_log(tid, limit)`**
- **Purpose:** View task execution history
- **When to use:** Checking if tasks ran, debugging failures
- **Key params:** `tid` (optional, filter by task), `limit=50` (max 500)
- **Example:** `mybb_task_run_log(tid=1, limit=20)`
- **Related:** `mybb_task_get`

---

### 9. Disk Sync (5 tools)

**`mybb_sync_export_templates(set_name)`**
- **Purpose:** Export all templates from set to disk files
- **When to use:** **FIRST STEP** before template development
- **Key params:** `set_name` (e.g., "Default Templates")
- **Example:** `mybb_sync_export_templates("Default Templates")`
- **Location:** Creates files in `mybb_sync/template_sets/{set_name}/`
- **Related:** `mybb_sync_start_watcher`

**`mybb_sync_export_stylesheets(theme_name)`**
- **Purpose:** Export all stylesheets from theme to disk files
- **When to use:** **FIRST STEP** before stylesheet development
- **Key params:** `theme_name` (e.g., "Default")
- **Example:** `mybb_sync_export_stylesheets("Default")`
- **Location:** Creates files in `mybb_sync/themes/{theme_name}/`
- **Related:** `mybb_sync_start_watcher`

**`mybb_sync_start_watcher()`**
- **Purpose:** **START FILE WATCHER** - auto-syncs disk changes to database
- **When to use:** **SECOND STEP** after export, before editing
- **Example:** `mybb_sync_start_watcher()`
- **Behavior:** Watches `mybb_sync/` directory, syncs changes automatically
- **Related:** `mybb_sync_stop_watcher`, `mybb_sync_status`

**`mybb_sync_stop_watcher()`**
- **Purpose:** Stop file watcher
- **When to use:** After finishing template/stylesheet development
- **Example:** `mybb_sync_stop_watcher()`
- **Related:** `mybb_sync_start_watcher`

**`mybb_sync_status()`**
- **Purpose:** Get sync service status (watcher state, directory, etc.)
- **When to use:** Checking if watcher is running, troubleshooting
- **Example:** `mybb_sync_status()`
- **Related:** `mybb_sync_start_watcher`

---

### 10. Server Orchestration (5 tools)

**`mybb_server_start(port, force)`**
- **Purpose:** Start PHP development server (auto-detects if running)
- **When to use:** Starting TestForum for browser testing
- **Key params:** `port=8022` (default from env), `force=False` (stop existing first)
- **Example:** `mybb_server_start()` or `mybb_server_start(port=8022, force=True)`
- **Requires:** MariaDB must be running
- **Related:** `mybb_server_status`, `mybb_server_stop`

**`mybb_server_stop(force)`**
- **Purpose:** Stop PHP development server gracefully
- **When to use:** Shutting down server
- **Key params:** `force=False` (force kill if graceful fails)
- **Example:** `mybb_server_stop()` or `mybb_server_stop(force=True)`
- **Related:** `mybb_server_start`, `mybb_server_restart`

**`mybb_server_status()`**
- **Purpose:** Get server status (port, PID, uptime, MariaDB status)
- **When to use:** **FIRST DIAGNOSTIC TOOL** - check if server is running
- **Example:** `mybb_server_status()`
- **Related:** `mybb_server_logs`

**`mybb_server_logs(errors_only, exclude_static, since_minutes, filter_keyword, limit, tail, offset)`**
- **Purpose:** **ESSENTIAL DEBUGGING TOOL** - query PHP server logs with filtering
- **When to use:** **PRIMARY TOOL** for debugging PHP errors, HTTP issues
- **Key params:**
  - `errors_only=False` - Only show PHP errors/warnings and 4xx/5xx
  - `exclude_static=False` - Filter out .css, .js, images
  - `since_minutes` - Last N minutes only
  - `filter_keyword` - Search for keyword
  - `limit=50` - Max entries
  - `tail=True` - Most recent first
  - `offset=0` - Pagination
- **Examples:**
  - `mybb_server_logs(errors_only=True, limit=50)` - Show errors
  - `mybb_server_logs(filter_keyword="Fatal", errors_only=True)` - Fatal errors only
  - `mybb_server_logs(since_minutes=5, errors_only=True)` - Recent errors
  - `mybb_server_logs(offset=50, limit=50)` - Page 2
- **Output:** Error breakdown summary + log entries
- **Related:** `mybb_server_status`

**`mybb_server_restart(port)`**
- **Purpose:** Restart server (stop then start)
- **When to use:** After config changes, fixing stuck server
- **Key params:** `port` (optional, for restart on different port)
- **Example:** `mybb_server_restart()` or `mybb_server_restart(port=8023)`
- **Related:** `mybb_server_start`, `mybb_server_stop`

---

### 11. Workspace Git (7 tools)

**Type Parameter (applies to all tools below):**
- `type="plugin"` (default) — for plugins, uses `visibility` param (public/private)
- `type="theme"` (REQUIRED for themes) — themes have no visibility, stored in `plugin_manager/themes/`

**`mybb_workspace_git_list(type)`**
- **Purpose:** List plugin/theme workspaces with git initialized
- **When to use:** Finding git-tracked workspace projects
- **Key params:** `type` ("plugins", "themes", "all")
- **Example:** `mybb_workspace_git_list(type="themes")`
- **Related:** `mybb_workspace_git_status`

**`mybb_workspace_git_init(codename, type, visibility, remote, branch)`**
- **Purpose:** Initialize git in plugin/theme workspace (nested repo)
- **When to use:** Starting version control for workspace
- **Key params:** `codename` (required), `type` ("plugin"|"theme", default "plugin"), `visibility` (plugins only), `branch="main"`
- **Plugin example:** `mybb_workspace_git_init(codename="my_plugin", visibility="private")`
- **Theme example:** `mybb_workspace_git_init(codename="my_theme", type="theme")`
- **Related:** `mybb_workspace_github_create`

**`mybb_workspace_github_create(codename, type, visibility, repo_visibility, repo_name, description)`**
- **Purpose:** Create GitHub repo + link to plugin/theme workspace (requires `gh` CLI)
- **When to use:** Publishing workspace to GitHub
- **Key params:** `codename` (required), `type` ("plugin"|"theme"), `repo_visibility` ("public"|"private")
- **Plugin example:** `mybb_workspace_github_create(codename="my_plugin", visibility="private", repo_visibility="public")`
- **Theme example:** `mybb_workspace_github_create(codename="my_theme", type="theme", repo_visibility="public")`
- **Related:** `mybb_workspace_git_init`, `mybb_workspace_git_push`

**`mybb_workspace_git_status(codename, type, visibility)`**
- **Purpose:** Get git status for plugin/theme workspace
- **When to use:** Checking uncommitted workspace changes
- **Key params:** `codename` (required), `type` ("plugin"|"theme"), `visibility` (plugins only)
- **Plugin example:** `mybb_workspace_git_status(codename="my_plugin")`
- **Theme example:** `mybb_workspace_git_status(codename="my_theme", type="theme")`
- **Related:** `mybb_workspace_git_commit`

**`mybb_workspace_git_commit(codename, message, type, visibility, files)`**
- **Purpose:** Commit changes in plugin/theme workspace repo
- **When to use:** Committing workspace changes
- **Key params:** `codename` (required), `message` (required), `type` ("plugin"|"theme"), `files=[]` (optional: specific files)
- **Plugin example:** `mybb_workspace_git_commit(codename="my_plugin", message="feat: Add feature")`
- **Theme example:** `mybb_workspace_git_commit(codename="my_theme", type="theme", message="Update styles")`
- **Related:** `mybb_workspace_git_push`

**`mybb_workspace_git_push(codename, type, visibility, set_upstream)`**
- **Purpose:** Push workspace commits to remote
- **When to use:** Publishing workspace commits
- **Key params:** `codename` (required), `type` ("plugin"|"theme"), `set_upstream=False`
- **Plugin example:** `mybb_workspace_git_push(codename="my_plugin", set_upstream=True)`
- **Theme example:** `mybb_workspace_git_push(codename="my_theme", type="theme")`
- **Related:** `mybb_workspace_git_pull`

**`mybb_workspace_git_pull(codename, type, visibility)`**
- **Purpose:** Pull workspace changes from remote
- **When to use:** Syncing workspace with remote repo
- **Key params:** `codename` (required), `type` ("plugin"|"theme"), `visibility` (plugins only)
- **Plugin example:** `mybb_workspace_git_pull(codename="my_plugin")`
- **Theme example:** `mybb_workspace_git_pull(codename="my_theme", type="theme")`
- **Related:** `mybb_workspace_git_push`

---

### 12. Language Validation (3 tools)

**`mybb_lang_validate(codename, include_templates, fix_suggestions)`**
- **Purpose:** **PRIMARY TOOL** - validate language files for plugin
- **When to use:** Before committing, during development
- **Key params:** `codename` (required), `include_templates=True` (scan for {$lang->x}), `fix_suggestions=True`
- **Finds:**
  - Missing definitions (code uses $lang->x but not defined)
  - Unused definitions
  - Potential typos
- **Example:** `mybb_lang_validate("my_plugin")`
- **Output:** Analysis + suggestions
- **Related:** `mybb_lang_generate_stub`

**`mybb_lang_generate_stub(codename, output, default_values)`**
- **Purpose:** Generate missing language definitions as PHP code
- **When to use:** After `mybb_lang_validate` finds missing keys
- **Key params:**
  - `codename` (required)
  - `output="stub"` (or "patch", "inline")
  - `default_values="placeholder"` (or "empty", "key_as_value")
- **Example:** `mybb_lang_generate_stub("my_plugin", output="stub")`
- **Output:** PHP code to copy into language file
- **Related:** `mybb_lang_validate`

**`mybb_lang_scan_usage(path, output)`**
- **Purpose:** Low-level tool - scan files for $lang->x and {$lang->x} usage
- **When to use:** Exploring language usage in any path (not just plugins)
- **Key params:** `path` (required, file or directory), `output="grouped"` (or "list", "json")
- **Example:** `mybb_lang_scan_usage("plugin_manager/plugins/public/my_plugin", output="grouped")`
- **Output:** List of language keys found
- **Related:** `mybb_lang_validate`

---

### 13. Database (1 tool)

**`mybb_db_query(query)`**
- **Purpose:** Execute read-only SQL SELECT query
- **When to use:** **LAST RESORT** - when no specialized tool exists
- **Key params:** `query` (SQL SELECT statement)
- **Restrictions:** Read-only, no INSERT/UPDATE/DELETE
- **Example:** `mybb_db_query("SELECT * FROM mybb_plugins WHERE active=1")`
- **Note:** Prefer specialized tools (mybb_plugin_list_installed, mybb_forum_list, etc.)
- **Related:** All other tools (prefer over raw queries)

---

## Workflow Recipes

### Recipe 1: Full Plugin Development Cycle

**Goal:** Create a new plugin from scratch, deploy, test, iterate

```python
# 1. CREATE PLUGIN
mybb_create_plugin(
    codename="welcome_banner",
    name="Welcome Banner",
    description="Shows a welcome message on index",
    hooks=["index_start"],
    has_settings=True,
    has_templates=True
)
# Creates workspace at plugin_manager/plugins/public/welcome_banner/

# 2. DEVELOP (edit files in workspace)
# - welcome_banner.php (main plugin)
# - templates/welcome_banner_message.html
# - inc/languages/english/welcome_banner.lang.php

# 3. VALIDATE LANGUAGE FILES
mybb_lang_validate("welcome_banner")
# If missing keys found:
mybb_lang_generate_stub("welcome_banner", output="stub")
# Copy generated code into language file

# 4. DEPLOY
mybb_plugin_install("welcome_banner")
# Deploys files + runs _install() + _activate()

# 5. TEST IN BROWSER
mybb_server_status()  # Ensure server running
# Visit http://localhost:8022

# 6. CHECK FOR ERRORS
mybb_server_logs(errors_only=True, limit=20)

# 7. UPDATE TEMPLATE (requires full reinstall)
# Edit workspace/templates/welcome_banner_message.html
mybb_plugin_uninstall("welcome_banner", remove_files=True)
mybb_plugin_install("welcome_banner")

# 8. VERSION CONTROL (optional) - type defaults to "plugin"
mybb_workspace_git_init(codename="welcome_banner", visibility="private")
mybb_workspace_github_create(codename="welcome_banner", repo_visibility="public")
mybb_workspace_git_commit(codename="welcome_banner", message="feat: Initial release")
mybb_workspace_git_push(codename="welcome_banner", set_upstream=True)

# 9. CLEANUP (if needed)
mybb_plugin_uninstall("welcome_banner", uninstall=True, remove_files=True)
mybb_delete_plugin("welcome_banner", archive=True)
```

---

### Recipe 2: Debug a Broken Plugin

**Goal:** Plugin isn't working, need to diagnose and fix

```python
# 1. CHECK SERVER LOGS FIRST (most common issues are PHP errors)
mybb_server_logs(errors_only=True, limit=50)
# Look for: Fatal errors, Parse errors, Warnings in your plugin file

# 2. CHECK PLUGIN STATUS
mybb_plugin_status("my_plugin")
# Shows: installed state, activation state, compatibility, info

# 3. VERIFY PLUGIN EXISTS
mybb_plugin_is_installed("my_plugin")
# If False → plugin not installed/active

# 4. ANALYZE PLUGIN STRUCTURE
mybb_analyze_plugin("my_plugin")
# Shows: hooks registered, settings, templates, tables

# 5. VERIFY HOOK EXISTS (if hook not firing)
mybb_hooks_discover(search="index_start")
# Or search specific file:
mybb_hooks_discover(path="index.php")

# 6. CHECK OTHER PLUGINS USING SAME HOOK
mybb_hooks_usage("index_start")
# See patterns, check for conflicts

# 7. VALIDATE LANGUAGE FILES
mybb_lang_validate("my_plugin")
# Missing definitions can cause errors

# 8. CHECK DATABASE (if needed)
mybb_db_query("SELECT * FROM mybb_plugins WHERE codename='my_plugin'")

# 9. COMMON FIXES
# - PHP error → Fix code, reinstall
# - Template not showing → Full reinstall (uninstall + install)
# - Hook not firing → Check function name matches hook
# - Settings missing → Check _install() creates them
```

---

### Recipe 3: Set Up Template Development

**Goal:** Edit core MyBB templates with live file sync

```python
# 1. EXPORT TEMPLATES TO DISK (if not already)
mybb_sync_export_templates("Default Templates")
# Creates files in mybb_sync/template_sets/Default Templates/

# 2. START FILE WATCHER
mybb_sync_start_watcher()
# Auto-syncs changes from disk to database

# 3. CHECK WATCHER STATUS
mybb_sync_status()
# Verify watcher is running

# 4. FIND TEMPLATE TO EDIT
mybb_list_templates(search="header")
# Or browse by group:
mybb_list_template_groups()

# 5. READ TEMPLATE (optional, to understand structure)
mybb_read_template("header")

# 6. EDIT FILE ON DISK
# Edit: mybb_sync/template_sets/Default Templates/{group}/header.html
# Watcher auto-syncs to database

# 7. TEST IN BROWSER
# Refresh http://localhost:8022
# Changes appear immediately

# 8. CHECK FOR TEMPLATE ERRORS
mybb_server_logs(errors_only=True, filter_keyword="template")

# 9. STOP WATCHER WHEN DONE
mybb_sync_stop_watcher()

# NOTES:
# - Never use mybb_write_template during development
# - Cortex syntax for conditionals: <if condition>...</if>
# - See CORTEX.md for full syntax reference
```

---

### Recipe 4: Content Management Workflow

**Goal:** Create test forum structure with threads and posts

```python
# 1. LIST EXISTING FORUMS
mybb_forum_list()

# 2. CREATE CATEGORY
cat_id = mybb_forum_create(name="Test Category", type="c")

# 3. CREATE FORUMS IN CATEGORY
forum1 = mybb_forum_create(
    name="General Discussion",
    description="Talk about anything",
    type="f",
    pid=cat_id
)

forum2 = mybb_forum_create(
    name="Bug Reports",
    description="Report issues here",
    type="f",
    pid=cat_id
)

# 4. CREATE THREADS
thread1 = mybb_thread_create(
    fid=forum1,
    subject="Welcome to the forum!",
    message="This is the first post. Use BBCode here.",
    username="Admin"
)

thread2 = mybb_thread_create(
    fid=forum2,
    subject="Bug: Login broken",
    message="Steps to reproduce...",
    username="TestUser"
)

# 5. ADD REPLIES
mybb_post_create(
    tid=thread1,
    message="Thanks for joining!",
    username="Moderator"
)

mybb_post_create(
    tid=thread2,
    message="Fixed in version 1.1",
    username="Developer",
    replyto=0  # Top-level reply
)

# 6. MODERATE CONTENT
mybb_mod_stick_thread(thread1, sticky=True)
mybb_mod_close_thread(thread2, closed=True)

# 7. SEARCH CONTENT
mybb_search_posts("login", forums=[forum2])
mybb_search_threads("welcome", forums=[forum1])

# 8. MOVE THREAD TO DIFFERENT FORUM
mybb_thread_move(tid=thread2, new_fid=forum1)

# 9. SOFT DELETE (recoverable)
mybb_post_delete(pid=5, soft=True)
mybb_thread_delete(tid=3, soft=True)

# 10. RESTORE DELETED
mybb_post_delete(pid=5, restore=True)

# 11. CHECK STATS
mybb_stats_board()
```

---

### Recipe 5: User Moderation Workflow

**Goal:** Manage users, permissions, and moderation actions

```python
# 1. LIST ALL USERGROUPS
mybb_usergroup_list()
# Find IDs for: Registered (2), Moderators (6), Banned (7), etc.

# 2. SEARCH FOR USER
mybb_search_users("testuser", field="username")
# Or:
mybb_user_get(username="testuser")
mybb_user_get(uid=5)

# 3. LIST USERS IN GROUP
mybb_user_list(usergroup=2, limit=10)  # Registered users

# 4. PROMOTE USER TO MODERATOR
mybb_user_update_group(
    uid=5,
    usergroup=6,  # Moderators
    additionalgroups="2"  # Keep registered group
)

# 5. BAN USER
import time
mybb_user_ban(
    uid=10,
    gid=7,  # Banned Users group
    admin=1,  # Admin performing ban
    dateline=int(time.time()),
    bantime="perm",
    reason="Spamming"
)

# 6. UNBAN USER
mybb_user_unban(uid=10)

# 7. MODERATE CONTENT
mybb_mod_approve_post(pid=15, approve=False)  # Unapprove
mybb_mod_soft_delete_post(pid=15, delete=True)  # Soft delete

# 8. VIEW MODERATION LOG
mybb_modlog_list(uid=1, limit=20)  # Actions by admin
mybb_modlog_list(fid=2, limit=20)  # Actions in forum 2

# 9. ADD CUSTOM MOD ACTION
mybb_modlog_add(
    uid=1,
    action="Merged duplicate threads",
    fid=2,
    tid=10
)

# 10. CHECK USER STATS
mybb_stats_forum()  # Includes newest member info
```

---

## Pro Tips

### Most Frequently Used Tools (by workflow stage)

**Initial Setup:**
1. `mybb_server_start` - Start development server
2. `mybb_server_status` - Check if running
3. `mybb_sync_export_templates` - Get templates on disk

**Plugin Development:**
1. `mybb_create_plugin` - Create new plugin
2. `mybb_plugin_install` - Deploy to TestForum
3. `mybb_plugin_status` - Check installation state
4. `mybb_plugin_uninstall` - Remove for reinstall
5. `mybb_lang_validate` - Validate language files

**Debugging:**
1. `mybb_server_logs(errors_only=True)` - **#1 DEBUGGING TOOL**
2. `mybb_plugin_status` - Plugin state
3. `mybb_hooks_discover` - Verify hooks exist
4. `mybb_analyze_plugin` - Inspect structure

**Template Work:**
1. `mybb_sync_start_watcher` - Enable auto-sync
2. `mybb_sync_status` - Check watcher
3. `mybb_list_templates` - Find templates

### Common Pitfalls

**1. Template updates not showing**
- Did you do full reinstall? (uninstall + install)
- Is watcher running? (mybb_sync_status)
- Did you edit workspace files, not TestForum?

**2. Plugin "not found" but files exist**
- Check workspace vs TestForum distinction
- Run mybb_plugin_status to see actual state
- Workspace is source, TestForum is deploy target

**3. Hook not firing**
- Verify hook exists: mybb_hooks_discover
- Check function name: {codename}_{hookname}
- Ensure plugin is activated, not just installed

**4. PHP errors after changes**
- Always check logs FIRST: mybb_server_logs(errors_only=True)
- Use filter_keyword to narrow down
- Check recent errors: since_minutes=5

**5. Forgot to validate language files**
- Run mybb_lang_validate before every commit
- Missing definitions cause runtime errors
- Use mybb_lang_generate_stub to create stubs

### Performance Tips

**Use batch operations when possible:**
- `mybb_template_batch_read` instead of multiple reads
- `mybb_search_advanced` instead of separate post/thread searches
- `mybb_thread_create` is atomic (creates thread + first post)

**Limit results appropriately:**
- Default limits are usually 25-50
- Use pagination (offset/limit) for large datasets
- Search tools max out at 100 results

**Cache management:**
- Rebuild specific caches instead of "all"
- Settings cache auto-rebuilds on mybb_setting_set
- Clear cache after direct DB modifications

---

## When to Use Which Tool

### Template Operations

| Goal | Tool | Notes |
|------|------|-------|
| Get templates on disk | `mybb_sync_export_templates` | First step |
| Enable auto-sync | `mybb_sync_start_watcher` | Second step |
| Find template by name | `mybb_list_templates(search="...")` | Before reading |
| View template code | `mybb_read_template` | Inspection |
| Edit core templates | Edit files in `mybb_sync/` | With watcher running |
| Edit plugin templates | Edit workspace files + reinstall | Full uninstall/install |

### Plugin Operations

| Goal | Tool | Notes |
|------|------|-------|
| Create new plugin | `mybb_create_plugin` | Primary tool |
| Deploy plugin | `mybb_plugin_install` | Runs lifecycle |
| Update templates/language | Uninstall + install | Full cycle required |
| Check plugin state | `mybb_plugin_status` | Primary diagnostic |
| Debug plugin | `mybb_analyze_plugin` | Structure analysis |
| Find available hooks | `mybb_list_hooks` or `mybb_hooks_discover` | Discovery |
| Delete plugin | `mybb_delete_plugin` | Archives by default |

### Debugging Operations

| Goal | Tool | Notes |
|------|------|-------|
| Check for PHP errors | `mybb_server_logs(errors_only=True)` | **FIRST TOOL** |
| Search logs | `mybb_server_logs(filter_keyword="...")` | Narrow down |
| Recent errors only | `mybb_server_logs(since_minutes=5)` | Time-based |
| Check server running | `mybb_server_status` | Port, PID, uptime |
| Verify plugin installed | `mybb_plugin_status` | Full state |
| Verify hook exists | `mybb_hooks_discover` | Dynamic scan |

### Content Operations

| Goal | Tool | Notes |
|------|------|-------|
| Create forum | `mybb_forum_create` | Set type="c" for category |
| Create thread | `mybb_thread_create` | Atomic (includes first post) |
| Reply to thread | `mybb_post_create` | Updates counters |
| Search posts | `mybb_search_posts` | Content search |
| Search threads | `mybb_search_threads` | Subject search |
| Move thread | `mybb_thread_move` | Updates counters |

### Admin Operations

| Goal | Tool | Notes |
|------|------|-------|
| Get setting | `mybb_setting_get` | By name |
| Update setting | `mybb_setting_set` | Auto-rebuilds cache |
| Clear cache | `mybb_cache_rebuild` | After DB changes |
| Get stats | `mybb_stats_board` | Comprehensive |

---

## Additional Resources

**Full parameter documentation:**
- [docs/wiki/mcp_tools/index.md](../../../docs/wiki/mcp_tools/index.md)

**Category-specific docs:**
- [Templates](../../../docs/wiki/mcp_tools/templates.md)
- [Plugins](../../../docs/wiki/mcp_tools/plugins.md)
- [Content (Forums/Threads/Posts)](../../../docs/wiki/mcp_tools/forums_threads_posts.md)
- [Users & Moderation](../../../docs/wiki/mcp_tools/users_moderation.md)
- [Search](../../../docs/wiki/mcp_tools/search.md)
- [Admin & Settings](../../../docs/wiki/mcp_tools/admin_settings.md)
- [Tasks](../../../docs/wiki/mcp_tools/tasks.md)
- [Disk Sync](../../../docs/wiki/mcp_tools/disk_sync.md)
- [Server Orchestration](../../../docs/wiki/mcp_tools/orchestration.md)
- [Language Validation](../../../docs/wiki/mcp_tools/languages.md)
- [Database](../../../docs/wiki/mcp_tools/database.md)

**Best practices:**
- [Plugin Development](../../../docs/wiki/best_practices/plugin_development.md)
- [Theme Development](../../../docs/wiki/best_practices/theme_development.md)

**Template syntax:**
- [CORTEX.md](CORTEX.md) - Cortex template syntax reference
