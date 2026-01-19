
# Research: MyBB Internals for Plugin/Manifest Integration

**Author:** R5-MyBBInternals
**Version:** v1.0
**Status:** Complete
**Last Updated:** 2026-01-18
**Project:** mybb-forge-v2

---

## Executive Summary

MyBB 1.8 has mature, well-designed infrastructure for plugin lifecycle management, template inheritance, caching, and file integrity verification. All major capabilities needed for manifest-based plugin tracking are available through built-in functions and the global objects system. The MCP bridge can safely include global.php to access full MyBB context with proper security considerations.

**Primary Objective:** Investigate MyBB's built-in capabilities for file hashing, plugin tracking, global.php integration, template management, and cache mechanisms to inform mybb-forge-v2 architecture

**Key Takeaways:**
- Plugin tracking is standardized in datacache with `['active']` array - can extend with manifest metadata
- SHA512 file hashing available via `verify_files()` function - suitable for plugin integrity verification
- Global objects ($mybb, $db, $cache, $plugins, $templates, $lang) available after including global.php with proper IN_MYBB security
- Template inheritance uses SID values (-2=master, -1=global, >=1=custom sets) - manifests should respect this
- Datacache provides atomic, multi-backend persistence - ideal for manifest storage
- Plugin lifecycle hooks (_install, _activate, _deactivate, _uninstall) provide integration points for manifest updates


---

## Research Scope

**Research Lead:** R5-MyBBInternals
**Investigation Window:** 2026-01-18 (single session)
**Analysis Depth:** Code inspection, direct file analysis, architectural understanding

**Focus Areas:**
- [x] File hashing and integrity verification in MyBB
- [x] Plugin tracking system (datacache storage, lifecycle management)
- [x] global.php integration points and available global objects
- [x] Template management internals (inheritance, versioning, find_replace mechanism)
- [x] Cache system architecture (handlers, persistence, update mechanisms)
- [x] Hook system availability and plugin lifecycle integration

**Files Examined:**
- TestForum/inc/class_plugins.php - Plugin system core
- TestForum/inc/class_datacache.php - Caching system (1382 lines)
- TestForum/inc/class_templates.php - Template engine (163 lines)
- TestForum/inc/functions.php - Core functions including verify_files() (9531 lines)
- TestForum/inc/adminfunctions_templates.php - find_replace_templatesets() function
- TestForum/inc/init.php - Global initialization sequence (329 lines)
- TestForum/global.php - Global entry point (1278 lines)
- TestForum/admin/modules/config/plugins.php - Plugin lifecycle management (727 lines)
- TestForum/admin/modules/tools/file_verification.php - File integrity tool (137 lines)

**Assumptions & Constraints:**
- MyBB 1.8.x version used in TestForum
- Analysis limited to core MyBB (no modifications assumed)
- Focus on standard, documented APIs (not internal implementation details)
- Security assumptions based on IN_MYBB constant and proper initialization


---

## Findings

### Finding 1: Plugin Tracking System

**Summary:** MyBB tracks active plugins in a standardized way using the datacache system. Plugins are stored in a serialized array under the key `'plugins'` with an `['active']` subarray containing plugin codenames. Plugin lifecycle is managed through standard functions (_install, _activate, _deactivate, _uninstall).

**Evidence:**
- TestForum/admin/modules/config/plugins.php (lines 375-476) - plugin activation/deactivation flow
- TestForum/inc/class_datacache.php (lines 1339-1340) - plugin cache reading
- Plugin lifecycle: install() → activate() → cache update → deactivate() → uninstall()

**Details:**
- **Storage:** `datacache` table with title='plugins', serialized array with active plugin codenames
- **Persistence:** `$cache->update("plugins", $plugins_cache)` makes changes atomic
- **Compatibility:** `$plugins->is_compatible($codename)` validates version compatibility
- **No built-in file tracking** - MyBB only tracks codenames, not files or hashes

**Confidence:** 95% - Direct code inspection of working system

