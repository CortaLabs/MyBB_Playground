"""Tool definitions for MyBB MCP server.

This module contains all 85+ tool definitions for the MyBB MCP server.
Tools are organized by category and exported as ALL_TOOLS list.
"""

from mcp.types import Tool


# ==================== Template Tools ====================

TEMPLATE_TOOLS = [
    Tool(
        name="mybb_list_template_sets",
        description="List all MyBB template sets. Template sets are collections of templates for a theme.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="mybb_list_templates",
        description="List templates. Filter by set ID (sid) or search term. sid=-2 for master templates, sid=-1 for global.",
        inputSchema={
            "type": "object",
            "properties": {
                "sid": {"type": "integer", "description": "Template set ID. Use -2 for master, -1 for global."},
                "search": {"type": "string", "description": "Search term for template names."},
            },
        },
    ),
    Tool(
        name="mybb_read_template",
        description="Read a template's HTML content. Shows both master and custom version if exists.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Template title to read."},
                "sid": {"type": "integer", "description": "Template set ID (default checks master and custom)."},
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="mybb_write_template",
        description="Update or create a template. Handles inheritance automatically.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Template title."},
                "template": {"type": "string", "description": "Template HTML content."},
                "sid": {"type": "integer", "description": "Template set ID. Use -2 for master, positive for specific set.", "default": 1},
            },
            "required": ["title", "template"],
        },
    ),
    Tool(
        name="mybb_list_template_groups",
        description="List template groups for organization (calendar, forum, usercp, etc.).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="mybb_template_find_replace",
        description="Perform find/replace across template sets (mirrors MyBB's find_replace_templatesets()). Most common plugin operation for template modification.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Template title to modify."},
                "find": {"type": "string", "description": "String or regex pattern to find."},
                "replace": {"type": "string", "description": "Replacement string."},
                "template_sets": {"type": "array", "items": {"type": "integer"}, "description": "List of template set IDs to modify, or empty for all sets."},
                "regex": {"type": "boolean", "description": "Use regex mode (default: True).", "default": True},
                "limit": {"type": "integer", "description": "Maximum replacements per template (-1 for unlimited).", "default": -1},
            },
            "required": ["title", "find", "replace"],
        },
    ),
    Tool(
        name="mybb_template_batch_read",
        description="Read multiple templates in one call for efficiency.",
        inputSchema={
            "type": "object",
            "properties": {
                "templates": {"type": "array", "items": {"type": "string"}, "description": "List of template names to read."},
                "sid": {"type": "integer", "description": "Template set ID (default -2 for master).", "default": -2},
            },
            "required": ["templates"],
        },
    ),
    Tool(
        name="mybb_template_batch_write",
        description="Write multiple templates in one call. Operation is atomic (all or nothing).",
        inputSchema={
            "type": "object",
            "properties": {
                "templates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "template": {"type": "string"},
                        },
                        "required": ["title", "template"],
                    },
                    "description": "List of templates to write with title and template content.",
                },
                "sid": {"type": "integer", "description": "Template set ID for all templates.", "default": 1},
            },
            "required": ["templates"],
        },
    ),
    Tool(
        name="mybb_template_outdated",
        description="Find templates that differ from master (outdated after MyBB upgrade). Compares version numbers.",
        inputSchema={
            "type": "object",
            "properties": {
                "sid": {"type": "integer", "description": "Template set ID to check for outdated templates."},
            },
            "required": ["sid"],
        },
    ),
]


# ==================== Theme/Style Tools ====================

