# Plugin Integration Patterns and Hook Safety Research

**Date:** 2026-01-18 07:31 UTC
**Researcher:** ResearchAgent
**Confidence:** 0.92
**Scope:** Hook integration patterns, snapshot hooks for safety, template modification patterns

## Executive Summary

This research complements the core plugin system analysis by examining how plugins safely integrate with MyBB through:
1. **Hook registration patterns** - how plugins add functionality without modifying core code
2. **Snapshot hooks pattern** - preventing hook pollution and conflicts during activation
3. **Template modification patterns** - how plugins modify existing templates safely
4. **Settings lifecycle** - how plugin settings are created and managed
5. **Cross-plugin concerns** - handling multiple activated plugins safely

## 1. Hook Integration Patterns

### Pattern A: Standard Hook Registration
**Location:** Plugin file scope (not in functions)
**Timing:** Executes when plugin file is `require_once`'d

```php
// From hello.php (lines 38-56)
if(defined('IN_ADMINCP'))
{
    $plugins->add_hook('admin_config_settings_manage', 'hello_settings');
    $plugins->add_hook('admin_config_settings_change', 'hello_settings');
    $plugins->add_hook('admin_config_settings_start', 'hello_settings');
}
else
{
    $plugins->add_hook('index_start', 'hello_index');
    $plugins->add_hook('postbit', 'hello_post');
    $plugins->add_hook('misc_start', 'hello_new');
}
```

**Key Pattern Points:**
- Hooks are registered at **file load time**, not at application startup
- Conditional registration based on execution context (`IN_ADMINCP`, `THIS_SCRIPT`)
- Multiple hooks can point to same function (hello_settings handles 3 hooks)
- Hooks are registered directly to global `$plugins` object

### Pattern B: Conditional Hook Loading by Script
**Example:** Template caching optimization from hello.php (lines 18-36)

```php
if(defined('THIS_SCRIPT'))
{
    global $templatelist;

    if(isset($templatelist))
    {
        $templatelist .= ',';
    }

    if(THIS_SCRIPT== 'index.php')
    {
        $templatelist .= 'hello_index, hello_message';
    }
    elseif(THIS_SCRIPT== 'showthread.php')
    {
        $templatelist .= 'hello_post, hello_message';
    }
}
```

**Pattern Insight:** Plugins optimize by only registering hooks and caching templates needed for specific pages

### Pattern C: Class Method Hooks
**Supported by:** `pluginSystem::add_hook()` (lines 55-88)

```php
// Static class method
$plugins->add_hook('hook_name', array('ClassName', 'static_method_name'));

// Instance class method
$plugins->add_hook('hook_name', array($object_instance, 'method_name'));
```

**Storage Structure:**
```php
$this->hooks['hook_name'][10]['ClassName::static_method_name'] = array(
    'class_method' => array('ClassName', 'static_method_name'),
    'file' => $file
);
```

**Execution:** Via `call_user_func_array()` (class_plugins.php:136)

## 2. Snapshot Hooks Pattern for Safety

**Research Reference:** `RESEARCH_PLUGIN_ACTIVATION_20260118_0727.md` identifies this pattern as critical for Phase 7

### The Problem It Solves

When activating a plugin via MCP:
1. Plugin file is `require_once`'d
2. All hooks in that file are registered to global `$plugins->hooks`
3. If plugin is buggy or conflicts with another plugin, hooks pollute the global state
4. Later plugin activation attempts fail with conflicting hooks

### The Snapshot Pattern

**Snapshot Before Activation:**
```python
# Pseudo-code for MCP tool
hooks_before = serialize($plugins->hooks)
hooks_before_count = count_all_hooks($plugins->hooks)
```

**Execute Activation:**
```php
require_once MYBB_ROOT."inc/plugins/$file";
if(function_exists("{$codename}_activate"))
{
    call_user_func("{$codename}_activate");
}
```

**Snapshot After Activation:**
```python
hooks_after = serialize($plugins->hooks)
hooks_after_count = count_all_hooks($plugins->hooks)

# Verify
new_hooks = hooks_after_count - hooks_before_count
if new_hooks > EXPECTED_HOOKS:
    log_warning("Plugin registered {new_hooks} hooks, expected <= N")
    rollback_activation()
```

### Implementation Strategy

**Phase 7 Approach:** Embed hook snapshot validation in `mybb_plugin_activate`:

```python
# 1. Get hook state before activation
hook_snapshot_before = db.select("
    SELECT name FROM mybb_hooks
    ORDER BY hook_name, priority
")

# 2. Execute plugin activation
php_result = execute_php_function(
    function_name=f"{codename}_activate"
)

# 3. Get hook state after activation
hook_snapshot_after = db.select(
    "SELECT name FROM mybb_hooks
     ORDER BY hook_name, priority"
)

# 4. Verify safety
new_hooks = set_difference(hook_snapshot_after, hook_snapshot_before)
if len(new_hooks) > SAFETY_THRESHOLD:
    raise ActivationError(
        f"Plugin created {len(new_hooks)} hooks, exceeds threshold"
    )

# 5. Return success with hook summary
return {
    "status": "success",
    "hooks_added": new_hooks,
    "hook_count_change": len(new_hooks)
}
```

