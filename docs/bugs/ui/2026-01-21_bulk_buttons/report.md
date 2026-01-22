
# 🐞 Bulk operations page buttons render as highlighted text instead of proper MyBB ACP buttons — invite_system_admin_panel
**Author:** Scribe
**Version:** v0.1
**Status:** Investigating
**Last Updated:** 2026-01-21 03:49:38 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** bulk_buttons

**Reported By:** Scribe

**Date Reported:** 2026-01-21 03:49:38 UTC

**Severity:** MEDIUM

**Status:** DIAGNOSED - Ready for Fix

**Component:** invite_system_admin_bulk

**Environment:** [local/staging/production]

**Customer Impact:** [Describe impact or 'None']


---
## Description
<!-- ID: description -->
### Summary
In the Admin CP invitations bulk operations page (`index.php?module=user-invitations&action=bulk`), the three operation buttons (Generate Codes, Revoke Expired, Cleanup) appear as highlighted text instead of proper MyBB ACP-styled buttons.

### Expected Behaviour
Buttons should render with full MyBB ACP styling using the Form class methods. They should appear as proper clickable buttons with standard MyBB admin panel styling (similar to form submit buttons on the bulk generate page).

### Actual Behaviour
Raw HTML anchor tags and button elements with `class="button"` render without proper MyBB button styling. They appear as highlighted text with inline styles instead of proper button appearance.

### Steps to Reproduce
1. Navigate to Admin CP → Users & Groups → Invitations → Bulk Operations
2. Observe the three operation cards: Generate Codes, Revoke Expired, Cleanup
3. Notice buttons render as text with background color instead of proper ACP button styling


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The `invite_admin_bulk_main()` function in `bulk.php` uses raw HTML to generate action buttons instead of MyBB's Form class methods.

**Problematic Code Pattern:**
```php
// Lines 99, 108, 112, 120 - WRONG PATTERN
echo '<a href="..." class="button" style="...">Generate Codes</a>';
echo '<button class="button" disabled style="...">No Expired Codes</button>';
```

**Correct Pattern (used in same file at lines 315-318):**
```php
$form->output_submit_wrapper(array(
    $form->generate_submit_button($lang->invite_bulk_generate),
    $form->generate_reset_button($lang->invite_cancel)
));
```

**Why It Fails:**
- Raw HTML with `class="button"` gets basic CSS styling but lacks MyBB's full button wrapper structure
- MyBB Form class methods apply proper admin panel styling classes and wrapper divs
- Inline styles override the intended button appearance

**Affected Areas:**
- `plugin_manager/plugins/private/invite_system/inc/plugins/invite_system/admin/bulk.php`
  - Line 99: Generate Codes button
  - Line 108: Revoke Expired button
  - Line 112: No Expired Codes button (disabled state)
  - Line 120: Cleanup button

**Related Issues:**
- None identified. This is an isolated styling issue in the bulk operations main page.
- Other admin pages (dashboard, codes, campaigns, etc.) do not have this issue as they either use forms properly or don't have standalone buttons.


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] **Identified root cause:** Raw HTML buttons instead of MyBB Form class
- [ ] **Replace raw HTML buttons** with proper MyBB button rendering:
  - Option 1: Create a mini-form for each button (proper MyBB pattern)
  - Option 2: Use `<input type="button" class="button" onclick="location.href='...'">`
  - Option 3: Keep links but remove inline styles, rely on MyBB's `.button` CSS class only
- [ ] **Test fix** in browser to verify buttons render properly

### Long-Term Fixes
- [ ] **Code review:** Check all admin pages for similar patterns
- [ ] **Documentation:** Add to wiki/best practices guide - "How to create buttons in MyBB admin pages"

### Testing Strategy
- [ ] **Visual verification:** Navigate to bulk operations page in ACP, verify buttons appear as proper MyBB buttons
- [ ] **Functional test:** Click each button to ensure they still work correctly
- [ ] **Regression test:** Verify bulk generate form still works (it already uses correct pattern)


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
  - Bug discovered during QA testing (user report: "buttons are just highlighted text instead of proper MyBB ACP buttons")

- **Fix References:**
  - Working example in same file: `bulk.php` lines 315-318 (bulk generate form)
  - MyBB Form class documentation: Official MyBB plugin development docs

- **Technical Details:**
  - **MyBB Button Requirements (from Form class inspection):**
    - CSS class: `submit_button` (NOT `button`)
    - Wrapper div: `<div class="form_button_wrapper">`
    - MyBB core: ALL admin buttons use `$form->generate_submit_button()` + `$form->output_submit_wrapper()`

  - **Recommended Fix:**
    Since these are action links (not form submissions), create a small form wrapper for each button:
    ```php
    // For each action button
    $form = new Form("index.php?module=user-invitations&action=bulk&bulk_action=generate", "post");
    $form->output_submit_wrapper(array(
        $form->generate_submit_button($lang->invite_bulk_generate, array('onclick' => "location.href='...'; return false;"))
    ));
    $form->end();
    ```

    Or use a helper pattern that wraps the link in proper MyBB button structure without a real form.


---