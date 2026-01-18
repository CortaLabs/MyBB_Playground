# Plugin Cache Mechanics and Data Persistence

**Date:** 2026-01-18 07:32 UTC
**Researcher:** ResearchAgent
**Confidence:** 0.93
**Scope:** Plugin cache structure, serialization, update mechanisms, and impact on plugin loading

## Executive Summary

The MyBB plugin system relies entirely on a **serialized cache entry** stored in the database under key `"plugins"`. This single cache entry contains an array with active plugin list. Understanding cache mechanics is critical for Phase 7 because:
1. All plugin activation/deactivation ultimately updates this cache
2. Cache updates trigger plugin loading on next page load
3. Cache corruption can break plugin loading entirely
4. MCP tools must manipulate cache safely

## Cache Initialization and Loading

### Boot Sequence (init.php)

**Timeline:**
```
1. init.php:162 - Load datacache class
   require_once MYBB_ROOT."inc/class_datacache.php";
   $cache = new datacache;

2. init.php:164 - Load plugin system class
   require_once MYBB_ROOT."inc/class_plugins.php";
   $plugins = new pluginSystem;

3. init.php:182 - Initialize cache handlers and load all caches
   $cache->cache();
   // This loads all datacache entries from database
   // Including the 'plugins' cache

4. init.php:262-265 - Load plugins if not disabled
   if(!defined("NO_PLUGINS") && !($mybb->settings['no_plugins'] == 1))
   {
       $plugins->load();  // Reads $cache->read("plugins")
   }
```

### Cache Initialization Function (class_datacache.php:74-141)

```php
function cache()
{
    global $db, $mybb;

    // Load cache handler (file, memcache, redis, etc.)
    // ... handler initialization code ...

    if($this->handler instanceof CacheHandlerInterface)
    {
        if(!$this->handler->connect())
        {
            $this->handler = null;
        }
    }
    else
    {
        // Fallback to database cache
        $query = $db->simple_select("datacache", "title,cache");
        while($data = $db->fetch_array($query))
        {
            // Store in memory: $this->cache[$title] = unserialized_data
            $this->cache[$data['title']] = native_unserialize($data['cache']);
        }
    }
}
```

**Key Insight:** Caching has two paths:
1. **External cache handlers** (memcache, redis, files) - fast, distributed
2. **Database fallback** - uses `mybb_datacache` table

For plugin-theme-manager (likely using database cache in dev), the `plugins` entry is deserialized from `mybb_datacache.cache` column.

## Plugin Cache Structure

### Reading Plugin Cache

**From hello.php admin activation (admin plugins.php:404-405):**
```php
$plugins_cache = $cache->read("plugins");
$active_plugins = isset($plugins_cache['active']) ? $plugins_cache['active'] : array();
```

**Structure:**
```php
$plugins_cache = array(
    'active' => array(
        'codename1' => 'codename1',
        'codename2' => 'codename2',
        // ... more active plugins ...
    )
    // Potentially other keys for future use
);
```

### Active Plugins Array

**Key Points:**
- Array keys and values are identical: `'hello' => 'hello'`
- Each activated plugin has one entry
- Plugin is activated if and only if present in this array
- Order in array does NOT matter for loading (no priority)

### Plugin Loading Check (class_plugins.php:27-42)

```php
function load()
{
    global $cache, $plugins;

    // READ cache
    $plugin_list = $cache->read("plugins");

    // Check if active plugins exist
    if(!empty($plugin_list['active']) && is_array($plugin_list['active']))
    {
        // ITERATE and load each
        foreach($plugin_list['active'] as $plugin)
        {
            if($plugin != "" && file_exists(MYBB_ROOT."inc/plugins/".$plugin.".php"))
            {
                require_once MYBB_ROOT."inc/plugins/".$plugin.".php";
            }
        }
    }
}
```

**Loading Logic:**
1. Read cache entry "plugins"
2. Check if `['active']` key exists and is array
3. For each plugin name in active array:
   - Verify file exists at `/inc/plugins/{codename}.php`
   - If file exists, `require_once` it (executes plugin code, registers hooks)
   - If file doesn't exist, silently skip
4. No error if plugin cache is empty or malformed

## Cache Update Mechanism

### Admin CP Update (admin/modules/config/plugins.php:464-466)

```php
// After executing activate/deactivate lifecycle functions:
$plugins_cache['active'] = $active_plugins;  // Update active array
$cache->update("plugins", $plugins_cache);   // Write cache
```

**Timing:** Cache is updated **after** lifecycle functions execute, **before** redirect

### Cache Update Flow (class_datacache.php)

