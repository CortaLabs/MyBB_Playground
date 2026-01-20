# Architecture Guide: Server Orchestration Layer

**Author:** MyBB-ArchitectAgent
**Version:** 1.0
**Status:** Approved
**Last Updated:** 2026-01-20
**Research Source:** RESEARCH_SERVER_ORCHESTRATION.md

---

## 1. Problem Statement
<!-- ID: problem_statement -->

### Context

The MyBB Playground currently relies on shell scripts (`start_mybb.sh`, `stop_mybb.sh`) for server lifecycle management. These scripts:
- Run PHP server in **foreground only** (blocking terminal)
- Have **no log capture** (stdout/stderr lost on disconnect)
- Have **no process state tracking** (no PID files, no health checks)
- Use loose process matching (`pkill -f "php -S localhost"`) risking killing unrelated processes

Agent swarms need programmatic server control to:
- Start/restart servers automatically when needed
- Query server logs for debugging without manual copy-paste
- Check server health before running tests
- Support future multi-instance development scenarios

### Goals

1. **MCP tool for log queries** - Filter errors, exclude HTTP noise, temporal queries
2. **MCP tools for server lifecycle** - Start/stop/restart with auto-detection
3. **Log capture** - Persist server output to gitignored log files
4. **Log rotation** - Prevent unbounded log growth
5. **Extensible design** - Support multi-instance in future phases

### Non-Goals

- **Phase 1 does NOT include:** Multi-instance support, auto-restart on crash, performance metrics
- **NOT replacing shell scripts:** They remain for backward compatibility (human use)
- **NOT managing MariaDB:** Database lifecycle is separate concern

### Success Metrics

- Agents can start server via MCP tool without human intervention
- Agents can query last 50 error lines without terminal access
- Log files persist across sessions, rotate on startup
- Zero breaking changes to existing shell script usage

---

## 2. Requirements & Constraints
<!-- ID: requirements_constraints -->

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1 | Start PHP server with log capture | P0 |
| FR2 | Stop server gracefully by PID | P0 |
| FR3 | Query server status (running, port, PID, uptime) | P0 |
| FR4 | Query logs with filtering (errors, keywords, time range) | P0 |
| FR5 | Detect if port already in use before starting | P0 |
| FR6 | Rotate logs on server start (keep previous session) | P1 |
| FR7 | Restart server (stop + start) | P1 |
| FR8 | Auto-start MariaDB if not running | P2 |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR1 | Handler response time | <500ms for status/logs |
| NFR2 | Log file growth | Rotate at startup, cap history |
| NFR3 | Backward compatibility | Shell scripts still work |
| NFR4 | Error messages | Actionable markdown output |

### Assumptions

- PHP 8.0+ installed and available in PATH
- MariaDB/MySQL installed (managed separately)
- TestForum directory exists at configured path
- Port 8022 available (or configurable via MYBB_PORT)
- Linux/WSL environment (not Windows native)

### Constraints

1. **Handler signature fixed:** Must match `async handler(args, db, config, sync_service) -> str`
2. **No new service injection:** Cannot modify dispatcher signature in Phase 1 - access orchestration service via module-level singleton or config
3. **Async handlers:** All handlers must be async (can wrap sync code)
4. **Markdown responses:** All tool outputs must be markdown-formatted

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Zombie processes (stale PID) | Medium | Verify PID exists on status check, recover gracefully |
| Port conflicts | Medium | Check port before start, clear error message |
| Log file corruption | Low | Atomic writes, rotation before write |
| MariaDB not running | Medium | Check and start if needed (optional, warn if fails) |

---

## 3. Architecture Overview
<!-- ID: architecture_overview -->

### Solution Summary

Create a **ServerOrchestrationService** class following the established DiskSyncService pattern. The service manages PHP server lifecycle through subprocess execution, tracks state in a JSON file, and captures logs to the gitignored `logs/` directory.

### Component Diagram

