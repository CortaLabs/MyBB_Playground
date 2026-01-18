---
id: mybb_sync_safeguards-architecture-guide
title: "\U0001F3D7\uFE0F Architecture Guide \u2014 mybb_sync_safeguards"
doc_name: ARCHITECTURE_GUIDE
category: engineering
status: draft
version: '0.1'
last_updated: '2026-01-18'
maintained_by: Corta Labs
created_by: Corta Labs
owners: []
related_docs: []
tags: []
summary: ''
---

# 🏗️ Architecture Guide — mybb_sync_safeguards
**Author:** Scribe
**Version:** Draft v0.1
**Status:** Draft
**Last Updated:** 2026-01-18 02:39:49 UTC

> Architecture guide for mybb_sync_safeguards.

---
## 1. Problem Statement
<!-- ID: problem_statement -->
**Context:** The MyBB MCP sync system experienced critical data corruption when template export operations ran concurrently with the file watcher. A race condition between non-atomic file writes and immediate file reads resulted in 465 templates being overwritten with empty content.

**Root Cause (Verified):**
1. **Non-Atomic Writes**: Export uses `Path.write_text()` at `templates.py:125`, which creates the file first (triggering watcher events) then writes content
2. **Immediate Reads**: Watcher reads file content at `watcher.py:151` with no validation that write is complete or file is non-empty
3. **Zero Coordination**: Export and watcher operate independently with no mutual exclusion or pause mechanism

**Goals:**
- **Primary**: Eliminate race condition between export and watcher operations
- **Secondary**: Prevent empty/partial file content from corrupting database
- **Tertiary**: Establish safe write patterns for all MCP write tools

**Non-Goals:**
- Rewriting entire sync system architecture
- Adding complex locking mechanisms across all components
- Implementing real-time conflict resolution for concurrent edits

**Success Metrics:**
- Zero data corruption during concurrent export + watcher operations
- File size validation rejects 100% of empty files before database write
- Bulk exports complete successfully with watcher active
- All safeguards can be independently verified through testing

**Risk Assessment:**
- **Critical Risk Mitigated**: Data loss from empty file corruption (465 templates affected in incident)
- **Implementation Risk**: Moderate - changes touch core sync components
- **Rollback Strategy**: Each safeguard is independent and can be disabled individually
<!-- ID: requirements_constraints -->
**Functional Requirements:**

**FR1: File Size Validation (Priority 1)**
- Watcher MUST validate file size > 0 bytes before reading content
- Watcher MUST log warning when empty file detected and skip import
- Validation MUST occur at `watcher.py:151` before `read_text()` call
- OPTIONAL: Configurable minimum size threshold (default: 1 byte)

**FR2: Watcher Pause/Resume (Priority 2)**
- FileWatcher MUST support `pause()` method to stop processing events
- FileWatcher MUST support `resume()` method to restart processing
- Pause MUST be idempotent (multiple pause calls safe)
- Resume MUST be idempotent (multiple resume calls safe)
- Export tools MUST call pause before bulk operations, resume after
- Export tools MUST use try/finally to guarantee resume on error
- Paused watcher MUST still queue events but not process them until resumed

**FR3: Atomic Writes (Priority 3)**
- Export MUST write to temporary `.tmp` file first
- Export MUST rename `.tmp` to final `.html` name after write completes
- Watcher MUST ignore files with `.tmp` extension
- Rename operation MUST be atomic (use `Path.rename()`)
- Applies to both template and stylesheet exporters

**Non-Functional Requirements:**

**NFR1: Performance**
- File size check MUST add <1ms overhead per file
- Pause/resume MUST complete in <10ms
- Atomic writes MUST not significantly slow export (acceptable: <5% slower)

**NFR2: Backward Compatibility**
- Existing export workflow MUST continue working
- Manual file edits MUST still trigger sync (when watcher not paused)
- No changes to database schema or MCP tool signatures

**NFR3: Error Handling**
- Empty file rejection MUST log clear warning with file path
- Pause failure MUST not block export (log warning, proceed)
- Resume MUST restore watcher to consistent state even after crash

**Assumptions:**
- Python `Path.rename()` is atomic on target filesystem (POSIX compliant)
- Watcher debounce (0.5s) remains adequate for manual edits
- Export operations are infrequent enough that pause is acceptable
- File system supports standard temp file patterns

**Constraints:**
- Cannot modify MyBB database structure
- Must work with existing `watchdog` library event model
- Cannot break existing MCP tool consumers
- Must maintain current sync root directory structure

**Risks & Mitigations:**

