
# 🐞 Codes and Campaigns pages missing admin language loading — invite_system_admin_panel
**Author:** Scribe
**Version:** v0.1
**Status:** Investigating
**Last Updated:** 2026-01-21 03:51:54 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** codes_campaigns_lang_loading

**Reported By:** Scribe

**Date Reported:** 2026-01-21 03:51:54 UTC

**Severity:** MEDIUM

**Status:** FIXED (pending deployment)

**Component:** admin/codes.php, admin/campaigns.php

**Environment:** Development (plugin_manager workspace)

**Customer Impact:** Low to Medium - Admin UI shows missing labels/headers, but functionality remains intact. Users can still use the pages, just with reduced clarity.


---
## Description
<!-- ID: description -->
### Summary
The Codes page (action=codes) and Campaign Add page (campaigns_action=add) in the Admin CP are missing language strings, causing column headers and form labels to appear blank or show raw variable names.

### Expected Behaviour
- Codes page should display "Status" as the column header for the status column
- Campaign add page should display proper labels above all form input fields (e.g., "Campaign Name", "Description", "Type", etc.)

### Actual Behaviour
- Codes page: Status column header shows nothing or raw variable name
- Campaign add page: All form input labels are missing, only showing input boxes with no context

### Steps to Reproduce
1. Navigate to Admin CP → User Invitations → Codes
2. Observe the "Status" column header in the "Manage Invite Codes" table
3. Navigate to Admin CP → User Invitations → Campaigns → Add Campaign
4. Observe missing labels above all input boxes in the form


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
Both `admin/codes.php` (line 27) and `admin/campaigns.php` (line 26) only load the frontend language file using `$lang->load('invite_system')`. They do not load the admin language file, which contains the required variables like `invite_code_status`, `invite_campaign_name`, etc.

MyBB admin context automatically prefixes 'admin/' to language file paths, but plugins must explicitly load both frontend and admin files when admin pages use variables from both.

This is the **same root cause** as bugs fixed in QA Round 1 for dashboard.php, applications.php, and tree.php.

**Affected Areas:**
- `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/codes.php` (main function)
- `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/campaigns.php` (main function)
- All language variables defined in `inc/languages/english/admin/invite_system.lang.php` are unavailable

**Related Issues:**
- QA Round 1 bugs: dashboard.php, applications.php, tree.php (same pattern, already fixed)
- Language file locations: Frontend in `inc/languages/english/invite_system.lang.php`, Admin in `inc/languages/english/admin/invite_system.lang.php`


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] **COMPLETED**: Add dual language loading pattern to `admin/codes.php`
  - Changed line 27 from single `$lang->load('invite_system')` to dual load:
    ```php
    $lang->load('invite_system', true);  // Force frontend load
    $lang->load('invite_system');         // Admin context loads admin file
    ```

- [x] **COMPLETED**: Add dual language loading pattern to `admin/campaigns.php`
  - Changed line 26 from single load to dual load (same pattern as above)

### Long-Term Fixes
- [ ] **RECOMMENDED**: Audit all remaining admin files for this pattern
  - Check if any other admin pages only load frontend language file
  - Apply consistent dual-load pattern across all admin modules

### Testing Strategy
- [ ] Browser test: Navigate to Codes page, verify "Status" column header shows "Status"
- [ ] Browser test: Navigate to Campaign Add page, verify all form labels are visible
- [ ] Regression test: Verify existing pages (dashboard, applications, tree) still work correctly
- [ ] Full admin panel walkthrough to catch any remaining language loading issues


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 2026-01-21 03:50 UTC | Root cause identified: missing dual language load |
| Fix Development | MyBBBugHunter | 2026-01-21 03:51 UTC | Applied dual-load pattern to both files |
| Testing | Orchestrator | Pending | Browser verification after deployment |
| Deployment | Orchestrator | Pending | Plugin reinstall required |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:**
  - User report: "Codes page status column missing language, Campaign add form missing labels"
  - Investigation logs in PROGRESS_LOG.md entries at 03:49-03:51 UTC

- **Fix References:**
  - Modified files: `admin/codes.php` (lines 28-30), `admin/campaigns.php` (lines 28-29)
  - Pattern matches previous fixes in QA Round 1
  - Code change: Dual load with force flag for frontend, followed by admin load

- **Open Questions:**
  - Are there other admin files with single language load that need fixing?
  - Should we create a helper function to standardize dual language loading across all admin modules?


---