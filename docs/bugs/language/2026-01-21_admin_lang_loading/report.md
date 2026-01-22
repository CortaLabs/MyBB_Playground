
# 🐞 Admin pages loading wrong language files causing UI corruption — invite_system_admin_panel
**Author:** Scribe
**Version:** v0.1
**Status:** Investigating
**Last Updated:** 2026-01-21 03:12:58 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** admin_lang_loading

**Reported By:** Scribe

**Date Reported:** 2026-01-21 03:12:58 UTC

**Severity:** HIGH

**Status:** INVESTIGATING

**Component:** invite_system_admin_panel

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
## Resolution Summary

**Status:** ✅ FIXED AND VERIFIED

**Root Causes Identified:**

1. **Wrong sprintf placeholder format**: Admin language file used PHP sprintf format (`%s`, `%d`) but MyBB's `$lang->sprintf()` expects `{1}`, `{2}`, `{3}` format.

2. **Missing language file**: Admin pages need BOTH frontend and admin language files loaded. Original code only loaded admin language file, missing variables defined in frontend file.

3. **Incorrect language loading**: One page (tree.php) had duplicate `admin/` prefix causing "admin/admin/invite_system" double-nesting error.

**Files Modified:**

1. `inc/languages/english/admin/invite_system.lang.php`
   - Converted 13 language strings from `%s`/`%d` to `{1}`/`{2}`/`{3}` format
   - Lines affected: 414-416, 462-463, 485, 550, 592, 600, 632-634, 683

2. `inc/plugins/invite_system/admin/dashboard.php`
   - Added dual language loading: frontend first, then admin
   - Line 24-25: `$lang->load('invite_system', true);` then `$lang->load('invite_system');`

3. `inc/plugins/invite_system/admin/applications.php`
   - Added dual language loading: frontend first, then admin
   - Line 23-24: `$lang->load('invite_system', true);` then `$lang->load('invite_system');`

4. `inc/plugins/invite_system/admin/tree.php`
   - Added dual language loading: frontend first, then admin
   - Removed duplicate `admin/` prefix line
   - Line 27-28: `$lang->load('invite_system', true);` then `$lang->load('invite_system');`

**How the Fix Works:**

1. **MyBB sprintf format**: MyBB's `$lang->sprintf()` uses `str_replace('{N}', $arg, $string)` instead of PHP's `vsprintf()`. Placeholders must be `{1}`, `{2}`, `{3}` not `%s`, `%d`.

2. **Dual language loading pattern**:
   - First load: `$lang->load('invite_system', true)` - Force flag loads frontend language file
   - Second load: `$lang->load('invite_system')` - Admin context automatically adds 'admin/' prefix
   - Result: Both frontend and admin language variables available in admin pages

**Verification Results:**

✅ **Dashboard** - Shows "No recent activity" instead of "code %s created by %s"
✅ **Applications** - All form labels visible: Status dropdown, Email Verified, Search, Filter button
✅ **Invite Tree** - Loads successfully, no "admin/admin" path error

**Screenshot Evidence:**
- `dashboard_fixed.png` - Dashboard showing correct language strings

**Deployment:**
Plugin redeployed via `mybb_plugin_uninstall(remove_files=true)` → `mybb_plugin_install()`

**Confidence:** 100% - All three reported issues verified fixed in browser testing.
