"""MyBB MCP Server - AI-assisted MyBB development tools.

This server provides tools for Claude to interact with MyBB:
- Template management (list, read, write with inheritance)
- Theme/stylesheet management with cache refresh
- Plugin scaffolding and hook reference
"""

import asyncio
import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import load_config, MyBBConfig
from .db import MyBBDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mybb-mcp")


def create_server(config: MyBBConfig) -> Server:
    """Create and configure the MCP server with all tools."""
    from pathlib import Path
    from .sync import DiskSyncService, SyncConfig

    server = Server("mybb-mcp")
    # Pool configuration is read from config.db.pool_size and config.db.pool_name
    db = MyBBDatabase(config.db)

    # Initialize DiskSync service
    # Use mybb_root's parent (repo root) for sync directory
    sync_root = config.mybb_root.parent / "mybb_sync"
    sync_root.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    sync_config = SyncConfig(sync_root=sync_root)
    sync_service = DiskSyncService(db, sync_config, config.mybb_url)

    # Auto-start file watcher (dev server - always want sync on)
    sync_service.start_watcher()
    logger.info(f"File watcher started: {sync_root}")

    # All tools in a combined list
    all_tools: list[Tool] = []

    # ==================== Template Tools ====================

    all_tools.extend([
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
    ])

    # ==================== Theme/Style Tools ====================

    all_tools.extend([
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
    ])

    # ==================== Plugin Tools ====================

    all_tools.extend([
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
    ])

    # ==================== Analysis Tools ====================

    all_tools.extend([
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
    ])

    # ==================== Plugin Lifecycle Tools ====================

    all_tools.extend([
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
    ])

    # ==================== Plugin Full Lifecycle Tools (Phase 7) ====================

    all_tools.extend([
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
    ])

    # ==================== Scheduled Task Tools ====================

    all_tools.extend([
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
    ])

    # ==================== Database Query Tool ====================

    all_tools.extend([
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
    ])

    # ==================== Content CRUD Tools ====================
    # Forum, Thread, and Post management

    all_tools.extend([
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
    ])

    # ==================== Disk Sync Tools ====================

    all_tools.extend([
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
    ])

    # ==================== Search Tools ====================

    all_tools.extend([
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
    ])

    # ==================== Admin Tools: Settings, Cache, Statistics ====================

    all_tools.extend([
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
    ])

    # ==================== Moderation Tools ====================

    all_tools.extend([
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
    ])

    # ==================== User Management Tools ====================

    all_tools.extend([
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
    ])

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return all_tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            result = await handle_tool(name, arguments, db, config, sync_service)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.exception(f"Error in tool {name}")
            return [TextContent(type="text", text=f"Error: {e}")]

    return server