THEME_TOOLS = [
    Tool(
        name="mybb_list_themes",
        description="List all MyBB themes.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="mybb_list_stylesheets",
        description="List stylesheets, optionally for a specific theme.",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Theme ID to filter by."},
            },
        },
    ),
    Tool(
        name="mybb_read_stylesheet",
        description="Read a stylesheet's CSS content.",
        inputSchema={
            "type": "object",
            "properties": {
                "sid": {"type": "integer", "description": "Stylesheet ID."},
            },
            "required": ["sid"],
        },
    ),
    Tool(
        name="mybb_write_stylesheet",
        description="Update a stylesheet's CSS and refresh cache.",
        inputSchema={
            "type": "object",
            "properties": {
                "sid": {"type": "integer", "description": "Stylesheet ID."},
                "stylesheet": {"type": "string", "description": "New CSS content."},
            },
            "required": ["sid", "stylesheet"],
        },
    ),
    Tool(
        name="mybb_create_theme",
        description="Create a new MyBB theme with proper structure in plugin_manager workspace.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {
                    "type": "string",
                    "description": "Theme codename (lowercase, underscores)"
                },
                "name": {
                    "type": "string",
                    "description": "Theme display name"
                },
                "description": {
                    "type": "string",
                    "description": "Theme description"
                },
                "author": {
                    "type": "string",
                    "description": "Author name"
                },
                "version": {
                    "type": "string",
                    "description": "Version (default: 1.0.0)"
                },
                "parent_theme": {
                    "type": "string",
                    "description": "Parent theme name to inherit from"
                },
                "stylesheets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of stylesheet names to create"
                }
            },
            "required": ["codename", "name"]
        }
    ),
]


# ==================== Plugin Tools ====================

PLUGIN_TOOLS = [
    Tool(
        name="mybb_list_plugins",
        description="List plugins in the MyBB plugins directory.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="mybb_read_plugin",
        description="Read a plugin's PHP source code.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Plugin filename (without .php)."},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="mybb_create_plugin",
        description="Create a new MyBB plugin in the plugin_manager workspace with proper structure, hooks, settings, templates, and database tables.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin codename (lowercase, underscores)."},
                "name": {"type": "string", "description": "Plugin display name."},
                "description": {"type": "string", "description": "Plugin description."},
                "author": {"type": "string", "description": "Author name.", "default": "Developer"},
                "version": {"type": "string", "description": "Version.", "default": "1.0.0"},
                "visibility": {"type": "string", "enum": ["public", "private"], "description": "Visibility: 'public' (shareable) or 'private' (personal).", "default": "public"},
                "hooks": {"type": "array", "items": {"type": "string"}, "description": "Hooks to attach (e.g., 'index_start', 'postbit')."},
                "has_settings": {"type": "boolean", "description": "Create ACP settings.", "default": False},
                "has_templates": {"type": "boolean", "description": "Create templates.", "default": False},
                "has_database": {"type": "boolean", "description": "Create database table.", "default": False},
            },
            "required": ["codename", "name", "description"],
        },
    ),
    Tool(
        name="mybb_delete_plugin",
        description="Permanently delete a plugin from workspace and database. Archives by default (can be recovered). Use force=True for installed plugins.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin codename to delete."},
                "archive": {"type": "boolean", "description": "Archive workspace instead of deleting (default: True).", "default": True},
                "force": {"type": "boolean", "description": "Force deletion of installed plugins (will uninstall first).", "default": False},
            },
            "required": ["codename"],
        },
    ),
    Tool(
        name="mybb_delete_theme",
        description="Permanently delete a theme from workspace and database. Archives by default (can be recovered). Use force=True for installed themes.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Theme codename to delete."},
                "archive": {"type": "boolean", "description": "Archive workspace instead of deleting (default: True).", "default": True},
                "force": {"type": "boolean", "description": "Force deletion of installed themes (will uninstall first).", "default": False},
            },
            "required": ["codename"],
        },
    ),
    Tool(
        name="mybb_list_hooks",
        description="List available MyBB hooks for plugin development.",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category: index, showthread, member, admin, global, etc."},
                "search": {"type": "string", "description": "Search term."},
            },
        },
    ),
    Tool(
        name="mybb_hooks_discover",
        description="Dynamically discover hooks in MyBB installation by scanning PHP files for $plugins->run_hooks() calls.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Specific PHP file to scan (optional, relative to MyBB root)."},
                "category": {"type": "string", "description": "Filter by category prefix (e.g., 'admin', 'usercp')."},
                "search": {"type": "string", "description": "Search term to filter hook names."},
            },
        },
    ),
    Tool(
        name="mybb_hooks_usage",
        description="Find where a hook is used in installed plugins by scanning for $plugins->add_hook() calls.",
        inputSchema={
            "type": "object",
            "properties": {
                "hook_name": {"type": "string", "description": "Name of the hook to search for."},
            },
            "required": ["hook_name"],
        },
    ),
    Tool(
        name="mybb_analyze_plugin",
        description="Analyze an existing plugin's structure, hooks, settings, and templates.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Plugin filename (without .php)."},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="mybb_plugin_list_installed",
        description="List installed/active plugins from datacache.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="mybb_plugin_info",
        description="Get plugin info by reading the _info() function from plugin file.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Plugin codename (without .php)."},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="mybb_plugin_activate",
        description="Activate a plugin by adding it to the active plugins cache. Note: This does NOT execute the PHP _activate() function - that must be done through MyBB's admin panel.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Plugin codename to activate."},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="mybb_plugin_deactivate",
        description="Deactivate a plugin by removing it from the active plugins cache. Note: This does NOT execute the PHP _deactivate() function - that must be done through MyBB's admin panel.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Plugin codename to deactivate."},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="mybb_plugin_is_installed",
        description="Check if a plugin is currently installed/active.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Plugin codename to check."},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="mybb_plugin_install",
        description="Full plugin installation: deploy files from workspace AND execute PHP lifecycle (_install, _activate). This runs the actual PHP code, unlike mybb_plugin_activate which only updates the cache.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin codename (without .php)."},
                "force": {"type": "boolean", "description": "Skip MyBB compatibility check.", "default": False},
            },
            "required": ["codename"],
        },
    ),
    Tool(
        name="mybb_plugin_uninstall",
        description="Full plugin uninstallation: execute PHP lifecycle (_deactivate, optionally _uninstall) AND optionally remove files. This runs the actual PHP code.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin codename (without .php)."},
                "uninstall": {"type": "boolean", "description": "Also run _uninstall() to remove settings/tables.", "default": False},
                "remove_files": {"type": "boolean", "description": "Also remove plugin files from TestForum.", "default": False},
            },
            "required": ["codename"],
        },
    ),
    Tool(
        name="mybb_plugin_status",
        description="Get comprehensive plugin status via PHP bridge: installation state, activation state, compatibility, and plugin info.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin codename (without .php)."},
            },
            "required": ["codename"],
        },
    ),
]