**Implications for Forge v2:**
- Can extend manifest alongside existing datacache structure
- Should use plugin lifecycle hooks to update manifest metadata
- Manifest should include file tracking that core MyBB lacks

---

### Finding 2: File Hashing with SHA512

**Summary:** MyBB has a built-in file verification system using SHA512 hashing for core files. The function `verify_files()` in functions.php compares file hashes against official MyBB checksums fetched from mybb.com.

**Evidence:**
- TestForum/inc/functions.php (lines 8429-8516) - verify_files() implementation
- TestForum/admin/modules/tools/file_verification.php (lines 39-87) - Admin CP usage
- Uses `hash_init('sha512')`, `hash_update()`, `hash_final()`
- Checksums fetched from: https://mybb.com/checksums/release_mybb_{version_code}.txt

**Details:**
- **Algorithm:** SHA512 (not MD5)
- **Checksum Format:** `<hash> <filepath>` (one per line)
- **Scope:** Only verifies core MyBB files (identified by path in checksum list)
- **Detection:** Can identify both modified files and missing files
- **Limitations:** Checksums stored externally, not in database; only for core files

**Confidence:** 95% - Direct code inspection and Admin CP verification

**Implications for Forge v2:**
- Can adopt SHA512 for plugin file integrity verification
- Manifest should include file hashes: `"files": { "path": { "sha512": "..." } }`
- Can use verify_files() logic for integrity checking on updates/syncs

---

### Finding 3: Global.php Integration Safety

**Summary:** MyBB initializes all core objects (database, cache, plugins, templates, language) through init.php when global.php is included. With proper security measures (IN_MYBB constant), it's safe to include global.php from the MCP bridge to access full MyBB context.

**Evidence:**
- TestForum/inc/init.php (lines 64-178) - initializes all global objects
- TestForum/global.php (lines 100, 498, 1276) - provides hook points
- IN_MYBB constant requirement in init.php (lines 12-14)
- Database credentials loaded from inc/config.php

**Available Objects After global.php:**

| Object | Type | Key Methods |
|--------|------|------------|
| `$mybb` | Core | $mybb->settings[], $mybb->version_code, $mybb->user[] |
| `$db` | Database | simple_select(), insert_query(), update_query(), escape_string() |
| `$cache` | Cache | read(), update(), delete() |
| `$plugins` | Plugin System | run_hooks(), add_hook(), is_compatible() |
| `$templates` | Templates | get(), cache() |
| `$lang` | Language | load(), set_language() |

**Security Requirements:**
- Define `IN_MYBB` constant before including global.php
- Ensure inc/config.php and database exist
- Handle database connection errors gracefully

**Recommended Pattern:**
```php
define('IN_MYBB', 1);
define('THIS_SCRIPT', 'api');
$_SERVER['REQUEST_METHOD'] = 'POST';
require_once '/path/to/TestForum/global.php';
// Now $cache, $db, $plugins, $templates available safely
```

**Confidence:** 98% - Direct code inspection of initialization flow

**Implications for Forge v2:**
- MCP bridge can safely include global.php for full context access
- Can use $cache for manifest persistence
- Can use $db for direct queries if needed
- Can call MyBB functions directly from bridge

---

### Finding 4: Template Inheritance and Modification

**Summary:** MyBB templates use a multi-level inheritance system with SID (set ID) values. Master templates (-2) are overridden by global templates (-1), which are overridden by theme-specific templates (>=1). The function `find_replace_templatesets()` enables regex-based modifications across all template sets with automatic inheritance handling.

**Evidence:**
- TestForum/inc/class_templates.php (lines 64-124) - template retrieval with inheritance
- TestForum/inc/adminfunctions_templates.php (lines 23-94) - find_replace_templatesets()
- Template query: `ORDER BY sid DESC` prefers custom > global > master
- Template versioning: version field stores MyBB version_code when created/modified