```
+------------------+     +----------------------+     +------------------+
|   MCP Handlers   |---->| ServerOrchestration  |---->|  PHP Built-in    |
| (orchestration.py)|     |      Service         |     |     Server       |
+------------------+     +----------------------+     +------------------+
        |                         |                          |
        |                         v                          v
        |                 +---------------+          +---------------+
        |                 | .mybb-server  |          | logs/server.log|
        |                 |    .json      |          | (captured via  |
        |                 | (state file)  |          |  tee/redirect) |
        |                 +---------------+          +---------------+
        v
+------------------+
| tools_registry.py|
| (tool definitions)|
+------------------+
```

### Component Breakdown

#### 1. ServerOrchestrationService (`orchestration/server_service.py`)

**Responsibility:** Manage PHP server lifecycle, state tracking, log capture

**Interfaces:**
- `start(port: int = None) -> ServerResult`
- `stop() -> ServerResult`
- `restart() -> ServerResult`
- `get_status() -> ServerStatus`
- `query_logs(options: LogQueryOptions) -> LogQueryResult`

**Notes:**
- Follows DiskSyncService lifecycle pattern
- Uses subprocess for shell execution
- State persisted to `.mybb-server.json`
- Module-level singleton for handler access

#### 2. MCP Handlers (`handlers/orchestration.py`)

**Responsibility:** Expose service methods as MCP tools

**Interfaces:**
- `handle_server_start(args, db, config, sync_service) -> str`
- `handle_server_stop(args, db, config, sync_service) -> str`
- `handle_server_restart(args, db, config, sync_service) -> str`
- `handle_server_status(args, db, config, sync_service) -> str`
- `handle_server_logs(args, db, config, sync_service) -> str`

**Notes:**
- Access service via module singleton (initialized on first use)
- Return markdown-formatted responses
- Handle all exceptions gracefully

#### 3. Log Parser (`orchestration/log_parser.py`)

**Responsibility:** Parse and filter PHP server log output

**Interfaces:**
- `parse_log_line(line: str) -> LogEntry`
- `filter_entries(entries, options: LogQueryOptions) -> list[LogEntry]`
- `format_entries(entries) -> str`

**Notes:**
- Detect PHP errors, HTTP status codes, stack traces
- Filter static asset requests
- Support time-based filtering

#### 4. State File (`.mybb-server.json`)

**Responsibility:** Persist server state across MCP restarts

**Notes:**
- Gitignored (contains runtime state)
- Validated on read (detect stale state)
- Atomic writes (write to temp, rename)

### Data Flow

**Start Server:**
```
Agent -> mybb_server_start -> handle_server_start -> ServerOrchestrationService.start()
                                                            |
                                                            v
                                                    [Check port available]
                                                            |
                                                            v
                                                    [Start PHP with tee]
                                                            |
                                                            v
                                                    [Write state file]
                                                            |
                                                            v
                                                    [Return success markdown]
```

**Query Logs:**
```
Agent -> mybb_server_logs -> handle_server_logs -> ServerOrchestrationService.query_logs()
                                                            |
                                                            v
                                                    [Read log file]
                                                            |
                                                            v
                                                    [Parse with log_parser]
                                                            |
                                                            v
                                                    [Filter by options]
                                                            |
                                                            v
                                                    [Format as markdown]
```

### External Integrations

- **Existing shell scripts:** Not modified, can coexist
- **DiskSyncService:** No direct integration, parallel service
- **Config system:** Uses existing `config.py` for paths

---

## 4. Detailed Design
<!-- ID: detailed_design -->

### 4.1 ServerOrchestrationService Class

```python
# orchestration/server_service.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import subprocess
import json
import os
import signal
from datetime import datetime

@dataclass
class ServerResult:
    success: bool
    message: str
    port: Optional[int] = None
    pid: Optional[int] = None
    log_file: Optional[str] = None

@dataclass
class ServerStatus:
    running: bool
    port: Optional[int] = None
    pid: Optional[int] = None
    uptime_seconds: Optional[int] = None
    log_file: Optional[str] = None
    mariadb_running: bool = False

@dataclass
class LogQueryOptions:
    errors_only: bool = False
    limit: int = 50
    tail: bool = True
    filter_keyword: Optional[str] = None
    exclude_static: bool = True
    since_minutes: Optional[int] = None

class ServerOrchestrationService:
    """Manages PHP development server lifecycle.

    Follows DiskSyncService pattern for consistency.
    Uses subprocess for server management.
    Persists state to .mybb-server.json.
    """

    def __init__(self, config):
        self.config = config
        self.repo_root = config.mybb_root.parent
        self.state_file = self.repo_root / ".mybb-server.json"
        self.logs_dir = self.repo_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)

    def start(self, port: int = None) -> ServerResult:
        """Start PHP development server with log capture."""
        # Implementation in Phase 1

    def stop(self) -> ServerResult:
        """Stop running server gracefully."""
        # Implementation in Phase 1

    def restart(self) -> ServerResult:
        """Stop and start server."""
        # Implementation in Phase 2

    def get_status(self) -> ServerStatus:
        """Get current server status with validation."""
        # Implementation in Phase 1

    def query_logs(self, options: LogQueryOptions) -> str:
        """Query server logs with filtering."""
        # Implementation in Phase 2
```