# ==================== Scheduled Task Tools ====================

TASK_TOOLS = [
    Tool(
        name="mybb_task_list",
        description="List all scheduled tasks.",
        inputSchema={
            "type": "object",
            "properties": {
                "enabled_only": {"type": "boolean", "description": "Only show enabled tasks.", "default": False},
            },
        },
    ),
    Tool(
        name="mybb_task_get",
        description="Get detailed information about a specific task.",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Task ID."},
            },
            "required": ["tid"],
        },
    ),
    Tool(
        name="mybb_task_enable",
        description="Enable a scheduled task.",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Task ID to enable."},
            },
            "required": ["tid"],
        },
    ),
    Tool(
        name="mybb_task_disable",
        description="Disable a scheduled task.",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Task ID to disable."},
            },
            "required": ["tid"],
        },
    ),
    Tool(
        name="mybb_task_update_nextrun",
        description="Update the next run time for a task.",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Task ID."},
                "nextrun": {"type": "integer", "description": "Unix timestamp for next execution."},
            },
            "required": ["tid", "nextrun"],
        },
    ),
    Tool(
        name="mybb_task_run_log",
        description="View task execution history.",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Optional task ID to filter by."},
                "limit": {"type": "integer", "description": "Maximum log entries to return (max 500).", "default": 50},
            },
        },
    ),
]


# ==================== Database Query Tool ====================

DATABASE_TOOLS = [
    Tool(
        name="mybb_db_query",
        description="Execute a read-only SQL query against MyBB database. For exploration only.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL SELECT query."},
            },
            "required": ["query"],
        },
    ),
]


# ==================== Content CRUD Tools ====================
# Forum, Thread, and Post management