async def handle_tool(name: str, args: dict, db: MyBBDatabase, config: MyBBConfig, sync_service=None) -> str:
    """Route tool calls to handlers."""
    import time
    import re
    import httpx

    plugins_dir = config.mybb_root / "inc" / "plugins"

    # ==================== Template Handlers ====================

    if name == "mybb_list_template_sets":
        sets = db.list_template_sets()
        if not sets:
            return "No template sets found."
        lines = ["# MyBB Template Sets\n", "| SID | Title |", "|-----|-------|"]
        for s in sets:
            lines.append(f"| {s['sid']} | {s['title']} |")
        lines.extend(["\n**Special SIDs:** -2 = Master templates, -1 = Global templates"])
        return "\n".join(lines)

    elif name == "mybb_list_templates":
        templates = db.list_templates(sid=args.get("sid"), search=args.get("search"))
        if not templates:
            return "No templates found."
        lines = [f"# Templates ({len(templates)} found)\n", "| TID | Title | SID | Version |", "|-----|-------|-----|---------|"]
        for t in templates[:100]:
            lines.append(f"| {t['tid']} | {t['title']} | {t['sid']} | {t['version']} |")
        if len(templates) > 100:
            lines.append(f"\n*...{len(templates) - 100} more*")
        return "\n".join(lines)

    elif name == "mybb_read_template":
        title = args.get("title")
        sid = args.get("sid")

        # Get master template (-2)
        master = db.get_template(title, -2)
        # Get custom if sid specified
        custom = db.get_template(title, sid) if sid and sid != -2 else None

        if not master and not custom:
            return f"Template '{title}' not found."

        lines = [f"# Template: {title}\n"]

        if master:
            lines.extend([
                "## Master Template (sid=-2)",
                f"- TID: {master['tid']}, Version: {master['version']}",
                "```html", master['template'], "```", ""
            ])

        if custom:
            lines.extend([
                f"## Custom Template (sid={sid})",
                f"- TID: {custom['tid']}, Version: {custom['version']}",
                "```html", custom['template'], "```"
            ])

        if master and not custom:
            lines.append("\n*No custom version exists. Editing will create a custom override.*")

        return "\n".join(lines)

    elif name == "mybb_write_template":
        title = args.get("title")
        template = args.get("template")
        sid = args.get("sid", 1)

        if not title or not template:
            return "Error: 'title' and 'template' are required."

        # Check for existing templates
        master = db.get_template(title, -2)
        custom = db.get_template(title, sid) if sid != -2 else None

        if sid == -2:
            # Updating master template
            if master:
                db.update_template(master['tid'], template)
                return f"Master template '{title}' updated (TID {master['tid']})."
            else:
                tid = db.create_template(title, template, -2)
                return f"Master template '{title}' created (TID {tid})."
        else:
            # Creating/updating custom template
            if custom:
                db.update_template(custom['tid'], template)
                return f"Custom template '{title}' updated in set {sid} (TID {custom['tid']})."
            else:
                tid = db.create_template(title, template, sid)
                msg = f"Custom template '{title}' created in set {sid} (TID {tid})."
                if master:
                    msg += f" (Overrides master TID {master['tid']})"
                return msg

    elif name == "mybb_list_template_groups":
        with db.cursor() as cur:
            cur.execute(f"SELECT prefix, title FROM {db.table('templategroups')} ORDER BY title")
            groups = cur.fetchall()

        if not groups:
            return "No template groups found."

        lines = ["# Template Groups\n", "| Prefix | Title |", "|--------|-------|"]
        for g in groups:
            lines.append(f"| {g['prefix']} | {g['title']} |")
        return "\n".join(lines)

    elif name == "mybb_template_find_replace":
        import re

        title = args.get("title")
        find = args.get("find")
        replace = args.get("replace")
        template_sets = args.get("template_sets", [])
        use_regex = args.get("regex", True)
        limit = args.get("limit", -1)

        if not title or not find or replace is None:
            return "Error: 'title', 'find', and 'replace' are required."

        # Get all matching templates
        templates = db.find_templates_for_replace(title, template_sets)

        if not templates:
            return f"No templates found matching '{title}' in specified template sets."

        modified_count = 0
        modified_templates = []

        for template in templates:
            original = template['template']

            # Perform replacement
            if use_regex:
                try:
                    if limit == -1:
                        new_content = re.sub(find, replace, original)
                    else:
                        new_content = re.sub(find, replace, original, count=limit)
                except re.error as e:
                    return f"Error: Invalid regex pattern: {e}"
            else:
                # Literal string replacement
                if limit == -1:
                    new_content = original.replace(find, replace)
                else:
                    new_content = original.replace(find, replace, limit)

            # Only update if content changed
            if new_content != original:
                db.update_template(template['tid'], new_content)
                modified_count += 1
                modified_templates.append(f"- TID {template['tid']} (sid={template['sid']})")

        if modified_count == 0:
            return f"No modifications made. Pattern '{find}' not found in template '{title}'."

        lines = [
            f"# Find/Replace Results for '{title}'",
            f"\nModified {modified_count} template(s):\n"
        ]
        lines.extend(modified_templates)
        return "\n".join(lines)

    elif name == "mybb_template_batch_read":
        template_names = args.get("templates", [])
        sid = args.get("sid", -2)

        if not template_names:
            return "Error: 'templates' list is required."

        results = {}
        not_found = []

        for title in template_names:
            template = db.get_template(title, sid)
            if template:
                results[title] = template['template']
            else:
                not_found.append(title)

        lines = [f"# Batch Read Results (sid={sid})\n"]

        if results:
            lines.append(f"Successfully read {len(results)} template(s):\n")
            for title, content in results.items():
                lines.extend([
                    f"## {title}",
                    "```html",
                    content,
                    "```\n"
                ])

        if not_found:
            lines.append(f"\nNot found ({len(not_found)}):")
            for title in not_found:
                lines.append(f"- {title}")

        return "\n".join(lines)

    elif name == "mybb_template_batch_write":
        templates = args.get("templates", [])
        sid = args.get("sid", 1)

        if not templates:
            return "Error: 'templates' list is required."

        # Atomic operation: collect all changes first
        operations = []
        for item in templates:
            title = item.get("title")
            content = item.get("template")

            if not title or not content:
                return f"Error: Each template must have 'title' and 'template' fields."

            # Check if template exists
            existing = db.get_template(title, sid)
            operations.append({
                "title": title,
                "content": content,
                "tid": existing['tid'] if existing else None,
                "action": "update" if existing else "create"
            })

        # Execute all operations
        created = []
        updated = []

        for op in operations:
            if op["action"] == "update":
                db.update_template(op["tid"], op["content"])
                updated.append(f"- {op['title']} (TID {op['tid']})")
            else:
                tid = db.create_template(op["title"], op["content"], sid)
                created.append(f"- {op['title']} (TID {tid})")

        lines = [f"# Batch Write Results (sid={sid})\n"]

        if created:
            lines.append(f"Created {len(created)} template(s):")
            lines.extend(created)
            lines.append("")

        if updated:
            lines.append(f"Updated {len(updated)} template(s):")
            lines.extend(updated)

        return "\n".join(lines)

    elif name == "mybb_template_outdated":
        sid = args.get("sid")

        if not sid:
            return "Error: 'sid' is required."

        if sid == -2:
            return "Error: Cannot check master templates (sid=-2) for outdated versions."

        outdated = db.find_outdated_templates(sid)

        if not outdated:
            return f"No outdated templates found in template set {sid}. All templates are up to date."

        lines = [
            f"# Outdated Templates in Set {sid}\n",
            f"Found {len(outdated)} outdated template(s):\n",
            "| Template | Custom Version | Master Version | TID |",
            "|----------|----------------|----------------|-----|"
        ]

        for template in outdated:
            lines.append(
                f"| {template['title']} | {template['custom_version']} | "
                f"{template['master_version']} | {template['tid']} |"
            )

        lines.append("\n*Note: Custom templates with version < master version are outdated and may need updating.*")
        return "\n".join(lines)

    # ==================== Theme/Style Handlers ====================

    elif name == "mybb_list_themes":
        # Import plugin_manager
        import sys
        pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
        if str(pm_path.parent) not in sys.path:
            sys.path.insert(0, str(pm_path.parent))
        from plugin_manager.manager import PluginManager

        manager = PluginManager()

        # Get workspace themes
        workspace_themes = manager.db.list_projects(project_type="theme")

        # Get MyBB themes (existing behavior)
        mybb_themes = db.list_themes()

        lines = ["# Themes\n"]

        if workspace_themes:
            lines.append("## Workspace Themes")
            for t in workspace_themes:
                status = "installed" if t['status'] == 'installed' else "workspace"
                lines.append(f"- `{t['codename']}` [{t['visibility']}] ({status})")
            lines.append("")

        lines.append("## MyBB Installed Themes")
        if mybb_themes:
            for t in mybb_themes:
                in_workspace = any(wt['codename'] == t['name'].lower().replace(' ', '_')
                                  for wt in workspace_themes)
                marker = " (managed)" if in_workspace else ""
                lines.append(f"- **{t['name']}** (tid: {t['tid']}){marker}")
        else:
            lines.append("No installed themes found.")

        return "\n".join(lines)

    elif name == "mybb_list_stylesheets":
        sheets = db.list_stylesheets(tid=args.get("tid"))
        if not sheets:
            return "No stylesheets found."
        lines = ["# Stylesheets\n", "| SID | Name | Theme TID | Cache File |", "|-----|------|-----------|------------|"]
        for s in sheets:
            lines.append(f"| {s['sid']} | {s['name']} | {s['tid']} | {s['cachefile']} |")
        return "\n".join(lines)

    elif name == "mybb_read_stylesheet":
        sid = args.get("sid")
        sheet = db.get_stylesheet(sid)
        if not sheet:
            return f"Stylesheet {sid} not found."

        # HYBRID MODE: Check if this stylesheet belongs to a workspace-managed theme
        import sys
        pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
        if str(pm_path.parent) not in sys.path:
            sys.path.insert(0, str(pm_path.parent))
        from plugin_manager.manager import PluginManager

        manager = PluginManager()

        # Get theme name from tid
        theme = db.get_theme(sheet['tid'])
        if theme:
            # Convert theme name to codename format for matching
            theme_codename = theme['name'].lower().replace(' ', '_')

            # Check if this theme is workspace-managed
            workspace_themes = manager.db.list_projects(project_type="theme")
            managed_theme = next((t for t in workspace_themes if t['codename'] == theme_codename), None)

            if managed_theme:
                # Read from workspace file
                workspace_path = Path(managed_theme['workspace_path'])
                stylesheet_file = workspace_path / "stylesheets" / sheet['name']

                if stylesheet_file.exists():
                    css_content = stylesheet_file.read_text(encoding='utf-8')
                    return (
                        f"# Stylesheet: {sheet['name']} (WORKSPACE)\n"
                        f"- Theme: {theme['name']} (managed)\n"
                        f"- Workspace File: `{stylesheet_file}`\n"
                        f"- Attached to: {sheet['attachedto'] or 'All'}\n\n"
                        f"```css\n{css_content}\n```"
                    )

        # Fall back to DB read for unmanaged themes
        return f"# Stylesheet: {sheet['name']}\n- SID: {sid}, Theme TID: {sheet['tid']}\n- Attached to: {sheet['attachedto'] or 'All'}\n\n```css\n{sheet['stylesheet']}\n```"

    elif name == "mybb_write_stylesheet":
        sid = args.get("sid")
        css = args.get("stylesheet")

        # HYBRID MODE: Check if this stylesheet belongs to a workspace-managed theme
        import sys
        pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
        if str(pm_path.parent) not in sys.path:
            sys.path.insert(0, str(pm_path.parent))
        from plugin_manager.manager import PluginManager

        manager = PluginManager()

        # Get stylesheet info
        sheet = db.get_stylesheet(sid)
        if not sheet:
            return f"Stylesheet {sid} not found."

        # Get theme name from tid
        theme = db.get_theme(sheet['tid'])
        wrote_to_workspace = False

        if theme:
            # Convert theme name to codename format for matching
            theme_codename = theme['name'].lower().replace(' ', '_')

            # Check if this theme is workspace-managed
            workspace_themes = manager.db.list_projects(project_type="theme")
            managed_theme = next((t for t in workspace_themes if t['codename'] == theme_codename), None)

            if managed_theme:
                # Write to workspace file
                workspace_path = Path(managed_theme['workspace_path'])
                stylesheets_dir = workspace_path / "stylesheets"
                stylesheets_dir.mkdir(exist_ok=True)
                stylesheet_file = stylesheets_dir / sheet['name']

                stylesheet_file.write_text(css, encoding='utf-8')
                wrote_to_workspace = True

                # Optionally sync to DB as well (keeping DB in sync for now)
                db.update_stylesheet(sid, css)

                result = f"Stylesheet {sheet['name']} updated in workspace: `{stylesheet_file}`"
            else:
                # Fall back to DB write for unmanaged themes
                if not db.update_stylesheet(sid, css):
                    return f"Failed to update stylesheet {sid}."
                result = f"Stylesheet {sid} updated in database."
        else:
            # No theme found, fall back to DB write
            if not db.update_stylesheet(sid, css):
                return f"Failed to update stylesheet {sid}."
            result = f"Stylesheet {sid} updated in database."

        # Try cache refresh
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{config.mybb_url}/cachecss.php")
                result += " Cache refresh triggered." if resp.status_code == 200 else ""
        except:
            pass

        return result

    elif name == "mybb_create_theme":
        # Import plugin_manager
        import sys
        pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
        if str(pm_path.parent) not in sys.path:
            sys.path.insert(0, str(pm_path.parent))
        from plugin_manager.manager import PluginManager

        manager = PluginManager()

        # Convert stylesheets to proper format
        stylesheets_input = args.get("stylesheets", ["global.css"])

        result = manager.create_theme(
            codename=args.get("codename", "").lower().replace(" ", "_"),
            display_name=args.get("name", ""),
            description=args.get("description", ""),
            author=args.get("author", "Developer"),
            version=args.get("version", "1.0.0"),
            visibility="public",
            parent_theme=args.get("parent_theme"),
            stylesheets=stylesheets_input
        )

        if result.get("success"):
            return (
                f"# Theme Created: {args.get('name')}\n\n"
                f"**Codename:** `{result['codename']}`\n"
                f"**Workspace:** `{result['workspace_path']}`\n"
                f"**Project ID:** {result['project_id']}\n\n"
                f"## Files Created\n" +
                "\n".join(f"- `{f}`" for f in result.get('files_created', [])) +
                f"\n\n**Next Steps:**\n"
                f"1. Edit stylesheets in `{result['workspace_path']}/stylesheets/`\n"
                f"2. Install to TestForum: Use `mybb_theme_activate` or Admin CP\n"
                f"3. Export for distribution: Use export workflow"
            )
        else:
            return f"# Error Creating Theme\n\n{result.get('error', 'Unknown error')}"

    # ==================== Plugin Handlers ====================

    elif name == "mybb_list_plugins":
        # Query both workspace and legacy plugins
        try:
            import sys
            from pathlib import Path

            # Add plugin_manager to path
            repo_root = Path(__file__).resolve().parent.parent.parent
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))

            from plugin_manager.database import ProjectDatabase

            # Get workspace plugins from ProjectDatabase
            db_path = repo_root / "plugin_manager" / "data" / "projects.db"
            if db_path.exists():
                project_db = ProjectDatabase(db_path)
                workspace_plugins = project_db.list_projects(type="plugin")
            else:
                workspace_plugins = []

            # Get legacy plugins from filesystem
            legacy_plugins = []
            if plugins_dir.exists():
                all_files = [f.stem for f in plugins_dir.glob("*.php") if f.stem != "index"]
                # Filter out plugins already in workspace
                workspace_codenames = {p['codename'] for p in workspace_plugins}
                legacy_plugins = [p for p in all_files if p not in workspace_codenames]

            # Build response
            lines = ["# Plugins\n"]

            if workspace_plugins:
                lines.append("## Workspace Plugins (Managed)")
                lines.append("| Name | Status | Visibility | Version |")
                lines.append("|------|--------|------------|---------|")
                for p in sorted(workspace_plugins, key=lambda x: x['codename']):
                    lines.append(f"| {p['display_name']} (`{p['codename']}`) | {p['status']} | {p['visibility']} | {p['version']} |")
                lines.append("")

            if legacy_plugins:
                lines.append("## Legacy Plugins (Unmanaged)")
                for p in sorted(legacy_plugins):
                    lines.append(f"- `{p}` ⚠️ Not in workspace")
                lines.append("")

            if not workspace_plugins and not legacy_plugins:
                return "# Plugins\n\nNo plugins found."

            lines.append("\n💡 **Tip:** Use `mybb_create_plugin` to create workspace-managed plugins.")
            return "\n".join(lines)

        except ImportError:
            # Fallback to legacy filesystem scan only
            if not plugins_dir.exists():
                return "Plugins directory not found."
            plugins = [f.stem for f in plugins_dir.glob("*.php") if f.stem != "index"]
            lines = [f"# Plugins ({len(plugins)})\n"]
            for p in sorted(plugins):
                lines.append(f"- `{p}`")
            return "\n".join(lines)

    elif name == "mybb_read_plugin":
        # Workspace-aware plugin reading
        pname = args.get("name", "").replace(".php", "")

        try:
            import sys
            from pathlib import Path

            # Add plugin_manager to path
            repo_root = Path(__file__).resolve().parent.parent.parent
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))

            from plugin_manager.database import ProjectDatabase
            import json

            # Check workspace first
            db_path = repo_root / "plugin_manager" / "data" / "projects.db"
            workspace_path = None
            meta_info = None

            if db_path.exists():
                project_db = ProjectDatabase(db_path)
                project = project_db.get_project(pname)
                if project:
                    workspace_path = repo_root / project['workspace_path']
                    # Try to read meta.json for additional context
                    meta_path = workspace_path / "meta.json"
                    if meta_path.exists():
                        with open(meta_path, 'r') as f:
                            meta_info = json.load(f)

            # Read plugin source (workspace or legacy)
            if workspace_path and workspace_path.exists():
                plugin_file = workspace_path / "src" / f"{pname}.php"
                if plugin_file.exists():
                    source = plugin_file.read_text()
                    location = f"Workspace: `{project['workspace_path']}/src/{pname}.php`"
                else:
                    return f"# Plugin: {pname}\n\n**Error:** Plugin found in database but source file missing."
            else:
                # Fallback to legacy TestForum location
                ppath = plugins_dir / f"{pname}.php"
                if not ppath.exists():
                    return f"Plugin '{pname}' not found in workspace or TestForum."
                source = ppath.read_text()
                location = f"Legacy: `TestForum/inc/plugins/{pname}.php` ⚠️"

            # Build response
            lines = [f"# Plugin: {pname}\n"]
            lines.append(f"**Location:** {location}\n")

            if meta_info:
                lines.append("## Metadata")
                lines.append(f"- **Display Name:** {meta_info.get('plugin', {}).get('name', 'N/A')}")
                lines.append(f"- **Version:** {meta_info.get('plugin', {}).get('version', 'N/A')}")
                lines.append(f"- **Author:** {meta_info.get('plugin', {}).get('author', 'N/A')}")
                lines.append(f"- **Visibility:** {meta_info.get('workspace', {}).get('visibility', 'N/A')}")
                lines.append("")

            lines.append("## Source Code\n")
            lines.append(f"```php\n{source}\n```")

            return "\n".join(lines)

        except ImportError:
            # Fallback to legacy read
            ppath = plugins_dir / f"{pname}.php"
            if not ppath.exists():
                return f"Plugin '{pname}' not found."
            return f"# Plugin: {pname}\n\n```php\n{ppath.read_text()}\n```"

    elif name == "mybb_create_plugin":
        # Delegate to PluginManager for workspace-based development
        import sys
        from pathlib import Path

        # Add plugin_manager to path
        repo_root = Path(__file__).resolve().parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        try:
            from plugin_manager.manager import PluginManager

            manager = PluginManager()

            # Map MCP args to plugin_manager params
            codename = args.get("codename", "").lower().replace(" ", "_").replace("-", "_")
            display_name = args.get("name", "")
            description = args.get("description", "")
            author = args.get("author", "Developer")
            version = args.get("version", "1.0.0")
            visibility = args.get("visibility", "public")  # New optional param

            # Convert hooks from list of strings to format expected by PluginManager
            hooks_input = args.get("hooks", [])
            hooks = [{"name": h, "handler": f"{codename}_{h}", "priority": 10}
                     for h in hooks_input] if hooks_input else None

            # Convert has_settings flag to settings list (empty list triggers settings creation)
            settings = [] if args.get("has_settings") else None

            result = manager.create_plugin(
                codename=codename,
                display_name=display_name,
                description=description,
                author=author,
                version=version,
                visibility=visibility,
                hooks=hooks,
                settings=settings,
                has_templates=args.get("has_templates", False),
                has_database=args.get("has_database", False)
            )

            # Format response as markdown
            if result.get("success"):
                files_list = "\n".join(f"- `{f}`" for f in result.get('files_created', []))
                return (
                    f"# Plugin Created: {display_name}\n\n"
                    f"**Codename:** `{result['codename']}`\n"
                    f"**Workspace:** `{result['workspace_path']}`\n"
                    f"**Project ID:** {result['project_id']}\n"
                    f"**Visibility:** {visibility}\n\n"
                    f"## Files Created\n{files_list}\n\n"
                    f"## Next Steps\n"
                    f"1. Edit the plugin at `{result['workspace_path']}/src/{codename}.php`\n"
                    f"2. Run `mybb_plugin_activate {codename}` to deploy to TestForum\n"
                    f"3. Activate in MyBB Admin CP to run PHP hooks\n"
                    f"4. Export for distribution when ready"
                )
            else:
                return f"# Error Creating Plugin\n\n**Error:** {result.get('error', 'Unknown error')}"

        except ImportError as e:
            # Fallback to legacy create_plugin if plugin_manager not available
            from .tools.plugins import create_plugin
            return create_plugin(args, config)
        except ValueError as e:
            return f"# Error Creating Plugin\n\n**Error:** {str(e)}"
        except Exception as e:
            return f"# Error Creating Plugin\n\n**Error:** {str(e)}"

    elif name == "mybb_list_hooks":
        from .tools.plugins import get_hooks_reference
        return get_hooks_reference(args.get("category"), args.get("search"))

    elif name == "mybb_hooks_discover":
        from .tools.hooks_expanded import discover_hooks
        return discover_hooks(
            config.mybb_root,
            path=args.get("path"),
            category=args.get("category"),
            search=args.get("search")
        )

    elif name == "mybb_hooks_usage":
        from .tools.hooks_expanded import find_hook_usage
        return find_hook_usage(config.mybb_root, args.get("hook_name"))

    elif name == "mybb_analyze_plugin":
        # Use meta.json for workspace plugins, parse PHP for legacy
        pname = args.get("name", "").replace(".php", "")

        try:
            import sys
            from pathlib import Path

            # Add plugin_manager to path
            repo_root = Path(__file__).resolve().parent.parent.parent
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))

            from plugin_manager.database import ProjectDatabase
            import json

            # Check if workspace plugin
            db_path = repo_root / "plugin_manager" / "data" / "projects.db"
            is_workspace = False
            meta_info = None

            if db_path.exists():
                project_db = ProjectDatabase(db_path)
                project = project_db.get_project(pname)
                if project:
                    workspace_path = repo_root / project['workspace_path']
                    meta_path = workspace_path / "meta.json"
                    if meta_path.exists():
                        with open(meta_path, 'r') as f:
                            meta_info = json.load(f)
                        is_workspace = True

            lines = [f"# Plugin Analysis: {pname}\n"]

            if is_workspace and meta_info:
                # Use structured meta.json data
                lines.append(f"**Source:** Workspace (Managed)\n")

                plugin_info = meta_info.get('plugin', {})
                workspace_info = meta_info.get('workspace', {})

                lines.append("## Plugin Information")
                lines.append(f"- **Name:** {plugin_info.get('name', 'N/A')}")
                lines.append(f"- **Author:** {plugin_info.get('author', 'N/A')}")
                lines.append(f"- **Version:** {plugin_info.get('version', 'N/A')}")
                lines.append(f"- **Compatibility:** {plugin_info.get('compatibility', 'N/A')}")
                lines.append(f"- **Visibility:** {workspace_info.get('visibility', 'N/A')}")
                lines.append(f"- **Status:** {project['status']}")

                # Hooks
                hooks = meta_info.get('hooks', [])
                lines.append(f"\n## Hooks ({len(hooks)})")
                for h in hooks[:20]:
                    hook_name = h if isinstance(h, str) else h.get('name', 'unknown')
                    priority = h.get('priority', 10) if isinstance(h, dict) else 10
                    lines.append(f"- `{hook_name}` (priority: {priority})")

                # Settings
                settings = meta_info.get('settings', [])
                lines.append(f"\n## Settings")
                if settings:
                    lines.append(f"- **Count:** {len(settings)}")
                    for s in settings[:10]:
                        setting_name = s if isinstance(s, str) else s.get('name', 'unknown')
                        lines.append(f"  - `{setting_name}`")
                else:
                    lines.append("- None")

                # Templates
                templates = meta_info.get('templates', [])
                lines.append(f"\n## Templates")
                if templates:
                    lines.append(f"- **Count:** {len(templates)}")
                    for t in templates[:10]:
                        template_name = t if isinstance(t, str) else t.get('name', 'unknown')
                        lines.append(f"  - `{template_name}`")
                else:
                    lines.append("- None")

                # Database
                database = meta_info.get('database', {})
                lines.append(f"\n## Database")
                if database and database.get('tables'):
                    tables = database.get('tables', [])
                    lines.append(f"- **Tables:** {len(tables)}")
                    for table in tables[:5]:
                        table_name = table if isinstance(table, str) else table.get('name', 'unknown')
                        lines.append(f"  - `{table_name}`")
                else:
                    lines.append("- No database tables")

                return "\n".join(lines)

            else:
                # Fall back to PHP parsing for legacy plugins
                ppath = plugins_dir / f"{pname}.php"
                if not ppath.exists():
                    return f"Plugin '{pname}' not found."

                content = ppath.read_text()
                lines = [f"# Plugin Analysis: {pname}\n"]
                lines.append("**Source:** Legacy (Unmanaged) ⚠️\n")

                # Find hooks
                hook_pattern = r"\$plugins->add_hook\s*\(\s*['\"]([^'\"]+)['\"]"
                hooks = re.findall(hook_pattern, content)
                lines.append(f"## Hooks ({len(hooks)})")
                for h in hooks[:20]:
                    lines.append(f"- `{h}`")

                # Find _info function
                if f"{pname}_info" in content:
                    lines.append("\n## Has _info: Yes")

                # Find functions
                func_pattern = rf"function\s+{pname}_(\w+)"
                funcs = re.findall(func_pattern, content)
                lines.append(f"\n## Functions ({len(funcs)})")
                for f in funcs[:20]:
                    lines.append(f"- `{pname}_{f}()`")

                # Check for features
                lines.append("\n## Features")
                lines.append(f"- Settings: {'Yes' if 'settinggroups' in content else 'No'}")
                lines.append(f"- Templates: {'Yes' if 'templates' in content and 'insert_query' in content else 'No'}")
                lines.append(f"- Database: {'Yes' if 'create_table' in content.lower() or 'write_query' in content else 'No'}")

                return "\n".join(lines)

        except ImportError:
            # Fallback to legacy PHP parsing
            ppath = plugins_dir / f"{pname}.php"
            if not ppath.exists():
                return f"Plugin '{pname}' not found."

            content = ppath.read_text()
            lines = [f"# Plugin Analysis: {pname}\n"]

            # Find hooks
            hook_pattern = r"\$plugins->add_hook\s*\(\s*['\"]([^'\"]+)['\"]"
            hooks = re.findall(hook_pattern, content)
            lines.append(f"## Hooks ({len(hooks)})")
            for h in hooks[:20]:
                lines.append(f"- `{h}`")

            # Find _info function
            if f"{pname}_info" in content:
                lines.append("\n## Has _info: Yes")

            # Find functions
            func_pattern = rf"function\s+{pname}_(\w+)"
            funcs = re.findall(func_pattern, content)
            lines.append(f"\n## Functions ({len(funcs)})")
            for f in funcs[:20]:
                lines.append(f"- `{pname}_{f}()`")

            # Check for features
            lines.append("\n## Features")
            lines.append(f"- Settings: {'Yes' if 'settinggroups' in content else 'No'}")
            lines.append(f"- Templates: {'Yes' if 'templates' in content and 'insert_query' in content else 'No'}")
            lines.append(f"- Database: {'Yes' if 'create_table' in content.lower() or 'write_query' in content else 'No'}")

            return "\n".join(lines)

    # ==================== Plugin Lifecycle Handlers ====================

    elif name == "mybb_plugin_list_installed":
        cache = db.get_plugins_cache()
        if not cache["plugins"]:
            return "# Installed Plugins\n\nNo plugins are currently active.\n\n*Note: This shows plugins from datacache. File-based listing available via mybb_list_plugins.*"

        lines = [f"# Installed Plugins ({len(cache['plugins'])})\n"]
        for plugin in sorted(cache["plugins"]):
            lines.append(f"- `{plugin}`")

        lines.append(f"\n**Raw Cache**: `{cache['raw']}`")
        return "\n".join(lines)

    elif name == "mybb_plugin_info":
        pname = args.get("name", "").replace(".php", "")
        ppath = plugins_dir / f"{pname}.php"
        if not ppath.exists():
            return f"Plugin '{pname}' not found in {plugins_dir}"

        content = ppath.read_text()
        info_func = f"{pname}_info"

        if info_func not in content:
            return f"# Plugin: {pname}\n\nNo `{info_func}()` function found."

        # Extract _info function content
        import re
        pattern = rf"function\s+{info_func}\s*\(\s*\)\s*\{{([^}}]+(?:\{{[^}}]+\}}[^}}]*)*)\}}"
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            return f"# Plugin: {pname}\n\nCould not parse `{info_func}()` function."

        info_content = match.group(1)
        lines = [f"# Plugin Info: {pname}\n"]

        # Extract key fields
        for field in ["name", "description", "website", "author", "authorsite", "version", "compatibility", "codename"]:
            field_pattern = rf'"{field}"\s*=>\s*"([^"]+)"'
            field_match = re.search(field_pattern, info_content)
            if field_match:
                lines.append(f"**{field.title()}**: {field_match.group(1)}")

        return "\n".join(lines)

    elif name == "mybb_plugin_activate":
        pname = args.get("name", "").replace(".php", "")

        # Try to use PluginManager for managed plugins
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        try:
            from plugin_manager.manager import PluginManager

            manager = PluginManager()

            # Check if this is a managed plugin in the workspace
            project = manager.db.get_project(pname)

            if project and project.get('type') == 'plugin':
                # Use plugin_manager install workflow (copies files to TestForum)
                visibility = project.get('visibility', 'public')
                result = manager.install_plugin(pname, visibility)

                if result.get("success"):
                    return (
                        f"# Plugin Installed: {pname}\n\n"
                        f"**Status:** Deployed to TestForum\n"
                        f"**Files Copied:** {result.get('files_copied', 0)}\n"
                        f"**Templates Installed:** {result.get('templates_installed', 0)}\n"
                        f"**Workspace:** `{result.get('workspace_path', 'N/A')}`\n\n"
                        f"**Note:** Plugin files deployed to TestForum. To fully activate (run `{pname}_activate()`), "
                        f"use MyBB Admin CP: {config.mybb_url}/admin/index.php?module=config-plugins"
                    )
                else:
                    return f"# Install Failed: {pname}\n\n**Error:** {result.get('error', 'Unknown error')}"

        except ImportError:
            pass  # Fall through to legacy behavior
        except Exception as e:
            # Log but continue to legacy if install fails
            logger.warning(f"PluginManager install failed for {pname}: {e}")

        # Legacy behavior: Check if plugin exists in TestForum and update cache
        ppath = plugins_dir / f"{pname}.php"
        if not ppath.exists():
            return f"Error: Plugin '{pname}' not found in TestForum or workspace."

        cache = db.get_plugins_cache()
        if pname in cache["plugins"]:
            return f"Plugin '{pname}' is already active."

        # Add to active plugins (legacy cache-only activation)
        updated_plugins = cache["plugins"] + [pname]
        db.update_plugins_cache(updated_plugins)

        return (
            f"# Plugin Activated: {pname} (Legacy)\n\n"
            f"Added to active plugins cache.\n\n"
            f"**Warning:** This plugin is not managed by plugin_manager. "
            f"Consider recreating it via `mybb_create_plugin` for full workspace features.\n\n"
            f"**Warning:** This does NOT execute the PHP `{pname}_activate()` function. "
            f"For full activation including database setup, templates, and settings, "
            f"use MyBB's Admin CP at {config.mybb_url}/admin/index.php?module=config-plugins"
        )

    elif name == "mybb_plugin_deactivate":
        pname = args.get("name", "").replace(".php", "")

        # Try to use PluginManager for managed plugins
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        try:
            from plugin_manager.manager import PluginManager

            manager = PluginManager()

            # Check if this is a managed plugin in the workspace
            project = manager.db.get_project(pname)

            if project and project.get('type') == 'plugin':
                # Use plugin_manager uninstall workflow (removes files from TestForum)
                visibility = project.get('visibility', 'public')
                result = manager.uninstall_plugin(pname, visibility)

                if result.get("success"):
                    return (
                        f"# Plugin Uninstalled: {pname}\n\n"
                        f"**Status:** Removed from TestForum\n"
                        f"**Files Removed:** {result.get('files_removed', 0)}\n"
                        f"**Templates Removed:** {result.get('templates_removed', 0)}\n\n"
                        f"**Note:** Plugin files removed from TestForum. "
                        f"Workspace copy preserved at `{result.get('workspace_path', 'N/A')}`\n\n"
                        f"**Reminder:** This does NOT execute the PHP `{pname}_deactivate()` function. "
                        f"For full deactivation including cleanup, use MyBB's Admin CP first."
                    )
                else:
                    return f"# Uninstall Failed: {pname}\n\n**Error:** {result.get('error', 'Unknown error')}"

        except ImportError:
            pass  # Fall through to legacy behavior
        except Exception as e:
            # Log but continue to legacy if uninstall fails
            logger.warning(f"PluginManager uninstall failed for {pname}: {e}")

        # Legacy behavior: Just update cache
        cache = db.get_plugins_cache()
        if pname not in cache["plugins"]:
            return f"Plugin '{pname}' is not currently active."

        # Remove from active plugins (legacy cache-only deactivation)
        updated_plugins = [p for p in cache["plugins"] if p != pname]
        db.update_plugins_cache(updated_plugins)

        return (
            f"# Plugin Deactivated: {pname} (Legacy)\n\n"
            f"Removed from active plugins cache.\n\n"
            f"**Warning:** This plugin is not managed by plugin_manager.\n\n"
            f"**Warning:** This does NOT execute the PHP `{pname}_deactivate()` function. "
            f"For full deactivation including cleanup, use MyBB's Admin CP at "
            f"{config.mybb_url}/admin/index.php?module=config-plugins"
        )

    elif name == "mybb_plugin_is_installed":
        # Check both ProjectDatabase and MyBB cache
        pname = args.get("name", "").replace(".php", "")

        try:
            import sys
            from pathlib import Path

            # Add plugin_manager to path
            repo_root = Path(__file__).resolve().parent.parent.parent
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))

            from plugin_manager.database import ProjectDatabase

            # Check workspace database first
            db_path = repo_root / "plugin_manager" / "data" / "projects.db"
            workspace_status = None
            workspace_project = None

            if db_path.exists():
                project_db = ProjectDatabase(db_path)
                workspace_project = project_db.get_project(pname)
                if workspace_project:
                    workspace_status = workspace_project.get('status')

            # Check MyBB cache
            is_active = db.is_plugin_installed(pname)

            # Build response
            lines = [f"# Plugin Status: {pname}\n"]

            if workspace_project:
                lines.append(f"**Workspace Status:** {workspace_status}")
                lines.append(f"**MyBB Cache Status:** {'Active' if is_active else 'Not Active'}")
                lines.append("")

                if workspace_status == 'installed' and is_active:
                    lines.append("✅ Plugin is installed in both workspace database and MyBB cache.")
                elif workspace_status == 'installed' and not is_active:
                    lines.append("⚠️ **Warning:** Plugin marked 'installed' in workspace but not active in MyBB cache.")
                    lines.append("   Run `mybb_plugin_activate` to sync.")
                elif workspace_status != 'installed' and is_active:
                    lines.append("⚠️ **Warning:** Plugin active in MyBB but not marked 'installed' in workspace.")
                    lines.append("   Workspace status may be out of sync.")
                else:
                    lines.append("Plugin is not currently installed/active.")

            else:
                # Legacy plugin (not in workspace)
                lines.append(f"**Source:** Legacy (Unmanaged) ⚠️")
                lines.append(f"**MyBB Cache Status:** {'Active' if is_active else 'Not Active'}")
                lines.append("")
                if is_active:
                    lines.append("Plugin is active in MyBB cache (legacy plugin).")
                else:
                    lines.append("Plugin is not active in MyBB cache.")

            return "\n".join(lines)

        except ImportError:
            # Fallback to MyBB cache check only
            is_active = db.is_plugin_installed(pname)

            if is_active:
                return f"# Plugin Status: {pname}\n\n**Status**: Active\n\nPlugin is currently in the active plugins cache."
            else:
                return f"# Plugin Status: {pname}\n\n**Status**: Not Active\n\nPlugin is not in the active plugins cache."

    # ==================== Plugin Full Lifecycle Handlers (Phase 7) ====================

    elif name == "mybb_plugin_install":
        codename = args.get("codename", "").replace(".php", "")
        force = args.get("force", False)

        if not codename:
            return "Error: Plugin codename is required."

        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        try:
            from plugin_manager.manager import PluginManager

            manager = PluginManager()
            result = manager.activate_full(codename, force=force)

            if result.get("success"):
                lines = [f"# Plugin Installed: {codename}\n"]

                # PHP Lifecycle results
                php = result.get("php_lifecycle", {})
                actions = php.get("actions_taken", [])
                lines.append(f"**PHP Lifecycle Actions:** {', '.join(actions) if actions else 'none'}")

                # Files deployed
                files = result.get("files_deployed", [])
                if files:
                    lines.append(f"**Files Deployed:** {len(files)}")

                # Workspace path
                if result.get("workspace_path"):
                    lines.append(f"**Workspace:** `{result['workspace_path']}`")

                lines.append("")
                lines.append("✅ Plugin is now fully installed and active in MyBB.")

                # Warnings
                if result.get("warnings"):
                    lines.append("")
                    lines.append("**Warnings:**")
                    for w in result["warnings"]:
                        lines.append(f"- {w}")

                return "\n".join(lines)
            else:
                return f"# Plugin Install Failed: {codename}\n\n**Error:** {result.get('error', 'Unknown error')}"

        except ImportError as e:
            return f"Error: plugin_manager not available: {e}"
        except Exception as e:
            logger.exception(f"Error in mybb_plugin_install for {codename}")
            return f"Error installing plugin {codename}: {e}"

    elif name == "mybb_plugin_uninstall":
        codename = args.get("codename", "").replace(".php", "")
        uninstall = args.get("uninstall", False)
        remove_files = args.get("remove_files", False)

        if not codename:
            return "Error: Plugin codename is required."

        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        try:
            from plugin_manager.manager import PluginManager

            manager = PluginManager()
            result = manager.deactivate_full(codename, uninstall=uninstall, remove_files=remove_files)

            if result.get("success"):
                lines = [f"# Plugin Uninstalled: {codename}\n"]

                # PHP Lifecycle results
                php = result.get("php_lifecycle", {})
                actions = php.get("actions_taken", [])
                lines.append(f"**PHP Lifecycle Actions:** {', '.join(actions) if actions else 'none'}")

                if php.get("uninstalled"):
                    lines.append("**Uninstall Function:** Executed (_uninstall ran)")

                # Files removed
                files = result.get("files_removed", [])
                if files:
                    lines.append(f"**Files Removed:** {len(files)}")

                lines.append("")
                if uninstall and remove_files:
                    lines.append("✅ Plugin fully uninstalled: PHP cleanup done, settings/tables removed, files deleted.")
                elif uninstall:
                    lines.append("✅ Plugin uninstalled: PHP cleanup done, settings/tables removed. Files remain in TestForum.")
                elif remove_files:
                    lines.append("✅ Plugin deactivated and files removed. Settings/tables preserved (use uninstall=true to remove).")
                else:
                    lines.append("✅ Plugin deactivated. Files and settings preserved.")

                # Warnings
                if result.get("warnings"):
                    lines.append("")
                    lines.append("**Warnings:**")
                    for w in result["warnings"]:
                        lines.append(f"- {w}")

                return "\n".join(lines)
            else:
                return f"# Plugin Uninstall Failed: {codename}\n\n**Error:** {result.get('error', 'Unknown error')}"

        except ImportError as e:
            return f"Error: plugin_manager not available: {e}"
        except Exception as e:
            logger.exception(f"Error in mybb_plugin_uninstall for {codename}")
            return f"Error uninstalling plugin {codename}: {e}"

    elif name == "mybb_plugin_status":
        codename = args.get("codename", "").replace(".php", "")

        if not codename:
            return "Error: Plugin codename is required."

        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        try:
            from plugin_manager.manager import PluginManager

            manager = PluginManager()
            result = manager.get_plugin_status(codename)

            if result.get("success"):
                lines = [f"# Plugin Status: {codename}\n"]

                # Plugin info
                info = result.get("info", {})
                if info:
                    lines.append(f"**Name:** {info.get('name', codename)}")
                    lines.append(f"**Version:** {info.get('version', 'unknown')}")
                    lines.append(f"**Author:** {info.get('author', 'unknown')}")
                    lines.append(f"**Compatibility:** {info.get('compatibility', '*')}")
                    lines.append("")

                # Status flags
                lines.append("**Status:**")
                lines.append(f"- Installed: {'✅ Yes' if result.get('is_installed') else '❌ No'}")
                lines.append(f"- Active: {'✅ Yes' if result.get('is_active') else '❌ No'}")
                lines.append(f"- Compatible: {'✅ Yes' if result.get('is_compatible') else '⚠️ No'}")

                # Available functions
                lines.append("")
                lines.append("**Available Functions:**")
                funcs = []
                if result.get('has_install'):
                    funcs.append('_install')
                if result.get('has_uninstall'):
                    funcs.append('_uninstall')
                if result.get('has_activate'):
                    funcs.append('_activate')
                if result.get('has_deactivate'):
                    funcs.append('_deactivate')
                lines.append(f"- {', '.join(funcs) if funcs else 'none'}")

                # File path
                if result.get('file_path'):
                    lines.append("")
                    lines.append(f"**File:** `{result['file_path']}`")

                return "\n".join(lines)
            else:
                return f"# Plugin Status: {codename}\n\n**Error:** {result.get('error', 'Plugin not found or error occurred')}"

        except ImportError as e:
            return f"Error: plugin_manager not available: {e}"
        except Exception as e:
            logger.exception(f"Error in mybb_plugin_status for {codename}")
            return f"Error getting plugin status for {codename}: {e}"

    # ==================== Scheduled Task Handlers ====================

    elif name == "mybb_task_list":
        enabled_only = args.get("enabled_only", False)
        tasks = db.list_tasks(enabled_only=enabled_only)

        if not tasks:
            return "No tasks found."

        import datetime
        lines = [
            f"# Scheduled Tasks ({len(tasks)})\n",
            "| TID | Title | File | Enabled | Next Run | Last Run |",
            "|-----|-------|------|---------|----------|----------|"
        ]

        for task in tasks:
            next_run = datetime.datetime.fromtimestamp(task['nextrun']).strftime('%Y-%m-%d %H:%M')
            last_run = datetime.datetime.fromtimestamp(task['lastrun']).strftime('%Y-%m-%d %H:%M') if task['lastrun'] else "Never"
            enabled = "Yes" if task['enabled'] else "No"
            lines.append(
                f"| {task['tid']} | {task['title']} | {task['file']} | "
                f"{enabled} | {next_run} | {last_run} |"
            )

        return "\n".join(lines)

    elif name == "mybb_task_get":
        tid = args.get("tid")
        task = db.get_task(tid)

        if not task:
            return f"Task {tid} not found."

        import datetime
        next_run = datetime.datetime.fromtimestamp(task['nextrun']).strftime('%Y-%m-%d %H:%M:%S')
        last_run = datetime.datetime.fromtimestamp(task['lastrun']).strftime('%Y-%m-%d %H:%M:%S') if task['lastrun'] else "Never"

        return (
            f"# Task: {task['title']} (TID {tid})\n\n"
            f"**Description**: {task['description']}\n"
            f"**File**: {task['file']}\n"
            f"**Enabled**: {'Yes' if task['enabled'] else 'No'}\n"
            f"**Logging**: {'Yes' if task['logging'] else 'No'}\n"
            f"**Locked**: {task['locked']}\n\n"
            f"## Schedule\n"
            f"**Minute**: {task['minute']}\n"
            f"**Hour**: {task['hour']}\n"
            f"**Day**: {task['day']}\n"
            f"**Month**: {task['month']}\n"
            f"**Weekday**: {task['weekday']}\n\n"
            f"## Execution\n"
            f"**Next Run**: {next_run} (Unix: {task['nextrun']})\n"
            f"**Last Run**: {last_run} (Unix: {task['lastrun']})"
        )

    elif name == "mybb_task_enable":
        tid = args.get("tid")
        if db.enable_task(tid):
            return f"Task {tid} enabled successfully."
        else:
            return f"Failed to enable task {tid}. Task may not exist."

    elif name == "mybb_task_disable":
        tid = args.get("tid")
        if db.disable_task(tid):
            return f"Task {tid} disabled successfully."
        else:
            return f"Failed to disable task {tid}. Task may not exist."

    elif name == "mybb_task_update_nextrun":
        tid = args.get("tid")
        nextrun = args.get("nextrun")

        if db.update_task_nextrun(tid, nextrun):
            import datetime
            next_run_str = datetime.datetime.fromtimestamp(nextrun).strftime('%Y-%m-%d %H:%M:%S')
            return f"Task {tid} next run updated to {next_run_str} (Unix: {nextrun})."
        else:
            return f"Failed to update task {tid}. Task may not exist."

    elif name == "mybb_task_run_log":
        tid = args.get("tid")
        limit = args.get("limit", 50)
        logs = db.get_task_logs(tid=tid, limit=limit)

        if not logs:
            return "No task logs found."

        import datetime
        lines = [
            f"# Task Run Log ({len(logs)} entries)\n",
            "| Log ID | Task ID | Time | Data |",
            "|--------|---------|------|------|"
        ]

        for log in logs:
            time_str = datetime.datetime.fromtimestamp(log['dateline']).strftime('%Y-%m-%d %H:%M:%S')
            data = str(log.get('data', ''))[:50]
            lines.append(f"| {log['lid']} | {log['tid']} | {time_str} | {data} |")

        return "\n".join(lines)

    elif name == "mybb_db_query":
        query = args.get("query", "").strip()
        if not query.upper().startswith("SELECT"):
            return "Error: Only SELECT queries are allowed."

        with db.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

        if not rows:
            return "No results."

        # Format as table
        keys = list(rows[0].keys())
        lines = [" | ".join(keys), " | ".join(["---"] * len(keys))]
        for row in rows[:50]:
            lines.append(" | ".join(str(row[k])[:50] for k in keys))
        if len(rows) > 50:
            lines.append(f"\n*...{len(rows) - 50} more rows*")

        return "\n".join(lines)

    # ==================== Disk Sync Handlers ====================

    elif name == "mybb_sync_export_templates":
        set_name = args.get("set_name", "")
        if not set_name:
            return "Error: set_name is required"

        try:
            # Pause watcher during export to prevent race conditions
            if sync_service and sync_service.watcher:
                sync_service.pause_watcher()

            stats = await sync_service.export_template_set(set_name)
            groups_str = ', '.join(f"{g} ({c})" for g, c in stats['groups'].items())
            return (
                f"# Templates Exported\n\n"
                f"**Set**: {stats['template_set']}\n"
                f"**Files**: {stats['files_exported']}\n"
                f"**Directory**: {stats['directory']}\n\n"
                f"**Groups**: {groups_str}"
            )
        except ValueError as e:
            return f"Error: {e}"
        finally:
            # Always resume watcher, even on error
            if sync_service and sync_service.watcher:
                sync_service.resume_watcher()

    elif name == "mybb_sync_export_stylesheets":
        theme_name = args.get("theme_name", "")
        if not theme_name:
            return "Error: theme_name is required"

        try:
            # Pause watcher during export to prevent race conditions
            if sync_service and sync_service.watcher:
                sync_service.pause_watcher()

            stats = await sync_service.export_theme(theme_name)
            return (
                f"# Stylesheets Exported\n\n"
                f"**Theme**: {stats['theme_name']}\n"
                f"**Files**: {stats['files_exported']}\n"
                f"**Directory**: {stats['directory']}"
            )
        except ValueError as e:
            return f"Error: {e}"
        finally:
            # Always resume watcher, even on error
            if sync_service and sync_service.watcher:
                sync_service.resume_watcher()

    elif name == "mybb_sync_start_watcher":
        started = sync_service.start_watcher()
        if started:
            return (
                f"# File Watcher Started\n\n"
                f"**Status**: Running\n"
                f"**Monitoring**: {sync_service.config.sync_root}\n\n"
                f"The watcher will automatically import template (.html) and stylesheet (.css) "
                f"changes from disk to the database."
            )
        else:
            return "# File Watcher Already Running\n\nThe watcher is already active."

    elif name == "mybb_sync_stop_watcher":
        stopped = sync_service.stop_watcher()
        if stopped:
            return "# File Watcher Stopped\n\n**Status**: Stopped"
        else:
            return "# File Watcher Not Running\n\nThe watcher was not active."

    elif name == "mybb_sync_status":
        status = sync_service.get_status()
        watcher_status = "Running ✓" if status['watcher_running'] else "Stopped"

        # Build base status output
        output = [
            "# Sync Status\n",
            f"**Watcher**: {watcher_status}",
            f"**Sync Root**: {status['sync_root']}",
            f"**MyBB URL**: {status['mybb_url']}"
        ]

        # Add workspace root if available
        if 'workspace_root' in status:
            output.append(f"**Workspace Root**: {status['workspace_root']}")

        # Query workspace projects from ProjectDatabase
        try:
            # Import PluginManager dependencies
            import sys
            from pathlib import Path
            repo_root = Path(__file__).resolve().parent.parent.parent
            plugin_manager_path = repo_root / "plugin_manager"
            if str(plugin_manager_path) not in sys.path:
                sys.path.insert(0, str(plugin_manager_path))

            from database import ProjectDatabase

            # Initialize database
            workspace_root = Path(status.get('workspace_root', repo_root / 'plugin_manager'))
            db_path = workspace_root / '.meta' / 'projects.db'

            if db_path.exists():
                project_db = ProjectDatabase(db_path)

                # Get all plugins and themes
                plugins = project_db.list_projects(type='plugin')
                themes = project_db.list_projects(type='theme')

                if plugins or themes:
                    output.append("\n## Workspace Projects\n")

                    if plugins:
                        output.append("### Plugins")
                        output.append("| Codename | Status | Version | Last Synced |")
                        output.append("|----------|--------|---------|-------------|")
                        for p in plugins:
                            last_synced = p.get('last_synced_at', 'never')
                            if last_synced and last_synced != 'never':
                                # Format timestamp nicely
                                from datetime import datetime
                                try:
                                    dt = datetime.fromisoformat(last_synced)
                                    last_synced = dt.strftime('%Y-%m-%d %H:%M')
                                except:
                                    pass
                            output.append(f"| {p['codename']} | {p['status']} | {p['version']} | {last_synced} |")
                        output.append("")

                    if themes:
                        output.append("### Themes")
                        output.append("| Codename | Status | Version | Last Synced |")
                        output.append("|----------|--------|---------|-------------|")
                        for t in themes:
                            last_synced = t.get('last_synced_at', 'never')
                            if last_synced and last_synced != 'never':
                                from datetime import datetime
                                try:
                                    dt = datetime.fromisoformat(last_synced)
                                    last_synced = dt.strftime('%Y-%m-%d %H:%M')
                                except:
                                    pass
                            output.append(f"| {t['codename']} | {t['status']} | {t['version']} | {last_synced} |")
        except Exception as e:
            # If workspace query fails, just continue with base status
            output.append(f"\n*Note: Could not query workspace projects: {e}*")

        return "\n".join(output)

    # ==================== Content CRUD Handlers ====================

    # Forum Handlers
    elif name == "mybb_forum_list":
        forums = db.list_forums()
        if not forums:
            return "No forums found."

        lines = ["# MyBB Forums\n", "| FID | Name | Type | Parent | Threads | Posts |", "|-----|------|------|--------|---------|-------|"]
        for f in forums:
            forum_type = "Category" if f['type'] == 'c' else "Forum"
            lines.append(f"| {f['fid']} | {f['name']} | {forum_type} | {f['pid']} | {f['threads']} | {f['posts']} |")
        return "\n".join(lines)

    elif name == "mybb_forum_read":
        fid = args.get("fid")
        if not fid:
            return "Error: 'fid' is required."

        forum = db.get_forum(fid)
        if not forum:
            return f"Forum {fid} not found."

        forum_type = "Category" if forum['type'] == 'c' else "Forum"
        status = "Active" if forum['active'] else "Inactive"
        posting = "Open" if forum['open'] else "Closed"

        return (
            f"# Forum: {forum['name']}\n\n"
            f"**FID**: {forum['fid']}\n"
            f"**Type**: {forum_type}\n"
            f"**Description**: {forum['description']}\n"
            f"**Parent**: {forum['pid']}\n"
            f"**Status**: {status} | {posting}\n"
            f"**Order**: {forum['disporder']}\n\n"
            f"## Statistics\n"
            f"- Threads: {forum['threads']}\n"
            f"- Posts: {forum['posts']}\n"
            f"- Unapproved Threads: {forum['unapprovedthreads']}\n"
            f"- Unapproved Posts: {forum['unapprovedposts']}"
        )

    elif name == "mybb_forum_create":
        name = args.get("name")
        if not name:
            return "Error: 'name' is required."

        fid = db.create_forum(
            name=name,
            description=args.get("description", ""),
            forum_type=args.get("type", "f"),
            pid=args.get("pid", 0),
            parentlist=args.get("parentlist", ""),
            disporder=args.get("disporder", 1)
        )

        return f"# Forum Created\n\nForum '{name}' created with FID: {fid}"

    elif name == "mybb_forum_update":
        fid = args.get("fid")
        if not fid:
            return "Error: 'fid' is required."

        # Build kwargs from args
        updates = {}
        for key in ['name', 'description', 'type', 'disporder', 'active', 'open']:
            if key in args and args[key] is not None:
                updates[key] = args[key]

        if not updates:
            return "Error: No update fields provided."

        success = db.update_forum(fid, **updates)
        if success:
            return f"# Forum Updated\n\nForum {fid} updated successfully."
        else:
            return f"Error: Failed to update forum {fid}."

    elif name == "mybb_forum_delete":
        fid = args.get("fid")
        if not fid:
            return "Error: 'fid' is required."

        # Check if forum has content
        forum = db.get_forum(fid)
        if not forum:
            return f"Error: Forum {fid} not found."

        if forum['threads'] > 0 or forum['posts'] > 0:
            return (
                f"# Cannot Delete Forum\n\n"
                f"Forum {fid} has {forum['threads']} threads and {forum['posts']} posts.\n"
                f"Please move or delete all content first."
            )

        success = db.delete_forum(fid)
        if success:
            return f"# Forum Deleted\n\nForum {fid} deleted successfully."
        else:
            return f"Error: Failed to delete forum {fid}."

    # Thread Handlers
    elif name == "mybb_thread_list":
        fid = args.get("fid")
        limit = args.get("limit", 50)
        offset = args.get("offset", 0)

        threads = db.list_threads(fid=fid, limit=limit, offset=offset)
        if not threads:
            return "No threads found."

        from datetime import datetime
        lines = [f"# Threads ({len(threads)} found)\n", "| TID | Forum | Subject | Author | Replies | Views | Last Post |", "|-----|-------|---------|--------|---------|-------|-----------|"]

        for t in threads:
            lastpost = datetime.fromtimestamp(t['lastpost']).strftime('%Y-%m-%d %H:%M')
            lines.append(f"| {t['tid']} | {t['fid']} | {t['subject']} | {t['username']} | {t['replies']} | {t['views']} | {lastpost} |")

        return "\n".join(lines)

    elif name == "mybb_thread_read":
        tid = args.get("tid")
        if not tid:
            return "Error: 'tid' is required."

        thread = db.get_thread(tid)
        if not thread:
            return f"Thread {tid} not found."

        from datetime import datetime
        created = datetime.fromtimestamp(thread['dateline']).strftime('%Y-%m-%d %H:%M')
        lastpost = datetime.fromtimestamp(thread['lastpost']).strftime('%Y-%m-%d %H:%M')
        visibility = {1: "Visible", 0: "Unapproved", -1: "Deleted"}.get(thread['visible'], "Unknown")

        return (
            f"# Thread: {thread['subject']}\n\n"
            f"**TID**: {thread['tid']}\n"
            f"**Forum**: {thread['fid']}\n"
            f"**Author**: {thread['username']} (UID: {thread['uid']})\n"
            f"**Created**: {created}\n"
            f"**Status**: {visibility} | {'Closed' if thread['closed'] else 'Open'} | {'Sticky' if thread['sticky'] else 'Normal'}\n\n"
            f"## Statistics\n"
            f"- Replies: {thread['replies']}\n"
            f"- Views: {thread['views']}\n"
            f"- First Post: {thread['firstpost']}\n"
            f"- Last Post: {lastpost} by {thread['lastposter']}\n"
            f"- Unapproved Posts: {thread['unapprovedposts']}\n"
            f"- Deleted Posts: {thread['deletedposts']}"
        )

    elif name == "mybb_thread_create":
        fid = args.get("fid")
        subject = args.get("subject")
        message = args.get("message")

        if not all([fid, subject, message]):
            return "Error: 'fid', 'subject', and 'message' are required."

        uid = args.get("uid", 1)
        username = args.get("username", "Admin")
        prefix = args.get("prefix", 0)

        # Atomic creation: first post, then thread
        # Create the post first (we need its pid for thread.firstpost)
        pid = db.create_post(
            tid=0,  # Temporary, will update after thread creation
            fid=fid,
            subject=subject,
            message=message,
            uid=uid,
            username=username
        )

        # Create the thread with the first post pid
        tid = db.create_thread(
            fid=fid,
            subject=subject,
            uid=uid,
            username=username,
            firstpost_pid=pid,
            message=message,
            prefix=prefix
        )

        # Update the post's tid
        with db.cursor() as cur:
            cur.execute(f"UPDATE {db.table('posts')} SET tid = %s WHERE pid = %s", (tid, pid))

        # Update forum counters
        db.update_forum_counters(fid, threads_delta=1, posts_delta=1)

        return f"# Thread Created\n\nThread '{subject}' created with TID: {tid} (First post PID: {pid})"

    elif name == "mybb_thread_update":
        tid = args.get("tid")
        if not tid:
            return "Error: 'tid' is required."

        # Build kwargs from args
        updates = {}
        for key in ['subject', 'prefix', 'fid', 'closed', 'sticky', 'visible']:
            if key in args and args[key] is not None:
                updates[key] = args[key]

        if not updates:
            return "Error: No update fields provided."

        success = db.update_thread(tid, **updates)
        if success:
            return f"# Thread Updated\n\nThread {tid} updated successfully."
        else:
            return f"Error: Failed to update thread {tid}."

    elif name == "mybb_thread_delete":
        tid = args.get("tid")
        soft = args.get("soft", True)

        if not tid:
            return "Error: 'tid' is required."

        # Get thread info for counter updates
        thread = db.get_thread(tid)
        if not thread:
            return f"Error: Thread {tid} not found."

        # Delete thread
        success = db.delete_thread(tid, soft=soft)
        if success:
            # Update forum counters (only for soft delete, hard delete should handle separately)
            if soft:
                # Soft delete: decrement by making negative (threads counter stays same in MyBB)
                # Actually, MyBB keeps soft-deleted in counters until permanent delete
                pass
            else:
                # Hard delete: update counters
                post_count = thread['replies'] + 1  # replies + first post
                db.update_forum_counters(thread['fid'], threads_delta=-1, posts_delta=-post_count)

            delete_type = "soft deleted" if soft else "permanently deleted"
            return f"# Thread Deleted\n\nThread {tid} {delete_type} successfully."
        else:
            return f"Error: Failed to delete thread {tid}."

    elif name == "mybb_thread_move":
        tid = args.get("tid")
        new_fid = args.get("new_fid")

        if not tid or not new_fid:
            return "Error: 'tid' and 'new_fid' are required."

        # Get thread info
        thread = db.get_thread(tid)
        if not thread:
            return f"Error: Thread {tid} not found."

        old_fid = thread['fid']
        if old_fid == new_fid:
            return "Error: Thread is already in that forum."

        # Move thread
        success = db.move_thread(tid, new_fid)
        if success:
            # Update counters for both forums
            post_count = thread['replies'] + 1
            db.update_forum_counters(old_fid, threads_delta=-1, posts_delta=-post_count)
            db.update_forum_counters(new_fid, threads_delta=1, posts_delta=post_count)

            # Update all posts in thread to new forum
            with db.cursor() as cur:
                cur.execute(f"UPDATE {db.table('posts')} SET fid = %s WHERE tid = %s", (new_fid, tid))

            return f"# Thread Moved\n\nThread {tid} moved from forum {old_fid} to {new_fid}."
        else:
            return f"Error: Failed to move thread {tid}."

    # Post Handlers
    elif name == "mybb_post_list":
        tid = args.get("tid")
        limit = args.get("limit", 50)
        offset = args.get("offset", 0)

        posts = db.list_posts(tid=tid, limit=limit, offset=offset)
        if not posts:
            return "No posts found."

        from datetime import datetime
        lines = [f"# Posts ({len(posts)} found)\n", "| PID | TID | Author | Date | Subject | Preview |", "|-----|-----|--------|------|---------|---------|"]

        for p in posts:
            date = datetime.fromtimestamp(p['dateline']).strftime('%Y-%m-%d')
            preview = p['message'][:50].replace('\n', ' ').replace('|', '\\|')
            if len(p['message']) > 50:
                preview += "..."
            lines.append(f"| {p['pid']} | {p['tid']} | {p['username']} | {date} | {p['subject']} | {preview} |")

        return "\n".join(lines)

    elif name == "mybb_post_read":
        pid = args.get("pid")
        if not pid:
            return "Error: 'pid' is required."

        post = db.get_post(pid)
        if not post:
            return f"Post {pid} not found."

        from datetime import datetime
        created = datetime.fromtimestamp(post['dateline']).strftime('%Y-%m-%d %H:%M')
        visibility = {1: "Visible", 0: "Unapproved", -1: "Deleted"}.get(post['visible'], "Unknown")

        edit_info = ""
        if post['edituid']:
            edit_time = datetime.fromtimestamp(post['edittime']).strftime('%Y-%m-%d %H:%M')
            edit_info = f"\n**Last Edited**: {edit_time} by UID {post['edituid']}"
            if post['editreason']:
                edit_info += f"\n**Edit Reason**: {post['editreason']}"

        return (
            f"# Post {pid}\n\n"
            f"**Thread**: {post['tid']}\n"
            f"**Forum**: {post['fid']}\n"
            f"**Subject**: {post['subject']}\n"
            f"**Author**: {post['username']} (UID: {post['uid']})\n"
            f"**Posted**: {created}\n"
            f"**Status**: {visibility}{edit_info}\n\n"
            f"## Message\n\n{post['message']}"
        )

    elif name == "mybb_post_create":
        tid = args.get("tid")
        message = args.get("message")

        if not tid or not message:
            return "Error: 'tid' and 'message' are required."

        # Get thread info
        thread = db.get_thread(tid)
        if not thread:
            return f"Error: Thread {tid} not found."

        subject = args.get("subject", f"RE: {thread['subject']}")
        uid = args.get("uid", 1)
        username = args.get("username", "Admin")
        replyto = args.get("replyto", 0)

        # Create post
        pid = db.create_post(
            tid=tid,
            fid=thread['fid'],
            subject=subject,
            message=message,
            uid=uid,
            username=username,
            replyto=replyto
        )

        # Update counters
        db.update_thread_counters(tid, replies_delta=1)
        db.update_forum_counters(thread['fid'], posts_delta=1)

        # Update thread lastpost
        import time
        dateline = int(time.time())
        db.update_thread_lastpost(tid, dateline, username, uid)

        return f"# Post Created\n\nPost created with PID: {pid} in thread {tid}"

    elif name == "mybb_post_update":
        pid = args.get("pid")
        if not pid:
            return "Error: 'pid' is required."

        message = args.get("message")
        subject = args.get("subject")
        edituid = args.get("edituid")
        editreason = args.get("editreason", "")

        if not any([message, subject]):
            return "Error: Provide at least 'message' or 'subject' to update."

        success = db.update_post(
            pid=pid,
            message=message,
            subject=subject,
            edituid=edituid,
            editreason=editreason
        )

        if success:
            return f"# Post Updated\n\nPost {pid} updated successfully."
        else:
            return f"Error: Failed to update post {pid}."

    elif name == "mybb_post_delete":
        pid = args.get("pid")
        soft = args.get("soft", True)

        if not pid:
            return "Error: 'pid' is required."

        # Get post info for counter updates
        post = db.get_post(pid)
        if not post:
            return f"Error: Post {pid} not found."

        # Don't allow deleting first post (should delete thread instead)
        thread = db.get_thread(post['tid'])
        if thread and thread['firstpost'] == pid:
            return "Error: Cannot delete first post. Delete the thread instead."

        # Delete post
        success = db.delete_post(pid, soft=soft)
        if success:
            # Update counters (only for hard delete)
            if not soft:
                db.update_thread_counters(post['tid'], replies_delta=-1)
                db.update_forum_counters(post['fid'], posts_delta=-1)

            delete_type = "soft deleted" if soft else "permanently deleted"
            return f"# Post Deleted\n\nPost {pid} {delete_type} successfully."
        else:
            return f"Error: Failed to delete post {pid}."

    # ==================== Search Handlers ====================

    elif name == "mybb_search_posts":
        query = args.get("query")
        if not query:
            return "Error: 'query' parameter is required."

        results = db.search_posts(
            query=query,
            forums=args.get("forums"),
            author=args.get("author"),
            date_from=args.get("date_from"),
            date_to=args.get("date_to"),
            limit=args.get("limit", 25),
            offset=args.get("offset", 0)
        )

        if not results:
            return f"# Post Search Results\n\nNo posts found matching '{query}'."

        lines = [f"# Post Search Results ({len(results)} found)\n"]
        lines.append("| PID | Thread | Author | Date | Preview |")
        lines.append("|-----|--------|--------|------|---------|")

        for post in results:
            from datetime import datetime
            date_str = datetime.fromtimestamp(post['dateline']).strftime('%Y-%m-%d')
            # Truncate message for preview
            preview = post['message'][:100].replace('\n', ' ').replace('|', '\\|')
            if len(post['message']) > 100:
                preview += "..."
            lines.append(
                f"| {post['pid']} | {post['thread_subject']} | {post['username']} | {date_str} | {preview} |"
            )

        return "\n".join(lines)

    elif name == "mybb_search_threads":
        query = args.get("query")
        if not query:
            return "Error: 'query' parameter is required."

        results = db.search_threads(
            query=query,
            forums=args.get("forums"),
            author=args.get("author"),
            prefix=args.get("prefix"),
            limit=args.get("limit", 25),
            offset=args.get("offset", 0)
        )

        if not results:
            return f"# Thread Search Results\n\nNo threads found matching '{query}'."

        lines = [f"# Thread Search Results ({len(results)} found)\n"]
        lines.append("| TID | Subject | Author | Replies | Views | Last Post |")
        lines.append("|-----|---------|--------|---------|-------|-----------|")

        for thread in results:
            from datetime import datetime
            last_post = datetime.fromtimestamp(thread['lastpost']).strftime('%Y-%m-%d %H:%M')
            lines.append(
                f"| {thread['tid']} | {thread['subject']} | {thread['username']} | "
                f"{thread['replies']} | {thread['views']} | {last_post} |"
            )

        return "\n".join(lines)

    elif name == "mybb_search_users":
        query = args.get("query")
        if not query:
            return "Error: 'query' parameter is required."

        field = args.get("field", "username")

        try:
            results = db.search_users(
                query=query,
                field=field,
                limit=args.get("limit", 25),
                offset=args.get("offset", 0)
            )
        except ValueError as e:
            return f"Error: {e}"

        if not results:
            return f"# User Search Results\n\nNo users found matching '{query}' in {field}."

        lines = [f"# User Search Results ({len(results)} found)\n"]
        lines.append("| UID | Username | Group | Posts | Threads | Registered |")
        lines.append("|-----|----------|-------|-------|---------|------------|")

        for user in results:
            from datetime import datetime
            reg_date = datetime.fromtimestamp(user['regdate']).strftime('%Y-%m-%d')
            lines.append(
                f"| {user['uid']} | {user['username']} | {user['usergroup']} | "
                f"{user['postnum']} | {user['threadnum']} | {reg_date} |"
            )

        return "\n".join(lines)

    elif name == "mybb_search_advanced":
        query = args.get("query")
        if not query:
            return "Error: 'query' parameter is required."

        results = db.search_advanced(
            query=query,
            content_type=args.get("content_type", "both"),
            forums=args.get("forums"),
            date_from=args.get("date_from"),
            date_to=args.get("date_to"),
            sort_by=args.get("sort_by", "date"),
            limit=args.get("limit", 25),
            offset=args.get("offset", 0)
        )

        lines = [f"# Advanced Search Results for '{query}'\n"]

        if "posts" in results:
            posts = results["posts"]
            lines.append(f"\n## Posts ({len(posts)} found)\n")
            if posts:
                lines.append("| PID | Thread | Author | Date | Preview |")
                lines.append("|-----|--------|--------|------|---------|")
                for post in posts:
                    from datetime import datetime
                    date_str = datetime.fromtimestamp(post['dateline']).strftime('%Y-%m-%d')
                    preview = post['message'][:80].replace('\n', ' ').replace('|', '\\|')
                    if len(post['message']) > 80:
                        preview += "..."
                    lines.append(
                        f"| {post['pid']} | {post['thread_subject']} | {post['username']} | {date_str} | {preview} |"
                    )

        if "threads" in results:
            threads = results["threads"]
            lines.append(f"\n## Threads ({len(threads)} found)\n")
            if threads:
                lines.append("| TID | Subject | Author | Replies | Views |")
                lines.append("|-----|---------|--------|---------|-------|")
                for thread in threads:
                    lines.append(
                        f"| {thread['tid']} | {thread['subject']} | {thread['username']} | "
                        f"{thread['replies']} | {thread['views']} |"
                    )

        if not results.get("posts") and not results.get("threads"):
            lines.append("\nNo results found.")

        return "\n".join(lines)

    # ==================== Admin Tool Handlers: Settings ====================

    elif name == "mybb_setting_get":
        setting_name = args.get("name")
        if not setting_name:
            return "Error: 'name' parameter is required."

        setting = db.get_setting(setting_name)
        if not setting:
            return f"Setting '{setting_name}' not found."

        lines = [
            f"# Setting: {setting['title']}\n",
            f"**Name:** `{setting['name']}`",
            f"**Value:** `{setting['value']}`",
            f"**Description:** {setting['description']}",
            f"**Group ID:** {setting['gid']}",
            f"**Display Order:** {setting['disporder']}",
            f"**Options Code:** {setting['optionscode']}",
        ]
        return "\n".join(lines)

    elif name == "mybb_setting_set":
        setting_name = args.get("name")
        value = args.get("value")
        if not setting_name or value is None:
            return "Error: 'name' and 'value' parameters are required."

        # Check if setting exists
        setting = db.get_setting(setting_name)
        if not setting:
            return f"Setting '{setting_name}' not found."

        # Update setting
        success = db.set_setting(setting_name, value)
        if not success:
            return f"Failed to update setting '{setting_name}'."

        # Rebuild settings cache
        db.rebuild_cache("settings")

        return f"Setting '{setting_name}' updated to '{value}'. Settings cache rebuilt."

    elif name == "mybb_setting_list":
        gid = args.get("gid")
        settings = db.list_settings(gid=gid)

        if not settings:
            return "No settings found."

        lines = [f"# MyBB Settings ({len(settings)} total)\n"]
        if gid is not None:
            lines[0] = f"# MyBB Settings for Group {gid} ({len(settings)} total)\n"

        lines.extend([
            "| Name | Title | Value | Group |",
            "|------|-------|-------|-------|"
        ])

        for setting in settings[:100]:
            value_preview = setting['value'][:50] if setting['value'] else ""
            if len(setting['value']) > 50:
                value_preview += "..."
            lines.append(
                f"| {setting['name']} | {setting['title']} | {value_preview} | {setting['gid']} |"
            )

        if len(settings) > 100:
            lines.append(f"\n*...{len(settings) - 100} more*")

        return "\n".join(lines)

    elif name == "mybb_settinggroup_list":
        groups = db.list_setting_groups()

        if not groups:
            return "No setting groups found."

        lines = [
            f"# MyBB Setting Groups ({len(groups)} total)\n",
            "| GID | Name | Title | Description |",
            "|-----|------|-------|-------------|"
        ]

        for group in groups:
            desc_preview = group['description'][:50] if group['description'] else ""
            if len(group['description']) > 50:
                desc_preview += "..."
            lines.append(
                f"| {group['gid']} | {group['name']} | {group['title']} | {desc_preview} |"
            )

        return "\n".join(lines)

    # ==================== Admin Tool Handlers: Cache ====================

    elif name == "mybb_cache_read":
        title = args.get("title")
        if not title:
            return "Error: 'title' parameter is required."

        cache_data = db.read_cache(title)
        if cache_data is None:
            return f"Cache '{title}' not found."

        # Return cache data with size info
        size = len(cache_data)
        lines = [
            f"# Cache: {title}\n",
            f"**Size:** {size} bytes",
            f"**Data Type:** PHP serialized",
            "\n```",
            cache_data[:1000] if len(cache_data) <= 1000 else cache_data[:1000] + "\n... (truncated)",
            "```"
        ]
        if size > 1000:
            lines.append(f"\n*Full size: {size} bytes (showing first 1000)*")

        return "\n".join(lines)

    elif name == "mybb_cache_rebuild":
        cache_type = args.get("cache_type", "all")
        result = db.rebuild_cache(cache_type)

        return f"**{result['message']}** ({result['rows_affected']} cache entries cleared)\n\nMyBB will regenerate these caches on next access."

    elif name == "mybb_cache_list":
        caches = db.list_caches()

        if not caches:
            return "No cache entries found."

        lines = [
            f"# MyBB Cache Entries ({len(caches)} total)\n",
            "| Title | Size (bytes) |",
            "|-------|--------------|"
        ]

        for cache in caches:
            lines.append(f"| {cache['title']} | {cache['size']:,} |")

        total_size = sum(c['size'] for c in caches)
        lines.append(f"\n**Total Cache Size:** {total_size:,} bytes")

        return "\n".join(lines)

    elif name == "mybb_cache_clear":
        title = args.get("title")
        success = db.clear_cache(title)

        if not success:
            if title:
                return f"Cache '{title}' not found or already cleared."
            else:
                return "No caches found to clear."

        if title:
            return f"Cache '{title}' cleared successfully."
        else:
            return "All caches cleared successfully."

    # ==================== Admin Tool Handlers: Statistics ====================

    elif name == "mybb_stats_forum":
        stats = db.get_forum_stats()

        lines = [
            "# Forum Statistics\n",
            f"**Total Users:** {stats['total_users']:,}",
            f"**Total Threads:** {stats['total_threads']:,}",
            f"**Total Posts:** {stats['total_posts']:,}",
        ]

        if stats['newest_member']:
            from datetime import datetime
            reg_date = datetime.fromtimestamp(stats['newest_member']['regdate']).strftime('%Y-%m-%d %H:%M:%S')
            lines.extend([
                "\n## Newest Member",
                f"**Username:** {stats['newest_member']['username']}",
                f"**UID:** {stats['newest_member']['uid']}",
                f"**Registered:** {reg_date}",
            ])

        return "\n".join(lines)

    elif name == "mybb_stats_board":
        stats = db.get_board_stats()

        lines = [
            "# Board Statistics\n",
            "## Overview",
            f"**Total Forums:** {stats['total_forums']:,}",
            f"**Total Users:** {stats['total_users']:,}",
            f"**Total Threads:** {stats['total_threads']:,}",
            f"**Total Posts:** {stats['total_posts']:,}",
            f"**Total Private Messages:** {stats['total_private_messages']:,}",
        ]

        if stats['latest_post']:
            from datetime import datetime
            post_date = datetime.fromtimestamp(stats['latest_post']['dateline']).strftime('%Y-%m-%d %H:%M:%S')
            lines.extend([
                "\n## Latest Post",
                f"**Subject:** {stats['latest_post']['subject']}",
                f"**Author:** {stats['latest_post']['username']}",
                f"**Date:** {post_date}",
                f"**Post ID:** {stats['latest_post']['pid']}",
                f"**Thread ID:** {stats['latest_post']['tid']}",
            ])

        if stats['most_active_forum']:
            lines.extend([
                "\n## Most Active Forum",
                f"**Name:** {stats['most_active_forum']['name']}",
                f"**Threads:** {stats['most_active_forum']['threads']:,}",
                f"**Posts:** {stats['most_active_forum']['posts']:,}",
                f"**Forum ID:** {stats['most_active_forum']['fid']}",
            ])

        return "\n".join(lines)

    # ==================== Moderation Handlers ====================

    elif name == "mybb_mod_close_thread":
        tid = args.get("tid")
        closed = args.get("closed", True)

        if not tid:
            return "Error: 'tid' is required."

        success = db.close_thread(tid, closed)
        if success:
            status = "closed" if closed else "opened"
            return f"# Thread {status.title()}\n\nThread {tid} has been {status} successfully."
        else:
            return f"Error: Failed to update thread {tid}."

    elif name == "mybb_mod_stick_thread":
        tid = args.get("tid")
        sticky = args.get("sticky", True)

        if not tid:
            return "Error: 'tid' is required."

        success = db.stick_thread(tid, sticky)
        if success:
            status = "sticked" if sticky else "unsticked"
            return f"# Thread {status.title()}\n\nThread {tid} has been {status} successfully."
        else:
            return f"Error: Failed to update thread {tid}."

    elif name == "mybb_mod_approve_thread":
        tid = args.get("tid")
        approve = args.get("approve", True)

        if not tid:
            return "Error: 'tid' is required."

        success = db.approve_thread(tid, approve)
        if success:
            status = "approved" if approve else "unapproved"
            return f"# Thread {status.title()}\n\nThread {tid} has been {status} successfully."
        else:
            return f"Error: Failed to update thread {tid}."

    elif name == "mybb_mod_approve_post":
        pid = args.get("pid")
        approve = args.get("approve", True)

        if not pid:
            return "Error: 'pid' is required."

        success = db.approve_post(pid, approve)
        if success:
            status = "approved" if approve else "unapproved"
            return f"# Post {status.title()}\n\nPost {pid} has been {status} successfully."
        else:
            return f"Error: Failed to update post {pid}."

    elif name == "mybb_mod_soft_delete_thread":
        tid = args.get("tid")
        delete = args.get("delete", True)

        if not tid:
            return "Error: 'tid' is required."

        # Use existing delete_thread method with soft parameter
        success = db.delete_thread(tid, soft=delete)
        if success:
            status = "soft deleted" if delete else "restored"
            return f"# Thread {status.title()}\n\nThread {tid} has been {status} successfully."
        else:
            return f"Error: Failed to update thread {tid}."

    elif name == "mybb_mod_soft_delete_post":
        pid = args.get("pid")
        delete = args.get("delete", True)

        if not pid:
            return "Error: 'pid' is required."

        success = db.soft_delete_post(pid, delete)
        if success:
            status = "soft deleted" if delete else "restored"
            return f"# Post {status.title()}\n\nPost {pid} has been {status} successfully."
        else:
            return f"Error: Failed to update post {pid}."

    elif name == "mybb_modlog_list":
        uid = args.get("uid")
        fid = args.get("fid")
        tid = args.get("tid")
        limit = args.get("limit", 50)

        entries = db.list_modlog_entries(uid=uid, fid=fid, tid=tid, limit=limit)

        if not entries:
            return "No moderation log entries found."

        from datetime import datetime
        lines = [
            f"# Moderation Log ({len(entries)} entries)\n",
            "| Log ID | User ID | Forum | Thread | Post | Action | Date |",
            "|--------|---------|-------|--------|------|--------|------|"
        ]

        for entry in entries:
            date = datetime.fromtimestamp(entry['dateline']).strftime('%Y-%m-%d %H:%M')
            lines.append(
                f"| {entry['lid']} | {entry['uid']} | {entry['fid']} | {entry['tid']} | {entry['pid']} | {entry['action']} | {date} |"
            )

        return "\n".join(lines)

    elif name == "mybb_modlog_add":
        uid = args.get("uid")
        fid = args.get("fid", 0)
        tid = args.get("tid", 0)
        pid = args.get("pid", 0)
        action = args.get("action")
        data = args.get("data", "")
        ipaddress = args.get("ipaddress", "")

        if not uid or not action:
            return "Error: 'uid' and 'action' are required."

        log_id = db.add_modlog_entry(uid, fid, tid, pid, action, data, ipaddress)

        if log_id:
            return f"# Moderation Log Entry Added\n\nLog entry created with ID {log_id}."
        else:
            return "Error: Failed to create moderation log entry."

    # ==================== User Management Handlers ====================

    elif name == "mybb_user_get":
        uid = args.get("uid")
        username = args.get("username")

        if not uid and not username:
            return "Error: Either 'uid' or 'username' is required."

        user = db.get_user(uid=uid, username=username, sanitize=True)

        if not user:
            identifier = f"UID {uid}" if uid else f"username '{username}'"
            return f"Error: User not found ({identifier})."

        # Format user information
        lines = [
            "# User Information\n",
            f"**User ID:** {user['uid']}",
            f"**Username:** {user['username']}",
            f"**Usergroup:** {user['usergroup']}",
            f"**Email:** {user.get('email', 'N/A')}",
            f"**Post Count:** {user.get('postnum', 0)}",
            f"**Thread Count:** {user.get('threadnum', 0)}",
            f"**Registration Date:** {user.get('regdate', 'N/A')}",
            f"**User Title:** {user.get('usertitle', 'N/A')}",
        ]

        if user.get('additionalgroups'):
            lines.append(f"**Additional Groups:** {user['additionalgroups']}")

        return "\n".join(lines)

    elif name == "mybb_user_list":
        usergroup = args.get("usergroup")
        limit = args.get("limit", 50)
        offset = args.get("offset", 0)

        users = db.list_users(usergroup=usergroup, limit=limit, offset=offset)

        if not users:
            return "No users found."

        lines = [
            f"# Users ({len(users)} found)\n",
            "| UID | Username | Usergroup | Posts | Threads |",
            "|-----|----------|-----------|-------|---------|"
        ]

        for user in users:
            lines.append(
                f"| {user['uid']} | {user['username']} | {user['usergroup']} | {user.get('postnum', 0)} | {user.get('threadnum', 0)} |"
            )

        return "\n".join(lines)

    elif name == "mybb_user_update_group":
        uid = args.get("uid")
        usergroup = args.get("usergroup")
        additionalgroups = args.get("additionalgroups")

        if not uid or not usergroup:
            return "Error: 'uid' and 'usergroup' are required."

        success = db.update_user_group(uid, usergroup, additionalgroups)

        if success:
            return f"# User Group Updated\n\nUser {uid} has been assigned to usergroup {usergroup}."
        else:
            return f"Error: Failed to update user {uid}."

    elif name == "mybb_user_ban":
        uid = args.get("uid")
        gid = args.get("gid")
        admin = args.get("admin")
        dateline = args.get("dateline")
        bantime = args.get("bantime", "---")
        reason = args.get("reason", "")

        if not uid or not gid or not admin or not dateline:
            return "Error: 'uid', 'gid', 'admin', and 'dateline' are required."

        ban_id = db.ban_user(uid, gid, admin, dateline, bantime, reason)

        if ban_id:
            return f"# User Banned\n\nUser {uid} has been banned. Ban ID: {ban_id}."
        else:
            return f"Error: Failed to ban user {uid}."

    elif name == "mybb_user_unban":
        uid = args.get("uid")

        if not uid:
            return "Error: 'uid' is required."

        success = db.unban_user(uid)

        if success:
            return f"# User Unbanned\n\nUser {uid} has been unbanned successfully."
        else:
            return f"Error: Failed to unban user {uid} (may not be banned)."

    elif name == "mybb_usergroup_list":
        groups = db.list_usergroups()

        if not groups:
            return "No usergroups found."

        lines = [
            f"# Usergroups ({len(groups)} total)\n",
            "| GID | Title | Type |",
            "|-----|-------|------|"
        ]

        for group in groups:
            group_type = "Admin" if group.get('cancp') == 1 else ("Moderator" if group.get('canmodcp') == 1 else "User")
            lines.append(f"| {group['gid']} | {group['title']} | {group_type} |")

        return "\n".join(lines)

    return f"Unknown tool: {name}"


async def run_server():
    """Run the MCP server."""
    config = load_config()
    logger.info(f"Starting MyBB MCP Server")
    logger.info(f"MyBB Root: {config.mybb_root}")
    logger.info(f"Database: {config.db.database}")

    server = create_server(config)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