### 4.2 State File Schema

```json
{
  "version": 1,
  "port": 8022,
  "pid": 12345,
  "started_at": "2026-01-20T03:42:00Z",
  "log_file": "/home/austin/projects/MyBB_Playground/logs/server.log",
  "mybb_root": "/home/austin/projects/MyBB_Playground/TestForum",
  "php_command": "php -S localhost:8022 -t ."
}
```

**Validation rules:**
- `pid` must exist in process table (check with `os.kill(pid, 0)`)
- `port` must match currently bound port (check with `lsof`)
- If validation fails, state is considered stale -> delete and report "not running"

### 4.3 Log Format & Parsing

**PHP Built-in Server Log Format:**
```
[Sun Jan 19 03:35:42 2026] 127.0.0.1:12345 Accepted
[Sun Jan 19 03:35:42 2026] 127.0.0.1:12345 [200]: GET /
[Sun Jan 19 03:35:42 2026] 127.0.0.1:12345 Closing
```

**PHP Error Format:**
```
[Sun Jan 19 03:35:42 2026] PHP Fatal error:  ... in /path/file.php on line 123
[Sun Jan 19 03:35:42 2026] PHP Warning:  ... in /path/file.php on line 456
```

**LogEntry Dataclass:**
```python
@dataclass
class LogEntry:
    timestamp: datetime
    client_ip: Optional[str]
    client_port: Optional[int]
    event_type: str  # 'request', 'error', 'info'
    status_code: Optional[int]
    method: Optional[str]  # GET, POST
    path: Optional[str]
    message: str
    is_static: bool  # True for .css, .js, .png, etc.
    is_error: bool   # True for PHP errors
```

**Static Asset Patterns (to exclude):**
```python
STATIC_PATTERNS = [
    r'/images/',
    r'/jscripts/',
    r'/cache/themes/',
    r'\.png$', r'\.gif$', r'\.jpg$', r'\.jpeg$',
    r'\.css$', r'\.js$', r'\.ico$', r'\.woff2?$',
]
```

**Error Patterns (to highlight):**
```python
ERROR_PATTERNS = [
    r'PHP Fatal error:',
    r'PHP Warning:',
    r'PHP Notice:',
    r'PHP Parse error:',
    r'\[500\]:',
    r'\[404\]:',
    r'^#\d+',  # Stack trace lines
]
```

### 4.4 MCP Tool Specifications

#### mybb_server_start

**Description:** Start the MyBB development server. Auto-detects if already running.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "port": {
      "type": "integer",
      "description": "Port to run server on (default: MYBB_PORT or 8022)",
      "default": 8022
    },
    "force": {
      "type": "boolean",
      "description": "Force start even if server appears to be running",
      "default": false
    }
  }
}
```

**Success Response:**
```markdown
# Server Started

**Port:** 8022
**PID:** 12345
**URL:** http://localhost:8022
**Log File:** logs/server.log

Server is now running. Use `mybb_server_logs` to view output.
```

**Already Running Response:**
```markdown
# Server Already Running

**Port:** 8022
**PID:** 12345
**Uptime:** 2 hours 15 minutes

Use `mybb_server_restart` to restart, or `mybb_server_stop` first.
```

**Error Response (port in use):**
```markdown
# Error: Port In Use

Port 8022 is already in use by another process (PID: 9999).

