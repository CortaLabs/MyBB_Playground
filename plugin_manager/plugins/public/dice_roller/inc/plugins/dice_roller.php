<?php
/**
 * Dice Roller
 * BBCode dice rolling with database tracking and post CSS effects for tabletop gaming
 *
 * @author Corta Labs
 * @version 1.0.0
 */

// Prevent direct access
if(!defined('IN_MYBB'))
{
    die('This file cannot be accessed directly.');
}

// Cache templates - add all our templates here
if(defined('THIS_SCRIPT'))
{
    global $templatelist;
    if(isset($templatelist))
    {
        $templatelist .= ',';
    }
    $templatelist .= 'dice_roller_result,dice_roller_result_crit,dice_roller_result_fail';
}

// Hook into post creation to process dice rolls BEFORE saving
$plugins->add_hook('datahandler_post_insert_post', 'dice_roller_process_on_insert');
$plugins->add_hook('datahandler_post_insert_thread_post', 'dice_roller_process_on_insert');
$plugins->add_hook('datahandler_post_update', 'dice_roller_process_on_update');

// Hook into message parsing to render dice results
$plugins->add_hook('parse_message', 'dice_roller_render_results');

// Hook into postbit to add CSS classes for crits
$plugins->add_hook('postbit', 'dice_roller_postbit');
$plugins->add_hook('postbit_prev', 'dice_roller_postbit');

// Hook to inject CSS styles (global_end ensures $headerinclude exists)
$plugins->add_hook('global_end', 'dice_roller_global_start');

/**
 * Plugin information
 */
function dice_roller_info()
{
    return array(
        'name'          => 'Dice Roller',
        'description'   => 'BBCode dice rolling with database tracking and post CSS effects for tabletop gaming. Use [roll]2d6+5[/roll] syntax.',
        'website'       => 'https://github.com/CortaLabs/MyBB_Playground',
        'author'        => 'Corta Labs',
        'authorsite'    => '',
        'version'       => '1.0.0',
        'compatibility' => '18*',
        'codename'      => 'dice_roller'
    );
}

/**
 * Plugin activation - add settings and templates
 */
function dice_roller_activate()
{
    global $db;

    // Add setting group
    $setting_group = array(
        'name'        => 'dice_roller',
        'title'       => 'Dice Roller Settings',
        'description' => 'Settings for the Dice Roller BBCode plugin',
        'disporder'   => 100,
        'isdefault'   => 0
    );
    $gid = $db->insert_query('settinggroups', $setting_group);

    // Add settings
    $settings = array(
        array(
            'name'        => 'dice_roller_enabled',
            'title'       => 'Enable Dice Roller',
            'description' => 'Enable or disable the dice roller BBCode',
            'optionscode' => 'yesno',
            'value'       => '1',
            'disporder'   => 1,
            'gid'         => $gid
        ),
        array(
            'name'        => 'dice_roller_max_dice',
            'title'       => 'Maximum Dice Per Roll',
            'description' => 'Maximum number of dice allowed in a single roll (e.g., 100 for 100d6)',
            'optionscode' => 'numeric',
            'value'       => '100',
            'disporder'   => 2,
            'gid'         => $gid
        ),
        array(
            'name'        => 'dice_roller_max_sides',
            'title'       => 'Maximum Sides Per Die',
            'description' => 'Maximum number of sides allowed (e.g., 1000 for d1000)',
            'optionscode' => 'numeric',
            'value'       => '1000',
            'disporder'   => 3,
            'gid'         => $gid
        ),
        array(
            'name'        => 'dice_roller_crit_effects',
            'title'       => 'Enable Critical Hit/Fail Effects',
            'description' => 'Add CSS classes to posts containing natural 20s or natural 1s',
            'optionscode' => 'yesno',
            'value'       => '1',
            'disporder'   => 4,
            'gid'         => $gid
        )
    );

    foreach($settings as $setting)
    {
        $db->insert_query('settings', $setting);
    }

    // Rebuild settings
    rebuild_settings();

    // Add templates
    $templates = array(
        'dice_roller_result' => '<span class="dice-roll" data-rid="{$rid}">
    <span class="dice-label">{$label}</span>
    <span class="dice-notation">{$notation}</span>
    <span class="dice-breakdown">[{$dice_display}]</span>
    <span class="dice-modifier">{$modifier_display}</span>
    <span class="dice-equals">=</span>
    <span class="dice-total">{$total}</span>
</span>',
        'dice_roller_result_crit' => '<span class="dice-roll dice-crit-success" data-rid="{$rid}">
    <span class="dice-label">{$label}</span>
    <span class="dice-notation">{$notation}</span>
    <span class="dice-breakdown">[{$dice_display}]</span>
    <span class="dice-modifier">{$modifier_display}</span>
    <span class="dice-equals">=</span>
    <span class="dice-total dice-nat20">{$total}</span>
    <span class="dice-crit-text">CRITICAL!</span>
</span>',
        'dice_roller_result_fail' => '<span class="dice-roll dice-crit-fail" data-rid="{$rid}">
    <span class="dice-label">{$label}</span>
    <span class="dice-notation">{$notation}</span>
    <span class="dice-breakdown">[{$dice_display}]</span>
    <span class="dice-modifier">{$modifier_display}</span>
    <span class="dice-equals">=</span>
    <span class="dice-total dice-nat1">{$total}</span>
    <span class="dice-crit-text">FUMBLE!</span>
</span>'
    );

    foreach($templates as $title => $template)
    {
        $template_data = array(
            'title'    => $title,
            'template' => $db->escape_string($template),
            'sid'      => -2,
            'version'  => '',
            'dateline' => TIME_NOW
        );
        $db->insert_query('templates', $template_data);
    }
}

