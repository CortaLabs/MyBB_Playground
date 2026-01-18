# Plugin Development Best Practices

**Complete guide to creating secure, maintainable MyBB plugins with proper structure, hooks, and database operations.**

---

## Critical Standards

### ⚠️ MyBB Settings vs Config Files (MANDATORY)

**All user-configurable options MUST use MyBB Admin CP Settings, not config files.**

| Use MyBB Settings For | Use Config Files For |
|-----------------------|----------------------|
| Enable/disable features | Advanced/dangerous options only |
| Numeric limits (cache TTL, max depth) | Functions to whitelist (security risk) |
| User-facing text/labels | File paths (if truly needed) |
| Mode selections | Developer-only debugging flags |
| Any option an admin should change | |

**Why this matters:**
- MyBB settings are the standard for distributable plugins
- Admins expect to configure plugins via Admin CP
- Config files require file access (not always available)
- Settings integrate with MyBB's caching system

**Pattern: Settings with Config Fallback**
```php
// In your handler - ACP settings override, config.php as fallback
$fileConfig = require MYBB_ROOT . 'inc/plugins/myplugin/config.php';

$enabled = isset($mybb->settings['myplugin_enabled'])
    ? (bool)$mybb->settings['myplugin_enabled']
    : ($fileConfig['enabled'] ?? true);

$maxDepth = isset($mybb->settings['myplugin_max_depth'])
    ? (int)$mybb->settings['myplugin_max_depth']
    : ($fileConfig['max_depth'] ?? 10);
```

---

## Plugin Structure

### Required Lifecycle Functions

Every MyBB plugin must implement these functions with the plugin codename prefix:

#### 1. `{codename}_info()`
Returns plugin metadata displayed in Admin CP.

```php
function myplugin_info()
{
    return array(
        "name"          => "My Plugin",
        "description"   => "Plugin description",
        "website"       => "https://example.com",
        "author"        => "Author Name",
        "authorsite"    => "https://example.com",
        "version"       => "1.0.0",
        "compatibility" => "18*",  // MyBB 1.8.x
        "codename"      => "myplugin"
    );
}
```

**Required Fields:**
- `name` - Display name in Admin CP
- `description` - What the plugin does
- `version` - Semantic versioning (e.g., "1.0.0")
- `compatibility` - MyBB version pattern ("18*" for all 1.8.x)
- `codename` - Unique identifier (lowercase, underscores)

#### 2. `{codename}_activate()`
Executed when plugin is activated. Registers hooks and creates templates.

```php
function myplugin_activate()
{
    global $db, $cache;

    // Register hooks
    // (Hooks are auto-loaded from database cache when registered here)

    // Create templates if needed
    if (has_templates) {
        // Template creation logic
        $cache->update_templates();
    }
}
```

**Purpose:** Setup operations that can be reversed by deactivation (hooks, templates, caches).

#### 3. `{codename}_deactivate()`
Executed when plugin is deactivated. Removes hooks.

```php
function myplugin_deactivate()
{
    global $db, $cache;

    // Remove hooks (automatic when plugin deactivated)
    // Remove templates if created
    if (has_templates) {
        // Template removal logic
        $cache->update_templates();
    }
}
```

**Purpose:** Reverse `_activate()` operations without removing permanent data.

#### 4. `{codename}_install()`
Executed on installation. Creates database tables and settings.

```php
function myplugin_install()
{
    global $db;

    // Create database tables
    $db->write_query("
        CREATE TABLE IF NOT EXISTS " . TABLE_PREFIX . "myplugin_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");

    // Create settings group
    $db->insert_query("settinggroups", array(
        'name' => 'myplugin',
        'title' => 'My Plugin Settings',
        'description' => 'Configure plugin behavior',
        'disporder' => 100,
        'isdefault' => 0
    ));
    $gid = $db->insert_id();

    // Create individual settings
    $db->insert_query("settings", array(
        'name' => 'myplugin_enabled',
        'title' => 'Enable Plugin',
        'description' => 'Enable or disable plugin functionality',
        'optionscode' => 'yesno',
        'value' => '1',
        'disporder' => 1,
        'gid' => $gid
    ));

    rebuild_settings();
}
```