**Options:**
1. Stop the other process: `kill 9999`
2. Use a different port: `mybb_server_start(port=8023)`
3. Check what's using it: `lsof -i :8022`
```

#### mybb_server_stop

**Description:** Stop the running MyBB development server.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "force": {
      "type": "boolean",
      "description": "Force kill (SIGKILL) if graceful shutdown fails",
      "default": false
    }
  }
}
```

**Success Response:**
```markdown
# Server Stopped

**Previous PID:** 12345
**Ran for:** 2 hours 15 minutes
**Log preserved:** logs/server.log
```

#### mybb_server_status

**Description:** Get current server status including health check.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {}
}
```

**Running Response:**
```markdown
# Server Status: Running

| Property | Value |
|----------|-------|
| Port | 8022 |
| PID | 12345 |
| Uptime | 2h 15m |
| URL | http://localhost:8022 |
| Log File | logs/server.log |
| MariaDB | Running |
```

**Not Running Response:**
```markdown
# Server Status: Stopped

No MyBB server is currently running.

| Property | Value |
|----------|-------|
| MariaDB | Running |
| Last Log | logs/server.log (15 KB) |

Use `mybb_server_start` to start the server.
```

#### mybb_server_logs

**Description:** Query server logs with filtering options.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "errors_only": {
      "type": "boolean",
      "description": "Only show PHP errors and warnings",
      "default": false
    },
    "limit": {
      "type": "integer",
      "description": "Maximum lines to return",
      "default": 50
    },
    "tail": {
      "type": "boolean",
      "description": "Read from end of file (most recent)",
      "default": true
    },
    "filter": {
      "type": "string",
      "description": "Keyword to filter log entries"
    },
    "exclude_static": {
      "type": "boolean",
      "description": "Filter out static asset requests (.css, .js, images)",
      "default": true
    },
    "since_minutes": {
      "type": "integer",
      "description": "Only entries from last N minutes"
    }
  }
}
```

**Response:**
```markdown
# Server Logs

**Showing:** Last 50 entries (errors highlighted)
**Log File:** logs/server.log
**Filters:** exclude_static=true

[03:35:42] [200] GET /
[03:35:43] [200] GET /forumdisplay.php?fid=2
[03:35:44] **[500] GET /showthread.php?tid=1** <- ERROR
[03:35:44] **PHP Fatal error: Call to undefined function...** <- ERROR
[03:35:44] **#0 /path/to/file.php(123): function()** <- STACK

**Summary:** 48 requests, 2 errors
```

#### mybb_server_restart

**Description:** Restart the server (stop + start).

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "port": {
      "type": "integer",
      "description": "Port for restarted server (default: same as before)"
    }
  }
}
```

### 4.5 Service Integration

**Problem:** Cannot modify `dispatch_tool` signature to add new service parameter.

**Solution:** Module-level singleton pattern with lazy initialization.

```python
# handlers/orchestration.py

from typing import Optional
from ..orchestration.server_service import ServerOrchestrationService

# Module-level singleton
_orchestration_service: Optional[ServerOrchestrationService] = None

def get_orchestration_service(config) -> ServerOrchestrationService:
    """Get or create the orchestration service singleton."""
    global _orchestration_service
    if _orchestration_service is None:
        _orchestration_service = ServerOrchestrationService(config)
    return _orchestration_service

async def handle_server_start(args, db, config, sync_service) -> str:
    service = get_orchestration_service(config)
    # ... implementation
```

---

## 5. Directory Structure
<!-- ID: directory_structure -->

```
mybb_mcp/mybb_mcp/
|-- orchestration/                  # NEW: Server orchestration module
|   |-- __init__.py                 # Export ServerOrchestrationService
|   |-- server_service.py           # Main service class (~200 lines)
|   +-- log_parser.py               # Log parsing utilities (~150 lines)
|-- handlers/
|   |-- orchestration.py            # NEW: MCP handlers (~150 lines)
|   |-- dispatcher.py               # MODIFIED: Add ORCHESTRATION_HANDLERS
|   +-- ... (existing handlers)
|-- tools_registry.py               # MODIFIED: Add 5 server tools
+-- server.py                       # NO CHANGES (service initialized lazily)

