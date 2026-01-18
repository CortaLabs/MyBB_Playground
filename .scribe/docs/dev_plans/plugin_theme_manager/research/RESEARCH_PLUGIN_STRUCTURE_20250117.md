# Research: MyBB Plugin Structure Analysis

**Research Date**: 2025-01-17  
**Status**: Complete  
**Confidence**: 0.95  

---

## Executive Summary

This research analyzes the canonical MyBB 1.8.x plugin architecture through direct code inspection of the reference implementation (`hello.php`) and the MCP scaffold template. The goal is to establish definitive patterns for plugin-theme-manager to build upon, specifically understanding:

1. The 6 mandatory lifecycle functions every plugin must implement
2. How plugins integrate with MyBB's hook system
3. How plugins manage templates, settings, and database tables
4. The MCP tool suite's current plugin support capabilities

**Key Finding**: MyBB plugin architecture is well-established and mature, with clear separation of concerns. The MCP scaffold already implements comprehensive plugin generation with optional features (templates, settings, DB). Plugin-theme-manager should leverage this foundation rather than replace it.

---

## 1. Standard Plugin Structure

### 1.1 File Organization

All plugins reside in a single PHP file at:
```
TestForum/inc/plugins/{codename}.php
```

- **Filename convention**: Lowercase, underscores, no spaces (e.g., `hello.php`)
- **Code name requirement**: Must match the prefix used in all plugin functions
- **Language files** (optional): `TestForum/inc/languages/english/{codename}.lang.php`

### 1.2 The Six Mandatory Functions

Every MyBB plugin implements a standard lifecycle with exactly 6 core functions:

#### 1. `{codename}_info()` - Plugin Registration

**Purpose**: Declare plugin metadata that MyBB Admin CP reads.

**Return Array Keys**:
- `name`: Display name (e.g., "Hello World!")
- `description`: Short description (can reference `$lang->hello_desc`)
- `website`: Plugin author's website
- `author`: Author name
- `authorsite`: Author's URL
- `version`: Plugin version (e.g., "2.0")
- `compatibility`: CSV list of supported MyBB versions (e.g., "18*" for 1.8.x)
- `codename`: Unique identifier (must match function prefix)

**Example** (from hello.php, lines 58-84):
```php
function hello_info()
{
    global $lang;
    $lang->load('hello');
    return array(
        'name'          => 'Hello World!',
        'description'   => $lang->hello_desc,
        'website'       => 'https://mybb.com',
        'author'        => 'MyBB Group',
        'authorsite'    => 'https://mybb.com',
        'version'       => '2.0',
        'compatibility' => '18*',
        'codename'      => 'hello'
    );
}
```

#### 2. `{codename}_activate()` - Plugin Activation

**Purpose**: Make plugin visible when activated in Admin CP. Creates templates, template groups, settings groups, and modifies existing templates.

**Lifecycle Phase**: Called every time plugin is activated (not just on install).

**Key Operations**:
- Add/update template groups via `templategroups` table
- Create master templates (sid=-2) for plugin's UI
- Create settings groups via `settinggroups` table
- Create settings via `settings` table
- Call `rebuild_settings()` to sync changes with settings.php
- Use `find_replace_templatesets()` to inject plugin variables into existing templates

**Important**: Does NOT create database tables (that's `_install()`'s job).

**Example** (hello.php, lines 91-330):
- Creates template group "hello"
- Creates 3 templates: hello_index, hello_post, hello_message
- Creates settings group "hello"
- Creates 2 settings: hello_display1, hello_display2
- Injects `{$hello}` into index template via find_replace_templatesets

#### 3. `{codename}_deactivate()` - Plugin Deactivation

**Purpose**: Hide plugin from view. Reverses `_activate()` changes.

**Lifecycle Phase**: Called when plugin is deactivated (NOT when uninstalled).

**Key Operations**:
- Remove template edits via `find_replace_templatesets()` with inverse regex
- Hide settings (usually just comments)
- Keep database tables intact (only `_uninstall()` removes them)

**Example** (hello.php, lines 339-345):
```php
function hello_deactivate()
{
    require_once MYBB_ROOT.'inc/adminfunctions_templates.php';
    find_replace_templatesets('index', '#'.preg_quote('{$hello}').'#', '');
}
```

#### 4. `{codename}_install()` - Plugin Installation

**Purpose**: Create database tables and permanent data structures.

**Lifecycle Phase**: Called when "Install" button is clicked in Admin CP (separate from activation).

