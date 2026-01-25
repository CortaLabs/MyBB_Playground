
# 🐞 Theme uninstall fails to delete from MyBB database — theme_uninstall_db_fix
**Author:** Scribe
**Version:** v0.1
**Status:** Fixed
**Last Updated:** 2026-01-24 09:34:53 UTC

> This bug report documents a critical infrastructure bug where theme uninstallation with database deletion failed due to using non-existent MyBBDatabase API methods. The fix replaces incorrect method calls with proper MyBBDatabase API usage.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** theme_uninstall_db_deletion

**Reported By:** Scribe

**Date Reported:** 2026-01-24 09:34:53 UTC

**Severity:** HIGH

**Status:** FIXED

**Component:** mybb_mcp/handlers/themes.py

**Environment:** Development (MyBB Playground MCP server)

**Customer Impact:** Users calling `mybb_theme_uninstall(codename, remove_from_db=True)` received AttributeError instead of successful theme deletion from database


---
## Description
<!-- ID: description -->
### Summary
The `mybb_theme_uninstall` MCP tool with `remove_from_db=True` parameter failed with AttributeError when attempting to delete theme records from the MyBB database. The handler used non-existent methods `db.simple_select()` and `db.delete()` which are not part of the MyBBDatabase API.

### Expected Behaviour
When calling `mybb_theme_uninstall(codename="theme_name", remove_from_db=True)`:
1. Theme should be uninstalled from TestForum (reverting customizations)
2. Theme record should be deleted from `mybb_themes` table
3. Associated stylesheet records should be deleted from `mybb_themestylesheets` table
4. Success message confirming database deletion

### Actual Behaviour
```
Failed to delete theme record from database: 'MyBBDatabase' object has no attribute 'simple_select'
```

Theme uninstallation succeeded but database records remained, requiring manual cleanup.

### Steps to Reproduce
1. Install a theme using `mybb_theme_install(codename="test_theme")`
2. Call `mybb_theme_uninstall(codename="test_theme", remove_from_db=True)`
3. Observe AttributeError in response warnings
4. Query database to confirm theme record still exists


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The `handle_theme_uninstall` function in `mybb_mcp/mybb_mcp/handlers/themes.py` (lines 471-477) used incorrect MyBBDatabase API methods:

**Incorrect Code (lines 471-477):**
```python
# Get theme ID first
theme = db.simple_select("themes", "tid,name", f"name='{codename}'")  # ❌ Method doesn't exist
if theme:
    tid = theme[0]["tid"]
    # Delete the theme record
    db.delete("themes", f"tid={tid}")  # ❌ Method doesn't exist
    # Also delete associated stylesheets
    db.delete("themestylesheets", f"tid={tid}")  # ❌ Method doesn't exist
```

**Analysis:**
1. MyBBDatabase class (connection.py) does NOT have `simple_select()` or `delete()` methods
2. Correct query method: `get_theme_by_name(name)` returns dict with theme data
3. Correct delete pattern: Use `cursor()` context manager with `execute()` for DELETE queries
4. Verified pattern by examining existing delete operations (delete_forum, delete_thread, delete_post)

**Affected Areas:**
- `mybb_mcp/mybb_mcp/handlers/themes.py` - handle_theme_uninstall function
- MCP tool: `mybb_theme_uninstall` with `remove_from_db=True` parameter
- MyBB database tables: `mybb_themes`, `mybb_themestylesheets`

**Related Issues:**
- Similar bug discovered and fixed: `2026-01-24_theme_install_incorrect_mcp_call` (installer.py used wrong MCP tool call)
- Related bug: `2026-01-24_theme_status_wrong_table` (status check queried wrong table)


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Replace `db.simple_select()` with `db.get_theme_by_name(codename)`
- [x] Replace `db.delete()` calls with proper `cursor().execute()` DELETE statements
- [x] Use parameterized queries for SQL injection safety
- [x] Delete stylesheets before theme (referential integrity best practice)

### Fix Implementation
**Corrected Code (lines 470-485):**
```python
# Get theme by name
theme = db.get_theme_by_name(codename)  # ✅ Correct API method
if theme:
    tid = theme["tid"]
    # Delete associated stylesheets first
    with db.cursor() as cur:  # ✅ Proper context manager
        cur.execute(
            f"DELETE FROM {db.table('themestylesheets')} WHERE tid = %s",  # ✅ Parameterized
            (tid,)
        )
        # Delete the theme record
        cur.execute(
            f"DELETE FROM {db.table('themes')} WHERE tid = %s",  # ✅ Parameterized
            (tid,)
        )
    result.setdefault("warnings", []).append(
        f"Theme record deleted from database (tid={tid})"
    )
```

**Key Improvements:**
1. Uses `get_theme_by_name()` which exists in MyBBDatabase API
2. Returns dict directly (not list), access `tid` via `theme["tid"]`
3. Cursor context manager ensures proper connection handling
4. Parameterized queries prevent SQL injection
5. Uses `db.table()` helper for proper table prefix handling
6. Deletes stylesheets first (foreign key best practice)

### Long-Term Fixes
- [ ] Code review: Audit all handlers for incorrect MyBBDatabase API usage
- [ ] Documentation: Update MCP handler development guide with MyBBDatabase API patterns
- [ ] Testing: Add integration tests for theme uninstall with database deletion

### Testing Strategy
- [x] Code inspection verified correct MyBBDatabase API usage
- [ ] Manual test: Install theme, uninstall with `remove_from_db=True`, verify database deletion
- [ ] Regression test: Ensure uninstall without `remove_from_db` still works
- [ ] Edge cases: Test with non-existent theme, test with theme that has multiple stylesheets


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Status | Notes |
| --- | --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 2026-01-24 | ✅ Complete | Root cause identified - incorrect API usage |
| Fix Development | MyBBBugHunter | 2026-01-24 | ✅ Complete | Replaced with correct MyBBDatabase API methods |
| Code Review | Pending | TBD | ⏳ Pending | Review fix and test |
| Testing | Pending | TBD | ⏳ Pending | Manual + regression testing needed |
| Deployment | Auto | N/A | ✅ Complete | Fix in source, active on next MCP restart |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:**
  - Error message: `'MyBBDatabase' object has no attribute 'simple_select'`
  - Scribe Progress Log: `.scribe/docs/dev_plans/theme_uninstall_db_fix/PROGRESS_LOG.md`

- **Fix References:**
  - File modified: `mybb_mcp/mybb_mcp/handlers/themes.py` (lines 470-485)
  - MyBBDatabase API reference: `mybb_mcp/mybb_mcp/db/connection.py`
  - Related methods: `get_theme_by_name()`, `cursor()`, `table()`

- **Open Questions:**
  - Are there other handlers using incorrect MyBBDatabase API methods?
  - Should we add MyBBDatabase API documentation to wiki?
  - Should we create integration tests for all theme MCP tools?

- **Prevention Measures:**
  - Code review checklist: Verify MyBBDatabase API usage in all handlers
  - Add MyBBDatabase API patterns to development guidelines
  - Consider adding linter rules to catch non-existent method calls


---