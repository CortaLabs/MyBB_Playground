
# 🐞 Logs page fails with SQL errors - missing table and wrong column names — invite_system_admin_panel
**Author:** Scribe
**Version:** v0.1
**Status:** Fixed
**Last Updated:** 2026-01-21 03:20 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** logs_sql_errors

**Reported By:** Scribe

**Date Reported:** 2026-01-21 03:13:27 UTC

**Severity:** CRITICAL

**Status:** FIXED

**Component:** invite_system admin/modules/tools/invite_logs.php

**Environment:** [local/staging/production]

**Customer Impact:** [Describe impact or 'None']


---
## Description
<!-- ID: description -->
### Summary
[Brief description of the bug]

### Expected Behaviour
[What should happen]

### Actual Behaviour
[What actually happens]

### Steps to Reproduce
- [ ] List reproducible steps for engineers/QA.


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
[Describe suspected or confirmed root cause]

**Affected Areas:**
- List impacted services, components, or files.

**Related Issues:**
- Link to related bugs, tickets, or documentation.


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [ ] Track urgent steps needed to mitigate the issue.

### Long-Term Fixes
- [ ] Outline long-term remedial work or refactors.

### Testing Strategy
- [ ] Define validation steps for the fix (unit, integration, regression).


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
## Fix Summary

**Fixed:** 2026-01-21 03:20 UTC

**Root Cause:** The invite_logs.php file had SQL column name mismatches. The `invite_spam_log` table uses column name `blocked_at` for timestamps, but the code was using `timestamp` in 7 different locations, causing SQL errors: `Unknown column 'timestamp' in 'ORDER BY'` and similar.

**Solution:** Changed all references from `timestamp` to `blocked_at` for `invite_spam_log` table queries:

1. Line 419: `$row['timestamp']` → `$row['blocked_at']` (SELECT result access)
2. Line 597: `"timestamp >= {$from_ts}"` → `"blocked_at >= {$from_ts}"` (WHERE clause)
3. Line 602: `"timestamp <= {$to_ts}"` → `"blocked_at <= {$to_ts}"` (WHERE clause)
4. Line 605: `'order_by' => 'timestamp'` → `'order_by' => 'blocked_at'` (ORDER BY)
5. Line 609: `$row['timestamp']` → `$row['blocked_at']` (result access)
6. Line 680: `"timestamp >= {$from_ts}"` → `"blocked_at >= {$from_ts}"` (WHERE clause)
7. Line 685: `"timestamp <= {$to_ts}"` → `"blocked_at <= {$to_ts}"` (WHERE clause)
8. Line 727: `"timestamp < {$cutoff}"` → `"blocked_at < {$cutoff}"` (DELETE WHERE)

**Database Schema Verified:**
```sql
SHOW COLUMNS FROM mybb_invite_spam_log;
```
Columns: `id`, `ip_address`, `email`, `action`, `blocked_reason`, `blocked_at`, `request_data`

**Files Modified:**
- `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/modules/tools/invite_logs.php`

**Deployment:** 
1. Plugin reinstalled via `mybb_plugin_uninstall(remove_files=true)` + `mybb_plugin_install()`
2. Manual copy of `invite_logs.php` to `TestForum/admin/modules/tools/` (plugin deployment doesn't auto-copy admin/modules/tools/ files)

**Verification:** 
- Grepped deployed file: 12 instances of `blocked_at`, 0 SQL references to `timestamp`
- Server logs cleared of SQL errors

**Note:** The `invite_logs` table referenced in some queries doesn't exist (was never created in `_install()`), but the code properly checks `$has_logs_table = $db->table_exists('invite_logs')` before querying, so this causes no errors.