/**
 * Plugin deactivation - remove settings and templates
 */
function dice_roller_deactivate()
{
    global $db;

    // Remove settings
    $db->delete_query('settinggroups', "name = 'dice_roller'");
    $db->delete_query('settings', "name LIKE 'dice_roller_%'");
    rebuild_settings();

    // Remove templates
    $db->delete_query('templates', "title LIKE 'dice_roller_%'");
}

/**
 * Check if plugin is installed
 */
function dice_roller_is_installed()
{
    global $db;
    return $db->table_exists('dice_rolls');
}

/**
 * Plugin installation - create database table
 */
function dice_roller_install()
{
    global $db;

    // Create dice_rolls table
    $collation = $db->build_create_table_collation();

    if(!$db->table_exists('dice_rolls'))
    {
        $db->write_query("CREATE TABLE ".TABLE_PREFIX."dice_rolls (
            rid INT UNSIGNED NOT NULL AUTO_INCREMENT,
            pid INT UNSIGNED NOT NULL DEFAULT 0,
            tid INT UNSIGNED NOT NULL DEFAULT 0,
            uid INT UNSIGNED NOT NULL DEFAULT 0,
            roll_input VARCHAR(100) NOT NULL DEFAULT '',
            roll_label VARCHAR(100) NOT NULL DEFAULT '',
            num_dice TINYINT UNSIGNED NOT NULL DEFAULT 1,
            num_sides SMALLINT UNSIGNED NOT NULL DEFAULT 6,
            modifier SMALLINT NOT NULL DEFAULT 0,
            dice_results VARCHAR(500) NOT NULL DEFAULT '',
            total SMALLINT NOT NULL DEFAULT 0,
            is_crit TINYINT NOT NULL DEFAULT 0,
            dateline INT UNSIGNED NOT NULL DEFAULT 0,
            PRIMARY KEY (rid),
            KEY pid (pid),
            KEY uid (uid),
            KEY is_crit (is_crit)
        ) ENGINE=MyISAM{$collation};");
    }
}

/**
 * Plugin uninstallation - drop table
 */
function dice_roller_uninstall()
{
    global $db;

    if($db->table_exists('dice_rolls'))
    {
        $db->drop_table('dice_rolls');
    }
}

// ============================================================================
// CORE DICE ROLLING LOGIC
// ============================================================================

/**
 * Parse dice notation string (e.g., "2d6+5", "1d20-2", "4d6k3")
 *
 * @param string $notation The dice notation
 * @return array|false Parsed components or false if invalid
 */
