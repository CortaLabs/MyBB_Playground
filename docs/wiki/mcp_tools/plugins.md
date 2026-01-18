# Plugin Tools

Plugin development tools for creating, managing, and analyzing MyBB plugins.

## Overview

The MyBB MCP Server provides comprehensive plugin management tools covering:
- Plugin listing and inspection
- Plugin creation with scaffolding
- Hook discovery and analysis
- Plugin lifecycle management (install, activate, deactivate, uninstall)
- Plugin structure analysis

## Tool Reference

### mybb_list_plugins

List all plugins in the MyBB plugins directory.

**Parameters:** None

**Returns:** Markdown table of plugins with filenames

**Example:**
```
List all available plugins
```

---

### mybb_read_plugin

Read a plugin's PHP source code.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| name | string | Yes | - | Plugin filename (without .php) |

**Returns:** Full PHP source code of the plugin

**Example:**
```
Read the hello_banner plugin code
```

---

### mybb_create_plugin

Create a new MyBB plugin with proper structure, hooks, settings, templates, and database tables.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| codename | string | Yes | - | Plugin codename (lowercase, underscores) |
| name | string | Yes | - | Plugin display name |
| description | string | Yes | - | Plugin description |
| author | string | No | "Developer" | Author name |
| version | string | No | "1.0.0" | Version number |
| visibility | string | No | "public" | Visibility: "public" (shareable) or "private" (personal) |
| hooks | array[string] | No | [] | Hook names to attach (e.g., "index_start", "postbit") |
| has_settings | boolean | No | false | Create ACP settings |
| has_templates | boolean | No | false | Create templates |
| has_database | boolean | No | false | Create database table |

**Returns:** Confirmation message with file paths

**Behavior:** Generates complete plugin scaffold with proper MyBB structure including _info(), _install(), _activate(), _deactivate(), _uninstall(), and _is_installed() functions.

**Example:**
```
Create a plugin called "welcome_message" with index_start hook and ACP settings
```

---

### mybb_list_hooks

List available MyBB hooks for plugin development.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| category | string | No | - | Hook category (index, showthread, member, admin, global, etc.) |
| search | string | No | - | Search term to filter hooks |

**Returns:** Formatted list of available hooks with categories

**Example:**
```
List all hooks in the index category
```

---

### mybb_hooks_discover

Dynamically discover hooks in the MyBB installation by scanning PHP files for `$plugins->run_hooks()` calls.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| path | string | No | - | Specific PHP file to scan (relative to MyBB root) |
| category | string | No | - | Filter by category prefix (e.g., "admin", "usercp") |
| search | string | No | - | Search term to filter hook names |

**Returns:** List of discovered hooks from actual MyBB source files

**Example:**
```
Discover all hooks in the admin control panel
```

---

### mybb_hooks_usage

Find where a specific hook is used in installed plugins by scanning for `$plugins->add_hook()` calls.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| hook_name | string | Yes | - | Name of the hook to search for |

**Returns:** List of plugins using this hook with file locations

**Example:**
```
Find which plugins use the index_start hook
```

---

### mybb_analyze_plugin

Analyze an existing plugin's structure, hooks, settings, and templates.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| name | string | Yes | - | Plugin filename (without .php) |

**Returns:** Detailed analysis including:
- Plugin info (_info() function data)
- Registered hooks
- Settings configuration
- Template usage
- Database tables

**Example:**
```
Analyze the structure of the hello_banner plugin
```

---

### mybb_plugin_list_installed

List installed/active plugins from the MyBB datacache.

**Parameters:** None

**Returns:** List of currently active plugins with their status

**Example:**
```
Show all installed plugins
```

---

### mybb_plugin_info

Get plugin metadata by reading the `_info()` function from the plugin file.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| name | string | Yes | - | Plugin codename (without .php) |

**Returns:** Plugin metadata including:
- Name and description
- Author and website
- Version and compatibility
- GUID

**Example:**
```
Get info for the hello_banner plugin
```

---

### mybb_plugin_activate

Activate a plugin by adding it to the active plugins cache.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| name | string | Yes | - | Plugin codename to activate |