**Purpose:** Create permanent data structures (tables, settings) that persist after deactivation.

#### 5. `{codename}_uninstall()`
Executed on uninstallation. Removes all plugin data.

```php
function myplugin_uninstall()
{
    global $db;

    // Drop database tables
    $db->drop_table("myplugin_data");

    // Remove settings
    $db->delete_query("settinggroups", "name = 'myplugin'");
    $db->delete_query("settings", "name LIKE 'myplugin_%'");
    rebuild_settings();
}
```

**Purpose:** Complete cleanup of all plugin data for removal.

#### 6. `{codename}_is_installed()`
Returns boolean indicating if plugin is installed.

```php
function myplugin_is_installed()
{
    global $db;

    return $db->table_exists("myplugin_data");
}
```

**Purpose:** Allows MyBB to detect installation state without executing install/uninstall.

---

## Hook Usage Patterns

### Hook Registration

Hooks are registered in the database (not in code) and auto-loaded via the plugin cache. The MCP `mybb_create_plugin` tool generates hooks automatically:

```php
// Generated by MCP tool - registered in database
// Hooks: index_start, postbit
```

### Hook Handler Functions

Each hook requires a handler function with the codename prefix:

```php
function myplugin_index_start()
{
    global $mybb, $templates, $db;

    // Hook logic here
}

function myplugin_postbit(&$post)
{
    global $mybb;

    // Modify $post data
    $post['message'] .= '<div class="myplugin_suffix">Custom content</div>';
}
```

**Naming Convention:** `{codename}_{hook_name}`

### CSRF Protection in Hook Handlers

**CRITICAL:** Always verify CSRF tokens for POST requests:

```php
function myplugin_form_handler()
{
    global $mybb;

    if ($mybb->request_method == "post") {
        // REQUIRED: Verify CSRF token
        verify_post_check($mybb->get_input('my_post_key'));

        // Process form data
        $data = $mybb->get_input('data', MyBB::INPUT_STRING);

        // ... rest of handler logic
    }
}
```

**Why:** Prevents cross-site request forgery attacks. Templates include token via `{$mybb->post_code}`.

### Common Hook Patterns

**Available via MCP Tools:**
- `mybb_list_hooks` - View all available hooks by category
- `mybb_hooks_discover` - Scan MyBB files for hooks dynamically
- `mybb_hooks_usage` - Find which plugins use a specific hook

**Categories:**
- `index` - Forum index hooks
- `showthread` - Thread display hooks
- `member` - User profile hooks
- `admin` - Admin CP hooks
- `global` - Global hooks (run on every page)

---

## Settings Management

### Creating Settings Groups

Settings are organized into groups displayed in Admin CP:

```php
// In _install()
$db->insert_query("settinggroups", array(
    'name' => 'myplugin',              // Unique group identifier
    'title' => 'My Plugin Settings',   // Display name in Admin CP
    'description' => 'Configure plugin',
    'disporder' => 100,                // Sort order (higher = lower)
    'isdefault' => 0                   // 0 = custom group
));
$gid = $db->insert_id();
```

### Creating Individual Settings

Each setting must reference its group:

```php
$db->insert_query("settings", array(
    'name' => 'myplugin_feature_enabled',     // Unique setting name
    'title' => 'Enable Feature',              // Display label
    'description' => 'Enable or disable',     // Help text
    'optionscode' => 'yesno',                 // Input type
    'value' => '1',                           // Default value
    'disporder' => 1,                         // Order within group
    'gid' => $gid                             // Group ID
));
```

**Input Types (`optionscode`):**
- `yesno` - Yes/No radio buttons
- `text` - Single-line text input
- `textarea` - Multi-line text area
- `select\noption1\noption2` - Dropdown select
- `radio\nvalue1=Label 1\nvalue2=Label 2` - Radio buttons
- `checkbox` - Single checkbox

### Accessing Settings

Settings are available globally via `$mybb->settings`:

```php
global $mybb;

if ($mybb->settings['myplugin_feature_enabled']) {
    // Feature is enabled
}
```

### Rebuilding Settings Cache

