<?php
/**
 * README Template Test
 * Testing the new comprehensive README template. This plugin demonstrates proper documentation structure.
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
    $templatelist .= 'readme_test_main';
}

$plugins->add_hook('index_start', 'readme_test_index_start');
$plugins->add_hook('postbit', 'readme_test_postbit');

/**
 * Plugin information
 */
function readme_test_info()
{
    return array(
        'name'          => 'README Template Test',
        'description'   => 'Testing the new comprehensive README template. This plugin demonstrates proper documentation structure.',
        'website'       => '',
        'author'        => 'Austin',
        'authorsite'    => 'https://cortalabs.com',
        'version'       => '1.0.0',
        'compatibility' => '18*',
        'codename'      => 'readme_test'
    );
}

/**
 * Load templates from disk files in the templates/ directory.
 * Template files are named without the plugin prefix (e.g., "main.html")
 * and will be inserted with the full name (e.g., "readme_test_main").
 */
function readme_test_load_templates_from_disk() {
    global $db;

    // Templates are in the plugin's subdirectory
    $templates_dir = MYBB_ROOT . 'inc/plugins/readme_test/templates';
    if (!is_dir($templates_dir)) {
        return;
    }

    foreach (glob($templates_dir . '/*.html') as $file) {
        $template_name = 'readme_test_' . basename($file, '.html');
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
function readme_test_activate()
{
    global $db;

    // Templates are loaded during installation
}

/**
 * Plugin deactivation
 */
function readme_test_deactivate()
{
    global $db;

    // Nothing to deactivate
}

/**
 * Check if plugin is installed
 */
function readme_test_is_installed()
{
    global $db;
    return $db->table_exists('readme_test_data');
}

/**
 * Plugin installation
 */
function readme_test_install()
{
    global $db;

    // Create database table
    $collation = $db->build_create_table_collation();

    if(!$db->table_exists('readme_test_data')) {
        $db->write_query("CREATE TABLE ".TABLE_PREFIX."readme_test_data (
            id int unsigned NOT NULL auto_increment,
            uid int unsigned NOT NULL default 0,
            data text,
            dateline int unsigned NOT NULL default 0,
            PRIMARY KEY (id)
        ) ENGINE=MyISAM{$collation};");
    }
    // Load templates from disk
    readme_test_load_templates_from_disk();
}

/**
 * Plugin uninstallation
 */
function readme_test_uninstall()
{
    global $db;

    $db->delete_query('templates', "title LIKE 'readme_test%'");
    $db->drop_table('readme_test_data');
}


/**
 * Hook: index_start
 */
function readme_test_index_start(&$args)
{
    global $mybb, $db, $templates, $lang;

    // Your hook code here

    // For form submissions, verify CSRF token:
    // verify_post_check($mybb->get_input('my_post_key'));
}


/**
 * Hook: postbit
 */
function readme_test_postbit(&$args)
{
    global $mybb, $db, $templates, $lang;

    // Your hook code here

    // For form submissions, verify CSRF token:
    // verify_post_check($mybb->get_input('my_post_key'));
}

