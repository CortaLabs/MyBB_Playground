
# 🐞 UserCP Invites Page 500 Error - Missing Templates — invite-system
**Author:** MyBB-BugHunter Agent
**Version:** v1.0
**Status:** Fixed (Pending Deployment)
**Last Updated:** 2026-01-19 03:35:00 UTC

> Documents critical bug where UserCP invites page returned 500 error due to missing template definitions in plugin activation function. Templates were referenced by handler code but never created during plugin installation.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** 2026-01-18_usercp_500_template_syntax

**Reported By:** Orchestrator

**Date Reported:** 2026-01-18 (discovered during testing)

**Severity:** CRITICAL

**Status:** FIXED (awaiting redeployment)

**Component:** invite_system plugin - UserCP handlers

**Environment:** Local development (MyBB 1.8.x)

**Customer Impact:** Complete failure of UserCP invites page - users cannot generate, view, or manage invite codes. 500 Internal Server Error on access.


---
## Description
<!-- ID: description -->
### Summary
The UserCP invites page (`usercp.php?action=invites`) returns a PHP Parse error and 500 status code. The error occurs when evaluating the `invite_usercp_pool_status` template, which does not exist in the database.

### Expected Behaviour
- User navigates to `usercp.php?action=invites`
- Page displays invite code generation form with pool statistics
- Templates render correctly showing available invites, forms, and code lists

### Actual Behaviour
- PHP Parse error: `syntax error, unexpected token ".", expecting "->" or "?->" or "{" or "["`
- Error location: `usercp.php(242) : eval()'d code on line 14`
- HTTP 500 Internal Server Error
- Page completely non-functional

### Steps to Reproduce
1. Install invite_system plugin via `mybb_plugin_install(codename='invite_system')`
2. Navigate to `usercp.php?action=invites` as any user
3. Observe 500 error in browser and PHP parse error in error logs


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
UserCP templates (Phase 8) were never created in the `invite_system_activate()` function, despite being referenced by handler code in `handlers/usercp.php`.

**Evidence Trail:**
1. **Error Location:** `/TestForum/inc/plugins/invite_system/handlers/usercp.php:242`
   ```php
   eval('$pool_status = "' . $templates->get('invite_usercp_pool_status') . '";');
   ```

2. **Database Check:** Template `invite_usercp_pool_status` does not exist (query returned empty)

3. **Source Code Analysis:**
   - Examined `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system.php`
   - Found templates listed in `_deactivate()` deletion array (line 666)
   - **NO corresponding template creation code found in `_activate()` function**
   - Other phases (7: Applications, 9: Invite Tree, 10: Campaigns, 14: Profile) had templates properly created
   - Phase 8 (UserCP) templates were completely missing

**Affected Templates (11 total):**
- `invite_usercp_nav` - Navigation menu item
- `invite_usercp_pool_status` - Pool statistics display (caused the error)
- `invite_usercp_generate` - Code generation form
- `invite_usercp_codes` - Codes listing page
- `invite_usercp_code_row` - Individual code row
- `invite_usercp_code_revoke` - Revoke action link
- `invite_usercp_no_codes` - Empty state message
- `invite_usercp` - Main wrapper page
- `invite_usercp_send_email` - Email invite form
- `invite_usercp_email_history` - Email history table
- `invite_usercp_email_history_row` - Email history row

**Why This Happened:**
Implementation gap during Phase 8 development - handler code was written referencing templates, but template creation code was never added to the activation function. The templates existed in the deactivation cleanup list but not in the creation logic.

**Affected Areas:**
- All UserCP invite management functionality
- Invite code generation
- Invite code listing and management
- Email invite sending
- Invite tree visualization


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Identify missing templates by comparing handler references vs. database
- [x] Create all 11 UserCP template definitions in `_activate()` function
- [x] Add template creation code at line 613 (after tree templates, before scheduled task)
- [x] Use proper PHP array syntax `$pool_stats['key']` not invalid dot notation
- [ ] Uninstall existing plugin deployment
- [ ] Reinstall plugin to deploy fixed templates
- [ ] Verify templates exist in database
- [ ] Test UserCP invites page functionality

