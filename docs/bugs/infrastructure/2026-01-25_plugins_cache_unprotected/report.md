
# 🐞 Plugins cache not protected from rebuild_cache causing all plugins to deactivate — workspace-sync-tool
**Author:** Scribe
**Version:** v0.1
**Status:** Fixed (pending verification)
**Last Updated:** 2026-01-25 08:40:04 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** plugins_cache_unprotected

**Reported By:** Scribe

**Date Reported:** 2026-01-25 08:40:04 UTC

**Severity:** CRITICAL

**Status:** FIXED

**Component:** mybb_mcp/db/connection.py

**Environment:** [local/staging/production]

**Customer Impact:** [Describe impact or 'None']


---
## Description
<!-- ID: description -->
### Summary
The `plugins` cache entry in MyBB's datacache table was not protected from deletion by `rebuild_cache('all')`. When the cache was cleared, the `plugins` row was deleted entirely, causing MyBB to report zero active plugins. Additionally, `update_plugins_cache()` used an UPDATE statement that silently failed when the row didn't exist.

### Expected Behaviour
- `rebuild_cache('all')` should preserve the `plugins` cache entry (like `version` and `internal_settings`)
- `update_plugins_cache()` should create the cache row if it doesn't exist
- Plugin activation state should be preserved across cache operations

### Actual Behaviour
- `rebuild_cache('all')` deleted the `plugins` row because it wasn't in `protected_caches`
- `update_plugins_cache()` did nothing when the row was missing (UPDATE affects 0 rows)
- All plugins appeared deactivated in MyBB Admin CP after cache clear

### Steps to Reproduce
1. Have active plugins in MyBB (cortex, dice_roller, invite_system)
2. Run `mybb_cache_rebuild('all')` MCP tool
3. Check `mybb_plugin_list_installed()` - shows no active plugins
4. Check Admin CP Plugins page - shows "There are no active plugins"


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
Three bugs combined to cause this issue:

1. **Bug 1 (Critical):** `rebuild_cache()` in `connection.py` line 1516 had `protected_caches = ('version', 'internal_settings')` which did NOT include `'plugins'`. When `rebuild_cache('all')` was called, the plugins row was deleted.

2. **Bug 2 (Secondary):** `update_plugins_cache()` used `UPDATE ... WHERE title = 'plugins'` which affects 0 rows if the row doesn't exist. This meant any attempt to restore plugins would silently fail.

3. **Bug 3 (Format):** `get_plugins_cache()` and `update_plugins_cache()` used a simplified PHP serialization format that didn't match MyBB's expected `{s:6:"active";a:N:{...}}` nested structure.

**Affected Areas:**
- `mybb_mcp/mybb_mcp/db/connection.py` - `rebuild_cache()`, `get_plugins_cache()`, `update_plugins_cache()`
- MyBB plugin system - all plugins appear deactivated
- Admin CP - shows no active plugins

**Related Issues:**
- The user reported this after running `mybb_workspace_sync()` but the sync itself was not the cause. The cache was likely already missing from a previous `rebuild_cache('all')` call.


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Add `'plugins'` to `protected_caches` tuple (line 1516)
- [x] Update message to list all protected caches (line 1528)
- [x] Rewrite `update_plugins_cache()` to use `INSERT...ON DUPLICATE KEY UPDATE`
- [x] Update cache format to match MyBB's `{s:6:"active";a:N:{...}}` structure
- [x] Add `restore_plugins_cache()` method for recovery

### Long-Term Fixes
- [x] Updated `get_plugins_cache()` to properly parse both old and new format (backward compatible)
- [ ] Consider adding MCP tool to restore plugins cache from workspace database

### Testing Strategy
- [ ] Restart MCP server to load changes
- [ ] Run `mybb_cache_rebuild('all')` - should NOT delete plugins row
- [ ] Check `mybb_cache_list()` - should show plugins entry
- [ ] Reactivate plugins via Admin CP or `mybb_plugin_install()`
- [ ] Verify `mybb_plugin_list_installed()` shows active plugins


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 2026-01-25 | Completed - root cause identified |
| Fix Development | MyBBBugHunter | 2026-01-25 | Completed - 4 fixes applied |
| Testing | User | 2026-01-25 | Pending MCP restart |
| Deployment | User | 2026-01-25 | Manual reactivation of plugins required |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:** Progress log entries in workspace-sync-tool project
- **Fix References:**
  - `mybb_mcp/mybb_mcp/db/connection.py` lines 1516, 1528, 1673-1716, 1718-1751, 1765-1792
- **Open Questions:**
  - When exactly was `mybb_cache_rebuild('all')` called that deleted the plugins cache?
  - Should we add an MCP tool specifically for restoring plugins from workspace state?

## Recovery Instructions

After MCP restart, to restore the plugins:

1. **Option A: Reinstall each plugin**
   ```
   mybb_plugin_install('cortex')
   mybb_plugin_install('dice_roller')
   mybb_plugin_install('invite_system')
   mybb_plugin_install('dvz_shoutbox')
   ```

2. **Option B: Use Admin CP**
   - Go to Admin CP > Configuration > Plugins
   - Click "Activate" on each plugin

3. **Option C: Direct cache restoration (requires code)**
   - Call `db.restore_plugins_cache(['cortex', 'dice_roller', 'invite_system', 'dvz_shoutbox'])`

---