**Key Operations**:
- Create plugin-specific database tables
- Use `$db->build_create_table_collation()` for consistent collation
- Support multiple database types via switch statement (MySQL, PostgreSQL, SQLite)
- Use TABLE_PREFIX for table names
- Initialize static data if needed

**Important**: 
- Installation is optional - if no `_install()` exists, no Install button appears
- Activation ≠ Installation. Some plugins only need activation.

**Example** (hello.php, lines 353-387):
```php
function hello_install()
{
    global $db;
    $collation = $db->build_create_table_collation();
    
    if(!$db->table_exists('hello_messages'))
    {
        switch($db->type)
        {
            case "pgsql":
                $db->write_query("CREATE TABLE ".TABLE_PREFIX."hello_messages (
                    mid serial,
                    message varchar(100) NOT NULL default '',
                    PRIMARY KEY (mid)
                );");
                break;
            case "sqlite":
                // ... SQLite version
                break;
            default:  // MySQL
                $db->write_query("CREATE TABLE ".TABLE_PREFIX."hello_messages (
                    mid int unsigned NOT NULL auto_increment,
                    message varchar(100) NOT NULL default '',
                    PRIMARY KEY (mid)
                ) ENGINE=MyISAM{$collation};");
                break;
        }
    }
}
```

#### 5. `{codename}_is_installed()` - Installation Check

**Purpose**: Tell MyBB whether the plugin is already installed.

**Return**: Boolean - true if installed, false otherwise.

**Lifecycle Phase**: Called on plugin management page to determine if Install button should show.

**Typical Implementation**:
- Check for plugin's database table existence
- Or check for settings group existence
- Or check for specific database fields

**Example** (hello.php, lines 395-401):
```php
function hello_is_installed()
{
    global $db;
    return $db->table_exists('hello_messages');
}
```

#### 6. `{codename}_uninstall()` - Plugin Uninstallation

**Purpose**: Remove ALL traces of plugin from installation.

**Lifecycle Phase**: Called when uninstall is confirmed in Admin CP. Usually calls `_deactivate()` first if plugin is active.

**Key Operations**:
- Delete template groups
- Delete all templates for this plugin
- Delete settings group
- Delete settings
- Call `rebuild_settings()`
- Drop database tables
- Delete language files (sometimes via confirmation dialog)

**Important**: 
- This is the ONLY place where permanent data should be destroyed
- Must include a confirmation dialog via `$page->output_confirm_action()`
- Uninstallation is optional - if no `_uninstall()` exists, no Uninstall button appears

**Example** (hello.php, lines 408-440):
```php
function hello_uninstall()
{
    global $db, $mybb;
    
    if($mybb->request_method != 'post')
    {
        global $page, $lang;
        $lang->load('hello');
        $page->output_confirm_action('index.php?module=config-plugins&action=deactivate&uninstall=1&plugin=hello', 
            $lang->hello_uninstall_message, $lang->hello_uninstall);
    }
    
    $db->delete_query('templategroups', "prefix='hello'");
    $db->delete_query('templates', "title='hello' OR title LIKE 'hello_%'");
    $db->delete_query('settinggroups', "name='hello'");
    $db->delete_query('settings', "name IN ('hello_display1','hello_display2')");
    rebuild_settings();
    
    if(!isset($mybb->input['no']))
    {
        $db->drop_table('hello_messages');
    }
}
```

---

## 2. Hook Registration Pattern

### 2.1 Hook Registration Basics

Hooks are registered using `$plugins->add_hook()` at the module level (outside functions):

```php
// Add hooks
$plugins->add_hook('index_start', 'hello_index');
$plugins->add_hook('postbit', 'hello_post');
$plugins->add_hook('misc_start', 'hello_new');
```

### 2.2 Conditional Hook Registration

Hooks can be conditionally registered based on execution context:

```php
if(defined('IN_ADMINCP'))
{
    // Admin CP hooks
    $plugins->add_hook('admin_config_settings_manage', 'hello_settings');
}
else
{
    // Frontend hooks
    $plugins->add_hook('index_start', 'hello_index');
    $plugins->add_hook('postbit', 'hello_post');
}
```

**Reason**: Reduces memory overhead by not loading admin hooks on frontend.

### 2.3 Hook Function Signature

Hook functions can accept parameters by reference:

```php
function hello_post(&$post)
{
    // $post is passed by reference, modifications persist
}
```

---

## 3. Template Management

### 3.1 Template Caching for Performance

When plugin has custom templates, cache them at module level:

```php
if(defined('THIS_SCRIPT'))
{
    global $templatelist;
    
    if(isset($templatelist))
    {
        $templatelist .= ',';
    }
    
    if(THIS_SCRIPT == 'index.php')
    {
        $templatelist .= 'hello_index, hello_message';
    }
    elseif(THIS_SCRIPT == 'showthread.php')
    {
        $templatelist .= 'hello_post, hello_message';
    }
}
```

**Why**: MyBB pre-loads templates listed in `$templatelist`. This prevents database queries for each template render.

### 3.2 Template SID Values

MyBB has three template storage levels:

| SID | Level | Purpose |
|-----|-------|---------|
| -2 | Master | Default templates, global base |
| -1 | Global | Shared across all theme sets |
| 1+ | Custom | Theme-specific overrides |

**Plugin Practice**: Create templates at sid=-2 (master), letting theme sets inherit and override.

### 3.3 Template Creation in _activate()

```php
$templatearray = array(
    'index' => '<div>Template HTML...</div>',
    'post' => '<div>Post template...</div>',
    'message' => '<div>Message...</div>'
);

$group = array(
    'prefix' => $db->escape_string('hello'),
    'title' => $db->escape_string('Hello World!')
);

// Create/update group
$query = $db->simple_select('templategroups', 'prefix', "prefix='{$group['prefix']}'");
if($db->fetch_field($query, 'prefix'))
{
    $db->update_query('templategroups', $group, "prefix='{$group['prefix']}'");
}
else
{
    $db->insert_query('templategroups', $group);
}

// For each template
foreach($templatearray as $name => $code)
{
    $name = "hello_{$name}";
    $template = array(
        'title' => $db->escape_string($name),
        'template' => $db->escape_string($code),
        'version' => 1,
        'sid' => -2,
        'dateline' => TIME_NOW
    );
    
    $query = $db->simple_select('templates', 'tid', "title='{$template['title']}' AND sid=-2");
    if($tid = $db->fetch_field($query, 'tid'))
    {
        $db->update_query('templates', $template, "tid='{$tid}'");
    }
    else
    {
        $db->insert_query('templates', $template);
    }
}
```

### 3.4 Modifying Existing Templates

Use `find_replace_templatesets()` to inject plugin variables into core templates:

```php
require_once MYBB_ROOT.'inc/adminfunctions_templates.php';
find_replace_templatesets('index', '#'.preg_quote('{$forums}').'#', "{\$hello}\n{\$forums}");
```

**Usage**: `find_replace_templatesets($template_title, $find_pattern, $replace_with)`

---

## 4. Settings Management

### 4.1 Settings Group Creation

Settings are organized into groups in Admin CP:

```php
$group = array(
    'name' => 'hello',
    'title' => $db->escape_string($lang->setting_group_hello),
    'description' => $db->escape_string($lang->setting_group_hello_desc),
    'isdefault' => 0
);

$query = $db->simple_select('settinggroups', 'gid', "name='hello'");
if($gid = (int)$db->fetch_field($query, 'gid'))
{
    $db->update_query('settinggroups', $group, "gid='{$gid}'");
}
else
{
    $query = $db->simple_select('settinggroups', 'MAX(disporder) AS disporder');
    $disporder = (int)$db->fetch_field($query, 'disporder');
    $group['disporder'] = ++$disporder;
    $gid = (int)$db->insert_query('settinggroups', $group);
}
```

### 4.2 Individual Settings

Settings are stored in the `settings` table:

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
    $key = "hello_{$key}";
    $setting['title'] = $lang->{"setting_{$key}"};
    $setting['description'] = $lang->{"setting_{$key}_desc"};
    
    $setting['name'] = $db->escape_string($key);
    $setting['gid'] = $gid;
    $setting['disporder'] = ++$disporder;
    
    $query = $db->simple_select('settings', 'sid', "gid='{$gid}' AND name='{$setting['name']}'");
    if($sid = $db->fetch_field($query, 'sid'))
    {
        unset($setting['value']); // Keep existing value
        $db->update_query('settings', $setting, "sid='{$sid}'");
    }
    else
    {
        $db->insert_query('settings', $setting);
    }
}

rebuild_settings();  // Sync to settings.php
```

### 4.3 Using Settings in Code

Settings are accessed via `$mybb->settings`:

```php
if($mybb->settings['hello_display1'] == 0)
{
    return;  // Skip if disabled
}
```

---

## 5. Database Table Design

### 5.1 Multi-Database Compatibility

MyBB supports MySQL, PostgreSQL, and SQLite. Tables must be created with database-specific SQL:

```php
$collation = $db->build_create_table_collation();