**REQUIRED** after modifying settings:

```php
rebuild_settings();  // Updates cache, makes changes available
```

---

## Template Management

### Template Caching

If your plugin uses templates, declare them for caching:

```php
global $templatelist;

if (isset($templatelist)) {
    $templatelist .= ',myplugin_template';
} else {
    $templatelist = 'myplugin_template';
}
```

**Where to add:** In hook handlers that run before templates are loaded (e.g., `global_start`, `index_start`).

### Creating Templates via MCP

Use MCP tools instead of manual database operations:

```php
// Via MCP (recommended):
// mybb_write_template(title="myplugin_template", template="<html>...</html>", sid=1)
```

Template content uses MyBB template syntax:
```html
<div class="myplugin">
    {$variable}
    <if condition="$mybb->user['uid']">
        Logged in content
    <else />
        Guest content
    </if>
</div>
```

### Template Variables

Pass variables to templates:

```php
global $templates;

eval('$myplugin_output = "' . $templates->get('myplugin_template') . '";');
```

MyBB automatically makes these variables available:
- `$mybb` - MyBB core object
- `$db` - Database object
- `$lang` - Language strings
- `$theme` - Current theme data

---

## Database Operations

### Secure Query Patterns

**ALWAYS use parameterized queries or escape_string:**

```php
global $db;

// CORRECT: Parameterized query (preferred)
$query = $db->simple_select(
    "users",
    "uid, username",
    "uid = ?",
    array('bind' => array($user_id))
);

// CORRECT: Escaped string (fallback)
$username = $db->escape_string($mybb->get_input('username'));
$query = $db->simple_select(
    "users",
    "uid, username",
    "username = '{$username}'"
);

// WRONG: Direct concatenation (SQL injection vulnerability)
$query = $db->simple_select(
    "users",
    "uid, username",
    "username = '{$_POST['username']}'"  // NEVER DO THIS
);
```

### Creating Tables

Use proper schema with indexes and character encoding:

```php
$db->write_query("
    CREATE TABLE IF NOT EXISTS " . TABLE_PREFIX . "myplugin_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_user_id (user_id),
        INDEX idx_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
");
```

**Best Practices:**
- Use `TABLE_PREFIX` for table names
- Add indexes on columns used in WHERE clauses
- Use `utf8mb4` for full Unicode support (including emoji)
- Use `InnoDB` for transaction support and foreign keys

### Database Methods

MyBB provides wrapper methods (safer than raw queries):

```php
// INSERT
$db->insert_query("table", array(
    'column1' => $value1,
    'column2' => $value2
));
$id = $db->insert_id();

// SELECT
$query = $db->simple_select(
    "table",
    "column1, column2",
    "id = " . (int)$id
);
$row = $db->fetch_array($query);

// UPDATE
$db->update_query("table", array(
    'column1' => $value1
), "id = " . (int)$id);

// DELETE
$db->delete_query("table", "id = " . (int)$id);
```

**Always cast user input:**
- `(int)$value` for integers
- `$db->escape_string($value)` for strings

---

## Plugin Workspace Structure

The Plugin Manager creates this workspace layout:

```
plugin_manager/plugins/{visibility}/{codename}/
├── inc/
│   ├── plugins/
│   │   └── {codename}.php          # Main plugin file
│   └── languages/
│       └── english/
│           └── {codename}.lang.php # Language strings
├── jscripts/                        # JavaScript files (optional)
├── images/                          # Image assets (optional)
├── meta.json                        # Plugin metadata
└── README.md                        # Documentation
```

**Visibility:**
- `public/` - Public plugins (shareable)
- `private/` - Private plugins (internal use)

### meta.json Structure

```json
{
  "codename": "myplugin",
  "display_name": "My Plugin",
  "type": "plugin",
  "version": "1.0.0",
  "author": "Author Name",
  "description": "Plugin description",
  "mybb_compatibility": "18*"
}
```

---

## Deployment Workflow

### 1. Create Plugin via MCP

```
mybb_create_plugin(
    codename="myplugin",
    name="My Plugin",
    description="Plugin description",
    hooks=["index_start", "postbit"],
    has_settings=true,
    has_templates=true,
    has_database=true
)
```

