
# 🐞 Invite Logs spam section fails due to timestamp/reason column mismatch — invite_system_admin_panel
**Author:** MyBBBugHunter
**Version:** v1.0
**Status:** FIXED ✅
**Last Updated:** 2026-01-21 03:14 UTC

> SQL schema mismatch in spam log queries causing Fatal errors. Code referenced 'timestamp' and 'reason' columns that don't exist in mybb_invite_spam_log table.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** spam_logs_schema_mismatch

**Reported By:** User (via orchestrator)

**Date Reported:** 2026-01-21 03:11 UTC

**Severity:** HIGH

**Status:** FIXED ✅

**Component:** admin/modules/tools/invite_logs.php

**Environment:** Development (MyBB 1.8.x)

**Customer Impact:** Invite System Logs page in Tools & Maintenance section crashes with Fatal SQL error when trying to display spam log entries


---
## Description
<!-- ID: description -->
### Summary
The Invite System Logs page (Tools & Maintenance → Invite System Logs) fails to load spam log data due to SQL column name mismatches.

### Expected Behaviour
- Logs page should display all log types including spam blocks
- Spam log entries should show with email, reason, IP, and timestamp
- Date filters and search should work on spam logs
- No Fatal PHP errors

### Actual Behaviour
- Page attempts to load spam logs from mybb_invite_spam_log table
- PHP Fatal error: "Unknown column 'timestamp' in 'ORDER BY'"
- Additional errors for 'reason' column in LIKE clause
- Spam logs section fails to render

### Steps to Reproduce
1. Navigate to MyBB Admin CP
2. Go to Tools & Maintenance → Invite System Logs
3. Page attempts to query spam log table
4. Fatal SQL error occurs
5. Check server logs: Multiple "Unknown column" errors


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
Code in `invite_logs.php` lines 247-275 queries `mybb_invite_spam_log` table using columns that don't exist:
- Queries use `timestamp` but actual column is `blocked_at`
- Queries use `reason` but actual column is `blocked_reason`

**Database Schema:**
```sql
SHOW COLUMNS FROM mybb_invite_spam_log;
-- Columns: id, ip_address, email, action, blocked_reason, blocked_at, request_data
-- NO 'timestamp' or 'reason' columns exist
```

**Affected Code:**
- Line 250: WHERE clause `timestamp >= {$from_ts}`
- Line 255: WHERE clause `timestamp <= {$to_ts}`
- Line 259: LIKE clause `reason LIKE '%...'`
- Line 262: ORDER BY `timestamp`
- Line 267: Row access `$row['timestamp']`
- Line 272: JSON data `'reason' => $row['reason']`

**Affected Areas:**
- `admin/modules/tools/invite_logs.php` spam log query section (lines 243-276)
- Date filtering functionality
- Search functionality
- Log display output

**Related Issues:**
- None identified


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Identify exact SQL column mismatches via database schema inspection
- [x] Update all timestamp references to blocked_at
- [x] Update all reason references to blocked_reason
- [x] Manually deploy fixed file to admin/modules/tools/
- [x] Verify no SQL errors in server logs

### Long-Term Fixes
- [ ] Automate deployment of admin/modules/tools/ files in plugin install
- [ ] Add database schema validation for custom tables
- [ ] Document schema expectations vs. actual table structure

### Testing Strategy
- [x] Manual verification: Check server logs for SQL errors after fix
- [x] Deployment verification: Confirm fixed file in correct location
- [ ] Browser testing: Load logs page and verify spam logs display


---
## Fix Summary

**Status:** FIXED ✅
**Fixed Date:** 2026-01-21 03:13 UTC
**Fixed By:** MyBBBugHunter

### Solution Applied
Changed all SQL column references in `invite_logs.php` lines 247-275:
- `timestamp` → `blocked_at` (4 occurrences: 2 WHERE, 1 ORDER BY, 1 row access)
- `reason` → `blocked_reason` (2 occurrences: 1 LIKE, 1 json_encode)

**Rationale:** The `mybb_invite_spam_log` table uses:
- `blocked_at` (int) for Unix timestamp
- `blocked_reason` (varchar 100) for reason text

### Files Modified
```
plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/modules/tools/invite_logs.php
Lines changed: 247-275 (6 column references corrected)
```

### Deployment
1. Fixed workspace file via Edit tool
2. **Manual deployment required** - tools modules not handled by plugin install
3. Copied fixed file to: `TestForum/admin/modules/tools/invite_logs.php`
4. Fixed file now active in MyBB admin

**Deployment Note:** This file requires manual copy because it lives in `admin/modules/tools/` outside the plugin directory. Plugin install doesn't update these files automatically.

### Verification
- ✅ Server logs: No "Unknown column 'timestamp'" or "Unknown column 'reason'" errors after fix
- ✅ Recent logs show only HTTP 200 responses, no Fatal errors
- ⏳ Browser verification pending


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Status | Notes |
| --- | --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 2026-01-21 | ✅ DONE | Server logs + schema inspection |
| Fix Development | MyBBBugHunter | 2026-01-21 | ✅ DONE | 6 column references corrected |
| Testing | MyBBBugHunter | 2026-01-21 | ✅ DONE | Server log verification |
| Deployment | MyBBBugHunter | 2026-01-21 | ✅ DONE | Manual file copy |


---
## Appendix
<!-- ID: appendix -->
**Logs & Evidence:**
- Server log errors: `mybb_server_logs(errors_only=True)` showed Fatal SQL errors for timestamp/reason columns
- Database schema: `SHOW COLUMNS FROM mybb_invite_spam_log` confirmed column names
- Recent logs (post-fix): Only HTTP 200 responses, no PHP errors

**Fix References:**
- Workspace file: `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/modules/tools/invite_logs.php`
- Deployed file: `TestForum/admin/modules/tools/invite_logs.php` (manually copied)
- Bug report: `docs/bugs/database/2026-01-21_spam_logs_schema_mismatch/report.md`

**Open Questions:**
- Should plugin _install() automate copying files to admin/modules/tools/?
- Are there other admin module files with similar deployment issues?
- Should this be documented in plugin deployment guide?

**Deployment Recommendations:**
Consider automating the admin/modules/tools/ file deployment in the plugin's `_install()` function:
```php
// Example automation
$source = MYBB_ROOT . 'inc/plugins/invite_system/admin/modules/tools/invite_logs.php';
$dest = MYBB_ROOT . 'admin/modules/tools/invite_logs.php';
copy($source, $dest);
```


---
