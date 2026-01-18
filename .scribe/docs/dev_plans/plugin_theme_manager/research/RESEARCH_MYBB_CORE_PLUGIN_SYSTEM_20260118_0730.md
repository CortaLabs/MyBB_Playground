# MyBB Core Plugin System - Deep Dive Research

**Date:** 2026-01-18 07:30 UTC
**Researcher:** ResearchAgent
**Confidence:** 0.95
**Scope:** Plugin loading, hook registration, lifecycle management

## Executive Summary

MyBB uses a class-based plugin system (`pluginSystem` in `class_plugins.php`) that:
1. **Loads plugins** from cache at boot time (init.php:264)
2. **Registers hooks** via `add_hook()` - called directly from plugin files when included
3. **Executes hooks** via priority-ordered `run_hooks()` function that can accept both function names and class methods
4. **Manages cache** through datacache system storing serialized plugin list with active plugins array
5. **Executes lifecycle functions** (`_info`, `_activate`, `_deactivate`, `_install`, `_uninstall`, `_is_installed`) via direct `call_user_func()` in admin CP

## Architecture: The Plugin Lifecycle

### 1. Plugin Loading (class_plugins.php:27-42)

```php
function load()
{
    global $cache, $plugins;

    $plugin_list = $cache->read("plugins");
    if(!empty($plugin_list['active']) && is_array($plugin_list['active']))
    {
        foreach($plugin_list['active'] as $plugin)
        {
            if($plugin != "" && file_exists(MYBB_ROOT."inc/plugins/".$plugin.".php"))
            {
                require_once MYBB_ROOT."inc/plugins/".$plugin.".php";
            }
        }
    }
}
```

**Key Facts:**
- Plugins are loaded **only if marked as active in cache**
- Cache key: `plugins['active']` - array of plugin codenames
- Plugin files must exist at `/inc/plugins/{codename}.php`
- Plugins are loaded via `require_once` - **they execute immediately upon inclusion**
- Called from `init.php:264` after cache initialization but before main application logic

### 2. Hook System (class_plugins.php:53-155)

#### Hook Registration: `add_hook()`
```php
function add_hook($hook, $function, $priority=10, $file="")
```

**Supports Two Hook Types:**

**A. Simple Function Hooks:**
```php
$plugins->add_hook('index_start', 'my_plugin_index_handler');
```
Stored as:
```php
$this->hooks['index_start'][10]['my_plugin_index_handler'] = array(
    'function' => 'my_plugin_index_handler',
    'file' => ''
)
```

**B. Class Method Hooks:**
```php
$plugins->add_hook('index_start', array('MyClass', 'method_name'));
```
Stored as:
```php
$this->hooks['index_start'][10]['MyClass::method_name'] = array(
    'class_method' => array('MyClass', 'method_name'),
    'file' => ''
)
```

**Hook Registration Flow in Plugins:**
1. Plugin file is `require_once`'d (during load() or admin activate)
2. Plugin file calls `$plugins->add_hook()` **at file scope** (not in a function)
3. Hooks are registered directly into `$plugins->hooks` array
4. Example from hello.php (lines 38-56):
   ```php
   if(defined('IN_ADMINCP'))
   {
       $plugins->add_hook('admin_config_settings_manage', 'hello_settings');
   }
   else
   {
       $plugins->add_hook('index_start', 'hello_index');
       $plugins->add_hook('postbit', 'hello_post');
       $plugins->add_hook('misc_start', 'hello_new');
   }
   ```

#### Hook Execution: `run_hooks()`
```php
function run_hooks($hook, &$arguments="")
```

**Execution Order:**
1. Check if hook exists in `$this->hooks[$hook]`
2. Sort by priority (ascending) - priority 1 executes before priority 20
3. For each priority group, execute all registered functions
4. Functions can return modified `$arguments` (passed by reference)
5. Each hook function receives the arguments and can modify them
6. Returns final modified arguments