CONTENT_TOOLS = [
    # Forum Management
    Tool(
        name="mybb_forum_list",
        description="List all forums with hierarchy information.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="mybb_forum_read",
        description="Get forum details by fid.",
        inputSchema={
            "type": "object",
            "properties": {
                "fid": {"type": "integer", "description": "Forum ID"},
            },
            "required": ["fid"],
        },
    ),
    Tool(
        name="mybb_forum_create",
        description="Create a new forum or category.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Forum name"},
                "description": {"type": "string", "description": "Forum description", "default": ""},
                "type": {"type": "string", "description": "'f' for forum, 'c' for category", "default": "f"},
                "pid": {"type": "integer", "description": "Parent forum ID", "default": 0},
                "parentlist": {"type": "string", "description": "Comma-separated ancestor path", "default": ""},
                "disporder": {"type": "integer", "description": "Display order", "default": 1},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="mybb_forum_update",
        description="Update forum properties.",
        inputSchema={
            "type": "object",
            "properties": {
                "fid": {"type": "integer", "description": "Forum ID"},
                "name": {"type": "string", "description": "Forum name"},
                "description": {"type": "string", "description": "Forum description"},
                "type": {"type": "string", "description": "'f' for forum, 'c' for category"},
                "disporder": {"type": "integer", "description": "Display order"},
                "active": {"type": "integer", "description": "Is active (0 or 1)"},
                "open": {"type": "integer", "description": "Is open for posting (0 or 1)"},
            },
            "required": ["fid"],
        },
    ),
    Tool(
        name="mybb_forum_delete",
        description="Delete a forum. WARNING: Does not handle content migration. Ensure forum is empty first.",
        inputSchema={
            "type": "object",
            "properties": {
                "fid": {"type": "integer", "description": "Forum ID"},
            },
            "required": ["fid"],
        },
    ),

    # Thread Management
    Tool(
        name="mybb_thread_list",
        description="List threads in a forum with pagination.",
        inputSchema={
            "type": "object",
            "properties": {
                "fid": {"type": "integer", "description": "Forum ID (omit for all threads)"},
                "limit": {"type": "integer", "description": "Maximum threads to return", "default": 50},
                "offset": {"type": "integer", "description": "Number of threads to skip", "default": 0},
            },
        },
    ),
    Tool(
        name="mybb_thread_read",
        description="Get thread details by tid.",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Thread ID"},
            },
            "required": ["tid"],
        },
    ),
    Tool(
        name="mybb_thread_create",
        description="Create a new thread with first post (atomic operation).",
        inputSchema={
            "type": "object",
            "properties": {
                "fid": {"type": "integer", "description": "Forum ID"},
                "subject": {"type": "string", "description": "Thread subject"},
                "message": {"type": "string", "description": "First post content (BBCode)"},
                "uid": {"type": "integer", "description": "Author user ID", "default": 1},
                "username": {"type": "string", "description": "Author username", "default": "Admin"},
                "prefix": {"type": "integer", "description": "Thread prefix ID", "default": 0},
            },
            "required": ["fid", "subject", "message"],
        },
    ),
    Tool(
        name="mybb_thread_update",
        description="Update thread properties (subject, status, prefix).",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Thread ID"},
                "subject": {"type": "string", "description": "New thread subject"},
                "prefix": {"type": "integer", "description": "Thread prefix ID"},
                "closed": {"type": "string", "description": "Closed status"},
                "sticky": {"type": "integer", "description": "Is sticky (0 or 1)"},
                "visible": {"type": "integer", "description": "Visibility (1=visible, 0=unapproved, -1=deleted)"},
            },
            "required": ["tid"],
        },
    ),
    Tool(
        name="mybb_thread_delete",
        description="Delete a thread (soft delete by default, updates counters).",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Thread ID"},
                "soft": {"type": "boolean", "description": "Soft delete (visible=-1) or permanent", "default": True},
            },
            "required": ["tid"],
        },
    ),
    Tool(
        name="mybb_thread_move",
        description="Move thread to a different forum (updates counters).",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Thread ID"},
                "new_fid": {"type": "integer", "description": "New forum ID"},
            },
            "required": ["tid", "new_fid"],
        },
    ),

    # Post Management
    Tool(
        name="mybb_post_list",
        description="List posts in a thread with pagination.",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Thread ID (omit for all posts)"},
                "limit": {"type": "integer", "description": "Maximum posts to return", "default": 50},
                "offset": {"type": "integer", "description": "Number of posts to skip", "default": 0},
            },
        },
    ),
    Tool(
        name="mybb_post_read",
        description="Get post details by pid.",
        inputSchema={
            "type": "object",
            "properties": {
                "pid": {"type": "integer", "description": "Post ID"},
            },
            "required": ["pid"],
        },
    ),
    Tool(
        name="mybb_post_create",
        description="Create a new post in a thread (updates counters).",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Thread ID"},
                "subject": {"type": "string", "description": "Post subject", "default": "RE: {thread subject}"},
                "message": {"type": "string", "description": "Post content (BBCode)"},
                "uid": {"type": "integer", "description": "Author user ID", "default": 1},
                "username": {"type": "string", "description": "Author username", "default": "Admin"},
                "replyto": {"type": "integer", "description": "Parent post ID for threading", "default": 0},
            },
            "required": ["tid", "message"],
        },
    ),
    Tool(
        name="mybb_post_update",
        description="Edit a post (tracks edit history).",
        inputSchema={
            "type": "object",
            "properties": {
                "pid": {"type": "integer", "description": "Post ID"},
                "message": {"type": "string", "description": "New post content (BBCode)"},
                "subject": {"type": "string", "description": "New post subject"},
                "edituid": {"type": "integer", "description": "Editor user ID"},
                "editreason": {"type": "string", "description": "Edit reason text", "default": ""},
            },
            "required": ["pid"],
        },
    ),
    Tool(
        name="mybb_post_delete",
        description="Delete a post (soft delete by default, updates counters).",
        inputSchema={
            "type": "object",
            "properties": {
                "pid": {"type": "integer", "description": "Post ID"},
                "soft": {"type": "boolean", "description": "Soft delete (visible=-1) or permanent", "default": True},
            },
            "required": ["pid"],
        },
    ),
]


