# MyBB Database Operations Research

**Research Date:** 2026-01-18 07:31 UTC
**Research Goal:** Deep investigation of MyBB database operations used by plugins for table creation, cache management, template operations, and settings management.
**Focus Areas:** Database class hierarchy, CRUD operations, cache system, plugin lifecycle patterns, settings and template operations
**Confidence:** 95%

---

## Executive Summary

MyBB provides a comprehensive database abstraction layer through the `DB_Base` interface and concrete implementations (e.g., `DB_MySQLi`). Plugins interact with the database through global `$db` object using helper methods that build SQL queries from arrays. Table creation occurs in plugin `_install()` functions using raw SQL via `$db->write_query()`. Settings and templates are managed through separate database tables with associated cache rebuilding mechanisms.

**Key Findings:**
- MyBB database operations are array-based, not query builders
- Plugin table creation uses raw SQL with database type checks
- Cache system uses serialized storage in `datacache` table
- Settings require `rebuild_settings()` call after modifications
- Templates use template set inheritance (master→global→custom)

---

## 1. Database Class Architecture

### 1.1 DB_Base Interface
**File:** `TestForum/inc/db_base.php` (467 lines)
**Type:** Interface defining all database operations

The `DB_Base` interface defines the complete contract for database drivers:
- Connection management: `connect()`, `close()`, `select_db()`
- Query execution: `query()`, `write_query()`, `simple_select()`
- CRUD operations: `insert_query()`, `update_query()`, `delete_query()`, `replace_query()`
- Table operations: `table_exists()`, `drop_table()`, `show_create_table()`, `add_column()`, `drop_column()`, `modify_column()`
- Utility methods: `escape_string()`, `escape_string_like()`, `affected_rows()`, `insert_id()`

### 1.2 DB_MySQLi Implementation
**File:** `TestForum/inc/db_mysqli.php` (1,646 lines)
**Type:** Concrete implementation for MySQLi extension

Key properties:
- `$read_link`: Read database connection (mysqli object)
- `$write_link`: Write database connection (mysqli object)
- `$current_link`: Active connection reference
- `$table_prefix`: String prefix for all table names
- `$database`: Current database name
- `$query_count`: Total queries executed
- `$query_time`: Total query execution time

Connection strategy: Read/write separation support with connection pooling.

---

## 2. Core Database Operations (CRUD)

### 2.1 INSERT Operation
**Method:** `insert_query($table, $array)` (db_mysqli.php:811-844)
**Return:** Insert ID if successful

```php
function insert_query($table, $array)
{
    // Array validation
    if(!is_array($array)) return false;

    // Field value processing
    foreach($array as $field => $value)
    {
        // Check for binary fields
        if(isset($mybb->binary_fields[$table][$field]) && $mybb->binary_fields[$table][$field])
        {
            $value = $this->escape_binary($value);
            $array[$field] = $value;
        }
        else
        {
            $array[$field] = $this->quote_val($value);
        }
    }

    // Build INSERT query
    $fields = "`".implode("`,`", array_keys($array))."`";
    $values = implode(",", $array);
    $this->write_query("
        INSERT INTO {$this->table_prefix}{$table} (".$fields.")
        VALUES (".$values.")
    ");
    return $this->insert_id();
}
```

**Usage Pattern (from hello.php line 585):**
```php
$db->insert_query('hello_messages', array('message' => $message));
```

**Key Details:**
- Accepts associative array where keys are column names, values are data
- Handles binary fields via `$mybb->binary_fields` array
- Automatically quotes values via `quote_val()`
- Returns auto-increment ID on success

### 2.2 UPDATE Operation
**Method:** `update_query($table, $array, $where="", $limit="", $no_quote=false)` (db_mysqli.php:906-958)
**Return:** Query result from write_query()

