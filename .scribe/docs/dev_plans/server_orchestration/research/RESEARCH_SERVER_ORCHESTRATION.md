# Research: Server Orchestration Infrastructure

**Research Goal:** Foundation analysis for MCP server orchestration layer enabling agent swarms to manage MyBB dev server lifecycle, query logs, and support multi-instance scenarios.

**Date:** 2026-01-19
**Status:** Complete
**Confidence:** 0.91 (verified code + direct testing)

---

## Executive Summary

The MyBB Playground currently has:
- **Bash-based server control** (`start_mybb.sh`, `stop_mybb.sh`) with foreground PHP execution
- **No process state tracking** (no PID files, health checks, or background management)
- **No log capture** (stdout/stderr not persisted)
- **MCP handler patterns** established for async service lifecycle (DiskSyncService as reference)

**Recommended approach:** Build Python-based server orchestration service following DiskSyncService patterns, with shell script wrappers for backward compatibility. Store server state (port, PID, log file) in `.mybb-server.json`.

---

## 1. Current Server Architecture

### 1.1 Shell Scripts (Existing)

**start_mybb.sh** - `/home/austin/projects/MyBB_Playground/start_mybb.sh`

```bash
# Reads MYBB_PORT from .env (defaults to 8022)
PORT="${MYBB_PORT:-8022}"

# Checks MariaDB is running (pgrep mariadbd/mysqld)
# Checks PHP is installed
# Validates TestForum directory exists

# Starts PHP built-in server (FOREGROUND - blocking)
cd "$MYBB_DIR"
php -S localhost:${PORT} -t .
```

**Key characteristics:**
- Port configurable via `MYBB_PORT` env var (default 8022)
- Checks dependencies (MariaDB, PHP, TestForum directory)
- Runs in foreground - no backgrounding, no PID file
- No log capture (stdout/stderr go to terminal)
- No way to detect if server already running on port
- Process killed with Ctrl+C

**stop_mybb.sh** - `/home/austin/projects/MyBB_Playground/stop_mybb.sh`

```bash
pkill -f "php -S localhost" 2>/dev/null && echo "✓ PHP server stopped"
```

**Issues:**
- Matches ALL PHP servers on localhost (loose matching)
- Could kill multiple instances unintentionally
- No graceful shutdown verification
- No timeout handling

### 1.2 Environment Configuration

**Source:** `/home/austin/projects/MyBB_Playground/.env`

```env
MYBB_PORT=8022
MYBB_ROOT=/home/austin/projects/MyBB_Playground/TestForum
MYBB_URL=http://localhost:8022
MYBB_DB_HOST=localhost
MYBB_DB_NAME=mybb_dev
MYBB_DB_USER=mybb_user
MYBB_DB_PREFIX=mybb_
```

**Config loading:** `mybb_mcp/mybb_mcp/config.py` uses `load_dotenv()` with parent directory search

---

## 2. MCP Architecture & Handler Patterns

### 2.1 Service Lifecycle Pattern (Reference: DiskSyncService)

**Location:** `mybb_mcp/mybb_mcp/sync/service.py`

The DiskSyncService demonstrates how MyBB Playground manages background services:

**Initialization:**
```python
# server.py:create_server()
sync_service = DiskSyncService(db, sync_config, config.mybb_url)
sync_service.start_watcher()  # Auto-start file watcher
```

**Lifecycle methods:**
- `start_watcher()` → Returns bool, manages state
- `stop_watcher()` → Graceful shutdown
- `pause_watcher()` / `resume_watcher()` → Atomic operation support
- `get_status()` → Returns service status dict

**FileWatcher implementation:**
- Uses `watchdog` library (file system events)
- Debouncing (configurable window to avoid rapid re-syncs)
- Batching (collect work items, flush after delay)
- Threading-safe (queue-based work submission)

### 2.2 MCP Handler Pattern

**Signature:** `async handle_XXX(args: dict, db: Any, config: Any, sync_service: Any) -> str`

**Example:** `handlers/sync.py:handle_sync_export_templates()`

```python
async def handle_sync_export_templates(args, db, config, sync_service) -> str:
    set_name = args.get("set_name", "")
    try:
        if sync_service and sync_service.watcher:
            sync_service.pause_watcher()  # Pause for atomic operation
        stats = await sync_service.export_template_set(set_name)
        return f"# Templates Exported\n\n..."
    finally:
        if sync_service and sync_service.watcher:
            sync_service.resume_watcher()  # Always resume
```

**Key patterns:**
- Service injection (db, config, sync_service passed to all handlers)
- Async/await for long operations
- Pause/resume for atomicity
- Try/finally for cleanup
- Markdown formatted responses