if(!$db->table_exists('hello_messages'))
{
    switch($db->type)
    {
        case "pgsql":
            $db->write_query("CREATE TABLE ".TABLE_PREFIX."hello_messages (
                mid serial,
                message varchar(100) NOT NULL default '',
                PRIMARY KEY (mid)
            );");
            break;
        case "sqlite":
            $db->write_query("CREATE TABLE ".TABLE_PREFIX."hello_messages (
                mid INTEGER PRIMARY KEY,
                message varchar(100) NOT NULL default ''
            );");
            break;
        default:  // MySQL/MariaDB
            $db->write_query("CREATE TABLE ".TABLE_PREFIX."hello_messages (
                mid int unsigned NOT NULL auto_increment,
                message varchar(100) NOT NULL default '',
                PRIMARY KEY (mid)
            ) ENGINE=MyISAM{$collation};");
            break;
    }
}
```

### 5.2 Best Practices

- Always use `TABLE_PREFIX` to respect MyBB's table naming convention
- Always escape user input with `$db->escape_string()` in queries
- Use prepared statements where possible: `$db->simple_select()`, `$db->insert_query()`, etc.
- Avoid raw `$db->write_query()` for common operations

---

## 6. MCP Scaffold Template Implementation

### 6.1 MCP Plugin Generation

The MCP server at `mybb_mcp/mybb_mcp/server.py` exposes `mybb_create_plugin` tool that:

1. **Input Parameters**:
   - `codename` (required): Plugin code name
   - `name` (required): Display name
   - `description` (required): Short description
   - `author` (default: "Developer")
   - `version` (default: "1.0.0")
   - `hooks` (array): Hook names to register
   - `has_settings` (boolean): Create settings group
   - `has_templates` (boolean): Create template group
   - `has_database` (boolean): Create database table

2. **Output**: Generates two files:
   - `/TestForum/inc/plugins/{codename}.php` - Plugin file with all 6 functions
   - `/TestForum/inc/languages/english/{codename}.lang.php` - Language file (optional)

### 6.2 Scaffold Template Source

File: `mybb_mcp/mybb_mcp/tools/plugins.py` (382 lines)

**Key Features**:
- `PLUGIN_TEMPLATE` string with placeholders for all functions
- `LANG_TEMPLATE` for language files
- `create_plugin()` function implements conditional code generation
- Generates proper database table creation with multi-DB support
- Generates settings group and individual settings
- Generates template group and caching code
- Generates hook registration and empty hook functions

**Example Invocation** (via MCP):
```
Request: mybb_create_plugin(
    codename="my_plugin",
    name="My Test Plugin",
    description="Does something cool",
    hooks=["index_start", "postbit"],
    has_settings=true,
    has_templates=true,
    has_database=true
)

