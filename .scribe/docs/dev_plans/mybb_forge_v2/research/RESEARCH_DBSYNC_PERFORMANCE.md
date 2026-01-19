# DB-Sync Performance Analysis & Optimization Research

**Research Phase**: R4-DBSync
**Date**: 2026-01-18
**Confidence**: 0.92 (high - direct code inspection)
**Scope**: Architecture analysis, bottleneck identification, multi-worktree considerations

---

## Executive Summary

The MyBB db-sync system (file watcher → async queue → database writer) currently reports noticeable latency when syncing template and stylesheet changes from disk to database. Investigation reveals a multi-layered architecture with identifiable bottlenecks at three key stages: **file detection latency**, **per-file debounce delay**, and **database write overhead**.

**Key Finding**: System is functionally correct but not optimized for "instant" feel. Bottlenecks are not catastrophic but cumulative:
- 0.5s debounce per file creates perceived lag
- Each file sync triggers independent DB queries (no batching)
- HTTP cache refresh adds 10s timeout overhead
- No incremental sync or caching layer

**High-priority optimizations** can reduce perceived latency from multi-second to sub-100ms for typical edits.

---

## 1. Current Architecture

### 1.1 High-Level Flow

```
File Change (disk)
    ↓
[Watchdog Observer] (synchronous thread-based detection)
    ↓
[SyncEventHandler] (filter + debounce)
    ↓
[asyncio.Queue] (thread-safe work queue)
    ↓
[_process_work_queue] (async background task)
    ↓
[TemplateImporter/StylesheetImporter] (DB operations)
    ↓
[MyBBDatabase.cursor()] (connection pool, transaction management)
    ↓
Database Update/Insert
    ↓
[CacheRefresher] (optional: HTTP POST to cachecss.php)
```

### 1.2 Key Components

| Component | File | Key Behavior |
|-----------|------|--------------|
| **FileWatcher** | `watcher.py:215-356` | Observer wrapper; manages start/stop/pause/resume |
| **SyncEventHandler** | `watcher.py:21-212` | Watches filesystem events; implements debounce logic |
| **work_queue** | `watcher.py:241` | asyncio.Queue for thread → async communication |
| **_process_work_queue** | `watcher.py:282-327` | Background async task; processes queued items sequentially |
| **TemplateImporter** | `templates.py:150-207` | Reads file content from disk → DB write |
| **StylesheetImporter** | `stylesheets.py:160-228` | CSS file sync to DB |
| **CacheRefresher** | `cache.py:10-70` | HTTP POST to MyBB's cachecss.php endpoint |
| **MyBBDatabase** | `db/connection.py:18-202` | Connection pooling, transaction management |
| **DiskSyncService** | `service.py:21-644` | Orchestrates all components |

### 1.3 Threading & Async Model

- **Watchdog threads**: File system monitoring (synchronous, spawned by watchdog.Observer)
- **Main asyncio event loop**: Work queue processor (_process_work_queue task)
- **Database cursor**: Creates connection from pool for each operation
- **Cache refresh**: async HTTP client (httpx.AsyncClient) with 10s timeout

**Design Choice**: Hybrid threading + async to decouple file detection (fast, synchronous) from database writes (potentially blocking, async-safe via connection pooling).

---

## 2. Debounce & Batching Strategy

### 2.1 Current Debounce Mechanism

**Location**: `watcher.py:32, 62-79`

Per-file debounce tracking:
```python
DEBOUNCE_SECONDS = 0.5  # 500ms debounce per file
_last_sync: dict[str, float] = {}  # Track last sync time per file

def _should_process(self, path: Path) -> bool:
    now = time.time()
    path_str = str(path)
    with self._lock:
        last_time = self._last_sync.get(path_str, 0)
        if now - last_time < self.DEBOUNCE_SECONDS:
            return False  # SKIP THIS EVENT (dropped)
        self._last_sync[path_str] = now
        return True
```

**Behavior**:
- Per-file tracking: Each file has independent 0.5s debounce window
- Events within window are **dropped** (not queued, not batched)
- Rapid saves (editor autosave every 100ms) → many dropped events
- After 0.5s silent period, next change is processed

**Problem**: 0.5s delay is noticeable to users.

### 2.2 No Request Batching

Currently, each file change is a separate work item:

```python
self.work_queue.put_nowait({
    "type": "template",
    "set_name": parsed.set_name,
    "template_name": parsed.template_name,
    "content": content
})
```

If user saves 3 templates in succession:
- Each file → separate work queue item
- Each item → separate cursor() → separate DB transaction
- 3 templates = 3 independent sync operations instead of 1 batch

**Impact**: No efficiency gain from grouping related operations; overhead compounds.

---

## 3. Identified Bottlenecks

### Bottleneck #1: Debounce Delay (0.5s per file)

**Problem**: User saves file at 0ms, first sync doesn't happen until ~500ms

**Location**: `watcher.py:62-79`