| Risk | Severity | Mitigation |
|------|----------|------------|
| Empty file validation misses edge cases | Medium | Add comprehensive test coverage for 0-byte, partial writes, special chars |
| Pause/resume race conditions | Medium | Use threading.Lock for pause state, queue all events during pause |
| Atomic rename fails across filesystems | Low | Document POSIX requirement, add fallback logging |
| Export forgets to resume watcher | High | **Use try/finally pattern (mandatory)**, add resume verification |
| Temp files leak on crash | Low | Watcher ignores .tmp files, add cleanup routine |
<!-- ID: architecture_overview -->
**Solution Summary:** Three-layer defense-in-depth strategy to eliminate race conditions: (1) File Size Validation provides immediate safety by rejecting empty files, (2) Watcher Pause/Resume coordination prevents racing during bulk operations, (3) Atomic Writes eliminates race at filesystem level.

**Component Breakdown:**

**Layer 1: File Size Validation (Priority 1 - 30 min implementation)**
- **Location**: `mybb_mcp/sync/watcher.py`, method `_handle_template_change()` and `_handle_stylesheet_change()`
- **Interface**: Add validation before existing `read_text()` calls at lines 151 and 178
- **Purpose**: Defensive check that prevents empty/corrupted content from reaching database
- **Minimal Surface Area**: 5-10 lines of code, zero API changes

**Layer 2: Watcher Coordination (Priority 2 - 2-4 hours implementation)**
- **Location**: `mybb_mcp/sync/watcher.py` (FileWatcher class), `mybb_mcp/sync/service.py` (expose API), `mybb_mcp/server.py` (tool handlers)
- **Interface**: 
  - `FileWatcher.pause()` - Stops processing work queue
  - `FileWatcher.resume()` - Resumes processing work queue
  - `SyncService.pause_watcher()` - Public API
  - `SyncService.resume_watcher()` - Public API
- **Purpose**: Mutual exclusion during bulk export operations
- **State Management**: Add `_paused` flag (threading.Lock protected), queue events during pause

**Layer 3: Atomic Writes (Priority 3 - 4-6 hours implementation)**
- **Location**: `mybb_mcp/sync/templates.py` (method `_export_templates_by_group`), `mybb_mcp/sync/stylesheets.py` (similar method)
- **Interface**: Internal refactor, no API changes
- **Purpose**: Filesystem-level atomicity - watcher only sees complete files
- **Pattern**: Write to `{filename}.tmp`, then `Path.rename()` to `{filename}.html`

**Data Flow:**

**Current Flow (Vulnerable):**
```
Export Loop → write_text() creates file → watcher on_created fires
                ↓                              ↓
         writes content (slow)        read_text() reads immediately
                                             ↓
                                      Queue import job
                                             ↓
                                      UPDATE database ❌ (may be empty)
```

**New Flow with All Safeguards:**
```
Export → pause_watcher()
   ↓
Write to .tmp file (watcher ignores .tmp)
   ↓
Rename .tmp → .html (atomic)
   ↓
resume_watcher()
   ↓
Watcher processes queued events
   ↓
Validation: file size > 0? ✓
   ↓
Read complete content ✓
   ↓
Import to database ✓
```

**External Integrations:**
- MyBB database (existing import/export logic unchanged)
- Python `watchdog` library (existing event model unchanged)
- MCP tool interface (existing tool signatures unchanged)
<!-- ID: detailed_design -->
### Priority 1: File Size Validation (Defensive Layer)

**Implementation Location:** `mybb_mcp/sync/watcher.py`

**Changes to `_handle_template_change()` method (starting line 137):**

```python
def _handle_template_change(self, path: Path) -> None:
    """Handle template file change."""
    try:
        # Get relative path from sync_root
        rel_path = path.relative_to(self.router.sync_root)
        parsed = self.router.parse(str(rel_path))
        if parsed.type != "template" or not parsed.set_name or not parsed.template_name:
            return

        # NEW: Validate file size before reading content
        file_size = path.stat().st_size
        if file_size == 0:
            print(f"[disk-sync] WARNING: Skipping empty file: {path}")
            return

        # Read file content (existing line 151)
        content = path.read_text(encoding='utf-8')
        
        # ... rest of method unchanged
```

**Changes to `_handle_stylesheet_change()` method (starting line 164):**
- Identical validation pattern before line 178 `read_text()` call

**Error Handling:**
- If `path.stat()` fails (file deleted between event and processing), catch `FileNotFoundError` and skip silently
- Log warning to console with file path for empty file detection
- Do NOT raise exception (silent skip is correct behavior)

**Test Coverage Required:**
- Zero-byte file rejected
- 1-byte file accepted
- File deleted between event and validation (handled gracefully)
- File with unicode characters in path handled correctly

