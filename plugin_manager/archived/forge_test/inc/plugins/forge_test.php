<?php
/**
 * Forge Config Test
 * Testing that ForgeConfig developer info is used
 *
 * @author Austin
 * @version 1.0.0
 */

// Prevent direct access
if(!defined('IN_MYBB'))
{
    die('This file cannot be accessed directly.');
}

// Cache templates
if(defined('THIS_SCRIPT'))
{
    global $templatelist;
    if(isset($templatelist))
    {
        $templatelist .= ',';
    }
    $templatelist .= 'forge_test_main';
}

$plugins->add_hook('index_start', 'forge_test_index_start');

/**
 * Plugin information
 */
function forge_test_info()
{
    return array(
        'name'          => 'Forge Config Test',
        'description'   => 'Testing that ForgeConfig developer info is used',
        'website'       => '',
        'author'        => 'Austin',
        'authorsite'    => 'https://cortalabs.com',
        'version'       => '1.0.0',
        'compatibility' => '18*',
        'codename'      => 'forge_test'
    );
}

/**
 * Load templates from disk files in the templates/ directory.
 * Template files are named without the plugin prefix (e.g., "main.html")
 * and will be inserted with the full name (e.g., "forge_test_main").
 */
function forge_test_load_templates_from_disk() {
    global $db;

    // Templates are in the plugin's subdirectory
    $templates_dir = MYBB_ROOT . 'inc/plugins/forge_test/templates';
    if (!is_dir($templates_dir)) {
        return;
    }

    foreach (glob($templates_dir . '/*.html') as $file) {
        $template_name = 'forge_test_' . basename($file, '.html');
        $content = file_get_contents($file);

        // Check if template already exists
        $existing = $db->simple_select('templates', 'tid', "title='" . $db->escape_string($template_name) . "' AND sid=-2");
        if ($db->num_rows($existing) > 0) {
            $row = $db->fetch_array($existing);
            $db->update_query('templates', [
                'template' => $db->escape_string($content),
                'dateline' => TIME_NOW
            ], "tid={$row['tid']}");
        } else {
            $db->insert_query('templates', [
                'title' => $db->escape_string($template_name),
                'template' => $db->escape_string($content),
                'sid' => -2,
                'version' => '',
                'dateline' => TIME_NOW
            ]);
        }
    }
}


/**
 * Plugin activation
 */
function forge_test_activate()
{
    global $db;

    // Templates are loaded during installation
}

/**
 * Plugin deactivation
 */
function forge_test_deactivate()
{
    global $db;

    // Nothing to deactivate
}

/**
 * Check if plugin is installed
 */
function forge_test_is_installed()
{
    global $db;
    return false; // No installation required
}

/**
 * Plugin installation
 */
function forge_test_install()
{
    global $db;

    // Load templates from disk
    forge_test_load_templates_from_disk();
}

/**
 * Plugin uninstallation
 */
function forge_test_uninstall()
{
    global $db;

    $db->delete_query('templates', "title LIKE 'forge_test%'");
}


/**
 * Hook: index_start
 */
function forge_test_index_start(&$args)
{
    global $mybb, $db, $templates, $lang;

    // Your hook code here

    // For form submissions, verify CSRF token:
    // verify_post_check($mybb->get_input('my_post_key'));
}

