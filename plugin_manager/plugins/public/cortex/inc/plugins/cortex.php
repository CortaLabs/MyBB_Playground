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
    // Cortex has no database tables - always considered installed
    return true;
}

/**
 * Plugin installation
 * Called once when admin installs the plugin
 *
 * @return void
 */
function cortex_install(): void
{
    // No database tables required
}

/**
 * Plugin uninstallation
 * Called when admin uninstalls the plugin
 *
 * @return void
 */
function cortex_uninstall(): void
{
    // No database cleanup required
    // Optionally clear cache directory here
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
    global $templates, $lang;

    // Load language file
    $lang->load('cortex', false, true);

    // Don't run in Admin CP - templates there don't need processing
    if (defined('IN_ADMINCP')) {
        return;
    }

    // Ensure templates object exists and is valid
    if (!is_object($templates)) {
        return;
    }

    // Don't wrap if already wrapped (prevents double-wrapping)
    if ($templates instanceof \Cortex\Runtime) {
        return;
    }

    // Load configuration
    $config = require CORTEX_PATH . 'config.php';

    // Skip if disabled in config
    if (empty($config['enabled'])) {
        return;
    }

    // Wrap templates with Cortex Runtime
    try {
        $runtime = new \Cortex\Runtime($templates, $config);
        $templates = $runtime;
    } catch (\Throwable $e) {
        // If Runtime fails to initialize, log and continue with original templates
        // Site must never break due to Cortex initialization failure
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
