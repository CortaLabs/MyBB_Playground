
# 🔬 Research Disk Sync Service — mybb-playground-docs
**Author:** ResearchAgent
**Version:** v1.0
**Status:** Complete
**Last Updated:** 2026-01-18 08:11 UTC

> Complete factual documentation of the Disk Sync Service for MyBB MCP, covering bidirectional synchronization of templates and stylesheets between database and disk files.

---
## Executive Summary
<!-- ID: executive_summary -->
The Disk Sync Service (`mybb_mcp/mybb_mcp/sync/`) is a comprehensive bidirectional synchronization system for MyBB templates and stylesheets between the MariaDB database and the filesystem (mybb_sync/ directory structure). It handles export (DB → Disk), import (Disk → DB), and continuous file watching with atomic write safety.

**Primary Objective:** Document the complete Disk Sync Service implementation, including export/import workflows, file watcher architecture, configuration options, and directory structure.

**Key Takeaways:**
- Service uses watchdog library for file system events with debouncing (0.5 sec)
- Atomic writes implemented via temp files + rename pattern (POSIX atomic)
- Template inheritance model supports master templates (sid=-2) and custom overrides (sid=specific_id)
- Stylesheet uses copy-on-write pattern with theme inheritance chain walking
- Watcher paused during exports to prevent race conditions
- Configuration via SyncConfig dataclass with environment variable loading

---
## Research Scope
<!-- ID: research_scope -->
**Research Lead:** ResearchAgent

**Investigation Window:** 2026-01-18

**Focus Areas:**
- DiskSyncService orchestrator and lifecycle management
- TemplateExporter/Importer bidirectional sync
- StylesheetExporter/Importer with inheritance handling
- FileWatcher with debouncing and atomic write support
- PathRouter for path parsing (mybb_sync + plugin_manager workspace)
- SyncConfig for configuration management

**Dependencies & Constraints:**
- Python 3.10+ with watchdog library for file system events
- MyBBDatabase instance required for all operations
- Assumes POSIX-compliant filesystem for atomic rename operations
- UTF-8 encoding for all template and stylesheet files
- mybb_sync/ directory structure must follow: template_sets/{set}/{group}/{name}.html and styles/{theme}/{name}.css


---
## Findings
<!-- ID: findings -->

### Finding 1: DiskSyncService Orchestrator Architecture
- **Summary:** DiskSyncService is the main orchestrator managing all sync components. It initializes and coordinates template/stylesheet exporters, importers, file watcher, and cache refresher. Watcher is not started by default.
- **Evidence:**
  - service.py lines 21-78: Constructor initializes PathRouter, TemplateGroupManager, TemplateExporter, StylesheetExporter, TemplateImporter, StylesheetImporter, CacheRefresher, and FileWatcher
  - service.py lines 144-169: start_watcher/stop_watcher public methods check is_running flag before modifying state
  - service.py lines 171-183: pause_watcher/resume_watcher used during export operations for race condition prevention
- **Confidence:** 0.98 (direct code inspection with clear method signatures)

### Finding 2: Template Export/Import Workflow
- **Summary:** Templates are exported from database with both master (sid=-2) and custom templates (sid=specific_id). Export organizes templates into group folders. Import handles template inheritance with update-or-insert pattern.
- **Evidence:**
  - templates.py lines 29-64: export_template_set() fetches templates via _fetch_templates() and exports via _export_templates_by_group()
  - templates.py lines 66-92: _fetch_templates() joins master and custom templates with query pattern `WHERE t.sid IN (-2, %s)`
  - templates.py lines 161-200: import_template() validates set existence, checks master/custom versions, then updates existing custom or creates new
  - templates.py lines 124-129: Atomic writes use temp file pattern: write to .tmp, then rename (POSIX atomic on same filesystem)
- **Confidence:** 0.97 (complete implementation visible with defensive checks)

### Finding 3: Stylesheet Export/Import with Theme Inheritance
- **Summary:** Stylesheets implement copy-on-write inheritance. Export walks theme inheritance chain (via pid) collecting stylesheets with child overrides taking precedence. Import creates override in child theme rather than modifying parent.
- **Evidence:**
  - stylesheets.py lines 26-59: export_theme_stylesheets() fetches theme by name and exports all stylesheets
  - stylesheets.py lines 61-110: _fetch_stylesheets() walks inheritance chain using cursor loop with `WHERE tid = %s` at each level, merging results with child precedence
  - stylesheets.py lines 175-200: import_stylesheet() validates theme exists, implements copy-on-write pattern for inheritance
  - stylesheets.py lines 136-141: Same atomic write pattern as templates (write to .tmp, rename)
