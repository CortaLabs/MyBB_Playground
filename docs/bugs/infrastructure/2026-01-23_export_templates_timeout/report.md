
# 🐞 mybb_sync_export_templates hangs due to async/sync mismatch blocking event loop — uninstaller-safety-fix
**Author:** Scribe
**Version:** v0.1
**Status:** Investigating
**Last Updated:** 2026-01-23 12:21:24 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** export_templates_timeout

**Reported By:** Scribe

**Date Reported:** 2026-01-23 12:21:24 UTC

**Severity:** HIGH

**Status:** INVESTIGATING

**Component:** disk_sync

**Environment:** [local/staging/production]

**Customer Impact:** [Describe impact or 'None']


---
## Description
<!-- ID: description -->
### Summary
MCP tool `mybb_sync_export_templates` hangs indefinitely when called, blocking the entire MCP server and preventing any response.

### Expected Behaviour
- Tool should export templates to disk within 2-3 seconds
- Should return export statistics (files exported, directory, groups)
- Should not block other MCP operations

### Actual Behaviour
- Tool hangs indefinitely with no timeout
- MCP server becomes unresponsive
- Database connections appear exhausted (all in "sleeping" state)
- Recent timeout fix (10s limit, increased pool size) had no effect

### Steps to Reproduce
1. Call `mybb_sync_export_templates(set_name="Default Templates")`
2. Observe indefinite hang with no response
3. Check database connections: all pool connections will be in use


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**

The bug is an **async/sync mismatch** in the template export pipeline:

1. **Handler Layer** (`handlers/sync.py` line 38):
   - Calls `await sync_service.export_template_set(set_name)`
   - Expects async operation

2. **Service Layer** (`sync/service.py` line 100):
   - Calls `await self.template_exporter.export_template_set(set_name)`
   - Expects async operation

3. **Exporter Layer** (`sync/templates.py` lines 37-67):
   - **DECLARED as `async def export_template_set()`** but...
   - **Calls SYNCHRONOUS blocking DB operations:**
     - Line 59: `template_set = self.db.get_template_set_by_name(set_name)` (BLOCKS EVENT LOOP)
     - Line 67: `templates = self._fetch_templates(sid)` (BLOCKS EVENT LOOP)
   - These sync calls use `with self.db.cursor()` which does blocking I/O

**Why This Causes Hangs:**

When an `async` function calls synchronous blocking code without wrapping it:
1. The blocking DB call runs on the **asyncio event loop thread**
2. This **blocks the entire event loop** - no other async tasks can run
3. The MCP server's timeout mechanism can't fire because it's also blocked
4. The `_get_connection_with_timeout()` timeout wrapper doesn't help because it's waiting for the event loop to free up
5. Result: **Indefinite hang** waiting for DB operations that are blocking the loop

**Why Pool Exhaustion Was Observed:**

The pool wasn't actually exhausted - connections were stuck in use because:
- The blocked event loop prevented connection cleanup
- Multiple concurrent MCP calls all blocked waiting for the same event loop
- Connections appeared "sleeping" but were held by blocked coroutines

**Affected Areas:**
- `mybb_mcp/mybb_mcp/sync/templates.py` - TemplateExporter
- `mybb_mcp/mybb_mcp/sync/stylesheets.py` - StylesheetExporter (likely has same issue)
- `mybb_mcp/mybb_mcp/handlers/sync.py` - Export handlers
- Any MCP tool using the disk sync service

**Related Issues:**
- Recent pool exhaustion fix (added timeout, increased pool size) didn't address root cause
- Sync/async mixing is a common Python asyncio anti-pattern


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Wrap synchronous DB calls in `asyncio.to_thread()` to run in thread pool
- [x] Fix `TemplateExporter.export_template_set()`:
  - Line 59: `template_set = await asyncio.to_thread(self.db.get_template_set_by_name, set_name)`
  - Line 67: `templates = await asyncio.to_thread(self._fetch_templates, sid)`
- [ ] Apply same fix to `StylesheetExporter.export_theme()` if it has the same issue
- [ ] Test export functionality

### Long-Term Fixes
- [ ] Audit all async functions in `sync/` module for sync/async mismatches
- [ ] Consider making DB layer fully async (use `aiomysql` or similar)
- [ ] Add linter rules to catch async functions calling blocking I/O

### Testing Strategy
- [x] Manual test: Call `mybb_sync_export_templates("Default Templates")`
- [x] Verify export completes within 3 seconds
- [x] Verify no pool exhaustion
- [ ] Regression test: Export while watcher is running
- [ ] Load test: Multiple concurrent export calls


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | [Name] | [Date] | [Details] |
| Fix Development | [Name] | [Date] | [Details] |
| Testing | [Name] | [Date] | [Details] |
| Deployment | [Name] | [Date] | [Details] |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:** [Link to relevant logs, traces, screenshots]
- **Fix References:** [Git commits, PRs, or documentation]
- **Open Questions:** [List unresolved unknowns or next investigations]


---