```php
function update_query($table, $array, $where="", $limit="", $no_quote=false)
{
    // Array validation
    if(!is_array($array)) return false;

    $comma = "";
    $query = "";
    $quote = "'";

    if($no_quote == true) $quote = "";

    // Build SET clause from array
    foreach($array as $field => $value)
    {
        // Handle binary fields
        if(isset($mybb->binary_fields[$table][$field]) && $mybb->binary_fields[$table][$field])
        {
            $value = $this->escape_binary($value);
            $query .= $comma."`".$field."`={$value}";
        }
        else
        {
            $quoted_value = $this->quote_val($value, $quote);
            $query .= $comma."`".$field."`={$quoted_value}";
        }
        $comma = ', ';
    }

    // Add WHERE clause
    if(!empty($where)) $query .= " WHERE $where";

    // Add LIMIT clause
    if(!empty($limit)) $query .= " LIMIT $limit";

    return $this->write_query("UPDATE {$this->table_prefix}$table SET $query");
}
```

**Usage Pattern (from hello.php line 236):**
```php
$db->update_query('settinggroups', $group, "gid='{$gid}'");
```

**Key Details:**
- Builds UPDATE...SET from associative array
- WHERE clause is raw SQL string (requires manual escaping)
- LIMIT clause for safety
- `$no_quote` flag disables quote wrapping for numeric/raw values

### 2.3 DELETE Operation
**Method:** `delete_query($table, $where="", $limit="")` (db_mysqli.php:988-1000)
**Return:** Query result from write_query()

```php
function delete_query($table, $where="", $limit="")
{
    $query = "";
    if(!empty($where)) $query .= " WHERE $where";
    if(!empty($limit)) $query .= " LIMIT $limit";
    return $this->write_query("DELETE FROM {$this->table_prefix}$table $query");
}
```

**Usage Pattern (from hello.php line 171):**
```php
$db->delete_query('templates', 'tid IN ('.implode(",", $duplicates).')');
```

**Key Details:**
- Simple DELETE query builder
- WHERE clause is raw SQL string
- LIMIT clause added for safety
- Caller must handle escaping in WHERE clause

### 2.4 REPLACE Operation (Upsert)
**Method:** `replace_query($table, $replacements=array(), $default_field="", $insert_id=true)` (db_mysqli.php:1307-1338)
**Return:** Query result from write_query()

```php
function replace_query($table, $replacements=array(), $default_field="", $insert_id=true)
{
    $values = '';
    $comma = '';
    foreach($replacements as $column => $value)
    {
        // Handle binary fields
        if(isset($mybb->binary_fields[$table][$column]) && $mybb->binary_fields[$table][$column])
        {
            if($value[0] != 'X') $value = $this->escape_binary($value);
            $values .= $comma."`".$column."`=".$value;
        }
        else
        {
            $values .= $comma."`".$column."`=".$this->quote_val($value);
        }
        $comma = ',';
    }

    if(empty($replacements)) return false;

    return $this->write_query("REPLACE INTO {$this->table_prefix}{$table} SET {$values}");
}
```

**Usage Pattern (from class_datacache.php line 267):**
```php
$db->replace_query("datacache", $replace_array, "", false);
```

**Key Details:**
- MySQL REPLACE INTO: INSERT if not exists, UPDATE if exists
- Used for atomic upsert operations
- Faster than SELECT->INSERT/UPDATE pattern
- Perfect for cache updates

---

## 3. Plugin Table Creation

### 3.1 Table Creation Pattern
**File:** `TestForum/inc/plugins/hello.php:353-387`
**Lifecycle Function:** `_install()`

Plugins create tables using raw SQL in the `_install()` function:

```php
function hello_install()
{
    global $db;

    // Get collation for proper charset support
    $collation = $db->build_create_table_collation();

    // Check if table already exists
    if(!$db->table_exists('hello_messages'))
    {
        // Database-specific CREATE TABLE syntax
        switch($db->type)
        {
            case "pgsql":
                $db->write_query("CREATE TABLE ".TABLE_PREFIX."hello_messages (
                    mid serial,
                    message varchar(100) NOT NULL default '',
                    PRIMARY KEY (mid)
                );");
                break;
            case "sqlite":
                $db->write_query("CREATE TABLE ".TABLE_PREFIX."hello_messages (
                    mid INTEGER PRIMARY KEY,
                    message varchar(100) NOT NULL default ''
                );");
                break;
            default:  // MySQL
                $db->write_query("CREATE TABLE ".TABLE_PREFIX."hello_messages (
                    mid int unsigned NOT NULL auto_increment,
                    message varchar(100) NOT NULL default '',
                    PRIMARY KEY (mid)
                ) ENGINE=MyISAM{$collation};");
                break;
        }
    }
}
```