### Long-Term Fixes
- [ ] Add template validation test to plugin test suite
- [ ] Document template requirements for each phase in ARCHITECTURE_GUIDE.md
- [ ] Create checklist for plugin activation function (templates, settings, hooks, tasks)

### Testing Strategy
- [ ] **Unit Test:** Verify all 11 templates exist after activation
- [ ] **Integration Test:** Navigate to `usercp.php?action=invites` without errors
- [ ] **Functional Test:** Generate invite code, view codes list, revoke code
- [ ] **Regression Test:** Verify other plugin features still work (registration, applications, admin)


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Completed | Notes |
| --- | --- | --- | --- |
| Bug Discovery | Orchestrator | 2026-01-18 22:24 | 500 error reported during testing |
| Investigation | MyBB-BugHunter | 2026-01-19 03:26 | Root cause identified - missing templates |
| Fix Development | MyBB-BugHunter | 2026-01-19 03:33 | Added 268 lines (11 templates) to activation function |
| Testing | Pending | TBD | Requires plugin reinstall |
| Deployment | Pending | TBD | Uninstall + reinstall plugin |


---
## Fix Summary
<!-- ID: fix_summary -->
**File Modified:** `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system.php`

**Location:** Line 613 (inserted new Phase 8: UserCP Templates section)

**Changes:**
- Added 268 lines of code
- Created 11 template definitions using proper MyBB template structure
- Templates use PHP array syntax `{$pool_stats['remaining']}` for proper evaluation
- Each template documented with inline comment describing purpose
- Templates inserted in foreach loop with duplicate-check logic (lines 868-880)

**Templates Added:**
1. **invite_usercp_nav** - Navigation menu item for UserCP sidebar
2. **invite_usercp_pool_status** - Pool statistics display with progress bar
3. **invite_usercp_generate** - Full code generation form with validation
4. **invite_usercp_codes** - Codes listing table wrapper
5. **invite_usercp_code_row** - Individual code row with status info
6. **invite_usercp_code_revoke** - Revoke action link with confirmation
7. **invite_usercp_no_codes** - Empty state with call-to-action
8. **invite_usercp** - Main wrapper with tab navigation
9. **invite_usercp_send_email** - Email invite form
10. **invite_usercp_email_history** - Email history table
11. **invite_usercp_email_history_row** - Email history row

**Deployment Commands:**
```bash
# 1. Uninstall existing deployment (preserves settings/data)
mybb_plugin_uninstall(codename='invite_system', uninstall=False, remove_files=True)

# 2. Reinstall with fixed templates
mybb_plugin_install(codename='invite_system')

# 3. Verify templates created
mybb_read_template(title='invite_usercp_pool_status')
```


---
## Appendix
<!-- ID: appendix -->
**Logs & Evidence:**
- Progress log entries: 10+ entries documenting investigation and fix
- Error message: `PHP Parse error: syntax error, unexpected token "." in usercp.php(242) : eval()'d code on line 14`
- File path: `/home/austin/projects/MyBB_Playground/plugin_manager/plugins/private/invite_system/inc/plugins/invite_system.php`

**Fix References:**
- Workspace fix applied to source files (not TestForum deployment)
- Templates use Cortex template engine syntax for conditionals (`<if>...</if>`)
- Follows MyBB template inheritance model (sid=-2 for master templates)

**Verification Criteria:**
- [ ] All 11 templates exist in `mybb_templates` table with sid=-2
- [ ] `usercp.php?action=invites` returns 200 status code
- [ ] Pool status displays correctly with user's invite statistics
- [ ] Forms submit without errors
- [ ] No PHP errors in error logs

**Confidence Score:** 0.95 (High - root cause confirmed, fix applied to source, deployment pending)


---
