# Acceptance Checklist: Server Orchestration Layer

**Author:** MyBB-ArchitectAgent
**Version:** 1.0
**Status:** Approved
**Last Updated:** 2026-01-20
**Phase Plan Reference:** PHASE_PLAN.md

---

## Documentation Hygiene
<!-- ID: documentation_hygiene -->

- [x] Architecture guide complete (proof: ARCHITECTURE_GUIDE.md)
- [x] Phase plan with task packages (proof: PHASE_PLAN.md)
- [x] Research verified against code (proof: PROGRESS_LOG.md entries)
- [ ] Wiki documentation added (proof: docs/wiki/mcp_tools/orchestration.md)

---

## Phase 1: Core Infrastructure
<!-- ID: phase_1 -->

### Task 1.1: Module Structure
<!-- ID: phase_1_task_1 -->
- [ ] `orchestration/__init__.py` created
- [ ] `orchestration/server_service.py` created
- [ ] Dataclasses defined: `ServerResult`, `ServerStatus`, `LogQueryOptions`
- [ ] Import works: `from mybb_mcp.orchestration import ServerOrchestrationService`

**Verification:** `python -c "from mybb_mcp.orchestration import ServerOrchestrationService"`

### Task 1.2: State File Management
<!-- ID: phase_1_task_2 -->
- [ ] `_read_state()` implemented
- [ ] `_write_state()` implemented with atomic write
- [ ] `_validate_state()` checks PID exists
- [ ] `_clear_state()` removes file

**Verification:** Unit tests in `tests/orchestration/test_state_file.py`

### Task 1.3: Get Status Method
<!-- ID: phase_1_task_3 -->
- [ ] `get_status()` returns `ServerStatus`
- [ ] Stale state auto-cleaned
- [ ] MariaDB check works
- [ ] Uptime calculated correctly

**Verification:** Manual test with state file present/absent

### Task 1.4: Start and Stop Methods
<!-- ID: phase_1_task_4 -->
- [ ] `_check_port_available()` implemented
- [ ] `_rotate_log()` renames existing log
- [ ] `start()` creates log file and state file
- [ ] `start()` returns error if port in use
- [ ] `stop()` sends SIGTERM and clears state
- [ ] `stop()` supports force kill

**Verification:** Manual test cycle: start -> status -> stop -> status

---

## Phase 2: Log System
<!-- ID: phase_2 -->

### Task 2.1: Log Parser Module
<!-- ID: phase_2_task_1 -->
- [ ] `LogEntry` dataclass created
- [ ] `STATIC_PATTERNS` constant defined
- [ ] `ERROR_PATTERNS` constant defined
- [ ] `parse_log_line()` parses request format
- [ ] `parse_log_line()` parses PHP error format
- [ ] `is_static_request()` works
- [ ] `is_error_line()` works

**Verification:** Unit tests in `tests/orchestration/test_log_parser.py`

### Task 2.2: Log Query and Restart
<!-- ID: phase_2_task_2 -->
- [ ] `query_logs()` reads log file
- [ ] `errors_only` filter works
- [ ] `exclude_static` filter works
- [ ] `filter_keyword` search works
- [ ] `since_minutes` time filter works
- [ ] Returns markdown with summary
- [ ] `restart()` stops then starts

**Verification:** Manual test with sample log entries

---

## Phase 3: MCP Integration
<!-- ID: phase_3 -->

### Task 3.1: Tool Definitions
<!-- ID: phase_3_task_1 -->
- [ ] `ORCHESTRATION_TOOLS` list created in `tools_registry.py`
- [ ] `mybb_server_start` tool defined
- [ ] `mybb_server_stop` tool defined
- [ ] `mybb_server_status` tool defined
- [ ] `mybb_server_logs` tool defined
- [ ] `mybb_server_restart` tool defined
- [ ] Tools added to `ALL_TOOLS`

**Verification:** `len(ALL_TOOLS)` increased by 5

### Task 3.2: Handlers Module
<!-- ID: phase_3_task_2 -->
- [ ] `handlers/orchestration.py` created
- [ ] Singleton pattern implemented
- [ ] `handle_server_start` handler
- [ ] `handle_server_stop` handler
- [ ] `handle_server_status` handler
- [ ] `handle_server_logs` handler
- [ ] `handle_server_restart` handler
- [ ] `ORCHESTRATION_HANDLERS` dict created
- [ ] Registered in `dispatcher.py`

**Verification:** MCP tools respond when called via Claude

### Task 3.3: Gitignore Update
<!-- ID: phase_3_task_3 -->
- [ ] `.mybb-server.json` added to `.gitignore`

**Verification:** `git status` does not show state file

---

## Phase 4: Testing & Polish
<!-- ID: phase_4 -->

### Task 4.1: Unit Tests
<!-- ID: phase_4_task_1 -->
- [ ] `tests/orchestration/__init__.py` created
- [ ] `test_log_parser.py` with 4+ test cases
- [ ] `test_state_file.py` with 4+ test cases
- [ ] All tests pass: `pytest tests/orchestration/`

**Verification:** CI green or local pytest output

### Task 4.2: Wiki Documentation
<!-- ID: phase_4_task_2 -->
- [ ] `docs/wiki/mcp_tools/orchestration.md` created
- [ ] All 5 tools documented with examples
- [ ] `docs/wiki/mcp_tools/index.md` updated

**Verification:** Links work, content complete

---

## Final Verification
<!-- ID: final_verification -->

- [ ] All Phase 1-4 checklist items complete
- [ ] Manual test: full lifecycle (start -> status -> logs -> stop)
- [ ] Manual test: error cases (port conflict, not running)
- [ ] Shell scripts still work (`./start_mybb.sh`)
- [ ] Review Agent approval (>=93%)
- [ ] No regressions in existing MCP tools

---

## Acceptance Criteria Summary

| Requirement | Acceptance Test | Status |
|-------------|-----------------|--------|
| FR1: Start with log capture | `mybb_server_start` creates `logs/server.log` | Pending |
| FR2: Stop by PID | `mybb_server_stop` terminates process | Pending |
| FR3: Query status | `mybb_server_status` returns running/stopped | Pending |
| FR4: Query logs with filters | `mybb_server_logs(errors_only=true)` works | Pending |
| FR5: Port conflict detection | Start on busy port returns helpful error | Pending |
| FR6: Log rotation | Previous log renamed to `.1` on start | Pending |
| FR7: Restart | `mybb_server_restart` stops then starts | Pending |
| NFR3: Backward compat | `./start_mybb.sh` still works | Pending |

---

**Document Status:** Ready for implementation tracking
**All checklist items must be completed before Review Agent approval**
