# MCP Tools Reference

Complete reference for all MyBB MCP server tools available in the `mybb_mcp` server.

## Overview

The MyBB MCP server provides **102 tools** across **15 categories** for comprehensive MyBB forum management through Claude Code.

### Tool Categories

| Category | Tools | Description |
|----------|-------|-------------|
| [Templates](templates.md) | 9 | Template set management, read/write, batch operations, find/replace |
| [Themes & Stylesheets](themes_stylesheets.md) | 6 | Theme and stylesheet CRUD operations |
| [Plugins](plugins.md) | 15 | Plugin scaffolding, lifecycle, hooks discovery, analysis |
| [Forums](forums_threads_posts.md#forums) | 5 | Forum CRUD operations and hierarchy management |
| [Threads](forums_threads_posts.md#threads) | 6 | Thread CRUD operations, moving, status changes |
| [Posts](forums_threads_posts.md#posts) | 5 | Post CRUD operations and editing |
| [Users](users_moderation.md#users) | 6 | User management, groups, banning |
| [Moderation](users_moderation.md#moderation) | 8 | Moderation actions and logging |
| [Search](search.md) | 4 | Content search across posts, threads, users |
| [Admin & Settings](admin_settings.md) | 11 | Settings management, cache control, board statistics |
| [Tasks](tasks.md) | 5 | Scheduled task management and logging |
| [Disk Sync](disk_sync.md) | 5 | Template/stylesheet disk synchronization |
| [Server Orchestration](orchestration.md) | 5 | Development server lifecycle and log querying |
| [Language Validation](languages.md) | 3 | Plugin language file validation and stub generation |
| [Database](database.md) | 1 | Direct database queries (read-only) |

**Total:** 102 tools

## Quick Reference

### Most Common Tools

**Templates:**
- `mybb_list_template_sets` - List all template sets
- `mybb_read_template` - Read template content
- `mybb_write_template` - Update template content
- `mybb_template_find_replace` - Bulk find/replace across templates

**Plugins:**
- `mybb_create_plugin` - Generate plugin scaffold
- `mybb_list_hooks` - List available hooks
- `mybb_plugin_install` - Full plugin installation with lifecycle
- `mybb_plugin_status` - Check plugin state

**Content Management:**
- `mybb_forum_list` - List all forums
- `mybb_thread_create` - Create new thread
- `mybb_post_create` - Create new post
- `mybb_search_posts` - Search post content

**Administration:**
- `mybb_setting_get` / `mybb_setting_set` - Manage board settings
- `mybb_cache_rebuild` - Rebuild caches
- `mybb_stats_board` - Board statistics

**Server Orchestration:**
- `mybb_server_start` - Start development server
- `mybb_server_stop` - Stop development server
- `mybb_server_status` - Check server status
- `mybb_server_logs` - Query server logs with filtering

**Language Validation:**
- `mybb_lang_validate` - Validate plugin language files
- `mybb_lang_generate_stub` - Generate missing definitions
- `mybb_lang_scan_usage` - Scan files for language usage

## Tool Documentation Structure

Each tool page includes:
- **Description** - What the tool does
- **Parameters** - Parameter name, type, required/optional, default value
- **Returns** - Return format and structure
- **Examples** - Usage examples
- **Notes** - Behavioral details and caveats

## Parameter Conventions

### Common Types
- `string` - Text value
- `int` - Integer number
- `bool` - Boolean (true/false)
- `array` - List of values (JSON format)
- `object` - Key-value object (JSON format)

### Required vs Optional
- **REQUIRED** - Must be provided
- **optional** - Can be omitted
- **default=X** - Optional with default value

### Special Values
- Template Set IDs: `-2` = master templates, `-1` = global templates, `≥1` = custom template sets
- Forum/Thread/Post IDs: `0` or omitted = not applicable
- Limits: Many tools use `default=25, max=100` for pagination

## Navigation

Browse by category:
- **[Templates](templates.md)** - Template management
- **[Themes & Stylesheets](themes_stylesheets.md)** - Visual design
- **[Plugins](plugins.md)** - Plugin development
- **[Forums/Threads/Posts](forums_threads_posts.md)** - Content management
- **[Users & Moderation](users_moderation.md)** - User management
- **[Search](search.md)** - Content search
- **[Admin & Settings](admin_settings.md)** - Configuration
- **[Tasks](tasks.md)** - Scheduled tasks
- **[Disk Sync](disk_sync.md)** - File synchronization
- **[Server Orchestration](orchestration.md)** - Development server management
- **[Language Validation](languages.md)** - Plugin language validation
- **[Database](database.md)** - Direct queries

---

See also: [Getting Started](../getting_started/index.md) | [Plugin Manager](../plugin_manager/index.md) | [Architecture](../architecture/index.md)
