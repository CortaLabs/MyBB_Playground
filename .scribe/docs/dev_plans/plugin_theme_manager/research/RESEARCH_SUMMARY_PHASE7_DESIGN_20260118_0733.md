# Phase 7 Design Summary: MyBB Core Plugin System Research

**Date:** 2026-01-18 07:33 UTC
**Researcher:** ResearchAgent
**Confidence:** 0.95
**Purpose:** Synthesis of core plugin system research to guide Phase 7 architecture

## Quick Reference: What You Need to Know

### The Plugin Lifecycle (3 Phases)

**Phase 1: File Load** (happens immediately when plugin file is require_once'd)
- Plugin file executes at file scope
- Hooks are registered via `$plugins->add_hook()` calls
- This happens during both admin activation AND normal page loads

**Phase 2: Activation** (happens in admin CP when "Activate" clicked)
- `{codename}_install()` runs once if plugin not already installed (creates tables)
- `{codename}_activate()` runs every activation (creates templates, settings, modifies existing templates)
- Plugin is added to cache `plugins['active']` array
- Cache is written to database

**Phase 3: Loading** (happens on next page load)
- init.php calls `$plugins->load()`
- Plugin file is `require_once`'d if codename is in `plugins['active']` cache
- Hooks are registered again (happens every page load)
- Subsequent code can call hooks which execute all registered functions

### The Key Insight: Plugins Are Executable

Plugins are not passive data - they're executable PHP code. When a plugin file is included:
1. PHP code at file scope executes immediately
2. Hook registration calls happen
3. Any initialization code runs
4. Plugin becomes "loaded" in the hook system

**Implication for Phase 7:** You cannot activate plugins without executing PHP code. Cache updates alone don't do it.

### The Two-Update Problem

Current MCP tools handle plugin cache but don't execute lifecycle functions:
```python
# Current limitation:
mybb_plugin_activate(codename)
  # Updates cache: plugins['active'][codename] = codename
  # Plugin is now marked active
  # But: _install() and _activate() never ran
  # Result: Plugin loads but has no templates, settings, or database tables
```

**Phase 7 Solution:**
```python
# Phase 7 approach:
mybb_plugin_activate(codename)
  # 1. require_once plugin file (registers hooks)
  # 2. Check compatibility
  # 3. If not installed, call _install() function
  # 4. Call _activate() function
  # 5. Update cache: plugins['active'][codename] = codename
  # 6. Verify cache update succeeded
  # Result: Plugin fully activated with all structures created
```

## Architecture Summary

### Component 1: The Plugin Manager Class
**File:** `TestForum/inc/class_plugins.php` (248 lines)
**Responsibility:** Hook registration and execution system

```
pluginSystem class
├── hooks array - in-memory hook registry
├── load() - load plugins from cache
├── add_hook() - register function/method to hook
├── run_hooks() - execute all hooks at point with priority ordering
├── remove_hook() - unregister hook
└── is_compatible() - check version compatibility
```

**Key Methods for Phase 7:**
- `load()` - reads plugins from cache
- `is_compatible()` - validates plugin version
- `add_hook()` / `run_hooks()` - needed for snapshot pattern validation

### Component 2: The Cache System
**File:** `TestForum/inc/class_datacache.php` (1382 lines)
**Responsibility:** Persistent storage of plugin list and other system data

```
datacache class
├── cache() - initialize cache handlers/database
├── read() - retrieve cache entry
├── update() - write cache entry
├── reload_plugins() - force re-read from database
└── [multiple cache-type specific methods]
```

**For plugins:**
- `read("plugins")` - get active plugin list
- `update("plugins", $data)` - write active plugin list to cache

### Component 3: Bootstrap/Init
**File:** `TestForum/inc/init.php` (329 lines)
**Responsibility:** MyBB startup sequence

**Plugin-relevant sequence:**
```
Line 164: Load class_plugins.php, instantiate $plugins
Line 182: Initialize cache handlers/database
Line 264: Call $plugins->load() to load active plugins
```

### Component 4: Admin Plugin Manager
**File:** `TestForum/admin/modules/config/plugins.php` (727 lines)
**Responsibility:** User interface for plugin management

**Key workflow (lines 375-482):**
```php
if(action == "activate")
{
    require_once plugin file                    // Step 1: Load plugin
    if(not installed) call _install()           // Step 2: Optional install
    if(_activate exists) call _activate()       // Step 3: Run activation
    $cache->update("plugins", ...)              // Step 4: Update cache
}
else if(action == "deactivate")
{
    if(_deactivate exists) call _deactivate()   // Step 1: Run deactivation
    if(uninstall) call _uninstall()             // Step 2: Optional uninstall
    $cache->update("plugins", ...)              // Step 3: Update cache
}
```

### Component 5: Plugin Structure
**Example:** `TestForum/inc/plugins/hello.php` (589 lines)

```
Plugin file structure:
├── IN_MYBB check (required security)
├── Template list caching (optimization)
├── Hook registration (at file scope)
├── hello_info() - plugin metadata
├── hello_activate() - create templates, settings
├── hello_deactivate() - remove template changes
├── hello_install() - create database tables
├── hello_is_installed() - check installation status
├── hello_uninstall() - remove all plugin data
└── [plugin function implementations]
```

## Data Flow Diagrams

### Activation Flow

```
Admin clicks "Activate" in Plugin Manager
↓
POST to admin/modules/config/plugins.php
↓
Load plugin file: require_once inc/plugins/{codename}.php
  → File scope code executes
  → Hook registration calls happen immediately
  → [Plugin is now in memory]
↓
Check: is_compatible({codename})? → No: Reject
↓
Check: is_installed()? → No: Call _install()
  → Creates database tables
  → [Database now has plugin structures]
↓
Call _activate()
  → Adds/modifies templates in database
  → Creates settings groups and individual settings
  → May modify existing templates with find_replace_templatesets()
  → Calls rebuild_settings() to sync inc/settings.php
  → [Database now has plugin UI]
↓
Update cache: plugins['active'][codename] = codename
↓
Write cache to database
↓
admin_redirect to plugins list
↓
Admin sees success message
↓
Next page load:
  ↓
  init.php line 264: $plugins->load()
  ↓
  Cache read: plugins['active'] includes {codename}
  ↓
  Loop: foreach active plugin in cache
  ↓
  require_once inc/plugins/{codename}.php
    → Hook registration calls happen again
    → [Plugin hooks are active]
  ↓
  Application code can call hooks
  ↓
  Hook execution runs all registered functions for that hook
  ↓
  Plugin functions execute, modify content
```

### Deactivation Flow

```
Admin clicks "Deactivate"
↓
POST to admin/modules/config/plugins.php
↓
Load plugin file: require_once inc/plugins/{codename}.php
  → File scope code executes (but won't matter much)
↓
Call _deactivate()
  → Reverts template changes using find_replace_templatesets()
  → Cleans up UI
  → [Plugin UI is hidden]
↓
Optional: Call _uninstall() if admin checked "Uninstall"
  → Deletes database tables
  → Deletes settings and template groups
  → [Plugin data is removed]
↓
Remove from cache: unset(plugins['active'][codename])
↓
Write cache to database
↓
Next page load:
  ↓
  init.php line 264: $plugins->load()
  ↓
  Cache read: plugins['active'] does NOT include {codename}
  ↓
  require_once skipped for deactivated plugin
  ↓
  Plugin hooks never register
  ↓
  Plugin is invisible to application
```

## Critical Findings for Phase 7 Design

### Finding 1: Hooks Must Be Registered Every Page Load
- Hooks are NOT persistent in database
- They exist only in `$plugins->hooks` array (memory)
- Every page load must re-execute plugin file to re-register hooks
- **Phase 7 implication:** Cannot create persistent hook registry - must rely on plugin files being loaded

### Finding 2: Two-Stage Lifecycle is Necessary
- Install stage creates permanent structures (databases) - happens once
- Activate stage makes plugin visible (templates, settings) - happens every admin click
- Deactivate must reverse activate but preserve data
- Uninstall removes all traces including data
- **Phase 7 implication:** Must support both _install() and _activate() execution

### Finding 3: Template Modifications Use Reversible Pattern
- `find_replace_templatesets()` uses regex to find/replace in templates
- Deactivate can reverse activation by finding what was added and removing it
- Pattern: Insert unique string in activation, find and remove in deactivation
- **Phase 7 implication:** Document this pattern for plugin developers

### Finding 4: Settings Require Prefix Convention
- All plugin settings use `{codename}_{setting_name}` format
- This prevents conflicts between plugins
- Settings changes require `rebuild_settings()` to sync inc/settings.php
- **Phase 7 implication:** Enforce prefix convention in plugin creation tool

### Finding 5: Cache is Single Point of Truth
- `plugins['active']` array determines which plugins load
- File existence check prevents error if file deleted
- No transaction protection - potential for inconsistency
- **Phase 7 implication:** Must add safety validation before cache update

### Finding 6: Compatibility Checking is Built-In
- `pluginSystem::is_compatible()` method validates version compatibility
- Uses `$mybb->version_code` and plugin compatibility string
- Should always be called before activation
- **Phase 7 implication:** Reuse existing method, don't reimplement

### Finding 7: Hook Registration Pollution is a Risk
- Each activated plugin adds hooks to global `$plugins->hooks`
- If plugin is buggy, hooks remain even if activation fails
- Multiple plugins hooking same point can conflict
- **Phase 7 implication:** Implement snapshot pattern to validate hooks

### Finding 8: Settings Rebuild is Mandatory
- `rebuild_settings()` writes inc/settings.php file with all settings
- Syncs database with PHP file
- Must be called after any settings changes
- **Phase 7 implication:** Always call rebuild_settings() after _activate()/_uninstall()

## Recommended Phase 7 Tool Specification

### Tool 1: mybb_plugin_activate_full

**Purpose:** Fully activate a plugin with lifecycle execution

**Input Parameters:**
- `plugin_codename` (string, required) - plugin to activate (e.g., "hello")
- `force_reinstall` (boolean, optional=false) - run _install even if already installed
- `validate_hooks` (boolean, optional=true) - use snapshot pattern to validate hooks

**Workflow:**
1. Validate plugin file exists at `/inc/plugins/{codename}.php`
2. Validate plugin codename (no `.`, `/`, `\` characters)
3. Load plugin and call `{codename}_info()` to get metadata
4. Check compatibility with `pluginSystem::is_compatible()`
5. If compatibility fails, return error
6. Check if installed via `{codename}_is_installed()`
7. If not installed (or force_reinstall), call `{codename}_install()`
8. Take hook snapshot if validate_hooks enabled
9. Call `{codename}_activate()`
10. Validate hook snapshot if enabled
11. Load current plugin cache
12. Add codename to `plugins['active']` array
13. Update cache with `$cache->update("plugins", ...)`
14. Verify cache update succeeded
15. Return success with metadata

**Output:**
```json
{
  "status": "success",
  "codename": "hello",
  "name": "Hello World!",
  "version": "2.0",
  "installed": true,
  "activated": true,
  "hooks_registered": 3,
  "templates_created": 3,
  "settings_created": 2
}
```

### Tool 2: mybb_plugin_deactivate_full

**Purpose:** Fully deactivate and optionally uninstall a plugin

**Input Parameters:**
- `plugin_codename` (string, required) - plugin to deactivate
- `execute_uninstall` (boolean, optional=false) - also run _uninstall

**Workflow:**
1. Validate plugin file exists
2. Load plugin and call `{codename}_info()`
3. Load current plugin cache
4. If codename not in active list, return error (already inactive)
5. Call `{codename}_deactivate()` if exists
6. If execute_uninstall and function exists, call `{codename}_uninstall()`
7. Remove codename from `plugins['active']` array
8. Update cache with `$cache->update("plugins", ...)`
9. Verify cache update succeeded
10. Return success with metadata

**Output:**
```json
{
  "status": "success",
  "codename": "hello",
  "deactivated": true,
  "uninstalled": false,
  "templates_removed": 3,
  "settings_removed": 2,
  "tables_kept": true
}
```

## Implementation Approach

### 1. Create PHP Helper Class
Create `mybb_mcp/mybb_mcp/tools/plugin_activator.py` (or similar)

Handles:
- Plugin file loading and validation
- Lifecycle function execution
- Hook snapshot logic
- Cache manipulation
- Error handling

### 2. Implement Snapshot Hooks Pattern

```python
class PluginActivator:
    def activate_with_validation(self, codename):
        # Snapshot hooks before
        hooks_before = self.get_hook_state()

        # Execute activation
        self.execute_lifecycle(codename, "activate")

        # Snapshot hooks after
        hooks_after = self.get_hook_state()

        # Validate
        if not self.validate_hooks(hooks_before, hooks_after):
            raise ValidationError("Hook validation failed")

        # Update cache
        self.update_cache(codename, "activate")
```

### 3. Safety Validations

- Plugin codename must exist as file
- Compatibility must pass
- Cache update must succeed
- Hook count must not exceed reasonable threshold

### 4. Error Handling

- Plugin file not found → Clear error
- Compatibility check fails → Explain version requirement
- Lifecycle function throws exception → Rollback cache if possible
- Cache update fails → Warn about state inconsistency

## Handoff Notes for Architect

### Critical Design Decisions Needed

1. **Snapshot Strategy:** Should snapshot be default or opt-in?
   - Default: Safer but slower (extra serialization)
   - Opt-in: Faster but less safe
   - Recommendation: Default enabled, with --no-validate flag to skip

2. **Transaction Safety:** Should Phase 7 add database transaction wrapper?
   - Risk of partial activation if cache write fails
   - Could wrap in BEGIN TRANSACTION / COMMIT
   - Recommendation: At minimum, log consistency errors

3. **Hook Threshold:** What's the maximum hooks a plugin can register?
   - Hello plugin: 3 hooks
   - Complex plugin: 10-20 hooks
   - Malicious plugin: 1000+ hooks
   - Recommendation: Allow up to 50 hooks, warn at 20

4. **Async Execution:** Should activation happen async or block request?
   - Current: Synchronous (waits for _activate to finish)
   - Async would improve UX but complicate error handling
   - Recommendation: Synchronous for now, design async-ready interface

### Open Questions for Architect to Resolve

1. Should mybb_plugin_deactivate_full also support the "keep data" pattern?
   - Deactivate removes UI but keeps tables/settings
   - Uninstall removes everything
   - Current design separates these - good decision

2. How to handle plugin dependencies?
   - Plugin A requires Plugin B
   - Currently: No dependency checking
   - Recommendation: Document pattern, don't enforce in Phase 7

3. Should activation create an audit log entry?
   - Currently: Logs in admin log
   - Phase 7 via MCP: Should also log
   - Recommendation: Yes, via existing MyBB logging system

## Files Analyzed and Line References

| File | Lines | Purpose |
|------|-------|---------|
| class_plugins.php | 27-42 | Plugin loading from cache |
| class_plugins.php | 53-106 | Hook registration |
| class_plugins.php | 115-155 | Hook execution |
| class_plugins.php | 209-247 | Compatibility checking |
| init.php | 162-182 | Cache initialization |
| init.php | 262-265 | Plugin load at boot |
| class_datacache.php | 74-141 | Cache initialization |
| class_datacache.php | 150-200 | Cache reading |
| class_datacache.php | 1335-1341 | Plugin cache reload |
| admin plugins.php | 375-482 | Activation/deactivation workflow |
| hello.php | 18-330 | Example plugin structure |
| hello.php | 408-440 | Uninstall function |

## Confidence Assessment

**High Confidence (95%+):**
- Plugin loading mechanism and hook registration
- Cache structure and reading
- Admin CP activation workflow
- Lifecycle functions existence and patterns

**Medium Confidence (85-94%):**
- Exact cache update implementation details
- Hook snapshot implementation approach
- Multi-plugin interaction safety

**Lower Confidence (75-84%):**
- Whether current MCP context can execute _activate safely
- Exact error handling in lifecycle function execution
- Edge cases with non-serializable data in cache

## Conclusion

MyBB's plugin system is well-designed with clear separation between:
- **Runtime concerns** (hook registration and execution)
- **Persistence concerns** (cache storage and plugin list)
- **Lifecycle concerns** (install/activate/deactivate/uninstall)

Phase 7 has a clear path forward: Create tools that bridge MCP to existing PHP lifecycle functions while adding safety validation through the snapshot pattern.

The implementation should be straightforward but requires careful attention to:
1. Cache consistency
2. Transaction safety
3. Hook validation
4. Error recovery

All necessary components exist in MyBB core - Phase 7 tools don't need to invent new patterns, just orchestrate existing ones safely.

