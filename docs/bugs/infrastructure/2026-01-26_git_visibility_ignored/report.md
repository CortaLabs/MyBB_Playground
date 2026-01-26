
# 🐞 MCP workspace git tools ignore visibility parameter for themes — flavor-theme-refinement-2
**Author:** Scribe
**Version:** v0.1
**Status:** Investigating
**Last Updated:** 2026-01-26 10:22:37 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** git_visibility_ignored

**Reported By:** Scribe

**Date Reported:** 2026-01-26 10:22:37 UTC

**Severity:** HIGH

**Status:** FIXED (Pending Verification)

**Component:** workspace_git.py

**Environment:** [local/staging/production]

**Customer Impact:** [Describe impact or 'None']


---
## Description
<!-- ID: description -->
### Summary
MCP workspace git tools fail to locate theme workspaces because the `get_theme_path()` helper function does not accept or use the `visibility` parameter, causing all git operations to construct incorrect paths like `plugin_manager/themes/{codename}` instead of `plugin_manager/themes/{visibility}/{codename}`.

### Expected Behaviour
When calling `mybb_workspace_git_status(codename="flavor", type="theme", visibility="public")`, the tool should:
1. Extract the `visibility` parameter from args
2. Pass it to `get_theme_path()`
3. Construct path: `/home/austin/projects/MyBB_Playground/plugin_manager/themes/public/flavor`
4. Return git status for that directory

### Actual Behaviour
The tool:
1. Extracts `visibility` from args (line 142)
2. Calls `get_theme_path(config, codename)` WITHOUT visibility (line 148)
3. Constructs path: `/home/austin/projects/MyBB_Playground/plugin_manager/themes/flavor`
4. Returns error: "theme 'flavor' not found"

### Steps to Reproduce
```python
# Theme exists at correct path
mybb_workspace_git_status(codename="flavor", type="theme", visibility="public")
# Returns: Error: theme 'flavor' not found at `/home/austin/projects/MyBB_Playground/plugin_manager/themes/flavor`

# Verify theme actually exists
$ ls /home/austin/projects/MyBB_Playground/plugin_manager/themes/public/flavor
# Shows: DESIGN_GUIDE.md  jscripts  meta.json  README.md  stylesheets  templates
```


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The `get_theme_path()` function at line 21-24 in `workspace_git.py` is missing the `visibility` parameter that `get_plugin_path()` has. This causes theme paths to be constructed as:
```python
# Current (WRONG):
return repo_root / "plugin_manager" / "themes" / codename
# Results in: plugin_manager/themes/flavor

# Should be (CORRECT):
return repo_root / "plugin_manager" / "themes" / visibility / codename
# Results in: plugin_manager/themes/public/flavor
```

**Affected Areas:**
- `get_theme_path()` function (line 21-24) - missing visibility parameter
- 6 handler functions that call `get_theme_path()`:
  1. `handle_workspace_git_init` (line 148)
  2. `handle_workspace_git_status` (line 260)
  3. `handle_workspace_git_commit` (line 355)
  4. `handle_workspace_git_push` (line 416)
  5. `handle_workspace_git_pull` (line 528)
  6. `handle_workspace_github_create` (line 598)

All 6 handlers correctly extract `visibility` from args but fail to pass it to `get_theme_path()`.

**Impact:**
- ALL git operations fail for themes in both public and private visibility
- Plugins work correctly (they use `get_plugin_path()` which has visibility parameter)
- Users cannot initialize git repos, check status, commit, push, or pull for themes
- GitHub repo creation fails for themes

**Related Issues:**
- Plugin git operations work correctly - this is theme-specific


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Update `get_theme_path()` function signature to accept `visibility` parameter with default "public"
- [x] Update function body to include visibility in path construction
- [x] Update all 6 call sites to pass visibility parameter
- [x] Verify fix works for both public and private visibility

### Long-Term Fixes
- [ ] Add integration tests for theme git operations (public and private)
- [ ] Add CI check to ensure visibility parameter consistency across plugin/theme helpers

### Testing Strategy
**Manual Verification:**
1. Test public theme: `mybb_workspace_git_status(codename="flavor", type="theme", visibility="public")`
2. Test private theme: Create private theme and test git operations
3. Verify all 6 git operations work: init, status, commit, push, pull, github_create
4. Verify plugins still work correctly (no regression)

**Test Cases:**
```python
# Public theme git operations
mybb_workspace_git_init(codename="flavor", type="theme", visibility="public")
mybb_workspace_git_status(codename="flavor", type="theme", visibility="public")

# Private theme git operations
mybb_workspace_git_init(codename="test_theme", type="theme", visibility="private")
mybb_workspace_git_status(codename="test_theme", type="theme", visibility="private")

# Plugin operations (regression check)
mybb_workspace_git_status(codename="test_plugin", type="plugin", visibility="public")
```


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
## Fix Summary
<!-- ID: fix_summary -->
**Date Fixed:** 2026-01-26 10:24 UTC

**Changes Made:**
1. Updated `get_theme_path()` function signature (line 21):
   - Added `visibility: str = "public"` parameter
   - Now matches `get_plugin_path()` signature

2. Updated path construction (line 24):
   - Changed from: `repo_root / "plugin_manager" / "themes" / codename`
   - Changed to: `repo_root / "plugin_manager" / "themes" / visibility / codename`

3. Updated all 6 handler call sites to pass visibility parameter:
   - `handle_workspace_git_init` (line 148)
   - `handle_workspace_git_status` (line 260)
   - `handle_workspace_git_commit` (line 355)
   - `handle_workspace_git_push` (line 416)
   - `handle_workspace_git_pull` (line 528)
   - `handle_workspace_github_create` (line 598)

**Verification Required:**
- MCP server restart needed for changes to take effect
- Test public theme: `mybb_workspace_git_status(codename="flavor", type="theme", visibility="public")`
- Test private theme: Create test private theme and verify git operations
- Verify no regression in plugin git operations

---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:** See `.scribe/docs/dev_plans/flavor_theme_refinement_2/PROGRESS_LOG.md`
- **Fix References:** `mybb_mcp/mybb_mcp/handlers/workspace_git.py` (lines 21, 24, 148, 260, 355, 416, 528, 598)
- **Bug Report:** `docs/bugs/infrastructure/2026-01-26_git_visibility_ignored/report.md`


---