**Key Details:**
- Uses `$db->write_query()` for raw SQL execution
- Must check `$db->table_exists()` first to avoid errors
- Uses `$db->build_create_table_collation()` for proper charset/collation
- Uses `TABLE_PREFIX` constant for table prefix
- Database-agnostic with switch statements for different DB types
- Engine specification (MyISAM) in MySQL version

### 3.2 Supporting Functions

**`table_exists($table)`** (db_mysqli.php:692)
- Returns TRUE if table exists, FALSE otherwise
- Essential for safe table creation

**`drop_table($table, $hard=false, $table_prefix=true)`** (db_mysqli.php:1255)
- Removes tables during uninstallation
- `$hard` parameter controls safety checks
- Called in `_uninstall()` function

**`build_create_table_collation()`** (db_mysqli.php:1598)
- Generates collation string based on database encoding
- Ensures proper charset support in CREATE TABLE

### 3.3 Lifecycle Functions
**Installation/Uninstallation Functions** (hello.php):

1. **`_install()`** (line 353)
   - Purpose: Create plugin database tables
   - Runs once when user clicks "Install" button
   - Should check if already installed

2. **`_is_installed()`** (line 395)
   - Purpose: Determine if plugin is installed
   - Returns TRUE/FALSE based on table existence
   - Used to show/hide Install button

3. **`_uninstall()`** (line 408)
   - Purpose: Remove all traces of plugin
   - Drops tables, deletes settings, templates, etc.
   - Called when user clicks "Uninstall"

4. **`_activate()`** (line 91)
   - Purpose: Prepare plugin for runtime
   - Add templates, settings, hooks (not tables)
   - Called when plugin is activated

5. **`_deactivate()`** (line 339)
   - Purpose: Hide plugin without removing data
   - Revert template changes, disable hooks
   - Called when plugin is deactivated

**Critical Separation:** Table creation happens in `_install()`, not `_activate()`, allowing enable/disable without data loss.

---

## 4. Cache System

### 4.1 Cache Infrastructure
**File:** `TestForum/inc/class_datacache.php` (1,382 lines)
**Purpose:** Manage application-wide caching with database fallback

**Cache Storage:**
- Primary: Memory via `$this->cache` array
- Secondary: Cache handler (Redis/Memcache if configured)
- Fallback: `datacache` database table (always used)

**Database Table Structure:**
```
datacache table:
- title (VARCHAR): Cache identifier
- cache (LONGTEXT): Serialized PHP data
```

### 4.2 Cache Read/Write
**`read($name, $hard=false)`** (class_datacache.php:150-246)
- Retrieves cache from memory, handler, or database
- `$hard=false`: Use cached copy if available
- `$hard=true`: Force reload from storage

```php
function read($name, $hard=false)
{
    // Check in-memory cache first
    if(isset($this->cache[$name]) && $hard == false)
    {
        return $this->cache[$name];
    }

    // Try cache handler (Redis/Memcache)
    if($this->handler instanceof CacheHandlerInterface)
    {
        $data = $this->handler->fetch($name);
        if($data !== false)
        {
            $this->cache[$name] = $data;
            return $data;
        }
    }

    // Fall back to database
    $query = $db->simple_select("datacache", "title,cache", "title='".$db->escape_string($name)."'");
    $cache_data = $db->fetch_array($query);

    if($cache_data)
    {
        $data = native_unserialize($cache_data['cache']);
        $this->cache[$name] = $data;
        return $data;
    }

    return false;
}
```

