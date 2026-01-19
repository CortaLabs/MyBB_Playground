# MCP Server Architecture

The MyBB MCP Server (`mybb_mcp/`) is a Python-based Model Context Protocol server that exposes MyBB operations to Claude Code through 85 tools. This document covers server initialization, the **modular handler architecture**, database connection management, and the connection pooling strategy.

## Architecture Overview

The MCP server uses a **modular handler architecture** that separates concerns:

```
mybb_mcp/mybb_mcp/
├── server.py           # Orchestration layer (116 lines)
├── tools_registry.py   # Tool definitions (1,105 lines, 85 tools)
├── config.py           # Configuration loading
├── handlers/           # Modular tool handlers (14 modules)
│   ├── __init__.py     # Exports dispatch_tool, HANDLER_REGISTRY
│   ├── dispatcher.py   # Central routing + registry population
│   ├── common.py       # Shared utilities (format_*, etc.)
│   ├── templates.py    # 8 template handlers
│   ├── themes.py       # 5 theme handlers
│   ├── plugins.py      # 15 plugin handlers
│   ├── content.py      # 16 forum/thread/post handlers
│   ├── users.py        # 6 user handlers
│   ├── moderation.py   # 8 moderation handlers
│   ├── search.py       # 4 search handlers
│   ├── admin.py        # 11 admin handlers
│   ├── tasks.py        # 6 task handlers
│   ├── sync.py         # 5 disk sync handlers
│   └── database.py     # 1 database handler
├── db/                 # Database operations
├── sync/               # Disk sync service
└── tools/              # Plugin scaffolding
```