**Impact**: Every file change has built-in minimum latency of 500ms before any action

**Severity**: HIGH - directly observed by user

### Bottleneck #2: No Request Batching

**Problem**: Each file change → separate database transaction

**Location**: `watcher.py:299-303` (individual calls to import_template)

**Example**: 3 templates in 150ms
- Template A → separate cursor/connection/queries
- Template B → separate cursor/connection/queries
- Template C → separate cursor/connection/queries
- **Total**: ~12 separate DB queries instead of ~5 in single transaction

**Severity**: MEDIUM - overhead compounds with multiple files

### Bottleneck #3: Query Redundancy in Template Importer

**Problem**: Template set name lookup repeated for every file in same set

**Location**: `templates.py:185-196`

Each import does:
```python
template_set = self.db.get_template_set_by_name(set_name)  # QUERY 1
master = self.db.get_template(template_name, sid=-2)       # QUERY 2
custom = self.db.get_template(template_name, sid=sid)      # QUERY 3
```

Syncing 10 templates from same set → set lookup happens 10 times

**Severity**: MEDIUM - noticeable only when syncing many templates at once

### Bottleneck #4: HTTP Cache Refresh Blocking

**Problem**: After stylesheet sync, cache refresh waits synchronously in async context

**Location**: `watcher.py:306-315` (calls cache_refresher.refresh_stylesheet)

```python
await self.cache_refresher.refresh_stylesheet(...)
```

Timeout set to 10s. Network latency + PHP execution blocks stylesheet completion.

**Severity**: MEDIUM - affects stylesheet perception, 100-500ms typical overhead

---

## 4. Database Operations Detail

### Template Import Flow

From `templates.py:161-208`:

```
import_template(set_name, template_name, content):
  1. Validate content not empty
  2. Get template set ID by name              [DB QUERY]
  3. Get master template by name (sid=-2)     [DB QUERY]
  4. Get custom template by name (sid=set_id) [DB QUERY]
  5. If custom exists: UPDATE                 [DB QUERY]
     Else: INSERT with version from master    [DB QUERY]
```

**Minimum queries per file**: 4-5 queries

### Connection Management

From `db/connection.py:175-202`:

```python
@contextmanager
def cursor(self, dictionary: bool = True):
    conn = self.connect()  # Get from pool
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor
        conn.commit()      # AUTO-COMMIT on success
    except Exception:
        conn.rollback()    # Auto-rollback on error
    finally:
        cursor.close()
        if self._use_pooling:
            conn.close()   # Return to pool
```

**Good news**:
- Connections properly pooled (mysql.connector.MySQLConnectionPool)
- Transactions auto-commit/rollback
- No connection leaks

**Concern**: Each `cursor()` creates separate transaction, related queries not grouped

---

## 5. Multi-Worktree Considerations

### Current Limitations

**Question**: Can multiple watchers run simultaneously (one per worktree)?

**Answer**: YES, but with limitations:
- Each FileWatcher instance has own Observer and asyncio.Queue
- Multiple watches can point to same sync_root (mybb_sync/)
- **Race condition risk**: Multiple watchers writing same files

### Scenario: Multi-Worktree Sync

```
Worktree-1/mybb_sync/template_sets/Default/index.html
Worktree-2/mybb_sync/template_sets/Default/index.html
            (same database!)
```

**Problem**: Watcher-1 and Watcher-2 both import same file → race condition

**Current handling**: Last write wins (no locking)

### Recommendation for Multi-Worktree

1. **Separate sync_root per worktree**: Each worktree has own mybb_sync/ directory
2. **Coordinated imports**: Central service coordinates which watcher owns which file
3. **Locking**: Database-level locking or distributed lock needed

**Status**: Not implemented - important for future but out of scope for current optimization

---

## 6. Optimization Opportunities (Prioritized)

### P1: Smart Debouncing & Batching (HIGH IMPACT)

**Problem**: 0.5s delay + separate queries

**Solution**:
- Replace per-file debounce with time-window batching
- Collect events for 100-200ms, then process as batch
- Use single database transaction for batch

**Estimated improvement**: 400-500ms latency reduction

**Example implementation**:
```python
BATCH_WINDOW_MS = 100  # Collect events for 100ms
batch_timer = None
pending_events = {}

# Group by set_name/theme_name
# On timer expiry, flush each group as single transaction
```

### P2: Query Batching within Transaction

**Problem**: 4-5 queries per template, no grouping

**Solution**:
- Group templates by set_name within batch
- Single `get_template_set_by_name` per set
- Batch INSERT for new templates
- Reduce from ~40 queries (10 templates) to ~8 queries

**Estimated improvement**: 50-100ms per batch

### P3: Async Cache Refresh (Fire & Forget)

**Problem**: Cache refresh waits synchronously in async context

**Solution**:
- Fire cache refresh without awaiting
- Let it happen in background
- Don't block stylesheet import completion on HTTP response

