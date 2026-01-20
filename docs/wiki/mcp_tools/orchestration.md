# Server Orchestration Tools

MCP tools for managing the MyBB PHP development server lifecycle and querying logs.

## Overview

These tools allow Claude to:
- Start/stop/restart the development server
- Check server and MariaDB status
- Query server logs with filtering (errors, keywords, time range)

**Total:** 5 tools

## Tools

### mybb_server_start

Start the MyBB PHP development server.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| port | integer | optional | 8022 | Port to run server on |
| force | boolean | optional | false | Stop existing server first |

**Returns:**
- Success/failure status
- Port and PID if started
- Error message if failed

**Examples:**
```python
# Start on default port (8022)
mybb_server_start()

# Start on custom port
mybb_server_start(port=8080)

# Restart if already running
mybb_server_start(force=true)
```

**Notes:**
- Requires MariaDB to be running
- Creates state file at `.mybb-server.json` in repo root
- Logs to `logs/server.log`
- Auto-detects if server is already running

---

### mybb_server_stop

Stop the development server gracefully.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| force | boolean | optional | false | Force kill if graceful shutdown fails |

**Returns:**
- Success/failure status
- Message indicating shutdown result

**Examples:**
```python
# Graceful shutdown
mybb_server_stop()

# Force kill if needed
mybb_server_stop(force=true)
```

**Notes:**
- Sends SIGTERM for graceful shutdown
- With `force=true`, sends SIGKILL after 5 second timeout
- Cleans up state file on successful stop

---

### mybb_server_status

Get current server status including port, PID, uptime, and MariaDB status.

**Parameters:** None

**Returns:**

Markdown-formatted status report with:
- Running status (🟢 Running / 🔴 Stopped)
- Port and PID (if running)
- Uptime (if running)
- Started at timestamp
- Log file location
- MariaDB status (🟢 Running / 🔴 Stopped)

**Example:**
```python
mybb_server_status()
```

**Example Output:**
```
## MyBB Development Server Status

🟢 **Running**

- **Port:** 8022
- **PID:** 12345
- **Started:** 2026-01-20 01:00:00 UTC
- **Uptime:** 10 minutes, 30 seconds
- **Log File:** /home/austin/projects/MyBB_Playground/logs/server.log

### Dependencies
- MariaDB: 🟢 Running
```

**Notes:**
- Detects servers started via `./start_mybb.sh` (not just MCP-started servers)
- Uses state file when available, falls back to port checking
- Checks MariaDB via `pgrep mariadbd`

---

### mybb_server_logs

Query PHP server logs with filtering. **Essential for debugging.**

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| errors_only | boolean | optional | false | Only show PHP errors and 4xx/5xx responses |
| exclude_static | boolean | optional | false | Filter out .css, .js, images |
| since_minutes | integer | optional | null | Only entries from last N minutes |
| filter_keyword | string | optional | null | Case-insensitive keyword search |
| limit | integer | optional | 50 | Maximum entries to return |
| tail | boolean | optional | true | Read from end (most recent first) |
| offset | integer | optional | 0 | Pagination offset (use with limit) |

**Returns:**

Markdown-formatted log entries with:
- Timestamp
- Entry type (request/error/connection)
- Status code (for requests)
- Method and path (for requests)
- Error message (for errors)

**Examples:**
```python
# Show recent errors only
mybb_server_logs(errors_only=true)

# Search for keyword in logs
mybb_server_logs(filter_keyword="invite", limit=20)

# Last 5 minutes, no static assets
mybb_server_logs(since_minutes=5, exclude_static=true)

# All logs from the beginning
mybb_server_logs(tail=false, limit=100)

# Combine filters
mybb_server_logs(errors_only=true, since_minutes=10, exclude_static=true)

# Pagination (page 2)
mybb_server_logs(limit=50, offset=50)

# Paginate through errors
mybb_server_logs(errors_only=true, limit=20, offset=20)
```

**Example Output:**
```markdown
## Server Logs (Last 50 entries)

**Filters:** errors_only=true, exclude_static=false

---

### [2026-01-20 01:32:55] ERROR
**Status:** 500
**Request:** GET /broken.php
**Type:** request

---

### [2026-01-20 01:30:12] ERROR
**Message:** PHP Fatal error: Call to undefined function
**Type:** error

---
```

**Notes:**
- Log file location: `logs/server.log` (created by `./start_mybb.sh`)
- **Token guard:** Max 8000 chars of log output to prevent context bloat
- Max file size read: 10MB (seeks to end for large files)
- File size shown in output
- Warning if log was truncated
- Pagination: Use `offset` and `limit` to page through large result sets
- Static assets: `.png`, `.jpg`, `.css`, `.js`, `.woff`, `.woff2`, `.ttf`, `.svg`, `.ico`
- **Error categories:** `fatal`, `parse`, `warning`, `notice`, `deprecated`, `strict`, `recoverable`, `exception`, `http_5xx`, `http_4xx`, `stack_trace`
- Error breakdown shown in output summary when errors present

---

### mybb_server_restart

Restart the server (stop then start).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| port | integer | optional | null | Port after restart (default: same as before) |

**Returns:**
- Success/failure status
- New port and PID if successful
- Error message if failed

**Examples:**
```python
# Restart on same port
mybb_server_restart()

# Restart on different port
mybb_server_restart(port=8080)
```

**Notes:**
- Stops server gracefully (5 second wait for shutdown)
- Preserves port from state file if not specified
- Sleeps 2 seconds between stop and start
- Requires MariaDB to be running

---

## Log File Location

Logs are written to `logs/server.log` in the repo root. The file is:
- Created/rotated when `./start_mybb.sh` runs
- Captured via `tee` (visible in terminal AND written to file)
- Gitignored (not committed)

## Log Entry Format

PHP development server logs in this format:
```
[Mon Jan 20 01:32:55 2026] 127.0.0.1:47778 [200]: GET /usercp.php
[Mon Jan 20 01:32:55 2026] PHP Fatal error: Something broke in /path/file.php:123
[Mon Jan 20 01:32:55 2026] 127.0.0.1:47778 Accepted
```

The log parser handles:
- HTTP requests with status codes
- PHP errors (Fatal, Warning, Notice, Parse)
- Connection events (Accepted, Closing)
- Stack traces (multi-line)

## Detecting External Servers

The tools detect servers started via `./start_mybb.sh` (not just via MCP):
- Checks if port 8022 is in use
- Reports as "running" even without MCP state file
- Can stop externally-started servers

## State File

Server state is persisted to `.mybb-server.json` at repo root:

```json
{
  "version": 1,
  "port": 8022,
  "pid": 12345,
  "started_at": "2026-01-20T01:00:00Z",
  "log_file": "/home/austin/projects/MyBB_Playground/logs/server.log"
}
```

**Note:** This file is gitignored and managed automatically by the orchestration service.

## Common Workflows

### Starting Development
```python
# Check if server is running
mybb_server_status()

# Start if needed
mybb_server_start()

# Check for errors
mybb_server_logs(errors_only=true, limit=10)
```

### Debugging Plugin Issues
```python
# Search for plugin name in logs
mybb_server_logs(filter_keyword="myplugin", since_minutes=5)

# Show recent errors
mybb_server_logs(errors_only=true, exclude_static=true, limit=20)
```

### Clean Restart
```python
# Stop server
mybb_server_stop()

# Clear old logs (optional - manual)
# rm logs/server.log

# Start fresh
mybb_server_start()
```

---

See also: [Getting Started](../getting_started/index.md) | [Plugin Development](../best_practices/plugin_development.md)