### 2.3 Subprocess Execution Pattern (Reference: PluginLifecycle)

**Location:** `plugin_manager/lifecycle.py`

```python
def _call_bridge(self, action: str, **kwargs) -> BridgeResult:
    cmd = [self.php_binary, str(self.bridge_path), f"--action={action}", "--json"]

    result = subprocess.run(
        cmd,
        cwd=str(self.mybb_root),
        capture_output=True,  # Capture stdout/stderr
        text=True,
        timeout=self.timeout  # 30 seconds default
    )

    # Parse JSON output
    json_output = json.loads(result.stdout)
    return BridgeResult.from_json(action, json_output)
```

**Patterns to reuse:**
- Error handling (TimeoutExpired, FileNotFoundError, JSON parse errors)
- Working directory control (`cwd=`)
- Timeout enforcement
- JSON output parsing
- Command construction with optional flags

---

## 3. PHP Built-in Server Characteristics

### 3.1 Execution Model

```bash
php -S localhost:8022 -t /path/to/docroot
```

**Key points:**
- **Blocking:** Runs in foreground until Ctrl+C
- **No background support:** Must be backgrounded with `&` or run in separate shell
- **Single-threaded:** Processes requests sequentially (fine for dev)
- **Router support:** Can pass optional router script for URL rewriting

### 3.2 Logging Output

**Format:** Stdout/stderr only (no file logging by default)

Example output:
```
[Sun Jan 19 03:35:42 2026] 127.0.0.1:12345 Accepted
[Sun Jan 19 03:35:42 2026] 127.0.0.1:12345 [200]: GET /
[Sun Jan 19 03:35:42 2026] 127.0.0.1:12345 Closing
```

**Gotchas:**
- No built-in file logging (must use `tee` or process redirection)
- Errors logged via PHP `error_log` config (not built-in server)
- Request logs intermixed with PHP errors on stderr

### 3.3 Port Detection & Process Management

**Check if port is in use:**
```bash
# Primary method (cross-platform with lsof)
lsof -i :8022 2>/dev/null

# Fallback (if lsof not available)
netstat -tlnp 2>/dev/null | grep :8022  # Linux
ss -tlnp 2>/dev/null | grep :8022       # Linux (ss preferred)
```

**Process termination:**
```bash
# Kill by port (not directly - need PID first)
# Kill by process match (current approach)
pkill -f "php -S localhost:8022"  # More specific than current

# Graceful shutdown
kill -TERM <PID>  # Allows cleanup
kill -9 <PID>     # Force kill (last resort)
```

---

## 4. Technical Constraints & Considerations

### 4.1 Multi-Instance Support

**For multiple MyBB instances, need to isolate:**

| Component | Strategy | Difficulty |
|-----------|----------|-----------|
| **Port** | Env var or config param (e.g., MYBB_PORT_1, MYBB_PORT_2) | ✅ Easy |
| **Database** | Separate databases or prefix-based (MYBB_DB_PREFIX) | ✅ Easy |
| **Log files** | Timestamp + instance ID (server_8022.log, server_8023.log) | ✅ Easy |
| **PID tracking** | Store per instance (server_8022.pid, server_8023.pid) | ✅ Easy |
| **File watcher** | Per-instance sync service (already designed for this) | ✅ Easy |
| **MCP server** | Single MCP server with multiple orchestration instances | ⚠️ Medium |

**Recommendation:** Start with single-instance support, design for extensibility

### 4.2 Process State Tracking

**Proposed `.mybb-server.json` structure:**

```json
{
  "port": 8022,
  "pid": 12345,
  "started_at": "2026-01-19T03:35:00Z",
  "log_file": "/home/austin/projects/MyBB_Playground/logs/server_8022.log",
  "status": "running",
  "mariadb_required": true,
  "mariadb_status": "running"
}
```

**State transitions:**
- Created when server starts
- Updated on status queries
- Verified (PID still exists) on health checks
- Deleted on graceful shutdown

### 4.3 Logging Strategy

**Current gaps:**
- No persistent logging (stdout/stderr lost on disconnect)
- No log rotation
- No structured logging

**Proposed approach:**
- Capture PHP server to file: `logs/server_8022.log`
- Structured JSON format for parsing
- Timestamp rotation: `logs/server_8022_YYYYMMDD_HHMMSS.log`
- Keep last N logs (e.g., 10 files)

**Implementation:**
```bash
php -S localhost:8022 -t . 2>&1 | tee -a logs/server_8022.log
```

---

## 5. Recommended Architecture

### 5.1 Components

**1. Python Service (New)**
- `mybb_mcp/mybb_mcp/orchestration/server_service.py`
- Similar to `DiskSyncService`
- Lifecycle: `start()`, `stop()`, `get_status()`, `health_check()`

