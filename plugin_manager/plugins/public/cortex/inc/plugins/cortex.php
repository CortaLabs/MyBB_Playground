<?php
/**
 * Cortex - Secure template conditionals for MyBB 1.8.x (PHP 8.1+)
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 * @version 1.0.0
 */

// Prevent direct access
if (!defined('IN_MYBB')) {
    die('This file cannot be accessed directly.');
}

// PHP version check - Cortex requires PHP 8.1+
if (PHP_VERSION_ID < 80100) {
    return;
}

// Define plugin constants
define('CORTEX_VERSION', '1.0.0');
define('CORTEX_PATH', __DIR__ . '/cortex/');

/**
 * PSR-4 Autoloader for Cortex namespace
 * Maps Cortex\ClassName to inc/plugins/cortex/src/ClassName.php
 */
spl_autoload_register(function (string $class): void {
    $prefix = 'Cortex\\';
    $baseDir = __DIR__ . '/cortex/src/';

    // Check if the class uses the Cortex namespace
    $len = strlen($prefix);
    if (strncmp($prefix, $class, $len) !== 0) {
        return;
    }

    // Get the relative class name
    $relativeClass = substr($class, $len);

    // Replace namespace separators with directory separators
    $file = $baseDir . str_replace('\\', '/', $relativeClass) . '.php';

    // Load the file if it exists
    if (file_exists($file)) {
        require $file;
    }
});

// Register hooks with priority 5 (runs early)
$plugins->add_hook('global_start', 'cortex_init', 5);
$plugins->add_hook('xmlhttp', 'cortex_init', 5);

// Admin hooks to clear cache when plugins or templates change
$plugins->add_hook('admin_config_plugins_activate_commit', 'cortex_clear_cache');
$plugins->add_hook('admin_config_plugins_deactivate_commit', 'cortex_clear_cache');
$plugins->add_hook('admin_style_templates_edit_template_commit', 'cortex_clear_cache');
$plugins->add_hook('admin_tools_cache_rebuild', 'cortex_clear_cache');

/**
 * Plugin information for MyBB Admin CP
 *
 * @return array Plugin metadata
 */
function cortex_info(): array
{
    global $lang;
    $lang->load('cortex', false, true);

    return [
        'name'          => $lang->cortex_name ?? 'Cortex',
        'description'   => $lang->cortex_description ?? 'Secure template conditionals for MyBB 1.8.x (PHP 8.1+)',
        'website'       => 'https://github.com/CortaLabs/cortex',
        'author'        => 'Corta Labs',
        'authorsite'    => '',
        'version'       => CORTEX_VERSION,
        'compatibility' => '18*',
        'codename'      => 'cortex'
    ];
}

/**
 * Plugin activation
 * Called when admin activates the plugin in ACP
 *
 * @return void
 */
function cortex_activate(): void
{
    // Create cache directory for compiled templates
    $cacheDir = MYBB_ROOT . 'cache/cortex/';
    if (!is_dir($cacheDir)) {
        @mkdir($cacheDir, 0755, true);
    }
}

/**
 * Plugin deactivation
 * Called when admin deactivates the plugin in ACP
 *
 * @return void
 */
function cortex_deactivate(): void
{
    // Cache preserved for quick re-activation
    // To clear cache, delete cache/cortex/ directory
}

/**
 * Check if plugin is installed
 *
 * @return bool True if installed
 */
function cortex_is_installed(): bool
{
    global $db;
    $query = $db->simple_select('settinggroups', 'gid', "name = 'cortex'", ['limit' => 1]);
    return (bool) $db->fetch_field($query, 'gid');
}

/**
 * Plugin installation
 * Called once when admin installs the plugin
 *
 * @return void
 */
function cortex_install(): void
{
    global $db, $lang;
    $lang->load('cortex', false, true);

    // Create setting group
    $setting_group = [
        'name'        => 'cortex',
        'title'       => $lang->cortex_settings_title ?? 'Cortex Template Engine',
        'description' => $lang->cortex_settings_desc ?? 'Settings for the Cortex secure template conditionals plugin',
        'disporder'   => 100,
        'isdefault'   => 0
    ];
    $gid = $db->insert_query('settinggroups', $setting_group);

    // Settings array
    $settings = [
        ['name' => 'cortex_enabled', 'title' => 'Enable Cortex', 'description' => 'Enable or disable Cortex template processing', 'optionscode' => 'yesno', 'value' => '1', 'disporder' => 1],
        ['name' => 'cortex_debug_mode', 'title' => 'Debug Mode', 'description' => 'Log parsing errors to PHP error log', 'optionscode' => 'yesno', 'value' => '0', 'disporder' => 2],
        ['name' => 'cortex_cache_enabled', 'title' => 'Enable Cache', 'description' => 'Enable disk caching of compiled templates', 'optionscode' => 'yesno', 'value' => '1', 'disporder' => 3],
        ['name' => 'cortex_cache_ttl', 'title' => 'Cache TTL (seconds)', 'description' => 'Cache expiration time in seconds. 0 = never expires', 'optionscode' => 'numeric', 'value' => '0', 'disporder' => 4],
        ['name' => 'cortex_max_nesting_depth', 'title' => 'Max Nesting Depth', 'description' => 'Maximum nested if-block depth. 0 = unlimited', 'optionscode' => 'numeric', 'value' => '10', 'disporder' => 5],
        ['name' => 'cortex_max_expression_length', 'title' => 'Max Expression Length', 'description' => 'Maximum expression length in characters. 0 = unlimited', 'optionscode' => 'numeric', 'value' => '1000', 'disporder' => 6],
        ['name' => 'cortex_denied_functions', 'title' => 'Denied Functions', 'description' => 'Comma-separated list of functions to block (e.g., strlen,substr)', 'optionscode' => 'textarea', 'value' => '', 'disporder' => 7],
    ];

    foreach ($settings as $setting) {
        $setting['gid'] = $gid;
        $db->insert_query('settings', $setting);
    }

    rebuild_settings();
}

