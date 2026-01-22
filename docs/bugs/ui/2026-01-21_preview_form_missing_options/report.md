
# 🐞 Form Builder preview missing radio/checkbox/dropdown options — invite_system_admin_panel
**Author:** MyBBBugHunter
**Version:** v1.0
**Status:** FIXED
**Last Updated:** 2026-01-21 06:50:00 UTC

> Bug report documenting missing radio button, checkbox, and dropdown options in Form Builder preview function. Root cause was variable name mismatch between CustomFields class and preview rendering logic.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** preview_form_missing_options

**Reported By:** User (QA testing)

**Date Reported:** 2026-01-21

**Severity:** HIGH

**Status:** FIXED

**Component:** form_builder

**Environment:** Local development / TestForum

**Customer Impact:** Admin cannot preview complete application form before deployment. Radio buttons, checkboxes, and dropdown options invisible in preview, preventing verification of field configurations.


---
## Description
<!-- ID: description -->
### Summary
Form Builder preview page fails to display options for radio buttons, checkboxes, and dropdown (select) fields. Field labels and descriptions render correctly, but the actual input elements with their option lists are missing or empty.

### Expected Behaviour
When clicking "Preview Form" button in Form Builder:
- Radio button fields should display all configured options (e.g., "Very active", "Moderately active", etc.)
- Checkbox fields should display all configured options with checkboxes
- Dropdown fields should display all configured options in the select element
- All options should be disabled (read-only) for preview mode

### Actual Behaviour
When clicking "Preview Form" button:
- Radio button fields show only the field label and description, no radio options render
- Checkbox fields show only the field label and description, no checkboxes render
- Dropdown fields show only "-- Select an Option --" placeholder, no actual options render
- Text input and textarea fields work correctly

### Steps to Reproduce
1. Navigate to Admin CP → Users & Groups → Invitations → Form Builder
2. Ensure at least one radio, checkbox, and dropdown field is enabled
3. Click "Preview Form" button
4. Observe that radio/checkbox/dropdown options are missing
5. Check browser console and server logs - no PHP/JS errors

**Affected Fields in Test Data:**
- "Expected Participation Level" (radio) - 4 options missing
- "Primary Interests" (checkbox) - 7 options missing
- "Community Rules and Guidelines" (checkbox) - 3 options missing
- "How did you find this community?" (dropdown) - 7 options missing


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**

Variable name mismatch between `CustomFields::getFields()` method and preview rendering logic in `invite_system_admin_field_preview()` function.

**Technical Details:**
1. **CustomFields.php (line 66):** The `getFields()` method decodes JSON field options and stores them in `$field['field_options']`
   ```php
   $field['field_options'] = json_decode($field['field_options'], true);
   ```

2. **fields.php (lines 782, 793, 805):** The preview function checks for `$field['field_options_array']` which never exists
   ```php
   if(!empty($field['field_options_array']))  // BUG: Wrong key name
   ```

3. **Result:** The `!empty()` check always fails, foreach loops never execute, no options render

**Affected Areas:**
- File: `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/fields.php`
- Function: `invite_system_admin_field_preview()` (lines 707-841)
- Affected lines: 782 (select), 793 (checkbox), 805 (radio)
- Impact: All three field types that use options arrays

**Related Issues:**
- None identified. Isolated bug in preview function only.


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Changed `field_options_array` to `field_options` in line 782 (select case)
- [x] Changed `field_options_array` to `field_options` in line 793 (checkbox case)
- [x] Changed `field_options_array` to `field_options` in line 805 (radio case)
- [x] Redeployed plugin via `mybb_plugin_install(codename='invite_system')`
- [x] Verified fix in browser - all field types now render correctly

### Long-Term Fixes
- Consider standardizing variable naming conventions across CustomFields class
- Add unit tests for preview rendering function
- Document field data structure in CustomFields class comments

### Testing Strategy
- [x] **Browser Testing:** Navigated to Form Builder preview, verified all field types render
- [x] **Field Type Coverage:** Tested radio (4 options), checkbox (7+3 options), dropdown (7 options)
- [x] **Visual Verification:** Screenshots confirm proper rendering of all input elements
- [x] **Regression Check:** Verified text input and textarea fields still work correctly
- [x] **Error Monitoring:** No PHP errors in server logs, no JS errors in console


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Date | Notes |
| --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 2026-01-21 06:44 | Located preview function, inspected code |
| Root Cause | MyBBBugHunter | 2026-01-21 06:48 | Identified variable name mismatch |
| Fix Development | MyBBBugHunter | 2026-01-21 06:48 | Applied 3-line surgical fix |
| Testing | MyBBBBugHunter | 2026-01-21 06:49 | Browser verification complete |
| Documentation | MyBBBugHunter | 2026-01-21 06:50 | Bug report created |


---
## Fix Summary
<!-- ID: fix_summary -->
**Files Modified:** 1 file
- `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/fields.php`

**Changes Applied:**
```diff
Line 782 (select dropdown):
- if(!empty($field['field_options_array']))
+ if(!empty($field['field_options']))

Line 793 (checkboxes):
- if(!empty($field['field_options_array']))
+ if(!empty($field['field_options']))

Line 805 (radio buttons):
- if(!empty($field['field_options_array']))
+ if(!empty($field['field_options']))
```

**Deployment:**
- Plugin uninstalled and reinstalled to deploy fix
- 64 files deployed from workspace to TestForum
- No database changes required
- No cache clearing required

**Verification Results:**
✅ Dropdown field "How did you find this community?" shows 7 options
✅ Radio field "Expected Participation Level" shows 4 options
✅ Checkbox field "Primary Interests" shows 7 options
✅ Checkbox field "Community Rules" shows 3 options
✅ Text input and textarea fields continue working
✅ No PHP errors in server logs
✅ No JavaScript errors in console


---
## Appendix
<!-- ID: appendix -->
**Logs & Evidence:**
- Browser snapshots showing before/after state (radio/checkbox/dropdown options now visible)
- Server logs clean - no PHP errors during preview rendering
- Scribe progress log: 11+ entries tracking investigation and fix

**Fix References:**
- Workspace file modified: `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/fields.php`
- Deployed via: `mybb_plugin_install(codename='invite_system')`
- Testing confirmed: Browser verification at http://localhost:8022/admin/ Form Builder Preview

**Code References:**
- CustomFields class: `inc/plugins/invite_system/core/CustomFields.php` line 66
- Preview function: `inc/plugins/invite_system/admin/fields.php` lines 707-841
- Field rendering switch: lines 770-815

**Prevention Recommendations:**
1. Add type hints to CustomFields methods documenting return array structure
2. Use consistent variable naming conventions (field_options vs field_options_array)
3. Add unit tests for CustomFields::getFields() return structure
4. Add integration test for preview rendering with sample field data

**Open Questions:** None - fix complete and verified.


---