**Line-by-line execution (class_plugins.php:115-155):**
```php
// Sort by priority
ksort($this->hooks[$hook]);
foreach($this->hooks[$hook] as $priority => $hooks)
{
    foreach($hooks as $key => $hook)
    {
        // Optionally require file if specified
        if(!empty($hook['file']))
        {
            require_once $hook['file'];
        }

        // Execute class method or function
        if(array_key_exists('class_method', $hook))
        {
            $return_args = call_user_func_array(
                $hook['class_method'],
                array(&$arguments)
            );
        }
        else
        {
            $func = $hook['function'];
            $return_args = $func($arguments);
        }

        // Update arguments if hook returned something
        if($return_args)
        {
            $arguments = $return_args;
        }
    }
}
```

### 3. Plugin Cache Structure (class_datacache.php)

**Cache Title:** `"plugins"`
**Storage:** Serialized in `mybb_datacache` database table
**Location:** Loaded in init.php:182 via `$cache->cache()` before plugin loading

**Cache Structure:**
```php
$plugins_cache = array(
    'active' => array(
        'hello' => 'hello',
        'hello_banner' => 'hello_banner',
        // ... other active plugins
    ),
    // ... potentially other plugin metadata
);
```

**Cache Serialization:**
- Stored in database as serialized PHP: `serialize($plugins_cache)`
- Deserialized when loaded via `native_unserialize()`
- Updated when admin activates/deactivates plugins in admin CP

**Cache Update (admin plugins.php:464-466):**
```php
$plugins_cache['active'] = $active_plugins;
$cache->update("plugins", $plugins_cache);
```

### 4. Plugin Lifecycle: Activation and Deactivation

**Two-Stage Activation Flow (admin/modules/config/plugins.php:375-482):**

#### Stage 1: Installation (if not already installed)
- Check if plugin is already installed via `{codename}_is_installed()` function
- If not installed AND `{codename}_install()` function exists:
  - Call `call_user_func("{$codename}_install")`
  - Creates database tables, settings groups, etc.
  - Example: hello.php creates `mybb_hello_messages` table (lines 361-386)

#### Stage 2: Activation
- Call `{codename}_activate()` function if it exists
- Adds templates, modifies existing templates, creates settings, etc.
- Example: hello.php modifies the `index` template (line 329)
- **Add plugin to active plugins array**
- Update cache: `$cache->update("plugins", $plugins_cache)`

**Complete Activation Code (admin plugins.php:418-442):**
```php
if($mybb->input['action'] == "activate")
{
    // Check compatibility
    if($plugins->is_compatible($codename) == false)
    {
        flash_message($lang->sprintf($lang->plugin_incompatible, $mybb->version), 'error');
        admin_redirect("index.php?module=config-plugins");
    }

    // Stage 1: Install if needed
    if($installed == false && function_exists("{$codename}_install"))
    {
        call_user_func("{$codename}_install");
        $message = $lang->success_plugin_installed;
        $install_uninstall = true;
    }

    // Stage 2: Activate
    if(function_exists("{$codename}_activate"))
    {
        call_user_func("{$codename}_activate");
    }

    // Update cache
    $active_plugins[$codename] = $codename;
    $executed[] = 'activate';
}
```

**Deactivation (admin plugins.php:445-462):**
```php
else if($mybb->input['action'] == "deactivate")
{
    // Call deactivate function
    if(function_exists("{$codename}_deactivate"))
    {
        call_user_func("{$codename}_deactivate");
    }

    // Optional uninstall
    if($mybb->get_input('uninstall') == 1 && function_exists("{$codename}_uninstall"))
    {
        call_user_func("{$codename}_uninstall");
        $message = $lang->success_plugin_uninstalled;
        $install_uninstall = true;
    }

    // Remove from active list
    unset($active_plugins[$codename]);
}

// Update cache
$plugins_cache['active'] = $active_plugins;
$cache->update("plugins", $plugins_cache);
```

### 5. Lifecycle Functions: The Plugin Contract

**Six Required/Optional Functions:**