---

### Priority 2: Watcher Pause/Resume (Coordination Layer)

**Implementation Location:** `mybb_mcp/sync/watcher.py` (FileWatcher class)

**New Class Attributes:**
```python
class FileWatcher:
    def __init__(self, ...):
        # Existing attributes...
        
        # NEW: Pause state management
        self._paused = False
        self._pause_lock = threading.Lock()
```

**New Method: `pause()`**
```python
def pause(self) -> None:
    """Pause watcher event processing.
    
    Events continue to be queued but are not processed until resume() is called.
    Idempotent - multiple pause() calls are safe.
    """
    with self._pause_lock:
        if self._paused:
            return  # Already paused, no-op
        self._paused = True
        print("[disk-sync] Watcher paused")
```

**New Method: `resume()`**
```python
def resume(self) -> None:
    """Resume watcher event processing.
    
    Processes any queued events that accumulated during pause.
    Idempotent - multiple resume() calls are safe.
    """
    with self._pause_lock:
        if not self._paused:
            return  # Not paused, no-op
        self._paused = False
        print("[disk-sync] Watcher resumed")
```

**Modified Method: `_process_work_queue()` (line 232)**
```python
async def _process_work_queue(self) -> None:
    """Background task that processes queued file changes."""
    while True:
        try:
            # Get work item from queue
            work_item = await self.work_queue.get()
            
            # NEW: Check pause state before processing
            while self._paused:
                await asyncio.sleep(0.1)  # Wait for resume
            
            # Process based on type (existing logic)
            if work_item["type"] == "template":
                # ... existing template processing
```

**Service Layer Integration:** `mybb_mcp/sync/service.py`

Add public methods to `SyncService` class:
```python
def pause_watcher(self) -> None:
    """Pause file watcher during bulk operations."""
    if self.watcher:
        self.watcher.pause()

def resume_watcher(self) -> None:
    """Resume file watcher after bulk operations."""
    if self.watcher:
        self.watcher.resume()
```

**Tool Handler Integration:** `mybb_mcp/server.py`

Modify export handlers (templates and stylesheets):
```python
@server.call_tool()
async def mybb_sync_export_templates(set_name: str) -> list[types.TextContent]:
    """Export templates with watcher coordination."""
    try:
        # NEW: Pause watcher before export
        sync_service.pause_watcher()
        
        # Existing export logic
        stats = await sync_service.export_template_set(set_name)
        
        return [types.TextContent(type="text", text=json.dumps(stats, indent=2))]
    finally:
        # NEW: Always resume watcher (even on error)
        sync_service.resume_watcher()
```

Apply same pattern to `mybb_sync_export_stylesheets` handler.

**Error Handling:**
- Pause/resume are no-fail operations (idempotent)
- try/finally MUST be used in all tool handlers (mandatory)
- If watcher not started, pause/resume are no-ops (safe)

---

### Priority 3: Atomic Writes (Filesystem Layer)

**Implementation Location:** `mybb_mcp/sync/templates.py`

**Modified Method: `_export_templates_by_group()` (line 95)**

```python
async def _export_templates_by_group(
    self, set_name: str, templates: list[dict[str, Any]], sid: int
) -> dict[str, Any]:
    """Export templates organized by group folders."""
    files_exported = 0
    group_counts: dict[str, int] = {}

    for template in templates:
        title = template['title']
        content = template['template']
        template_sid = template['sid']

        # Determine group folder
        group_name = self.group_manager.get_group_name(title, template_sid)

        # Build file path
        file_path = self.router.build_template_path(set_name, group_name, title)

        # Create directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # NEW: Atomic write pattern
        temp_path = file_path.with_suffix('.tmp')
        
        try:
            # Write to temp file first
            temp_path.write_text(content, encoding='utf-8')
            
            # Atomic rename (completes write before watcher sees file)
            temp_path.rename(file_path)
        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise

        files_exported += 1
        group_counts[group_name] = group_counts.get(group_name, 0) + 1

    # ... rest of method unchanged
```

**Implementation Location:** `mybb_mcp/sync/stylesheets.py`

Apply identical atomic write pattern to stylesheet export method (similar structure to templates).

**Watcher Ignore Pattern:** `mybb_mcp/sync/watcher.py`

The watcher already ignores temp files via its ignore patterns. Verify in `SyncEventHandler`:
- Should ignore files ending with `.tmp`
- If not present, add to ignore logic in event filter

**Error Handling:**
- If `temp_path.write_text()` fails, exception propagates (export fails)
- If `temp_path.rename()` fails, clean up temp file before re-raising
- Temp files are cleaned up on any error (no leaks)

