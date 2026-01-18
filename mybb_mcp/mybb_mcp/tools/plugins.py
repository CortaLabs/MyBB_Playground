"""Plugin development tools for MyBB MCP Server."""

from pathlib import Path
from typing import Any

from ..config import MyBBConfig


# ==================== Hooks Reference ====================

HOOKS_REFERENCE = {
    "index": ["index_start", "index_end", "build_forumbits_forum"],
    "showthread": ["showthread_start", "showthread_end", "postbit", "postbit_prev", "postbit_pm", "postbit_author", "postbit_signature"],
    "member": ["member_profile_start", "member_profile_end", "member_register_start", "member_register_end", "member_do_register_start", "member_do_register_end"],
    "usercp": ["usercp_start", "usercp_menu", "usercp_options_start", "usercp_options_end", "usercp_profile_start", "usercp_profile_end"],
    "forumdisplay": ["forumdisplay_start", "forumdisplay_end", "forumdisplay_thread"],
    "newthread": ["newthread_start", "newthread_end", "newthread_do_newthread_start", "newthread_do_newthread_end"],
    "newreply": ["newreply_start", "newreply_end", "newreply_do_newreply_start", "newreply_do_newreply_end"],
    "modcp": ["modcp_start", "modcp_nav"],
    "admin": ["admin_home_menu", "admin_config_menu", "admin_forum_menu", "admin_user_menu", "admin_tools_menu", "admin_style_menu", "admin_config_settings_change", "admin_config_plugins_begin"],
    "global": ["global_start", "global_end", "global_intermediate", "fetch_wol_activity_end", "build_friendly_wol_location_end", "redirect", "error", "no_permission"],
    "misc": ["misc_start", "xmlhttp"],
    "datahandler": ["datahandler_post_insert_post", "datahandler_post_insert_thread", "datahandler_post_update", "datahandler_user_insert", "datahandler_user_update"],
}


def get_hooks_reference(category: str | None = None, search: str | None = None) -> str:
    """Get formatted hooks reference."""
    lines = ["# MyBB Hooks Reference\n"]

    if category and category.lower() in HOOKS_REFERENCE:
        cat = category.lower()
        lines.append(f"## {cat.title()} Hooks\n")
        for h in HOOKS_REFERENCE[cat]:
            if not search or search.lower() in h:
                lines.append(f"- `{h}`")
    elif search:
        search_lower = search.lower()
        lines.append(f"## Hooks matching '{search}'\n")
        for cat, hooks in HOOKS_REFERENCE.items():
            matching = [h for h in hooks if search_lower in h]
            if matching:
                lines.append(f"### {cat.title()}")
                for h in matching:
                    lines.append(f"- `{h}`")
    else:
        for cat, hooks in HOOKS_REFERENCE.items():
            lines.append(f"### {cat.title()}")
            for h in hooks[:5]:
                lines.append(f"- `{h}`")
            if len(hooks) > 5:
                lines.append(f"  *...and {len(hooks) - 5} more*")

    lines.append("\n---")
    lines.append("*Full list: https://docs.mybb.com/1.8/development/plugins/hooks/*")
    return "\n".join(lines)


# ==================== Plugin Template ====================

PLUGIN_TEMPLATE = '''<?php
/**
 * {plugin_name}
 * {description}
 *
 * @author {author}
 * @version {version}
 */

// Prevent direct access
if(!defined('IN_MYBB'))
{{
    die('This file cannot be accessed directly.');
}}

{template_caching}

{hooks}

/**
 * Plugin information
 */
function {codename}_info()
{{
    return array(
        'name'          => '{plugin_name}',
        'description'   => '{description}',
        'website'       => '{website}',
        'author'        => '{author}',
        'authorsite'    => '{author_site}',
        'version'       => '{version}',
        'compatibility' => '18*',
        'codename'      => '{codename}'
    );
}}

/**
 * Plugin activation
 */
function {codename}_activate()
{{
    global $db;

{activate_code}
}}

/**
 * Plugin deactivation
 */
function {codename}_deactivate()
{{
    global $db;

{deactivate_code}
}}

/**
 * Check if plugin is installed
 */
function {codename}_is_installed()
{{
    global $db;
    {is_installed_check}
}}

/**
 * Plugin installation
 */
function {codename}_install()
{{
    global $db;

{install_code}
}}

/**
 * Plugin uninstallation
 */
function {codename}_uninstall()
{{
    global $db;

{uninstall_code}
}}

{hook_functions}
'''