| Function | Timing | Purpose | Required? |
|----------|--------|---------|-----------|
| `{codename}_info()` | On list, before activate | Return plugin metadata (name, version, compatibility, etc.) | **REQUIRED** |
| `{codename}_activate()` | When admin clicks "Activate" | Make plugin visible (add templates, hooks, settings) | Optional |
| `{codename}_deactivate()` | When admin clicks "Deactivate" | Hide plugin (remove template changes, clean up UI) | Optional |
| `{codename}_install()` | First activation if not installed | Create database tables, initial setup | Optional |
| `{codename}_uninstall()` | When admin clicks "Uninstall" | Remove all plugin data (tables, settings, etc.) | Optional |
| `{codename}_is_installed()` | Before install during activation | Check if plugin is already installed | Optional |

**From hello.php Example:**

**_info() function (lines 58-84):**
```php
function hello_info()
{
    global $lang;
    $lang->load('hello');

    return array(
        'name' => 'Hello World!',
        'description' => $lang->hello_desc,
        'website' => 'https://mybb.com',
        'author' => 'MyBB Group',
        'authorsite' => 'https://mybb.com',
        'version' => '2.0',
        'compatibility' => '18*',
        'codename' => 'hello'
    );
}
```

**_activate() function (lines 91-330):**
- Creates/updates template groups in database
- Inserts/updates templates (master templates, sid=-2)
- Creates/updates settings groups and settings
- Calls `rebuild_settings()` to sync inc/settings.php
- Uses `find_replace_templatesets()` to modify existing templates

**_install() function (lines 353-387):**
- Creates database tables (supports multiple DB types: MySQL, PostgreSQL, SQLite)
- Uses `$db->table_exists()` to check if already exists
- Creates `mybb_hello_messages` table with auto-increment primary key

**_is_installed() function (lines 395-401):**
```php
function hello_is_installed()
{
    global $db;
    return $db->table_exists('hello_messages');
}
```

**_deactivate() function (lines 339-345):**
- Removes template modifications using `find_replace_templatesets()`
- Reverses changes made in _activate()
- Does NOT delete database tables or settings (preserves user data)

**_uninstall() function (lines 408-440):**
- Deletes template groups
- Deletes all plugin templates
- Deletes settings group and individual settings
- Calls `rebuild_settings()` again
- Optionally drops database tables (after confirmation)

## Critical Insights for Phase 7

### 1. Hook Registration Happens at File Load Time
- When a plugin file is `require_once`'d, hook registrations happen **immediately**
- The plugin file contains bare `$plugins->add_hook()` calls at file scope
- This means hooks are registered before the plugin manager realizes the plugin is active
- **IMPLICATION:** For MCP tools to execute activation, we must execute the PHP file (admin CP does this with `require_once`)

### 2. Two-Stage Activation is Necessary
- **Install stage:** Only happens once, creates permanent structures
- **Activate stage:** Happens every time plugin is activated, makes it visible
- Current MCP tools only manipulate cache, skipping both stages
- **PHASE 7 REQUIREMENT:** Create tools that execute PHP activation functions

### 3. Plugin Files Are Executable Code
- Plugin files are not data - they contain PHP code that executes on load
- `require_once` in admin CP (line 407) is **required** to execute lifecycle functions
- We cannot create a pure-Python activation mechanism - must execute PHP

### 4. Cache is the Only Activation Indicator
- The `plugins['active']` array in cache is **the** truth source for plugin status
- Plugin loading checks this cache first (init.php:31)
- Admin CP updates cache after executing lifecycle functions (admin plugins.php:465-466)
- **CRITICAL:** Our tools must update this cache to make plugins actually load on next page load

### 5. Compatibility Checking is Built-In
- `pluginSystem::is_compatible()` method (class_plugins.php:209-247) checks version compatibility
- Automatically called by admin CP before activation (admin plugins.php:423)
- Should be reused in MCP tools

## Proposed Architecture for Phase 7

### New MCP Tool: `mybb_plugin_activate`
**Input:**
- `plugin_codename` - name of plugin to activate
- `execute_install` - boolean, whether to run install function first