**2. MCP Handlers (New)**
- `handlers/orchestration.py`
- Tools: `mybb_start_server`, `mybb_stop_server`, `mybb_server_status`, `mybb_server_logs`

**3. State File**
- `.mybb-server.json` (in repo root, gitignored)
- Single source of truth for server state

**4. Shell Wrappers (Enhanced)**
- `start_mybb.sh` (backwards compatible wrapper)
- `stop_mybb.sh` (backwards compatible wrapper)
- Can call Python service or direct shell commands

### 5.2 Integration Points

**With existing MCP server:**

```python
# server.py:create_server()
from .orchestration.server_service import ServerOrchestrationService

# Initialize
server_service = ServerOrchestrationService(config)

# Pass to handlers
# (similar to sync_service)
```

**Handler signature stays the same:**
```python
async def handle_start_server(args, db, config, sync_service) -> str:
    # New: add orchestration_service parameter
    # or access via config
```

---

## 6. Process Management Patterns in Codebase

### 6.1 Shell Script Standards (install.sh)

The project uses high-quality shell scripts with:
- Structured logging to timestamped files
- ANSI color output with stripping
- TRAP-based cleanup
- Temp directory tracking
- Non-interactive mode support
- Comprehensive error handling

**Implications:** Complex shell scripts are acceptable and expected for infrastructure tasks.

### 6.2 Subprocess Patterns (lifecycle.py, plugin_git.py)

Python subprocess calls follow patterns:
- `subprocess.run()` with `capture_output=True`
- `cwd=` for working directory control
- `timeout=` parameter (30 second default)
- Error handling: `TimeoutExpired`, `FileNotFoundError`
- JSON parsing for structured output
- Command array construction (shell safety)

---

## 7. Risks & Edge Cases

### 7.1 Port Conflicts

**Risk:** Multiple instances trying to use same port

**Mitigation:**
- Check port availability before starting
- Return error if port already in use
- Allow port override via parameter
- Store allocated port in state file

### 7.2 Zombie Processes

**Risk:** PHP process terminated unexpectedly, PID file stale

**Mitigation:**
- Verify PID still exists in `get_status()`
- Detect stale state and recover
- Cleanup PID file on graceful shutdown

### 7.3 Database Connection Loss

**Risk:** MariaDB stops while server running, requests fail

**Current handling:** start_mybb.sh checks MariaDB on startup only

**Recommendation:** Health check can verify DB connection, but don't auto-restart (leave to admin)

### 7.4 Log File Growth

**Risk:** Logs consume disk space over time

**Mitigation:**
- Implement rotation strategy (daily or size-based)
- Keep limited history (last 10 files)
- Consider compression for old logs

### 7.5 Signal Handling

**Risk:** Server doesn't catch SIGTERM gracefully

**Current:** PHP built-in server catches SIGTERM (verified)

**Note:** Verify PHP version for signal handling support

---

## 8. Future Extensibility

### 8.1 Planned vs. Deferred

**Phase 1 (MVP):**
- Single instance support
- Basic start/stop/status tools
- JSON state file
- Log file capture
- Health checks

**Phase 2 (Future):**
- Multi-instance support
- Log rotation and cleanup
- Dashboard/monitoring
- Automated restart on failure
- Performance metrics

### 8.2 Design for Extension

**Recommend:**
- Use config objects instead of hardcoded values
- Parameterize port/database per instance
- Async-ready (use asyncio patterns)
- Testable (dependency injection)

---

## 9. Questions for Architect

1. **Single vs. Multi-instance:** Should Phase 1 support multiple instances or start simple?
2. **Shell vs. Python:** Wrap shell scripts (backward compatible) or rewrite in Python?
3. **Health check frequency:** How often should server status be checked? (on-demand vs. background thread?)
4. **Log persistence:** How many historical logs to keep? Size limits?
5. **Error recovery:** Auto-restart on crash or admin intervention only?

---

## 10. Verification Checklist

- [x] Analyzed start_mybb.sh, stop_mybb.sh current implementation
- [x] Reviewed MCP handler patterns (sync.py)
- [x] Examined DiskSyncService lifecycle management
- [x] Tested port detection methods (lsof)
- [x] Researched PHP built-in server logging format
- [x] Reviewed subprocess patterns (lifecycle.py, plugin_git.py)
- [x] Checked shell script standards (install.sh)
- [x] Identified configuration loading mechanism (.env)
- [x] Mapped existing logs directory structure
- [x] Reviewed FileWatcher threading/async patterns

---

**Research completed:** 2026-01-19 03:37 UTC