# ==================== Disk Sync Tools ====================

SYNC_TOOLS = [
    Tool(
        name="mybb_sync_export_templates",
        description="Export all templates from a template set to disk files.",
        inputSchema={
            "type": "object",
            "properties": {
                "set_name": {"type": "string", "description": "Template set name (e.g., 'Default Templates')"},
            },
            "required": ["set_name"],
        },
    ),
    Tool(
        name="mybb_sync_export_stylesheets",
        description="Export all stylesheets from a theme to disk files.",
        inputSchema={
            "type": "object",
            "properties": {
                "theme_name": {"type": "string", "description": "Theme name (e.g., 'Default')"},
            },
            "required": ["theme_name"],
        },
    ),
    Tool(
        name="mybb_sync_start_watcher",
        description="Start the file watcher to automatically sync template and stylesheet changes from disk to database.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="mybb_sync_stop_watcher",
        description="Stop the file watcher.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="mybb_sync_status",
        description="Get current sync service status (watcher state, sync directory, etc.).",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
]


# ==================== Plugin Git Tools (Nested Repo Operations) ====================

PLUGIN_GIT_TOOLS = [
    Tool(
        name="mybb_plugin_git_list",
        description="List all plugins and themes that have git initialized.",
        inputSchema={
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Filter: 'plugins', 'themes', or 'all'", "enum": ["plugins", "themes", "all"]},
            },
            "required": [],
        },
    ),
    Tool(
        name="mybb_plugin_git_init",
        description="Initialize git in a plugin or theme directory. Creates a nested repo (not a subtree).",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin or theme codename"},
                "type": {"type": "string", "description": "'plugin' or 'theme'", "enum": ["plugin", "theme"]},
                "visibility": {"type": "string", "description": "'public' or 'private'", "enum": ["public", "private"]},
                "remote": {"type": "string", "description": "Remote URL to add as origin"},
                "branch": {"type": "string", "description": "Initial branch name", "default": "main"},
            },
            "required": ["codename"],
        },
    ),
    Tool(
        name="mybb_plugin_github_create",
        description="Create a GitHub repo and link it to a plugin/theme. Requires GitHub CLI (gh) authenticated.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin or theme codename"},
                "type": {"type": "string", "description": "'plugin' or 'theme'", "enum": ["plugin", "theme"]},
                "visibility": {"type": "string", "description": "'public' or 'private'", "enum": ["public", "private"]},
                "repo_visibility": {"type": "string", "description": "GitHub repo: 'public' or 'private'", "enum": ["public", "private"]},
                "repo_name": {"type": "string", "description": "GitHub repo name (default: codename)"},
                "description": {"type": "string", "description": "Repo description"},
            },
            "required": ["codename"],
        },
    ),
    Tool(
        name="mybb_plugin_git_status",
        description="Get git status for a plugin or theme.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin or theme codename"},
                "type": {"type": "string", "description": "'plugin' or 'theme'", "enum": ["plugin", "theme"]},
                "visibility": {"type": "string", "description": "'public' or 'private'", "enum": ["public", "private"]},
            },
            "required": ["codename"],
        },
    ),
    Tool(
        name="mybb_plugin_git_commit",
        description="Commit changes in a plugin or theme repository. By default stages all changes. Use 'files' param to commit only specific files (useful for agent swarms).",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin or theme codename"},
                "message": {"type": "string", "description": "Commit message"},
                "type": {"type": "string", "description": "'plugin' or 'theme'", "enum": ["plugin", "theme"]},
                "visibility": {"type": "string", "description": "'public' or 'private'", "enum": ["public", "private"]},
                "files": {"type": "array", "items": {"type": "string"}, "description": "Specific files to commit (relative to plugin root). If omitted, commits all changes."},
            },
            "required": ["codename", "message"],
        },
    ),
    Tool(
        name="mybb_plugin_git_push",
        description="Push commits to remote repository.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin or theme codename"},
                "type": {"type": "string", "description": "'plugin' or 'theme'", "enum": ["plugin", "theme"]},
                "visibility": {"type": "string", "description": "'public' or 'private'", "enum": ["public", "private"]},
                "set_upstream": {"type": "boolean", "description": "Set upstream tracking branch", "default": False},
            },
            "required": ["codename"],
        },
    ),
    Tool(
        name="mybb_plugin_git_pull",
        description="Pull changes from remote repository.",
        inputSchema={
            "type": "object",
            "properties": {
                "codename": {"type": "string", "description": "Plugin or theme codename"},
                "type": {"type": "string", "description": "'plugin' or 'theme'", "enum": ["plugin", "theme"]},
                "visibility": {"type": "string", "description": "'public' or 'private'", "enum": ["public", "private"]},
            },
            "required": ["codename"],
        },
    ),
]


