<?php
/**
 * MCP Bridge - CLI interface to MyBB
 *
 * Provides a standardized JSON API for external tools to interact with MyBB.
 * Bootstraps MyBB properly and uses MyBB's own systems for all operations.
 *
 * Usage: php mcp_bridge.php --action=<action> [options] --json
 *
 * Actions:
 *   plugin:status    - Get plugin status and info
 *   plugin:activate  - Install (if needed) and activate a plugin
 *   plugin:deactivate - Deactivate a plugin (optionally uninstall)
 *   plugin:list      - List all plugins with status
 *   cache:read       - Read a cache entry
 *   cache:rebuild    - Rebuild cache
 *   info             - Get MyBB installation info
 *
 * @author MCP Bridge
 * @version 1.0.0
 */

// ============================================================================
// Security: CLI only
// ============================================================================
if (php_sapi_name() !== 'cli') {
    http_response_code(403);
    die('CLI access only.');
}

// ============================================================================
// Parse CLI arguments
// ============================================================================
$options = getopt('', [
    'action:',
    'plugin:',
    'uninstall',
    'force',
    'json',
    'cache:',
    'help'
]);

// Help output
if (isset($options['help']) || empty($options['action'])) {
    echo <<<HELP
MCP Bridge - CLI interface to MyBB

Usage: php mcp_bridge.php --action=<action> [options] --json

Actions:
  plugin:status     Get plugin status and info
                    --plugin=<codename>

  plugin:activate   Install (if needed) and activate a plugin
                    --plugin=<codename>
                    --force (skip compatibility check)

  plugin:deactivate Deactivate a plugin
                    --plugin=<codename>
                    --uninstall (also run uninstall function)

  plugin:list       List all plugins with their status

  cache:read        Read a cache entry
                    --cache=<cache_name>

  cache:rebuild     Rebuild settings cache

  info              Get MyBB installation info

Options:
  --json            Output as JSON (recommended for programmatic use)
  --help            Show this help message

Examples:
  php mcp_bridge.php --action=plugin:status --plugin=hello_world --json
  php mcp_bridge.php --action=plugin:activate --plugin=hello_world --json
  php mcp_bridge.php --action=plugin:deactivate --plugin=hello_world --uninstall --json
  php mcp_bridge.php --action=plugin:list --json
  php mcp_bridge.php --action=info --json

HELP;
    exit(0);
}

$action = $options['action'] ?? '';
$outputJson = isset($options['json']);

