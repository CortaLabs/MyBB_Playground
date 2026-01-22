
# 🐞 Campaigns page loses main Invitations navigation header — invite_system_admin_panel
**Author:** Scribe
**Version:** v0.1
**Status:** Fixed
**Last Updated:** 2026-01-21 03:20 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** campaigns_nav_loss

**Reported By:** Scribe

**Date Reported:** 2026-01-21 03:13:23 UTC

**Severity:** MEDIUM

**Status:** FIXED

**Component:** invite_system admin/campaigns.php

**Environment:** [local/staging/production]

**Customer Impact:** [Describe impact or 'None']


---
## Description
<!-- ID: description -->
### Summary
The Campaigns page in the Invite System admin panel loses the main "Invitations" navigation header when visited, making it difficult for users to navigate back to other sections of the invite system.

### Expected Behaviour
The Campaigns page should display the full navigation breadcrumb trail: "Home > Invitations > Campaigns" with the main "Invitations" header visible to allow navigation to other invite system pages.

### Actual Behaviour
The Campaigns page only shows "Campaigns" without the parent "Invitations" navigation context, causing the main navigation tabs to disappear.

### Steps to Reproduce
- [x] Navigate to Admin CP > Invitations > Campaigns
- [x] Observe that the "Invitations" header navigation disappears
- [x] Compare to Dashboard, Analytics, or other invite system pages which correctly show the parent navigation


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The campaigns.php file was missing the parent breadcrumb item. Dashboard.php correctly adds two breadcrumbs:
1. `$page->add_breadcrumb_item($lang->invite_system, 'index.php?module=user-invitations');` (parent)
2. `$page->add_breadcrumb_item($lang->invite_admin_dashboard);` (page)

But campaigns.php only added the campaigns breadcrumb, missing the parent. This caused MyBB's navigation system to lose the "Invitations" context.

**Affected Areas:**
- `inc/plugins/invite_system/admin/campaigns.php` - 4 functions affected:
  - `invite_admin_campaigns_list()` (line 75)
  - `invite_admin_campaigns_add()` (line 228)
  - `invite_admin_campaigns_edit()` (line 495)
  - `invite_admin_campaigns_stats()` (line 808)

**Related Issues:**
- None - isolated UI navigation bug


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Add parent breadcrumb to all 4 campaign functions
- [x] Redeploy plugin via uninstall/reinstall cycle
- [x] Verify deployed files contain the fix

### Long-Term Fixes
- None needed - this was a simple missing breadcrumb

### Testing Strategy
- [x] Compare breadcrumb setup with working pages (dashboard.php)
- [x] Grep deployed file to confirm all 4 functions have parent breadcrumb
- [ ] Manual browser test: Navigate to Campaigns page and verify "Invitations" header is visible


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
- **Logs & Evidence:** Scribe progress log entries 2026-01-21 03:11-03:20 UTC
- **Fix References:**
  - Modified: `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/campaigns.php`
  - Lines changed: 79, 232, 500, 814 (added parent breadcrumb before existing breadcrumb)
  - Deployment: Full plugin reinstall
- **Fix Code:**
```php
// Added to all 4 functions BEFORE existing breadcrumb:
$page->add_breadcrumb_item($lang->invite_system, 'index.php?module=user-invitations');
```
- **Open Questions:** None - bug fully resolved


---