logs/                               # EXISTING (gitignored)
|-- server.log                      # Current session log
|-- server.log.1                    # Previous session (rotated)
+-- .gitkeep                        # Ensure directory tracked

.mybb-server.json                   # NEW: Runtime state (gitignored)
.gitignore                          # MODIFIED: Add .mybb-server.json
```

---

## 6. Data & Storage
<!-- ID: data_storage -->

### State File (`.mybb-server.json`)

- **Location:** Repository root
- **Lifecycle:** Created on start, deleted on stop, validated on status
- **Concurrency:** Single writer (service), no locking needed
- **Recovery:** If stale (PID gone), delete and report stopped

### Log Files (`logs/server.log`)

- **Location:** `logs/` directory (gitignored)
- **Rotation:** On server start, rename existing to `.1` (keep only 1 backup)
- **Format:** Raw PHP server output (not structured JSON)
- **Size:** Unbounded during session, typically <10MB for dev use
- **Encoding:** UTF-8

### No Database Changes

This feature does not modify MyBB database or add new tables.

---

## 7. Testing & Validation Strategy
<!-- ID: testing_strategy -->

### Unit Tests

| Test | Location | Purpose |
|------|----------|----------|
| `test_log_parser.py` | `tests/orchestration/` | Log line parsing, filtering |
| `test_state_file.py` | `tests/orchestration/` | State file read/write/validation |
| `test_service_unit.py` | `tests/orchestration/` | Service methods with mocked subprocess |

### Integration Tests

| Test | Purpose |
|------|----------|
| `test_start_stop_cycle` | Start server, verify running, stop, verify stopped |
| `test_port_detection` | Start on custom port, verify correct binding |
| `test_log_capture` | Start server, make request, verify log entry |
| `test_stale_state_recovery` | Kill server externally, verify status detects |

### Manual Verification

1. **Basic flow:** `mybb_server_start` -> `mybb_server_status` -> `mybb_server_logs` -> `mybb_server_stop`
2. **Error handling:** Start when already running, stop when not running
3. **Log filtering:** Verify `errors_only=true` hides normal requests
4. **Backward compat:** Verify `./start_mybb.sh` still works

---

## 8. Deployment & Operations
<!-- ID: deployment_operations -->

### Rollout Plan

1. **Phase 1:** Core service + basic start/stop/status
2. **Phase 2:** Log capture and query tool
3. **Phase 3:** Tool registration and handler wiring
4. **Phase 4:** Testing and documentation

### Configuration

| Variable | Source | Default |
|----------|--------|----------|
| `MYBB_PORT` | `.env` | 8022 |
| `MYBB_ROOT` | `.env` | Required |
| Log directory | Hardcoded | `{repo_root}/logs/` |
| State file | Hardcoded | `{repo_root}/.mybb-server.json` |

### Maintenance

- **Log cleanup:** Manual or add cleanup tool in future phase
- **State recovery:** Automatic on status check
- **Upgrades:** State file has `version` field for migrations

---

## 9. Open Questions & Follow-Ups
<!-- ID: open_questions -->

| Item | Owner | Status | Resolution |
|------|-------|--------|------------|
| Should MariaDB auto-start be optional? | Architect | Resolved | Yes, with `start_mariadb` parameter (default true) |
| Multi-instance state file naming? | Architect | Deferred | Future phase: `server_{port}.json` |
| Log rotation strategy? | Architect | Resolved | Rename to `.1` on start, keep 1 backup |
| Service injection vs singleton? | Architect | Resolved | Singleton pattern (simpler, no dispatcher changes) |

---

## 10. References & Appendix
<!-- ID: references_appendix -->

### Research Documents

- `RESEARCH_SERVER_ORCHESTRATION.md` - Foundation analysis

### Code References

- `mybb_mcp/mybb_mcp/sync/service.py` - DiskSyncService pattern reference
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py` - Handler registry pattern
- `mybb_mcp/mybb_mcp/tools_registry.py` - Tool definition format
- `start_mybb.sh` - Current shell script implementation

### MyBB Documentation

- PHP Built-in Server: https://www.php.net/manual/en/features.commandline.webserver.php

---

**Document Status:** Ready for implementation
**Confidence:** 0.93 (all patterns verified against actual code)
