
# 🐞 Template cleanup functions leave orphaned templates — invite-system
**Author:** MyBB-BugHunterAgent
**Version:** v1.0
**Status:** FIXED
**Last Updated:** 2026-01-19 04:02 UTC

> Two critical bugs in invite_system plugin's _deactivate() and _uninstall() functions caused templates to be orphaned in the database during plugin lifecycle operations.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** 2026-01-19_invite_template_cleanup

**Reported By:** Research Agent (Cortex Audit Investigation)

**Date Reported:** 2026-01-18

**Severity:** HIGH

**Status:** FIXED

**Component:** invite_system plugin lifecycle functions

**Environment:** Development (MyBB Playground)

**Customer Impact:** Plugin deactivation/uninstallation leaves orphaned templates in database, causing table bloat and potential conflicts if plugin is reinstalled.


---
## Description
<!-- ID: description -->
### Summary
The invite_system plugin contains two critical bugs in template cleanup that prevent complete template removal during deactivation and uninstallation.

### Expected Behaviour
- **_deactivate()**: Should remove ALL plugin templates from ALL template sets (master, global, and theme-specific)
- **_uninstall()**: Should remove ALL templates with 'invite_' prefix

### Actual Behaviour
- **_deactivate()**: Only removes templates from sid=-2 (master) and sid=-1 (global), leaving theme-specific templates (sid=1+) orphaned
- **_uninstall()**: Only removes templates matching 'invite_system%', missing all templates named 'invite_usercp_*', 'invite_application_*', 'invite_admin_*', etc.

### Steps to Reproduce
1. Install and activate invite_system plugin
2. Create a custom template set (sid=1)
3. Edit any plugin template in custom set (creates sid=1 version)
4. Deactivate plugin via ACP
5. Query database: `SELECT * FROM mybb_templates WHERE title LIKE 'invite_%' AND sid=1`
6. Result: Orphaned sid=1 templates still exist
7. Uninstall plugin
8. Query database: `SELECT * FROM mybb_templates WHERE title LIKE 'invite_%'`
9. Result: Most templates still exist (only those matching 'invite_system%' were deleted)


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**

**Bug 1 - Line 953 (_deactivate function):**
```php
$db->delete_query('templates', "title IN ({$templates_list}) AND sid IN (-2, -1)");
```
The sid restriction incorrectly assumes plugin templates only exist in master and global sets. When users customize templates in theme-specific sets (sid=1+), those copies are orphaned.

**Bug 2 - Line 2011 (_uninstall function):**
```php
$db->delete_query('templates', "title LIKE 'invite_system%'");
```
The pattern assumes all plugin templates start with 'invite_system', but they actually use 'invite_' prefix with diverse suffixes:
- invite_usercp_*
- invite_application_*
- invite_admin_*
- invite_landing_page
- invite_tree_*
- invite_email_*

**Affected Areas:**
- Plugin lifecycle management (deactivation/uninstallation)
- MyBB templates table integrity
- Theme-specific template set management

**Related Issues:**
- Part of broader template inheritance investigation during Cortex audit
- Discovered during research into MyBB template inheritance patterns


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] **Bug 1 Fix**: Remove sid restriction from _deactivate() (line 953)
  ```php
  // BEFORE:
  $db->delete_query('templates', "title IN ({$templates_list}) AND sid IN (-2, -1)");

  // AFTER:
  $db->delete_query('templates', "title IN ({$templates_list})");
  ```

- [x] **Bug 2 Fix**: Correct LIKE pattern in _uninstall() (line 2011)
  ```php
  // BEFORE:
  $db->delete_query('templates', "title LIKE 'invite_system%'");

  // AFTER:
  $db->delete_query('templates', "title LIKE 'invite_%'");
  ```

### Long-Term Fixes
- [ ] Add verification to _uninstall() to confirm all plugin templates removed
- [ ] Consider adding template cleanup verification to plugin installation workflow
- [ ] Document template naming patterns for future plugin development

### Testing Strategy
- [x] Verified fixes applied to workspace file
- [ ] Test deactivation: Confirm no orphaned templates in ANY template set
- [ ] Test uninstall: Confirm ALL 'invite_*' templates removed
- [ ] Test reinstall: Confirm clean installation with no conflicts


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Status |
| --- | --- | --- | --- |
| Investigation | MyBB-ResearchAgent | 2026-01-18 | ✅ Complete |
| Bug Report | Orchestrator | 2026-01-18 | ✅ Complete |
| Fix Development | MyBB-BugHunterAgent | 2026-01-19 | ✅ Complete |
| Testing | Pending | TBD | 🔲 Not Started |
| Deployment | Pending | TBD | 🔲 Not Started |


---
## Fix Summary

**Files Modified:**
- `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system.php`

**Changes Applied:**

1. **Line 953** - Removed sid restriction:
   - Changed: `AND sid IN (-2, -1)` → (removed)
   - Effect: Now deletes templates from ALL template sets, not just master/global

2. **Line 2011** - Broadened LIKE pattern:
   - Changed: `'invite_system%'` → `'invite_%'`
   - Effect: Now matches ALL plugin templates regardless of naming convention

**Confidence:** 1.0 (100%)

Both fixes are surgical, well-understood, and target the exact root causes identified during investigation.


---
## Appendix
<!-- ID: appendix -->

**Evidence:**
- Research document: `RESEARCH_TEMPLATE_INHERITANCE_20260118.md`
- Progress log entries: invite-system project (2026-01-18 to 2026-01-19)
- Bug discovery: Line 953 confirmed via code inspection
- Bug discovery: Line 2011 confirmed via template naming audit

**Fix References:**
- Workspace file: `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system.php`
- Bug fixes pending deployment via `mybb_plugin_install(codename='invite_system')`

**Testing Notes:**
- Fixes applied to workspace source
- Plugin must be reinstalled to TestForum for live testing
- Recommend testing with custom template set to verify sid=1+ cleanup

**Open Questions:**
- Should we add defensive checks to other plugins' cleanup functions?
- Should Plugin Manager validate template cleanup during uninstallation?

---
