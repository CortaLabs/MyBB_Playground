# MyBB MCP Plugin and Hook Tools Documentation

Comprehensive guide to the 12 MyBB MCP tools for plugin and hook management.

## Table of Contents

1. [Plugin Management Tools (9)](#plugin-management-tools)
2. [Hook Discovery Tools (3)](#hook-discovery-tools)
3. [Common Workflows](#common-workflows)
4. [Important Warnings](#important-warnings)

---

## Plugin Management Tools

### 1. mybb_list_plugins

**Purpose:** List all plugin files in the `/inc/plugins` directory

**Parameters:** None

**Example:**
```
Tool: mcp__mybb__mybb_list_plugins

Response:
# Plugins (2)

- `hello`
- `test_doc_plugin`
```

**Notes:**
- Shows file-based plugins (not activation status)
- Lists plugins without `.php` extension
- For activation status, use `mybb_plugin_list_installed`

---

### 2. mybb_read_plugin

**Purpose:** Read the complete PHP source code of a plugin

**Parameters:**
- `name` (string, required): Plugin filename without .php extension

**Example:**
```
Tool: mcp__mybb__mybb_read_plugin
Parameters: {"name": "hello"}

Response:
# Plugin: hello

```php
<?php
// Full plugin source code returned...
function hello_info() { ... }
function hello_activate() { ... }
// etc.
```
```

**Notes:**
- Returns full PHP source for analysis
- Useful for understanding plugin structure before modification
- Does NOT execute any code, just reads file

---

### 3. mybb_create_plugin

**Purpose:** Create a new plugin skeleton with proper MyBB structure

**Parameters:**
- `codename` (string, required): Plugin codename (lowercase, underscores)
- `name` (string, required): Display name for plugin
- `description` (string, required): Plugin description
- `author` (string, optional): Author name (default: "Developer")
- `version` (string, optional): Version string (default: "1.0.0")
- `hooks` (array, optional): List of hook names to attach
- `has_settings` (boolean, optional): Create ACP settings (default: false)
- `has_templates` (boolean, optional): Create templates (default: false)
- `has_database` (boolean, optional): Create database table (default: false)

**Example:**
```
Tool: mcp__mybb__mybb_create_plugin
Parameters: {
  "codename": "test_doc_plugin",
  "name": "Test Documentation Plugin",
  "description": "A test plugin for documentation",
  "author": "Scribe Coder",
  "version": "1.0.0",
  "hooks": ["index_start", "global_start"],
  "has_settings": true,
  "has_templates": true,
  "has_database": true
}

Response:
# Plugin Created: Test Documentation Plugin

**Plugin file**: `/inc/plugins/test_doc_plugin.php`
**Language file**: `/inc/languages/english/test_doc_plugin.lang.php`

## Features
- Hooks: index_start, global_start
- Settings: Yes
- Templates: Yes
- Database: Yes
```

**Notes:**
- Creates both plugin file and language file
- Generates all standard MyBB plugin functions (_info, _activate, _deactivate, _install, _uninstall, _is_installed)
- Creates hook handler functions automatically
- Database table uses plugin codename as prefix
- Still requires manual implementation of functionality

---

### 4. mybb_analyze_plugin

**Purpose:** Analyze an existing plugin's structure, hooks, settings, and templates

**Parameters:**
- `name` (string, required): Plugin filename without .php extension

**Example:**
```
Tool: mcp__mybb__mybb_analyze_plugin
Parameters: {"name": "test_doc_plugin"}

Response:
# Plugin Analysis: test_doc_plugin

## Hooks (2)
- `index_start`
- `global_start`

## Has _info: Yes

## Functions (8)
- `test_doc_plugin_info()`
- `test_doc_plugin_activate()`
- `test_doc_plugin_deactivate()`
- `test_doc_plugin_is_installed()`
- `test_doc_plugin_install()`
- `test_doc_plugin_uninstall()`
- `test_doc_plugin_index_start()`
- `test_doc_plugin_global_start()`

## Features
- Settings: Yes
- Templates: Yes
- Database: Yes
```

**Notes:**
- Parses PHP file to extract structure
- Identifies all hooks used by plugin
- Lists all functions defined
- Detects feature flags (settings/templates/database)
- Useful for understanding plugin before modification

---

### 5. mybb_plugin_list_installed

**Purpose:** List currently active/installed plugins from datacache

**Parameters:** None

**Example:**
```
Tool: mcp__mybb__mybb_plugin_list_installed

Response (when no plugins active):
# Installed Plugins

No plugins are currently active.

*Note: This shows plugins from datacache. File-based listing available via mybb_list_plugins.*

Response (when plugins active):
# Installed Plugins

- `hello`
- `test_doc_plugin`
```

**Notes:**
- **IMPORTANT:** Shows only activated plugins (from datacache)
- Different from `mybb_list_plugins` which shows files
- Plugin must be activated to appear here
- Reflects MyBB's runtime plugin state

---

### 6. mybb_plugin_info

**Purpose:** Get plugin metadata by reading the _info() function

**Parameters:**
- `name` (string, required): Plugin codename (without .php)

**Example:**
```
Tool: mcp__mybb__mybb_plugin_info
Parameters: {"name": "test_doc_plugin"}

Response:
# Plugin Info: test_doc_plugin

Name: Test Documentation Plugin
Description: A test plugin for documentation
Version: 1.0.0
Author: Scribe Coder
Compatibility: 18*
Codename: test_doc_plugin
```

**Notes:**
- Executes the plugin's _info() function
- Does NOT require plugin to be installed/activated
- Returns metadata only (name, description, version, author, etc.)
- Safe to call on any plugin file

---

### 7. mybb_plugin_activate

**Purpose:** Activate a plugin via PHP lifecycle (_activate) using the bridge

**Parameters:**
- `name` (string, required): Plugin codename to activate
- `force` (boolean, optional): Skip compatibility check (default: false)

**Example:**
```
Tool: mcp__mybb__mybb_plugin_activate
Parameters: {"name": "test_doc_plugin"}

Response:
# Plugin Activated: test_doc_plugin

**PHP Lifecycle Actions:** activated
```

**Notes:**
- Uses the PHP bridge to run `_activate()` and update plugin cache
- **Requires plugin to be installed** (use `mybb_plugin_install` or `mybb_plugin_deploy(action="reinstall")` first)
- Managed plugins are deployed to TestForum before activation

---

### 8. mybb_plugin_deactivate

**Purpose:** Deactivate a plugin via PHP lifecycle (_deactivate) using the bridge

**Parameters:**
- `name` (string, required): Plugin codename to deactivate

**Example:**
```
Tool: mcp__mybb__mybb_plugin_deactivate
Parameters: {"name": "test_doc_plugin"}

Response:
# Plugin Deactivated: test_doc_plugin

**PHP Lifecycle Actions:** deactivated
```

**Notes:**
- Uses the PHP bridge to run `_deactivate()` and update plugin cache
- Does not run `_uninstall()` (use `mybb_plugin_uninstall` or deploy reinstall)

---

### 9. mybb_plugin_deploy

**Purpose:** Wrapper for activate/deactivate or full reinstall

**Parameters:**
- `codename` (string, required): Plugin codename
- `action` (string, required): `activate`, `deactivate`, or `reinstall`
- `force` (boolean, optional): Skip compatibility check (default: false)

**Example (full reinstall):**
```
Tool: mcp__mybb__mybb_plugin_deploy
Parameters: {"codename": "test_doc_plugin", "action": "reinstall"}
```

**Notes:**
- `reinstall` runs: deactivate + uninstall + remove files + install + activate
- Use when you need a clean redeploy without manual steps

---

### 10. mybb_plugin_is_installed

**Purpose:** Check if a plugin is currently installed/active

**Parameters:**
- `name` (string, required): Plugin codename to check

**Example:**
```
Tool: mcp__mybb__mybb_plugin_is_installed
Parameters: {"name": "test_doc_plugin"}

Response (when active):
# Plugin Status: test_doc_plugin

**Status**: Active

Plugin is currently in the active plugins cache.

Response (when not active):
# Plugin Status: test_doc_plugin

**Status**: Not Active

Plugin is not in the active plugins cache.
```

**Notes:**
- Checks datacache only (not file system)
- Returns quick boolean status
- Useful for conditional logic in workflows
- Does NOT check _is_installed() function, only cache

---

## Hook Discovery Tools

### 11. mybb_list_hooks

**Purpose:** List available MyBB hooks organized by category

**Parameters:**
- `category` (string, optional): Filter by category prefix (e.g., 'admin', 'usercp')
- `search` (string, optional): Search term for hook names

**Example:**
```
Tool: mcp__mybb__mybb_list_hooks

Response:
# MyBB Hooks Reference

### Index
- `index_start`
- `index_end`
- `build_forumbits_forum`

### Showthread
- `showthread_start`
- `showthread_end`
- `postbit`
- `postbit_prev`
- `postbit_pm`

### Member
- `member_profile_start`
- `member_profile_end`
- `member_register_start`

### Global
- `global_start`
- `global_end`
- `global_intermediate`

[...more categories...]

---
*Full list: https://docs.mybb.com/1.8/development/plugins/hooks/*
```

**Notes:**
- Returns categorized static hook list
- Based on MyBB documentation
- Use for discovering available integration points
- Categories: Index, Showthread, Member, Usercp, Admin, Global, etc.
- 60+ hooks available

---

### 11. mybb_hooks_discover

**Purpose:** Dynamically discover hooks in MyBB installation by scanning PHP files for $plugins->run_hooks() calls

**Parameters:**
- `category` (string, optional): Filter by category prefix (e.g., 'admin', 'usercp')
- `path` (string, optional): Specific PHP file to scan (relative to MyBB root)
- `search` (string, optional): Search term to filter hook names

**Example:**
```
Tool: mcp__mybb__mybb_hooks_discover
Parameters: {"category": "index"}

Response:
# Discovered 2 MyBB Hooks

| Hook Name | File | Line |
|-----------|------|------|
| `index_end` | index.php | 466 |
| `index_start` | index.php | 26 |
```

**Notes:**
- Scans actual MyBB source code (not static list)
- Finds $plugins->run_hooks() calls
- Returns file location and line number
- Useful for finding exact hook placement
- Can discover undocumented hooks
- Category filter narrows results

---

### 12. mybb_hooks_usage

**Purpose:** Find where a specific hook is used in installed plugins by scanning for $plugins->add_hook() calls

**Parameters:**
- `hook_name` (string, required): Name of the hook to search for

**Example:**
```
Tool: mcp__mybb__mybb_hooks_usage
Parameters: {"hook_name": "index_start"}

Response:
# Hook Usage: `index_start`

Found 2 usage(s) in installed plugins:

### hello.php
- **Function**: `hello_index`
- **Priority**: 10
- **Line**: 49

### test_doc_plugin.php
- **Function**: `test_doc_plugin_index_start`
- **Priority**: 10
- **Line**: 27
```

**Notes:**
- Scans all plugin files for $plugins->add_hook() calls
- Shows which plugins use the hook
- Includes callback function name
- Shows priority (for execution order)
- Includes line number in plugin file
- **Use case:** Detect hook conflicts or understand plugin interactions

---

## Common Workflows

### Creating a New Plugin

1. **Create plugin skeleton:**
   ```
   mybb_create_plugin(
     codename="my_plugin",
     name="My Plugin",
     description="Plugin description",
     hooks=["index_start", "postbit"],
     has_settings=true,
     has_templates=true
   )
   ```

2. **Read generated code:**
   ```
   mybb_read_plugin(name="my_plugin")
   ```

3. **Analyze structure:**
   ```
   mybb_analyze_plugin(name="my_plugin")
   ```

4. **Edit plugin file** (add functionality)

5. **Install via MyBB Admin CP** (not MCP tools)

---

### Understanding Existing Plugin

1. **Check if plugin exists:**
   ```
   mybb_list_plugins()
   ```

2. **Read plugin source:**
   ```
   mybb_read_plugin(name="hello")
   ```

3. **Analyze structure:**
   ```
   mybb_analyze_plugin(name="hello")
   ```

4. **Check activation status:**
   ```
   mybb_plugin_is_installed(name="hello")
   ```

5. **Find which hooks it uses:**
   Look at analyze output, or read source for $plugins->add_hook() calls

---

### Finding Hook Integration Points

1. **List all available hooks:**
   ```
   mybb_list_hooks()
   ```

2. **Discover specific category hooks:**
   ```
   mybb_hooks_discover(category="admin")
   ```

3. **Find where hook is defined in MyBB:**
   ```
   mybb_hooks_discover(search="index_start")
   ```
   Result shows: `index.php` line 26

4. **See which plugins use this hook:**
   ```
   mybb_hooks_usage(hook_name="index_start")
   ```

5. **Check for conflicts** (multiple plugins on same hook)

---

### Debugging Plugin Conflicts

1. **Find all plugins using a hook:**
   ```
   mybb_hooks_usage(hook_name="postbit")
   ```

2. **Check priorities** (from output above)

3. **Analyze each conflicting plugin:**
   ```
   mybb_analyze_plugin(name="plugin1")
   mybb_analyze_plugin(name="plugin2")
   ```

4. **Read source to understand behavior:**
   ```
   mybb_read_plugin(name="plugin1")
   ```

---

## Important Warnings

### ⚠️ Activation/Deactivation Tools Use the Bridge

`mybb_plugin_activate` and `mybb_plugin_deactivate` now execute PHP lifecycle via the CLI bridge.

**Key behavior:**
- Runs `_activate()` / `_deactivate()` and updates plugin cache
- **Does NOT run** `_install()` or `_uninstall()` (use install/uninstall or deploy)
- Requires the plugin to already be installed

**Best practice:**
- Use `mybb_plugin_install` for DB setup (_install + activate)
- Use `mybb_plugin_deploy(action="reinstall")` for a full clean cycle
- Use MyBB Admin CP when you need manual UI confirmation

---

### 🔍 Datacache vs File System

**Two different views of plugins:**

1. **File system** (`mybb_list_plugins`): Shows all .php files in /inc/plugins
2. **Datacache** (`mybb_plugin_list_installed`): Shows active plugins in MyBB runtime

**A plugin can exist in files but not be active!**

Example:
- `mybb_list_plugins()` → Shows: hello, test_doc_plugin
- `mybb_plugin_list_installed()` → Shows: (none)
- Explanation: Plugins exist as files but haven't been activated

**Always check both** when troubleshooting:
1. Is plugin file present? → `mybb_list_plugins()`
2. Is plugin activated? → `mybb_plugin_list_installed()`

---

### 📝 Hook Discovery Methods

**Two tools, different purposes:**

1. **mybb_list_hooks()** - Static reference
   - Shows documented hooks
   - Organized by category
   - Quick reference for common hooks
   - **Use when:** Planning plugin, looking for standard integration points

2. **mybb_hooks_discover()** - Dynamic scanning
   - Scans actual MyBB source code
   - Shows $plugins->run_hooks() locations
   - Finds file and line number
   - Can discover undocumented hooks
   - **Use when:** Need exact hook location, finding all hooks in a file

**Best practice:** Use both
- Start with `mybb_list_hooks()` for quick reference
- Use `mybb_hooks_discover()` to find exact placement

---

### 🔧 Plugin Creation Tips

**When using mybb_create_plugin:**

1. **Plan your hooks first** - Use `mybb_list_hooks()` to find appropriate hooks
2. **Enable features you need:**
   - `has_settings=true` → Creates settings group framework
   - `has_templates=true` → Creates template group framework
   - `has_database=true` → Creates table creation code

3. **Generated code is a skeleton:**
   - You MUST add actual functionality
   - Hook functions are empty placeholders
   - Settings/templates are examples
   - Database schema is basic

4. **Test incrementally:**
   - Create plugin
   - Add one feature
   - Test via Admin CP
   - Repeat

---

### 🐛 Common Pitfalls

1. **Activating without installing first**
   - ❌ `mybb_plugin_activate()` on an uninstalled plugin → fails or missing DB setup
   - ✅ Use `mybb_plugin_install()` or `mybb_plugin_deploy(action="reinstall")` first

2. **Confusing file listing with activation status**
   - ❌ "Plugin shows in `mybb_list_plugins()` so it's active"
   - ✅ Check `mybb_plugin_is_installed()` for activation status

3. **Not checking hook conflicts**
   - ❌ Add hook without checking existing usage
   - ✅ Use `mybb_hooks_usage()` before adding hook

4. **Editing plugin without analyzing first**
   - ❌ Directly edit plugin code
   - ✅ Use `mybb_analyze_plugin()` and `mybb_read_plugin()` to understand structure

5. **Forgetting plugin codename conventions**
   - ❌ Using spaces or capitals in codename
   - ✅ Use lowercase with underscores: `my_plugin_name`

---

## Quick Reference Table

| Tool | Purpose | Requires Plugin Active? | Modifies Database? |
|------|---------|-------------------------|-------------------|
| mybb_list_plugins | List plugin files | No | No |
| mybb_read_plugin | Read source code | No | No |
| mybb_create_plugin | Create new plugin | No | No (creates file) |
| mybb_analyze_plugin | Analyze structure | No | No |
| mybb_plugin_list_installed | List active plugins | No | No |
| mybb_plugin_info | Get metadata | No | No |
| mybb_plugin_activate | Activate (PHP lifecycle) | No | Yes (PHP lifecycle) |
| mybb_plugin_deactivate | Deactivate (PHP lifecycle) | No | Yes (PHP lifecycle) |
| mybb_plugin_deploy | Wrapper (activate/deactivate/reinstall) | No | Yes (lifecycle) |
| mybb_plugin_is_installed | Check status | No | No |
| mybb_list_hooks | List hooks (static) | No | No |
| mybb_hooks_discover | Find hooks (scan) | No | No |
| mybb_hooks_usage | Find plugin usage | No | No |

---

## Additional Resources

- **MyBB Plugin Development:** https://docs.mybb.com/1.8/development/plugins/
- **MyBB Hooks Reference:** https://docs.mybb.com/1.8/development/plugins/hooks/
- **MyBB Database Methods:** https://docs.mybb.com/1.8/development/database-methods/

---

**Last Updated:** 2026-01-21
**Tested With:** MyBB 1.8.x
**MCP Version:** Latest
