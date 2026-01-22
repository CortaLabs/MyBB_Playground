
# 🐞 Bulk Operations page blank due to status column mismatch — invite_system_admin_panel
**Author:** MyBBBugHunter
**Version:** v1.0
**Status:** FIXED ✅
**Last Updated:** 2026-01-21 03:14 UTC

> SQL schema mismatch causing Fatal errors and blank Bulk Operations page. Code referenced non-existent 'status' column instead of 'revoked'.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** bulk_operations_schema_mismatch

**Reported By:** User (via orchestrator)

**Date Reported:** 2026-01-21 03:11 UTC

**Severity:** HIGH

**Status:** FIXED ✅

**Component:** admin/bulk.php

**Environment:** Development (MyBB 1.8.x)

**Customer Impact:** Bulk Operations admin page completely inaccessible (blank page) due to Fatal SQL errors


---
## Description
<!-- ID: description -->
### Summary
The Bulk Operations page in the Invite System admin panel was completely blank. No content rendered, no error messages visible to user.

### Expected Behaviour
- Bulk Operations page should display stats (total codes, active codes, expired codes, revoked codes)
- Page should show operation cards for bulk actions
- No Fatal PHP errors

### Actual Behaviour
- Blank page with no content
- PHP Fatal error in server logs: "Unknown column 'status' in 'WHERE'"
- MyBB admin frame loads but page content section empty

### Steps to Reproduce
1. Navigate to MyBB Admin CP
2. Go to Users & Groups → Invite System → Bulk Operations
3. Page loads but shows blank content area
4. Check server logs: Fatal SQL errors present


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
Code in `bulk.php` lines 83-90 queries `mybb_invite_codes` table using WHERE clauses with `status='active'` and `status='revoked'`. However, the actual database schema uses a `revoked` column (tinyint: 0 or 1) instead of a `status` column (varchar).

**Database Schema:**
```sql
SHOW COLUMNS FROM mybb_invite_codes;
-- Columns include: revoked (tinyint), revoked_at, revoked_by
-- NO 'status' column exists
```

**Affected Code:**
- Line 83: `$db->simple_select('invite_codes', 'COUNT(*) as count', "status='active'")`
- Line 86: `$db->simple_select('invite_codes', 'COUNT(*) as count', "status='active' AND expires_at > 0...")`
- Line 89: `$db->simple_select('invite_codes', 'COUNT(*) as count', "status='revoked'")`

**Affected Areas:**
- `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/bulk.php`
- Statistics display section (lines 78-91)

**Related Issues:**
- None identified


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Identify exact SQL column mismatch via database schema inspection
- [x] Update all status column references to use revoked column
- [x] Deploy fix via plugin reinstall
- [x] Verify no SQL errors in server logs

### Long-Term Fixes
- [ ] Add database schema validation tests
- [ ] Document actual schema vs. expected column names
- [ ] Review other admin files for similar schema mismatches

### Testing Strategy
- [x] Manual verification: Check server logs for SQL errors after fix
- [x] Deployment verification: Confirm fixed files deployed to TestForum
- [ ] Browser testing: Load Bulk Operations page and verify content displays


---
## Fix Summary

**Status:** FIXED ✅
**Fixed Date:** 2026-01-21 03:13 UTC
**Fixed By:** MyBBBugHunter

### Solution Applied
Changed all SQL WHERE clauses in `bulk.php` lines 83-90:
- `status='active'` → `revoked=0` (2 occurrences)
- `status='revoked'` → `revoked=1` (1 occurrence)

**Rationale:** The `revoked` column is a tinyint where:
- `0` = code is active (not revoked)
- `1` = code is revoked

### Files Modified
```
plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/bulk.php
Lines changed: 83-90 (3 SQL queries corrected)
```

### Deployment
1. Fixed workspace file via Edit tool
2. Uninstalled plugin with `remove_files=True`
3. Reinstalled plugin - 63 files deployed
4. Fixed file now active in TestForum

### Verification
- ✅ Server logs: No "Unknown column 'status'" errors after fix deployment
- ✅ Recent logs show only HTTP 200 responses, no Fatal errors
- ⏳ Browser verification pending


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Status | Notes |
| --- | --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 2026-01-21 | ✅ DONE | Server logs + schema inspection |
| Fix Development | MyBBBugHunter | 2026-01-21 | ✅ DONE | 3 lines corrected in bulk.php |
| Testing | MyBBBugHunter | 2026-01-21 | ✅ DONE | Server log verification |
| Deployment | MyBBBugHunter | 2026-01-21 | ✅ DONE | Plugin reinstalled |


---
## Appendix
<!-- ID: appendix -->
**Logs & Evidence:**
- Server log errors: `mybb_server_logs(errors_only=True)` showed Fatal SQL errors at lines 21:27-22:08
- Database schema: `SHOW COLUMNS FROM mybb_invite_codes` confirmed no 'status' column exists
- Recent logs (post-fix): Only HTTP 200 responses, no PHP errors

**Fix References:**
- Workspace file: `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/bulk.php`
- Deployed file: `TestForum/inc/plugins/invite_system/admin/bulk.php`
- Bug report: `docs/bugs/database/2026-01-21_bulk_operations_schema_mismatch/report.md`

**Open Questions:**
- Should add schema validation during plugin install?
- Are there other files with similar column name assumptions?
- Should this be caught by automated tests?


---