# ==================== Search Tools ====================

SEARCH_TOOLS = [
    Tool(
        name="mybb_search_posts",
        description="Search post content with optional filters for forums, author, and date range.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term to find in post content."},
                "forums": {"type": "array", "items": {"type": "integer"}, "description": "Optional list of forum IDs to search within."},
                "author": {"type": "string", "description": "Optional username to filter by."},
                "date_from": {"type": "integer", "description": "Optional start timestamp (Unix epoch)."},
                "date_to": {"type": "integer", "description": "Optional end timestamp (Unix epoch)."},
                "limit": {"type": "integer", "description": "Maximum results (default 25, max 100).", "default": 25},
                "offset": {"type": "integer", "description": "Pagination offset.", "default": 0},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="mybb_search_threads",
        description="Search thread subjects with optional filters for forums, author, and prefix.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term to find in thread subjects."},
                "forums": {"type": "array", "items": {"type": "integer"}, "description": "Optional list of forum IDs to search within."},
                "author": {"type": "string", "description": "Optional username to filter by."},
                "prefix": {"type": "integer", "description": "Optional thread prefix ID."},
                "limit": {"type": "integer", "description": "Maximum results (default 25, max 100).", "default": 25},
                "offset": {"type": "integer", "description": "Pagination offset.", "default": 0},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="mybb_search_users",
        description="Search users by username or email. Returns safe user info (no passwords).",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term."},
                "field": {"type": "string", "description": "Field to search ('username' or 'email').", "default": "username"},
                "limit": {"type": "integer", "description": "Maximum results (default 25, max 100).", "default": 25},
                "offset": {"type": "integer", "description": "Pagination offset.", "default": 0},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="mybb_search_advanced",
        description="Combined search across posts and/or threads with multiple filters.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term."},
                "content_type": {"type": "string", "description": "Content type: 'posts', 'threads', or 'both'.", "default": "both"},
                "forums": {"type": "array", "items": {"type": "integer"}, "description": "Optional list of forum IDs."},
                "date_from": {"type": "integer", "description": "Optional start timestamp (Unix epoch)."},
                "date_to": {"type": "integer", "description": "Optional end timestamp (Unix epoch)."},
                "sort_by": {"type": "string", "description": "Sort order ('date' or 'relevance').", "default": "date"},
                "limit": {"type": "integer", "description": "Maximum results per type (default 25, max 100).", "default": 25},
                "offset": {"type": "integer", "description": "Pagination offset.", "default": 0},
            },
            "required": ["query"],
        },
    ),
]