**UNVERIFIED:** Whether MyBB stores hook information in database. Current evidence suggests hooks are **runtime-only**, not persisted.
- `$plugins->hooks` is an in-memory array (class_plugins.php:16)
- No corresponding `mybb_hooks` database table found in previous research
- Hooks are only loaded when plugin files are executed
- **Implication:** Snapshot must be done on runtime `$plugins->hooks` array, not database

### Alternative Snapshot Approach (Memory-Based)

Since hooks are runtime-only, MCP must snapshot via PHP execution:

```php
// MCP Tool: mybb_plugin_activate
function mybb_plugin_activate_with_snapshot($codename) {
    global $plugins;

    // Snapshot before
    $hooks_before = json_encode($plugins->hooks);

    // Execute activation
    require_once MYBB_ROOT."inc/plugins/{$codename}.php";
    if(function_exists("{$codename}_activate"))
    {
        call_user_func("{$codename}_activate");
    }

    // Snapshot after
    $hooks_after = json_encode($plugins->hooks);

    // Compare
    $before_count = count_hooks($plugins->hooks);
    $after_count = count_hooks($plugins->hooks);

    return array(
        'status' => 'success',
        'hooks_added' => $after_count - $before_count,
        'hook_snapshot_change' => sha1($hooks_before) !== sha1($hooks_after)
    );
}
```

## 3. Template Modification Patterns

**Key Function:** `find_replace_templatesets()` (from adminfunctions_templates.php)

### Pattern: Find and Replace in Existing Templates

**From hello.php activation (line 329):**
```php
find_replace_templatesets(
    'index',                                    // template name
    '#'.preg_quote('{$forums}').'#',            // find (regex)
    "{\$hello}\n{\$forums}"                     // replace with
);
```

**Effect:** Modifies the master `index` template by inserting `{$hello}` before `{$forums}`

**From hello.php deactivation (line 344):**
```php
find_replace_templatesets(
    'index',
    '#'.preg_quote('{$hello}').'#',             // find what plugin added
    ''                                          // remove it
);
```

**Pattern Insight:** Safe template modifications use regex find/replace to:
1. Insert custom variables into existing templates
2. Wrap existing content with custom markup
3. Easily remove changes in deactivate() by reversing the operation

### Why This Pattern is Safe

- **Non-destructive:** Only modifies specific strings, leaves rest intact
- **Reversible:** Deactivate can undo the exact change
- **Database-safe:** Changes are persisted in database template rows
- **Multi-version compatible:** Works across multiple template sets (master, custom, theme-specific)

## 4. Settings Lifecycle Pattern

**Analyzed from:** hello.php activate() and uninstall() functions

### Creation Pattern (from hello.php:222-320)

**Step 1: Create Settings Group**
```php
$group = array(
    'name' => 'hello',
    'title' => $db->escape_string($lang->setting_group_hello),
    'description' => $db->escape_string($lang->setting_group_hello_desc),
    'isdefault' => 0
);

// Check if exists, update or create
$query = $db->simple_select('settinggroups', 'gid', "name='hello'");
if($gid = (int)$db->fetch_field($query, 'gid'))
{
    $db->update_query('settinggroups', $group, "gid='{$gid}'");
}
else
{
    // Get max disporder and increment
    $query = $db->simple_select('settinggroups', 'MAX(disporder) AS disporder');
    $disporder = (int)$db->fetch_field($query, 'disporder');
    $group['disporder'] = ++$disporder;
    $gid = (int)$db->insert_query('settinggroups', $group);
}
```

**Step 2: Create Individual Settings**
```php
$settings = array(
    'display1' => array(
        'optionscode' => 'yesno',
        'value' => 1
    ),
    'display2' => array(
        'optionscode' => 'yesno',
        'value' => 1
    )
);

foreach($settings as $key => $setting)
{
    $key = "hello_{$key}";  // Prefix with plugin name

    $setting = array_merge(array(
        'description' => '',
        'optionscode' => 'yesno',
        'value' => 0,
        'disporder' => $disporder
    ), $setting);

    $setting['name'] = $db->escape_string($key);
    $setting['gid'] = $gid;

    // Check if exists and update/create accordingly
    $query = $db->simple_select('settings', 'sid', "gid='{$gid}' AND name='{$setting['name']}'");
    if($sid = $db->fetch_field($query, 'sid'))
    {
        $db->update_query('settings', $setting, "sid='{$sid}'");
    }
    else
    {
        $db->insert_query('settings', $setting);
    }
}
```

**Step 3: Rebuild Settings File**
```php
rebuild_settings();  // Syncs inc/settings.php with database
```

**Critical Pattern:** Settings names are **prefixed** with plugin codename (e.g., `hello_display1`) to avoid conflicts

### Deletion Pattern (from hello.php:420-433)

