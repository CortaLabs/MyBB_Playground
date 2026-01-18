"""Expanded hook system with dynamic discovery for MyBB MCP Server."""

import re
from pathlib import Path


# Expanded hooks reference with 180+ hooks from research
HOOKS_REFERENCE_EXPANDED = {
    # Global hooks - run on every page
    "global": [
        "global_start", "global_intermediate", "global_end",
        "fetch_wol_activity_end", "build_friendly_wol_location_end",
        "redirect", "error", "no_permission",
        "pre_parse_page", "pre_output_page", "post_output_page"
    ],

    # Index page hooks
    "index": ["index_start", "index_end", "build_forumbits_forum"],

    # Thread display hooks
    "showthread": [
        "showthread_start", "showthread_end",
        "postbit", "postbit_prev", "postbit_pm", "postbit_author", "postbit_signature",
        "postbit_announcement"
    ],

    # Member profile and registration hooks
    "member": [
        "member_profile_start", "member_profile_end",
        "member_register_start", "member_register_end",
        "member_do_register_start", "member_do_register_end",
        "member_login", "member_do_login_start", "member_do_login_end", "member_login_end",
        "member_logout_start", "member_logout_end",
        "member_lostpw", "member_do_lostpw_start", "member_do_lostpw_end",
        "member_activate_start", "member_activate_emailupdated", "member_activate_accountactivated"
    ],

    # User Control Panel hooks
    "usercp": [
        "usercp_start", "usercp_menu", "usercp_end",
        "usercp_options_start", "usercp_options_end",
        "usercp_do_options_start", "usercp_do_options_end",
        "usercp_profile_start", "usercp_profile_end",
        "usercp_do_profile_start", "usercp_do_profile_end",
        "usercp_email", "usercp_do_email_start", "usercp_do_email_changed", "usercp_do_email_verify",
        "usercp_password", "usercp_do_password_start", "usercp_do_password_end",
        "usercp_editsig_start", "usercp_editsig_process", "usercp_editsig_end",
        "usercp_avatar_start", "usercp_avatar_intermediate", "usercp_avatar_end",
        "usercp_do_avatar_start", "usercp_do_avatar_end",
        "usercp_subscriptions_start", "usercp_subscriptions_end",
        "usercp_forumsubscriptions_start", "usercp_forumsubscriptions_end",
        "usercp_usergroups_start", "usercp_usergroups_end",
        "usercp_attachments_start", "usercp_attachments_end",
        "usercp_do_attachments_start", "usercp_do_attachments_end",
        "usercp_drafts_start", "usercp_drafts_end",
        "usercp_do_drafts_start", "usercp_do_drafts_end",
        "usercp_editlists_start", "usercp_editlists_end",
        "usercp_do_editlists_start", "usercp_do_editlists_end"
    ],

    # Forum display hooks
    "forumdisplay": [
        "forumdisplay_start", "forumdisplay_end",
        "forumdisplay_announcement", "forumdisplay_get_threads",
        "forumdisplay_before_thread", "forumdisplay_thread", "forumdisplay_thread_end",
        "forumdisplay_threadlist"
    ],

    # New thread hooks
    "newthread": [
        "newthread_start", "newthread_end",
        "newthread_do_newthread_start", "newthread_do_newthread_end"
    ],

    # New reply hooks
    "newreply": [
        "newreply_start", "newreply_end",
        "newreply_do_newreply_start", "newreply_do_newreply_end",
        "newreply_threadreview_post"
    ],

    # Edit post hooks
    "editpost": [
        "editpost_start", "editpost_end",
        "editpost_action_start",
        "editpost_deletepost", "editpost_restorepost",
        "editpost_do_editpost_start", "editpost_do_editpost_end"
    ],

    # Moderator Control Panel hooks
    "modcp": [
        "modcp_start", "modcp_nav", "modcp_end",
        "modcp_reports_start", "modcp_reports_intermediate", "modcp_reports_report", "modcp_reports_end",
        "modcp_allreports_start", "modcp_allreports_report", "modcp_allreports_end",
        "modcp_do_reports",
        "modcp_modqueue_threads_end", "modcp_modqueue_posts_end", "modcp_modqueue_attachments_end",
        "modcp_do_modqueue_start", "modcp_do_modqueue_end",
        "modcp_new_announcement", "modcp_do_new_announcement_start", "modcp_do_new_announcement_end",
        "modcp_edit_announcement", "modcp_do_edit_announcement_start", "modcp_do_edit_announcement_end",
        "modcp_delete_announcement", "modcp_do_delete_announcement",
        "modcp_editprofile_start", "modcp_editprofile_end",
        "modcp_do_editprofile_start", "modcp_do_editprofile_update", "modcp_do_editprofile_end",
        "modcp_finduser_start", "modcp_finduser_end",
        "modcp_banning", "modcp_banuser_start", "modcp_banuser_end",
        "modcp_do_banuser_start", "modcp_do_banuser_end",
        "modcp_liftban_start", "modcp_liftban_end",
        "modcp_ipsearch_posts_start", "modcp_ipsearch_users_start", "modcp_ipsearch_end",
        "modcp_iplookup_end",
        "modcp_modlogs_start", "modcp_modlogs_result", "modcp_modlogs_filter",
        "modcp_warninglogs_start", "modcp_warninglogs_end",
        "modcp_do_modnotes_start", "modcp_do_modnotes_end"
    ],

    # Admin Control Panel hooks
    "admin": [
        "admin_home_menu", "admin_config_menu", "admin_forum_menu",
        "admin_user_menu", "admin_tools_menu", "admin_style_menu",
        "admin_config_settings_change", "admin_config_plugins_begin",
        "admin_login", "admin_login_success", "admin_login_fail",
        "admin_login_incorrect_pin", "admin_login_lockout",
        "admin_unlock_start", "admin_unlock_end",
        "admin_logout",
        "admin_tabs", "admin_load"
    ],

    # Parser hooks - message content processing
    "parser": [
        "parse_message_start", "parse_message_htmlsanitized",
        "parse_message_me_mycode", "parse_message",
        "parse_message_end", "text_parse_message"
    ],

    # Moderation class hooks - thread/post operations
    "moderation": [
        "class_moderation_close_threads", "class_moderation_open_threads",
        "class_moderation_stick_threads", "class_moderation_unstick_threads",
        "class_moderation_remove_redirects",
        "class_moderation_delete_thread_start", "class_moderation_delete_thread",
        "class_moderation_delete_poll",
        "class_moderation_approve_threads", "class_moderation_unapprove_threads"
    ],

    # Datahandler hooks - data validation and insertion
    "datahandler": [
        # Post datahandler
        "datahandler_post_validate_post", "datahandler_post_validate_thread",
        "datahandler_post_insert_merge",
        "datahandler_post_insert_post", "datahandler_post_insert_post_end",
        "datahandler_post_insert_thread", "datahandler_post_insert_thread_post",
        "datahandler_post_insert_subscribed",
        "datahandler_post_update",
        # User datahandler
        "datahandler_user_validate",
        "datahandler_user_insert", "datahandler_user_insert_end",
        "datahandler_user_update",
        "datahandler_user_delete_start", "datahandler_user_delete_end",
        "datahandler_user_delete_content", "datahandler_user_delete_posts",
        "datahandler_user_clear_profile"
    ],

    # Email system hooks
    "email": [
        "send_mail_queue_start", "send_mail_queue_end",
        "my_mailhandler_builtin_after_init", "my_mailhandler_init",
        "my_mail_pre_build_message", "my_mail_pre_send"
    ],

    # Miscellaneous hooks
    "misc": ["misc_start", "xmlhttp", "my_date"]
}


