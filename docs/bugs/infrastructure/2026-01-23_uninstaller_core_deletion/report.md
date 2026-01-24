
# 🐞 Plugin uninstaller deletes core MyBB directories — uninstaller-safety-fix
**Author:** Scribe
**Version:** v0.1
**Status:** FIXED
**Last Updated:** 2026-01-23 11:31:31 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** uninstaller_core_deletion

**Reported By:** Scribe

**Date Reported:** 2026-01-23 11:31:31 UTC

**Severity:** CRITICAL

**Status:** FIXED

**Component:** plugin_manager/installer.py

**Environment:** [local/staging/production]

**Customer Impact:** [Describe impact or 'None']


---
## Description
<!-- ID: description -->
### Summary
The plugin uninstaller in `plugin_manager/installer.py` incorrectly tracks and deletes core MyBB directories during plugin uninstallation. When a plugin is uninstalled, directories like `admin/modules/user/` can be deleted, destroying core MyBB functionality.

### Expected Behaviour
- Only directories CREATED by the plugin installer should be deleted during uninstall
- Core MyBB directories (admin/, inc/plugins/, etc.) should NEVER be deleted
- Only plugin-specific directories (e.g., `inc/plugins/myplugin/`) should be tracked and removed

### Actual Behaviour
- The `_overlay_directory()` method at lines 296-304 tracks directories based on whether they exist at the moment of checking
- Due to race conditions and the use of `mkdir(parents=True)`, intermediate directories can be incorrectly marked as "created by us"
- During uninstall, these incorrectly tracked directories are deleted if they become "empty" (after plugin files are removed)
- This results in core MyBB directories being deleted, corrupting the installation

### Steps to Reproduce
1. Create a plugin that deploys files to a nested path like `admin/modules/user/myplugin/foo.php`
2. Install the plugin using `mybb_plugin_install(codename)`
3. Uninstall the plugin using `mybb_plugin_uninstall(codename, remove_files=True)`
4. Observe that `admin/modules/user/` and potentially other core directories are deleted


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The bug is in the `_overlay_directory()` method (lines 261-327) of `plugin_manager/installer.py`:

1. **Race Condition in Directory Tracking (lines 296-307):**
   ```python
   for parent in reversed(dest_file.parents):
       if parent == dest_dir:
           continue  # Skip the base MyBB dir
       if not parent.exists():
           parent_str = str(parent)
           if parent_str not in dirs_created:
               dirs_created.append(parent_str)

   # Create parent directories
   dest_file.parent.mkdir(parents=True, exist_ok=True)
   ```

   The code checks if a directory exists BEFORE creating it. But `mkdir(parents=True)` creates ALL intermediate directories. If a plugin deploys multiple files, the first file's mkdir creates directories that are then seen as "already existing" by subsequent files - but they may still have been tracked by the first file.

2. **No Protection for Core Directories:**
   The code has no concept of "protected" directories. It will track ANY directory that doesn't exist at check time, including core MyBB directories if they happen to be created as intermediates.

3. **Overlay Logic Maps to Core Paths:**
   Line 181: `dest_dir = self.mybb_root / item_name` means a workspace `admin/` directory maps directly to `TestForum/admin/`. Any subdirectories created under this path could be tracked.

**Affected Areas:**
- `plugin_manager/installer.py` - `_overlay_directory()` method (lines 261-327)
- `plugin_manager/installer.py` - `uninstall_plugin()` method (lines 375-541)
- All plugins that deploy files outside of `inc/plugins/{codename}/`

**Related Issues:**
- Previous Scribe log entry documenting the incident where core MyBB files were deleted


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Add PROTECTED_DIRECTORIES constant with core MyBB paths that can NEVER be deleted
- [x] Add `_is_plugin_specific_directory()` helper to validate directories before tracking
- [x] Add safety check in `uninstall_plugin()` to skip protected directories
- [x] Log warnings when attempting to delete suspicious paths

### Long-Term Fixes
- [x] Refactor `_overlay_directory()` to only track directories that are plugin-specific
- [x] Add `_is_safe_to_track()` method that validates a directory should be tracked
- [ ] Consider adding a "dry-run" mode to uninstall that shows what would be deleted

### Testing Strategy
- [x] Create reproduction test that deploys a plugin to a nested core path
- [x] Verify that core directories are NOT tracked during install
- [x] Verify that uninstall does NOT delete core directories
- [x] Verify that plugin-specific directories ARE still cleaned up properly


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | BugHunterAgent | 2026-01-23 | Root cause identified in _overlay_directory() |
| Fix Development | BugHunterAgent | 2026-01-23 | Defense-in-depth implemented |
| Testing | BugHunterAgent | 2026-01-23 | 8 new tests + 16 existing tests pass |
| Deployment | Pending | - | Awaiting review |


---
## Fix Summary
<!-- ID: fix_summary -->

### Changes Made

**File: `plugin_manager/installer.py`**

1. **Added `PROTECTED_DIRECTORIES` constant** (lines 95-124)
   - Set of 25 core MyBB directory paths that can NEVER be deleted
   - Includes: admin/, admin/modules/*, inc/, inc/plugins/, uploads/, etc.

2. **Added `_is_safe_to_track()` method** (lines 74-110)
   - Validates that a directory is plugin-specific before tracking
   - Returns True only if the directory path contains the plugin codename
   - Rejects all paths in PROTECTED_DIRECTORIES

3. **Added `_is_protected_directory()` method** (lines 112-125)
   - Simple check if a path is in the protected set

4. **Updated `_overlay_directory()` method** (line 389)
   - Now uses `_is_safe_to_track()` before adding to dirs_created
   - Core directories will never be tracked for deletion

5. **Added safety check in `uninstall_plugin()`** (lines 563-568)
   - Defense-in-depth: blocks deletion of protected directories
   - Logs warning if attempted deletion of protected path is blocked

### Test Coverage

Created `tests/bugs/test_2025_01_23_uninstaller_core_deletion.py` with 8 tests:
- `test_core_admin_directories_exist_before_install`
- `test_install_does_not_track_core_directories`
- `test_uninstall_preserves_core_directories`
- `test_uninstall_cleans_plugin_specific_dirs`
- `test_protected_directories_constant_exists`
- `test_protected_directories_includes_core_paths`
- `test_is_safe_to_track_rejects_core_dirs`
- `test_is_safe_to_track_accepts_plugin_specific_dirs`

All 8 new tests pass. All 16 existing installer tests pass (no regressions).


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:** Scribe progress log entries in `.scribe/docs/dev_plans/uninstaller_safety_fix/PROGRESS_LOG.md`
- **Fix References:** Changes in `plugin_manager/installer.py`, new tests in `tests/bugs/`
- **Open Questions:** None - fix is complete and verified


---