**Details:**
- **SID Values:** -2=master, -1=global, >=1=custom sets (for different themes)
- **Retrieval:** `$templates->get($title)` performs inheritance lookup automatically
- **Modification:** `find_replace_templatesets($title, $find, $replace, $autocreate, $sid, $limit)`
- **Auto-creation:** With `$autocreate=1` (default), creates override in all template sets
- **Version Tracking:** Each template stores version = current MyBB version_code
- **Plugin Usage:** Plugins use find_replace_templatesets() in _activate()/_install()

**Example from hello.php plugin:**
```php
find_replace_templatesets('index', '#'.preg_quote('{$forums}').'#', "{\$hello}\n{\$forums}");
```

**Confidence:** 98% - Direct code inspection and real plugin examples

**Implications for Forge v2:**
- Manifest should track plugin-injected templates with their groups and patterns
- Should track version of templates for upgrade detection
- Can use find_replace_templatesets() for injection/removal
- Should respect SID hierarchy in manifest design

---

### Finding 5: Cache System Architecture

**Summary:** MyBB uses a pluggable cache system with multiple backends (database, files, memcache, memcached, eAccelerator). The datacache class provides atomic read/update/delete operations that work transparently across all backends.

**Evidence:**
- TestForum/inc/class_datacache.php (lines 74-285) - cache backend handling and persistence
- Multiple handlers supported: files, memcache, memcached, eAccelerator, database
- `$cache->read($name, $hard=false)` - returns false if not found
- `$cache->update($name, $contents)` - serializes and persists to DB + handler
- `$cache->delete($name, $greedy=false)` - removes from DB and handler

**Details:**
- **Persistence:** Always stores in database (datacache table), optional handler caching
- **Serialization:** Uses `my_serialize()` for storage, `native_unserialize()` for retrieval
- **Atomicity:** Data guaranteed to persist even if handler fails
- **Multi-backend:** Transparent fallback if handler unavailable
- **Performance:** Handler caching (RAM/disk) for speed, database as fallback

**Handlers Available:**
- Files (disk) - slow but reliable
- Memcache - fast RAM caching
- Memcached - modern Memcached alternative
- eAccelerator - legacy PHP extension caching
- Database - default, always works

**Confidence:** 95% - Direct code inspection of datacache implementation

**Implications for Forge v2:**
- **IDEAL for manifest storage** - use `$cache->read/update()` for manifest persistence
- Manifest automatically survives server restarts and works in all environments
- Supports multi-worktree scenarios (single DB persists manifest)
- Can safely store complex nested structures (serialized PHP arrays)

---

### Finding 6: Hook System and Plugin Integration

**Summary:** MyBB's hook system (`$plugins->run_hooks()`) is available at multiple points in global.php execution. Plugins register hooks during include time, and hooks are executed at defined points throughout the request lifecycle.

**Evidence:**
- TestForum/inc/class_plugins.php (lines 27-155) - hook loading and execution
- TestForum/global.php (lines 100, 498, 1276) - hook points: global_start, global_intermediate, global_end
- Plugins loaded from cache in plugins->load() at initialization

**Hook Points in global.php:**
- `global_start` (line 100) - after basics set up, before user context
- `global_intermediate` (line 498) - middle of initialization
- `global_end` (line 1276) - end of initialization

**Plugin Integration Pattern:**
```php
function my_plugin_activate() {
    global $cache;
    // Update manifest on activation
    $manifest = $cache->read('forge_manifest');
    $manifest['plugins']['codename']['activated'] = true;
    $cache->update('forge_manifest', $manifest);
}
```

**Confidence:** 95% - Direct code inspection and verified with hello.php example plugin

**Implications for Forge v2:**
- Can hook into global_start for manifest initialization
- Plugin _activate/_deactivate hooks can update manifest
- Plugin _install/_uninstall hooks can manage file tracking
- Hooks provide reliable integration points for manifest lifecycle

---

### Additional Notes

