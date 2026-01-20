# Phase Plan: Server Orchestration Layer

**Author:** MyBB-ArchitectAgent
**Version:** 1.0
**Status:** Approved
**Last Updated:** 2026-01-20
**Architecture Source:** ARCHITECTURE_GUIDE.md

---

## Phase Overview
<!-- ID: phase_overview -->

| Phase | Goal | Key Deliverables | Est. Effort | Confidence |
|-------|------|------------------|-------------|------------|
| Phase 1 | Core Infrastructure | Service class, state file, dataclasses | 2-3 hours | 0.95 |
| Phase 2 | Log System | Log capture, rotation, parser | 2-3 hours | 0.90 |
| Phase 3 | MCP Integration | Tool definitions, handlers, dispatcher | 2-3 hours | 0.95 |
| Phase 4 | Testing & Polish | Unit tests, integration tests, docs | 2-3 hours | 0.85 |

**Total Estimated Effort:** 8-12 hours
**Parallelization:** Phases 1-2 can be done by same coder sequentially. Phase 3 depends on 1-2. Phase 4 depends on all.

---

## Phase 1: Core Infrastructure
<!-- ID: phase_1 -->

**Objective:** Create the ServerOrchestrationService class with basic lifecycle methods.

### Task Package 1.1: Create orchestration module structure

**Scope:** Create the `orchestration/` directory and module files.

**Files to Create:**
- `mybb_mcp/mybb_mcp/orchestration/__init__.py`
- `mybb_mcp/mybb_mcp/orchestration/server_service.py`

**Specifications:**
1. Create `__init__.py` that exports `ServerOrchestrationService`
2. Create `server_service.py` with:
   - Dataclasses: `ServerResult`, `ServerStatus`, `LogQueryOptions`
   - `ServerOrchestrationService` class skeleton with `__init__`

**Verification:**
- [ ] `from mybb_mcp.orchestration import ServerOrchestrationService` works
- [ ] Service initializes with config parameter

**Out of Scope:** Do NOT implement lifecycle methods yet (Phase 1.2-1.4)

---

### Task Package 1.2: Implement state file management

**Scope:** Add state file read/write/validate methods to ServerOrchestrationService.

**Files to Modify:**
- `mybb_mcp/mybb_mcp/orchestration/server_service.py` (lines 50-150 region)

**Specifications:**
1. Add method `_read_state() -> Optional[dict]`:
   - Read `.mybb-server.json` from repo root
   - Return None if file doesn't exist
   - Return parsed JSON dict if exists

2. Add method `_write_state(state: dict) -> None`:
   - Write to temp file, then atomic rename
   - Include `version: 1` field

3. Add method `_validate_state(state: dict) -> bool`:
   - Check PID exists: `os.kill(state['pid'], 0)` (catches ProcessLookupError)
   - Return False if PID doesn't exist
   - Return True if PID valid

4. Add method `_clear_state() -> None`:
   - Delete state file if exists

**Verification:**
- [ ] State file round-trips correctly
- [ ] Invalid PID returns False from validate
- [ ] Clear removes file

**Out of Scope:** Do NOT check port availability yet (Phase 1.3)

---

### Task Package 1.3: Implement get_status method

**Scope:** Complete the `get_status()` method with state validation.

**Files to Modify:**
- `mybb_mcp/mybb_mcp/orchestration/server_service.py` (lines 150-200 region)

**Specifications:**
1. Implement `get_status() -> ServerStatus`:
   - Read state file
   - If no state: return `ServerStatus(running=False)`
   - If state exists: validate PID
   - If PID invalid: clear state, return `ServerStatus(running=False)`
   - If PID valid: calculate uptime, return full status
   - Check MariaDB: `subprocess.run(['pgrep', '-x', 'mariadbd'], ...)` or `mysqld`

2. Add helper `_check_mariadb() -> bool`:
   - Return True if mariadbd or mysqld process exists

**Verification:**
- [ ] Returns running=False when no state file
- [ ] Returns running=True when valid state exists
- [ ] Cleans up stale state automatically

**Out of Scope:** Do NOT implement start/stop yet (Phase 1.4)

---

### Task Package 1.4: Implement start and stop methods

**Scope:** Complete `start()` and `stop()` methods.

**Files to Modify:**
- `mybb_mcp/mybb_mcp/orchestration/server_service.py` (lines 200-350 region)

**Specifications:**
1. Add method `_check_port_available(port: int) -> tuple[bool, Optional[int]]`:
   - Use `lsof -i :{port}` to check if port in use
   - Return `(True, None)` if available
   - Return `(False, pid)` if in use

2. Add method `_rotate_log() -> None`:
   - If `logs/server.log` exists, rename to `logs/server.log.1`