This creates the workspace and scaffolds the PHP file with lifecycle functions.

### 2. Develop in Workspace

Edit files in `plugin_manager/plugins/public/myplugin/inc/plugins/myplugin.php`.

### 3. Deploy to TestForum

```
mybb_plugin_install(codename="myplugin")
```

This deploys files AND executes `_install()` and `_activate()` lifecycle functions.

### 4. Verify Installation

```
mybb_plugin_status(codename="myplugin")
```

Returns: installation state, activation state, compatibility check.

---

## Complex Plugin Architecture

For plugins with multiple files, classes, JavaScript, and Admin CP pages.

### Multi-File Plugin Structure

```
plugin_manager/plugins/public/myplugin/
├── inc/
│   ├── plugins/
│   │   ├── myplugin.php                 # Main plugin file (lifecycle + hooks)
│   │   └── myplugin/                    # Plugin subdirectory
│   │       ├── core.php                 # Core functionality class
│   │       ├── handlers.php             # Hook handler functions
│   │       ├── admin.php                # Admin CP module
│   │       ├── ajax.php                 # AJAX handlers
│   │       └── config.php               # Advanced config (fallback only)
│   └── languages/english/
│       ├── myplugin.lang.php            # Frontend language strings
│       └── admin/myplugin.lang.php      # Admin CP language strings
├── jscripts/
│   └── myplugin.js                      # Frontend JavaScript
├── images/myplugin/                     # Plugin images
├── styles/
│   └── myplugin.css                     # Plugin stylesheet
├── meta.json
└── README.md
```

### Loading Plugin Files

In your main plugin file, load additional files as needed:

```php
<?php
// myplugin.php

if (!defined('IN_MYBB')) {
    die('Direct access not allowed.');
}

define('MYPLUGIN_PATH', MYBB_ROOT . 'inc/plugins/myplugin/');

// Hooks registered at file load time
$plugins->add_hook('global_start', 'myplugin_global_start');
$plugins->add_hook('index_start', 'myplugin_index_start');
$plugins->add_hook('xmlhttp', 'myplugin_ajax_handler');
$plugins->add_hook('admin_config_menu', 'myplugin_admin_menu');
$plugins->add_hook('admin_config_action_handler', 'myplugin_admin_action');
$plugins->add_hook('admin_load', 'myplugin_admin_load');

// Load handlers (contains hook handler functions)
require_once MYPLUGIN_PATH . 'handlers.php';

// Lifecycle functions below...
```

### Namespace and Class Organization

For larger plugins, use classes with proper namespacing:

```php
<?php
// inc/plugins/myplugin/core.php

namespace MyPlugin;

class Core
{
    private static ?self $instance = null;
    private array $config;

    public static function getInstance(): self
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct()
    {
        global $mybb;

        // Load config from settings with file fallback
        $this->loadConfig();
    }

    private function loadConfig(): void
    {
        global $mybb;

        $fileConfig = file_exists(MYPLUGIN_PATH . 'config.php')
            ? require MYPLUGIN_PATH . 'config.php'
            : [];

        $this->config = [
            'enabled' => isset($mybb->settings['myplugin_enabled'])
                ? (bool)$mybb->settings['myplugin_enabled']
                : ($fileConfig['enabled'] ?? true),
            'cache_ttl' => isset($mybb->settings['myplugin_cache_ttl'])
                ? (int)$mybb->settings['myplugin_cache_ttl']
                : ($fileConfig['cache_ttl'] ?? 3600),
            // ... more settings
        ];
    }

    public function getConfig(string $key, $default = null)
    {
        return $this->config[$key] ?? $default;
    }

    public function isEnabled(): bool
    {
        return $this->config['enabled'];
    }
}
```

---

## JavaScript Integration

### Adding JavaScript Files

**Method 1: Via global_end hook (recommended)**

```php
function myplugin_global_end()
{
    global $mybb, $headerinclude;

    // Only load on specific pages if needed
    if (THIS_SCRIPT !== 'showthread.php') {
        return;
    }

    // Add JavaScript
    $headerinclude .= '<script type="text/javascript" src="' . $mybb->asset_url . '/jscripts/myplugin.js?ver=1.0.0"></script>';
}
```