/**
 * Plugin uninstallation
 * Called when admin uninstalls the plugin
 *
 * @return void
 */
function cortex_uninstall(): void
{
    global $db;

    // Remove settings
    $db->delete_query('settings', "name LIKE 'cortex_%'");

    // Remove setting group
    $db->delete_query('settinggroups', "name = 'cortex'");

    rebuild_settings();

    // Optionally clear cache directory
    $cacheDir = MYBB_ROOT . 'cache/cortex/';
    if (is_dir($cacheDir)) {
        $files = glob($cacheDir . '*.php');
        if ($files) {
            foreach ($files as $file) {
                @unlink($file);
            }
        }
    }
}

/**
 * Main initialization hook
 * Called on every page load via global_start and xmlhttp hooks
 *
 * Wraps MyBB's $templates object with Cortex Runtime to enable
 * template conditionals, functions, and expressions.
 *
 * @return void
 */
function cortex_init(): void
{
    global $templates, $lang, $mybb;

    // Load language file
    $lang->load('cortex', false, true);

    // Don't run in Admin CP
    if (defined('IN_ADMINCP')) {
        return;
    }

    // Ensure templates object exists and is valid
    if (!is_object($templates)) {
        return;
    }

    // Don't wrap if already wrapped
    if ($templates instanceof \Cortex\Runtime) {
        return;
    }

    // Load file-based config as defaults
    $fileConfig = require CORTEX_PATH . 'config.php';

    // Build config from MyBB settings with file fallback
    $config = [
        'enabled' => isset($mybb->settings['cortex_enabled'])
            ? (bool)$mybb->settings['cortex_enabled']
            : ($fileConfig['enabled'] ?? true),
        'cache_enabled' => isset($mybb->settings['cortex_cache_enabled'])
            ? (bool)$mybb->settings['cortex_cache_enabled']
            : ($fileConfig['cache_enabled'] ?? true),
        'cache_ttl' => isset($mybb->settings['cortex_cache_ttl'])
            ? (int)$mybb->settings['cortex_cache_ttl']
            : ($fileConfig['cache_ttl'] ?? 0),
        'debug' => isset($mybb->settings['cortex_debug_mode'])
            ? (bool)$mybb->settings['cortex_debug_mode']
            : ($fileConfig['debug'] ?? false),
        'security' => [
            // additional_allowed_functions stays in file config only (security risk if in ACP)
            'additional_allowed_functions' => $fileConfig['security']['additional_allowed_functions'] ?? [],
            'denied_functions' => isset($mybb->settings['cortex_denied_functions'])
                ? array_filter(array_map('trim', explode(',', $mybb->settings['cortex_denied_functions'])))
                : ($fileConfig['security']['denied_functions'] ?? []),
            'max_nesting_depth' => isset($mybb->settings['cortex_max_nesting_depth'])
                ? (int)$mybb->settings['cortex_max_nesting_depth']
                : ($fileConfig['security']['max_nesting_depth'] ?? 10),
            'max_expression_length' => isset($mybb->settings['cortex_max_expression_length'])
                ? (int)$mybb->settings['cortex_max_expression_length']
                : ($fileConfig['security']['max_expression_length'] ?? 1000),
        ],
    ];

    // Skip if disabled
    if (empty($config['enabled'])) {
        return;
    }

    // Wrap templates with Cortex Runtime
    try {
        $runtime = new \Cortex\Runtime($templates, $config);
        $templates = $runtime;
    } catch (\Throwable $e) {
        if (!empty($config['debug'])) {
            error_log('Cortex initialization failed: ' . $e->getMessage());
        }
    }
}

/**
 * Clear all Cortex compiled template cache.
 *
 * Called automatically when:
 * - Any plugin is activated or deactivated
 * - Templates are edited in Admin CP
 * - Cache is rebuilt via Admin CP Tools
 *
 * Can also be called manually: cortex_clear_cache()
 *
 * @return int Number of cache files removed
 */
function cortex_clear_cache(): int
{
    $cacheDir = MYBB_ROOT . 'cache/cortex/';

    if (!is_dir($cacheDir)) {
        return 0;
    }

    $count = 0;
    $files = glob($cacheDir . '*.php');

    if ($files === false) {
        return 0;
    }

    foreach ($files as $file) {
        if (@unlink($file)) {
            $count++;
        }
    }

    return $count;
}
