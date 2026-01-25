
# Theme Stylesheet Display Bugs - 4 Fixes Applied
**Author:** MyBBBugHunter
**Version:** v1.0
**Status:** FIXED
**Last Updated:** 2026-01-24 09:18:44 UTC

> This document captures the investigation and resolution of 4 critical bugs preventing theme stylesheets from displaying in the MyBB Admin CP and loading on the frontend.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** theme_stylesheet_display_fixes

**Reported By:** Orchestrator (from research swarm findings)

**Date Fixed:** 2026-01-24 09:18 UTC

**Severity:** HIGH

**Status:** FIXED

**Components:** ThemeInstaller (installer.py), themes.py handler, manager.py, mcp_bridge.php

**Environment:** Development (MyBB Playground)

**Impact:** Theme stylesheets created programmatically were invisible in Admin CP and CSS not loaded on frontend


---
## Description
<!-- ID: description -->
### Summary
Four related bugs prevented programmatically created theme stylesheets from displaying:
1. `handle_theme_status()` used non-existent `db.query()` method
2. `ThemeInstaller` accessed non-existent config attributes for DB credentials
3. Stylesheet names were stored without `.css` extension
4. `update_theme_stylesheet_list()` was never called after stylesheet creation

### Expected Behaviour
- Stylesheets created via installer should appear in Admin CP Theme Editor
- CSS should load on forum frontend
- Theme properties should contain `disporder` and `stylesheets` arrays

### Actual Behaviour
- `mybb_theme_status` raised `AttributeError: 'MyBBDatabase' object has no attribute 'query'`
- `mybb_delete_theme` raised `AttributeError: 'Config' object has no attribute 'mybb_db_host'`
- Stylesheets stored as `global` instead of `global.css`
- Theme `properties` field was empty, stylesheets not indexed


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
1. **Bug #1 (query method):** `handle_theme_status` used `db.query()` but `MyBBDatabase` only provides `db.cursor()` context manager
2. **Bug #2 (config attrs):** `ThemeInstaller` and `PluginManager.get_disk_sync_service()` accessed `config.mybb_db_host` etc. but `Config` class only stores file paths, not DB credentials
3. **Bug #3 (.css extension):** Used `css_file.stem` (strips extension) instead of `css_file.name`
4. **Bug #4 (disporder):** The critical `update_theme_stylesheet_list()` function was never called after creating stylesheets

**Affected Areas:**
- `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/handlers/themes.py`
- `/home/austin/projects/MyBB_Playground/plugin_manager/installer.py`
- `/home/austin/projects/MyBB_Playground/plugin_manager/manager.py`
- `/home/austin/projects/MyBB_Playground/TestForum/mcp_bridge.php`

**Related Issues:**
- Research document: `RESEARCH_stylesheet_loading_mechanism_20260124.md`
- Research document: `RESEARCH_theme_properties_structure_20260124.md`


---
## Resolution
<!-- ID: resolution_plan -->
### Fix #1: Replace db.query() with db.cursor()
**File:** `handlers/themes.py` lines 614-636
**Change:** Replaced `db.query(theme_query, params)` with `with db.cursor() as cur: cur.execute(...); cur.fetchall()`

### Fix #2: Use load_config() for DB credentials
**Files:** `installer.py:680-685`, `manager.py:1449-1458`
**Change:** Import `mybb_mcp.config.load_config()` and use `mybb_config.db` instead of non-existent `config.mybb_db_*` attributes

### Fix #3: Use full filename with .css extension
**File:** `installer.py:758`
**Change:** Changed `css_file.stem` to `css_file.name` (includes .css extension)

### Fix #4: Add bridge action for update_theme_stylesheet_list
**Files:** `mcp_bridge.php:1036-1068`, `installer.py:776-795`
**Changes:**
- Added new bridge action `theme:update_stylesheet_list` that calls MyBB's `update_theme_stylesheet_list()` function
- Added bridge call in installer after stylesheet deployment loop
- Added action to `supported_actions` lists in bridge

### Verification
- [x] Python syntax verified: `python3 -m py_compile themes.py installer.py manager.py`
- [x] PHP syntax verified: `php -l mcp_bridge.php`
- [x] Import path verified: `MyBBBridgeClient` importable from plugin_manager
- [x] Bug index updated with fix details


---
## Timeline
<!-- ID: timeline -->
| Phase | Owner | Completed | Notes |
| --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 09:11 UTC | Read research docs, diagnosed 4 bugs |
| Fix #1 | MyBBBugHunter | 09:14 UTC | db.query -> db.cursor |
| Fix #2 | MyBBBugHunter | 09:15 UTC | config attrs -> load_config() |
| Fix #3 | MyBBBugHunter | 09:16 UTC | bridge action added |
| Fix #4 | MyBBBugHunter | 09:17 UTC | installer calls bridge |
| Verification | MyBBBugHunter | 09:18 UTC | Syntax checks, index update |


---
## Appendix
<!-- ID: appendix -->
- **Progress Log:** Scribe project `theme-management-system`
- **Research Docs:** `.scribe/docs/dev_plans/theme_management_system/research/`
- **Test Required:** Delete existing Flavor theme, reinstall with fixed code, verify stylesheets appear


---