**Method 2: Template modification via find_replace**

```php
function myplugin_activate()
{
    require_once MYBB_ROOT . 'inc/adminfunctions_templates.php';

    find_replace_templatesets(
        'headerinclude',
        '#\\{\\$stylesheets\\}#',
        '{$stylesheets}<script type="text/javascript" src="{$mybb->asset_url}/jscripts/myplugin.js"></script>'
    );
}

function myplugin_deactivate()
{
    require_once MYBB_ROOT . 'inc/adminfunctions_templates.php';

    find_replace_templatesets(
        'headerinclude',
        '#<script type="text/javascript" src="\\{\\$mybb->asset_url\\}/jscripts/myplugin\\.js"></script>#',
        ''
    );
}
```

### JavaScript Best Practices

```javascript
// jscripts/myplugin.js

var MyPlugin = {
    init: function() {
        // Initialize when DOM ready
        $(document).ready(function() {
            MyPlugin.bindEvents();
        });
    },

    bindEvents: function() {
        // Use delegated events for dynamic content
        $(document).on('click', '.myplugin-button', function(e) {
            e.preventDefault();
            MyPlugin.handleClick($(this));
        });
    },

    handleClick: function($element) {
        var postId = $element.data('pid');
        MyPlugin.sendAjax('action', { pid: postId });
    },

    sendAjax: function(action, data) {
        data.action = 'myplugin_' + action;
        data.my_post_key = my_post_key; // CSRF token (global in MyBB)

        $.ajax({
            url: 'xmlhttp.php',
            type: 'POST',
            data: data,
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    MyPlugin.onSuccess(response);
                } else {
                    MyPlugin.onError(response.error);
                }
            },
            error: function() {
                MyPlugin.onError('Request failed');
            }
        });
    },

    onSuccess: function(response) {
        // Handle success
    },

    onError: function(message) {
        alert(message);
    }
};

MyPlugin.init();
```

---

## AJAX Handlers

### Setting Up AJAX via xmlhttp Hook

```php
// In main plugin file
$plugins->add_hook('xmlhttp', 'myplugin_ajax_handler');

// In handlers.php
function myplugin_ajax_handler()
{
    global $mybb, $charset;

    // Check if this is our action
    $action = $mybb->get_input('action');
    if (strpos($action, 'myplugin_') !== 0) {
        return;
    }

    // CSRF verification (REQUIRED)
    verify_post_check($mybb->get_input('my_post_key'));

    // Must be logged in
    if (!$mybb->user['uid']) {
        myplugin_ajax_error('You must be logged in.');
    }

    // Route to specific handler
    switch ($action) {
        case 'myplugin_vote':
            myplugin_ajax_vote();
            break;
        case 'myplugin_delete':
            myplugin_ajax_delete();
            break;
        default:
            myplugin_ajax_error('Invalid action.');
    }
}

function myplugin_ajax_vote()
{
    global $mybb, $db;

    $post_id = $mybb->get_input('pid', MyBB::INPUT_INT);
    $vote = $mybb->get_input('vote', MyBB::INPUT_INT);

    if (!$post_id || !in_array($vote, [-1, 1])) {
        myplugin_ajax_error('Invalid parameters.');
    }

    // Process vote...
    $db->insert_query('myplugin_votes', [
        'pid' => $post_id,
        'uid' => $mybb->user['uid'],
        'vote' => $vote,
        'dateline' => TIME_NOW
    ]);

    myplugin_ajax_success(['message' => 'Vote recorded!', 'new_score' => 42]);
}

function myplugin_ajax_success(array $data = [])
{
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(array_merge(['success' => true], $data));
    exit;
}

function myplugin_ajax_error(string $message)
{
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['success' => false, 'error' => $message]);
    exit;
}
```

---

## Stylesheet Integration

### Adding CSS Files

**Method 1: Inject in headerinclude (global_end hook)**