function dice_roller_parse_notation($notation)
{
    global $mybb;

    // Pattern: [count]d<sides>[k<keep>][+/-<modifier>]
    // Examples: 2d6, 1d20+5, 4d6k3, 3d8-2
    $pattern = '/^(\d+)?d(\d+)(k(\d+))?([+-]\d+)?$/i';

    if(!preg_match($pattern, trim($notation), $matches))
    {
        return false;
    }

    $num_dice = !empty($matches[1]) ? (int)$matches[1] : 1;
    $num_sides = (int)$matches[2];
    $keep_highest = !empty($matches[4]) ? (int)$matches[4] : 0;
    $modifier = !empty($matches[5]) ? (int)$matches[5] : 0;

    // Validate limits
    $max_dice = isset($mybb->settings['dice_roller_max_dice']) ? (int)$mybb->settings['dice_roller_max_dice'] : 100;
    $max_sides = isset($mybb->settings['dice_roller_max_sides']) ? (int)$mybb->settings['dice_roller_max_sides'] : 1000;

    if($num_dice < 1 || $num_dice > $max_dice)
    {
        return false;
    }

    if($num_sides < 2 || $num_sides > $max_sides)
    {
        return false;
    }

    if($keep_highest > 0 && $keep_highest >= $num_dice)
    {
        $keep_highest = 0; // Keep all if keep >= dice count
    }

    return array(
        'num_dice'     => $num_dice,
        'num_sides'    => $num_sides,
        'keep_highest' => $keep_highest,
        'modifier'     => $modifier,
        'original'     => $notation
    );
}

/**
 * Roll dice and return results
 *
 * @param array $parsed Parsed notation from dice_roller_parse_notation()
 * @return array Roll results
 */
function dice_roller_execute_roll($parsed)
{
    $results = array();

    // Roll each die
    for($i = 0; $i < $parsed['num_dice']; $i++)
    {
        $results[] = mt_rand(1, $parsed['num_sides']);
    }

    // Handle keep highest (e.g., 4d6k3)
    $kept_results = $results;
    $dropped = array();

    if($parsed['keep_highest'] > 0)
    {
        rsort($kept_results, SORT_NUMERIC);
        $dropped = array_slice($kept_results, $parsed['keep_highest']);
        $kept_results = array_slice($kept_results, 0, $parsed['keep_highest']);
    }

    // Calculate total
    $dice_sum = array_sum($kept_results);
    $total = $dice_sum + $parsed['modifier'];

    // Check for critical (natural 20 on d20, or natural 1)
    $is_crit = 0;
    if($parsed['num_sides'] == 20 && $parsed['num_dice'] == 1)
    {
        if($results[0] == 20)
        {
            $is_crit = 1; // Natural 20
        }
        elseif($results[0] == 1)
        {
            $is_crit = -1; // Natural 1
        }
    }

    return array(
        'dice_results'  => $results,
        'kept_results'  => $kept_results,
        'dropped'       => $dropped,
        'dice_sum'      => $dice_sum,
        'modifier'      => $parsed['modifier'],
        'total'         => $total,
        'is_crit'       => $is_crit,
        'num_dice'      => $parsed['num_dice'],
        'num_sides'     => $parsed['num_sides']
    );
}

/**
 * Process [roll] tags in message content
 *
 * @param string $message The message content
 * @param int $pid Post ID (0 if new post)
 * @param int $tid Thread ID
 * @param int $uid User ID
 * @return string Modified message with [diceresult] tags
 */
function dice_roller_process_rolls(&$message, $pid, $tid, $uid)
{
    global $db, $mybb;

    // Check if enabled
    if(isset($mybb->settings['dice_roller_enabled']) && !$mybb->settings['dice_roller_enabled'])
    {
        return $message;
    }

    // Pattern: [roll=Label]notation[/roll] or [roll]notation[/roll]
    $pattern = '/\[roll(?:=([^\]]*))?\]([^\[]+)\[\/roll\]/i';

    $message = preg_replace_callback($pattern, function($matches) use ($db, $pid, $tid, $uid) {
        $label = !empty($matches[1]) ? htmlspecialchars_uni(trim($matches[1])) : '';
        $notation = trim($matches[2]);

        // Parse the notation
        $parsed = dice_roller_parse_notation($notation);
        if($parsed === false)
        {
            // Invalid notation - return original text with error
            return '<span class="dice-error">[Invalid dice: ' . htmlspecialchars_uni($notation) . ']</span>';
        }

        // Execute the roll
        $roll = dice_roller_execute_roll($parsed);

        // Save to database
        $roll_data = array(
            'pid'          => (int)$pid,
            'tid'          => (int)$tid,
            'uid'          => (int)$uid,
            'roll_input'   => $db->escape_string($notation),
            'roll_label'   => $db->escape_string($label),
            'num_dice'     => $roll['num_dice'],
            'num_sides'    => $roll['num_sides'],
            'modifier'     => $roll['modifier'],
            'dice_results' => $db->escape_string(json_encode($roll['dice_results'])),
            'total'        => $roll['total'],
            'is_crit'      => $roll['is_crit'],
            'dateline'     => TIME_NOW
        );
        $rid = $db->insert_query('dice_rolls', $roll_data);

        // Return placeholder that will be rendered later
        return "[diceresult={$rid}][/diceresult]";

    }, $message);

    return $message;
}

