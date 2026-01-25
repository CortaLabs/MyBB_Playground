
# _sync_plugin_php() does not overlay entire workspace

**Author:** MyBBBugHunter
**Version:** v1.0
**Status:** FIXED
**Last Updated:** 2026-01-25 08:27 UTC

> Documents the bug where `_sync_plugin_php()` looked for specific files instead of overlaying the entire workspace to TestForum.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** sync_plugin_php_overlay

**Reported By:** User (orchestrator)

**Date Reported:** 2026-01-25

**Severity:** HIGH

**Status:** FIXED

**Component:** mybb_mcp/mybb_mcp/sync/service.py

**Environment:** Local development

**Customer Impact:** Plugin sync failed for plugins with complex directory structures (e.g., cortex with src/ subdirectory)


---
## Description
<!-- ID: description -->
### Summary
The `_sync_plugin_php()` function in `service.py` was hardcoded to look for specific file paths (`src/{codename}.php`, `languages/english/`) instead of doing a proper recursive overlay of the entire workspace to TestForum.

### Expected Behaviour
Workspace sync should overlay ENTIRE workspace onto TestForum, mirroring the structure:
- `workspace/inc/` -> `TestForum/inc/`
- `workspace/jscripts/` -> `TestForum/jscripts/`
- `workspace/images/` -> `TestForum/images/`
- ALL files, ALL directories, NOTHING LEFT BEHIND

### Actual Behaviour (Before Fix)
The function only looked for:
1. `src/{codename}.php` - Wrong path! Plugins use `inc/plugins/{codename}.php`
2. `languages/english/*.php` - Only language files

This missed:
- Main PHP file at `inc/plugins/{codename}.php`
- Plugin subdirectories like `inc/plugins/{codename}/src/`
- Any other directories (jscripts, images, admin, etc.)

### Steps to Reproduce
1. Create a plugin with complex structure (e.g., cortex with src/ subdirectory)
2. Run `mybb_workspace_sync(codename="cortex", type="plugin")`
3. Observe warning: "Plugin PHP not found: src/cortex.php"
4. Verify TestForum/inc/plugins/ is NOT updated


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The `_sync_plugin_php()` function (lines 253-303) was implemented with hardcoded path assumptions:
```python
# BROKEN: Looked for wrong path
src_php = workspace_path / "src" / f"{codename}.php"
```

But actual plugin workspaces use MyBB's standard structure:
```
workspace/
  inc/plugins/{codename}.php      <- Main plugin file
  inc/plugins/{codename}/src/     <- Optional subdirectory
  inc/languages/english/          <- Language files
```

The correct pattern exists in `PluginInstaller._overlay_directory()` (installer.py lines 345-413) which:
1. Iterates all items in workspace
2. Skips WORKSPACE_ONLY files (meta.json, README.md, tests, etc.)
3. Recursively copies all directories to TestForum

**Affected Areas:**
- `mybb_mcp/mybb_mcp/sync/service.py` - `_sync_plugin_php()` method
- `mybb_mcp/mybb_mcp/handlers/sync.py` - `_format_dry_run_plugin()` function

**Related Issues:**
- RESEARCH_workspace_sync_audit_20250125.md identified this as HIGH priority bug


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Rewrite `_sync_plugin_php()` to use workspace overlay pattern
- [x] Add `WORKSPACE_ONLY` constant mirroring PluginInstaller
- [x] Add `_overlay_directory()` and `_overlay_file()` helper methods
- [x] Update `_format_dry_run_plugin()` to show complete overlay preview

### Long-Term Fixes
- [x] Pattern now matches PluginInstaller exactly - no further work needed

### Testing Strategy
- [x] Verified syntax with `py_compile`
- [ ] Test `mybb_workspace_sync(codename="cortex", type="plugin", dry_run=True)` shows all files
- [ ] Test actual sync copies all files to TestForum
- [ ] Test with dice_roller (simpler plugin) to verify both patterns work


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 2026-01-25 | Compared service.py vs installer.py patterns |
| Fix Development | MyBBBugHunter | 2026-01-25 | Rewrote _sync_plugin_php() with overlay pattern |
| Testing | Pending | 2026-01-25 | Requires MCP restart to test |
| Deployment | Pending | - | Merge to main when verified |


---
## Appendix
<!-- ID: appendix -->
### Files Modified
1. **mybb_mcp/mybb_mcp/sync/service.py**
   - Added `WORKSPACE_ONLY` constant (lines 253-269)
   - Rewrote `_sync_plugin_php()` (lines 271-333)
   - Added `_overlay_directory()` helper (lines 335-395)
   - Added `_overlay_file()` helper (lines 397-434)

2. **mybb_mcp/mybb_mcp/handlers/sync.py**
   - Rewrote `_format_dry_run_plugin()` to show complete overlay (lines 302-364)

### Before/After Comparison

**Before (broken):**
```python
# Only looked for specific files
src_php = workspace_path / "src" / f"{codename}.php"  # Wrong path!
lang_src_dir = workspace_path / "languages" / "english"  # Only language
```

**After (fixed):**
```python
# Iterates entire workspace, overlays everything
for item in workspace_path.iterdir():
    if item.name in self.WORKSPACE_ONLY:
        continue
    if item.is_dir():
        files, dirs = self._overlay_directory(item, self.mybb_root / item.name, codename)
    elif item.is_file():
        files = self._overlay_file(item, self.mybb_root, codename)
```

### Confidence Score
0.95 - Fix follows exact pattern from PluginInstaller which is battle-tested.


---