```php
// Delete template groups
$db->delete_query('templategroups', "prefix='hello'");

// Delete templates
$db->delete_query('templates', "title='hello' OR title LIKE 'hello_%'");

// Delete settings group (this cascades to settings)
$db->delete_query('settinggroups', "name='hello'");

// Delete specific settings
$db->delete_query('settings', "name IN ('hello_display1','hello_display2')");

// Rebuild settings file
rebuild_settings();
```

## 5. Cross-Plugin Concerns

### Hook Priority System

**From class_plugins.php hook execution (line 122):**
```php
ksort($this->hooks[$hook]);  // Sort by priority ascending
foreach($this->hooks[$hook] as $priority => $hooks)
{
    // Execute hooks at each priority level in order
}
```

**Default Priority:** 10

**Common Patterns:**
- **Priority 1-5:** Early hooks that prepare data (compatibility with most plugins)
- **Priority 10 (default):** Standard plugin hooks
- **Priority 15-20:** Late hooks that rely on other plugins' modifications

**Example:** If two plugins hook the same point:
- Plugin A registers hook at priority 5
- Plugin B registers hook at priority 10
- Plugin B's hook executes first when hook runs (sorts ascending)

### Multiple Plugins, Same Hook

**Scenario:** Two plugins both hook `index_start`

```php
// Plugin A (priority 10, default)
$plugins->add_hook('index_start', 'plugin_a_handler');

// Plugin B (priority 10, default)
$plugins->add_hook('index_start', 'plugin_b_handler');
```

**Execution Order:** By registration order (both priority 10)

**Data Flow:** Each hook can modify arguments passed to next hook:
```php
// Hook execution
function_a($arguments);  // Modifies $arguments
function_b($arguments);  // Receives modified $arguments
```

## 6. Plugin Compatibility Checking

**Implementation:** `pluginSystem::is_compatible()` (class_plugins.php:209-247)

```php
function is_compatible($plugin)
{
    global $mybb;

    // Load plugin file
    require_once MYBB_ROOT."inc/plugins/".$plugin.".php";

    // Get plugin info
    $info_func = "{$plugin}_info";
    if(!function_exists($info_func))
    {
        return false;
    }
    $plugin_info = $info_func();

    // Check compatibility string
    if(empty($plugin_info['compatibility']) || $plugin_info['compatibility'] == "*")
    {
        return true;  // Compatible with all versions
    }

    // Match version against pattern
    $compatibility = explode(",", $plugin_info['compatibility']);
    foreach($compatibility as $version)
    {
        $version = trim($version);
        $version = str_replace("*", ".+", preg_quote($version));
        $version = str_replace("\.+", ".+", $version);

        if(preg_match("#{$version}#i", $mybb->version_code))
        {
            return true;
        }
    }

    return false;
}
```

**Compatibility Patterns:**
- `"18*"` - matches any 1.8.x version
- `"1.8.0,1.8.1,1.8.2"` - specific versions
- `"*"` - all versions
- Empty string - all versions

## Insights for Phase 7 Implementation

### 1. Hook Safety is Critical
The snapshot pattern is essential to prevent plugin conflicts. Tools must validate hook registration before committing cache updates.

### 2. Settings Prefixing is Standard
All plugin settings must use codename prefix (e.g., `hello_display1`). Tools should enforce this pattern.

### 3. Template Modifications Must Be Reversible
The find/replace pattern allows safe activation and deactivation. Tools should document this requirement.

### 4. Version Compatibility Must Be Checked
Always call `pluginSystem::is_compatible()` before activation to prevent incompatible plugins from being activated.

### 5. Settings Cache Rebuilding is Required
Any settings changes must trigger `rebuild_settings()` to keep `inc/settings.php` in sync with database.

### 6. Priority Ordering Enables Plugin Composition
The priority system allows multiple plugins to hook the same point safely, as long as they don't have hard dependencies on execution order.

## File References

- `class_plugins.php` (lines 53-155) - Hook system implementation
- `hello.php` (lines 18-330, 408-440) - Template, settings, hook patterns
- `admin/modules/config/plugins.php` (lines 375-482) - Activation/deactivation workflow
- `inc/functions.php` (lines 7022-7046) - rebuild_settings() function

## Open Questions

**UNVERIFIED:** Whether hook modifications in activation can conflict with existing active plugins
- If Plugin A adds hook at priority 5, then Plugin B adds hook at same point/priority
- Would conflict happen at runtime or at hook execution?
- **Research Gap:** Need to test with multiple active plugins

**UNVERIFIED:** Whether `find_replace_templatesets()` works correctly on already-modified templates
- If plugin A modifies template, does plugin B's find/replace work on modified version?
- Or does it work on master template?
- **Research Gap:** Need to examine `find_replace_templatesets()` implementation in adminfunctions_templates.php

## Recommendations

1. **Implement snapshot hooks** in Phase 7 activation tool as safety mechanism
2. **Validate settings prefixing** in plugin creation tools
3. **Enforce rebuild_settings()** after any settings changes in MCP tools
4. **Document priority system** in plugin creation guidelines
5. **Add compatibility validation** to activation tool using existing `pluginSystem::is_compatible()`
6. **Test multi-plugin scenarios** before releasing Phase 7 tools