**Workflow:**
1. Verify plugin file exists in `/inc/plugins/`
2. Check compatibility using `pluginSystem::is_compatible()`
3. Load plugin file via `require_once` (executes hook registrations)
4. If `execute_install`, call `{codename}_install()` function
5. Call `{codename}_activate()` function
6. Update plugins cache: add codename to `active` array
7. Return success/error with summary

**Requires:**
- Database access for setting updates (already available)
- PHP execution context (MCP server has this)
- Direct cache manipulation (already supported)

### New MCP Tool: `mybb_plugin_deactivate`
**Input:**
- `plugin_codename` - name of plugin
- `execute_uninstall` - boolean, whether to run uninstall function

**Workflow:**
1. Verify plugin file exists
2. Load plugin file via `require_once`
3. Call `{codename}_deactivate()` function if exists
4. If `execute_uninstall`, call `{codename}_uninstall()` function
5. Update plugins cache: remove codename from `active` array
6. Return success/error with summary

### Critical Implementation Note: Snapshot Hooks
The Phase 7 research (RESEARCH_PLUGIN_ACTIVATION_20260118_0727.md) identified a "snapshot hooks" pattern:
- Before executing activation, capture current hook state
- After activation, verify no conflicting hooks were added
- This prevents plugin conflicts and hook pollution

## File References

**Core Plugin System Files:**
- `/home/austin/projects/MyBB_Playground/TestForum/inc/class_plugins.php` (248 lines) - Plugin manager class
- `/home/austin/projects/MyBB_Playground/TestForum/inc/init.php` (329 lines) - Plugin loading at boot (line 264)
- `/home/austin/projects/MyBB_Playground/TestForum/inc/class_datacache.php` (1382 lines) - Cache system
- `/home/austin/projects/MyBB_Playground/TestForum/admin/modules/config/plugins.php` (727 lines) - Admin CP plugin manager
- `/home/austin/projects/MyBB_Playground/TestForum/inc/plugins/hello.php` (589 lines) - Example plugin

**Key Line Numbers:**
- Plugin load: `init.php:262-265`
- Hook registration: `class_plugins.php:53-106`
- Hook execution: `class_plugins.php:115-155`
- Admin activation: `admin plugins.php:375-482`
- Cache structure: `class_datacache.php:1335-1341`

## Open Questions / Unverified

**UNVERIFIED:** Whether MCP server context has sufficient PHP superglobals for `$_SERVER['REQUEST_METHOD']` checks in plugin lifecycle functions
- Some plugins may check `$_SERVER` in activate/deactivate
- MCP runs outside standard web request context
- **Risk Level:** Low (most plugins use `call_user_func()` which doesn't require superglobals)
- **Mitigation:** Set minimal `$_SERVER` superglobals before executing PHP

**UNVERIFIED:** Whether plugin compatibility check works with version codes outside standard web request
- `pluginSystem::is_compatible()` requires `$mybb->version_code`
- MCP server initializes `$mybb` via init.php, should have this set
- **Risk Level:** Very Low (already verified in previous research)

## Recommendations for Architect

1. **Design Phase 7 with two separate tools** (`mybb_plugin_activate` and `mybb_plugin_deactivate`) rather than a combined tool - allows granular control
2. **Implement snapshot hooks pattern** as a safety mechanism to prevent hook pollution
3. **Require admin credentials/verification** before executing lifecycle functions
4. **Document the two-stage activation flow** clearly in tool docs
5. **Add validation** for plugin codename (prevent directory traversal with `.`, `/`, `\` like admin CP does)
6. **Consider transaction safety** - if database update fails mid-activation, cache is left inconsistent

## Conclusion

The MyBB plugin system is well-structured and clean. The two-stage activation model (install + activate) provides good flexibility. Phase 7 tools can be designed to reuse existing MyBB infrastructure without modification, by simply executing the lifecycle functions that already exist in plugin files.

The key architectural insight is that **plugins are executable code**, not data. Activation requires running PHP, which the MCP server can do via direct function execution in a MyBB context.

