# Theme Installer Does Not Deploy Workspace Files to TestForum

**Bug ID:** 2026-01-25_theme_workspace_files_not_deployed
**Severity:** HIGH
**Status:** FIXED
**Component:** plugin_manager/installer.py ThemeInstaller
**Project:** flavor-theme-rebuild
**Date Reported:** 2026-01-25
**Date Fixed:** 2026-01-25
**Fixed By:** MyBBBugHunter

---

## Description

### Summary
The ThemeInstaller class in `plugin_manager/installer.py` only deployed stylesheets and templates to the MyBB database, but completely ignored other workspace directories like `jscripts/`, `images/`, etc. that need to be copied to the TestForum filesystem. This meant theme assets like JavaScript files were never deployed.

### Expected Behaviour
When running `mybb_theme_install(codename)`, ALL workspace files should be deployed:
- `stylesheets/*.css` -> MyBB database (themes table)
- `templates/*.html` -> MyBB database (templates table)
- `jscripts/*` -> TestForum/jscripts/ (filesystem)
- `images/*` -> TestForum/images/ (filesystem)
- Any other directories mirroring MyBB structure -> TestForum (filesystem)

All deployed files should be tracked for clean uninstall.

### Actual Behaviour
Only stylesheets and templates were deployed to the database. Directories like `jscripts/` containing `flavor-alpine.js` were completely ignored. The uninstall method also did not remove any deployed files.

### Steps to Reproduce
1. Create theme workspace with `jscripts/` directory containing JavaScript files
2. Run `mybb_theme_install("flavor")`
3. Check TestForum/jscripts/ - JavaScript files are NOT present
4. Run `mybb_theme_uninstall("flavor")` - no files removed (no manifest tracked)

---

## Investigation

### Root Cause Analysis
The ThemeInstaller class was designed with only database-based assets in mind (stylesheets and templates). Unlike PluginInstaller which iterates over ALL workspace directories and copies them to TestForum with full tracking, ThemeInstaller had hardcoded logic for only two directories.

**PluginInstaller pattern (correct):**
```python
for item in workspace_path.iterdir():
    if item_name in self.WORKSPACE_ONLY:
        continue  # Skip meta.json, README.md, etc.
    # Deploy everything else to TestForum
    files, dirs, backups = self._overlay_directory(item, dest_dir, codename)
    # Track in manifest for uninstall
```

**ThemeInstaller (broken):**
```python
# Only handled stylesheets_dir and templates_dir
# No iteration over other workspace directories
# No file deployment to filesystem
# No manifest tracking
```

### Affected Areas
- `plugin_manager/installer.py` - ThemeInstaller class
- All themes with `jscripts/`, `images/`, or other filesystem assets
- Theme uninstall functionality (no cleanup possible without manifest)

### Related Issues
- Similar to how PluginInstaller handles file deployment (reference implementation)
- Part of flavor-theme-rebuild project

---

## Resolution

### Code Changes Applied

**File:** `plugin_manager/installer.py`

**1. Added class constants (lines 665-696):**
```python
WORKSPACE_ONLY = {
    "meta.json", "README.md", "DESIGN_GUIDE.md",
    "stylesheets",  # Deployed to database
    "templates",    # Deployed to database
    "tests", ".git", ".gitignore", ...
}

PROTECTED_DIRECTORIES = {
    "admin", "archive", "cache", "images", "inc", "jscripts", "uploads", ...
}
```

**2. Added backup_root initialization (lines 718-720):**
```python
self.backup_root = config.repo_root / "plugin_manager" / "backups"
self.backup_root.mkdir(parents=True, exist_ok=True)
```

**3. Added helper methods (lines 732-845):**
- `_is_protected_directory()` - Safety check for core MyBB directories
- `_is_safe_to_track()` - Determines if directory can be tracked for uninstall
- `_overlay_directory()` - Copies files with backup and metadata tracking

**4. Added file deployment loop in install_theme (lines 1106-1167):**
```python
# Step 3.5: Deploy workspace files to TestForum filesystem
for item in workspace_path.iterdir():
    if item_name in self.WORKSPACE_ONLY:
        continue
    if item.is_dir():
        dest_dir = self.mybb_root / item_name
        files, dirs, backups = self._overlay_directory(item, dest_dir, codename)
        all_files.extend(files)
        # ... tracking
# Save deployment manifest
self.db.set_deployed_manifest(codename, all_files, all_dirs, all_backups)
```

**5. Rewrote uninstall_theme (lines 1217-1382):**
- Uses `db.get_deployed_manifest(codename)` to find all deployed files
- Deletes files and empty directories (deepest first)
- Safety checks prevent deleting protected directories
- Clears manifest after cleanup

### Testing Strategy
1. **Install test:** `mybb_theme_install("flavor")` should:
   - Deploy stylesheets to DB
   - Deploy templates to DB
   - Copy `jscripts/flavor-alpine.js` to `TestForum/jscripts/`
   - Track all files in deployment manifest

2. **Verify deployment:** Check `TestForum/jscripts/flavor-alpine.js` exists

3. **Uninstall test:** `mybb_theme_uninstall("flavor")` should:
   - Remove `TestForum/jscripts/flavor-alpine.js`
   - Clear deployment manifest
   - NOT delete core directories like `jscripts/` itself

4. **Edge cases:**
   - Empty directories should be skipped
   - Protected directories should never be deleted
   - Existing files should be backed up before overwrite

---

## Timeline

| Phase | Owner | Date | Status |
|-------|-------|------|--------|
| Investigation | MyBBBugHunter | 2026-01-25 | Complete |
| Code Fix | MyBBBugHunter | 2026-01-25 | Complete |
| Testing | Pending | - | Awaiting MCP restart |
| Verification | Pending | - | After testing |

---

## Additional Changes

**headerinclude.html template updated:**
Added Alpine Collapse plugin for collapsible forum categories:
```html
<script defer src="https://cdn.jsdelivr.net/npm/@alpinejs/collapse@3.x.x/dist/cdn.min.js"></script>
```

---

## Appendix

### Files Modified
- `plugin_manager/installer.py` (~270 lines added)
- `plugin_manager/themes/public/flavor/templates/headerinclude.html` (1 line added)

### Consistency with PluginInstaller
Both installers now follow the same pattern:
1. Iterate workspace directories (excluding WORKSPACE_ONLY)
2. Copy to TestForum using overlay methods
3. Track all files with `db.set_deployed_manifest()`
4. On uninstall, use `db.get_deployed_manifest()` for cleanup

This ensures themes and plugins work identically for file deployment and cleanup.