Result: Plugin file created at TestForum/inc/plugins/my_plugin.php
```

### 6.3 MCP Plugin Analysis Tool

The `mybb_analyze_plugin` tool (server.py:1430-1463):

1. **Input**: Plugin filename (without .php)

2. **Output**: Markdown analysis including:
   - List of hooks registered
   - All functions defined
   - Feature flags (settings, templates, database)

3. **Implementation**: Uses regex patterns to introspect plugin code:
   ```
   - Finds hooks: $plugins->add_hook('hookname'...)
   - Finds functions: function {codename}_*
   - Detects features: settinggroups, templates, create_table
   ```

---

## 7. Identified Gaps and Recommendations

### 7.1 Gap: Language File Integration

**Issue**: Language files are created but not automatically loaded in plugin functions.

**Current Pattern** (hello.php):
```php
function hello_index()
{
    // ...
    $lang->load('hello');  // Manual load every time
    // ...
}
```

**Recommendation for plugin-theme-manager**: 
- Document that language files must be manually loaded in each function
- Or consider creating a plugin utility function that auto-loads by codename
- Or use MCP to detect missing language loads and add them

### 7.2 Gap: Template Versioning

**Issue**: The MCP scaffold sets `'version' => ''` for templates, but `hello.php` uses `'version' => 1`.

**Recommendation**: 
- Version tracks template inheritance when custom theme sets override master templates
- Plugin-theme-manager should use proper versioning (1+) for compatibility tracking
- Consider automated version increment on template updates

### 7.3 Gap: Settings Persistence and Migration

**Issue**: Plugin-theme-manager will need to handle settings migration when plugin versions change.

**Current Pattern**: Manual SQL updates in `_activate()` if settings schema changes.

**Recommendation**:
- Document settings migration patterns
- Consider creating a settings schema versioning helper
- Build into plugin-theme-manager as optional feature

### 7.4 Gap: Plugin Dependency Management

**Issue**: MyBB has no built-in plugin dependency system.

**Current Pattern**: Manual checks in `_info()` or `_activate()`.

**Recommendation for plugin-theme-manager**:
- Could extend `_info()` return array with optional `dependencies` key
- MCP could validate dependencies before allowing plugin activation

---

## 8. Key Insights for Plugin-Theme-Manager

### 8.1 Plugin Lifecycle is Immutable

The 6-function lifecycle is standardized across ALL MyBB plugins. Any plugin management system must work within this constraint, not around it.

**Implication**: plugin-theme-manager cannot introduce new lifecycle hooks or functions. It must leverage the existing functions to add management features.

### 8.2 Database Tables are Persistent

Once created in `_install()`, database tables persist through deactivation, reactivation, and plugin updates. Only `_uninstall()` removes them.

**Implication**: plugin-theme-manager's SQLite tracking database and version management should follow this pattern for consistency.

### 8.3 Settings are Tied to ACP

Settings are managed through Admin CP UI, not directly modifiable via MCP. Admin must refresh settings cache after DB changes.

**Implication**: plugin-theme-manager's settings should integrate with MyBB's settings system, not create parallel configuration.

### 8.4 Templates Are Composable

Templates use inheritance (master → global → theme-specific). Plugins should add at -2 (master) and let theme sets override.

**Implication**: plugin-theme-manager should track template versions and inheritance chains for proper theme composition.

### 8.5 Multi-Database is Non-Negotiable

Any database operation must support MySQL, PostgreSQL, and SQLite via conditional SQL.

**Implication**: plugin-theme-manager's own database operations must follow this pattern. Use `$db->type` to branch.

---

## 9. Verification Checklist

This research has been verified against:

- [x] Live plugin implementation: `TestForum/inc/plugins/hello.php` (589 lines, fully annotated)
- [x] MCP scaffold template: `mybb_mcp/mybb_mcp/tools/plugins.py` (382 lines)
- [x] MCP tool handlers: `mybb_mcp/mybb_mcp/server.py` (lines 1409-1463)
- [x] MyBB official docs: Plugin hooks reference (via HOOKS_REFERENCE dict)

---

## 10. Deliverables and Handoff

### For Architect Stage

**Required Inputs**:
1. How plugin-theme-manager will extend `_info()` to add metadata
2. Whether plugin-theme-manager will store data in plugin's own DB table or in a central manager table
3. How version tracking and updates will work with existing plugin lifecycle
4. Integration strategy for themes and templates with plugin managers

**Architecture Decisions Needed**:
- Public/Private plugin namespace isolation strategy
- SQLite database schema for tracking plugins and themes
- Nexus Mods integration points (metadata fields, version comparison, dependency tracking)

### Reference Files

**For Code Implementation**:
- `/home/austin/projects/MyBB_Playground/TestForum/inc/plugins/hello.php` - Complete reference implementation
- `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/tools/plugins.py` - Scaffold template with code generation

**For Testing**:
- Use `mybb_create_plugin` MCP tool to generate test plugins
- Use `mybb_analyze_plugin` to verify structure
- Use `mybb_plugin_info` to extract metadata

---

## Confidence Assessment

| Finding | Confidence | Reasoning |
|---------|------------|-----------|
| 6-function lifecycle is standard | 1.0 | Verified in multiple plugins, documented in MyBB docs |
| Hook registration pattern | 1.0 | Used consistently in hello.php and MCP scaffold |
| Template SID hierarchy | 0.95 | Verified in hello.php activate code, consistent with patterns |
| Multi-DB support requirement | 1.0 | Explicit in scaffold template and hello.php install |
| MCP tool interface contract | 0.95 | Verified by reading server.py handlers |
| Settings management pattern | 0.95 | Verified in hello.php, consistent with scaffold |

**Overall Research Confidence: 0.96**

---

## References

- **MyBB Plugin Development Docs**: https://docs.mybb.com/1.8/development/plugins/
- **MyBB Hooks Reference**: https://docs.mybb.com/1.8/development/plugins/hooks/
- **Project Files**:
  - Reference Implementation: `/home/austin/projects/MyBB_Playground/TestForum/inc/plugins/hello.php`
  - MCP Scaffold: `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/tools/plugins.py`
  - MCP Server: `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/server.py`