3. Implement `start(port: int = None, force: bool = False) -> ServerResult`:
   - Default port from env var `MYBB_PORT` or 8022
   - Check if already running (get_status)
   - If running and not force: return already-running result
   - Check port available
   - If port in use: return error result with PID
   - Rotate log file
   - Start PHP server with log capture:
     ```python
     cmd = f"cd {mybb_root} && php -S localhost:{port} -t . >> {log_file} 2>&1 &"
     subprocess.Popen(cmd, shell=True, ...)
     ```
   - Wait briefly (0.5s), verify process started
   - Write state file
   - Return success result

4. Implement `stop(force: bool = False) -> ServerResult`:
   - Get current status
   - If not running: return not-running result
   - Send SIGTERM to PID
   - Wait up to 5 seconds for process to exit
   - If still running and force: send SIGKILL
   - Clear state file
   - Return success result with uptime

**Verification:**
- [ ] Start creates server.log
- [ ] Start writes state file
- [ ] Stop removes state file
- [ ] Port conflict returns helpful error

**Out of Scope:** Do NOT implement restart (Phase 2), query_logs (Phase 2)

---

## Phase 2: Log System
<!-- ID: phase_2 -->

**Objective:** Implement log capture, rotation, and query functionality.

### Task Package 2.1: Create log parser module

**Scope:** Create the log parsing utilities.

**Files to Create:**
- `mybb_mcp/mybb_mcp/orchestration/log_parser.py`

**Specifications:**
1. Create `LogEntry` dataclass with fields from ARCHITECTURE_GUIDE section 4.3

2. Define constants:
   - `STATIC_PATTERNS` - list of regex patterns for static assets
   - `ERROR_PATTERNS` - list of regex patterns for PHP errors

3. Implement `parse_log_line(line: str) -> Optional[LogEntry]`:
   - Parse PHP server log format: `[timestamp] ip:port [status]: METHOD /path`
   - Parse PHP error format: `[timestamp] PHP Fatal error: ...`
   - Extract timestamp, status_code, method, path, error flags
   - Return None for unparseable lines

4. Implement `is_static_request(entry: LogEntry) -> bool`:
   - Match path against STATIC_PATTERNS

5. Implement `is_error_line(entry: LogEntry) -> bool`:
   - Match message against ERROR_PATTERNS or status >= 400

**Verification:**
- [ ] Parses request lines correctly
- [ ] Parses PHP error lines correctly
- [ ] Static detection works for .css, .js, /images/

**Out of Scope:** Do NOT implement filtering or formatting yet (Phase 2.2)

---

### Task Package 2.2: Implement log query and restart methods

**Scope:** Complete query_logs and restart methods in service.

**Files to Modify:**
- `mybb_mcp/mybb_mcp/orchestration/server_service.py` (add to end)
- `mybb_mcp/mybb_mcp/orchestration/__init__.py` (export LogQueryOptions)

**Specifications:**
1. Implement `query_logs(options: LogQueryOptions) -> str`:
   - Read log file (handle not exists)
   - If tail: read last N lines (use deque for efficiency)
   - Parse each line with log_parser
   - Filter by:
     - `errors_only`: only entries where is_error=True
     - `exclude_static`: skip entries where is_static=True
     - `filter_keyword`: case-insensitive search in message
     - `since_minutes`: compare timestamp to now
   - Format as markdown with summary stats

2. Implement `restart(port: int = None) -> ServerResult`:
   - Call stop()
   - Wait 1 second
   - Call start(port)
   - Return combined result

**Verification:**
- [ ] query_logs returns markdown
- [ ] errors_only filter works
- [ ] exclude_static filter works
- [ ] restart stops then starts

**Out of Scope:** Do NOT create MCP tools yet (Phase 3)

---

## Phase 3: MCP Integration
<!-- ID: phase_3 -->

**Objective:** Wire up MCP tools and handlers for the orchestration service.

### Task Package 3.1: Add tool definitions

**Scope:** Add 5 server orchestration tools to tools_registry.py.

**Files to Modify:**
- `mybb_mcp/mybb_mcp/tools_registry.py` (add new section after SYNC_TOOLS)

**Specifications:**
1. Create `ORCHESTRATION_TOOLS` list with 5 Tool() definitions:
   - `mybb_server_start` - per ARCHITECTURE_GUIDE section 4.4
   - `mybb_server_stop` - per ARCHITECTURE_GUIDE section 4.4
   - `mybb_server_status` - per ARCHITECTURE_GUIDE section 4.4
   - `mybb_server_logs` - per ARCHITECTURE_GUIDE section 4.4
   - `mybb_server_restart` - per ARCHITECTURE_GUIDE section 4.4

2. Add `ORCHESTRATION_TOOLS` to `ALL_TOOLS` list at bottom

**Verification:**
- [ ] All 5 tools appear in `ALL_TOOLS`
- [ ] Input schemas match ARCHITECTURE_GUIDE specs