def discover_hooks(mybb_root: Path, path: str | None = None, category: str | None = None, search: str | None = None) -> str:
    """
    Dynamically discover hooks in MyBB PHP files by scanning for $plugins->run_hooks() calls.

    Args:
        mybb_root: Path to MyBB installation root
        path: Specific PHP file to scan (relative to mybb_root)
        category: Filter by category (e.g., 'admin', 'usercp')
        search: Search term to filter hook names

    Returns:
        Formatted markdown table of discovered hooks
    """
    hooks_found = []

    # Determine which files to scan
    if path:
        files_to_scan = [mybb_root / path]
    else:
        # Scan all PHP files
        files_to_scan = list(mybb_root.glob("*.php"))
        files_to_scan.extend(mybb_root.glob("inc/**/*.php"))
        files_to_scan.extend(mybb_root.glob("admin/**/*.php"))

    # Regex pattern for $plugins->run_hooks('hook_name', ...)
    hook_pattern = re.compile(r'\$plugins\->run_hooks\(["\']([^"\']+)["\']')

    for file_path in files_to_scan:
        if not file_path.exists() or not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            relative_path = file_path.relative_to(mybb_root)

            for line_num, line in enumerate(content.split('\n'), 1):
                matches = hook_pattern.findall(line)
                for hook_name in matches:
                    # Apply filters
                    if category and not hook_name.startswith(category):
                        continue
                    if search and search.lower() not in hook_name.lower():
                        continue

                    hooks_found.append({
                        'hook': hook_name,
                        'file': str(relative_path),
                        'line': line_num
                    })
        except Exception:
            continue

    # Remove duplicates and sort
    unique_hooks = {}
    for hook_info in hooks_found:
        key = hook_info['hook']
        if key not in unique_hooks:
            unique_hooks[key] = hook_info

    sorted_hooks = sorted(unique_hooks.values(), key=lambda x: x['hook'])

    # Format output
    if not sorted_hooks:
        return "No hooks found matching the criteria."

    lines = [
        f"# Discovered {len(sorted_hooks)} MyBB Hooks\n",
        "| Hook Name | File | Line |",
        "|-----------|------|------|"
    ]

    for hook_info in sorted_hooks:
        lines.append(f"| `{hook_info['hook']}` | {hook_info['file']} | {hook_info['line']} |")

    return "\n".join(lines)


