# Phase Plan — mybb_sync_safeguards
**Author:** Scribe Architect
**Version:** v1.0
**Status:** Active
**Last Updated:** 2026-01-18

> Three-layer defense-in-depth strategy to eliminate sync race conditions.

---

## Phase Overview

| Phase | Goal | Coder | Effort | Files |
|-------|------|-------|--------|-------|
| **Layer 1** | File Size Validation | Coder-1 | 30 min | `watcher.py` |
| **Layer 2** | Watcher Pause/Resume | Coder-2 | 2-4 hrs | `watcher.py`, `service.py`, `server.py` |
| **Layer 3** | Atomic Writes | Coder-3 | 4-6 hrs | `templates.py`, `stylesheets.py`, `watcher.py` |

**Parallel Execution:** All three layers can be developed in parallel. Layer 1 and Layer 3 have no dependencies. Layer 2 touches `server.py` for export tool handlers.

---

## Layer 1 — File Size Validation (Defensive)

**Objective:** Prevent empty/corrupted files from reaching the database.

**Coder-1 Scope:**
- `mybb_mcp/sync/watcher.py`

**Tasks:**
1. Add file size validation before `read_text()` in `_handle_template_change()` (line ~151)
2. Add file size validation before `read_text()` in `_handle_stylesheet_change()` (line ~178)
3. Log warning when empty file detected: `[disk-sync] WARNING: Skipping empty file: {path}`
4. Handle `FileNotFoundError` gracefully (file deleted between event and validation)
5. Create test file: `tests/sync/test_file_validation.py`

**Implementation Pattern:**
```python
# Before reading content
file_size = path.stat().st_size
if file_size == 0:
    print(f"[disk-sync] WARNING: Skipping empty file: {path}")
    return
```

**Tests Required:**
- `test_empty_file_rejected` - 0-byte file skipped
- `test_tiny_file_accepted` - 1-byte file processed
- `test_file_deleted_during_processing` - graceful handling
- `test_validation_logs_warning` - verify log output

**Acceptance Criteria:**
- [ ] Empty files (0 bytes) are rejected before database write
- [ ] Warning logged with file path
- [ ] No exceptions raised for missing files
- [ ] All 4 tests pass

---

## Layer 2 — Watcher Pause/Resume (Coordination)

**Objective:** Mutual exclusion during bulk export operations.

**Coder-2 Scope:**
- `mybb_mcp/sync/watcher.py` (FileWatcher class)
- `mybb_mcp/sync/service.py` (SyncService API)
- `mybb_mcp/server.py` (export tool handlers)

**Tasks:**
1. Add `_paused` flag and `_pause_lock` to FileWatcher class
2. Implement `pause()` method (idempotent, logs `[disk-sync] Watcher paused`)
3. Implement `resume()` method (idempotent, logs `[disk-sync] Watcher resumed`)
4. Modify `_process_work_queue()` to wait while paused
5. Add `pause_watcher()` and `resume_watcher()` to SyncService
6. Wrap `mybb_sync_export_templates` handler with try/finally pause/resume
7. Wrap `mybb_sync_export_stylesheets` handler with try/finally pause/resume
8. Create test file: `tests/sync/test_pause_resume.py`

**Implementation Pattern (watcher.py):**
```python
def pause(self) -> None:
    with self._pause_lock:
        if self._paused:
            return
        self._paused = True
        print("[disk-sync] Watcher paused")

def resume(self) -> None:
    with self._pause_lock:
        if not self._paused:
            return
        self._paused = False
        print("[disk-sync] Watcher resumed")
```

**Implementation Pattern (server.py export handlers):**
```python
try:
    sync_service.pause_watcher()
    # existing export logic
finally:
    sync_service.resume_watcher()
```

**Tests Required:**
- `test_pause_idempotent` - multiple pause() calls safe
- `test_resume_idempotent` - multiple resume() calls safe
- `test_events_queue_during_pause` - events accumulate, process on resume
- `test_export_pauses_and_resumes` - integration test
- `test_resume_on_export_error` - verify finally block works

**Acceptance Criteria:**
- [ ] `pause()` and `resume()` methods work correctly
- [ ] Export tools pause watcher before bulk operations
- [ ] Export tools resume watcher even on error (try/finally)
- [ ] Events queue during pause, process on resume
- [ ] All 5 tests pass

---

## Layer 3 — Atomic Writes (Filesystem)

**Objective:** Eliminate race at filesystem level - watcher only sees complete files.

**Coder-3 Scope:**
- `mybb_mcp/sync/templates.py`
- `mybb_mcp/sync/stylesheets.py`
- `mybb_mcp/sync/watcher.py` (verify .tmp ignore)

**Tasks:**
1. Modify `_export_templates_by_group()` to use atomic write pattern
2. Modify stylesheet export method to use atomic write pattern
3. Verify watcher ignores `.tmp` files (add to ignore list if needed)
4. Clean up temp files on error
5. Create test file: `tests/sync/test_atomic_writes.py`

**Implementation Pattern:**
```python
temp_path = file_path.with_suffix('.tmp')
try:
    temp_path.write_text(content, encoding='utf-8')
    temp_path.rename(file_path)  # Atomic on POSIX
except Exception as e:
    if temp_path.exists():
        temp_path.unlink()
    raise
```

**Tests Required:**
- `test_atomic_write_creates_temp_file` - .tmp file created first
- `test_atomic_rename_completes` - final file exists after rename
- `test_temp_file_cleaned_on_error` - .tmp removed on failure
- `test_watcher_ignores_tmp_files` - watcher skips .tmp
- `test_export_uses_atomic_pattern` - integration test

**Acceptance Criteria:**
- [ ] Export writes to `.tmp` file first
- [ ] Rename to final extension after write completes
- [ ] Watcher ignores `.tmp` files
- [ ] Temp files cleaned up on error
- [ ] All 5 tests pass

---

## Integration Test (Post-Implementation)

After all three layers are complete, run integration test:

```python
async def test_export_with_watcher_active_no_corruption():
    """Verify all safeguards prevent corruption during concurrent export."""
    watcher.start()
    await sync_service.export_template_set("Default")

    templates = fetch_all_templates()
    for t in templates:
        assert len(t['content']) > 0, f"Template {t['title']} corrupted"
```

---

## Milestone Tracking

| Milestone | Owner | Status | Evidence |
|-----------|-------|--------|----------|
| Layer 1: File Validation | Coder-1 | Pending | tests/sync/test_file_validation.py |
| Layer 2: Pause/Resume | Coder-2 | Pending | tests/sync/test_pause_resume.py |
| Layer 3: Atomic Writes | Coder-3 | Pending | tests/sync/test_atomic_writes.py |
| Integration Test | Review Agent | Pending | Full export with watcher active |
| Opus Post-Implementation Review | Review Agent | Pending | ≥93% score required |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Export forgets to resume watcher | **Mandatory try/finally pattern** |
| Temp files leak on crash | Watcher ignores .tmp, add cleanup routine |
| Pause/resume race conditions | Use `threading.Lock` for pause state |
| Atomic rename fails cross-filesystem | Document POSIX requirement |

---

## Dependencies

- **Layer 1**: No dependencies (can start immediately)
- **Layer 2**: No dependencies (can start immediately)
- **Layer 3**: No dependencies (can start immediately)
- **Integration Test**: Requires all 3 layers complete
