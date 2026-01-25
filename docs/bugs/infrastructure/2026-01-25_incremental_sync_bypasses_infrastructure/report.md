# Bug Report: Incremental Sync Bypasses MyBB Infrastructure

**Bug ID:** 2026-01-25_incremental_sync_bypasses_infrastructure
**Category:** Infrastructure
**Severity:** CRITICAL - Architecture Violation
**Status:** FIXED
**Date:** 2026-01-25
**Agent:** MyBBBugHunter

---

## Summary

The `mybb_workspace_sync` incremental mode was bypassing all established infrastructure by:
1. Doing direct database writes for templates
2. Excluding template folders from file sync

This violated the core architectural principle that incremental sync should ONLY copy files.

---

## Symptoms

When running:
```python
mybb_workspace_sync(codename="invite_system", type="plugin", visibility="private")
```

The tool was:
- Writing templates directly to database via `db.update_template()` and `db.create_template()`
- NOT copying template folders to TestForum
- Bypassing: Bridge, MyBB PHP lifecycle, proper plugin infrastructure

---

## Root Cause Analysis

### Issue 1: Templates Excluded from File Sync

**Location:** `mybb_mcp/mybb_mcp/sync/service.py` lines 267-268

The `WORKSPACE_ONLY` set included `"templates"` and `"templates_themes"`, which caused these directories to be skipped during file sync instead of being copied to TestForum.

```python
WORKSPACE_ONLY = {
    ...
    "templates",           # <-- BUG: Should be copied as files
    "templates_themes",    # <-- BUG: Should be copied as files
}
```

### Issue 2: Direct DB Writes in Incremental Mode

**Location:** `mybb_mcp/mybb_mcp/sync/service.py` lines 231-236

The `sync_plugin()` method was calling `_sync_plugin_templates_to_db()` which performed direct database writes:

```python
if direction == 'to_db':
    php_result = self._sync_plugin_php(codename, workspace_path)
    ...
    # BUG: Direct DB writes bypass Bridge/MCP/PHP
    templates_result = self._sync_plugin_templates_to_db(
        codename, workspace_path
    )
```

The `_sync_plugin_templates_to_db()` method (lines 436-480) was calling:
- `self.db.update_template(existing['tid'], content)`
- `self.db.create_template(full_template_name, content, sid=-2)`

These are raw database operations that bypass:
- The Bridge endpoints
- MyBB PHP lifecycle
- Proper plugin activation flow

### Issue 3: Misleading Output

**Location:** `mybb_mcp/mybb_mcp/handlers/sync.py` lines 264-266

The output format reported "Templates synced" for incremental mode, which was misleading since incremental mode should NOT sync templates to DB.

---

## Fix Applied

### Fix 1: Remove Templates from WORKSPACE_ONLY

**File:** `mybb_mcp/mybb_mcp/sync/service.py`

Removed `"templates"` and `"templates_themes"` from the `WORKSPACE_ONLY` set. Templates are now copied to TestForum as regular files during incremental sync.

```python
WORKSPACE_ONLY = {
    "meta.json",
    "README.md",
    ...
    # templates and templates_themes are NOT excluded - they get copied as regular files
}
```

### Fix 2: Remove Template DB Sync from Incremental Mode

**File:** `mybb_mcp/mybb_mcp/sync/service.py`

Removed the `_sync_plugin_templates_to_db()` call from the `to_db` direction. Added explanatory comment:

```python
if direction == 'to_db':
    # Sync PHP and language files to TestForum (files ONLY, no DB writes)
    php_result = self._sync_plugin_php(codename, workspace_path)
    ...
    # NOTE: Template DB sync REMOVED from incremental mode.
    # Incremental sync copies files ONLY. To update templates in DB,
    # use full_pipeline=True which runs proper PHP lifecycle (_activate).
```

### Fix 3: Update Output Formatting

**File:** `mybb_mcp/mybb_mcp/handlers/sync.py`

Updated `_format_incremental_result()` to:
- Report "Mode: Incremental (files only)"
- Remove misleading "Templates synced" count
- Add note: "Use `full_pipeline=True` to update database templates via PHP lifecycle."

---

## Verification

After fix, running:
```python
mybb_workspace_sync(codename="invite_system", type="plugin", visibility="private")
```

Should:
1. Copy ALL files including `templates/` to TestForum
2. NOT touch the database
3. Report only file counts
4. Display note about using `full_pipeline=True` for DB updates

Templates should update in DB ONLY when using:
```python
mybb_workspace_sync(codename="invite_system", type="plugin", visibility="private", full_pipeline=True)
```

---

## Prevention

The `_sync_plugin_templates_to_db()` method is retained for potential future use (e.g., explicit template export) but is no longer called from incremental sync mode. The architectural principle is now clear:

| Mode | What It Does | Database Writes |
|------|--------------|-----------------|
| Incremental (`full_pipeline=False`) | Copy files only | NONE |
| Full Pipeline (`full_pipeline=True`) | Uninstall + Install cycle | Via PHP lifecycle |

---

## Files Modified

1. `mybb_mcp/mybb_mcp/sync/service.py`
   - Removed templates from WORKSPACE_ONLY
   - Removed _sync_plugin_templates_to_db() call from incremental mode

2. `mybb_mcp/mybb_mcp/handlers/sync.py`
   - Updated _format_incremental_result() output formatting

---

## Testing Checklist

- [ ] `mybb_workspace_sync(codename, type="plugin")` copies templates/ to TestForum
- [ ] `mybb_workspace_sync(codename, type="plugin")` does NOT write to database
- [ ] Output shows "Mode: Incremental (files only)"
- [ ] Output shows note about full_pipeline=True
- [ ] `mybb_workspace_sync(codename, type="plugin", full_pipeline=True)` still works (uses PHP lifecycle)

---

## Related Issues

- This is related to the plugins_cache_unprotected bug (same session) where cache clearing caused plugin deactivation
- The direct DB writes in this bug would have bypassed cache invalidation, potentially causing template inconsistencies
