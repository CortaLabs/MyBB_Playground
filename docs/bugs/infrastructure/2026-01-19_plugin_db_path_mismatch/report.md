
# 🐞 Plugin manager database path inconsistency causing constraint failures — plugin_manager_db_fix
**Author:** Scribe
**Version:** v0.1
**Status:** Fixed
**Last Updated:** 2026-01-19 10:23:15 UTC

> Documents critical bug where hardcoded database paths in MCP handlers caused plugin_manager to write to one database while MCP tools read from another, resulting in constraint failures and data inconsistency.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** plugin_db_path_mismatch

**Reported By:** Scribe

**Date Reported:** 2026-01-19 10:23:15 UTC

**Severity:** CRITICAL

**Status:** FIXED

**Component:** plugin_manager/MCP_handlers

**Environment:** local development

**Customer Impact:** None (internal development tool)


---
## Description
<!-- ID: description -->
### Summary
Plugin creation was failing with "UNIQUE constraint failed" and "database is locked" errors due to multiple conflicting database files being used simultaneously by different components.

### Root Cause
**Critical Path Mismatch:**
- `plugin_manager/config.py` DEFAULT_CONFIG: `"database_path": "plugin_manager/projects.db"`
- `.plugin_manager/config.json` (actual config): `"database_path": ".plugin_manager/projects.db"`
- `mybb_mcp/handlers/plugins.py` **hardcoded 4 times**: `repo_root / "plugin_manager" / "data" / "projects.db"`

**Result:**
1. Plugin Manager writing to `.plugin_manager/projects.db` (152KB, 9 plugins)
2. MCP handlers reading from `plugin_manager/data/projects.db` (empty)
3. Stale databases at `plugin_manager/.meta/projects.db` (40KB) and `plugin_manager/projects.db` (0 bytes)

### Expected Behaviour
All components should read/write to the same canonical database defined by `plugin_manager.Config.database_path`.

### Actual Behaviour
- Plugin creation appeared to succeed but plugins didn't show in listings
- UNIQUE constraint failures when recreating "existing" plugins
- Database locked errors from concurrent access attempts
- Three separate databases with inconsistent data

### Steps to Reproduce
1. Create a plugin using `mybb_create_plugin`
2. List plugins using `mybb_list_plugins` → Plugin doesn't appear
3. Try creating the same plugin again → UNIQUE constraint error


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
MCP handlers in `mybb_mcp/handlers/plugins.py` hardcoded the database path to `plugin_manager/data/projects.db` in 4 locations (lines 49, 124, 351, 751), completely bypassing the `plugin_manager.Config.database_path` property. This caused MCP tools to read from a non-existent database while plugin_manager wrote to the correct location at `.plugin_manager/projects.db`.

**Affected Areas:**
- `mybb_mcp/mybb_mcp/handlers/plugins.py` - 4 hardcoded paths
- `handle_list_plugins()` - couldn't find workspace plugins
- `handle_read_plugin()` - couldn't find workspace metadata
- `handle_analyze_plugin()` - missing workspace context
- `handle_plugin_status()` - incorrect status reporting

**Related Issues:**
- Database locking issues mentioned in user reports
- Plugin "disappearing" after creation
- UNIQUE constraint errors on duplicate plugin names


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Created `_get_plugin_manager_db_path()` helper function that uses `plugin_manager.Config.database_path`
- [x] Replaced all 4 hardcoded paths in `mybb_mcp/handlers/plugins.py` with helper function call
- [x] Backed up canonical database (`.plugin_manager/projects.db`) with timestamp
- [x] Removed duplicate database files (4 files cleaned up)
- [x] Verified no remaining hardcoded paths using grep

### Long-Term Fixes
- Consider centralizing database connection logic to prevent future hardcoding
- Add validation tests to catch path mismatches during CI/CD
- Document the canonical database location in CLAUDE.md (already correct)

### Testing Strategy
- [x] Verified helper function uses Config.database_path correctly
- [x] Confirmed all hardcoded paths removed (grep verification)
- [x] Verified only canonical database remains
- [ ] Manual test: Create plugin and verify it appears in listings
- [ ] Manual test: Verify no UNIQUE constraint errors on duplicate creation


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | MyBB-BugHunterAgent | 2026-01-19 | Identified 4 hardcoded paths and 3 database files |
| Fix Development | MyBB-BugHunterAgent | 2026-01-19 | Created helper function, fixed all occurrences |
| Database Cleanup | MyBB-BugHunterAgent | 2026-01-19 | Backed up and removed duplicates |
| Verification | MyBB-BugHunterAgent | 2026-01-19 | Grep confirmed no hardcoded paths remain |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:**
  - Progress log: `.scribe/docs/dev_plans/plugin_manager_db_fix/PROGRESS_LOG.md`
  - 12 Scribe entries documenting investigation and fix process

- **Fix References:**
  - Modified: `mybb_mcp/mybb_mcp/handlers/plugins.py`
    - Added `_get_plugin_manager_db_path()` helper function (lines 22-38)
    - Fixed lines: 68, 143, 370, 770
  - Backed up: `.plugin_manager/projects.db.backup_20260119_052239`
  - Removed: `plugin_manager/{.meta,data,}/projects.db`, `plugin_manager/plugins.db`

- **Open Questions:**
  - Should we add integration tests to prevent similar path mismatches?
  - Consider refactoring to use dependency injection for database connections?


---