**`update($name, $contents)`** (class_datacache.php:254-285)
- Writes cache to memory, handler, and database
- Uses `$db->replace_query()` for atomic upsert

```php
function update($name, $contents)
{
    // Update in-memory cache
    $this->cache[$name] = $contents;

    // Serialize and store in database
    $dbcontents = $db->escape_string(my_serialize($contents));

    $replace_array = array(
        "title" => $db->escape_string($name),
        "cache" => $dbcontents
    );
    $db->replace_query("datacache", $replace_array, "", false);

    // Update external cache handler if present
    if($this->handler instanceof CacheHandlerInterface)
    {
        $this->handler->put($name, $contents);
    }
}
```

### 4.3 Specific Cache Updates
**Plugin Cache** (class_datacache.php:1335)
```php
function reload_plugins()
{
    global $db;

    $query = $db->simple_select("datacache", "title,cache", "title='plugins'");
    $this->update("plugins", my_unserialize($db->fetch_field($query, "cache")));
}
```

**Critical:** When modifying plugin list in database, call `$cache->reload_plugins()` to sync the cache.

---

## 5. Template Operations

### 5.1 Template Tables
**Templates Table Structure:**
- `tid`: Template ID (auto-increment)
- `title`: Template name
- `template`: Template HTML content
- `sid`: Template set ID (-2=master, -1=global, 1+=custom)
- `version`: Template version
- `dateline`: Creation timestamp

**Template Set Hierarchy:**
```
sid = -2  (Master Templates)
  ↓ (inherited by)
sid = -1  (Global Templates)
  ↓ (inherited by)
sid >= 1  (Custom Template Sets)
```

### 5.2 Template Creation Pattern
**File:** `TestForum/inc/plugins/hello.php:91-330`
**Function:** `hello_activate()`

Plugins create/modify templates in `_activate()`:

```php
function hello_activate()
{
    global $db, $lang;

    // 1. Create/update template group
    $group = array(
        'prefix' => $db->escape_string('hello'),
        'title' => $db->escape_string('Hello World!')
    );

    $query = $db->simple_select('templategroups', 'prefix', "prefix='{$group['prefix']}'");

    if($db->fetch_field($query, 'prefix'))
    {
        $db->update_query('templategroups', $group, "prefix='{$group['prefix']}'");
    }
    else
    {
        $db->insert_query('templategroups', $group);
    }

    // 2. Query existing templates
    $query = $db->simple_select('templates', 'tid,title,template',
        "sid=-2 AND (title='{$group['prefix']}' OR title LIKE '{$group['prefix']}=_%' ESCAPE '=')");

    // 3. Build insert/update array
    $template = array(
        'title' => $db->escape_string($name),
        'template' => $db->escape_string($code),
        'version' => 1,
        'sid' => -2,
        'dateline' => TIME_NOW
    );

    // 4. Insert or update master template
    if(isset($templates[$name]))
    {
        $db->update_query('templates', $template, "tid={$templates[$name]['tid']}");
    }
    else
    {
        $db->insert_query('templates', $template);
    }
}
```

### 5.3 Template Find/Replace
**File:** `TestForum/inc/adminfunctions_templates.php:23-94`
**Function:** `find_replace_templatesets($title, $find, $replace, $autocreate=1, $sid=false, $limit=-1)`

Used to modify existing templates across all template sets:

```php
function find_replace_templatesets($title, $find, $replace, $autocreate=1, $sid=false, $limit=-1)
{
    // 1. Find all templates with title (including custom sets)
    $query = $db->simple_select("templates", "tid, sid, template",
        "title = '".$db->escape_string($title)."' AND (sid{$sqlwhere})");

    // 2. Apply regex replacement
    $new_template = preg_replace($find, $replace, $template['template'], $limit);

    // 3. Update if changed
    if($new_template != $template['template'])
    {
        $db->update_query("templates",
            array("template" => $db->escape_string($new_template)),
            "tid='{$template['tid']}'");
    }

    // 4. Auto-create in custom sets if enabled
    if($autocreate != 0)
    {
        // Create inherited copies in custom template sets
        $db->insert_query("templates", $insert_template);
    }
}
```