**Returns:** Confirmation message

**Important:** This does NOT execute the PHP `_activate()` function - it only updates the cache. For full activation with PHP execution, use `mybb_plugin_install`.

**Example:**
```
Activate the hello_banner plugin
```

---

### mybb_plugin_deactivate

Deactivate a plugin by removing it from the active plugins cache.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| name | string | Yes | - | Plugin codename to deactivate |

**Returns:** Confirmation message

**Important:** This does NOT execute the PHP `_deactivate()` function - it only updates the cache. For full deactivation with PHP execution, use `mybb_plugin_uninstall`.

**Example:**
```
Deactivate the hello_banner plugin
```

---

### mybb_plugin_is_installed

Check if a plugin is currently installed/active.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| name | string | Yes | - | Plugin codename to check |

**Returns:** Boolean status (installed/active or not)

**Example:**
```
Check if hello_banner is installed
```

---

### mybb_plugin_install

Full plugin installation: deploy files from workspace AND execute PHP lifecycle functions (_install, _activate).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| codename | string | Yes | - | Plugin codename (without .php) |
| force | boolean | No | false | Skip MyBB compatibility check |

**Returns:** Confirmation message with installation details

**Behavior:**
- Deploys plugin files from plugin_manager workspace to TestForum
- Executes PHP `_install()` function (creates settings, templates, database tables)
- Executes PHP `_activate()` function (registers hooks, enables plugin)
- This runs actual PHP code, unlike `mybb_plugin_activate` which only updates cache

**Example:**
```
Install the hello_banner plugin with full PHP lifecycle execution
```

---

### mybb_plugin_uninstall

Full plugin uninstallation: execute PHP lifecycle functions (_deactivate, optionally _uninstall) AND optionally remove files.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| codename | string | Yes | - | Plugin codename (without .php) |
| uninstall | boolean | No | false | Also run _uninstall() to remove settings/tables |
| remove_files | boolean | No | false | Also remove plugin files from TestForum |

**Returns:** Confirmation message with uninstallation details

**Behavior:**
- Executes PHP `_deactivate()` function (unregisters hooks, disables plugin)
- If `uninstall=true`: executes PHP `_uninstall()` function (removes settings, templates, database tables)
- If `remove_files=true`: removes plugin files from TestForum
- This runs actual PHP code, unlike `mybb_plugin_deactivate` which only updates cache

**Example:**
```
Uninstall the hello_banner plugin completely, removing all settings and files
```

---

### mybb_plugin_status

Get comprehensive plugin status via PHP bridge.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| codename | string | Yes | - | Plugin codename (without .php) |

**Returns:** Comprehensive status including:
- Installation state (installed or not)
- Activation state (active or not)
- Compatibility information
- Plugin info metadata

**Behavior:** Uses PHP bridge to query actual MyBB state, not just cache

**Example:**
```
Get full status of the hello_banner plugin
```

---

## Lifecycle Comparison

### Cache-Only Operations
- `mybb_plugin_activate` - Updates cache only, no PHP execution
- `mybb_plugin_deactivate` - Updates cache only, no PHP execution
- `mybb_plugin_is_installed` - Checks cache only

### Full PHP Lifecycle Operations
- `mybb_plugin_install` - Deploys files + runs _install() + runs _activate()
- `mybb_plugin_uninstall` - Runs _deactivate() + optionally runs _uninstall() + optionally removes files
- `mybb_plugin_status` - Queries via PHP bridge for accurate state

**Recommendation:** Use full lifecycle operations (`mybb_plugin_install`, `mybb_plugin_uninstall`) for proper plugin management. Cache-only operations are legacy tools primarily for testing.

---

## Related Documentation

- [Plugin Manager System](/docs/wiki/plugin_manager/index.md)
- [Plugin Manager Workspace](/docs/wiki/plugin_manager/workspace.md)
- [Plugin Deployment](/docs/wiki/plugin_manager/deployment.md)
- [Template Tools](/docs/wiki/mcp_tools/templates.md)
- [Theme & Stylesheet Tools](/docs/wiki/mcp_tools/themes_stylesheets.md)