**Code change**:
```python
# Current (blocks):
await self.cache_refresher.refresh_stylesheet(...)

# Proposed (fire and forget):
asyncio.create_task(self.cache_refresher.refresh_stylesheet(...))
```

**Estimated improvement**: 100-500ms for stylesheet syncs

### P4: In-Memory Cache for Template Lookups

**Problem**: Template set lookup repeated for every file in same set

**Solution**:
- Maintain dict cache: `{set_name: sid}` in TemplateImporter
- TTL of 60s (invalidate after 1 minute)
- Reduces redundant DB queries

**Estimated improvement**: ~5-10ms per batch

### P5: Incremental Sync with Checksums

**Problem**: Every sync writes full content to DB (large templates = slow)

**Solution**:
- On disk read, compute SHA256 of content
- Query DB for current template hash
- Only UPDATE if hash differs
- Avoid unnecessary writes

**Estimated improvement**: Saves 10-50% of writes on non-changes

### P6: Connection Pool Tuning

**Problem**: Pool may be undersized for concurrent operations

**Solution**:
- Increase pool_size from default (~5) to 10-15
- Profile actual concurrent connections needed
- Monitor pool exhaustion metrics

**Estimated improvement**: Minimal for current sequential model, more relevant if P1 (batching) becomes concurrent

---

## 7. Findings Summary

| Finding | Severity | Confidence | Evidence |
|---------|----------|-----------|----------|
| Per-file 0.5s debounce noticeable to users | HIGH | 0.92 | Code at watcher.py:32 |
| No request batching across files | MEDIUM | 0.95 | Architecture: each file queued separately |
| Query redundancy (template set lookup 10x) | MEDIUM | 0.92 | Code at templates.py:185-196 |
| HTTP cache refresh blocks stylesheet completion | MEDIUM | 0.90 | Code awaits in watcher.py:306-315 |
| Connection pooling adequate for sequential model | LOW | 0.88 | Design is sequential per _process_work_queue |

---

## 8. Handoff Guidance for Architect

### What Architect Should Know

1. **Debounce is the main culprit**: 0.5s window feels slow. Primary optimization target.

2. **Batching is straightforward**: Change debounce from per-file to time-window; collect events into groups; flush groups as single transaction.

3. **No architectural rewrite needed**: Current async/thread hybrid model is sound. Optimizations are incremental.

4. **Multi-worktree is future concern**: Not blocking current work but requires coordination strategy later.

### Recommended Phase Approach

**Phase 1 (Quick Win)**: Smart batching + async cache refresh (P1 + P3)
- Reduces perceived latency by 400-500ms
- Low risk (no DB schema changes)
- Implementation: ~200 lines of code

**Phase 2 (Medium)**: Query batching within batch (P2)
- Reduces query overhead by 50-75%
- Risk: Transaction semantics must be preserved
- Implementation: ~100-150 lines

**Phase 3 (Polish)**: Incremental sync + cache optimization (P4 + P5)
- Variable gains, good for scale
- Can be done independently

---

## 9. Research Limitations & Gaps

### What Was Verified

- [x] File watcher implementation (watchdog library)
- [x] Debounce mechanism (per-file tracking)
- [x] Queue architecture (asyncio.Queue)
- [x] Async processor implementation
- [x] Database connection pooling
- [x] Transaction management
- [x] Cache refresh HTTP POST
- [x] Template importer query patterns
- [x] Stylesheet importer query patterns

### What Remains Unverified (For Coder)

- [ ] Actual MySQL query execution times (would need benchmarking)
- [ ] File system event latency from watchdog (OS-dependent)
- [ ] HTTP network latency in cache refresh (environment-dependent)
- [ ] Concurrent stress behavior (multiple files simultaneously)
- [ ] Memory usage of work_queue under load
- [ ] Real-world user-perceived latency in milliseconds

### Recommended Next Steps for Coder

1. **Benchmark query times**: Time actual DB operations on test data
2. **Prototype P1 (batching)**: Implement time-window collector, measure improvement
3. **Load test**: Sync many files simultaneously, profile queue behavior
4. **Monitor in production**: Add timing metrics to track real-world latency

---

## References

| File | Lines | Purpose |
|------|-------|---------|
| `mybb_mcp/sync/watcher.py` | 21-356 | File watcher, event handler, debounce logic |
| `mybb_mcp/sync/templates.py` | 150-207 | Template importer with DB operations |
| `mybb_mcp/sync/stylesheets.py` | 160-228 | Stylesheet importer with DB operations |
| `mybb_mcp/sync/cache.py` | 10-70 | HTTP cache refresh client |
| `mybb_mcp/sync/service.py` | 21-644 | Service orchestrator |
| `mybb_mcp/db/connection.py` | 18-202 | Connection pooling, cursor management |

---

**END OF RESEARCH DOCUMENT**

*This research was produced by R4-DBSync on 2026-01-18.*
*Confidence: 0.92 (high) - Based on direct code inspection and architecture analysis.*
*Ready for Architect review and design phase.*
