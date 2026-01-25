
# 🐞 theme:update_stylesheet_list wipes templateset property — theme-management-system
**Author:** MyBBBugHunter
**Version:** v1.0
**Status:** Fixed
**Last Updated:** 2026-01-25 07:28 UTC

> Bug fix for theme:update_stylesheet_list MCP bridge action that was wiping the templateset property when updating stylesheet lists after theme installation.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** 2026-01-25_theme_stylesheet_list_templateset_wipe

**Reported By:** MyBBResearchAnalyst (investigation), MyBBBugHunter (fix)

**Date Reported:** 2026-01-25 07:04 UTC

**Severity:** HIGH

**Status:** FIXED

**Component:** TestForum/mcp_bridge.php (theme:update_stylesheet_list action)

**Environment:** Local development (TestForum)

**Customer Impact:** Themes installed via mybb_theme_install() would have null templateset, breaking template inheritance


---
## Description
<!-- ID: description -->
### Summary
When themes are installed via `mybb_theme_install()`, the templateset property gets wiped out (set to NULL) after the theme is created. This happens because the `theme:update_stylesheet_list` bridge action calls `get_theme()` which only fetches 4 columns (tid, name, pid, allowedgroups), missing the critical `properties` and `stylesheets` columns. When `update_theme_stylesheet_list()` rebuilds the properties array, it has no existing properties to preserve, resulting in the templateset being lost.

### Expected Behaviour
- Themes created with a specific templateset should retain that templateset value
- The `theme:update_stylesheet_list` action should preserve all existing theme properties
- Theme properties should not be wiped out when updating stylesheet lists

### Actual Behaviour
- After theme installation, `mybb_theme_get(name="Flavor")` shows `Templateset: N/A`
- The theme's `properties` field in the database has templateset set to null
- This breaks template inheritance for the theme

### Steps to Reproduce
1. Create and install a theme: `mybb_theme_install(codename='flavor')`
2. Check theme templateset: `mybb_theme_get(name="Flavor")`
3. Observe templateset shows "N/A" instead of expected value (e.g., 12)


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**

**File 1: `TestForum/mcp_bridge.php` (line 1056)**
```php
// Get the theme to pass to update_theme_stylesheet_list
$theme = get_theme($tid);
```
The bridge action uses `get_theme()` which comes from MyBB core.

**File 2: `TestForum/inc/functions.php` (line 5697)**
```php
$query = $db->simple_select('themes', 'tid, name, pid, allowedgroups', "pid!='0'");
```
The `get_theme()` function only selects 4 columns, **missing `properties` and `stylesheets`**.

**File 3: `TestForum/mcp_bridge.php` (line 1063)**
```php
update_theme_stylesheet_list($tid, $theme, true);
```
When `update_theme_stylesheet_list()` receives an incomplete `$theme` object (missing properties), it rebuilds the properties array from scratch, **wiping out the templateset** that was set during theme creation.

**Call Chain:**
1. `mybb_theme_install()` → creates theme with templateset via `theme:create` action
2. Installer calls `theme:update_stylesheet_list` to build stylesheet arrays
3. Bridge action fetches theme using incomplete `get_theme()`
4. MyBB's `update_theme_stylesheet_list()` rebuilds properties without templateset
5. Templateset is lost

**Affected Areas:**
- `TestForum/mcp_bridge.php` - theme:update_stylesheet_list action (lines 1045-1077)
- Any theme installed via the Python installer that relies on stylesheet list updates
- Template inheritance for custom themes

**Related Issues:**
- Part of workspace-systems-audit project investigating theme installation bugs


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Replace `get_theme($tid)` with explicit database query that fetches ALL required columns
- [x] Include `properties` and `stylesheets` columns in the SELECT statement
- [x] Add `my_unserialize()` call to unpack properties before passing to update function
- [x] Test with flavor theme uninstall/reinstall cycle

### Fix Implementation