# ==================== Admin Tools: Settings, Cache, Statistics ====================

ADMIN_TOOLS = [
    Tool(
        name="mybb_setting_get",
        description="Get a MyBB setting value by name.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Setting name (e.g., 'boardclosed', 'bbname', 'contactemail')."},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="mybb_setting_set",
        description="Update a MyBB setting value. Automatically rebuilds settings cache after update.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Setting name to update."},
                "value": {"type": "string", "description": "New value for the setting."},
            },
            "required": ["name", "value"],
        },
    ),
    Tool(
        name="mybb_setting_list",
        description="List all MyBB settings or filter by setting group.",
        inputSchema={
            "type": "object",
            "properties": {
                "gid": {"type": "integer", "description": "Optional setting group ID to filter by."},
            },
        },
    ),
    Tool(
        name="mybb_settinggroup_list",
        description="List all MyBB setting groups (categories for organizing settings).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="mybb_cache_read",
        description="Read a MyBB cache entry by title. Returns serialized PHP cache data.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Cache title (e.g., 'settings', 'plugins', 'usergroups', 'forums')."},
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="mybb_cache_rebuild",
        description="Rebuild (clear) MyBB cache entries. MyBB regenerates them on next access. Use 'all' to clear all caches.",
        inputSchema={
            "type": "object",
            "properties": {
                "cache_type": {"type": "string", "description": "Cache type to rebuild (e.g., 'settings', 'plugins', 'usergroups') or 'all' for all caches.", "default": "all"},
            },
        },
    ),
    Tool(
        name="mybb_cache_list",
        description="List all MyBB cache entries with their titles and sizes.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="mybb_cache_clear",
        description="Clear a specific MyBB cache entry or all caches.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Optional cache title to clear. Omit to clear all caches."},
            },
        },
    ),
    Tool(
        name="mybb_stats_forum",
        description="Get forum statistics including total users, threads, posts, and newest member info.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="mybb_stats_board",
        description="Get comprehensive board statistics including forums, users, threads, posts, latest post, and most active forum.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]


# ==================== Moderation Tools ====================

MODERATION_TOOLS = [
    Tool(
        name="mybb_mod_close_thread",
        description="Close or open a thread.",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Thread ID"},
                "closed": {"type": "boolean", "description": "True to close, False to open", "default": True},
            },
            "required": ["tid"],
        },
    ),
    Tool(
        name="mybb_mod_stick_thread",
        description="Stick or unstick a thread.",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Thread ID"},
                "sticky": {"type": "boolean", "description": "True to stick, False to unstick", "default": True},
            },
            "required": ["tid"],
        },
    ),
    Tool(
        name="mybb_mod_approve_thread",
        description="Approve or unapprove a thread (set visible=1 or visible=0).",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Thread ID"},
                "approve": {"type": "boolean", "description": "True to approve, False to unapprove", "default": True},
            },
            "required": ["tid"],
        },
    ),
    Tool(
        name="mybb_mod_approve_post",
        description="Approve or unapprove a post (set visible=1 or visible=0).",
        inputSchema={
            "type": "object",
            "properties": {
                "pid": {"type": "integer", "description": "Post ID"},
                "approve": {"type": "boolean", "description": "True to approve, False to unapprove", "default": True},
            },
            "required": ["pid"],
        },
    ),
    Tool(
        name="mybb_mod_soft_delete_thread",
        description="Soft delete or restore a thread (uses existing delete_thread method with soft=True).",
        inputSchema={
            "type": "object",
            "properties": {
                "tid": {"type": "integer", "description": "Thread ID"},
                "delete": {"type": "boolean", "description": "True to soft delete, False to restore", "default": True},
            },
            "required": ["tid"],
        },
    ),
    Tool(
        name="mybb_mod_soft_delete_post",
        description="Soft delete or restore a post (set visible=-1 or visible=1).",
        inputSchema={
            "type": "object",
            "properties": {
                "pid": {"type": "integer", "description": "Post ID"},
                "delete": {"type": "boolean", "description": "True to soft delete, False to restore", "default": True},
            },
            "required": ["pid"],
        },
    ),
    Tool(
        name="mybb_modlog_list",
        description="List moderation log entries with optional filters.",
        inputSchema={
            "type": "object",
            "properties": {
                "uid": {"type": "integer", "description": "Filter by moderator user ID"},
                "fid": {"type": "integer", "description": "Filter by forum ID"},
                "tid": {"type": "integer", "description": "Filter by thread ID"},
                "limit": {"type": "integer", "description": "Maximum number of entries (1-100)", "default": 50},
            },
        },
    ),
    Tool(
        name="mybb_modlog_add",
        description="Add a moderation log entry.",
        inputSchema={
            "type": "object",
            "properties": {
                "uid": {"type": "integer", "description": "User ID performing the action"},
                "fid": {"type": "integer", "description": "Forum ID (0 if not applicable)", "default": 0},
                "tid": {"type": "integer", "description": "Thread ID (0 if not applicable)", "default": 0},
                "pid": {"type": "integer", "description": "Post ID (0 if not applicable)", "default": 0},
                "action": {"type": "string", "description": "Action description"},
                "data": {"type": "string", "description": "Additional data (serialized)", "default": ""},
                "ipaddress": {"type": "string", "description": "IP address of moderator", "default": ""},
            },
            "required": ["uid", "action"],
        },
    ),
]