/**
 * Hook: Process rolls when a new post is inserted
 */
function dice_roller_process_on_insert(&$posthandler)
{
    global $mybb;

    if(isset($posthandler->post_insert_data['message']))
    {
        $pid = 0; // Will be updated after insert
        $tid = isset($posthandler->post_insert_data['tid']) ? (int)$posthandler->post_insert_data['tid'] : 0;
        $uid = isset($posthandler->post_insert_data['uid']) ? (int)$posthandler->post_insert_data['uid'] : (int)$mybb->user['uid'];

        dice_roller_process_rolls(
            $posthandler->post_insert_data['message'],
            $pid,
            $tid,
            $uid
        );
    }
}

/**
 * Hook: Process rolls when a post is updated
 */
function dice_roller_process_on_update(&$posthandler)
{
    global $mybb;

    if(isset($posthandler->post_update_data['message']))
    {
        $pid = isset($posthandler->pid) ? (int)$posthandler->pid : 0;
        $tid = isset($posthandler->data['tid']) ? (int)$posthandler->data['tid'] : 0;
        $uid = (int)$mybb->user['uid'];

        dice_roller_process_rolls(
            $posthandler->post_update_data['message'],
            $pid,
            $tid,
            $uid
        );
    }
}

/**
 * Hook: Render dice results in message
 */
function dice_roller_render_results(&$message)
{
    global $db, $templates;

    // Pattern: [diceresult=rid][/diceresult]
    $pattern = '/\[diceresult=(\d+)\]\[\/diceresult\]/';

    $message = preg_replace_callback($pattern, function($matches) use ($db, $templates) {
        $rid = (int)$matches[1];

        // Fetch roll from database
        $query = $db->simple_select('dice_rolls', '*', "rid = {$rid}", array('limit' => 1));
        $roll = $db->fetch_array($query);

        if(!$roll)
        {
            return '<span class="dice-error">[Roll not found]</span>';
        }

        // Prepare template variables
        $label = $roll['roll_label'] ? htmlspecialchars_uni($roll['roll_label']) . ': ' : '';
        $notation = htmlspecialchars_uni($roll['roll_input']);
        $dice_results = json_decode($roll['dice_results'], true);
        $dice_display = implode(', ', $dice_results);
        $total = (int)$roll['total'];
        $modifier = (int)$roll['modifier'];

        $modifier_display = '';
        if($modifier > 0)
        {
            $modifier_display = '+' . $modifier;
        }
        elseif($modifier < 0)
        {
            $modifier_display = $modifier;
        }

        // Select template based on crit status
        $is_crit = (int)$roll['is_crit'];

        if($is_crit == 1)
        {
            eval('$output = "' . $templates->get('dice_roller_result_crit') . '";');
        }
        elseif($is_crit == -1)
        {
            eval('$output = "' . $templates->get('dice_roller_result_fail') . '";');
        }
        else
        {
            eval('$output = "' . $templates->get('dice_roller_result') . '";');
        }

        return $output;

    }, $message);

    return $message;
}

/**
 * Hook: Add CSS classes to posts with critical rolls
 */
