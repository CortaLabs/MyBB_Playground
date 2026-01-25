# Bug Report: Workspace Sync Bridge Bypass

**Bug ID:** 2026-01-25_workspace_sync_bridge_bypass
**Category:** infrastructure
**Severity:** CRITICAL
**Status:** FIXED (partial - see Remaining Issues)
**Component:** `mybb_mcp/mybb_mcp/sync/service.py`

## Summary

The `DiskSyncService` class was bypassing the bridge infrastructure and making direct database calls for template and stylesheet operations. This violates CLAUDE.md's absolute prohibition on direct database access.

## Root Cause

The sync service was using `self.db.*` methods directly instead of routing through the PHP bridge:

- `self.db.get_template()` - direct DB read
- `self.db.update_template()` - direct DB write
- `self.db.create_template()` - direct DB write
- `self.db.get_stylesheet_by_name()` - direct DB read
- `self.db.update_stylesheet()` - direct DB write
- `self.db.create_stylesheet()` - direct DB write
- `self.db.list_stylesheets()` - direct DB read
- `self.db.search_templates()` - direct DB read
- `self.db.list_templates_by_set()` - direct DB read

## Affected Methods

### Fixed (Now Use Bridge)

| Method | Bridge Endpoint | Lines |
|--------|-----------------|-------|
| `_sync_plugin_templates_to_db` | `template:batch_write` | 436-506 |
| `_sync_theme_stylesheets_to_db` | `stylesheet:create` | 625-683 |
| `_sync_theme_templates_to_db` | `template:batch_write` | 713-790 |

### Not Fixed (Missing Bridge Endpoints)

| Method | Required Endpoint | Status |
|--------|-------------------|--------|
| `_sync_plugin_templates_from_db` | `template:list`, `template:read` | Documented, pending |
| `_sync_theme_stylesheets_from_db` | `stylesheet:list` | Documented, pending |
| `_sync_theme_templates_from_db` | `template:list` | Documented, pending |

## Fix Applied

1. **Added bridge import:** `from ..bridge import MyBBBridgeClient`

2. **Refactored `_sync_plugin_templates_to_db`:**
   - Collects templates into batch list
   - Uses `bridge.call("template:batch_write", templates_json=..., sid=-2)`
   - Handles success/failure with proper error reporting

3. **Refactored `_sync_theme_stylesheets_to_db`:**
   - Iterates over CSS files
   - Uses `bridge.call("stylesheet:create", tid=..., name=..., content=...)`
   - Per-file error handling preserved

4. **Refactored `_sync_theme_templates_to_db`:**
   - Collects templates into batch list
   - Uses `bridge.call("template:batch_write", templates_json=..., sid=template_set_sid)`
   - Handles success/failure with proper error reporting

5. **Documented export methods:**
   - Added NOTE comments explaining direct DB access is temporary
   - Referenced future GitHub issue for bridge endpoint additions

## Remaining Issues

The export (from_db) operations CANNOT be fixed until the bridge has read/list endpoints:

- `template:list` - List templates by sid or search pattern
- `template:read` - Read single template content
- `stylesheet:list` - List stylesheets by theme ID

These endpoints need to be added to `TestForum/mcp_bridge.php`.

## Verification

```bash
# Syntax check
cd /home/austin/projects/MyBB_Playground/mybb_mcp
python -m py_compile mybb_mcp/sync/service.py
# Result: Syntax OK
```

## Testing Checklist

- [ ] Restart MCP server to load changes
- [ ] Test `mybb_workspace_sync(codename, direction="to_db")` for plugins
- [ ] Test `mybb_workspace_sync(codename, type="theme", direction="to_db")` for themes
- [ ] Verify templates appear in database via bridge
- [ ] Verify stylesheets appear in database via bridge
- [ ] Check for any bridge errors in output

## Files Changed

- `mybb_mcp/mybb_mcp/sync/service.py` - All fixes applied here

## Related

- CLAUDE.md - Database access prohibition
- `mybb_mcp/mybb_mcp/bridge/client.py` - Bridge client implementation
- `TestForum/mcp_bridge.php` - Bridge PHP endpoints