```php
function myplugin_global_end()
{
    global $mybb, $headerinclude;

    $headerinclude .= '<link rel="stylesheet" href="' . $mybb->asset_url . '/styles/myplugin.css?ver=1.0.0" />';
}
```

**Method 2: Create stylesheet in database (_activate)**

```php
function myplugin_activate()
{
    global $db;

    // Read CSS from file
    $css = file_get_contents(MYBB_ROOT . 'styles/myplugin.css');

    // Insert stylesheet record
    $stylesheet = [
        'name'         => 'myplugin.css',
        'tid'          => 1,  // Theme ID (1 = default)
        'attachedto'   => '', // Empty = all pages, or 'showthread.php,forumdisplay.php'
        'stylesheet'   => $db->escape_string($css),
        'cachefile'    => 'myplugin.css',
        'lastmodified' => TIME_NOW
    ];
    $db->insert_query('themestylesheets', $stylesheet);

    // Update theme stylesheet list
    require_once MYBB_ROOT . 'inc/adminfunctions_templates.php';
    update_theme_stylesheet_list(1);
}

function myplugin_deactivate()
{
    global $db;

    // Remove stylesheet
    $db->delete_query('themestylesheets', "name = 'myplugin.css'");

    // Update theme stylesheet list
    require_once MYBB_ROOT . 'inc/adminfunctions_templates.php';
    update_theme_stylesheet_list(1);
}
```

**Method 3: Inline styles (small CSS only)**

```php
function myplugin_global_end()
{
    global $headerinclude;

    $headerinclude .= '<style>
.myplugin-badge {
    display: inline-block;
    padding: 2px 8px;
    background: #4a90d9;
    color: #fff;
    border-radius: 4px;
    font-size: 11px;
}
</style>';
}
```

---

## Admin CP Modules

### Creating an Admin Page

```php
// Hook registration in main file
$plugins->add_hook('admin_config_menu', 'myplugin_admin_menu');
$plugins->add_hook('admin_config_action_handler', 'myplugin_admin_action');
$plugins->add_hook('admin_load', 'myplugin_admin_load');

// In handlers.php or admin.php
function myplugin_admin_menu(&$sub_menu)
{
    global $lang;
    $lang->load('myplugin', false, true);

    $sub_menu[] = [
        'id'    => 'myplugin',
        'title' => $lang->myplugin_admin_title ?? 'My Plugin',
        'link'  => 'index.php?module=config-myplugin'
    ];
}

function myplugin_admin_action(&$actions)
{
    $actions['myplugin'] = ['active' => 'myplugin'];
}

function myplugin_admin_load()
{
    global $mybb, $page, $db, $lang;

    if ($page->active_action !== 'myplugin') {
        return;
    }

    $lang->load('myplugin', false, true);

    // Page header
    $page->add_breadcrumb_item($lang->myplugin_admin_title ?? 'My Plugin');
    $page->output_header($lang->myplugin_admin_title ?? 'My Plugin');

    // Tabs
    $tabs = [
        'main'     => $lang->myplugin_tab_main ?? 'Main',
        'settings' => $lang->myplugin_tab_settings ?? 'Settings',
        'logs'     => $lang->myplugin_tab_logs ?? 'Logs'
    ];

    $page->output_nav_tabs($tabs, 'main');

    // Handle form submission
    if ($mybb->request_method === 'post') {
        verify_post_check($mybb->get_input('my_post_key'));

        // Process form...
        flash_message($lang->myplugin_saved ?? 'Settings saved.', 'success');
        admin_redirect('index.php?module=config-myplugin');
    }

    // Build form
    $form = new Form('index.php?module=config-myplugin', 'post');

    $form_container = new FormContainer($lang->myplugin_settings ?? 'Settings');
    $form_container->output_row(
        $lang->myplugin_option1 ?? 'Option 1',
        $lang->myplugin_option1_desc ?? 'Description',
        $form->generate_yes_no_radio('myplugin_option1', $mybb->settings['myplugin_option1'])
    );
    $form_container->end();

    $buttons[] = $form->generate_submit_button($lang->myplugin_save ?? 'Save');
    $form->output_submit_wrapper($buttons);
    $form->end();

    $page->output_footer();
    exit;
}
```

