# Database Tool

Direct database query tool for read-only exploration of MyBB's database.

## Tools Overview

| Tool | Description |
|------|-------------|
| `mybb_db_query` | Execute read-only SQL queries against MyBB database |

---

## mybb_db_query

Execute a read-only SQL query against the MyBB database for exploration and debugging.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | **REQUIRED** | - | SQL SELECT query |

### Returns

Query results as markdown table with:
- Column headers from query results
- Row data formatted as table
- Row count

### Behavior

- **Read-only:** Only SELECT queries are allowed
- INSERT, UPDATE, DELETE, DROP, ALTER, and other write operations are **rejected**
- Query is executed against the MyBB database configured in `.env`
- Results are limited to prevent excessive output
- Table prefixes (e.g., `mybb_`) must be included in queries

### Example

```
List all forums:
query: "SELECT fid, name, description FROM mybb_forums ORDER BY disporder"

Check plugin installation status:
query: "SELECT codename, active FROM mybb_datacache WHERE title = 'plugins'"

Find users by usergroup:
query: "SELECT uid, username, email FROM mybb_users WHERE usergroup = 4 LIMIT 10"

Get template set information:
query: "SELECT sid, title FROM mybb_templatesets"
```

---

## Usage Notes

### Security Restrictions

**This tool is READ-ONLY for safety:**
- ✅ Allowed: `SELECT` queries
- ❌ Blocked: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`
- ❌ Blocked: Any query with write operations or schema changes

### Table Prefix

MyBB uses a table prefix (default: `mybb_`):
- Always include the prefix in your queries
- Example: `mybb_users`, `mybb_forums`, `mybb_threads`
- Check `.env` file for your installation's prefix

### Common MyBB Tables

| Table | Contents |
|-------|----------|
| `mybb_users` | User accounts and profiles |
| `mybb_forums` | Forum categories and forums |
| `mybb_threads` | Thread metadata |
| `mybb_posts` | Post content |
| `mybb_usergroups` | User permission groups |
| `mybb_settings` | Board configuration |
| `mybb_templates` | Template HTML content |
| `mybb_themes` | Theme definitions |
| `mybb_datacache` | Cached data (plugins, settings, etc.) |
| `mybb_tasks` | Scheduled tasks |
| `mybb_moderatorlog` | Moderation action log |

### Use Cases

**Debugging:**
```sql
-- Check if a plugin is active
SELECT title, cache FROM mybb_datacache WHERE title = 'plugins';

-- Find templates modified in a set
SELECT tid, title, sid FROM mybb_templates WHERE sid = 1;

-- List recent threads
SELECT tid, subject, username, dateline
FROM mybb_threads
ORDER BY dateline DESC
LIMIT 20;
```

**Data Exploration:**
```sql
-- Count posts per forum
SELECT f.name, COUNT(p.pid) as post_count
FROM mybb_forums f
LEFT JOIN mybb_posts p ON p.fid = f.fid
GROUP BY f.fid, f.name;

-- Find users in specific usergroup
SELECT uid, username, usergroup, regdate
FROM mybb_users
WHERE usergroup = 4
ORDER BY regdate DESC;
```

**Configuration Checking:**
```sql
-- View board settings
SELECT name, value FROM mybb_settings WHERE name LIKE '%board%';

-- List all scheduled tasks
SELECT tid, title, enabled, nextrun FROM mybb_tasks;
```

### Best Practices

1. **Use specific columns** instead of `SELECT *` for clarity
2. **Add LIMIT clauses** to prevent overwhelming output
3. **Use ORDER BY** to control result ordering
4. **Join with caution** - large joins may be slow
5. **Check data types** in MyBB's database schema before filtering

### Performance Tips

- Add `LIMIT` to queries that might return many rows
- Use `WHERE` clauses to filter data efficiently
- Avoid complex joins on large tables (users, posts)
- Consider using specialized tools (e.g., `mybb_forum_list`) instead of raw queries for common operations

### When to Use vs Other Tools

**Use `mybb_db_query` when:**
- Exploring database schema
- Debugging data issues
- Running complex queries not covered by other tools
- Need custom filtered/joined data

**Use specialized tools instead when:**
- Standard CRUD operations exist (forums, threads, posts, users)
- Reading/writing templates or stylesheets (use template/stylesheet tools)
- Managing settings (use `mybb_setting_get`/`mybb_setting_set`)
- Plugin operations (use plugin tools)

The specialized tools provide better error handling, validation, and return formatting.

### Caveats

- **No write access** - use specialized tools for modifications
- **Raw results** - no validation or post-processing
- **Schema knowledge required** - you need to know table structure
- **Performance** - complex queries may be slow on large databases
- **No transaction support** - this is a single-query tool

---

[← Back to MCP Tools Index](index.md)
