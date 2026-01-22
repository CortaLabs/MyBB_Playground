
# 🐞 Duplicate tree depth settings causing UI inconsistency — invite_system_admin_panel
**Author:** Scribe
**Version:** v0.1
**Status:** Fixed and Verified
**Last Updated:** 2026-01-21 03:12:13 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** duplicate_tree_depth_settings

**Reported By:** Scribe

**Date Reported:** 2026-01-21 03:12:13 UTC

**Severity:** MEDIUM

**Status:** FIXED

**Component:** invite_system

**Environment:** [local/staging/production]

**Customer Impact:** [Describe impact or 'None']


---
## Description
<!-- ID: description -->
### Summary
The invite_system plugin defined duplicate settings for tree depth, causing the "Maximum Tree Depth" setting in ACP to display improperly. One setting used a numeric optionscode (broken), while the other used a select dropdown (correct). Different parts of the code referenced different setting names.

### Expected Behaviour
- Single "Maximum Tree Depth" setting in ACP Configuration > Settings
- Setting displays as dropdown with values 1-10
- All plugin code references the same setting name

### Actual Behaviour
- Two settings existed: `invite_system_tree_max_depth` and `invite_tree_max_depth`
- The numeric optionscode setting didn't render properly
- Code inconsistently referenced both setting names
- ACP showed confusing/broken UI for this setting

### Steps to Reproduce
- [x] Install invite_system plugin (before fix)
- [x] Navigate to ACP > Configuration > Settings > Invite System
- [x] Look for "Maximum Tree Depth" setting
- [x] Observe missing or broken input control
- [x] Query database: `SELECT * FROM mybb_settings WHERE name LIKE '%tree%depth%'`
- [x] Find two duplicate settings


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The plugin's `_install()` function defined TWO settings for tree depth:
1. `invite_system_tree_max_depth` (line 625) - numeric optionscode (broken rendering)
2. `invite_tree_max_depth` (line 1099) - select dropdown optionscode (correct)

Different parts of the code referenced different setting names:
- `admin/settings.php` used `invite_system_tree_max_depth`
- `InviteTree.php` and `usercp.php` used `invite_tree_max_depth`

This inconsistency caused the ACP to show a broken UI element.

**Affected Areas:**
- `inc/plugins/invite_system.php` (setting definitions)
- `inc/plugins/invite_system/admin/settings.php` (setting references)
- MyBB settings table in database
- ACP Configuration > Settings UI

**Related Issues:**
- None identified


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Remove duplicate setting definition `invite_system_tree_max_depth` from line 625
- [x] Update all references in `admin/settings.php` to use `invite_tree_max_depth`
- [x] Uninstall and reinstall plugin to apply database changes
- [x] Verify database contains only one tree depth setting

### Long-Term Fixes
- [x] Add test case to prevent future duplicate settings
- [x] Document proper setting naming conventions in plugin development guide

### Testing Strategy
- [x] Write reproduction test (`tests/bugs/test_2026-01-21_duplicate_tree_depth_settings.py`)
- [x] Verify test fails before fix (confirmed duplicate settings)
- [x] Apply fixes to workspace files
- [x] Verify test passes after fix (single setting, consistent usage)
- [x] Deploy to TestForum via uninstall/reinstall
- [x] Query database to confirm fix in production


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
- **Logs & Evidence:**
  - Scribe Progress Log: `.scribe/docs/dev_plans/invite_system_admin_panel/PROGRESS_LOG.md`
  - Test file: `tests/bugs/test_2026-01-21_duplicate_tree_depth_settings.py`
  - Database query confirmed duplicate before fix, single setting after fix

- **Fix References:**
  - File 1: `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system.php` (removed lines 624-632)
  - File 2: `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/settings.php` (lines 400, 401, 481, 704 updated)

- **Test Results:**
  ```
  Before Fix:
    Test 1 (No duplicates): FAIL - 2 settings found
    Test 2 (Correct optionscode): PASS
    Test 3 (Consistent usage): FAIL - inconsistent references

  After Fix:
    Test 1 (No duplicates): PASS ✅
    Test 2 (Correct optionscode): PASS ✅
    Test 3 (Consistent usage): PASS ✅
  ```

- **Database Verification:**
  ```sql
  -- After fix, only one setting exists:
  SELECT name, title, optionscode FROM mybb_settings WHERE name LIKE '%tree%depth%';
  -- Result: invite_tree_max_depth with select dropdown (1-10)
  ```

- **Open Questions:** None - fix complete and verified


---