**Verification Method:**
All findings based on direct code inspection of TestForum core MyBB 1.8.x files. No speculation - every claim references specific file paths and line numbers.

**Related Research:**
See ARCHITECTURE_GUIDE.md and PHASE_PLAN.md for how these findings should inform manifest design and integration strategy.

**Unverified Assumptions:**
- Custom plugin compatibility - tested with hello.php example only
- Multi-worktree scenarios - not tested, only analyzed architecturally
- Custom cache handlers beyond database - not directly tested


---

## Technical Analysis

### Code Patterns Identified

**1. MyBB Datacache Pattern (for manifest storage)**
```php
// Read manifest
$manifest = $cache->read('forge_manifest');

// Modify manifest
$manifest['plugins']['codename']['activated'] = true;

// Persist atomically
$cache->update('forge_manifest', $manifest);
```

**2. Plugin Lifecycle Hooks (for manifest updates)**
```php
function my_plugin_activate() {
    global $cache;
    // Update manifest - called automatically when plugin activated
}

function my_plugin_install() {
    global $cache;
    // Initialize file tracking - called once on install
}

function my_plugin_deactivate() {
    global $cache;
    // Clean up manifest - called when deactivated
}
```

**3. Template Injection Pattern (for tracking)**
```php
// Plugin injects content into template
find_replace_templatesets('index', '#pattern#', 'replacement');

// Manifest should track:
// - Which templates were modified
// - What was injected (pattern and replacement)
// - Which template sets were affected
```

**4. File Hashing Pattern (for integrity)**
```php
// When creating manifest, hash files:
$hash = hash_file('sha512', $filepath);

// Store in manifest:
$manifest['plugins']['codename']['files']['path'] = ['sha512' => $hash];

// Later, verify integrity:
$current_hash = hash_file('sha512', $filepath);
if ($current_hash !== $manifest['plugins']['codename']['files']['path']['sha512']) {
    // File modified!
}
```

### System Interactions

**Dataflow: Plugin Installation & Manifest Update**
```
1. Admin clicks "Install Plugin"
2. MyBB calls plugin's _install() function
3. Plugin creates database tables, settings
4. Plugin's _install() calls:
   - $cache->update('forge_manifest', [...])  ← Manifest updated atomically
5. MyBB Admin CP shows success
6. Plugin lifecycle complete, manifest reflects state
```

**Dataflow: Manifest Verification on Sync**
```
1. MCP bridge reads manifest from $cache->read('forge_manifest')
2. For each plugin file, verify SHA512 hash
3. If mismatch, report integrity issue
4. If file missing, report missing file
5. Used for multi-worktree consistency checks
```

### Dependency Analysis

**MyBB Internals (used by Forge v2):**
- datacache system (required for manifest persistence)
- plugin lifecycle functions (required for manifest updates)
- file hashing functions (optional, for integrity checks)
- template system (optional, for tracking template modifications)

**External Dependencies:**
- MyBB 1.8.x core (required)
- MariaDB/MySQL database (required for datacache)
- PHP 5.4+ (for hash functions)

### Risk Assessment

**Risk 1: Multi-worktree Plugin State Desynchronization**
- **Description:** Different worktrees might install plugins differently
- **Impact:** Manifest might not match actual state
- **Mitigation:** Manifest stored in shared database, always represents current state
- **Confidence:** LOW risk - datacache provides atomic updates

**Risk 2: Plugin Uninstall Doesn't Remove Manifest**
- **Description:** If _uninstall() doesn't call manifest update, plugin remains in manifest
- **Impact:** Manifest would claim plugin installed when it's not
- **Mitigation:** Enforce manifest update in plugin lifecycle hooks
- **Confidence:** MEDIUM risk - requires plugin author discipline

**Risk 3: Manifest Corruption from Failed Updates**
- **Description:** If _activate() crashes mid-manifest-update, manifest could be incomplete
- **Impact:** Inconsistent manifest state
- **Mitigation:** Use database transactions or pre-serialized updates
- **Confidence:** MEDIUM risk - mitigated by MyBB's serialize/unserialize atomicity

