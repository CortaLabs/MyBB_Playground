# Forum, Thread & Post Management Tools

Complete reference for MyBB MCP tools that manage forums, threads, and posts.

## Table of Contents
- [Forum Management](#forum-management)
- [Thread Management](#thread-management)
- [Post Management](#post-management)

---

## Forum Management

### mybb_forum_list

List all forums with hierarchy information.

**Parameters:**
None

**Returns:**
Markdown table of all forums with hierarchy.

**Example:**
```
Use "List all forums" or call mybb_forum_list directly
```

---

### mybb_forum_read

Get forum details by forum ID.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `fid` | integer | Yes | - | Forum ID |

**Returns:**
Full forum details (name, description, parent, permissions, etc.).

**Example:**
```
Use "Show me details for forum 2" or mybb_forum_read(fid=2)
```

---

### mybb_forum_create

Create a new forum or category.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | Yes | - | Forum name |
| `description` | string | No | `""` | Forum description |
| `type` | string | No | `"f"` | "f" for forum, "c" for category |
| `pid` | integer | No | `0` | Parent forum ID |
| `parentlist` | string | No | `""` | Comma-separated ancestor path |
| `disporder` | integer | No | `1` | Display order |

**Returns:**
New forum ID.

**Example:**
```
mybb_forum_create(name="Support", description="Get help here", type="f")
```

---

### mybb_forum_update

Update forum properties.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `fid` | integer | Yes | - | Forum ID |
| `name` | string | No | - | New name |
| `description` | string | No | - | New description |
| `type` | string | No | - | "f" for forum, "c" for category |
| `disporder` | integer | No | - | Display order |
| `active` | integer | No | - | Is active (0 or 1) |
| `open` | integer | No | - | Is open for posting (0 or 1) |

**Returns:**
Confirmation.

**Example:**
```
mybb_forum_update(fid=5, name="New Name", open=0)
```

---

### mybb_forum_delete

Delete a forum.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `fid` | integer | Yes | - | Forum ID |

**Returns:**
Confirmation.

**WARNING:**
Does not handle content migration. Ensure forum is empty first.

**Example:**
```
mybb_forum_delete(fid=10)
```

---

## Thread Management

### mybb_thread_list

List threads in a forum with pagination.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `fid` | integer | No | - | Forum ID (omit for all threads) |
| `limit` | integer | No | `50` | Maximum threads to return |
| `offset` | integer | No | `0` | Number of threads to skip |

**Returns:**
Markdown table of threads.

**Example:**
```
mybb_thread_list(fid=2, limit=20)
```

---

### mybb_thread_read

Get thread details by thread ID.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | integer | Yes | - | Thread ID |

**Returns:**
Full thread details.

**Example:**
```
mybb_thread_read(tid=42)
```

---

### mybb_thread_create

Create a new thread with first post (atomic operation).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `fid` | integer | Yes | - | Forum ID |
| `subject` | string | Yes | - | Thread subject |
| `message` | string | Yes | - | First post content (BBCode) |
| `uid` | integer | No | `1` | Author user ID |
| `username` | string | No | `"Admin"` | Author username |
| `prefix` | integer | No | `0` | Thread prefix ID |

**Returns:**
New thread ID.

**Behavior:**
Atomic operation creating thread and first post.

**Example:**
```
mybb_thread_create(
    fid=2,
    subject="Welcome to our forum",
    message="This is the first post content"
)
```

---

### mybb_thread_update

Update thread properties (subject, status, prefix).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | integer | Yes | - | Thread ID |
| `subject` | string | No | - | New thread subject |
| `prefix` | integer | No | - | Thread prefix ID |
| `closed` | string | No | - | Closed status |
| `sticky` | integer | No | - | Is sticky (0 or 1) |
| `visible` | integer | No | - | Visibility (1=visible, 0=unapproved, -1=deleted) |

**Returns:**
Confirmation.

**Example:**
```
mybb_thread_update(tid=42, sticky=1, closed="1")
```

---

### mybb_thread_delete

Delete a thread (soft delete by default, updates counters).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | integer | Yes | - | Thread ID |
| `soft` | boolean | No | `true` | Soft delete (visible=-1) or permanent |

**Returns:**
Confirmation.

**Behavior:**
Updates thread counters.

**Example:**
```
mybb_thread_delete(tid=42, soft=true)
```

---

### mybb_thread_move

Move thread to a different forum (updates counters).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | integer | Yes | - | Thread ID |
| `new_fid` | integer | Yes | - | New forum ID |

**Returns:**
Confirmation.

**Behavior:**
Updates counters for source and destination forums.

**Example:**
```
mybb_thread_move(tid=42, new_fid=5)
```

---

## Post Management

### mybb_post_list

List posts in a thread with pagination.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | integer | No | - | Thread ID (omit for all posts) |
| `limit` | integer | No | `50` | Maximum posts to return |
| `offset` | integer | No | `0` | Number of posts to skip |

**Returns:**
Markdown table of posts.

**Example:**
```
mybb_post_list(tid=42, limit=25)
```

---

### mybb_post_read

Get post details by post ID.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `pid` | integer | Yes | - | Post ID |

**Returns:**
Full post details.

**Example:**
```
mybb_post_read(pid=123)
```

---

### mybb_post_create

Create a new post in a thread (updates counters).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | integer | Yes | - | Thread ID |
| `message` | string | Yes | - | Post content (BBCode) |
| `subject` | string | No | `"RE: {thread subject}"` | Post subject |
| `uid` | integer | No | `1` | Author user ID |
| `username` | string | No | `"Admin"` | Author username |
| `replyto` | integer | No | `0` | Parent post ID for threading |

**Returns:**
New post ID.

**Behavior:**
Updates thread counters.

**Example:**
```
mybb_post_create(
    tid=42,
    message="Thanks for the help!",
    uid=5
)
```

---

### mybb_post_update

Edit a post (tracks edit history).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `pid` | integer | Yes | - | Post ID |
| `message` | string | No | - | New post content (BBCode) |
| `subject` | string | No | - | New post subject |
| `edituid` | integer | No | - | Editor user ID |
| `editreason` | string | No | `""` | Edit reason text |

**Returns:**
Confirmation.

**Behavior:**
Tracks edit history.

**Example:**
```
mybb_post_update(
    pid=123,
    message="Updated content",
    editreason="Fixed typo"
)
```

---

### mybb_post_delete

Delete a post (soft delete by default, updates counters).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `pid` | integer | Yes | - | Post ID |
| `soft` | boolean | No | `true` | Soft delete (visible=-1) or permanent |

**Returns:**
Confirmation.

**Behavior:**
Updates thread counters.

**Example:**
```
mybb_post_delete(pid=123, soft=true)
```

---

## Related Documentation

- [Templates](templates.md) - Template management
- [Users & Moderation](users_moderation.md) - User and moderation tools
- [Search](search.md) - Content search tools
