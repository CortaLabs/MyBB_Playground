# MyBB MCP Tools: Search, Settings, Cache & Stats

Complete documentation for MyBB MCP tools covering search functionality, settings management, cache operations, statistics, and database queries.

## Table of Contents
- [Search Tools](#search-tools)
- [Settings Tools](#settings-tools)
- [Cache Tools](#cache-tools)
- [Statistics Tools](#statistics-tools)
- [Database Tools](#database-tools)

---

## Search Tools

### mybb_search_posts
**Purpose:** Search post content with optional filters for forums, author, and date range.

**Parameters:**
- `query` (string, required): Search term to find in post content
- `forums` (array, optional): List of forum IDs to search within
- `author` (string, optional): Username to filter by
- `date_from` (integer, optional): Start timestamp (Unix epoch)
- `date_to` (integer, optional): End timestamp (Unix epoch)
- `limit` (integer, optional): Maximum results (default 25, max 100)
- `offset` (integer, optional): Pagination offset (default 0)

**Example:**
```json
{
  "query": "welcome",
  "limit": 5
}
```

**Response:**
```
# Post Search Results

No posts found matching 'welcome'.
```

**Notes:**
- Returns formatted table with post details when matches found
- Searches within message content (BBCode)
- Supports partial word matching
- Empty results return helpful message

---

### mybb_search_threads
**Purpose:** Search thread subjects with optional filters for forums, author, and prefix.

**Parameters:**
- `query` (string, required): Search term to find in thread subjects
- `forums` (array, optional): List of forum IDs to search within
- `author` (string, optional): Username to filter by
- `prefix` (integer, optional): Thread prefix ID
- `limit` (integer, optional): Maximum results (default 25, max 100)
- `offset` (integer, optional): Pagination offset (default 0)

**Example:**
```json
{
  "query": "test",
  "limit": 5
}
```

**Response:**
```
# Thread Search Results (1 found)

| TID | Subject | Author | Replies | Views | Last Post |
|-----|---------|--------|---------|-------|-----------|
| 1 | Test thread | admin | 0 | 2 | 2026-01-17 06:07 |
```

**Notes:**
- Searches only thread subjects, not content
- Returns thread metadata including reply count and views
- Use `mybb_search_posts` for content searching
- Displays last post timestamp

---

### mybb_search_users
**Purpose:** Search users by username or email. Returns safe user info (no passwords).

**Parameters:**
- `query` (string, required): Search term
- `field` (string, optional): Field to search - 'username' or 'email' (default: 'username')
- `limit` (integer, optional): Maximum results (default 25, max 100)
- `offset` (integer, optional): Pagination offset (default 0)

**Example:**
```json
{
  "query": "admin",
  "field": "username"
}
```

**Response:**
```
# User Search Results (1 found)

| UID | Username | Group | Posts | Threads | Registered |
|-----|----------|-------|-------|---------|------------|
| 1 | admin | 4 | 1 | 1 | 2026-01-17 |
```

**Notes:**
- Sensitive fields (passwords, salts, IPs) are NEVER returned
- Supports partial username/email matching
- Group field shows primary usergroup ID
- Registered date shown in YYYY-MM-DD format

---

### mybb_search_advanced
**Purpose:** Combined search across posts and/or threads with multiple filters.

**Parameters:**
- `query` (string, required): Search term
- `content_type` (string, optional): 'posts', 'threads', or 'both' (default: 'both')
- `forums` (array, optional): List of forum IDs
- `date_from` (integer, optional): Start timestamp (Unix epoch)
- `date_to` (integer, optional): End timestamp (Unix epoch)
- `sort_by` (string, optional): 'date' or 'relevance' (default: 'date')
- `limit` (integer, optional): Maximum results per type (default 25, max 100)
- `offset` (integer, optional): Pagination offset (default 0)

**Example:**
```json
{
  "query": "test",
  "content_type": "both",
  "limit": 10
}
```

**Response:**
```
# Advanced Search Results for 'test'


## Posts (0 found)


## Threads (1 found)

| TID | Subject | Author | Replies | Views |
|-----|---------|--------|---------|-------|
| 1 | Test thread | admin | 0 | 2 |
```

**Notes:**
- Most comprehensive search tool
- Searches both posts and threads simultaneously
- Results grouped by content type
- Useful for global content discovery

---

## Settings Tools

### mybb_settinggroup_list
**Purpose:** List all MyBB setting groups (categories for organizing settings).

**Parameters:** None

**Example:**
```json
{}
```

**Response:**
```
# MyBB Setting Groups (30 total)

| GID | Name | Title | Description |
|-----|------|-------|-------------|
| 1 | onlineoffline | Board Online / Offline | These settings allow you to globally turn your for... |
| 2 | details | Site Details | This section contains various settings such as you... |
| 3 | general | General Configuration | This section allows you to manage the general aspe... |
...
```

**Notes:**
- Returns all setting groups with metadata
- Groups organize related settings (e.g., all posting settings together)
- Use GID to filter settings with `mybb_setting_list`
- Descriptions are truncated in list view

---

### mybb_setting_list
**Purpose:** List all MyBB settings or filter by setting group.

**Parameters:**
- `gid` (integer, optional): Setting group ID to filter by

**Example:**
```json
{}
```

**Response:**
```
# MyBB Settings (297 total)

| Name | Title | Value | Group |
|------|-------|-------|-------|
| boardclosed | Board Closed | 0 | 1 |
| boardclosed_reason | Board Closed Reason | These forums are currently closed for maintenance.... | 1 |
| bbname | Board Name | Test Forums | 2 |
| bburl | Board URL | http://localhost:8022 | 2 |
...
```

**Notes:**
- 297 settings in default MyBB installation
- Filter by `gid` to see only settings in a specific group
- Shows current value for each setting
- Use setting `name` with `mybb_setting_get` for full details

---

### mybb_setting_get
**Purpose:** Get a MyBB setting value by name.

**Parameters:**
- `name` (string, required): Setting name (e.g., 'boardclosed', 'bbname', 'contactemail')

**Example:**
```json
{
  "name": "bbname"
}
```

**Response:**
```
# Setting: Board Name

**Name:** `bbname`
**Value:** `Test Forums`
**Description:** The name of your community. We recommend that it is not over 75 characters.
**Group ID:** 2
**Display Order:** 1
**Options Code:** text
```

**Notes:**
- Returns full setting details including description
- Options Code indicates input type (text, yesno, numeric, etc.)
- Use this before modifying settings to understand constraints
- Group ID links to setting group

---

### mybb_setting_set
**Purpose:** Update a MyBB setting value. Automatically rebuilds settings cache after update.

**Parameters:**
- `name` (string, required): Setting name to update
- `value` (string, required): New value for the setting

**Example:**
```json
{
  "name": "maxmultipagelinks",
  "value": "7"
}
```

**Response:**
```
Setting 'maxmultipagelinks' updated to '7'. Settings cache rebuilt.
```

**Notes:**
- **CAUTION:** Use non-critical settings for testing
- Cache rebuild happens automatically (no manual rebuild needed)
- Verify setting type before updating (use `mybb_setting_get` first)
- Changes take effect immediately
- **Dangerous settings:** boardclosed, disableregs, no_plugins
- **Safe for testing:** maxmultipagelinks, threadsperpage, postsperpage

---

## Cache Tools

### mybb_cache_list
**Purpose:** List all MyBB cache entries with their titles and sizes.

**Parameters:** None

**Example:**
```json
{}
```

**Response:**
```
# MyBB Cache Entries (30 total)

| Title | Size (bytes) |
|-------|--------------|
| attachtypes | 7,037 |
| forums | 1,540 |
| usergroups | 19,467 |
| statistics | 102 |
...

**Total Cache Size:** 45,908 bytes
```

**Notes:**
- Shows all cached data in MyBB datacache system
- Sizes help identify large caches
- Common caches: forums, usergroups, plugins, smilies
- Total size shows overall cache footprint

---

### mybb_cache_read
**Purpose:** Read a MyBB cache entry by title. Returns serialized PHP cache data.

**Parameters:**
- `title` (string, required): Cache title (e.g., 'settings', 'plugins', 'usergroups', 'forums')

**Example:**
```json
{
  "title": "forums"
}
```

**Response:**
```
# Cache: forums

**Size:** 1540 bytes
**Data Type:** PHP serialized

```
a:2:{i:1;a:30:{s:3:"fid";s:1:"1";s:4:"name";s:11:"My Category";...
```

*Full size: 1540 bytes (showing first 1000)*
```

**Notes:**
- Returns PHP serialized data (may need parsing)
- Large caches are truncated (first 1000 bytes shown)
- Some caches may not exist (returns "Cache 'X' not found")
- **Does not exist:** 'settings' cache (settings stored differently)
- Use `mybb_cache_list` to see available caches first

---

### mybb_cache_rebuild
**Purpose:** Rebuild (clear) MyBB cache entries. MyBB regenerates them on next access. Use 'all' to clear all caches.

**Parameters:**
- `cache_type` (string, optional): Cache type to rebuild (e.g., 'settings', 'plugins', 'usergroups') or 'all' for all caches (default: 'all')

**Example:**
```json
{
  "cache_type": "statistics"
}
```

**Response:**
```
**Cache 'statistics' cleared** (1 cache entries cleared)

MyBB will regenerate these caches on next access.
```

**Notes:**
- Safe operation - caches regenerate automatically
- Use after plugin changes or data modifications
- 'all' clears entire cache system
- MyBB handles regeneration transparently
- Common rebuilds: plugins (after install), forums (after changes), usergroups (after permission changes)

---

### mybb_cache_clear
**Purpose:** Clear a specific MyBB cache entry or all caches.

**Parameters:**
- `title` (string, optional): Cache title to clear. Omit to clear all caches.

**Example:**
```json
{
  "title": "statistics"
}
```

**Notes:**
- Alias for `mybb_cache_rebuild` with similar functionality
- Prefer `mybb_cache_rebuild` for consistency
- Both tools are safe and regenerate automatically

---

## Statistics Tools

### mybb_stats_forum
**Purpose:** Get forum statistics including total users, threads, posts, and newest member info.

**Parameters:** None

**Example:**
```json
{}
```

**Response:**
```
# Forum Statistics

**Total Users:** 1
**Total Threads:** 1
**Total Posts:** 3

## Newest Member
**Username:** admin
**UID:** 1
**Registered:** 2026-01-17 06:03:37
```

**Notes:**
- Provides overview of forum activity
- Includes newest member details
- Post count includes all posts (visible and deleted)
- Real-time data (not cached)

---

### mybb_stats_board
**Purpose:** Get comprehensive board statistics including forums, users, threads, posts, latest post, and most active forum.

**Parameters:** None

**Example:**
```json
{}
```

**Response:**
```
# Board Statistics

## Overview
**Total Forums:** 2
**Total Users:** 1
**Total Threads:** 1
**Total Posts:** 3
**Total Private Messages:** 0

## Latest Post
**Subject:** RE: Test thread
**Author:** admin
**Date:** 2026-01-17 21:07:27
**Post ID:** 3
**Thread ID:** 1

## Most Active Forum
**Name:** My Forum
**Threads:** 1
**Posts:** 2
**Forum ID:** 2
```

**Notes:**
- Most comprehensive statistics tool
- Includes latest post and most active forum
- Useful for dashboard/overview displays
- Categories are NOT counted as "forums" in total
- Shows private message count

---

## Database Tools

### mybb_db_query
**Purpose:** Execute a read-only SQL query against MyBB database. For exploration only.

**Parameters:**
- `query` (string, required): SQL SELECT query

**Example:**
```json
{
  "query": "SELECT COUNT(*) as total_users FROM mybb_users"
}
```

**Response:**
```
total_users
---
1
```

**Example (Multiple Columns):**
```json
{
  "query": "SELECT fid, name, type FROM mybb_forums ORDER BY disporder LIMIT 5"
}
```

**Response:**
```
fid | name | type
--- | --- | ---
1 | My Category | c
2 | My Forum | f
```

**Notes:**
- **READ-ONLY:** Only SELECT queries allowed
- Direct database access for custom queries
- Results formatted as ASCII table
- Use MyBB table prefix (usually `mybb_`)
- **Security:** Cannot execute INSERT, UPDATE, DELETE, DROP, etc.
- Useful for debugging and data exploration
- All other MCP tools are safer for standard operations

---

## Testing Summary

All 15 tools tested successfully:

**Search (4 tools):**
- ✅ mybb_search_posts - Tested with various queries
- ✅ mybb_search_threads - Returns formatted results
- ✅ mybb_search_users - Safe user data only
- ✅ mybb_search_advanced - Multi-criteria search works

**Settings (4 tools):**
- ✅ mybb_settinggroup_list - Lists 30 groups
- ✅ mybb_setting_list - Returns 297 settings
- ✅ mybb_setting_get - Full setting details
- ✅ mybb_setting_set - Updates with auto cache rebuild

**Cache (4 tools):**
- ✅ mybb_cache_list - Shows 30 caches (45KB total)
- ✅ mybb_cache_read - Returns serialized data
- ✅ mybb_cache_rebuild - Safe regeneration
- ✅ mybb_cache_clear - Alias for rebuild

**Statistics (2 tools):**
- ✅ mybb_stats_forum - Basic forum stats
- ✅ mybb_stats_board - Comprehensive board overview

**Database (1 tool):**
- ✅ mybb_db_query - Read-only SQL execution

---

## Best Practices

1. **Search Operations:**
   - Use specific tools (posts/threads/users) for focused searches
   - Use advanced search for broad multi-criteria queries
   - Apply limits to prevent overwhelming results

2. **Settings Management:**
   - Always use `mybb_setting_get` before `mybb_setting_set`
   - Test with non-critical settings first
   - Cache rebuilds happen automatically

3. **Cache Operations:**
   - Use `mybb_cache_list` to discover available caches
   - Rebuild caches after plugin/data changes
   - Cache regeneration is automatic and safe

4. **Statistics:**
   - Use `mybb_stats_forum` for simple overviews
   - Use `mybb_stats_board` for comprehensive dashboards
   - Data is real-time (not cached)

5. **Database Queries:**
   - Prefer specialized tools over direct SQL
   - Use `mybb_db_query` only for custom exploration
   - Always use SELECT for read-only access

---

## Edge Cases & Gotchas

1. **Search:**
   - Empty results return helpful messages (not errors)
   - Post search is content-based, thread search is subject-only
   - User search never exposes sensitive data

2. **Settings:**
   - Some settings have validation (numeric ranges, yes/no only)
   - Cache rebuild adds ~100ms to setting updates
   - Setting names are case-sensitive

3. **Cache:**
   - Not all cache names exist (e.g., 'settings' cache doesn't exist)
   - Large caches are truncated in read responses
   - PHP serialized format may need parsing for complex data

4. **Statistics:**
   - Post counts include deleted/unapproved posts
   - Forum count excludes categories
   - Private message count may be 0 on new installations

5. **Database:**
   - Read-only enforcement prevents destructive queries
   - Table prefix must be correct (usually `mybb_`)
   - Results are ASCII formatted (not JSON)

---

*Documentation generated: 2026-01-17*
*MyBB MCP Version: 1.0*
*Testing Environment: MyBB 1.8.x*
