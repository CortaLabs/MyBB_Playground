<?php
/**
 * Test Tracker Plugin
 * Test plugin for verifying file tracking and deployment
 *
 * @author Developer
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
    $templatelist .= 'test_tracker_main';
}

$plugins->add_hook('index_start', 'test_tracker_index_start');
$plugins->add_hook('global_start', 'test_tracker_global_start');

/**
 * Plugin information
 */
function test_tracker_info()
{
    return array(
        'name'          => 'Test Tracker Plugin',
        'description'   => 'Test plugin for verifying file tracking and deployment',
        'website'       => '',
        'author'        => 'Developer',
        'authorsite'    => '',
        'version'       => '1.0.0',
        'compatibility' => '18*',
        'codename'      => 'test_tracker'
    );
}

/**
 * Plugin activation - inject banner into index template
 */
function test_tracker_activate()
{
    global $db;

    require_once MYBB_ROOT . 'inc/adminfunctions_templates.php';

    // Inject banner variable after header in index template
    find_replace_templatesets(
        'index',
        '#' . preg_quote('{$header}') . '#',
        '{$header}{$test_tracker_banner}'
    );
}

/**
 * Plugin deactivation - remove banner from index template
 */
function test_tracker_deactivate()
{
    global $db;

    require_once MYBB_ROOT . 'inc/adminfunctions_templates.php';

    // Remove banner variable from index template
    find_replace_templatesets(
        'index',
        '#' . preg_quote('{$test_tracker_banner}') . '#',
        ''
    );
}

/**
 * Check if plugin is installed
 */
function test_tracker_is_installed()
{
    global $db;
    $query = $db->simple_select('templates', 'tid', "title='test_tracker_banner'", array('limit' => 1));
    return $db->num_rows($query) > 0;
}

/**
 * Plugin installation
 */
function test_tracker_install()
{
    global $db;

    // Create banner template
    $template = array(
        'title' => 'test_tracker_banner',
        'template' => $db->escape_string('<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <strong>🎉 Test Tracker Plugin Active!</strong>
    <p style="margin: 5px 0 0 0; opacity: 0.9;">File tracking deployment test successful. Installed: {$install_time}</p>
</div>'),
        'sid' => -2,
        'version' => '',
        'dateline' => TIME_NOW
    );
    $db->insert_query('templates', $template);
}

/**
 * Plugin uninstallation
 */
function test_tracker_uninstall()
{
    global $db;

    $db->delete_query('templates', "title LIKE 'test_tracker%'");
}


/**
 * Hook: index_start - inject banner into index page
 */
function test_tracker_index_start(&$args)
{
    global $mybb, $templates, $test_tracker_banner;

    // Get install time for display
    $install_time = date('Y-m-d H:i:s');

    // Eval the banner template
    eval('$test_tracker_banner = "' . $templates->get('test_tracker_banner') . '";');
}


/**
 * Hook: global_start
 */
function test_tracker_global_start(&$args)
{
    global $mybb;
    // Nothing needed here for now
}