# ==================== User Management Tools ====================

USER_TOOLS = [
    Tool(
        name="mybb_user_get",
        description="Get user by UID or username. Sensitive fields (password, salt, loginkey, regip, lastip) are excluded by default.",
        inputSchema={
            "type": "object",
            "properties": {
                "uid": {"type": "integer", "description": "User ID"},
                "username": {"type": "string", "description": "Username"},
            },
        },
    ),
    Tool(
        name="mybb_user_list",
        description="List users with optional filters. Sensitive fields are always excluded.",
        inputSchema={
            "type": "object",
            "properties": {
                "usergroup": {"type": "integer", "description": "Filter by usergroup ID"},
                "limit": {"type": "integer", "description": "Maximum number of users (1-100)", "default": 50},
                "offset": {"type": "integer", "description": "Number of users to skip", "default": 0},
            },
        },
    ),
    Tool(
        name="mybb_user_update_group",
        description="Update user's usergroup and optionally additional groups.",
        inputSchema={
            "type": "object",
            "properties": {
                "uid": {"type": "integer", "description": "User ID"},
                "usergroup": {"type": "integer", "description": "Primary usergroup ID"},
                "additionalgroups": {"type": "string", "description": "Comma-separated additional group IDs"},
            },
            "required": ["uid", "usergroup"],
        },
    ),
    Tool(
        name="mybb_user_ban",
        description="Add user to banned list.",
        inputSchema={
            "type": "object",
            "properties": {
                "uid": {"type": "integer", "description": "User ID to ban"},
                "gid": {"type": "integer", "description": "Banned usergroup ID"},
                "admin": {"type": "integer", "description": "Admin user ID performing the ban"},
                "dateline": {"type": "integer", "description": "Ban timestamp (Unix timestamp)"},
                "bantime": {"type": "string", "description": "Ban duration (e.g., 'perm', '---')", "default": "---"},
                "reason": {"type": "string", "description": "Ban reason", "default": ""},
            },
            "required": ["uid", "gid", "admin", "dateline"],
        },
    ),
    Tool(
        name="mybb_user_unban",
        description="Remove user from banned list.",
        inputSchema={
            "type": "object",
            "properties": {
                "uid": {"type": "integer", "description": "User ID to unban"},
            },
            "required": ["uid"],
        },
    ),
    Tool(
        name="mybb_usergroup_list",
        description="List all usergroups.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]


# ==================== Combined Tool List ====================

ALL_TOOLS = (
    TEMPLATE_TOOLS +
    THEME_TOOLS +
    PLUGIN_TOOLS +
    TASK_TOOLS +
    DATABASE_TOOLS +
    CONTENT_TOOLS +
    SYNC_TOOLS +
    PLUGIN_GIT_TOOLS +
    SEARCH_TOOLS +
    ADMIN_TOOLS +
    MODERATION_TOOLS +
    USER_TOOLS
)

# Tool count verification
EXPECTED_TOOL_COUNT = 94  # Was 91, added 3 git tools (commit, push, pull)
assert len(ALL_TOOLS) == EXPECTED_TOOL_COUNT, f"Expected {EXPECTED_TOOL_COUNT} tools, got {len(ALL_TOOLS)}"