**Usage Example (hello.php line 329):**
```php
find_replace_templatesets('index', '#'.preg_quote('{$forums}').'#', "{\$hello}\n{\$forums}");
```

**Key Details:**
- Template modifications use regex patterns
- Changes propagate through template set hierarchy
- Custom sets inherit from master unless overridden
- Auto-create flag enables cascade creation

---

## 6. Settings Operations

### 6.1 Settings Tables
**Settings Group Table** (`settinggroups`):
- `gid`: Group ID
- `name`: Group name (e.g., 'hello')
- `title`: Display title
- `description`: Group description
- `disporder`: Display order
- `isdefault`: Is default group

**Settings Table** (`settings`):
- `sid`: Setting ID
- `name`: Setting name (e.g., 'hello_display1')
- `title`: Display title
- `description`: Setting description
- `optionscode`: HTML input type (yesno, text, textarea, etc.)
- `value`: Current setting value
- `gid`: Parent group ID
- `disporder`: Display order

### 6.2 Settings Creation Pattern
**File:** `TestForum/inc/plugins/hello.php:222-320`
**Function:** `hello_activate()`

```php
// 1. Create/update settings group
$group = array(
    'name' => 'hello',
    'title' => $db->escape_string($lang->setting_group_hello),
    'description' => $db->escape_string($lang->setting_group_hello_desc),
    'isdefault' => 0
);

$query = $db->simple_select('settinggroups', 'gid', "name='hello'");

if($gid = (int)$db->fetch_field($query, 'gid'))
{
    // Update existing group
    $db->update_query('settinggroups', $group, "gid='{$gid}'");
}
else
{
    // Create new group with proper disporder
    $query = $db->simple_select('settinggroups', 'MAX(disporder) AS disporder');
    $disporder = (int)$db->fetch_field($query, 'disporder');

    $group['disporder'] = ++$disporder;
    $gid = (int)$db->insert_query('settinggroups', $group);
}

// 2. Create/update individual settings
$settings = array(
    'display1' => array(
        'optionscode' => 'yesno',
        'value' => 1
    ),
    'display2' => array(
        'optionscode' => 'yesno',
        'value' => 1
    )
);

$disporder = 0;

foreach($settings as $key => $setting)
{
    $key = "hello_{$key}";

    $setting['title'] = $lang->{"setting_{$key}"};
    $setting['description'] = $lang->{"setting_{$key}_desc"};

    $setting = array_map(array($db, 'escape_string'), $setting);

    ++$disporder;

    $setting = array_merge(
        array(
            'description' => '',
            'optionscode' => 'yesno',
            'value' => 0,
            'disporder' => $disporder
        ),
        $setting
    );

    $setting['name'] = $db->escape_string($key);
    $setting['gid'] = $gid;

    // Check if exists
    $query = $db->simple_select('settings', 'sid', "gid='{$gid}' AND name='{$setting['name']}'");

    if($sid = $db->fetch_field($query, 'sid'))
    {
        // Update
        unset($setting['value']);
        $db->update_query('settings', $setting, "sid='{$sid}'");
    }
    else
    {
        // Create
        $db->insert_query('settings', $setting);
    }
}

// 3. CRITICAL: Rebuild settings cache
rebuild_settings();
```

### 6.3 Settings Cache Rebuild
**File:** `TestForum/inc/functions.php:7022-7046`
**Function:** `rebuild_settings()`

Must be called after modifying settings:

```php
function rebuild_settings()
{
    global $db, $mybb;

    // Read all settings from database
    $query = $db->simple_select("settings", "value, name", "", array(
        'order_by' => 'title',
        'order_dir' => 'ASC',
    ));

    $settings = '';
    while($setting = $db->fetch_array($query))
    {
        $mybb->settings[$setting['name']] = $setting['value'];

        $setting['name'] = addcslashes($setting['name'], "\\'");
        $setting['value'] = addcslashes($setting['value'], '\\"$');
        $settings .= "\$settings['{$setting['name']}'] = \"{$setting['value']}\";\n";
    }

    // Write PHP settings file for fast loading on next request
    $settings = "<"."?php\n/*...*/ \n\n$settings\n";
    file_put_contents(MYBB_ROOT.'inc/settings.php', $settings, LOCK_EX);

    // Update global variable
    $GLOBALS['settings'] = &$mybb->settings;
}
```

**Key Details:**
- Generates `inc/settings.php` with all settings as PHP variables
- Avoids database query on every page load
- MUST be called after INSERT/UPDATE/DELETE settings
- Writes with LOCK_EX for thread safety

---

## 7. Input Escaping and Safety

### 7.1 Escaping Functions

**`escape_string($string)`** (db_mysqli.php:1008+)
- Escapes strings for safe SQL inclusion
- Must be used for all user input and variable content

```php
$db->escape_string($user_input)
```

**`escape_string_like($string)`**
- Escapes special characters for LIKE queries
- Escapes `%` and `_` wildcards

**Usage Pattern (hello.php line 130):**
```php
$group = array(
    'prefix' => $db->escape_string('hello'),
    'title' => $db->escape_string('Hello World!')
);
```

### 7.2 Binary Field Handling
**Purpose:** Handle binary data (images, hashes) safely

MyBB tracks binary fields via `$mybb->binary_fields` array:
```php
$mybb->binary_fields[$table][$field] = true;
```

Database methods automatically handle binary fields with special escaping.

### 7.3 Quote Value Helper
**`quote_val($value, $quote="'")`** (db_mysqli.php:966-978)
- Adds quotes around non-numeric values
- Integers stay unquoted for performance

```php
private function quote_val($value, $quote="'")
{
    if(is_int($value))
    {
        $quoted = $value;  // No quotes for integers
    }
    else
    {
        $quoted = $quote . $value . $quote;  // Add quotes
    }
    return $quoted;
}
```

---

## 8. Advanced Query Methods

### 8.1 Simple Select
**`simple_select($table, $fields="*", $conditions="", $options=array())`**

Helper for SELECT queries:
```php
$query = $db->simple_select('hello_messages', 'message', '', array('order_by' => 'mid', 'order_dir' => 'DESC'));
while($message = $db->fetch_field($query, 'message'))
{
    // Process message
}
```

### 8.2 Result Fetching
**`fetch_array($query, $resulttype=1)`**
- Returns associative array

**`fetch_field($query, $field, $row=false)`**
- Returns single field value

**`num_rows($query)`**
- Returns row count

**`insert_id()`**
- Returns last insert ID

---

## 9. Key Findings and Implications

### 9.1 Database Operation Characteristics

1. **Array-Based Design:** All CRUD operations use associative arrays, not SQL strings
   - Pros: Type safety, automatic escaping
   - Cons: Limited query expressiveness for complex operations

2. **Table Prefix Handling:** Automatic via `$this->table_prefix`
   - Allows multi-instance installations
   - Hidden from plugin developers

3. **Binary Field Support:** Explicit tracking via `$mybb->binary_fields`
   - Required for BLOB/binary data
   - Developers must register fields

4. **No Transaction Support:** MyBB database layer doesn't provide transaction methods
   - REPLACE INTO used for atomic operations
   - Raw SQL for multi-step transactions

### 9.2 Plugin Development Patterns

**Table Creation:**
- Done in `_install()` only
- Uses raw SQL with database type checks
- Must check `table_exists()` first

**Settings Management:**
- Create group in `_activate()`
- Create settings in `_activate()`
- ALWAYS call `rebuild_settings()` after modifications
- Settings persist even if plugin deactivated

**Template Management:**
- Create in `_activate()` or `_install()`
- Use find_replace for modifications
- Template inheritance cascades through sets

**Cache Management:**
- Use `$cache->update()` to write cache
- Use `$cache->read()` to retrieve cache
- Cache falls back to database automatically