**Change in `TestForum/mcp_bridge.php` (lines 1055-1072):**
```php
// BEFORE (buggy):
// Get the theme to pass to update_theme_stylesheet_list
$theme = get_theme($tid);
if (!$theme) {
    respond(false, ["tid" => $tid], "Theme not found");
}

// AFTER (fixed):
// Query theme WITH properties instead of using incomplete get_theme()
// get_theme() only fetches tid, name, pid, allowedgroups - missing properties/stylesheets
// This caused templateset to be wiped when update_theme_stylesheet_list() rebuilt properties
$query = $db->simple_select(
    'themes',
    'tid, name, pid, properties, stylesheets',
    "tid = ".(int)$tid
);
$theme = $db->fetch_array($query);

if (!$theme) {
    respond(false, ["tid" => $tid], "Theme not found");
}

// Unserialize properties for update_theme_stylesheet_list
if (isset($theme['properties'])) {
    $theme['properties'] = my_unserialize($theme['properties']);
}
```

**Why this works:**
- Fetches complete theme record including `properties` and `stylesheets` columns
- Provides `update_theme_stylesheet_list()` with existing properties to preserve
- Unserializes properties array so MyBB function can merge/update correctly
- Maintains all existing error handling and control flow

### Long-Term Fixes
- Consider reporting this as a MyBB core bug - `get_theme()` should fetch all columns
- Add validation to ensure critical theme properties are never lost during updates
- Document the incomplete nature of `get_theme()` for future reference

### Testing Strategy
1. Uninstall flavor theme completely: `mybb_theme_uninstall(codename='flavor', remove_from_db=True)`
2. Reinstall with fixed code: `mybb_theme_install(codename='flavor')`
3. Verify templateset is preserved: `mybb_theme_get(name="Flavor")`
4. Expected result: `Templateset: 12` (not N/A)


---
## Fix Summary
<!-- ID: fix_summary -->

**Fix Applied:** 2026-01-25 07:20 UTC

**Code Change:**
File: `TestForum/mcp_bridge.php` (lines 1055-1072)

**What Changed:**
- Replaced single-line `get_theme($tid)` call with explicit `simple_select()` query
- Query now fetches: `tid, name, pid, properties, stylesheets` (all 5 required columns)
- Added `my_unserialize()` call to unpack properties before passing to MyBB function
- Preserved all existing error handling and response logic

**Why It Works:**
- `get_theme()` from MyBB core only selects 4 columns, omitting properties and stylesheets
- `update_theme_stylesheet_list()` needs existing properties to preserve templateset
- By fetching complete theme record, we provide all data needed for proper updates
- Unserialization ensures properties are in correct format for MyBB function

**Verification Results:**
- **Before fix:** `mybb_theme_get(name="Flavor")` showed `Templateset: N/A`
- **After fix:** `mybb_theme_get(name="Flavor")` shows `Templateset: 12` ✅
- Theme tid changed from 55 to 56 due to reinstall
- Fix verified with complete uninstall/reinstall cycle

**Test Evidence:**
```
# Before fix (tid=55):
Templateset: N/A

# After fix (tid=56):
Templateset: 12
```

---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Status |
| --- | --- | --- | --- |
| Investigation | MyBBResearchAnalyst | 2026-01-25 07:04 | ✅ Complete |
| Root Cause Diagnosis | MyBBBugHunter | 2026-01-25 07:20 | ✅ Complete |
| Fix Development | MyBBBugHunter | 2026-01-25 07:20 | ✅ Complete |
| Testing | MyBBBugHunter | 2026-01-25 07:28 | ✅ Complete |
| Verification | MyBBBugHunter | 2026-01-25 07:28 | ✅ Complete |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:**
  - Scribe progress log entries in workspace-systems-audit project
  - Research document: RESEARCH_THEME_TEMPLATESET_NULL_BUG.md
  - Call chain analysis: RESEARCH_THEME_INSTALL_CALLCHAIN_20260125.md

- **Fix References:**
  - File modified: `TestForum/mcp_bridge.php` (lines 1055-1072)
  - MyBB core function with incomplete SELECT: `inc/functions.php` line 5697
  - Related project: workspace-systems-audit

- **Root Cause:**
  - MyBB's `get_theme()` function has design limitation (only 4 columns)
  - Bridge code relied on incomplete core function instead of explicit query
  - This is a surgical fix that works around MyBB core limitation

- **Confidence Score:** 0.99
  - Fix verified through complete test cycle
  - Root cause confirmed by code inspection
  - Behavior matches expected results after fix


---
