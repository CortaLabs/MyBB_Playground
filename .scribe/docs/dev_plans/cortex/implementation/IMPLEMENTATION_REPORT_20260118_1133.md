# Implementation Report: Phase 4 - Runtime Integration

**Date:** 2026-01-18 11:33 UTC
**Agent:** Scribe Coder
**Project:** cortex
**Phase:** 4 - Runtime Integration

---

## Scope of Work

Phase 4 implements the runtime integration layer for the Cortex plugin, connecting the Parser, Compiler, and SecurityPolicy components from Phases 1-3 into a working MyBB template wrapper.

### Deliverables Completed

1. **src/Cache.php** - Disk cache for compiled templates
2. **src/Runtime.php** - Template wrapper extending MyBB `templates` class
3. **cortex/config.php** - Plugin configuration file
4. **Updated cortex.php** - Complete plugin implementation with autoloader

---

## Files Created/Modified

### 1. Cache.php (NEW)
**Path:** `plugin_manager/plugins/public/cortex/inc/plugins/cortex/src/Cache.php`

**Purpose:** Disk cache for compiled templates with memory cache layer.

**Key Features:**
- Constructor accepts cache directory, auto-creates if missing
- `get(string $title, string $hash, ?int $tid = null): ?string` - retrieves cached content
- `set(string $title, string $hash, string $content, ?int $tid = null): bool` - stores with atomic write
- `invalidate(string $title): int` - removes all cached versions of a template
- `clear(): int` - removes all cache files
- `isWritable(): bool` - checks if cache directory is writable
- `getCount(): int` - returns number of cached files

**Implementation Details:**
- Uses atomic writes (temp file + rename) for crash safety
- Memory cache for current request performance
- Cache file format: `{tid}_{sanitized_title}_{hash}.php`
- Sanitizes template titles for filesystem safety

### 2. Runtime.php (NEW)
**Path:** `plugin_manager/plugins/public/cortex/inc/plugins/cortex/src/Runtime.php`

**Purpose:** Template wrapper that intercepts `get()` calls and processes Cortex syntax.

**Class Declaration:** `class Runtime extends \templates`

**Key Features:**
- Constructor copies `cache`, `total`, `uncached_templates` from original templates object
- Creates SecurityPolicy, Parser, Compiler, Cache instances
- Overrides `get()` method with processing pipeline

**Processing Flow:**
1. If disabled or eslashes=0, return `parent::get()`
2. Get original template from parent
3. Quick syntax check via regex for Cortex syntax
4. If no syntax, return original unchanged
5. Generate MD5 hash from content
6. Check memory cache, then disk cache
7. On cache miss: parse, compile, cache result
8. On ANY exception: log error, return original template (graceful fallback)

**Syntax Detection Pattern:** `/<(?:if\s|else|func\s|template\s|setvar\s)|\{=/i`

### 3. config.php (NEW)
**Path:** `plugin_manager/plugins/public/cortex/inc/plugins/cortex/config.php`

**Purpose:** Runtime configuration for Cortex behavior.

**Settings:**
- `enabled` - Enable/disable Cortex processing (default: true)
- `cache_enabled` - Enable disk caching (default: true)
- `cache_ttl` - Cache time-to-live (default: 0, no expiration)
- `debug` - Enable debug logging (default: false)
- `security.additional_allowed_functions` - Extra functions to whitelist
- `security.denied_functions` - Functions to blacklist
- `security.max_nesting_depth` - Maximum nesting depth (default: 10)
- `security.max_expression_length` - Maximum expression length (default: 1000)

### 4. cortex.php (UPDATED)
**Path:** `plugin_manager/plugins/public/cortex/inc/plugins/cortex.php`

**Purpose:** Main plugin entry point with autoloader and hook registration.