**Risk 4: Template Injection Tracking Inaccuracy**
- **Description:** find_replace_templatesets() modifies templates, but manifest might not reflect all changes
- **Impact:** Template cleanup on uninstall could leave orphaned injected content
- **Mitigation:** Plugin must update manifest during template injection in _install()
- **Confidence:** MEDIUM risk - requires careful plugin documentation

---

## Recommendations

### Immediate Next Steps for Architect Phase

1. **Design Manifest Data Structure**
   - Use datacache as primary storage
   - Include fields: version, plugins[], templates[], files[], dependencies[]
   - Design schema in ARCHITECTURE_GUIDE.md

2. **Define Plugin Integration Points**
   - Document which plugin lifecycle hooks should update manifest
   - Create template for plugin _activate()/_install()/_deactivate()/_uninstall() functions
   - Ensure atomic updates using $cache->update()

3. **Plan File Integrity Verification**
   - Decide on SHA512 hash inclusion in manifest
   - Document hash storage format in manifest
   - Plan verification routine for multi-worktree syncs

4. **Plan MCP Bridge Integration**
   - Design safe global.php inclusion pattern
   - Plan manifest read/write operations via $cache
   - Document error handling for database failures

### Long-Term Opportunities

**1. Git-Based Manifest Export**
- Export manifest from $cache to JSON file for version control
- Use JSON for human-readable manifest in repo
- Sync back to cache on import (bidirectional)

**2. Plugin Dependency Resolution**
- Track plugin dependencies in manifest
- Validate dependency trees before installation
- Auto-install dependencies if available

**3. Multi-version Plugin Tracking**
- Track multiple versions of same plugin
- Enable safe plugin downgrade/rollback
- Provide version compatibility matrix

**4. Automated File Verification on Sync**
- Periodically verify plugin file hashes
- Detect and alert on file modifications
- Automated recovery or quarantine for corrupted plugins

**5. Plugin Update Notifications**
- Track plugin versions in manifest
- Compare against known updates
- Provide update readiness assessment

---

## Appendix

### References

- **MyBB Plugin Development Docs:** https://docs.mybb.com/1.8/development/plugins/
- **MyBB Hooks Reference:** https://docs.mybb.com/1.8/development/plugins/hooks/
- **MCP Protocol Docs:** https://modelcontextprotocol.io/
- **Project Architecture:** See ARCHITECTURE_GUIDE.md in same directory
- **Project Phase Plan:** See PHASE_PLAN.md in same directory

### Files Referenced

Core MyBB Files (TestForum/):
- `/inc/class_plugins.php` - 248 lines, plugin system core
- `/inc/class_datacache.php` - 1382 lines, caching system
- `/inc/class_templates.php` - 163 lines, template engine
- `/inc/functions.php` - 9531 lines, verify_files() at lines 8429-8516
- `/inc/adminfunctions_templates.php` - 94 lines, find_replace_templatesets()
- `/inc/init.php` - 329 lines, initialization
- `/global.php` - 1278 lines, entry point
- `/admin/modules/config/plugins.php` - 727 lines, plugin management UI
- `/admin/modules/tools/file_verification.php` - 137 lines, file verification UI

### Confidence Summary

| Finding | Score | Basis |
|---------|-------|-------|
| Plugin tracking in datacache | 95% | Direct code + working system |
| SHA512 file hashing | 95% | Direct code + Admin CP demo |
| global.php integration | 98% | Direct code + architecture |
| Template inheritance | 98% | Direct code + real examples |
| Cache system | 95% | Direct code + datacache inspection |
| Hook system | 95% | Direct code + plugin examples |

### Next Steps for Research Consumers

- **Architect:** Use Findings 1-6 to design manifest structure and integration points
- **Coder:** Reference Technical Analysis for code patterns and integration examples
- **Reviewer:** Use Confidence Scores to validate implementation against findings

---