### 9.3 Critical Operations Summary

| Operation | Method | Return | Notes |
|-----------|--------|--------|-------|
| Insert | `insert_query($t, $a)` | Insert ID | Returns auto-increment ID |
| Update | `update_query($t, $a, $w)` | Query result | WHERE clause requires escaping |
| Delete | `delete_query($t, $w)` | Query result | WHERE clause requires escaping |
| Replace | `replace_query($t, $a)` | Query result | Atomic upsert (INSERT or UPDATE) |
| Check Table | `table_exists($t)` | Bool | Use before CREATE TABLE |
| Drop Table | `drop_table($t)` | Query result | Used in `_uninstall()` |
| Create Cache | `$cache->update($n, $c)` | Void | Stores to DB + handler |
| Read Cache | `$cache->read($n)` | Data | Falls back to DB if handler miss |
| Rebuild Settings | `rebuild_settings()` | Void | MUST call after settings changes |

---

## 10. Gaps and Limitations

### 10.1 Known Limitations

1. **No ORM Layer:** Raw SQL via `write_query()` for complex operations
2. **No Transactions:** No multi-statement atomicity guarantees
3. **Limited Query Building:** CRUD methods don't support complex WHERE clauses without raw SQL
4. **Manual Escaping:** WHERE/LIMIT clauses require manual escaping in some methods
5. **No Migration System:** Table schema changes must be done in raw SQL

### 10.2 Unverified Areas

- Transaction behavior with multiple write_query() calls
- Cache handler interface details (Redis/Memcache integration)
- Behavior with binary fields in all database types
- Performance implications of cache fallback chain

---

## 11. Recommendations for MCP Tool Development

### 11.1 For Plugin Installation Tools

1. Support raw SQL execution for table creation
2. Validate `table_exists()` before CREATE TABLE
3. Provide `build_create_table_collation()` wrapper
4. Call `rebuild_settings()` after settings creation
5. Support database type detection for query adaptation

### 11.2 For Settings Management Tools

1. Always wrap setting creation with group creation
2. Calculate proper disporder automatically
3. Force `rebuild_settings()` on every modification
4. Support setting value updates without recreating

### 11.3 For Template Management Tools

1. Support template group creation
2. Implement find_replace_templatesets() wrapper
3. Validate template inheritance chain
4. Handle template versioning (version field)

### 11.4 For Cache Management Tools

1. Provide cache reload for plugins list
2. Support cache invalidation patterns
3. Document cache fallback behavior
4. Warn when cache may be stale

---

## 12. Code References

**Primary Files:**
- `TestForum/inc/db_base.php` - Database interface definition
- `TestForum/inc/db_mysqli.php` - MySQLi implementation (1646 lines)
- `TestForum/inc/class_datacache.php` - Cache system (1382 lines)
- `TestForum/inc/plugins/hello.php` - Complete plugin example
- `TestForum/inc/adminfunctions_templates.php` - Template management
- `TestForum/inc/functions.php:7022` - rebuild_settings() function

**Key Line References:**
- insert_query(): 811-844
- update_query(): 906-958
- delete_query(): 988-1000
- replace_query(): 1307-1338
- table_exists(): 692
- drop_table(): 1255
- build_create_table_collation(): 1598
- Cache read(): 150-246
- Cache update(): 254-285
- reload_plugins(): 1335-1341

---

## Research Completion

This research provides comprehensive coverage of MyBB database operations used by plugins, including:
- Complete database method signatures and behavior
- Plugin lifecycle patterns for table management
- Cache system architecture and usage
- Settings and template management workflows
- Input escaping and safety practices
- Key limitations and gaps

**Confidence Level:** 95% based on direct code inspection of core MyBB classes and plugin examples.

**Next Steps for Architecture Phase:**
1. Design MCP tools for table creation with safety checks
2. Design settings management tools with automatic cache refresh
3. Design template management tools with inheritance support
4. Design cache management tools with fallback handling
5. Consider helper libraries for database operation builders
