# User & Moderation Tools

User management and moderation tools for MyBB forums.

---

## User Management Tools

### mybb_user_get

Get user profile by UID or username.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| uid | int | No | - | User ID |
| username | string | No | - | Username |

**Notes:**
- At least one parameter (uid or username) should be provided
- Sensitive fields are excluded from response: password, salt, loginkey, regip, lastip

**Returns:** User profile object (excludes password, salt, loginkey, regip, lastip)

---

### mybb_user_list

List users with optional filtering.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| usergroup | int | No | - | Filter by usergroup ID |
| limit | int | No | 50 | Maximum results (max 100) |
| offset | int | No | 0 | Pagination offset |

**Returns:** Markdown table of users (no sensitive fields)

---

### mybb_user_update_group

Update user's primary usergroup and additional groups.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| uid | int | Yes | - | User ID |
| usergroup | int | Yes | - | Primary usergroup ID |
| additionalgroups | string | No | - | Comma-separated group IDs |

**Returns:** Confirmation message

---

### mybb_user_ban

Ban a user by adding them to the banned list.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| uid | int | Yes | - | User ID to ban |
| gid | int | Yes | - | Banned usergroup ID |
| admin | int | Yes | - | Admin user ID (who is banning) |
| dateline | int | Yes | - | Ban timestamp (Unix epoch) |
| bantime | string | No | "---" | Duration (e.g., "perm", "---") |
| reason | string | No | "" | Ban reason |

**Returns:** Confirmation message

---

### mybb_user_unban

Remove user from banned list.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| uid | int | Yes | - | User ID to unban |

**Returns:** Confirmation message

---

### mybb_usergroup_list

List all usergroups.

**Parameters:** None

**Returns:** Markdown table of all usergroups

---

## Moderation Tools

### mybb_mod_close_thread

Close or open a thread.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| tid | int | Yes | - | Thread ID |
| closed | bool | No | True | True to close, False to open |

**Returns:** Confirmation message

---

### mybb_mod_stick_thread

Stick or unstick a thread.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| tid | int | Yes | - | Thread ID |
| sticky | bool | No | True | True to stick, False to unstick |

**Returns:** Confirmation message

---

### mybb_mod_approve_thread

Approve or unapprove a thread.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| tid | int | Yes | - | Thread ID |
| approve | bool | No | True | True to approve, False to unapprove |

**Returns:** Confirmation message

---

### mybb_mod_approve_post

Approve or unapprove a post.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| pid | int | Yes | - | Post ID |
| approve | bool | No | True | True to approve, False to unapprove |

**Returns:** Confirmation message

---

### mybb_mod_soft_delete_thread

Soft delete or restore a thread (sets visible flag).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| tid | int | Yes | - | Thread ID |
| delete | bool | No | True | True to soft delete, False to restore |

**Returns:** Confirmation message

---

### mybb_mod_soft_delete_post

Soft delete or restore a post (sets visible flag).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| pid | int | Yes | - | Post ID |
| delete | bool | No | True | True to soft delete, False to restore |

**Returns:** Confirmation message

---

### mybb_modlog_list

List moderation log entries with optional filtering.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| uid | int | No | - | Filter by moderator user ID |
| fid | int | No | - | Filter by forum ID |
| tid | int | No | - | Filter by thread ID |
| limit | int | No | 50 | Maximum results (max 100) |

**Returns:** Markdown table of moderation log entries

---

### mybb_modlog_add

Add a moderation log entry.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| uid | int | Yes | - | User ID performing action |
| action | string | Yes | - | Action description |
| fid | int | No | 0 | Forum ID (0 if N/A) |
| tid | int | No | 0 | Thread ID (0 if N/A) |
| pid | int | No | 0 | Post ID (0 if N/A) |
| data | string | No | "" | Additional data (serialized) |
| ipaddress | string | No | "" | Moderator IP address |

**Returns:** Confirmation message