The `update()` method (not shown in previous research) typically:
1. Serializes the data
2. Updates the database record OR notifies cache handler
3. Clears in-memory cache if needed

**Expected implementation pattern:**
```php
function update($title, $data)
{
    global $db;

    // Serialize data
    $serialized = serialize($data);

    // Update database record
    $db->update_query("datacache", array(
        'cache' => $serialized,
        'dateline' => TIME_NOW
    ), "title='{$db->escape_string($title)}'");

    // Update in-memory copy
    $this->cache[$title] = $data;

    // Notify cache handler if present
    if($this->handler instanceof CacheHandlerInterface)
    {
        $this->handler->update($title, $serialized);
    }
}
```

**UNVERIFIED:** Exact implementation of `update()` method - not yet analyzed in detail

## Database Storage Details

### Datacache Table Structure

**Table:** `mybb_datacache`

**Columns (inferred from usage):**
- `title` (VARCHAR) - Cache key (e.g., "plugins", "settings", "usergroups")
- `cache` (LONGTEXT/MEDIUMTEXT) - Serialized PHP data
- `dateline` (INT) - Timestamp of last update

**Example Record:**
```
title   = 'plugins'
cache   = 'a:1:{s:6:"active";a:2:{s:5:"hello";s:5:"hello";s:12:"hello_banner";s:12:"hello_banner";}}'
dateline = 1642598400
```

**Serialization Format:** PHP serialization
```php
// From above example:
// a:1        = array with 1 element
// s:6:"active" = key "active" (string, 6 chars)
// a:2        = array with 2 elements (active plugins)
// s:5:"hello" = key "hello" (string, 5 chars)
// s:5:"hello" = value "hello" (string, 5 chars)
```

## Cache Consistency and Corruption Risk

### Cache Consistency Guarantee

**Current State:** MyBB has **no transaction protection** for plugin cache updates

**Risk Scenario:**
1. Admin clicks "Activate hello"
2. System executes `hello_activate()`
3. System updates cache: `$plugins_cache['active']['hello'] = 'hello'`
4. `$cache->update()` is called
5. **DATABASE WRITE FAILS** - cache is corrupted, plugin not marked active but files were modified
6. Next page load: plugin files not loaded, templates exist but no hooks to process them

### Serialization Safety

**Risk:** If plugin data contains non-serializable objects, cache update fails

**Example Problem:**
```php
// Bad plugin code in activate():
$plugins_cache['some_object'] = new PDO(...);  // Can't serialize
$cache->update("plugins", $plugins_cache);     // FAILS
```

**Mitigation:** MyBB doesn't expose serialization issues - admin must not put non-serializable data in cache

## Cache Impact on Plugin Lifecycle

### Scenario 1: Plugin Activation

```
User clicks "Activate hello" in Admin CP
    ↓
Admin plugins.php receives POST
    ↓
Load plugin file: require_once inc/plugins/hello.php
    ↓
Execute hello_activate() function
    ↓
Update cache: add 'hello' to plugins['active']
    ↓
Redirect to plugins list
    ↓
NEXT PAGE LOAD:
    ↓
init.php calls $plugins->load()
    ↓
Cache read returns plugins with 'hello' in active
    ↓
hello.php is require_once'd again
    ↓
Hooks are registered again (happens every page load)
```

### Scenario 2: Plugin Deactivation

```
User clicks "Deactivate hello" in Admin CP
    ↓
Admin plugins.php receives POST
    ↓
Load plugin file: require_once inc/plugins/hello.php
    ↓
Execute hello_deactivate() function
    ↓
Remove 'hello' from cache: plugins['active']
    ↓
Update cache
    ↓
Redirect to plugins list
    ↓
NEXT PAGE LOAD:
    ↓
init.php calls $plugins->load()
    ↓
Cache read returns plugins WITHOUT 'hello' in active
    ↓
hello.php is NOT require_once'd
    ↓
Hooks are NOT registered (plugin is invisible)
```

**Critical Insight:** Plugin deactivation works because plugin file is **not loaded** on next page load, so hooks never register

## Cache Reload and Hard Refresh

### Soft Refresh (During Current Request)

**From class_datacache.php:150-158:**
```php
function read($name, $hard=false)
{
    // ...
    if(isset($this->cache[$name]) && $hard == false)
    {
        // Return cached copy (already loaded)
        return $this->cache[$name];
    }
    // ...
}
```

**Default behavior:** Once loaded, cache stays in memory for request duration

### Hard Refresh (Force Database Read)

```php
$cache->read("plugins", $hard=true);  // Force re-read from database/handler
```

**Use case:** When cache was just updated in same request, hard refresh gets latest

