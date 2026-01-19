# Architecture

This section documents the internal architecture of the MyBB Playground system, including the MCP server implementation, disk sync service, and configuration management.

## System Overview

MyBB Playground consists of three primary components:

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code (MCP Client)                  │
└───────────────────────────┬─────────────────────────────────┘
                            │ MCP Protocol
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              MyBB MCP Server (mybb_mcp/)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Tool Registry│  │  Dispatcher  │  │ Disk Sync    │      │
│  │  (85 tools)  │  │ (14 modules) │  │   Service    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         └──────────────────┼──────────────────┘              │
│                            ↓                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ handlers/: templates, themes, plugins, content, users,  ││
│  │            search, moderation, admin, tasks, sync, db   ││
│  └─────────────────────────────────────────────────────────┘│
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│   MyBB Database         │   │   Filesystem (mybb_sync)│
│   (MariaDB)             │   │   - template_sets/      │
│   - templates           │   │   - styles/             │
│   - themes              │   │   - (bidirectional sync)│
│   - plugins             │   │                         │
│   - forums/posts        │   │                         │
└─────────────────────────┘   └─────────────────────────┘
```

## Component Relationships

### MCP Server → Database
- Connection pooling with health checks
- Exponential backoff retry logic (0.5s → 1s → 2s, capped at 5s)
- 87+ database methods for MyBB operations
- Parameterized queries for security

### MCP Server → Filesystem
- **DiskSyncService** orchestrates bidirectional sync
- **FileWatcher** monitors mybb_sync/ for changes (0.5s debounce)
- **TemplateExporter/Importer** handles template sync
- **StylesheetExporter/Importer** handles stylesheet sync
- Atomic writes via temp file + rename pattern

### Database ↔ Filesystem Sync
- Export: Database → Disk (on-demand via MCP tools)
- Import: Disk → Database (automatic via FileWatcher)
- Race prevention: Watcher paused during exports
- UTF-8 encoding for all files

## Architecture Documents

### [MCP Server Architecture](mcp_server.md)
Covers server initialization, modular handler architecture, database connection management, and connection pooling strategy.

**Topics:**
- Server initialization sequence (116-line orchestration layer)
- **Modular handler architecture** (14 handler modules, 85 tools)
- Dictionary-based dispatcher routing
- Database connection pooling
- Tool categories: templates, themes, plugins, content, users, etc.

### [Disk Sync Architecture](disk_sync.md)
Documents the DiskSyncService orchestrator and bidirectional synchronization between database and filesystem.

**Topics:**
- DiskSyncService lifecycle management
- FileWatcher implementation (watchdog-based)
- Template export/import with inheritance
- Stylesheet export/import with copy-on-write
- Race condition prevention

### [Configuration](configuration.md)
Complete reference for environment variables and configuration loading.

**Topics:**
- Database configuration (MYBB_DB_*)
- MyBB root and URL configuration
- Disk sync configuration (MYBB_SYNC_ROOT, MYBB_AUTO_UPLOAD)
- Plugin Manager workspace configuration
- Configuration loading patterns

## Key Architectural Patterns

### Template Inheritance Model
- **Master templates (sid=-2)**: Base templates, never deleted
- **Global templates (sid=-1)**: Shared across template sets
- **Custom templates (sid ≥ 1)**: Override master templates
- Read operations check all levels
- Write operations create custom versions

### Stylesheet Inheritance Model
- **Copy-on-write pattern**: Child themes override parent stylesheets
- **Inheritance chain walking**: Fetch parent stylesheets recursively
- **Child precedence**: Child theme overrides always win
- Export walks entire inheritance chain
- Import creates override in child theme

### Atomic File Operations
- **Write pattern**: Write to `.tmp` file, then atomic rename
- **POSIX atomic rename**: Same filesystem guarantees atomicity
- **Corruption prevention**: Temp files filtered by watcher
- **Empty file detection**: File size validation before import

### Race Condition Prevention
- **Pause during export**: Watcher paused before export operations
- **Queue draining**: Empty event queue after export completes
- **Resume guarantee**: `finally` block ensures watcher resumes
- **Thread-safe debouncing**: Per-file timestamp tracking with lock

## Design Decisions

### Why Connection Pooling?
- **Pool size > 1**: Use MySQLConnectionPool with automatic retrieval/return
- **Pool size = 1**: Maintain single persistent connection
- **Health checks**: Ping verification before returning connections
- **Retry logic**: Handles transient connection failures gracefully

### Why Watchdog for File Watching?
- **Cross-platform**: Works on Linux, macOS, Windows
- **Event-driven**: Efficient monitoring without polling
- **Debouncing**: Built-in support via custom event handler
- **Atomic write detection**: Handles both direct writes and temp→rename

### Why Bidirectional Sync?
- **Developer experience**: Edit templates in IDE or Admin CP
- **Version control**: Templates in filesystem can be committed to git
- **Backup**: Automatic disk backups of all templates/stylesheets
- **Migration**: Easy export/import between MyBB installations

## Security Considerations

### Input Validation
- User input escaped with `$db->escape_string()`
- Parameterized queries (? placeholders)
- CSRF token verification templates for forms

### Sensitive Data Protection
- User passwords never exposed (excluded from queries)
- Database credentials in `.env` (not in code)
- `MYBB_DB_PASS` required - server fails fast if missing

### Database Access
- Read-only `SELECT` queries exposed via `mybb_db_query`
- No direct INSERT/UPDATE/DELETE execution
- All modifications go through typed methods

## Performance Characteristics

### Connection Pooling
- Configurable pool size (default: 5 connections)
- Automatic connection reuse
- Health check overhead: ~1ms per connection retrieval

### File Watcher
- Debounce window: 0.5 seconds (hardcoded)
- Event processing: Async queue (non-blocking)
- Temp file filtering: Prevents duplicate events

### Export Operations
- Templates: ~100ms per template set (varies by size)
- Stylesheets: ~50ms per theme (varies by inheritance depth)
- Atomic writes: Minimal overhead (~1-2ms per file)

## Known Limitations

### Disk Sync
- UTF-8 encoding assumed (no charset detection)
- Debounce window hardcoded (not configurable)
- Concurrent exports not officially supported
- No transaction wrapping for multi-statement imports

### Connection Pooling
- Pool exhaustion possible under high concurrency
- No connection timeout configuration
- Ping overhead on every connection retrieval

### Template/Stylesheet Operations
- No partial template updates (full template always replaced)
- No diff/merge support for concurrent edits
- No conflict resolution for bidirectional changes

## Further Reading

- [MCP Server Implementation](mcp_server.md) - Server initialization and tool registration details
- [Disk Sync Service](disk_sync.md) - Complete bidirectional sync workflow
- [Configuration Reference](configuration.md) - All environment variables and loading patterns
- [MCP Tools Overview](/docs/wiki/mcp_tools/index.md) - Complete tool reference
- [Best Practices](/docs/wiki/best_practices/index.md) - Development guidelines

---

*Last Updated: 2026-01-19*
*Based on: MyBB Forge v2 Phase 3 Modularization, RESEARCH_MCP_SERVER_ARCHITECTURE_20250118_0811.md*