**Key Features:**
- IN_MYBB security check
- PHP 8.1+ version check with early return
- `CORTEX_VERSION` and `CORTEX_PATH` constants
- PSR-4 autoloader for `Cortex\` namespace
- Hook registration at priority 5 (`global_start`, `xmlhttp`)
- Language file loading in `cortex_info()` and `cortex_init()`
- Cache directory creation in `cortex_activate()`
- Double-wrap prevention via `instanceof` check
- Graceful error handling with `try/catch` in `cortex_init()`

**Functions:**
- `cortex_info(): array` - Plugin metadata for ACP
- `cortex_activate(): void` - Creates cache directory
- `cortex_deactivate(): void` - Preserves cache for quick reactivation
- `cortex_is_installed(): bool` - Always returns true (no DB tables)
- `cortex_install(): void` - No-op (no DB tables)
- `cortex_uninstall(): void` - No-op (no cleanup needed)
- `cortex_init(): void` - Main hook that wraps `$templates` with Runtime

---

## Key Changes and Rationale

### 1. Graceful Fallback Strategy
**Rationale:** The site must never break due to Cortex. Any parsing/compilation error returns the original template unchanged.

**Implementation:** `try/catch (\Throwable $e)` wrapping all processing with error logging in debug mode.

### 2. Quick Syntax Detection
**Rationale:** Avoid parsing overhead for templates without Cortex syntax (majority of templates).

**Implementation:** Simple regex check before full parsing: `/<(?:if\s|else|func\s|template\s|setvar\s)|\{=/i`

### 3. Two-Level Caching
**Rationale:** Minimize re-parsing overhead.

**Implementation:**
- Memory cache: Instant lookups within current request
- Disk cache: Persistent across requests, atomic writes for safety

### 4. Double-Wrap Prevention
**Rationale:** Hooks may fire multiple times in edge cases.

**Implementation:** `instanceof \Cortex\Runtime` check before wrapping.

### 5. Admin CP Exclusion
**Rationale:** ACP templates don't need Cortex processing.

**Implementation:** Early return when `IN_ADMINCP` is defined.

---

## Test Outcomes

### PHP Syntax Validation
All 13 PHP files pass `php -l` syntax validation:

| File | Status |
|------|--------|
| cortex.php | Pass |
| config.php | Pass |
| src/Cache.php | Pass |
| src/Runtime.php | Pass |
| src/Compiler.php | Pass |
| src/Parser.php | Pass |
| src/SecurityPolicy.php | Pass |
| src/Token.php | Pass |
| src/TokenType.php | Pass |
| src/Exceptions/CompileException.php | Pass |
| src/Exceptions/ParseException.php | Pass |
| src/Exceptions/SecurityException.php | Pass |
| inc/languages/english/cortex.lang.php | Pass |

---

## File Structure

```
plugin_manager/plugins/public/cortex/
├── README.md
├── meta.json
├── inc/
│   ├── languages/
│   │   └── english/
│   │       └── cortex.lang.php
│   └── plugins/
│       ├── cortex.php                    (Main plugin file - UPDATED)
│       └── cortex/
│           ├── config.php                (NEW - Phase 4)
│           └── src/
│               ├── Cache.php             (NEW - Phase 4)
│               ├── Compiler.php          (Phase 3)
│               ├── Parser.php            (Phase 1)
│               ├── Runtime.php           (NEW - Phase 4)
│               ├── SecurityPolicy.php    (Phase 2)
│               ├── Token.php             (Phase 1)
│               ├── TokenType.php         (Phase 1)
│               └── Exceptions/
│                   ├── CompileException.php   (Phase 3)
│                   ├── ParseException.php     (Phase 1)
│                   └── SecurityException.php  (Phase 2)
```

---

## Confidence Score

**Overall Confidence:** 0.92

**Breakdown:**
- Cache.php implementation: 0.95 (straightforward, follows established patterns)
- Runtime.php implementation: 0.90 (extends MyBB class, may need integration testing)
- config.php implementation: 0.98 (simple configuration array)
- cortex.php update: 0.92 (autoloader and hooks are standard patterns)
- PHP syntax validation: 1.0 (all files verified)

---

## Suggested Follow-ups

1. **Integration Testing:** Deploy to TestForum and verify:
   - Plugin activates without errors
   - `$templates` is instance of `Cortex\Runtime` after hook
   - Templates with `<if>` syntax render correctly
   - Templates without syntax pass through unchanged

2. **Phase 5 - Testing & QA:** Create PHPUnit test suite per PHASE_PLAN.md

3. **Performance Benchmarking:** Measure overhead of syntax detection and caching

4. **Documentation:** Update wiki with Cortex template syntax reference

---

## Verification Checklist

- [x] Cache.php created with all required methods
- [x] Runtime.php created extending `\templates`
- [x] config.php created with all settings
- [x] cortex.php updated with autoloader and cortex_init
- [x] PHP syntax validated on all files
- [x] No files created in TestForum
- [x] All files in workspace directory
- [x] Implementation report created