### Reload Specific Cache (class_datacache.php:1335-1341)

```php
function reload_plugins()
{
    global $db;

    $query = $db->simple_select("datacache", "title,cache", "title='plugins'");
    $this->update("plugins", my_unserialize($db->fetch_field($query, "cache")));
}
```

**Pattern:** Reload functions read from database and update in-memory cache

## Cache Handlers and Performance

### Handler Types Supported (class_datacache.php:80-122)

MyBB supports multiple cache backends:
- **files** - Disk files (fast, simple)
- **memcache** - Distributed memory (requires Memcache extension)
- **memcached** - Distributed memory (requires Memcached extension)
- **eaccelerator** - PHP opcode caching (deprecated)
- **xcache** - PHP opcode caching (deprecated)
- **apc** - Alternative PHP Cache
- **apcu** - Alternative PHP Cache (user data)
- **redis** - In-memory data store (recommended modern choice)
- **database** (fallback) - Stores in mybb_datacache table

### Default for Development

In TestForum/.env or config.php, likely configured for database cache:
- No special cache configuration
- Falls back to database storage
- Each cache read queries `mybb_datacache` table

**Performance Implication:** For Phase 7, every plugin activation reads/updates database directly

## Cache Invalidation Patterns

### Full Cache Rebuild

**Triggered by:** Admin CP settings changes, plugin updates, etc.

```php
$cache->update("plugins", $plugins_cache);
$cache->update("settings", $settings);
$cache->update("usergroups", $usergroups);
// ... individual cache updates
```

### Partial Cache Update

Most operations only update what changed:
```php
$plugins_cache = $cache->read("plugins");
$plugins_cache['active']['hello'] = 'hello';
$cache->update("plugins", $plugins_cache);
```

**Implication:** Phase 7 tools should follow this pattern: read, modify, write

## Phase 7 Implications

### 1. Must Update Cache After Activation
```python
# Wrong - plugin won't load next page
execute_php_activation(codename)
# Missing: $cache->update("plugins", ...)

# Correct
execute_php_activation(codename)
plugin_cache = read_plugin_cache()
plugin_cache['active'][codename] = codename
update_plugin_cache(plugin_cache)
```

### 2. Cache Must Match Filesystem State
If plugin file is deleted but cache still lists it as active:
- Plugin loads: `if file_exists()` check fails
- Hook registration silently skipped
- No error, but plugin doesn't work

**Mitigation:** Always validate plugin file exists before activating

### 3. Cache Corruption Recovery
If cache becomes corrupted:
- Manually delete `mybb_datacache` record where title='plugins'
- System will create new empty cache
- Or update database directly with valid serialized data

### 4. Transaction Safety Gap
No database transaction wraps activation + cache update:
- If cache write fails, lifecycle functions already executed
- Plugin code changes may persist while cache reflects old state
- **Workaround:** Phase 7 tool should validate cache update success before returning success

## File References

- `class_datacache.php` (lines 74-141, 1335-1341) - Cache initialization and update
- `class_plugins.php` (lines 27-42) - Plugin loading from cache
- `init.php` (lines 162-182, 262-265) - Cache and plugin initialization
- `admin/modules/config/plugins.php` (lines 404-406, 464-466) - Cache reading and updating
- `mybb_datacache` database table - Physical storage

## Recommendations for Phase 7

1. **Always validate cache update success** - don't assume `$cache->update()` worked
2. **Read cache fresh before updating** - don't rely on stale in-memory copy
3. **Verify plugin file exists** before adding to active array
4. **Handle serialization errors** gracefully - malformed cache should fail loudly
5. **Document cache structure** in tool help - explain the `['active']` array format
6. **Add cache validation endpoint** - let admins check cache integrity from MCP

## Open Questions

**UNVERIFIED:** Exact implementation of `$cache->update()` method for database cache backend
- Need to examine what happens if update query fails
- Whether it throws exception or silently fails

**UNVERIFIED:** Whether multiple simultaneous plugin activations can race on cache update
- If two admins activate plugins at exactly same time, which wins?
- Current MyBB likely has race condition here

**UNVERIFIED:** Whether cache handlers (memcache, redis) handle serialization differently
- Probable: handlers store serialized same way as database
- Need to verify no incompatibilities

## Conclusion

The plugin cache is a single serialized array entry in the database that contains the list of active plugins. Phase 7 tools must:
1. Read this cache before making changes
2. Modify the `['active']` array appropriately
3. Write the updated cache back
4. Verify the write succeeded

The cache mechanism is simple and reliable, but lacks transaction safety. Phase 7 should add defensive validation to ensure cache consistency.

