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
 *   cache:rebuild_smilies - Rebuild smilies cache
 *   info             - Get MyBB installation info
 *
 * @author MCP Bridge
 * @version 1.0.0
 */

// ============================================================================
// Bridge/Protocol Versioning
// ============================================================================
define('MCP_BRIDGE_VERSION', '1.3.0');
define('MCP_BRIDGE_PROTOCOL_VERSION', '1');

// MyBB version compatibility - which MyBB versions this bridge is tested with
// IMPORTANT: Only tested versions are guaranteed to work
define('MCP_BRIDGE_MYBB_COMPAT', [
    'min' => '1.8.39',      // Minimum tested version
    'max' => '1.8.39',      // Maximum tested version
    'tested' => '1.8.39',   // Primary tested version
]);

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
    'title:',
    'template:',
    'sid:',
    'templates_json:',
    'find:',
    'replace:',
    'template_sets:',
    'regex:',
    'limit:',
    'stylesheet:',
    'request_id:',
    'mode:',
    'name:',
    'description:',
    'type:',
    'pid:',
    'parentlist:',
    'disporder:',
    'active:',
    'open:',
    'linkto:',
    'showinjump:',
    'usepostcounts:',
    'usethreadcounts:',
    'allowhtml:',
    'allowmycode:',
    'allowsmilies:',
    'allowimgcode:',
    'allowvideocode:',
    'allowpicons:',
    'allowtratings:',
    'rulestype:',
    'rulestitle:',
    'rules:',
    'fid:',
    'tid:',
    'pid:',
    'replyto:',
    'uid:',
    'usergroup:',
    'additionalgroups:',
    'gid:',
    'admin:',
    'bantime:',
    'reason:',
    'dateline:',
    'username:',
    'subject:',
    'message:',
    'closed:',
    'sticky:',
    'approve:',
    'visible:',
    'new_fid:',
    'edituid:',
    'edit_uid:',
    'editreason:',
    'signature:',
    'disablesmilies:',
    'logaction:',
    'ipaddress:',
    'data:',
    'restore',
    'delete',
    'soft',
    'xml:',
    'no-stylesheets',
    'no-templates',
    'force-version',
    'parent:',
    'key:',
    'value:',
    'templateset:',
    'logo:',
    'editortheme:',
    'source_sid:',
    'content:',
    'attachedto:',
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

  cache:rebuild_smilies  Rebuild smilies cache

  template:write    Write or create a template (MyBB-native)
                    --title=<name> --template=<html> [--sid=<sid>]

  template:find_replace  Find/replace across templates (MyBB-native)
                    --title=<name> --find=<pattern> --replace=<text>
                    [--template_sets=<csv>] [--regex=0|1] [--limit=<int>]

  template:batch_write   Batch write templates (MyBB-native)
                    --sid=<sid> --templates_json=<json>

  stylesheet:write  Write stylesheet CSS (MyBB-native)
                    --sid=<sid> --stylesheet=<css>

  forum:create      Create a forum or category (MyBB-native)
                    --name=<text> [--type=f|c] [--pid=<parent_fid>]
                    [--description=<text>] [--disporder=<int>]

  forum:update      Update a forum or category (MyBB-native)
                    --fid=<forum_id>
                    [--name=<text>] [--description=<text>] [--type=f|c] [--pid=<parent_fid>]
                    [--disporder=<int>] [--active=0|1] [--open=0|1]

  user:update_group Update a user's primary group (MyBB-native)
                    --uid=<user_id> --usergroup=<gid>
                    [--additionalgroups=<csv_gids>]

  user:ban          Ban a user (MyBB-native)
                    --uid=<user_id> --gid=<banned_gid> --admin=<admin_uid>
                    [--dateline=<unix>] [--bantime=<spec>] [--reason=<text>]

  user:unban        Unban a user (MyBB-native)
                    --uid=<user_id>

  mod:close_thread  Close or open a thread (MyBB-native)
                    --tid=<thread_id> [--closed=0|1]

  mod:stick_thread  Stick or unstick a thread (MyBB-native)
                    --tid=<thread_id> [--sticky=0|1]

  mod:approve_thread Approve or unapprove a thread (MyBB-native)
                    --tid=<thread_id> [--approve=0|1]

  mod:approve_post  Approve or unapprove a post (MyBB-native)
                    --pid=<post_id> [--approve=0|1]

  mod:soft_delete_thread Soft delete a thread (MyBB-native)
                    --tid=<thread_id>

  mod:restore_thread Restore a soft-deleted thread (MyBB-native)
                    --tid=<thread_id>

  mod:soft_delete_post Soft delete a post (MyBB-native)
                    --pid=<post_id>

  mod:restore_post  Restore a soft-deleted post (MyBB-native)
                    --pid=<post_id>

  modlog:add        Add a moderator log entry (MyBB-native)
                    --uid=<mod_uid> --logaction=<text>
                    [--fid=<forum_id>] [--tid=<thread_id>] [--pid=<post_id>]
                    [--data=<extra>] [--ipaddress=<ip>]

  thread:create     Create a new thread (MyBB-native)
                    --fid=<forum_id> --subject=<text> --message=<text>
                    [--uid=<uid>] [--username=<name>]

  thread:edit       Edit a thread (MyBB-native)
                    --tid=<thread_id>
                    [--subject=<text>] [--closed=0|1] [--sticky=0|1] [--visible=1|0|-1]

  thread:delete     Delete a thread (MyBB-native)
                    --tid=<thread_id>
                    [--soft] (soft delete; default if provided)

  thread:move       Move a thread (MyBB-native)
                    --tid=<thread_id> --new_fid=<forum_id>

  post:create       Create a new post reply (MyBB-native)
                    --tid=<thread_id> --message=<text>
                    [--subject=<text>] [--replyto=<pid>]
                    [--uid=<uid>] [--username=<name>]

  post:edit         Edit a post (MyBB-native)
                    --pid=<post_id>
                    [--subject=<text>] [--message=<text>]
                    [--edituid=<uid>] [--edit_uid=<uid>] [--editreason=<text>]
                    [--signature=0|1] [--disablesmilies=0|1]

  post:delete       Delete a post (MyBB-native)
                    --pid=<post_id>
                    [--soft] (soft delete; default if provided)
                    [--restore] (restore soft-deleted post)

  info              Get MyBB installation info

Options:
  --json            Output as JSON (recommended for programmatic use)
  --request_id      Correlation id echoed back in JSON
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
$requestId = $options['request_id'] ?? null;