// ============================================================================
// Response helper
// ============================================================================
function respond($success, $data = [], $error = null) {
    global $outputJson;

    $response = [
        'success' => $success,
        'timestamp' => date('c'),
        'data' => $data
    ];

    if ($error !== null) {
        $response['error'] = $error;
    }

    if ($outputJson) {
        echo json_encode($response, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n";
    } else {
        if ($success) {
            echo "SUCCESS\n";
            print_r($data);
        } else {
            echo "ERROR: " . ($error ?? 'Unknown error') . "\n";
            if (!empty($data)) {
                print_r($data);
            }
        }
    }

    exit($success ? 0 : 1);
}

// ============================================================================
// Bootstrap MyBB
// ============================================================================
// Change to MyBB root directory for proper path resolution
chdir(__DIR__);

// Define required constants before loading MyBB
define('IN_MYBB', 1);
define('THIS_SCRIPT', 'mcp_bridge.php');

// Suppress plugin loading during bootstrap - we'll handle plugins manually
// This prevents hooks from firing during our CLI operations
define('NO_PLUGINS', 1);

// Capture any output/errors during bootstrap
ob_start();

try {
    // Load MyBB core
    require_once __DIR__ . '/inc/init.php';
} catch (Exception $e) {
    ob_end_clean();
    respond(false, [], 'Failed to bootstrap MyBB: ' . $e->getMessage());
}

// Clear bootstrap output
ob_end_clean();

// Verify MyBB loaded correctly
if (!isset($mybb) || !isset($db) || !isset($cache)) {
    respond(false, [], 'MyBB core objects not initialized');
}

// ============================================================================
// Action Router
// ============================================================================
switch ($action) {
    // ========================================================================
    // Plugin Actions
    // ========================================================================
    case 'plugin:status':
        $codename = $options['plugin'] ?? '';
        if (empty($codename)) {
            respond(false, [], 'Plugin codename required (--plugin=<codename>)');
        }

        $codename = preg_replace('/[^a-zA-Z0-9_]/', '', $codename);
        $file = MYBB_ROOT . "inc/plugins/{$codename}.php";

        if (!file_exists($file)) {
            respond(false, ['codename' => $codename], "Plugin file not found: {$codename}.php");
        }

        // Load plugin to get info
        require_once $file;

        $info_func = "{$codename}_info";
        if (!function_exists($info_func)) {
            respond(false, ['codename' => $codename], "Plugin missing {$codename}_info() function");
        }

        $info = $info_func();

        // Check if installed
        $is_installed_func = "{$codename}_is_installed";
        $is_installed = true;
        if (function_exists($is_installed_func)) {
            $is_installed = $is_installed_func();
        }

        // Check if active
        $plugins_cache = $cache->read('plugins');
        $active_plugins = isset($plugins_cache['active']) ? $plugins_cache['active'] : [];
        $is_active = isset($active_plugins[$codename]);

        // Check compatibility
        $is_compatible = $plugins->is_compatible($codename);

        respond(true, [
            'codename' => $codename,
            'info' => $info,
            'is_installed' => $is_installed,
            'is_active' => $is_active,
            'is_compatible' => $is_compatible,
            'has_install' => function_exists("{$codename}_install"),
            'has_uninstall' => function_exists("{$codename}_uninstall"),
            'has_activate' => function_exists("{$codename}_activate"),
            'has_deactivate' => function_exists("{$codename}_deactivate"),
            'file_path' => $file
        ]);
        break;

    case 'plugin:activate':
        $codename = $options['plugin'] ?? '';
        if (empty($codename)) {
            respond(false, [], 'Plugin codename required (--plugin=<codename>)');
        }

        $codename = preg_replace('/[^a-zA-Z0-9_]/', '', $codename);
        $file = MYBB_ROOT . "inc/plugins/{$codename}.php";
        $force = isset($options['force']);

        if (!file_exists($file)) {
            respond(false, ['codename' => $codename], "Plugin file not found: {$codename}.php");
        }

        // Load the plugin
        require_once $file;

        // Verify _info function exists
        $info_func = "{$codename}_info";
        if (!function_exists($info_func)) {
            respond(false, ['codename' => $codename], "Plugin missing {$codename}_info() function");
        }

        $info = $info_func();

        // Check compatibility (unless forced)
        if (!$force && !$plugins->is_compatible($codename)) {
            respond(false, [
                'codename' => $codename,
                'mybb_version' => $mybb->version,
                'plugin_compatibility' => $info['compatibility'] ?? 'not specified'
            ], "Plugin incompatible with MyBB {$mybb->version}. Use --force to override.");
        }

        // Get current plugin cache
        $plugins_cache = $cache->read('plugins');
        $active_plugins = isset($plugins_cache['active']) ? $plugins_cache['active'] : [];

        // Check if already active
        if (isset($active_plugins[$codename])) {
            respond(true, [
                'codename' => $codename,
                'action' => 'none',
                'message' => 'Plugin already active'
            ]);
        }

        $actions_taken = [];

        // Check if installed
        $is_installed_func = "{$codename}_is_installed";
        $is_installed = true;
        if (function_exists($is_installed_func)) {
            $is_installed = $is_installed_func();
        }

        // Run install if needed
        $install_func = "{$codename}_install";
        if (!$is_installed && function_exists($install_func)) {
            try {
                call_user_func($install_func);
                $actions_taken[] = 'installed';
            } catch (Exception $e) {
                respond(false, ['codename' => $codename], "Install failed: " . $e->getMessage());
            }
        }

        // Run activate
        $activate_func = "{$codename}_activate";
        if (function_exists($activate_func)) {
            try {
                call_user_func($activate_func);
                $actions_taken[] = 'activated';
            } catch (Exception $e) {
                respond(false, ['codename' => $codename, 'actions_taken' => $actions_taken], "Activate failed: " . $e->getMessage());
            }
        }

        // Update plugin cache
        $active_plugins[$codename] = $codename;
        $plugins_cache['active'] = $active_plugins;
        $cache->update('plugins', $plugins_cache);
        $actions_taken[] = 'cache_updated';

        respond(true, [
            'codename' => $codename,
            'actions_taken' => $actions_taken,
            'info' => $info
        ]);
        break;

    case 'plugin:deactivate':
        $codename = $options['plugin'] ?? '';
        if (empty($codename)) {
            respond(false, [], 'Plugin codename required (--plugin=<codename>)');
        }

        $codename = preg_replace('/[^a-zA-Z0-9_]/', '', $codename);
        $file = MYBB_ROOT . "inc/plugins/{$codename}.php";
        $uninstall = isset($options['uninstall']);

        // Get current plugin cache
        $plugins_cache = $cache->read('plugins');
        $active_plugins = isset($plugins_cache['active']) ? $plugins_cache['active'] : [];

        // Check if active
        if (!isset($active_plugins[$codename])) {
            // Still allow uninstall even if not active
            if (!$uninstall) {
                respond(true, [
                    'codename' => $codename,
                    'action' => 'none',
                    'message' => 'Plugin not active'
                ]);
            }
        }

        $actions_taken = [];

        // Load plugin if file exists (needed for deactivate/uninstall functions)
        if (file_exists($file)) {
            require_once $file;

            // Run deactivate
            $deactivate_func = "{$codename}_deactivate";
            if (function_exists($deactivate_func)) {
                try {
                    call_user_func($deactivate_func);
                    $actions_taken[] = 'deactivated';
                } catch (Exception $e) {
                    respond(false, ['codename' => $codename], "Deactivate failed: " . $e->getMessage());
                }
            }

            // Run uninstall if requested
            if ($uninstall) {
                $uninstall_func = "{$codename}_uninstall";
                if (function_exists($uninstall_func)) {
                    try {
                        call_user_func($uninstall_func);
                        $actions_taken[] = 'uninstalled';
                    } catch (Exception $e) {
                        respond(false, ['codename' => $codename, 'actions_taken' => $actions_taken], "Uninstall failed: " . $e->getMessage());
                    }
                }
            }
        }

        // Update plugin cache
        unset($active_plugins[$codename]);
        $plugins_cache['active'] = $active_plugins;
        $cache->update('plugins', $plugins_cache);
        $actions_taken[] = 'cache_updated';

        respond(true, [
            'codename' => $codename,
            'actions_taken' => $actions_taken,
            'uninstalled' => $uninstall
        ]);
        break;

    case 'plugin:list':
        $plugins_dir = MYBB_ROOT . 'inc/plugins/';
        $plugins_cache = $cache->read('plugins');
        $active_plugins = isset($plugins_cache['active']) ? $plugins_cache['active'] : [];

        $plugin_list = [];

        if (is_dir($plugins_dir)) {
            $files = scandir($plugins_dir);
            foreach ($files as $file) {
                if (pathinfo($file, PATHINFO_EXTENSION) !== 'php') {
                    continue;
                }

                $codename = pathinfo($file, PATHINFO_FILENAME);

                // Skip index.php and other system files
                if (in_array($codename, ['index', 'hello'])) {
                    continue;
                }

                $plugin_info = [
                    'codename' => $codename,
                    'file' => $file,
                    'is_active' => isset($active_plugins[$codename])
                ];

                // Try to load info
                try {
                    require_once $plugins_dir . $file;
                    $info_func = "{$codename}_info";
                    if (function_exists($info_func)) {
                        $info = $info_func();
                        $plugin_info['name'] = $info['name'] ?? $codename;
                        $plugin_info['version'] = $info['version'] ?? 'unknown';
                        $plugin_info['author'] = $info['author'] ?? 'unknown';
                        $plugin_info['compatibility'] = $info['compatibility'] ?? '*';
                        $plugin_info['is_compatible'] = $plugins->is_compatible($codename);
                    }

                    // Check installed status
                    $is_installed_func = "{$codename}_is_installed";
                    if (function_exists($is_installed_func)) {
                        $plugin_info['is_installed'] = $is_installed_func();
                    } else {
                        $plugin_info['is_installed'] = null;
                    }
                } catch (Exception $e) {
                    $plugin_info['error'] = $e->getMessage();
                }

                $plugin_list[] = $plugin_info;
            }
        }

        respond(true, [
            'plugins' => $plugin_list,
            'count' => count($plugin_list),
            'active_count' => count($active_plugins)
        ]);
        break;

    // ========================================================================
    // Cache Actions
    // ========================================================================
    case 'cache:read':
        $cache_name = $options['cache'] ?? '';
        if (empty($cache_name)) {
            respond(false, [], 'Cache name required (--cache=<name>)');
        }

        $cache_name = preg_replace('/[^a-zA-Z0-9_]/', '', $cache_name);
        $data = $cache->read($cache_name);

        respond(true, [
            'cache_name' => $cache_name,
            'data' => $data
        ]);
        break;

    case 'cache:rebuild':
        // Rebuild settings cache
        rebuild_settings();

        respond(true, [
            'message' => 'Settings cache rebuilt'
        ]);
        break;

    // ========================================================================
    // Info Action
    // ========================================================================
    case 'info':
        respond(true, [
            'mybb_version' => $mybb->version,
            'mybb_version_code' => $mybb->version_code,
            'php_version' => PHP_VERSION,
            'database_type' => $db->type,
            'table_prefix' => TABLE_PREFIX,
            'mybb_root' => MYBB_ROOT,
            'board_url' => $settings['bburl'] ?? null,
            'board_name' => $settings['bbname'] ?? null
        ]);
        break;

    // ========================================================================
    // Unknown Action
    // ========================================================================
    default:
        respond(false, ['action' => $action], "Unknown action: {$action}. Use --help for usage.");
}