**Key Metrics:**
- **server.py**: 116 lines (orchestration only)
- **tools_registry.py**: 1,105 lines (85 tool definitions)
- **handlers/**: 14 modules with 85 handlers total

## Server Initialization

The server is initialized through the `create_server()` function in `server.py`.

### Initialization Sequence

```python
# Initialization order (server.py):
1. Create MCP Server instance with name "mybb-mcp"
2. Initialize MyBBDatabase with config
3. Initialize DiskSyncService:
   - sync_root: {mybb_root}/../mybb_sync/
   - Automatically starts file watcher
4. Import ALL_TOOLS from tools_registry
5. Import dispatch_tool from handlers
6. Log handler registry status
7. Setup async handlers:
   - @server.list_tools() → returns ALL_TOOLS
   - @server.call_tool(name, arguments) → calls dispatch_tool()
```

### Server Instance Creation

```python
from .tools_registry import ALL_TOOLS
from .handlers import dispatch_tool, HANDLER_REGISTRY

server = Server("mybb-mcp")
config = load_config()
db = MyBBDatabase(config.db)

# Initialize disk sync
sync_root = config.mybb_root.parent / "mybb_sync"
sync_service = DiskSyncService(db, SyncConfig(sync_root=sync_root), config.mybb_url)
sync_service.start_watcher()

logger.info(f"Handler registry loaded: {len(HANDLER_REGISTRY)} handlers")
```

**Key Points:**
- Server name is hardcoded as `"mybb-mcp"`
- Tool definitions imported from `tools_registry.py`
- Handler dispatch imported from `handlers/` module
- DiskSyncService auto-starts file watcher in development mode

## Tool Registration

All tools are registered via the `all_tools` array and `@server.list_tools()` handler.

### Tool Categories

The server provides **85+ tools** across 9 categories:

#### A. Template Management Tools (8 tools)
- `mybb_list_template_sets` - List all template sets
- `mybb_list_templates` - List templates (filter by set/search)
- `mybb_read_template` - Read template HTML content
- `mybb_write_template` - Update or create template
- `mybb_list_template_groups` - List template groups
- `mybb_template_find_replace` - Find/replace across templates
- `mybb_template_batch_read` - Read multiple templates
- `mybb_template_batch_write` - Write multiple templates

#### B. Theme & Stylesheet Tools (6 tools)
- `mybb_list_themes` - List all themes
- `mybb_list_stylesheets` - List stylesheets (filter by theme)
- `mybb_read_stylesheet` - Read stylesheet CSS content
- `mybb_write_stylesheet` - Update stylesheet and refresh cache
- `mybb_template_outdated` - Find outdated templates
- `mybb_create_theme` - Create new theme (Plugin Manager)

#### C. Plugin Tools (12 tools)
- `mybb_list_plugins` - List plugins in directory
- `mybb_read_plugin` - Read plugin PHP source
- `mybb_create_plugin` - Create new plugin with scaffolding
- `mybb_analyze_plugin` - Analyze plugin structure
- `mybb_list_hooks` - List available MyBB hooks
- `mybb_hooks_discover` - Dynamically discover hooks
- `mybb_hooks_usage` - Find hook usage in plugins
- `mybb_plugin_list_installed` - List installed plugins
- `mybb_plugin_info` - Get plugin info
- `mybb_plugin_activate` - Activate plugin (cache only)
- `mybb_plugin_deactivate` - Deactivate plugin (cache only)
- `mybb_plugin_is_installed` - Check install status

#### D. Scheduled Task Tools (5 tools)
- `mybb_task_list` - List all scheduled tasks
- `mybb_task_get` - Get task details
- `mybb_task_enable` - Enable task
- `mybb_task_disable` - Disable task
- `mybb_task_update_nextrun` - Update next run time

#### E. Database Query Tool (1 tool)
- `mybb_db_query` - Execute read-only SELECT queries

#### F. Forum Management Tools (6 tools)
- `mybb_forum_list` - List forums with hierarchy
- `mybb_forum_read` - Get forum details
- `mybb_forum_create` - Create forum or category
- `mybb_forum_update` - Update forum properties
- `mybb_forum_delete` - Delete forum

#### G. Thread Management Tools (6 tools)
- `mybb_thread_list` - List threads (filter by forum)
- `mybb_thread_read` - Get thread details
- `mybb_thread_create` - Create thread with first post
- `mybb_thread_update` - Update thread properties
- `mybb_thread_delete` - Delete thread (soft/permanent)
- `mybb_thread_move` - Move thread to different forum

#### H. Post Management Tools (6 tools)
- `mybb_post_list` - List posts (filter by thread)
- `mybb_post_read` - Get post details
- `mybb_post_create` - Create post in thread
- `mybb_post_update` - Edit post with history
- `mybb_post_delete` - Delete post (soft/permanent)

#### I. Search Tools (4 tools)
- `mybb_search_posts` - Search post content
- `mybb_search_threads` - Search thread subjects
- `mybb_search_users` - Search users
- `mybb_search_advanced` - Combined search

**Additional categories:** Moderation (6 tools), User Management (5 tools), Settings (4 tools), Cache (4 tools), Statistics (2 tools), Disk Sync (6 tools)

### Tool Handler System (Modular Dispatcher)

Tool calls are routed through a **dictionary-based dispatcher** in `handlers/dispatcher.py`:

```python
# handlers/dispatcher.py
HANDLER_REGISTRY: dict[str, Callable] = {}

async def dispatch_tool(
    name: str,
    args: dict,
    db: MyBBDatabase,
    config: MyBBConfig,
    sync_service: DiskSyncService
) -> str:
    """Route tool call to appropriate handler."""
    if name not in HANDLER_REGISTRY:
        return f"Unknown tool: {name}"

    handler = HANDLER_REGISTRY[name]
    return await handler(args, db, config, sync_service)
```

**Handler Registration Pattern:**
```python
# handlers/templates.py
from .dispatcher import HANDLER_REGISTRY

async def handle_mybb_list_templates(args, db, config, sync_service) -> str:
    sid = args.get("sid")
    search = args.get("search")
    templates = db.list_templates(sid=sid, search=search)
    return format_template_list(templates)

# Register handler
HANDLER_REGISTRY["mybb_list_templates"] = handle_mybb_list_templates
```

**Key Characteristics:**
- Dictionary-based routing (O(1) lookup vs O(n) if-elif chain)
- All tools return formatted Markdown strings
- Consistent handler signature: `(args, db, config, sync_service) -> str`
- Errors caught and returned as user-friendly messages
- No exceptions propagate to MCP client
- Database queries use parameterized statements

### Handler Module Reference

| Module | Handlers | Tools |
|--------|----------|-------|
| `templates.py` | 8 | list_template_sets, list_templates, read_template, write_template, list_template_groups, template_find_replace, template_batch_read, template_batch_write |
| `themes.py` | 5 | list_themes, list_stylesheets, read_stylesheet, write_stylesheet, create_theme |
| `plugins.py` | 15 | list_plugins, read_plugin, create_plugin, analyze_plugin, list_hooks, hooks_discover, hooks_usage, plugin_list_installed, plugin_info, plugin_activate, plugin_deactivate, plugin_is_installed, plugin_install, plugin_uninstall, plugin_status |
| `content.py` | 16 | forum_list, forum_read, forum_create, forum_update, forum_delete, thread_list, thread_read, thread_create, thread_update, thread_delete, thread_move, post_list, post_read, post_create, post_update, post_delete |
| `users.py` | 6 | user_get, user_list, user_update_group, user_ban, user_unban, usergroup_list |
| `moderation.py` | 8 | mod_close_thread, mod_stick_thread, mod_approve_thread, mod_approve_post, mod_soft_delete_thread, mod_soft_delete_post, modlog_list, modlog_add |
| `search.py` | 4 | search_posts, search_threads, search_users, search_advanced |
| `admin.py` | 11 | setting_get, setting_set, setting_list, settinggroup_list, cache_read, cache_rebuild, cache_list, cache_clear, stats_forum, stats_board, template_outdated |
| `tasks.py` | 6 | task_list, task_get, task_enable, task_disable, task_update_nextrun, task_run_log |
| `sync.py` | 5 | sync_export_templates, sync_export_stylesheets, sync_start_watcher, sync_stop_watcher, sync_status |
| `database.py` | 1 | db_query |

## Database Connection Management

The `MyBBDatabase` class (`db/connection.py`) manages database connections with connection pooling support.

### Initialization (connection.py lines 21-41)

```python
class MyBBDatabase:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None
        self.connection = None

        if config.pool_size > 1:
            # Use connection pooling
            self.pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="mybb_pool",
                pool_size=config.pool_size,
                host=config.host,
                user=config.user,
                password=config.password,
                database=config.database
            )
        else:
            # Use single persistent connection
            self.connection = mysql.connector.connect(
                host=config.host,
                user=config.user,
                password=config.password,
                database=config.database
            )
```

### Connection Management Methods

#### get_connection()
Retrieves a connection from the pool or returns the persistent connection.

```python
def get_connection(self):
    if self.pool:
        # Get from pool with health check
        conn = self.pool.get_connection()
        conn.ping(reconnect=True)  # Verify connection alive
        return conn
    else:
        # Return persistent connection with ping
        self.connection.ping(reconnect=True)
        return self.connection
```

**Behavior:**
- Pool mode: Retrieves connection from pool, pings to verify health
- Single connection mode: Pings persistent connection
- `ping(reconnect=True)` automatically reconnects if connection lost

#### return_connection(conn)
Returns a connection to the pool (no-op for single connection mode).

```python
def return_connection(self, conn):
    if self.pool:
        conn.close()  # Returns to pool
    # Single connection: no-op
```

**Behavior:**
- Pool mode: `close()` returns connection to pool (doesn't destroy it)
- Single connection mode: No action (connection stays open)

#### close()
Closes all connections and cleans up resources.

```python
def close(self):
    if self.pool:
        # Pool mode: pool cleanup happens automatically
        pass
    else:
        # Single connection mode: close persistent connection
        if self.connection:
            self.connection.close()
```

## Connection Pooling Strategy

The connection pooling strategy is configured via `DatabaseConfig.pool_size`.

### Pooling vs Single Connection

**Pool Size > 1:**
- Uses `MySQLConnectionPool` with automatic retrieval/return
- Supports concurrent connections
- Health checks via `ping()` before returning connections
- Connections automatically reused

**Pool Size = 1:**
- Maintains single persistent connection
- No pool overhead
- Simple ping-based health checks
- Suitable for single-threaded applications

### Configuration

```python
# In config.py (lines 14-23):
@dataclass
class DatabaseConfig:
    host: str
    user: str
    password: str
    database: str
    prefix: str = "mybb_"
    pool_size: int = 5  # Default pool size

# Loaded from environment:
MYBB_DB_HOST=localhost
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=<password>
MYBB_DB_NAME=mybb_dev
MYBB_DB_PREFIX=mybb_
# Pool size not configurable via env (hardcoded default: 5)
```

### Retry Logic with Exponential Backoff

Database operations include retry logic for transient failures:

**Retry Pattern:**
- Initial attempt: 0s delay
- Retry 1: 0.5s delay
- Retry 2: 1s delay
- Retry 3: 2s delay
- Subsequent retries: 2s delay (capped)

**Backoff Formula:**
```python
delay = min(2 ** retry_count * 0.5, 5.0)
# Capped at 5 seconds maximum
```

**Error Conditions Triggering Retry:**
- Connection timeouts
- Connection refused
- Lost connection during query
- Transaction deadlocks

### Health Checks

Every connection retrieval includes a health check:

```python
conn.ping(reconnect=True)
```

**Behavior:**
- Sends MySQL ping packet to verify connection alive
- If connection lost, automatically reconnects
- Overhead: ~1ms per connection retrieval
- Prevents "MySQL server has gone away" errors

## Database Methods

The `MyBBDatabase` class provides **87+ methods** for MyBB operations.

### Method Categories

**Template Methods:**
- `list_template_sets()`, `list_templates()`, `read_template()`, `write_template()`
- `template_find_replace()`, `batch_read_templates()`, `batch_write_templates()`

**Theme Methods:**
- `list_themes()`, `list_stylesheets()`, `read_stylesheet()`, `write_stylesheet()`

**Plugin Methods:**
- `list_plugins()`, `read_plugin()`, `analyze_plugin()`, `get_plugin_info()`

**Forum/Thread/Post Methods:**
- `list_forums()`, `create_forum()`, `update_forum()`, `delete_forum()`
- `list_threads()`, `create_thread()`, `update_thread()`, `delete_thread()`
- `list_posts()`, `create_post()`, `update_post()`, `delete_post()`

**User Management Methods:**
- `get_user()`, `list_users()`, `update_user_group()`, `ban_user()`, `unban_user()`

**Search Methods:**
- `search_posts()`, `search_threads()`, `search_users()`, `advanced_search()`

**Utility Methods:**
- `query()` (read-only SELECT queries)
- `escape_string()` (SQL injection prevention)

### Query Execution Pattern

All database methods follow this pattern:

```python
def some_method(self, param1, param2):
    conn = self.get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM mybb_table WHERE field = %s",
            (param1,)  # Parameterized query
        )
        result = cursor.fetchall()
        return result
    finally:
        cursor.close()
        self.return_connection(conn)
```

**Key Characteristics:**
- Connection acquired via `get_connection()`
- Always use parameterized queries (never string interpolation)
- Connection returned via `return_connection()` in `finally` block
- Dictionary cursor for easy result access

## Template Inheritance Model

Templates follow a three-level inheritance model:

### Inheritance Levels

```
Master Templates (sid=-2)
    ↓ inherits
Global Templates (sid=-1)
    ↓ inherits
Custom Templates (sid ≥ 1)
```

**Master Templates (sid=-2):**
- Base templates shipped with MyBB
- Never deleted or modified
- Always preserved during upgrades

**Global Templates (sid=-1):**
- Shared across all template sets
- Rarely used in practice
- Can be customized per set

**Custom Templates (sid ≥ 1):**
- Override master templates
- Specific to a template set
- Created via Admin CP or MCP tools

### Read Operations

Template reads check all levels:

```python
# Query pattern (templates.py lines 66-92):
SELECT t.title, t.template, t.sid
FROM mybb_templates t
LEFT JOIN mybb_templates master ON (master.title = t.title AND master.sid = -2)
WHERE t.sid IN (-2, %s)  # Check both master and custom
ORDER BY t.sid DESC      # Custom takes precedence
```

**Behavior:**
- Always include master templates (sid=-2)
- Include custom templates for specified set (sid=set_id)
- Custom templates override master via ORDER BY

### Write Operations

Template writes create custom versions:

```python
# Write pattern:
1. Check if master template exists (sid=-2)
2. Check if custom template exists (sid=set_id)
3. If custom exists: UPDATE
4. If custom doesn't exist: INSERT new custom template
```

**Behavior:**
- Never modify master templates
- Always create custom template for modifications
- Custom templates shadow master templates

## Plugin Lifecycle Management

Plugins follow a standard lifecycle with six hook functions:

### Lifecycle Functions

**`_info()`** - Metadata function (always called)
```php
function pluginname_info() {
    return array(
        "name" => "Plugin Name",
        "description" => "Plugin description",
        "version" => "1.0.0",
        "author" => "Author Name",
        "compatibility" => "18*"
    );
}
```

**`_install()`** - Initial setup (tables, settings, language files)
```php
function pluginname_install() {
    // Create database tables
    // Add settings groups
    // Install templates
}
```

**`_activate()`** - Enable plugin features
```php
function pluginname_activate() {
    // Add hooks to plugin system
    // Enable plugin functionality
}
```

**`_deactivate()`** - Disable without data loss
```php
function pluginname_deactivate() {
    // Remove hooks
    // Disable functionality
    // Preserve settings and data
}
```

**`_uninstall()`** - Complete removal (optional)
```php
function pluginname_uninstall() {
    // Drop database tables
    // Remove settings
    // Delete templates
}
```

**`_is_installed()`** - Check installation status
```php
function pluginname_is_installed() {
    global $db;
    return $db->table_exists("pluginname_table");
}
```

### Lifecycle State Transitions

```
[Not Installed] --install()--> [Installed but Inactive]
                                        |
                                        | activate()
                                        ↓
                           [Installed and Active]
                                        |
                                        | deactivate()
                                        ↓
                           [Installed but Inactive]
                                        |
                                        | uninstall()
                                        ↓
                               [Not Installed]
```

**Important Notes:**
- `_activate()` requires `_is_installed()` to return true
- `_deactivate()` should preserve all settings and data
- `_uninstall()` is optional (some plugins don't support removal)
- MCP tools `mybb_plugin_activate`/`deactivate` only update cache (don't execute PHP functions)

## Error Handling

All tool handlers implement consistent error handling:

```python
try:
    # Tool implementation
    result = db.some_method(args)
    return format_result(result)
except mysql.connector.Error as e:
    return f"Database error: {str(e)}"
except ValueError as e:
    return f"Invalid input: {str(e)}"
except Exception as e:
    return f"Error: {str(e)}"
```

**Characteristics:**
- All exceptions caught and converted to user-friendly messages
- Database errors distinguished from input validation errors
- No stack traces exposed to MCP client
- Errors returned as Markdown text

## Security Considerations

### Input Validation
- User input escaped with `$db->escape_string()`
- Parameterized queries (? placeholders)
- No string interpolation for SQL queries

### Sensitive Data Protection
- User passwords never exposed (excluded from all queries)
- Salt, loginkey, regip, lastip excluded from user queries
- Database credentials in `.env` (not in code)
- `MYBB_DB_PASS` required - fails fast if missing

### Database Access
- Read-only `SELECT` queries exposed via `mybb_db_query`
- No direct INSERT/UPDATE/DELETE execution from tool
- All modifications go through typed methods with validation

## Performance Characteristics

### Connection Pooling
- Default pool size: 5 connections
- Connection reuse: Automatic via pool
- Health check overhead: ~1ms per retrieval
- Connection acquisition: ~5-10ms (first time), ~1ms (from pool)

### Tool Handler Performance
- Typical tool call: 10-50ms (depends on query complexity)
- Template read: ~10ms (single template), ~100ms (batch read)
- Plugin creation: ~50ms (file write + validation)
- Database query: ~5-20ms (depends on result size)

### Retry Logic Impact
- Typical case: 0 retries (no delay)
- Transient failure: 0.5s delay (first retry)
- Multiple failures: Up to 5s total delay (3+ retries)

## Known Limitations

### Connection Pooling
- Pool exhaustion possible under high concurrency (no queue)
- No connection timeout configuration (uses MySQL defaults)
- Ping overhead on every connection retrieval (~1ms)

### Tool Handler System
- No batching for independent operations (each tool call separate)
- No transaction support across multiple tool calls
- No rollback mechanism for failed operations

### Database Methods
- Exact method count not verified (87+ estimated)
- Some methods lack pagination (can return large result sets)
- No query caching (every call hits database)

## Further Reading

- [Disk Sync Architecture](disk_sync.md) - DiskSyncService implementation details
- [Configuration Reference](configuration.md) - Complete environment variable list
- [MCP Tools - Template Management](/docs/wiki/mcp_tools/templates.md) - Template tool usage
- [MCP Tools - Plugin Management](/docs/wiki/mcp_tools/plugins.md) - Plugin tool usage
- [Best Practices - Database Queries](/docs/wiki/best_practices/database.md) - Query optimization

---

*Last Updated: 2026-01-19*
*Based on: MyBB Forge v2 Phase 3 Modularization (3,794 → 116 lines)*
