
# 🐞 Campaigns page missing main module navigation tabs — invite_system_admin_panel
**Author:** Scribe
**Version:** v0.1
**Status:** FIXED
**Last Updated:** 2026-01-21 03:51:00 UTC

> Documents the fix for campaigns page showing local mini-navigation instead of main module navigation tabs.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** campaigns_missing_nav_tabs

**Reported By:** Scribe

**Date Reported:** 2026-01-21 03:51:36 UTC

**Severity:** HIGH

**Status:** FIXED

**Component:** invite_system admin/campaigns.php

**Environment:** Development (workspace)

**Customer Impact:** High - Users cannot navigate between admin sections from campaigns page


---
## Description
<!-- ID: description -->
### Summary
Campaigns admin page displays only local "List | Add" navigation tabs instead of the main module navigation tabs (Dashboard | Invitations | Users | Groups | Settings | Campaigns).

### Expected Behaviour
All admin pages should show the same main module navigation: Dashboard | Invitations | Users | Groups | Settings | Campaigns, with the current page highlighted.

### Actual Behaviour
Campaigns page shows only "List | Add" tabs, preventing navigation to other admin sections.

### Steps to Reproduce
1. Navigate to Admin CP → Invitations → Campaigns
2. Observe navigation tabs at top of page
3. See only "List | Add" instead of full module navigation


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**

All 4 view functions in campaigns.php implemented LOCAL navigation tabs instead of calling the module-wide navigation system.

**Affected Functions:**
1. `invite_admin_campaigns_list()` - Lines 85-98: Local sub_tabs array with 'list' and 'add'
2. `invite_admin_campaigns_add()` - Lines 239-252: Local sub_tabs array with 'list' and 'add'
3. `invite_admin_campaigns_edit()` - Lines 507-518: Local sub_tabs array with 'list' and 'edit'
4. `invite_admin_campaigns_stats()` - Lines 820-831: Local sub_tabs array with 'list' and 'stats'

**Missing Code:**
- No `require_once MYBB_ROOT . 'inc/plugins/invite_system/admin/module_meta.php';` in main function
- No calls to `invite_system_build_nav_tabs('campaigns')` in view functions

**Code Pattern Error:**
```php
// WRONG - creates local mini-navigation
$sub_tabs = array(
    'list' => array('title' => $lang->invite_campaigns_list, ...),
    'add' => array('title' => $lang->invite_campaigns_add, ...)
);
$page->output_nav_tabs($sub_tabs, 'list');

// CORRECT - uses main module navigation
$tabs = invite_system_build_nav_tabs('campaigns');
$page->output_nav_tabs($tabs, 'campaigns');
```

**Related Issues:**
- Same pattern was used in other admin pages initially, but was corrected during development
- Dashboard, tree, applications, and other pages use correct navigation pattern


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Add `require_once MYBB_ROOT . 'inc/plugins/invite_system/admin/module_meta.php';` to main campaigns function
- [x] Replace local sub_tabs arrays in all 4 view functions with `invite_system_build_nav_tabs('campaigns')` call
- [x] Remove all local sub_tabs definitions (56 lines removed, 4 lines added)

### Fix Implementation
**File Modified:** `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/campaigns.php`

**Changes Made:**
1. Line 30: Added module_meta.php require in `invite_admin_campaigns()`
2. Lines 88-89: Replaced sub_tabs in `invite_admin_campaigns_list()`
3. Lines 230-231: Replaced sub_tabs in `invite_admin_campaigns_add()`
4. Lines 486-487: Replaced sub_tabs in `invite_admin_campaigns_edit()`
5. Lines 790-791: Replaced sub_tabs in `invite_admin_campaigns_stats()`

**Code Changes:**
```php
// Added to main function (line 30)
require_once MYBB_ROOT . 'inc/plugins/invite_system/admin/module_meta.php';

// Replaced in each view function (4 locations)
$tabs = invite_system_build_nav_tabs('campaigns');
$page->output_nav_tabs($tabs, 'campaigns');
```

### Testing Strategy
- [x] Verify all navigation calls present with grep
- [x] Verify no local sub_tabs remain with grep
- [ ] Deploy to TestForum via `mybb_plugin_install('invite_system')`
- [ ] Test campaigns list page shows main navigation
- [ ] Test campaigns add page shows main navigation
- [ ] Test campaigns edit page shows main navigation
- [ ] Test campaigns stats page shows main navigation
- [ ] Verify 'Campaigns' tab is highlighted on all pages
- [ ] Verify all 6 tabs are clickable and navigate correctly


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Completed | Notes |
| --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 2026-01-21 03:50 UTC | Root cause identified in 4 view functions |
| Fix Development | MyBBBugHunter | 2026-01-21 03:51 UTC | 5 edits applied to campaigns.php |
| Code Verification | MyBBBugHunter | 2026-01-21 03:51 UTC | Grep verification confirms all fixes present |
| Deployment | Orchestrator | Pending | Awaiting orchestrator deployment |
| Browser Testing | Orchestrator/QA | Pending | Test all 4 campaign views in browser |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:**
  - Scribe progress log entries documenting investigation and fix
  - Grep verification output confirming all fixes applied

- **Fix References:**
  - File: `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/campaigns.php`
  - Lines modified: 30, 88-89, 230-231, 486-487, 790-791
  - Net change: -56 lines (removed local navigation), +5 lines (added module navigation)

- **Prevention:**
  - All admin pages should use `invite_system_build_nav_tabs()` for consistent navigation
  - Code review should check for local sub_tabs definitions that duplicate main navigation
  - Template: Always require module_meta.php and call build_nav_tabs() in admin pages


---