### Admin Language File

```php
<?php
// inc/languages/english/admin/myplugin.lang.php

$l['myplugin_admin_title'] = 'My Plugin';
$l['myplugin_tab_main'] = 'Main';
$l['myplugin_tab_settings'] = 'Settings';
$l['myplugin_tab_logs'] = 'Logs';
$l['myplugin_settings'] = 'Plugin Settings';
$l['myplugin_option1'] = 'Enable Feature';
$l['myplugin_option1_desc'] = 'Enable or disable the main feature.';
$l['myplugin_save'] = 'Save Settings';
$l['myplugin_saved'] = 'Settings saved successfully.';
```

---

## Template Groups

### Organizing Plugin Templates

Group your templates logically for Admin CP display:

```php
function myplugin_activate()
{
    global $db;

    // Create template group
    $db->insert_query('templategroups', [
        'prefix' => 'myplugin',
        'title'  => '<lang:myplugin_tpl_group>',
        'isdefault' => 0
    ]);

    // Create templates (they'll be grouped by prefix)
    $templates = [
        'myplugin_main'   => '<div class="myplugin-container">{$content}</div>',
        'myplugin_item'   => '<div class="myplugin-item">{$item_content}</div>',
        'myplugin_button' => '<a href="{$url}" class="myplugin-btn">{$label}</a>',
    ];

    foreach ($templates as $title => $template) {
        $db->insert_query('templates', [
            'title'    => $title,
            'template' => $db->escape_string($template),
            'sid'      => -2,  // Master templates
            'version'  => '',
            'dateline' => TIME_NOW
        ]);
    }
}

function myplugin_deactivate()
{
    global $db;

    // Remove templates
    $db->delete_query('templates', "title LIKE 'myplugin_%' AND sid = -2");

    // Remove template group
    $db->delete_query('templategroups', "prefix = 'myplugin'");
}
```

---

## Security Checklist

- [ ] All user input escaped with `$db->escape_string()`
- [ ] Parameterized queries used (or proper escaping)
- [ ] CSRF verification in all POST handlers (`verify_post_check()`)
- [ ] Integer values cast with `(int)$value`
- [ ] No direct `$_POST`, `$_GET`, `$_COOKIE` access (use `$mybb->get_input()`)
- [ ] Sensitive fields excluded from queries (no password, salt, loginkey exposure)
- [ ] File operations validate paths (no directory traversal)
- [ ] Settings have sensible defaults
- [ ] Database tables use proper character encoding (utf8mb4)

---

## Common Pitfalls

### Function Naming
❌ **WRONG:** `function myFunction()` (missing codename prefix)
✅ **CORRECT:** `function myplugin_myFunction()`

### SQL Injection
❌ **WRONG:** `"WHERE username = '{$_POST['name']}'"`
✅ **CORRECT:** `"WHERE username = '" . $db->escape_string($mybb->get_input('name')) . "'"`

### CSRF Protection
❌ **WRONG:** Processing POST without token verification
✅ **CORRECT:** `verify_post_check($mybb->get_input('my_post_key'));`

### Settings Cache
❌ **WRONG:** Modifying settings without rebuilding cache
✅ **CORRECT:** `rebuild_settings();` after modifications

---

## Testing Your Plugin

1. **Install/Uninstall Cycle**: Verify clean installation and complete removal
2. **Activate/Deactivate Cycle**: Ensure hooks work when active, disabled when inactive
3. **Settings**: Test all setting options and defaults
4. **Templates**: Verify template variables and conditional logic
5. **Database**: Check table creation, indexes, and query performance
6. **Security**: Test with malicious input (SQL injection attempts, XSS)
7. **Compatibility**: Test on fresh MyBB 1.8.x installation

---

## Additional Resources

- [MCP Plugin Tools](../mcp_tools/plugins.md) - 12 plugin management tools
- [Plugin Manager Guide](../plugin_manager/index.md) - Workspace and deployment
- [Security Guide](security.md) - Complete security best practices
- [MyBB Plugin Documentation](https://docs.mybb.com/1.8/development/plugins/)

---

**Last Updated:** 2026-01-18
