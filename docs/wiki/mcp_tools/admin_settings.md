# Admin & Settings Tools

Tools for managing MyBB settings, cache, and viewing board statistics.

## Overview

These tools provide control over MyBB's configuration system and cache management:

- **Settings Tools (4)** - Get, set, and list MyBB configuration settings
- **Cache Tools (4)** - Manage MyBB's internal cache system
- **Statistics Tools (2)** - View board and forum statistics

---

## Settings Tools

### mybb_setting_get

Get a specific MyBB setting value by name.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | ✓ | - | Setting name (e.g., "boardclosed", "bbname", "contactemail") |

**Returns:**

Markdown-formatted setting details including:
- Setting title and name
- Current value
- Description
- Group ID and display order
- Options code

**Example:**
```
mybb_setting_get(name="bbname")
```

---

### mybb_setting_set

Update a MyBB setting value. Automatically rebuilds the settings cache after update.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | ✓ | - | Setting name to update |
| `value` | string | ✓ | - | New value for the setting |

**Returns:**

Confirmation message.

**Behavior:**
- Automatically rebuilds settings cache after update
- Changes take effect immediately

**Example:**
```
mybb_setting_set(name="boardclosed", value="1")
```

---

### mybb_setting_list

List all MyBB settings, optionally filtered by setting group.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `gid` | int | - | - | Setting group ID to filter by (optional) |

**Returns:**

Markdown table of all settings with columns for name, title, value, and group.

**Example:**
```
# List all settings
mybb_setting_list()

# List settings in a specific group
mybb_setting_list(gid=3)
```

---

### mybb_settinggroup_list

List all MyBB setting groups (categories for organizing settings).

**Parameters:**

None.

**Returns:**

Markdown table of setting group categories with group ID, name, title, and description.

**Example:**
```
mybb_settinggroup_list()
```

---

## Cache Tools

### mybb_cache_read

Read a MyBB cache entry by title.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | ✓ | - | Cache title (e.g., "settings", "plugins", "usergroups", "forums") |

**Returns:**

Serialized PHP cache data.

**Common Cache Titles:**
- `settings` - Board settings
- `plugins` - Active plugins list
- `usergroups` - User groups
- `forums` - Forum structure

**Example:**
```
mybb_cache_read(title="plugins")
```

---

### mybb_cache_rebuild

Rebuild (clear) MyBB cache entries. MyBB regenerates them on next access.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `cache_type` | string | - | `"all"` | Cache type to rebuild (e.g., "settings", "plugins", "usergroups") or "all" for all caches |

**Returns:**

Confirmation message.

**Note:**

MyBB automatically regenerates caches on next access after clearing.

**Example:**
```
# Rebuild all caches
mybb_cache_rebuild()

# Rebuild specific cache
mybb_cache_rebuild(cache_type="settings")
```

---

### mybb_cache_list

List all MyBB cache entries with their titles and sizes.

**Parameters:**

None.

**Returns:**

Markdown table of all cache entries showing cache title and size.

**Example:**
```
mybb_cache_list()
```

---

### mybb_cache_clear

Clear a specific MyBB cache entry or all caches.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | - | - | Optional cache title to clear. Omit to clear all caches. |

**Returns:**

Confirmation message.

**Example:**
```
# Clear all caches
mybb_cache_clear()

# Clear specific cache
mybb_cache_clear(title="forums")
```

---

## Statistics Tools

### mybb_stats_forum

Get forum statistics including total users, threads, posts, and newest member info.

**Parameters:**

None.

**Returns:**

Board statistics including:
- Total users
- Total threads
- Total posts
- Newest member information

**Example:**
```
mybb_stats_forum()
```

---

### mybb_stats_board

Get comprehensive board statistics including forums, users, threads, posts, latest post, and most active forum.

**Parameters:**

None.

**Returns:**

Comprehensive board statistics including:
- Total forums
- Total users
- Total threads
- Total posts
- Latest post information
- Most active forum

**Example:**
```
mybb_stats_board()
```

---

## Common Use Cases

### Managing Board Settings

```
# Check if board is closed
mybb_setting_get(name="boardclosed")

# Close the board
mybb_setting_set(name="boardclosed", value="1")

# View all settings in a group
mybb_settinggroup_list()
mybb_setting_list(gid=1)
```

### Cache Maintenance

```
# View all cached data
mybb_cache_list()

# Clear specific cache after changes
mybb_cache_clear(title="settings")

# Rebuild all caches
mybb_cache_rebuild()
```

### Monitoring Board Activity

```
# Quick forum stats
mybb_stats_forum()

# Comprehensive statistics
mybb_stats_board()
```

---

## See Also

- [Database Tools](database.md) - Direct database queries
- [Search Tools](search.md) - Advanced search capabilities
- [Getting Started](../getting_started/index.md) - Initial setup