function dice_roller_postbit(&$post)
{
    global $db, $mybb;

    // Check if crit effects are enabled
    if(!isset($mybb->settings['dice_roller_crit_effects']) || !$mybb->settings['dice_roller_crit_effects'])
    {
        return;
    }

    $pid = (int)$post['pid'];
    if($pid <= 0)
    {
        return;
    }

    // Check if this post has any critical rolls
    $query = $db->simple_select('dice_rolls', 'is_crit', "pid = {$pid} AND is_crit != 0", array('limit' => 10));

    $has_crit = false;
    $has_fail = false;

    while($roll = $db->fetch_array($query))
    {
        if($roll['is_crit'] == 1)
        {
            $has_crit = true;
        }
        elseif($roll['is_crit'] == -1)
        {
            $has_fail = true;
        }
    }

    // Add CSS classes
    if($has_crit && $has_fail)
    {
        $post['post_css_class'] = (isset($post['post_css_class']) ? $post['post_css_class'] . ' ' : '') . 'post-dice-mixed';
    }
    elseif($has_crit)
    {
        $post['post_css_class'] = (isset($post['post_css_class']) ? $post['post_css_class'] . ' ' : '') . 'post-dice-crit';
    }
    elseif($has_fail)
    {
        $post['post_css_class'] = (isset($post['post_css_class']) ? $post['post_css_class'] . ' ' : '') . 'post-dice-fail';
    }
}

/**
 * Hook: Inject CSS styles into page head
 */
function dice_roller_global_start()
{
    global $mybb, $headerinclude;

    // CSS for dice roll display and post effects
    $css = '<style type="text/css">
/* Dice Roll Result Styling */
.dice-roll {
    display: inline-block;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: #eee;
    padding: 4px 10px;
    border-radius: 6px;
    font-family: "Segoe UI", Tahoma, sans-serif;
    font-size: 0.95em;
    margin: 2px 0;
    border: 1px solid #0f3460;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.dice-label {
    color: #a0a0a0;
    font-style: italic;
    margin-right: 4px;
}
.dice-notation {
    color: #00d9ff;
    font-weight: bold;
}
.dice-breakdown {
    color: #888;
    margin: 0 6px;
}
.dice-modifier {
    color: #ffa500;
}
.dice-equals {
    color: #666;
    margin: 0 4px;
}
.dice-total {
    color: #00ff88;
    font-weight: bold;
    font-size: 1.1em;
}

/* Critical Success (Natural 20) */
.dice-crit-success {
    background: linear-gradient(135deg, #1a472a 0%, #0d3320 100%);
    border-color: #00ff88;
    box-shadow: 0 0 10px rgba(0, 255, 136, 0.3);
}
.dice-nat20 {
    color: #00ff88;
    text-shadow: 0 0 8px rgba(0, 255, 136, 0.5);
}
.dice-crit-text {
    display: inline-block;
    background: #00ff88;
    color: #000;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.75em;
    font-weight: bold;
    margin-left: 6px;
    animation: pulse-green 1s ease-in-out infinite;
}

/* Critical Fail (Natural 1) */
.dice-crit-fail {
    background: linear-gradient(135deg, #4a1a1a 0%, #331010 100%);
    border-color: #ff4444;
    box-shadow: 0 0 10px rgba(255, 68, 68, 0.3);
}
.dice-nat1 {
    color: #ff4444;
    text-shadow: 0 0 8px rgba(255, 68, 68, 0.5);
}
.dice-crit-fail .dice-crit-text {
    background: #ff4444;
    animation: pulse-red 1s ease-in-out infinite;
}

/* Error styling */
.dice-error {
    color: #ff6b6b;
    background: #2a1515;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.9em;
}

/* Post-level CSS effects for crits */
.post-dice-crit {
    box-shadow: inset 0 0 20px rgba(0, 255, 136, 0.1), 0 0 15px rgba(0, 255, 136, 0.1);
    border-left: 3px solid #00ff88 !important;
}
.post-dice-fail {
    box-shadow: inset 0 0 20px rgba(255, 68, 68, 0.1), 0 0 15px rgba(255, 68, 68, 0.1);
    border-left: 3px solid #ff4444 !important;
}
.post-dice-mixed {
    box-shadow: inset 0 0 20px rgba(255, 165, 0, 0.1);
    border-left: 3px solid #ffa500 !important;
}

/* Animations */
@keyframes pulse-green {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
@keyframes pulse-red {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
</style>';

    $headerinclude .= $css;
}