def find_hook_usage(mybb_root: Path, hook_name: str) -> str:
    """
    Find where a hook is used in installed plugins.

    Args:
        mybb_root: Path to MyBB installation root
        hook_name: Name of the hook to search for

    Returns:
        Formatted markdown list of plugins using this hook
    """
    plugins_dir = mybb_root / "inc" / "plugins"
    usage_found = []

    if not plugins_dir.exists():
        return f"Plugins directory not found: {plugins_dir}"

    # Regex pattern for $plugins->add_hook('hook_name', 'function', priority)
    add_hook_pattern = re.compile(
        rf'\$plugins\->add_hook\(["\']({re.escape(hook_name)})["\'],\s*["\']([^"\']+)["\'](?:,\s*(\d+))?'
    )

    for plugin_file in plugins_dir.glob("*.php"):
        try:
            content = plugin_file.read_text(encoding='utf-8', errors='ignore')

            for line_num, line in enumerate(content.split('\n'), 1):
                match = add_hook_pattern.search(line)
                if match:
                    function_name = match.group(2)
                    priority = match.group(3) or "10"

                    usage_found.append({
                        'plugin': plugin_file.stem,
                        'function': function_name,
                        'priority': priority,
                        'line': line_num
                    })
        except Exception:
            continue

    # Format output
    if not usage_found:
        return f"Hook `{hook_name}` is not used by any installed plugins."

    lines = [
        f"# Hook Usage: `{hook_name}`\n",
        f"Found {len(usage_found)} usage(s) in installed plugins:\n"
    ]

    for usage in sorted(usage_found, key=lambda x: (x['plugin'], int(x['priority']))):
        lines.append(f"### {usage['plugin']}.php")
        lines.append(f"- **Function**: `{usage['function']}`")
        lines.append(f"- **Priority**: {usage['priority']}")
        lines.append(f"- **Line**: {usage['line']}\n")

    return "\n".join(lines)
