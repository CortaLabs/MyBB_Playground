# Search Tools

Tools for searching content across posts, threads, and users.

## Tools Overview

| Tool | Description |
|------|-------------|
| `mybb_search_posts` | Search post content with filters |
| `mybb_search_threads` | Search thread subjects with filters |
| `mybb_search_users` | Search users by username or email |
| `mybb_search_advanced` | Combined search across posts and/or threads |

---

## mybb_search_posts

Search post content with optional filters for forums, author, and date range.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | **REQUIRED** | - | Search term to find in post content |
| `forums` | array of int | optional | - | Forum IDs to search within |
| `author` | string | optional | - | Filter by username |
| `date_from` | int | optional | - | Start timestamp (Unix epoch) |
| `date_to` | int | optional | - | End timestamp (Unix epoch) |
| `limit` | int | optional | 25 | Maximum results (max 100) |
| `offset` | int | optional | 0 | Pagination offset |

### Returns

Markdown table of matching posts with:
- Post ID
- Thread subject
- Author
- Post excerpt
- Post date
- Forum name

### Example

```
Search for posts containing "plugin" in forum 5 from last month:
- query: "plugin"
- forums: [5]
- date_from: 1704067200
- limit: 50
```

---

## mybb_search_threads

Search thread subjects with optional filters for forums, author, and prefix.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | **REQUIRED** | - | Search term to find in thread subjects |
| `forums` | array of int | optional | - | Forum IDs to search within |
| `author` | string | optional | - | Filter by username |
| `prefix` | int | optional | - | Thread prefix ID |
| `limit` | int | optional | 25 | Maximum results (max 100) |
| `offset` | int | optional | 0 | Pagination offset |

### Returns

Markdown table of matching threads with:
- Thread ID
- Subject
- Author
- Forum name
- Reply count
- View count
- Last post date

### Example

```
Find all threads with "[Solved]" prefix authored by "admin":
- query: ""
- author: "admin"
- prefix: 1
- limit: 100
```

---

## mybb_search_users

Search users by username or email. Returns safe user info (no passwords).

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | **REQUIRED** | - | Search term |
| `field` | string | optional | "username" | Field to search: "username" or "email" |
| `limit` | int | optional | 25 | Maximum results (max 100) |
| `offset` | int | optional | 0 | Pagination offset |

### Returns

Markdown table of user profiles with:
- User ID
- Username
- Email (if searching by email)
- Registration date
- Post count
- Usergroup

**Note:** Excludes sensitive fields (password, salt, loginkey, regip, lastip)

### Example

```
Find users with "john" in username:
- query: "john"
- field: "username"
- limit: 10
```

---

## mybb_search_advanced

Combined search across posts and/or threads with multiple filters.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | **REQUIRED** | - | Search term |
| `content_type` | string | optional | "both" | Content type: "posts", "threads", or "both" |
| `forums` | array of int | optional | - | Forum IDs to search within |
| `date_from` | int | optional | - | Start timestamp (Unix epoch) |
| `date_to` | int | optional | - | End timestamp (Unix epoch) |
| `sort_by` | string | optional | "date" | Sort order: "date" or "relevance" |
| `limit` | int | optional | 25 | Maximum results per type (max 100) |
| `offset` | int | optional | 0 | Pagination offset |

### Returns

Combined results from posts and threads:
- Separate sections for thread results and post results
- Each result includes relevant metadata
- Total count for each content type

### Example

```
Search for "template" across all content from last week, sorted by relevance:
- query: "template"
- content_type: "both"
- date_from: 1704931200
- sort_by: "relevance"
- limit: 50
```

---

## Usage Notes

### Pagination

All search tools support pagination:
- Use `limit` to control results per page (max 100)
- Use `offset` to skip results for subsequent pages
- Example: Page 2 with 25 results → `limit=25, offset=25`

### Performance Tips

- Use specific forum IDs to narrow search scope
- Apply date ranges when searching large boards
- Use `mybb_search_threads` instead of `mybb_search_posts` when searching subjects only
- For comprehensive searches across both content types, use `mybb_search_advanced`

### Search Behavior

- Search is case-insensitive
- Partial word matching is supported
- Special characters are handled automatically
- Empty query string returns all results (filtered by other parameters)

---

[← Back to MCP Tools Index](index.md)