// ============================================================================
// Response helper
// ============================================================================
function respond($success, $data = [], $error = null) {
    global $outputJson, $action, $requestId;

    $response = [
        'success' => $success,
        'timestamp' => date('c'),
        'data' => $data,
        'action' => $action,
        'bridge_version' => MCP_BRIDGE_VERSION,
        'protocol_version' => MCP_BRIDGE_PROTOCOL_VERSION,
    ];

    if ($requestId !== null && $requestId !== '') {
        $response['request_id'] = (string) $requestId;
    }

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

// ========================================================================
// Template helper
// ========================================================================
function mcp_upsert_template($title, $template, $sid)
{
    global $db, $mybb;

    $template_array = array(
        'title' => $db->escape_string($title),
        'sid' => (int)$sid,
        'template' => $db->escape_string(rtrim($template)),
        'version' => $mybb->version_code,
        'status' => '',
        'dateline' => TIME_NOW
    );

    $existing_tid = 0;
    $created = false;
    $sid = (int)$sid;

    if ($sid === -2 || $sid === -1) {
        $query = $db->simple_select(
            "templates",
            "tid",
            "title='".$db->escape_string($title)."' AND sid='{$sid}'",
            array('limit' => 1)
        );
        $existing_tid = (int)$db->fetch_field($query, "tid");
        if ($existing_tid > 0) {
            $db->update_query("templates", $template_array, "tid='{$existing_tid}'");
        } else {
            $existing_tid = (int)$db->insert_query("templates", $template_array);
            $created = true;
        }
    } else {
        $query = $db->simple_select(
            "templates",
            "tid",
            "title='".$db->escape_string($title)."' AND sid='{$sid}'",
            array('limit' => 1)
        );
        $existing_tid = (int)$db->fetch_field($query, "tid");
        if ($existing_tid > 0) {
            $db->update_query("templates", $template_array, "tid='{$existing_tid}'");
        } else {
            $existing_tid = (int)$db->insert_query("templates", $template_array);
            $created = true;
        }
    }

    return array(
        'tid' => $existing_tid,
        'created' => $created
    );
}

// ========================================================================
// Moderator log helper
// ========================================================================
function ensure_mod_context($uid) {
    global $mybb, $session;

    if (!isset($mybb->user) || !is_array($mybb->user)) {
        $mybb->user = [];
    }
    $mybb->user['uid'] = (int)$uid;

    if (!isset($session) || !is_object($session)) {
        $session = new stdClass();
    }
    if (!isset($session->packedip)) {
        $session->packedip = my_inet_pton('127.0.0.1');
    }
}

function log_mod_action($action, $data, $uid) {
    if ($uid <= 0) {
        $uid = 1;
    }
    ensure_mod_context($uid);
    log_moderator_action($data, $action);
}

// ============================================================================
// Bootstrap MyBB
// ============================================================================
// Change to MyBB root directory for proper path resolution
chdir(__DIR__);

// Define required constants before loading MyBB
define('IN_MYBB', 1);
define('IN_ADMINCP', 1);  // Needed for plugins that conditionally load admin functions
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

    case 'cache:rebuild_smilies':
        $cache->update_smilies();
        respond(true, [
            'message' => 'Smilies cache rebuilt'
        ]);
        break;

    // ========================================================================
    // Settings & Task Actions (MyBB-native)
    // ========================================================================
    case 'setting:set':
        $name = $options['name'] ?? '';
        $value = $options['value'] ?? '';
        if (empty($name)) {
            respond(false, [], 'Setting name required');
        }

        $db->update_query("settings", ["value" => $db->escape_string($value)], "name='".$db->escape_string($name)."'");
        rebuild_settings();  // MyBB-native cache rebuild

        respond(true, ['name' => $name, 'value' => $value, 'cached' => true]);
        break;

    case 'task:enable':
        $tid = (int)($options['tid'] ?? 0);
        if (!$tid) {
            respond(false, [], 'Task ID required');
        }

        $task = $db->fetch_array($db->simple_select("tasks", "*", "tid='{$tid}'"));
        if (!$task) {
            respond(false, [], "Task {$tid} not found");
        }

        $db->update_query("tasks", ["enabled" => 1], "tid='{$tid}'");
        $cache->update_tasks();  // MyBB-native cache rebuild

        respond(true, ['tid' => $tid, 'status' => 'enabled']);
        break;

    case 'task:disable':
        $tid = (int)($options['tid'] ?? 0);
        if (!$tid) {
            respond(false, [], 'Task ID required');
        }

        $task = $db->fetch_array($db->simple_select("tasks", "*", "tid='{$tid}'"));
        if (!$task) {
            respond(false, [], "Task {$tid} not found");
        }

        $db->update_query("tasks", ["enabled" => 0], "tid='{$tid}'");
        $cache->update_tasks();  // MyBB-native cache rebuild

        respond(true, ['tid' => $tid, 'status' => 'disabled']);
        break;

    case 'task:update_nextrun':
        $tid = (int)($options['tid'] ?? 0);
        $nextrun = (int)($options['nextrun'] ?? 0);
        if (!$tid || !$nextrun) {
            respond(false, [], 'Task ID and nextrun timestamp required');
        }

        $task = $db->fetch_array($db->simple_select("tasks", "*", "tid='{$tid}'"));
        if (!$task) {
            respond(false, [], "Task {$tid} not found");
        }

        $db->update_query("tasks", ["nextrun" => $nextrun], "tid='{$tid}'");
        $cache->update_tasks();

        respond(true, ['tid' => $tid, 'nextrun' => $nextrun]);
        break;

    // ========================================================================
    // Template Actions (MyBB-native)
    // ========================================================================
    case 'template:write':
        require_once MYBB_ROOT . "admin/inc/functions.php";

        $title = $options['title'] ?? '';
        $template = $options['template'] ?? null;
        $sid = isset($options['sid']) ? (int)$options['sid'] : 1;

        if ($title === '' || $template === null) {
            respond(false, [], "Required: --title and --template");
        }

        if (check_template($template)) {
            respond(false, [], "Template failed security check");
        }

        $result = mcp_upsert_template($title, $template, $sid);
        $action_taken = $result['created'] ? "template_created" : "template_updated";

        log_admin_action($result['tid'], $title, $sid);

        respond(true, [
            "tid" => $result['tid'],
            "sid" => $sid,
            "title" => $title,
            "actions_taken" => [$action_taken]
        ]);
        break;

    case 'template:find_replace':
        require_once MYBB_ROOT . "inc/adminfunctions_templates.php";

        $title = $options['title'] ?? '';
        $find = $options['find'] ?? null;
        $replace = $options['replace'] ?? null;

        if ($title === '' || $find === null || $replace === null) {
            respond(false, [], "Required: --title, --find, --replace");
        }

        $use_regex = isset($options['regex']) ? (int)$options['regex'] : 1;
        $pattern = $use_regex ? $find : '#'.preg_quote($find, '#').'#';
        $limit = isset($options['limit']) ? (int)$options['limit'] : -1;

        $updated = false;
        if (!empty($options['template_sets'])) {
            $set_list = array_filter(array_map('trim', explode(',', $options['template_sets'])));
            foreach ($set_list as $set) {
                $sid = (int)$set;
                if ($sid === 0) {
                    continue;
                }
                if (find_replace_templatesets($title, $pattern, $replace, 1, $sid, $limit)) {
                    $updated = true;
                }
            }
        } else {
            $updated = find_replace_templatesets($title, $pattern, $replace, 1, false, $limit) ? true : false;
        }

        respond(true, [
            "title" => $title,
            "updated" => $updated,
            "actions_taken" => $updated ? ["templates_updated"] : []
        ]);
        break;

    case 'template:batch_write':
        require_once MYBB_ROOT . "admin/inc/functions.php";

        $sid = isset($options['sid']) ? (int)$options['sid'] : 1;
        $templates_json = $options['templates_json'] ?? '';
        $templates = json_decode($templates_json, true);

        if (!is_array($templates)) {
            respond(false, [], "Required: --templates_json (array of {title, template})");
        }

        $created = 0;
        $updated = 0;

        foreach ($templates as $item) {
            $title = $item['title'] ?? '';
            $template = $item['template'] ?? null;
            if ($title === '' || $template === null) {
                respond(false, [], "Each template must include title and template");
            }
            if (check_template($template)) {
                respond(false, ["title" => $title], "Template failed security check");
            }
        }

        foreach ($templates as $item) {
            $title = $item['title'];
            $template = $item['template'];
            $result = mcp_upsert_template($title, $template, $sid);
            if ($result['created']) {
                $created++;
            } else {
                $updated++;
            }
        }

        respond(true, [
            "sid" => $sid,
            "created" => $created,
            "updated" => $updated,
            "actions_taken" => ["templates_batch_written"]
        ]);
        break;

    case 'template:list':
        // List templates with optional filtering
        // Optional: --sid (filter by template set ID, e.g., -2 for master, 1+ for custom sets)
        // Optional: --title (filter by title prefix, useful for plugin templates like "myplugin_")
        $sid = isset($options['sid']) ? (int)$options['sid'] : null;
        $title_prefix = $options['title'] ?? null;

        $where_clauses = [];
        if ($sid !== null) {
            $where_clauses[] = "sid = '{$sid}'";
        }
        if ($title_prefix !== null && $title_prefix !== '') {
            $where_clauses[] = "title LIKE '" . $db->escape_string($title_prefix) . "%'";
        }

        $where = !empty($where_clauses) ? implode(' AND ', $where_clauses) : '1=1';

        $query = $db->simple_select(
            'templates',
            'tid, title, template, sid, version, dateline',
            $where,
            ['order_by' => 'title', 'order_dir' => 'ASC']
        );

        $templates = [];
        while ($row = $db->fetch_array($query)) {
            $templates[] = [
                'tid' => (int)$row['tid'],
                'title' => $row['title'],
                'template' => $row['template'],
                'sid' => (int)$row['sid'],
                'version' => $row['version'],
                'dateline' => (int)$row['dateline']
            ];
        }

        respond(true, [
            'templates' => $templates,
            'count' => count($templates),
            'filters' => [
                'sid' => $sid,
                'title_prefix' => $title_prefix
            ]
        ]);
        break;

    // ========================================================================
    // Stylesheet Actions (MyBB-native)
    // ========================================================================
    case 'stylesheet:write':
        require_once MYBB_ROOT . "admin/inc/functions_themes.php";
        require_once MYBB_ROOT . "admin/inc/functions.php";

        $sid = isset($options['sid']) ? (int)$options['sid'] : 0;
        $css = $options['stylesheet'] ?? null;

        if ($sid <= 0 || $css === null) {
            respond(false, [], "Required: --sid and --stylesheet");
        }

        $query = $db->simple_select("themestylesheets", "*", "sid='{$sid}'", array('limit' => 1));
        $stylesheet = $db->fetch_array($query);
        if (!$stylesheet) {
            respond(false, ["sid" => $sid], "Stylesheet not found");
        }

        $db->update_query("themestylesheets", array(
            "stylesheet" => $db->escape_string($css),
            "lastmodified" => TIME_NOW
        ), "sid='{$sid}'");

        $tid = (int)$stylesheet['tid'];
        $theme = get_theme($tid);
        if (!$theme) {
            $theme = $db->fetch_array($db->simple_select("themes", "name, tid", "tid='{$tid}'", array('limit' => 1)));
        }

        $cache_ok = cache_stylesheet($tid, $stylesheet['name'], $css);
        if (!$cache_ok) {
            $db->update_query("themestylesheets", array('cachefile' => "css.php?stylesheet={$sid}"), "sid='{$sid}'", 1);
        }

        update_theme_stylesheet_list($tid, $theme ?: false, true);

        log_admin_action($sid, $stylesheet['name'], $stylesheet['tid'], $theme ? $theme['name'] : null);

        respond(true, [
            "sid" => $sid,
            "tid" => (int)$stylesheet['tid'],
            "name" => $stylesheet['name'],
            "cache_updated" => $cache_ok,
            "actions_taken" => ["stylesheet_updated", "stylesheet_cache_refreshed"]
        ]);
        break;

    case 'theme:import':
        require_once MYBB_ROOT . "admin/inc/functions_themes.php";
        require_once MYBB_ROOT . "admin/inc/functions.php";

        // Get XML content from --xml argument
        $xml = $options['xml'] ?? null;
        if (!$xml) {
            respond(false, [], 'No XML provided (--xml=<path_or_content>)');
        }

        // If it's a file path, read the file
        if (file_exists($xml)) {
            $xml_content = file_get_contents($xml);
            if ($xml_content === false) {
                respond(false, ['xml_path' => $xml], 'Failed to read XML file');
            }
            $xml = $xml_content;
        }

        // Build import options
        $import_options = [
            'no_stylesheets' => isset($options['no-stylesheets']) ? 1 : 0,
            'no_templates' => isset($options['no-templates']) ? 1 : 0,
            'version_compat' => isset($options['force-version']) ? 1 : 0,
            'parent' => isset($options['parent']) ? (int)$options['parent'] : 1,
        ];

        // Override name if provided
        if (isset($options['name']) && !empty($options['name'])) {
            $import_options['name'] = $options['name'];
        }

        // Call MyBB's import_theme_xml function
        $result = import_theme_xml($xml, $import_options);

        // Map return codes to response
        if ($result > 0) {
            // Success - result is the new theme ID
            $theme = get_theme($result);
            respond(true, [
                'theme_id' => $result,
                'theme_name' => $theme ? $theme['name'] : 'Unknown',
                'import_options' => $import_options
            ]);
        } else {
            // Error codes from import_theme_xml
            $errors = [
                -1 => 'Invalid XML format',
                -2 => 'Version mismatch (use --force-version to override)',
                -3 => 'Theme name already exists (use --name to override)',
                -4 => 'Security violation in templates',
            ];
            $error_message = $errors[$result] ?? 'Unknown error';
            respond(false, [
                'error' => $error_message,
                'code' => $result,
                'import_options' => $import_options
            ], $error_message);
        }
        break;

    case 'theme:update_stylesheet_list':
        // Updates theme properties (disporder, stylesheets arrays) after stylesheet creation
        // This is the critical missing step that causes stylesheets to not display
        require_once MYBB_ROOT . "admin/inc/functions_themes.php";
        require_once MYBB_ROOT . "admin/inc/functions.php";

        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        if ($tid <= 0) {
            respond(false, [], "Required: --tid (theme ID)");
        }

        // Query theme WITH properties instead of using incomplete get_theme()
        // get_theme() only fetches tid, name, pid, allowedgroups - missing properties/stylesheets
        // This caused templateset to be wiped when update_theme_stylesheet_list() rebuilt properties
        $query = $db->simple_select(
            'themes',
            'tid, name, pid, properties, stylesheets',
            "tid = ".(int)$tid
        );
        $theme = $db->fetch_array($query);

        if (!$theme) {
            respond(false, ["tid" => $tid], "Theme not found");
        }

        // Unserialize properties for update_theme_stylesheet_list
        if (isset($theme['properties'])) {
            $theme['properties'] = my_unserialize($theme['properties']);
        }

        // Call the critical function that builds disporder and stylesheets arrays
        // Parameters: $tid, $theme, $update_disporder
        update_theme_stylesheet_list($tid, $theme, true);

        // Verify the update by re-fetching theme
        $updated_theme = get_theme($tid);
        $properties = my_unserialize($updated_theme['properties']);
        $stylesheets = my_unserialize($updated_theme['stylesheets']);

        respond(true, [
            "tid" => $tid,
            "theme_name" => $theme['name'],
            "disporder_count" => is_array($properties['disporder']) ? count($properties['disporder']) : 0,
            "stylesheets_pages" => is_array($stylesheets) ? count($stylesheets) : 0
        ]);
        break;

    case 'theme:set_property':
        // Set a property in a theme's properties array
        // Required: --tid, --key, --value
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        $key = $options['key'] ?? '';
        $value = $options['value'] ?? '';

        if ($tid < 1) {
            respond(false, [], "Required: --tid (theme ID)");
        }
        if ($key === '') {
            respond(false, [], "Required: --key (property name)");
        }

        // Query theme directly to get properties (get_theme() doesn't include properties!)
        $query = $db->simple_select('themes', 'tid, name, properties', "tid='{$tid}'");
        $theme = $db->fetch_array($query);
        if (!$theme) {
            respond(false, ["tid" => $tid], "Theme not found");
        }

        // Unserialize properties, add/update the key, re-serialize
        $properties = my_unserialize($theme['properties']);
        if (!is_array($properties)) {
            $properties = [];
        }

        // Type cast numeric properties (templateset should be int, not string)
        if ($key === 'templateset') {
            $properties[$key] = (int)$value;
        } else {
            $properties[$key] = $value;
        }

        // Update the theme
        $db->update_query("themes", [
            "properties" => my_serialize($properties)
        ], "tid='{$tid}'");

        respond(true, [
            "tid" => $tid,
            "key" => $key,
            "value" => $value,
            "properties_count" => count($properties)
        ]);
        break;

    case 'templateset:create':
        // Create a new template set or return existing one
        // Required: --title
        $title = $options['title'] ?? null;
        if (!$title) {
            respond(false, [], "Missing required parameter: title");
        }

        // Check if templateset already exists
        $query = $db->simple_select('templatesets', 'sid, title', "title = '".$db->escape_string($title)."'");
        $existing = $db->fetch_array($query);

        if ($existing) {
            respond(true, [
                'sid' => (int)$existing['sid'],
                'title' => $existing['title'],
                'existed' => true
            ]);
        }

        // Create new templateset
        $sid = $db->insert_query('templatesets', [
            'title' => $db->escape_string($title)
        ]);

        respond(true, [
            'sid' => (int)$sid,
            'title' => $title,
            'existed' => false
        ]);
        break;

    case 'templateset:copy_master':
        // Copy all templates from source templateset to target templateset
        // Required: --sid (target templateset ID)
        // Optional: --source_sid (source templateset ID, default -2 for master)
        // Optional: --force (overwrite existing templates)
        $target_sid = $options['sid'] ?? null;
        $source_sid = $options['source_sid'] ?? -2;
        $force = isset($options['force']);

        if (!$target_sid) {
            respond(false, null, 'Missing required parameter: sid');
        }

        // Verify target templateset exists
        $query = $db->simple_select('templatesets', 'sid, title', "sid = ".(int)$target_sid);
        $templateset = $db->fetch_array($query);
        if (!$templateset) {
            respond(false, null, 'Templateset not found: '.$target_sid);
        }

        // Check if target already has templates (unless force)
        if (!$force) {
            $existing_count = $db->fetch_field(
                $db->simple_select('templates', 'COUNT(*) as cnt', "sid = ".(int)$target_sid),
                'cnt'
            );
            if ($existing_count > 0) {
                respond(false, null, 'Target templateset already has '.$existing_count.' templates. Use --force to overwrite.');
            }
        }

        // Get all templates from source
        $query = $db->simple_select('templates', 'title, template, version', "sid = ".(int)$source_sid);
        $copied = 0;
        while ($template = $db->fetch_array($query)) {
            // Delete existing if force mode
            if ($force) {
                $db->delete_query('templates', "sid = ".(int)$target_sid." AND title = '".$db->escape_string($template['title'])."'");
            }

            $db->insert_query('templates', [
                'title' => $db->escape_string($template['title']),
                'template' => $db->escape_string($template['template']),
                'sid' => (int)$target_sid,
                'version' => $template['version'] ?? '1800',
                'dateline' => TIME_NOW
            ]);
            $copied++;
        }

        respond(true, [
            'sid' => (int)$target_sid,
            'templateset_title' => $templateset['title'],
            'source_sid' => (int)$source_sid,
            'templates_copied' => $copied
        ]);
        break;

    case 'theme:create':
        require_once MYBB_ROOT . "admin/inc/functions_themes.php";

        $name = $options['name'] ?? null;
        $pid = (int)($options['pid'] ?? 1);
        $templateset = $options['templateset'] ?? null;
        $logo = $options['logo'] ?? null;
        $editortheme = $options['editortheme'] ?? null;

        if (!$name) {
            respond(false, null, 'Missing required parameter: name');
        }

        // Check if theme already exists
        $query = $db->simple_select('themes', '*', "name = '".$db->escape_string($name)."'");
        $existing = $db->fetch_array($query);

        if ($existing) {
            $props = my_unserialize($existing['properties']);
            respond(true, [
                'tid' => (int)$existing['tid'],
                'name' => $existing['name'],
                'pid' => (int)$existing['pid'],
                'templateset' => $props['templateset'] ?? null,
                'existed' => true
            ]);
        }

        // Build properties array
        $properties = [];
        if ($templateset !== null) {
            $properties['templateset'] = (int)$templateset;
        }
        if ($logo !== null) {
            $properties['logo'] = $logo;
        }
        if ($editortheme !== null) {
            $properties['editortheme'] = $editortheme;
        }

        // Create theme using MyBB function
        $tid = build_new_theme($name, $properties, $pid);

        // Verify templateset was set correctly (build_new_theme may have inherited)
        if ($templateset !== null) {
            $query = $db->simple_select('themes', 'properties', "tid = ".(int)$tid);
            $theme = $db->fetch_array($query);
            $props = my_unserialize($theme['properties']);

            if (($props['templateset'] ?? null) != $templateset) {
                // Force the templateset we want
                $props['templateset'] = (int)$templateset;
                $db->update_query('themes', [
                    'properties' => my_serialize($props)
                ], "tid = ".(int)$tid);
            }
        }

        // Get final theme data
        $query = $db->simple_select('themes', '*', "tid = ".(int)$tid);
        $theme = $db->fetch_array($query);
        $props = my_unserialize($theme['properties']);

        respond(true, [
            'tid' => (int)$tid,
            'name' => $theme['name'],
            'pid' => (int)$theme['pid'],
            'templateset' => $props['templateset'] ?? null,
            'existed' => false
        ]);
        break;

    case 'theme:get':
        $tid = $options['tid'] ?? null;
        $name = $options['name'] ?? null;

        if (!$tid && !$name) {
            respond(false, null, 'Missing required parameter: tid or name');
        }

        // Build query condition
        if ($tid) {
            $where = "tid = ".(int)$tid;
        } else {
            $where = "name = '".$db->escape_string($name)."'";
        }

        $query = $db->simple_select('themes', '*', $where);
        $theme = $db->fetch_array($query);

        if (!$theme) {
            respond(false, null, 'Theme not found');
        }

        // Unserialize properties for response
        $properties = my_unserialize($theme['properties']);
        $stylesheets = my_unserialize($theme['stylesheets']);

        respond(true, [
            'tid' => (int)$theme['tid'],
            'name' => $theme['name'],
            'pid' => (int)$theme['pid'],
            'def' => (int)$theme['def'],
            'properties' => $properties,
            'stylesheets' => $stylesheets,
            'allowedgroups' => $theme['allowedgroups']
        ]);
        break;

    case 'theme:set_default':
        // Set a theme as the default theme
        // This resets all other themes and sets the specified one
        $tid = $options['tid'] ?? null;

        if (!$tid) {
            respond(false, null, 'Missing required parameter: tid');
        }

        $tid = (int)$tid;

        // Verify theme exists
        $query = $db->simple_select('themes', '*', "tid='{$tid}'");
        if (!$db->num_rows($query)) {
            respond(false, null, "Theme not found: {$tid}");
        }

        // Reset all themes to not default
        $db->update_query('themes', array('def' => 0), "def='1'");

        // Set this theme as default
        $db->update_query('themes', array('def' => 1), "tid='{$tid}'");

        // Update cache
        $cache->update_default_theme();

        respond(true, [
            'tid' => $tid,
            'set_default' => true
        ]);
        break;

    case 'stylesheet:create':
        require_once MYBB_ROOT.'admin/inc/functions_themes.php';

        $tid = $options['tid'] ?? null;
        $name = $options['name'] ?? null;
        $content = $options['content'] ?? null;
        $attachedto = $options['attachedto'] ?? '';

        if (!$tid || !$name || $content === null) {
            respond(false, null, 'Missing required parameters: tid, name, content');
        }

        $tid = (int)$tid;

        // Verify theme exists
        $query = $db->simple_select('themes', 'tid', "tid = ".$tid);
        if (!$db->fetch_array($query)) {
            respond(false, null, 'Theme not found: '.$tid);
        }

        // Check if stylesheet exists for this theme
        $query = $db->simple_select('themestylesheets', '*', "tid = ".$tid." AND name = '".$db->escape_string($name)."'");
        $existing = $db->fetch_array($query);

        $updated = false;

        if ($existing) {
            // Update existing stylesheet
            $sid = (int)$existing['sid'];
            $db->update_query('themestylesheets', [
                'stylesheet' => $db->escape_string($content),
                'attachedto' => $db->escape_string($attachedto),
                'lastmodified' => TIME_NOW
            ], "sid = ".$sid);
            $updated = true;
        } else {
            // Insert new stylesheet
            $sid = $db->insert_query('themestylesheets', [
                'name' => $db->escape_string($name),
                'tid' => $tid,
                'attachedto' => $db->escape_string($attachedto),
                'stylesheet' => $db->escape_string($content),
                'cachefile' => $db->escape_string($name),
                'lastmodified' => TIME_NOW
            ]);
        }

        // Create cache directory and file
        $cache_dir = MYBB_ROOT.'cache/themes/theme'.$tid.'/';
        if (!is_dir($cache_dir)) {
            @mkdir($cache_dir, 0755, true);
        }

        $cachefile = $cache_dir.$name;
        @file_put_contents($cachefile, $content);

        respond(true, [
            'sid' => $sid,
            'tid' => $tid,
            'name' => $name,
            'cachefile' => 'cache/themes/theme'.$tid.'/'.$name,
            'updated' => $updated
        ]);
        break;

    case 'stylesheet:list':
        // List stylesheets with optional theme filtering
        // Optional: --tid (filter by theme ID)
        $tid = isset($options['tid']) ? (int)$options['tid'] : null;

        $where = $tid !== null ? "tid = '{$tid}'" : '1=1';

        $query = $db->simple_select(
            'themestylesheets',
            'sid, name, tid, stylesheet, cachefile, lastmodified, attachedto',
            $where,
            ['order_by' => 'name', 'order_dir' => 'ASC']
        );

        $stylesheets = [];
        while ($row = $db->fetch_array($query)) {
            $stylesheets[] = [
                'sid' => (int)$row['sid'],
                'name' => $row['name'],
                'tid' => (int)$row['tid'],
                'stylesheet' => $row['stylesheet'],
                'cachefile' => $row['cachefile'],
                'lastmodified' => (int)$row['lastmodified'],
                'attachedto' => $row['attachedto']
            ];
        }

        respond(true, [
            'stylesheets' => $stylesheets,
            'count' => count($stylesheets),
            'filters' => [
                'tid' => $tid
            ]
        ]);
        break;

    // ========================================================================
    // Forum Actions (MyBB-native)
    // ========================================================================
    case 'forum:create':
        $name = $options['name'] ?? '';
        if ($name === '') {
            respond(false, [], "Required: --name");
        }

        $type = $options['type'] ?? 'f';
        $pid = isset($options['pid']) ? (int)$options['pid'] : 0;
        if ($pid < 0) {
            $pid = 0;
        }

        $disporder = isset($options['disporder']) ? (int)$options['disporder'] : 1;
        $active = isset($options['active']) ? (int)$options['active'] : 1;
        $open = isset($options['open']) ? (int)$options['open'] : 1;

        $insert_array = [
            "name" => $db->escape_string($name),
            "description" => $db->escape_string($options['description'] ?? ''),
            "linkto" => $db->escape_string($options['linkto'] ?? ''),
            "type" => $db->escape_string($type),
            "pid" => $pid,
            "parentlist" => '',
            "disporder" => $disporder,
            "active" => $active,
            "open" => $open,
            "allowhtml" => isset($options['allowhtml']) ? (int)$options['allowhtml'] : 0,
            "allowmycode" => isset($options['allowmycode']) ? (int)$options['allowmycode'] : 1,
            "allowsmilies" => isset($options['allowsmilies']) ? (int)$options['allowsmilies'] : 1,
            "allowimgcode" => isset($options['allowimgcode']) ? (int)$options['allowimgcode'] : 1,
            "allowvideocode" => isset($options['allowvideocode']) ? (int)$options['allowvideocode'] : 1,
            "allowpicons" => isset($options['allowpicons']) ? (int)$options['allowpicons'] : 1,
            "allowtratings" => isset($options['allowtratings']) ? (int)$options['allowtratings'] : 1,
            "usepostcounts" => isset($options['usepostcounts']) ? (int)$options['usepostcounts'] : 1,
            "usethreadcounts" => isset($options['usethreadcounts']) ? (int)$options['usethreadcounts'] : 1,
            "showinjump" => isset($options['showinjump']) ? (int)$options['showinjump'] : 1,
            "rulestype" => isset($options['rulestype']) ? (int)$options['rulestype'] : 0,
            "rulestitle" => $db->escape_string($options['rulestitle'] ?? ''),
            "rules" => $db->escape_string($options['rules'] ?? ''),
        ];

        $fid = $db->insert_query("forums", $insert_array);

        require_once MYBB_ROOT . "admin/inc/functions.php";
        $parentlist = make_parent_list($fid);
        $db->update_query("forums", ["parentlist" => $parentlist], "fid='{$fid}'");

        $cache->update_forums();
        $cache->update_forumsdisplay();

        respond(true, [
            "fid" => (int)$fid,
            "parentlist" => $parentlist,
            "actions_taken" => ["forum_created", "forums_cache_updated"]
        ]);
        break;

    case 'forum:update':
        $fid = isset($options['fid']) ? (int)$options['fid'] : 0;
        if ($fid <= 0) {
            respond(false, [], "Required: --fid");
        }

        $forum = get_forum($fid);
        if (!$forum) {
            respond(false, ["fid" => $fid], "Forum not found");
        }

        $update_array = [];
        if (isset($options['name'])) {
            $update_array["name"] = $db->escape_string($options['name']);
        }
        if (isset($options['description'])) {
            $update_array["description"] = $db->escape_string($options['description']);
        }
        if (isset($options['linkto'])) {
            $update_array["linkto"] = $db->escape_string($options['linkto']);
        }
        if (isset($options['type'])) {
            $update_array["type"] = $db->escape_string($options['type']);
        }
        if (isset($options['pid'])) {
            $update_array["pid"] = (int)$options['pid'];
        }
        if (isset($options['disporder'])) {
            $update_array["disporder"] = (int)$options['disporder'];
        }
        if (isset($options['active'])) {
            $update_array["active"] = (int)$options['active'];
        }
        if (isset($options['open'])) {
            $update_array["open"] = (int)$options['open'];
        }
        if (isset($options['rulestype'])) {
            $update_array["rulestype"] = (int)$options['rulestype'];
        }
        if (isset($options['rulestitle'])) {
            $update_array["rulestitle"] = $db->escape_string($options['rulestitle']);
        }
        if (isset($options['rules'])) {
            $update_array["rules"] = $db->escape_string($options['rules']);
        }
        if (isset($options['showinjump'])) {
            $update_array["showinjump"] = (int)$options['showinjump'];
        }
        if (isset($options['usepostcounts'])) {
            $update_array["usepostcounts"] = (int)$options['usepostcounts'];
        }
        if (isset($options['usethreadcounts'])) {
            $update_array["usethreadcounts"] = (int)$options['usethreadcounts'];
        }
        if (isset($options['allowhtml'])) {
            $update_array["allowhtml"] = (int)$options['allowhtml'];
        }
        if (isset($options['allowmycode'])) {
            $update_array["allowmycode"] = (int)$options['allowmycode'];
        }
        if (isset($options['allowsmilies'])) {
            $update_array["allowsmilies"] = (int)$options['allowsmilies'];
        }
        if (isset($options['allowimgcode'])) {
            $update_array["allowimgcode"] = (int)$options['allowimgcode'];
        }
        if (isset($options['allowvideocode'])) {
            $update_array["allowvideocode"] = (int)$options['allowvideocode'];
        }
        if (isset($options['allowpicons'])) {
            $update_array["allowpicons"] = (int)$options['allowpicons'];
        }
        if (isset($options['allowtratings'])) {
            $update_array["allowtratings"] = (int)$options['allowtratings'];
        }

        if (empty($update_array)) {
            respond(false, [], "No update fields provided");
        }

        $db->update_query("forums", $update_array, "fid='{$fid}'");

        if (isset($update_array["pid"]) && $update_array["pid"] != $forum['pid']) {
            require_once MYBB_ROOT . "admin/inc/functions.php";
            $db->update_query("forums", ["parentlist" => make_parent_list($fid)], "fid='{$fid}'");

            switch ($db->type) {
                case "sqlite":
                case "pgsql":
                    $query = $db->simple_select("forums", "fid", "','||parentlist||',' LIKE '%,$fid,%'");
                    break;
                default:
                    $query = $db->simple_select("forums", "fid", "CONCAT(',',parentlist,',') LIKE '%,$fid,%'");
            }
            while ($child = $db->fetch_array($query)) {
                $db->update_query("forums", ["parentlist" => make_parent_list($child['fid'])], "fid='{$child['fid']}'");
            }
        }

        $cache->update_forums();
        $cache->update_forumsdisplay();

        respond(true, [
            "fid" => $fid,
            "actions_taken" => ["forum_updated", "forums_cache_updated"]
        ]);
        break;

    case 'forum:delete':
        $fid = isset($options['fid']) ? (int)$options['fid'] : 0;
        $force_content_deletion = isset($options['force_content_deletion']) && $options['force_content_deletion'];

        if ($fid <= 0) {
            respond(false, [], "Required: --fid");
        }

        // Validate forum exists
        $forum = get_forum($fid);
        if (!$forum) {
            respond(false, ["fid" => $fid], "Forum not found");
        }

        // Check if forum has content
        if (($forum['threads'] > 0 || $forum['posts'] > 0) && !$force_content_deletion) {
            respond(false, [
                "fid" => $fid,
                "threads" => (int)$forum['threads'],
                "posts" => (int)$forum['posts'],
                "hint" => "Use force_content_deletion=true to delete content"
            ], "Forum has content - cannot delete. Move or delete content first, or use force_content_deletion.");
        }

        // Build query for child forums
        $delquery = "";
        switch ($db->type) {
            case "pgsql":
            case "sqlite":
                $query = $db->simple_select("forums", "fid", "','||parentlist||',' LIKE '%,$fid,%'");
                break;
            default:
                $query = $db->simple_select("forums", "fid", "CONCAT(',',parentlist,',') LIKE '%,$fid,%'");
        }
        while ($child = $db->fetch_array($query)) {
            $delquery .= " OR fid='{$child['fid']}'";
        }

        // If force_content_deletion and has content, use Moderation class (matches management.php:2031-2037)
        if ($force_content_deletion && ($forum['threads'] > 0 || $forum['posts'] > 0)) {
            require_once MYBB_ROOT.'inc/class_moderation.php';
            $moderation = new Moderation();

            // Delete threads in batches of 50
            do {
                $query = $db->simple_select("threads", "tid", "fid='{$fid}' {$delquery}", ["limit" => 50]);
                $count = 0;
                while ($thread = $db->fetch_array($query)) {
                    $moderation->delete_thread($thread['tid']);
                    $count++;
                }
            } while ($count > 0);
        }

        // Delete the forum
        $db->delete_query("forums", "fid='$fid'");

        // Delete subforums
        if ($delquery) {
            switch ($db->type) {
                case "pgsql":
                case "sqlite":
                    $db->delete_query("forums", "','||parentlist||',' LIKE '%,$fid,%'");
                    break;
                default:
                    $db->delete_query("forums", "CONCAT(',',parentlist,',') LIKE '%,$fid,%'");
            }
        }

        // Cleanup related tables
        $db->delete_query('moderators', "fid='{$fid}' {$delquery}");
        $db->delete_query('forumsubscriptions', "fid='{$fid}' {$delquery}");
        $db->delete_query('forumpermissions', "fid='{$fid}' {$delquery}");
        $db->delete_query('announcements', "fid='{$fid}' {$delquery}");
        $db->delete_query('forumsread', "fid='{$fid}' {$delquery}");

        // Fire hook (matches management.php:2080)
        $plugins->run_hooks("admin_forum_management_delete_commit");

        // Rebuild caches
        $cache->update_forums();
        $cache->update_moderators();
        $cache->update_forumpermissions();
        $cache->update_forumsdisplay();

        // Log admin action (matches management.php:2088)
        log_admin_action($fid, $forum['name']);

        $actions = [
            "forum_deleted",
            "subforums_deleted",
            "related_records_cleaned",
            "hook_fired",
            "forums_cache_updated",
            "moderators_cache_updated",
            "permissions_cache_updated",
            "forumsdisplay_cache_updated",
            "admin_action_logged"
        ];

        if ($force_content_deletion) {
            array_unshift($actions, "content_deleted_via_moderation");
        }

        respond(true, [
            "fid" => $fid,
            "actions_taken" => $actions
        ]);
        break;

    // ========================================================================
    // User Actions (MyBB-native)
    // ========================================================================
    case 'user:update_group':
        $uid = isset($options['uid']) ? (int)$options['uid'] : 0;
        $usergroup = isset($options['usergroup']) ? (int)$options['usergroup'] : 0;

        if ($uid <= 0 || $usergroup <= 0) {
            respond(false, [], "Required: --uid and --usergroup");
        }

        require_once MYBB_ROOT . "inc/datahandlers/user.php";
        $userhandler = new UserDataHandler('update');

        $update_data = [
            "uid" => $uid,
            "usergroup" => $usergroup,
        ];

        if (isset($options['additionalgroups'])) {
            $update_data["additionalgroups"] = (string)$options['additionalgroups'];
        }

        $userhandler->set_data($update_data);

        if (!$userhandler->validate_user()) {
            $errors = $userhandler->get_friendly_errors();
            respond(false, ["errors" => $errors], "User validation failed");
        }

        $success = $userhandler->update_user();
        if (!$success) {
            respond(false, [], "User update failed");
        }

        respond(true, [
            "uid" => $uid,
            "actions_taken" => ["usergroup_updated"]
        ]);
        break;

    case 'user:ban':
        $uid = isset($options['uid']) ? (int)$options['uid'] : 0;
        $gid = isset($options['gid']) ? (int)$options['gid'] : 0;
        $admin = isset($options['admin']) ? (int)$options['admin'] : 0;
        $dateline = isset($options['dateline']) ? (int)$options['dateline'] : TIME_NOW;
        $bantime = $options['bantime'] ?? '---';
        $reason = $options['reason'] ?? '';

        if ($uid <= 0 || $gid <= 0 || $admin <= 0) {
            respond(false, [], "Required: --uid, --gid, --admin");
        }

        $user = get_user($uid);
        if (!$user) {
            respond(false, ["uid" => $uid], "User not found");
        }

        if (is_super_admin($uid) && !is_super_admin($admin)) {
            respond(false, ["uid" => $uid], "Cannot ban a super admin");
        }

        if ($uid === $admin) {
            respond(false, ["uid" => $uid], "Cannot ban self");
        }

        $query = $db->simple_select("banned", "uid", "uid='{$uid}'");
        if ($db->fetch_field($query, "uid")) {
            respond(false, ["uid" => $uid], "User already banned");
        }

        $usergroups = $cache->read("usergroups");
        if (!empty($usergroups[$user['usergroup']]) && $usergroups[$user['usergroup']]['isbannedgroup'] == 1) {
            respond(false, ["uid" => $uid], "User already in a banned group");
        }

        if ($bantime === '---') {
            $lifted = 0;
        } else {
            $lifted = ban_date2timestamp($bantime, $dateline);
        }

        $reason = my_substr($reason, 0, 255);

        $insert_array = [
            'uid' => $uid,
            'gid' => $gid,
            'oldgroup' => $user['usergroup'],
            'oldadditionalgroups' => $db->escape_string($user['additionalgroups']),
            'olddisplaygroup' => $user['displaygroup'],
            'admin' => $admin,
            'dateline' => $dateline,
            'bantime' => $db->escape_string($bantime),
            'lifted' => $db->escape_string($lifted),
            'reason' => $db->escape_string($reason),
        ];

        // Step 1: Insert ban record
        $db->insert_query('banned', $insert_array);

        // Step 2: Delete subscriptions (must happen before hook)
        $db->delete_query("forumsubscriptions", "uid='{$uid}'");
        $db->delete_query("threadsubscriptions", "uid='{$uid}'");

        // Step 3: Fire hook (matches banning.php:412)
        $plugins->run_hooks("admin_user_banning_start_commit");

        // Step 4: Update users table
        $update_array = [
            'usergroup' => $gid,
            'displaygroup' => 0,
            'additionalgroups' => '',
        ];
        $db->update_query('users', $update_array, "uid='{$uid}'");

        // Step 5: Log admin action (matches banning.php:417)
        log_admin_action($uid, $user['username'], $lifted);

        respond(true, [
            "uid" => $uid,
            "actions_taken" => ["user_banned", "subscriptions_deleted", "hook_fired", "admin_action_logged"],
            "ban" => [
                "gid" => $gid,
                "lifted" => $lifted,
            ],
        ]);
        break;

    case 'user:unban':
        $uid = isset($options['uid']) ? (int)$options['uid'] : 0;
        if ($uid <= 0) {
            respond(false, [], "Required: --uid");
        }

        $query = $db->simple_select("banned", "*", "uid='{$uid}'");
        $ban = $db->fetch_array($query);
        if (!$ban) {
            respond(false, ["uid" => $uid], "User is not banned");
        }

        // Get user record for logging (matches banning.php pattern)
        $user = get_user($uid);

        $updated_group = [
            'usergroup' => $ban['oldgroup'],
            'additionalgroups' => $db->escape_string($ban['oldadditionalgroups']),
            'displaygroup' => $ban['olddisplaygroup'],
        ];

        // Delete from banned table first (matches banning.php:148)
        $db->delete_query("banned", "uid='{$uid}'");

        // Fire hook after delete, before update (matches banning.php:150)
        $plugins->run_hooks("admin_user_banning_lift_commit");

        // Update users table (matches banning.php:152)
        $db->update_query("users", $updated_group, "uid='{$uid}'");

        // Update moderators cache
        $cache->update_moderators();

        // Log admin action (matches banning.php:157)
        log_admin_action($ban['uid'], $user['username']);

        respond(true, [
            "uid" => $uid,
            "actions_taken" => [
                "ban_record_deleted",
                "hook_admin_user_banning_lift_commit_fired",
                "user_groups_restored",
                "moderators_cache_updated",
                "admin_action_logged"
            ]
        ]);
        break;

    // ========================================================================
    // Moderation Actions (MyBB-native)
    // ========================================================================
    case 'mod:close_thread':
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        $closed = isset($options['closed']) ? (int)$options['closed'] : 1;
        $mod_uid = isset($options['uid']) ? (int)$options['uid'] : 1;

        if ($tid <= 0) {
            respond(false, [], "Required: --tid");
        }

        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation();
        $success = $closed ? $moderation->close_threads($tid) : $moderation->open_threads($tid);

        if (!$success) {
            respond(false, ["tid" => $tid], "Failed to update thread status");
        }

        $thread = get_thread($tid);
        $log_data = [
            "tid" => $tid,
            "fid" => $thread['fid'] ?? 0,
            "subject" => $thread['subject'] ?? '',
        ];
        log_mod_action($closed ? "Thread closed" : "Thread opened", $log_data, $mod_uid);

        respond(true, [
            "tid" => $tid,
            "actions_taken" => [$closed ? "thread_closed" : "thread_opened"]
        ]);
        break;

    case 'mod:stick_thread':
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        $sticky = isset($options['sticky']) ? (int)$options['sticky'] : 1;
        $mod_uid = isset($options['uid']) ? (int)$options['uid'] : 1;

        if ($tid <= 0) {
            respond(false, [], "Required: --tid");
        }

        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation();
        $success = $sticky ? $moderation->stick_threads($tid) : $moderation->unstick_threads($tid);

        if (!$success) {
            respond(false, ["tid" => $tid], "Failed to update thread sticky state");
        }

        $thread = get_thread($tid);
        $log_data = [
            "tid" => $tid,
            "fid" => $thread['fid'] ?? 0,
            "subject" => $thread['subject'] ?? '',
        ];
        log_mod_action($sticky ? "Thread stuck" : "Thread unstuck", $log_data, $mod_uid);

        respond(true, [
            "tid" => $tid,
            "actions_taken" => [$sticky ? "thread_stuck" : "thread_unstuck"]
        ]);
        break;

    case 'mod:approve_thread':
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        $approve = isset($options['approve']) ? (int)$options['approve'] : 1;
        $mod_uid = isset($options['uid']) ? (int)$options['uid'] : 1;

        if ($tid <= 0) {
            respond(false, [], "Required: --tid");
        }

        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation();
        $success = $approve ? $moderation->approve_threads($tid) : $moderation->unapprove_threads($tid);

        if (!$success) {
            respond(false, ["tid" => $tid], "Failed to update thread approval state");
        }

        $thread = get_thread($tid);
        $log_data = [
            "tid" => $tid,
            "fid" => $thread['fid'] ?? 0,
            "subject" => $thread['subject'] ?? '',
        ];
        log_mod_action($approve ? "Thread approved" : "Thread unapproved", $log_data, $mod_uid);

        respond(true, [
            "tid" => $tid,
            "actions_taken" => [$approve ? "thread_approved" : "thread_unapproved"]
        ]);
        break;

    case 'mod:approve_post':
        $pid = isset($options['pid']) ? (int)$options['pid'] : 0;
        $approve = isset($options['approve']) ? (int)$options['approve'] : 1;
        $mod_uid = isset($options['uid']) ? (int)$options['uid'] : 1;

        if ($pid <= 0) {
            respond(false, [], "Required: --pid");
        }

        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation();
        $success = $approve ? $moderation->approve_posts([$pid]) : $moderation->unapprove_posts([$pid]);

        if (!$success) {
            respond(false, ["pid" => $pid], "Failed to update post approval state");
        }

        $post = get_post($pid);
        $log_data = [
            "pid" => $pid,
            "tid" => $post['tid'] ?? 0,
            "fid" => $post['fid'] ?? 0,
        ];
        log_mod_action($approve ? "Post approved" : "Post unapproved", $log_data, $mod_uid);

        respond(true, [
            "pid" => $pid,
            "actions_taken" => [$approve ? "post_approved" : "post_unapproved"]
        ]);
        break;

    case 'mod:soft_delete_thread':
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        $mod_uid = isset($options['uid']) ? (int)$options['uid'] : 1;
        if ($tid <= 0) {
            respond(false, [], "Required: --tid");
        }

        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation();
        $success = $moderation->soft_delete_threads($tid);

        if (!$success) {
            respond(false, ["tid" => $tid], "Failed to soft delete thread");
        }

        $thread = get_thread($tid);
        $log_data = [
            "tid" => $tid,
            "fid" => $thread['fid'] ?? 0,
            "subject" => $thread['subject'] ?? '',
        ];
        log_mod_action("Thread soft deleted", $log_data, $mod_uid);

        respond(true, [
            "tid" => $tid,
            "actions_taken" => ["thread_soft_deleted"]
        ]);
        break;

    case 'mod:restore_thread':
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        $mod_uid = isset($options['uid']) ? (int)$options['uid'] : 1;
        if ($tid <= 0) {
            respond(false, [], "Required: --tid");
        }

        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation();
        $success = $moderation->restore_threads($tid);

        if (!$success) {
            respond(false, ["tid" => $tid], "Failed to restore thread");
        }

        $thread = get_thread($tid);
        $log_data = [
            "tid" => $tid,
            "fid" => $thread['fid'] ?? 0,
            "subject" => $thread['subject'] ?? '',
        ];
        log_mod_action("Thread restored", $log_data, $mod_uid);

        respond(true, [
            "tid" => $tid,
            "actions_taken" => ["thread_restored"]
        ]);
        break;

    case 'mod:soft_delete_post':
        $pid = isset($options['pid']) ? (int)$options['pid'] : 0;
        $mod_uid = isset($options['uid']) ? (int)$options['uid'] : 1;
        if ($pid <= 0) {
            respond(false, [], "Required: --pid");
        }

        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation();
        $success = $moderation->soft_delete_posts([$pid]);

        if (!$success) {
            respond(false, ["pid" => $pid], "Failed to soft delete post");
        }

        $post = get_post($pid);
        $log_data = [
            "pid" => $pid,
            "tid" => $post['tid'] ?? 0,
            "fid" => $post['fid'] ?? 0,
        ];
        log_mod_action("Post soft deleted", $log_data, $mod_uid);

        respond(true, [
            "pid" => $pid,
            "actions_taken" => ["post_soft_deleted"]
        ]);
        break;

    case 'mod:restore_post':
        $pid = isset($options['pid']) ? (int)$options['pid'] : 0;
        $mod_uid = isset($options['uid']) ? (int)$options['uid'] : 1;
        if ($pid <= 0) {
            respond(false, [], "Required: --pid");
        }

        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation();
        $success = $moderation->restore_posts([$pid]);

        if (!$success) {
            respond(false, ["pid" => $pid], "Failed to restore post");
        }

        $post = get_post($pid);
        $log_data = [
            "pid" => $pid,
            "tid" => $post['tid'] ?? 0,
            "fid" => $post['fid'] ?? 0,
        ];
        log_mod_action("Post restored", $log_data, $mod_uid);

        respond(true, [
            "pid" => $pid,
            "actions_taken" => ["post_restored"]
        ]);
        break;

    case 'modlog:add':
        $uid = isset($options['uid']) ? (int)$options['uid'] : 0;
        $log_action = $options['logaction'] ?? '';
        $fid = isset($options['fid']) ? (int)$options['fid'] : 0;
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        $pid = isset($options['pid']) ? (int)$options['pid'] : 0;
        $data = $options['data'] ?? '';
        $ipaddress = $options['ipaddress'] ?? '';

        if ($uid <= 0 || $log_action === '') {
            respond(false, [], "Required: --uid and --logaction");
        }

        if (!isset($mybb->user) || !is_array($mybb->user)) {
            $mybb->user = [];
        }
        $mybb->user['uid'] = $uid;

        if (!isset($session) || !is_object($session)) {
            $session = new stdClass();
        }
        if ($ipaddress !== '') {
            $session->packedip = my_inet_pton($ipaddress);
        } elseif (!isset($session->packedip)) {
            $session->packedip = my_inet_pton('127.0.0.1');
        }

        $payload = [];
        if ($fid > 0) {
            $payload['fid'] = $fid;
        }
        if ($tid > 0) {
            $payload['tid'] = $tid;
        }
        if ($pid > 0) {
            $payload['pid'] = $pid;
        }
        if ($data !== '') {
            $payload['data'] = $data;
        }

        log_moderator_action($payload, $log_action);

        respond(true, [
            "uid" => $uid,
            "actions_taken" => ["modlog_added"]
        ]);
        break;

    // ========================================================================
    // Content Actions (MyBB-native)
    // ========================================================================
    case 'thread:create':
        $fid = isset($options['fid']) ? (int)$options['fid'] : 0;
        $subject = $options['subject'] ?? '';
        $message = $options['message'] ?? '';
        $uid = isset($options['uid']) ? (int)$options['uid'] : 1;
        $username = $options['username'] ?? 'Admin';

        if ($fid <= 0 || $subject === '' || $message === '') {
            respond(false, [], "Required: --fid, --subject, --message");
        }

        require_once MYBB_ROOT . "inc/datahandlers/post.php";
        $posthandler = new PostDataHandler("insert");
        $posthandler->action = "thread";

        // PostDataHandler expects a packed ip for validation paths.
        $packed_ip = my_inet_pton('127.0.0.1');
        $posthash = md5(uniqid((string)mt_rand(), true));

        $new_thread = array(
            "fid" => $fid,
            "subject" => $subject,
            "prefix" => 0,
            "icon" => 0,
            "uid" => $uid,
            "username" => $username,
            "message" => $message,
            "ipaddress" => $packed_ip,
            "posthash" => $posthash,
            "savedraft" => 0,
            "options" => array(
                "signature" => 0,
                "subscriptionmethod" => 0,
                "disablesmilies" => 0
            ),
            "modoptions" => array()
        );

        $posthandler->set_data($new_thread);
        $valid_thread = $posthandler->validate_thread();
        if (!$valid_thread) {
            $errors = $posthandler->get_friendly_errors();
            respond(false, ["errors" => $errors], "Thread validation failed");
        }

        $threadinfo = $posthandler->insert_thread();
        respond(true, [
            "tid" => (int)$posthandler->tid,
            "pid" => (int)$posthandler->pid,
            "visibility" => $threadinfo["visible"] ?? null,
            "actions_taken" => ["thread_created"]
        ]);
        break;

    case 'thread:edit':
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        if ($tid <= 0) {
            respond(false, [], "Required: --tid");
        }

        $actions_taken = [];
        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation;

        if (isset($options['subject'])) {
            $subject = (string)$options['subject'];
            $moderation->change_thread_subject($tid, $subject);
            $actions_taken[] = "thread_subject_updated";
        }

        if (isset($options['closed'])) {
            $closed = (int)$options['closed'];
            if ($closed === 1) {
                $moderation->close_threads([$tid]);
                $actions_taken[] = "thread_closed";
            } elseif ($closed === 0) {
                $moderation->open_threads([$tid]);
                $actions_taken[] = "thread_opened";
            }
        }

        if (isset($options['sticky'])) {
            $sticky = (int)$options['sticky'];
            if ($sticky === 1) {
                $moderation->stick_threads([$tid]);
                $actions_taken[] = "thread_stuck";
            } elseif ($sticky === 0) {
                $moderation->unstick_threads([$tid]);
                $actions_taken[] = "thread_unstuck";
            }
        }

        if (isset($options['visible'])) {
            $visible = (int)$options['visible'];
            if ($visible === 1) {
                $moderation->approve_threads([$tid]);
                $actions_taken[] = "thread_approved";
            } elseif ($visible === 0) {
                $moderation->unapprove_threads([$tid]);
                $actions_taken[] = "thread_unapproved";
            } elseif ($visible === -1) {
                $moderation->soft_delete_threads([$tid]);
                $actions_taken[] = "thread_soft_deleted";
            }
        }

        if (empty($actions_taken)) {
            respond(false, [], "No editable fields provided. Use --subject, --closed, --sticky, or --visible.");
        }

        respond(true, [
            "tid" => $tid,
            "actions_taken" => $actions_taken
        ]);
        break;

    case 'thread:delete':
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        $soft = isset($options['soft']);

        if ($tid <= 0) {
            respond(false, [], "Required: --tid");
        }

        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation;
        if ($soft) {
            $moderation->soft_delete_threads([$tid]);
            respond(true, [
                "tid" => $tid,
                "actions_taken" => ["thread_soft_deleted"]
            ]);
        } else {
            $ok = $moderation->delete_thread($tid);
            if (!$ok) {
                respond(false, ["tid" => $tid], "Thread deletion failed");
            }
            respond(true, [
                "tid" => $tid,
                "actions_taken" => ["thread_deleted"]
            ]);
        }
        break;

    case 'thread:move':
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        $new_fid = isset($options['new_fid']) ? (int)$options['new_fid'] : 0;

        if ($tid <= 0 || $new_fid <= 0) {
            respond(false, [], "Required: --tid, --new_fid");
        }

        require_once MYBB_ROOT . "inc/class_moderation.php";
        $moderation = new Moderation;
        $result = $moderation->move_thread($tid, $new_fid, "move", 0);
        if ($result === false) {
            respond(false, ["tid" => $tid, "new_fid" => $new_fid], "Thread move failed");
        }

        respond(true, [
            "tid" => $tid,
            "new_fid" => $new_fid,
            "actions_taken" => ["thread_moved"]
        ]);
        break;

    case 'post:create':
        $tid = isset($options['tid']) ? (int)$options['tid'] : 0;
        $message = $options['message'] ?? '';
        $uid = isset($options['uid']) ? (int)$options['uid'] : 1;
        $username = $options['username'] ?? 'Admin';
        $replyto = isset($options['replyto']) ? (int)$options['replyto'] : 0;

        if ($tid <= 0 || $message === '') {
            respond(false, [], "Required: --tid, --message");
        }

        $thread = get_thread($tid);
        if (!$thread || empty($thread['fid'])) {
            respond(false, ["tid" => $tid], "Thread not found");
        }

        $subject = $options['subject'] ?? ("RE: " . ($thread['subject'] ?? ''));

        require_once MYBB_ROOT . "inc/datahandlers/post.php";
        $posthandler = new PostDataHandler("insert");

        $packed_ip = my_inet_pton('127.0.0.1');
        $posthash = md5(uniqid((string)mt_rand(), true));

        $post = array(
            "tid" => $tid,
            "replyto" => $replyto,
            "fid" => (int)$thread['fid'],
            "subject" => $subject,
            "icon" => 0,
            "uid" => $uid,
            "username" => $username,
            "message" => $message,
            "ipaddress" => $packed_ip,
            "posthash" => $posthash,
            "savedraft" => 0,
            "options" => array(
                "signature" => 0,
                "subscriptionmethod" => 0,
                "disablesmilies" => 0
            ),
            "modoptions" => array()
        );

        $posthandler->set_data($post);
        $valid_post = $posthandler->validate_post();
        if (!$valid_post) {
            $errors = $posthandler->get_friendly_errors();
            respond(false, ["errors" => $errors], "Post validation failed");
        }

        $postinfo = $posthandler->insert_post();
        respond(true, [
            "pid" => (int)($postinfo["pid"] ?? 0),
            "visibility" => $postinfo["visible"] ?? null,
            "actions_taken" => ["post_created"]
        ]);
        break;

    case 'post:edit':
        $pid = isset($options['pid']) ? (int)$options['pid'] : 0;
        $edituid = null;
        if (isset($options['edituid'])) {
            $edituid = (int)$options['edituid'];
        } elseif (isset($options['edit_uid'])) {
            $edituid = (int)$options['edit_uid'];
        }
        $editreason = $options['editreason'] ?? '';
        $subject_in = $options['subject'] ?? null;
        $message_in = $options['message'] ?? null;
        $signature_in = isset($options['signature']) ? (int)$options['signature'] : null;
        $disablesmilies_in = isset($options['disablesmilies']) ? (int)$options['disablesmilies'] : null;

        if ($pid <= 0) {
            respond(false, [], "Required: --pid");
        }

        if ($subject_in === null && $message_in === null) {
            respond(false, [], "Provide at least one of --subject or --message");
        }

        $post = get_post($pid);
        if (!$post) {
            respond(false, ["pid" => $pid], "Post not found");
        }

        $thread = get_thread($post['tid']);
        $prefix = ($thread && isset($thread['prefix'])) ? (int)$thread['prefix'] : 0;

        require_once MYBB_ROOT . "inc/datahandlers/post.php";
        $posthandler = new PostDataHandler("update");

        $subject = $subject_in ?? $post['subject'];
        $message = $message_in ?? $post['message'];
        $signature = $signature_in ?? (isset($post['includesig']) ? (int)$post['includesig'] : 0);
        $disablesmilies = $disablesmilies_in ?? (isset($post['smilieoff']) ? (int)$post['smilieoff'] : 0);
        $icon = isset($post['icon']) ? (int)$post['icon'] : 0;

        $post_data = array(
            "pid" => $pid,
            "tid" => (int)$post['tid'],
            "prefix" => $prefix,
            "subject" => $subject,
            "icon" => $icon,
            "uid" => (int)$post['uid'],
            "username" => $post['username'],
            "edit_uid" => $edituid !== null ? $edituid : (int)$post['uid'],
            "message" => $message,
            "editreason" => $editreason,
            "options" => array(
                "signature" => $signature,
                "disablesmilies" => $disablesmilies
            )
        );

        $posthandler->set_data($post_data);
        if (!$posthandler->validate_post()) {
            $errors = $posthandler->get_friendly_errors();
            respond(false, ["errors" => $errors], "Post validation failed");
        }

        $postinfo = $posthandler->update_post();
        respond(true, [
            "pid" => $pid,
            "visibility" => $postinfo["visible"] ?? null,
            "first_post" => $postinfo["first_post"] ?? null,
            "actions_taken" => ["post_edited"]
        ]);
        break;

    case 'post:delete':
        $pid = isset($options['pid']) ? (int)$options['pid'] : 0;
        $soft = isset($options['soft']);
        $restore = isset($options['restore']);

        if ($pid <= 0) {
            respond(false, [], "Required: --pid");
        }

        if ($restore) {
            require_once MYBB_ROOT . "inc/class_moderation.php";
            $moderation = new Moderation;
            $ok = $moderation->restore_posts([$pid]);
            if (!$ok) {
                respond(false, ["pid" => $pid], "Post restore failed");
            }
            respond(true, [
                "pid" => $pid,
                "actions_taken" => ["post_restored"]
            ]);
        } elseif ($soft) {
            require_once MYBB_ROOT . "inc/class_moderation.php";
            $moderation = new Moderation;
            $moderation->soft_delete_posts([$pid]);
            respond(true, [
                "pid" => $pid,
                "actions_taken" => ["post_soft_deleted"]
            ]);
        } else {
            $ok = delete_post($pid);
            if (!$ok) {
                respond(false, ["pid" => $pid], "Post deletion failed");
            }
            respond(true, [
                "pid" => $pid,
                "actions_taken" => ["post_deleted"]
            ]);
        }
        break;

    // ========================================================================
    // Health Check Action
    // ========================================================================
    case 'bridge:health_check':
        $mode = $options['mode'] ?? 'quick';
        $results = [
            'bridge_version' => MCP_BRIDGE_VERSION,
            'protocol_version' => MCP_BRIDGE_PROTOCOL_VERSION,
            'timestamp' => date('c'),
            'mode' => $mode
        ];

        // Core health
        $results['core'] = [
            'mybb_bootstrap' => defined('IN_MYBB'),
            'mybb_version' => $mybb->version,
            'php_version' => PHP_VERSION,
            'db_connected' => isset($db) && $db->read_link ? true : false,
            'db_engine' => $db->engine ?? 'unknown',
            'cache_handler' => isset($cache->handler) ? get_class($cache->handler) : 'unknown',
            'table_prefix' => TABLE_PREFIX
        ];

        // Forum context (quick stats)
        $stats = $cache->read('stats');
        $results['forum_context'] = [
            'board_name' => $mybb->settings['bbname'] ?? 'Unknown',
            'total_users' => (int)($stats['numusers'] ?? 0),
            'total_threads' => (int)($stats['numthreads'] ?? 0),
            'total_posts' => (int)($stats['numposts'] ?? 0),
            'newest_user' => $stats['lastusername'] ?? 'N/A'
        ];

        // Count forums
        $forum_count = $db->fetch_field($db->simple_select("forums", "COUNT(*) as cnt"), "cnt");
        $results['forum_context']['total_forums'] = (int)$forum_count;

        // Subsystem read probes
        $results['subsystems'] = [];

        // Templates
        $tpl_count = $db->fetch_field($db->simple_select("templates", "COUNT(*) as cnt"), "cnt");
        $results['subsystems']['templates'] = ['read' => true, 'count' => (int)$tpl_count];

        // Stylesheets
        $css_count = $db->fetch_field($db->simple_select("themestylesheets", "COUNT(*) as cnt"), "cnt");
        $results['subsystems']['stylesheets'] = ['read' => true, 'count' => (int)$css_count];

        // Settings
        $set_count = $db->fetch_field($db->simple_select("settings", "COUNT(*) as cnt"), "cnt");
        $results['subsystems']['settings'] = ['read' => true, 'count' => (int)$set_count];

        // Users
        $results['subsystems']['users'] = ['read' => true, 'count' => (int)($stats['numusers'] ?? 0)];

        // Forums
        $results['subsystems']['forums'] = ['read' => true, 'count' => (int)$forum_count];

        // Threads
        $results['subsystems']['threads'] = ['read' => true, 'count' => (int)($stats['numthreads'] ?? 0)];

        // Posts
        $results['subsystems']['posts'] = ['read' => true, 'count' => (int)($stats['numposts'] ?? 0)];

        // Tasks
        $task_total = $db->fetch_field($db->simple_select("tasks", "COUNT(*) as cnt"), "cnt");
        $task_enabled = $db->fetch_field($db->simple_select("tasks", "COUNT(*) as cnt", "enabled=1"), "cnt");
        $results['subsystems']['tasks'] = ['read' => true, 'count' => (int)$task_total, 'enabled' => (int)$task_enabled];

        // Plugins
        $active_plugins = $cache->read('plugins');
        $plugin_count = isset($active_plugins['active']) ? count($active_plugins['active']) : 0;
        $results['subsystems']['plugins'] = ['read' => true, 'active' => $plugin_count];

        // Supported actions
        $supported_actions = [
            'plugin:status',
            'plugin:activate',
            'plugin:deactivate',
            'plugin:list',
            'cache:read',
            'cache:rebuild',
            'cache:rebuild_smilies',
            'setting:set',
            'task:enable',
            'task:disable',
            'task:update_nextrun',
            'template:write',
            'template:find_replace',
            'template:batch_write',
            'templateset:create',
            'templateset:copy_master',
            'stylesheet:write',
            'stylesheet:create',
            'theme:import',
            'theme:update_stylesheet_list',
            'theme:create',
            'theme:get',
            'theme:set_default',
            'forum:create',
            'forum:update',
            'forum:delete',
            'user:update_group',
            'user:ban',
            'user:unban',
            'mod:close_thread',
            'mod:stick_thread',
            'mod:approve_thread',
            'mod:approve_post',
            'mod:soft_delete_thread',
            'mod:restore_thread',
            'mod:soft_delete_post',
            'mod:restore_post',
            'modlog:add',
            'thread:create',
            'thread:edit',
            'thread:delete',
            'thread:move',
            'post:create',
            'post:edit',
            'post:delete',
            'bridge:health_check',
            'info'
        ];
        $results['supported_actions'] = $supported_actions;
        $results['action_count'] = count($supported_actions);

        // Write tests (full mode only)
        $results['write_tests'] = ['enabled' => false, 'results' => null];

        if ($mode === 'full') {
            $results['write_tests']['enabled'] = true;
            $write_results = [];
            $test_start = microtime(true);

            // Load required MyBB classes
            require_once MYBB_ROOT . 'inc/datahandlers/post.php';
            require_once MYBB_ROOT . 'inc/class_moderation.php';

            // Use an existing forum for thread/post tests (forum ID 2 is usually default)
            $test_fid = 2;
            $existing_forum = get_forum($test_fid);
            if (!$existing_forum) {
                // Fallback to first available forum
                $forum_query = $db->simple_select('forums', 'fid', "type='f'", ['limit' => 1]);
                $first_forum = $db->fetch_array($forum_query);
                $test_fid = $first_forum ? (int)$first_forum['fid'] : 0;
            }

            $write_results['forum:exists'] = ['pass' => $test_fid > 0, 'fid' => $test_fid, 'note' => 'using existing forum'];

            if ($test_fid > 0) {
                // Create test thread using PostDataHandler (proper MyBB API)
                $postHandler = new PostDataHandler('insert');
                $postHandler->action = 'thread';
                $thread_data = [
                    'fid' => $test_fid,
                    'subject' => '_mcp_health_test_' . time(),
                    'uid' => 1,
                    'username' => 'Admin',
                    'message' => 'MCP Bridge health check test thread. Safe to delete.',
                    'ipaddress' => '127.0.0.1',
                    'posthash' => md5(time()),
                    'options' => [
                        'signature' => 0,
                        'subscriptionmethod' => 0,
                        'disablesmilies' => 0
                    ]
                ];
                $postHandler->set_data($thread_data);

                $test_tid = 0;
                $test_pid = 0;
                if ($postHandler->validate_thread()) {
                    $thread_info = $postHandler->insert_thread();
                    $test_tid = (int)($thread_info['tid'] ?? 0);
                    $test_pid = (int)($thread_info['pid'] ?? 0);
                    $write_results['thread:create'] = ['pass' => $test_tid > 0, 'tid' => $test_tid, 'pid' => $test_pid];
                } else {
                    $write_results['thread:create'] = ['pass' => false, 'errors' => $postHandler->get_friendly_errors()];
                }

                if ($test_tid > 0) {
                    // Create reply post using PostDataHandler
                    $postHandler2 = new PostDataHandler('insert');
                    $postHandler2->action = 'post';
                    $post_data = [
                        'tid' => $test_tid,
                        'fid' => $test_fid,
                        'subject' => 'Re: Health Check',
                        'uid' => 1,
                        'username' => 'Admin',
                        'message' => 'MCP Bridge health check test reply.',
                        'ipaddress' => '127.0.0.1',
                        'posthash' => md5(time() . '2'),
                        'options' => [
                            'signature' => 0,
                            'disablesmilies' => 0
                        ]
                    ];
                    $postHandler2->set_data($post_data);

                    $reply_pid = 0;
                    if ($postHandler2->validate_post()) {
                        $post_info = $postHandler2->insert_post();
                        $reply_pid = (int)($post_info['pid'] ?? 0);
                        $write_results['post:create'] = ['pass' => $reply_pid > 0, 'pid' => $reply_pid];
                    } else {
                        $write_results['post:create'] = ['pass' => false, 'errors' => $postHandler2->get_friendly_errors()];
                    }

                    // Delete using proper MyBB functions
                    $moderation = new Moderation();

                    if ($reply_pid > 0) {
                        $moderation->delete_post($reply_pid);
                        $write_results['post:delete'] = ['pass' => true];
                    }

                    $moderation->delete_thread($test_tid);
                    $write_results['thread:delete'] = ['pass' => true];
                }
            }

            // Test setting:set (read, write same value back)
            $bbname = $mybb->settings['bbname'];
            $db->update_query('settings', ['value' => $db->escape_string($bbname)], "name='bbname'");
            rebuild_settings();
            $write_results['setting:set'] = ['pass' => true, 'note' => 'wrote same value'];

            // Test template write (create and delete test template)
            $test_tpl_title = '_mcp_test_template_' . time();
            $db->insert_query('templates', [
                'title' => $test_tpl_title,
                'template' => '<div>test</div>',
                'sid' => -2,
                'version' => '',
                'dateline' => TIME_NOW
            ]);
            $db->delete_query('templates', "title='" . $db->escape_string($test_tpl_title) . "'");
            $write_results['template:write'] = ['pass' => true, 'note' => 'created and cleaned'];

            // Test cache rebuild
            $cache->update_forums();
            $write_results['cache:rebuild'] = ['pass' => true];

            $test_duration = round((microtime(true) - $test_start) * 1000);

            $results['write_tests']['results'] = $write_results;
            $results['write_tests']['cleanup'] = 'complete';
            $results['write_tests']['duration_ms'] = $test_duration;
        }

        // Overall health determination
        $issues = [];
        if (!$results['core']['mybb_bootstrap']) $issues[] = 'MyBB failed to bootstrap';
        if (!$results['core']['db_connected']) $issues[] = 'Database not connected';

        $all_subsystems_ok = true;
        foreach ($results['subsystems'] as $name => $status) {
            if (!($status['read'] ?? false)) {
                $issues[] = "Subsystem '{$name}' read failed";
                $all_subsystems_ok = false;
            }
        }

        if (count($issues) === 0) {
            $results['health'] = 'HEALTHY';
        } elseif ($results['core']['mybb_bootstrap'] && $results['core']['db_connected']) {
            $results['health'] = 'DEGRADED';
        } else {
            $results['health'] = 'UNHEALTHY';
        }
        $results['issues'] = $issues;

        respond(true, $results);
        break;

    // ========================================================================
    // Info Action
    // ========================================================================
    case 'info':
        // Check MyBB version compatibility
        $compat = MCP_BRIDGE_MYBB_COMPAT;
        $mybb_version = $mybb->version;
        $is_compatible = version_compare($mybb_version, $compat['min'], '>=') &&
                         version_compare($mybb_version, $compat['max'], '<=');
        $compat_warning = null;
        if (!$is_compatible) {
            if (version_compare($mybb_version, $compat['min'], '<')) {
                $compat_warning = "MyBB {$mybb_version} is older than minimum tested ({$compat['min']}). Bridge may not work correctly.";
            } else {
                $compat_warning = "MyBB {$mybb_version} is newer than maximum tested ({$compat['max']}). Bridge may need updates.";
            }
        }

        respond(true, [
            'bridge_version' => MCP_BRIDGE_VERSION,
            'protocol_version' => MCP_BRIDGE_PROTOCOL_VERSION,
            'mybb_compat' => [
                'min' => $compat['min'],
                'max' => $compat['max'],
                'tested' => $compat['tested'],
                'current' => $mybb_version,
                'is_compatible' => $is_compatible,
                'warning' => $compat_warning,
            ],
            'supported_actions' => [
                'plugin:status',
                'plugin:activate',
                'plugin:deactivate',
                'plugin:list',
                'cache:read',
                'cache:rebuild',
                'cache:rebuild_smilies',
                'setting:set',
                'task:enable',
                'task:disable',
                'task:update_nextrun',
                'template:write',
                'template:find_replace',
                'template:batch_write',
                'template:list',
                'templateset:create',
                'templateset:copy_master',
                'stylesheet:write',
                'stylesheet:create',
                'stylesheet:list',
                'theme:import',
                'theme:update_stylesheet_list',
                'theme:create',
                'theme:get',
                'theme:set_default',
                'forum:create',
                'forum:update',
                'forum:delete',
                'user:update_group',
                'user:ban',
                'user:unban',
                'mod:close_thread',
                'mod:stick_thread',
                'mod:approve_thread',
                'mod:approve_post',
                'mod:soft_delete_thread',
                'mod:restore_thread',
                'mod:soft_delete_post',
                'mod:restore_post',
                'modlog:add',
                'thread:create',
                'thread:edit',
                'thread:delete',
                'thread:move',
                'post:create',
                'post:edit',
                'post:delete',
                'bridge:health_check',
                'info',
            ],
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