**Out of Scope:** Do NOT create handlers yet (Phase 3.2)

---

### Task Package 3.2: Create handlers module

**Scope:** Create orchestration handlers and wire to dispatcher.

**Files to Create:**
- `mybb_mcp/mybb_mcp/handlers/orchestration.py`

**Files to Modify:**
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py` (add import and registry)

**Specifications:**
1. Create `handlers/orchestration.py`:
   - Module-level singleton pattern (see ARCHITECTURE_GUIDE section 4.5)
   - `get_orchestration_service(config)` function
   - 5 async handler functions:
     - `handle_server_start(args, db, config, sync_service) -> str`
     - `handle_server_stop(args, db, config, sync_service) -> str`
     - `handle_server_status(args, db, config, sync_service) -> str`
     - `handle_server_logs(args, db, config, sync_service) -> str`
     - `handle_server_restart(args, db, config, sync_service) -> str`
   - Each handler formats result as markdown per ARCHITECTURE_GUIDE

2. Create `ORCHESTRATION_HANDLERS` dict at module end

3. Modify `dispatcher.py`:
   - Add import: `from .orchestration import ORCHESTRATION_HANDLERS`
   - Add: `HANDLER_REGISTRY.update(ORCHESTRATION_HANDLERS)`

**Verification:**
- [ ] All 5 handlers registered in dispatcher
- [ ] Handlers return markdown-formatted strings
- [ ] Error handling wraps exceptions

**Out of Scope:** Do NOT add tests yet (Phase 4)

---

### Task Package 3.3: Update gitignore

**Scope:** Add state file to gitignore.

**Files to Modify:**
- `.gitignore` (add line)

**Specifications:**
1. Add `.mybb-server.json` to gitignore (server state file)

**Verification:**
- [ ] State file not tracked by git

---

## Phase 4: Testing & Polish
<!-- ID: phase_4 -->

**Objective:** Add tests and documentation.

### Task Package 4.1: Create unit tests

**Scope:** Add unit tests for log parser and state management.

**Files to Create:**
- `tests/orchestration/__init__.py`
- `tests/orchestration/test_log_parser.py`
- `tests/orchestration/test_state_file.py`

**Specifications:**
1. `test_log_parser.py`:
   - Test parse_log_line with request lines
   - Test parse_log_line with PHP error lines
   - Test is_static_request
   - Test is_error_line

2. `test_state_file.py`:
   - Test _write_state / _read_state round trip
   - Test _validate_state with valid PID
   - Test _validate_state with invalid PID
   - Test _clear_state

**Verification:**
- [ ] `pytest tests/orchestration/` passes

**Out of Scope:** Integration tests requiring actual server (manual verification)

---

### Task Package 4.2: Update wiki documentation

**Scope:** Add orchestration tools to wiki.

**Files to Create:**
- `docs/wiki/mcp_tools/orchestration.md`

**Files to Modify:**
- `docs/wiki/mcp_tools/index.md` (add orchestration section)

**Specifications:**
1. Create `orchestration.md` documenting all 5 tools
2. Update `index.md` to reference new page

**Verification:**
- [ ] Wiki page complete with examples

---

## Milestone Tracking
<!-- ID: milestone_tracking -->

| Milestone | Target | Owner | Status | Evidence |
|-----------|--------|-------|--------|----------|
| Phase 1 Complete | Day 1 | Coder | Pending | Unit tests pass |
| Phase 2 Complete | Day 1 | Coder | Pending | Log query works |
| Phase 3 Complete | Day 2 | Coder | Pending | MCP tools respond |
| Phase 4 Complete | Day 2 | Coder | Pending | Tests pass, docs done |
| Production Ready | Day 2 | Review | Pending | Review approval |

---

## Dependencies Graph

```
Phase 1.1 (module structure)
    |
    v
Phase 1.2 (state file) --> Phase 1.3 (get_status)
                                |
                                v
                          Phase 1.4 (start/stop)
                                |
    +---------------------------+
    |                           |
    v                           v
Phase 2.1 (log parser)    Phase 3.1 (tool defs)
    |                           |
    v                           |
Phase 2.2 (query_logs) --------+
                                |
                                v
                          Phase 3.2 (handlers)
                                |
                                v
                          Phase 3.3 (gitignore)
                                |
                                v
                          Phase 4.1 (tests)
                                |
                                v
                          Phase 4.2 (docs)
```

**Parallel Opportunities:**
- Phase 2.1 and Phase 3.1 can run in parallel after Phase 1.4
- Phase 3.3 can be done anytime

---

## Retro Notes & Adjustments
<!-- ID: retro_notes -->

*To be filled after implementation*

---

**Document Status:** Ready for implementation
**Architecture Reference:** See ARCHITECTURE_GUIDE.md for detailed specifications