- **Confidence:** 0.97 (clear inheritance chain logic with explicit precedence rules)

### Finding 4: FileWatcher with Debouncing and Atomic Write Support
- **Summary:** FileWatcher uses watchdog Observer with SyncEventHandler. Debouncing implemented via per-file timestamp tracking (0.5 sec window). Handles direct writes (on_modified), atomic writes via temp→rename (on_moved), and file creation (on_created). Validates file size to prevent empty file corruption.
- **Evidence:**
  - watcher.py lines 21-30: SyncEventHandler documented to support both direct and atomic writes
  - watcher.py lines 32: DEBOUNCE_SECONDS = 0.5 hardcoded constant
  - watcher.py lines 62-79: _should_process() implements debounce check with thread-safe lock and per-file timestamp dict
  - watcher.py lines 108-138: on_modified, on_created, on_moved all route to _handle_file_change()
  - watcher.py lines 140-175: _handle_template_change() validates file size before reading, queues work for async processing
  - watcher.py lines 177-213: _handle_stylesheet_change() follows same pattern
  - watcher.py lines 87-94: Filters out temp files (.tmp), hidden files (.*), backup files (~)
- **Confidence:** 0.96 (comprehensive event handling with multiple safeguards)

### Finding 5: Path Routing (mybb_sync + Plugin Manager Workspace)
- **Summary:** PathRouter parses both mybb_sync paths (templates: template_sets/{set}/{group}/{name}.html, stylesheets: styles/{theme}/{name}.css) and extended plugin_manager workspace paths (plugins/{visibility}/{codename}/{subdir}/*, themes/{visibility}/{codename}/{subdir}/*). Returns ParsedPath dataclass with metadata.
- **Evidence:**
  - router.py lines 51-119: PathRouter.parse() handles both mybb_sync and workspace paths, returns ParsedPath with type indicators
  - router.py lines 67-119: Original mybb_sync patterns documented with exact path structure
  - router.py lines 96-104: Template path pattern: `template_sets/{set_name}/{group_name}/{template_name}.html` uses path.stem for name
  - router.py lines 106-113: Stylesheet path pattern: `styles/{theme_name}/{stylesheet_name}.css` uses path.name (includes .css)
  - router.py lines 121-153: _parse_workspace_path() routes plugins and themes to separate handlers
  - router.py lines 155-200+: _parse_plugin_path() handles templates, PHP, and language files with visibility validation
- **Confidence:** 0.95 (pattern parsing logic clear, workspace support partially visible in truncated file)

### Finding 6: Configuration and Environment Variables
- **Summary:** SyncConfig dataclass manages configuration with from_env() class method. Supports three environment variables: MYBB_SYNC_ROOT (default: ./mybb_sync), MYBB_AUTO_UPLOAD (default: true), MYBB_CACHE_TOKEN (default: empty).
- **Evidence:**
  - config.py lines 8-47: SyncConfig dataclass with three attributes: sync_root (Path), auto_upload (bool, default True), cache_token (str, default "")
  - config.py lines 21-47: from_env() loads MYBB_SYNC_ROOT with fallback to Path.cwd() / "mybb_sync", parses MYBB_AUTO_UPLOAD as boolean, gets MYBB_CACHE_TOKEN
  - config.py line 40: auto_upload parsing handles "true", "1", "yes" case-insensitive
- **Confidence:** 0.99 (complete configuration implementation visible)

### Finding 7: Race Condition Prevention During Export
- **Summary:** DiskSyncService pauses watcher before export operations and drains queued events after export completes. This prevents file watcher from re-importing files that the export just wrote.
- **Evidence:**
  - service.py lines 80-101: export_template_set() tries pause_watcher(), exports, drains queue, finally resumes
  - service.py lines 103-124: export_theme() follows identical pattern
  - service.py lines 126-142: _drain_watcher_queue() empties asyncio.Queue with try/except, logs drained count
  - service.py lines 171-183: pause_watcher() and resume_watcher() delegate to FileWatcher instance
- **Confidence:** 0.98 (complete race condition prevention visible with finally block guarantee)

### Additional Notes
- All file writes use UTF-8 encoding explicitly
- Empty file detection in watcher prevents corruption from partial writes
- TemplateGroupManager required for template export (uses get_group_name method)
- CacheRefresher component handles stylesheet cache invalidation on updates
- Watcher queues work items in asyncio.Queue for thread-safe processing


---
## Technical Analysis
<!-- ID: technical_analysis -->

### Directory Structure (mybb_sync/)

Templates are organized into a 4-level hierarchy:
```
mybb_sync/
└── template_sets/
    └── {set_name}/
        └── {group_name}/
            └── {template_name}.html
```

Example from actual deployment:
- `mybb_sync/template_sets/Default Templates/Sendthread Templates/sendthread.html`
- `mybb_sync/template_sets/Default Templates/Forumdisplay Templates/forumdisplay_inlinemoderation_custom.html`

Stylesheets are organized into 2 levels:
```
mybb_sync/
└── styles/
    └── {theme_name}/
        └── {stylesheet_name}.css
```

Examples from deployment (Default theme):
- `mybb_sync/styles/Default/global.css`
- `mybb_sync/styles/Default/showthread.css`
- `mybb_sync/styles/Default/color_black.css` through `color_water.css` (9 color variants)

### Code Patterns Identified

**1. Async/Await Pattern**
- All export methods are async (export_template_set, import_template, export_theme_stylesheets)
- Allows non-blocking file I/O operations
- DiskSyncService awaits export operations in try/finally blocks

**2. Atomic Write Safety**
- Universally implemented: write to `.tmp` file, then atomic rename to target
- Applies to both templates.py (line 125-129) and stylesheets.py (line 137-141)
- Prevents corruption from interrupted writes or partial file states
- Temp files filtered out by watcher (watcher.py line 93: `if path.suffix == '.tmp': return`)

**3. Inheritance Chain Walking**
- Stylesheets _fetch_stylesheets() (line 61-110) walks up theme inheritance using while loop:
  1. Fetch stylesheets for current theme (tid)
  2. Merge into dict with child precedence (only add if not present)
  3. Get parent theme ID (pid) from themes table
  4. Continue until parent is None
- Ensures child theme overrides always take precedence

**4. Template Master Template Pattern**
- Templates support two levels: master (sid=-2) and custom (sid=specific_set_id)
- Master templates are always included in exports via LEFT JOIN (templates.py line 85-86)
- Import checks both master and custom existence to decide UPDATE vs INSERT (templates.py line 193-200)

**5. Debounce with Thread-Safe Locking**
- Per-file timestamp dict (_last_sync) protected by Lock (watcher.py lines 59-60, 74-79)
- Prevents race conditions from multiple file system events
- 0.5 second window hardcoded for all files

### System Interactions

**DiskSyncService Dependencies:**
- MyBBDatabase: All queries go through db instance for templates, themes, stylesheets
- PathRouter: All file path parsing delegates to router instance
- TemplateGroupManager: Determines which group folder each template belongs to
- CacheRefresher: Triggers HTTP request to invalidate stylesheet cache on updates
- FileWatcher: Background observer for file system changes
- watchdog library: Provides Observer and file system event handlers

**Async Work Queue:**
- FileWatcher uses asyncio.Queue for thread-safe work submission from watchdog threads to async loop
- Queue items are dicts with type, content, set_name, template_name/theme_name/stylesheet_name

**Database Interactions:**
- Templates table: sid (set ID), title, template (content)
- Themes table: tid, pid (parent ID), name
- Themestylesheets table: tid (theme ID), name, stylesheet (content)

### Risk Assessment

**RISK 1: Race Condition in Concurrent Exports**
- **Severity:** Medium
- **Scenario:** If export_template_set and export_theme run concurrently, _drain_watcher_queue() may not clear all events
- **Mitigation:** Service.pause_watcher() serializes event processing, but only per export call. No global lock across multiple concurrent exports.
- **Recommendation:** Document that concurrent exports are not recommended, or implement global export lock

**RISK 2: Empty File Corruption Window**
- **Severity:** Low
- **Scenario:** File size check at line 156-158 (templates) and 193-195 (stylesheets) happens after file exists but could be deleted before read
- **Mitigation:** Try/except FileNotFoundError on stat() and read() calls (lines 154-161, 191-198)
- **Current Status:** Already handled with proper exception handling

**RISK 3: UTF-8 Encoding Assumption**
- **Severity:** Low
- **Scenario:** Files not encoded in UTF-8 will raise UnicodeDecodeError during import
- **Mitigation:** Explicit encoding='utf-8' in all read_text/write_text calls, defensive code prevents partial corruption
- **Recommendation:** Consider error handling for encoding mismatches

**RISK 4: Database Transaction Isolation**
- **Severity:** Medium
- **Scenario:** Import operations are not wrapped in transactions, risking partial updates
- **Mitigation:** Each import is a single INSERT or UPDATE statement, atomic at DB level
- **Recommendation:** Verify MyBBDatabase uses autocommit=true or explicit transactions

**RISK 5: Watcher Queue Buildup**
- **Severity:** Low
- **Scenario:** If async import loop is slow, queue could grow unbounded
- **Mitigation:** asyncio.Queue is unbounded by default, but drained after each export
- **Recommendation:** Monitor queue size, consider max_size parameter


---
## Recommendations
<!-- ID: recommendations -->

### Immediate Next Steps (For Architects/Coders)

1. **Verify Async Execution Model**
   - Confirm FileWatcher's async import loop and event queue implementation
   - Read remainder of watcher.py (lines 200-356) to understand FileWatcher.start/stop/pause/resume lifecycle
   - Verify asyncio integration with watchdog Observer threads

2. **Document Export Safety Requirements**
   - Add comment in DiskSyncService stating that concurrent export operations not recommended
   - Consider implementing optional global export lock to prevent race conditions

3. **Complete PathRouter Investigation**
   - Read router.py lines 200-376 to document plugin_manager workspace path parsing completely
   - Document _parse_theme_path() method and full path building logic

4. **Verify Template Group Manager**
   - Read groups.py module to understand TemplateGroupManager.get_group_name() logic
   - Document how template groups are categorized (this affects export directory structure)

5. **Review Cache Refresher**
   - Read cache.py module to understand CacheRefresher implementation
   - Verify HTTP cache invalidation strategy for stylesheet updates

### Long-Term Opportunities

1. **Performance Optimization**
   - Consider batch processing for large template/stylesheet exports
   - Evaluate async file I/O library (aiofiles) to replace blocking write_text/read_text
   - Profile queue event processing speed for large watch directories

2. **Robustness Improvements**
   - Implement optional transaction wrapping for import operations
   - Add metrics/logging for queue depth and event processing latency
   - Add configurable debounce window (currently hardcoded 0.5 sec)

3. **Feature Enhancements**
   - Support selective template/stylesheet sync (only modified files)
   - Add bidirectional sync status API (which files are out of sync)
   - Support theme stylesheet inheritance visualization/export

4. **Developer Experience**
   - Add verbose logging option for debugging file watch events
   - Create CLI tool to manually trigger export/import operations
   - Document mybb_sync directory layout in wiki with examples


---
## Appendix
<!-- ID: appendix -->

### Module Inventory
- `service.py` (644 lines): Main orchestrator, lifecycle management
- `watcher.py` (356 lines): File system monitoring, event handling
- `templates.py` (207 lines): Template export/import logic
- `stylesheets.py` (228 lines): Stylesheet export/import with inheritance
- `router.py` (376 lines): Path parsing for mybb_sync and workspace paths
- `config.py` (47 lines): Configuration management via environment variables

Related modules (not fully analyzed):
- `groups.py`: TemplateGroupManager implementation
- `cache.py`: CacheRefresher implementation

### Database Tables Referenced
- mybb_templates (sid, tid, title, template)
- mybb_themes (tid, pid, name)
- mybb_themestylesheets (tid, name, stylesheet)
- mybb_templatesets (sid, name)

### External Dependencies
- watchdog 3.0+: File system event monitoring
- pathlib (stdlib): Path manipulation
- asyncio (stdlib): Async event handling
- dataclasses (stdlib): Configuration objects

### Known Limitations
- UTF-8 encoding assumed for all templates and stylesheets
- Debounce window (0.5 sec) hardcoded, not configurable
- No transaction wrapping for multi-statement imports
- Concurrent exports not officially supported

### Reference Implementation Locations
- Export start-to-finish: service.py:80 → templates.py:29 → templates.py:66 → write via templates.py:124
- Import start-to-finish: watcher.py:167 → templates.py:161 → DB update via templates.py:200+
- Inheritance handling: stylesheets.py:61 (walk chain) vs stylesheets.py:175 (copy-on-write)


---