LANG_TEMPLATE = '''<?php
/**
 * {plugin_name} - Language File
 */

$l['{codename}_name'] = '{plugin_name}';
$l['{codename}_desc'] = '{description}';

// Add your language strings below
'''


def create_plugin(args: dict[str, Any], config: MyBBConfig) -> str:
    """Create a new MyBB plugin with proper structure."""
    plugins_dir = config.mybb_root / "inc" / "plugins"

    codename = args.get("codename", "").lower().replace(" ", "_")
    plugin_name = args.get("name", "")
    description = args.get("description", "")
    author = args.get("author", "Developer")
    version = args.get("version", "1.0.0")
    hooks = args.get("hooks", [])
    has_settings = args.get("has_settings", False)
    has_templates = args.get("has_templates", False)
    has_database = args.get("has_database", False)

    if not codename or not plugin_name:
        return "Error: 'codename' and 'name' are required."

    # Generate hook registrations
    hook_lines = []
    hook_functions = []

    for hook in hooks:
        hook_lines.append(f"$plugins->add_hook('{hook}', '{codename}_{hook}');")
        hook_functions.append(f'''
/**
 * Hook: {hook}
 */
function {codename}_{hook}(&$args)
{{
    global $mybb, $db, $templates, $lang;

    // Your hook code here

    // For form submissions, verify CSRF token:
    // verify_post_check($mybb->get_input('my_post_key'));
}}
''')

    hooks_code = "\n".join(hook_lines) if hook_lines else "// No hooks registered"
    hook_funcs_code = "\n".join(hook_functions) if hook_functions else ""

    # Template caching
    template_cache = ""
    if has_templates:
        template_cache = f'''// Cache templates
if(defined('THIS_SCRIPT'))
{{
    global $templatelist;
    if(isset($templatelist))
    {{
        $templatelist .= ',';
    }}
    $templatelist .= '{codename}_main';
}}'''

    # Activation code
    activate_parts = []
    if has_templates:
        activate_parts.append(f'''    // Add templates
    $template = array(
        'title' => '{codename}_main',
        'template' => '<div class="{codename}-container">{{$content}}</div>',
        'sid' => -2,
        'version' => '',
        'dateline' => TIME_NOW
    );
    $db->insert_query('templates', $template);''')

    activate_code = "\n".join(activate_parts) if activate_parts else "    // Nothing to activate"

    # Deactivation code
    deactivate_code = "    // Nothing to deactivate"
    if has_templates:
        deactivate_code = f'''    // Remove template edits if any
    require_once MYBB_ROOT.'inc/adminfunctions_templates.php';
    // find_replace_templatesets('index', '#'.preg_quote('{{${codename}}}').'#', '');'''

    # Install code
    install_parts = []
    if has_settings:
        install_parts.append(f'''    // Add settings group
    $group = array(
        'name' => '{codename}',
        'title' => '{plugin_name}',
        'description' => '{description}',
        'disporder' => 100,
        'isdefault' => 0
    );
    $gid = $db->insert_query('settinggroups', $group);

    // Add settings
    $setting = array(
        'name' => '{codename}_enabled',
        'title' => 'Enable {plugin_name}',
        'description' => 'Enable or disable this plugin.',
        'optionscode' => 'yesno',
        'value' => '1',
        'disporder' => 1,
        'gid' => $gid
    );
    $db->insert_query('settings', $setting);

    rebuild_settings();''')

    if has_database:
        install_parts.append(f'''    // Create database table with multi-DB support
    $collation = $db->build_create_table_collation();

    if(!$db->table_exists('{codename}_data')) {{
        switch($db->type) {{
            case "pgsql":
                $db->write_query("CREATE TABLE ".TABLE_PREFIX."{codename}_data (
                    id serial,
                    uid int NOT NULL default 0,
                    data text,
                    dateline int NOT NULL default 0,
                    PRIMARY KEY (id)
                );");
                break;
            case "sqlite":
                $db->write_query("CREATE TABLE ".TABLE_PREFIX."{codename}_data (
                    id INTEGER PRIMARY KEY,
                    uid INTEGER NOT NULL default 0,
                    data TEXT,
                    dateline INTEGER NOT NULL default 0
                );");
                break;
            default:  // MySQL/MariaDB
                $db->write_query("CREATE TABLE ".TABLE_PREFIX."{codename}_data (
                    id int unsigned NOT NULL auto_increment,
                    uid int unsigned NOT NULL default 0,
                    data text,
                    dateline int unsigned NOT NULL default 0,
                    PRIMARY KEY (id)
                ) ENGINE=MyISAM{{$collation}};");
                break;
        }}
    }}''')

    install_code = "\n".join(install_parts) if install_parts else "    // Nothing to install"

    # Uninstall code
    uninstall_parts = []
    if has_templates:
        uninstall_parts.append(f"    $db->delete_query('templates', \"title LIKE '{codename}%'\");")
    if has_settings:
        uninstall_parts.append(f"    $db->delete_query('settinggroups', \"name='{codename}'\");")
        uninstall_parts.append(f"    $db->delete_query('settings', \"name LIKE '{codename}%'\");")
        uninstall_parts.append("    rebuild_settings();")
    if has_database:
        uninstall_parts.append(f"    $db->drop_table('{codename}_data');")

    uninstall_code = "\n".join(uninstall_parts) if uninstall_parts else "    // Nothing to uninstall"

    # Is installed check
    if has_database:
        is_installed = f"return $db->table_exists('{codename}_data');"
    elif has_settings:
        is_installed = f"$query = $db->simple_select('settinggroups', 'gid', \"name='{codename}'\");\n    return (bool)$db->num_rows($query);"
    else:
        is_installed = "return false; // No installation required"

    # Generate plugin file
    plugin_content = PLUGIN_TEMPLATE.format(
        codename=codename,
        plugin_name=plugin_name,
        description=description,
        author=author,
        author_site="",
        website="",
        version=version,
        template_caching=template_cache,
        hooks=hooks_code,
        activate_code=activate_code,
        deactivate_code=deactivate_code,
        install_code=install_code,
        uninstall_code=uninstall_code,
        is_installed_check=is_installed,
        hook_functions=hook_funcs_code,
    )

    # Write plugin file
    plugin_path = plugins_dir / f"{codename}.php"
    plugin_path.write_text(plugin_content, encoding='utf-8')

    # Create language file
    lang_dir = config.mybb_root / "inc" / "languages" / "english"
    lang_created = False
    if lang_dir.exists():
        lang_content = LANG_TEMPLATE.format(
            codename=codename,
            plugin_name=plugin_name,
            description=description,
        )
        lang_path = lang_dir / f"{codename}.lang.php"
        lang_path.write_text(lang_content, encoding='utf-8')
        lang_created = True

    lines = [
        f"# Plugin Created: {plugin_name}",
        "",
        f"**Plugin file**: `{plugin_path}`",
    ]

    if lang_created:
        lines.append(f"**Language file**: `{lang_dir / f'{codename}.lang.php'}`")

    lines.extend([
        "",
        "## Features",
        f"- Hooks: {', '.join(hooks) if hooks else 'None'}",
        f"- Settings: {'Yes' if has_settings else 'No'}",
        f"- Templates: {'Yes' if has_templates else 'No'}",
        f"- Database: {'Yes' if has_database else 'No'}",
        "",
        "## Next Steps",
        "1. Go to ACP > Configuration > Plugins",
        "2. Install and activate the plugin",
        "3. Edit the plugin file to add your functionality",
    ])

    return "\n".join(lines)