**Platform Notes:**
- `Path.rename()` is atomic on POSIX filesystems (Linux, macOS)
- On Windows, may not be atomic across different drives (document limitation)
- Same-directory renames are atomic on all platforms
<!-- ID: directory_structure -->
```
/home/austin/projects/MCP_SPINE/scribe_mcp/docs/dev_plans/mybb_sync_safeguards
```
> Agents rely on this tree for orientation. Update whenever files are added, removed, or reorganised.


---
## 6. Data & Storage
<!-- ID: data_storage -->
- **Datastores:** ['Filesystem markdown', 'SQLite mirror']
- **Indexes & Performance:** FTS for sections
- **Migrations:** Sequential migrations tracked in storage layer


---
## 7. Testing & Validation Strategy
<!-- ID: testing_strategy -->
### Unit Tests

**Location:** `tests/sync/test_safeguards.py` (new file)

**Priority 1: File Size Validation Tests**
- `test_empty_file_rejected()` - Create 0-byte file, verify watcher skips it
- `test_tiny_file_accepted()` - Create 1-byte file, verify watcher processes it
- `test_file_deleted_during_processing()` - Delete file between event and validation
- `test_validation_with_unicode_path()` - File with special characters in name

**Priority 2: Pause/Resume Tests**
- `test_pause_idempotent()` - Multiple pause() calls safe
- `test_resume_idempotent()` - Multiple resume() calls safe
- `test_events_queue_during_pause()` - Events accumulate, process on resume
- `test_pause_while_not_started()` - Pause before watcher started (no-op)
- `test_resume_after_error()` - Watcher resumes correctly after exception

**Priority 3: Atomic Write Tests**
- `test_atomic_write_creates_temp_file()` - Verify .tmp file created first
- `test_atomic_rename_completes()` - Verify final file exists after rename
- `test_temp_file_cleaned_on_error()` - Verify .tmp removed if write fails
- `test_watcher_ignores_tmp_files()` - Watcher doesn't process .tmp files

### Integration Tests

**Location:** `tests/sync/test_safeguards_integration.py` (new file)

**End-to-End Race Condition Test:**
```python
async def test_export_with_watcher_active_no_corruption():
    """Verify all safeguards prevent corruption during concurrent export."""
    # Start watcher
    watcher.start()
    
    # Export 100 templates while watcher active
    await sync_service.export_template_set("Default")
    
    # Verify all templates have non-empty content in database
    templates = fetch_all_templates()
    for t in templates:
        assert len(t['content']) > 0, f"Template {t['title']} corrupted"
```

**Safeguard Failure Scenarios:**
- Test with only validation (no pause, no atomic writes)
- Test with only pause (no validation, no atomic writes)
- Test with only atomic writes (no validation, no pause)
- Verify each layer independently prevents corruption

### Manual QA Checklist

**Before Merge:**
- [ ] Export 465 templates with watcher active → zero corruption
- [ ] Create empty file manually → watcher logs warning, skips import
- [ ] Pause watcher, create files, resume → files processed correctly
- [ ] Force crash during export → temp files cleaned up, watcher recovers
- [ ] Performance: Export time increase <5% with atomic writes

### Performance Benchmarks

**Baseline (before safeguards):**
- Export 465 templates: ~2.5 seconds
- Empty file validation overhead: N/A

**Target (with all safeguards):**
- Export 465 templates: <2.7 seconds (8% acceptable overhead)
- Empty file validation: <1ms per file
- Pause/resume latency: <10ms

### Observability

**Logging Points:**
- File size validation rejection: `[disk-sync] WARNING: Skipping empty file: {path}`
- Watcher pause: `[disk-sync] Watcher paused`
- Watcher resume: `[disk-sync] Watcher resumed`
- Atomic write temp file cleanup: `[disk-sync] Cleaned up temp file: {temp_path}`

**Metrics to Track:**
- Count of empty files rejected per day
- Frequency of pause/resume operations
- Export duration before vs after safeguards
<!-- ID: deployment_operations -->
- **Environments:** Local development
- **Release Process:** Git commits drive deployment
- **Configuration Management:** Project-specific .scribe settings
- **Maintenance & Ownership:** Doc management team


---
## 9. Open Questions & Follow-Ups
<!-- ID: open_questions -->
| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Should templates support conditionals per phase? | Docs Lead | TODO | Evaluate after initial rollout. |
Close each question once answered and reference the relevant section above.


---
## 10. References & Appendix
<!-- ID: references_appendix -->
- PROGRESS_LOG.md- ARCHITECTURE_GUIDE.md
Generated via generate_doc_templates.


---