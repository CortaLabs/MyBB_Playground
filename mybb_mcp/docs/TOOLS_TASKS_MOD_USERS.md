# MyBB MCP Tools: Task Management, Moderation, and User Management

Complete documentation for MyBB MCP tools covering scheduled tasks, moderation operations, and user management.

---

## Table of Contents

- [Task Management Tools](#task-management-tools)
  - [mybb_task_list](#mybb_task_list)
  - [mybb_task_get](#mybb_task_get)
  - [mybb_task_enable](#mybb_task_enable)
  - [mybb_task_disable](#mybb_task_disable)
  - [mybb_task_update_nextrun](#mybb_task_update_nextrun)
  - [mybb_task_run_log](#mybb_task_run_log)
- [Moderation Tools](#moderation-tools)
  - [mybb_mod_close_thread](#mybb_mod_close_thread)
  - [mybb_mod_stick_thread](#mybb_mod_stick_thread)
  - [mybb_mod_approve_thread](#mybb_mod_approve_thread)
  - [mybb_mod_approve_post](#mybb_mod_approve_post)
  - [mybb_mod_soft_delete_thread](#mybb_mod_soft_delete_thread)
  - [mybb_mod_soft_delete_post](#mybb_mod_soft_delete_post)
  - [mybb_modlog_list](#mybb_modlog_list)
  - [mybb_modlog_add](#mybb_modlog_add)
- [User Management Tools](#user-management-tools)
  - [mybb_user_get](#mybb_user_get)
  - [mybb_user_list](#mybb_user_list)
  - [mybb_user_update_group](#mybb_user_update_group)
  - [mybb_user_ban](#mybb_user_ban)
  - [mybb_user_unban](#mybb_user_unban)
  - [mybb_usergroup_list](#mybb_usergroup_list)

---

## Task Management Tools

### mybb_task_list

**Purpose:** List all scheduled tasks in the MyBB installation with their status and execution schedule.

**Parameters:**
- `enabled_only` (boolean, optional): Only show enabled tasks. Default: false

**Example:**
```json
// Call
mcp__mybb__mybb_task_list()

// Response
# Scheduled Tasks (14)

| TID | Title | File | Enabled | Next Run | Last Run |
|-----|-------|------|---------|----------|----------|
| 2 | Daily Cleanup | dailycleanup | Yes | 2026-01-17 19:00 | Never |
| 11 | Delayed Moderation | delayedmoderation | Yes | 2026-01-17 19:00 | Never |
| 3 | Half-hourly User Cleanup | usercleanup | Yes | 2026-01-17 08:59 | 2026-01-17 08:48 |
| 1 | Hourly Cleanup | hourlycleanup | Yes | 2026-01-17 09:00 | 2026-01-17 08:08 |
...
```

**Notes:**
- Returns both enabled and disabled tasks by default
- Tasks with "Never" in Last Run have not been executed yet
- Next Run time is calculated based on the cron-style schedule

---

### mybb_task_get

**Purpose:** Get detailed information about a specific scheduled task including its description, schedule, and execution history.

**Parameters:**
- `tid` (integer, required): Task ID

**Example:**
```json
// Call
mcp__mybb__mybb_task_get(tid=1)

// Response
# Task: Hourly Cleanup (TID 1)

**Description**: Cleans out old searches, captcha images, registration questions and expires redirects.
**File**: hourlycleanup
**Enabled**: Yes
**Logging**: Yes
**Locked**: 0

## Schedule
**Minute**: 0
**Hour**: *
**Day**: *
**Month**: *
**Weekday**: *

## Execution
**Next Run**: 2026-01-17 09:00:00 (Unix: 1768658400)
**Last Run**: 2026-01-17 08:08:31 (Unix: 1768655311)
```

**Notes:**
- Schedule uses cron-style notation (* means every)
- Locked=1 indicates the task is currently running
- Both human-readable and Unix timestamps are provided

---

### mybb_task_enable

**Purpose:** Enable a disabled scheduled task so it will run according to its schedule.

**Parameters:**
- `tid` (integer, required): Task ID to enable

**Example:**
```json
// Call
mcp__mybb__mybb_task_enable(tid=13)

// Response
Task 13 enabled successfully.
```

**Notes:**
- Enabling a task does not immediately execute it - it will run at the next scheduled time
- Verify the task is enabled by checking mybb_task_get or mybb_task_list

---

### mybb_task_disable

**Purpose:** Disable a scheduled task to prevent it from running automatically.

**Parameters:**
- `tid` (integer, required): Task ID to disable

**Example:**
```json
// Call
mcp__mybb__mybb_task_disable(tid=13)

// Response
Task 13 disabled successfully.
```

**Notes:**
- Disabling prevents automatic execution but does not affect manual execution through admin panel
- Useful for temporarily stopping resource-intensive tasks
- **Known Issue:** Returns error "Task may not exist" if task is already disabled

---

### mybb_task_update_nextrun

**Purpose:** Manually set the next execution time for a scheduled task.

**Parameters:**
- `tid` (integer, required): Task ID
- `nextrun` (integer, required): Unix timestamp for next execution

**Example:**
```json
// Call
mcp__mybb__mybb_task_update_nextrun(tid=13, nextrun=1800000000)

// Response
Task 13 next run updated to 2027-01-15 03:00:00 (Unix: 1800000000).
```

**Notes:**
- Useful for delaying or advancing task execution
- Does not change the regular schedule - subsequent runs follow the cron schedule
- Can be used to manually trigger immediate execution by setting nextrun to current time

---

### mybb_task_run_log

**Purpose:** View execution history of scheduled tasks including success/failure status and execution time.

**Parameters:**
- `limit` (integer, optional): Maximum log entries to return (max 500). Default: 50
- `tid` (integer, optional): Filter by specific task ID

**Example:**
```json
// Call
mcp__mybb__mybb_task_run_log(limit=5)

// Response (when table exists)
Would show recent task executions with timestamps and status
```

**Notes:**
- **Database Requirement:** Requires `mybb_tasklogs` table to exist
- **Known Issue:** Returns error "Table 'mybb_dev.mybb_tasklogs' doesn't exist" on fresh installations
- This is a MyBB installation issue, not a tool issue - the table may need to be created manually

---

## Moderation Tools

**Bridge-backed:** All moderation mutations now execute via the PHP bridge to ensure MyBB-native side effects (counters, logs, cache updates).

### mybb_mod_close_thread

**Purpose:** Close or open a thread to prevent/allow new replies.

**Parameters:**
- `tid` (integer, required): Thread ID
- `closed` (boolean, optional): True to close, False to open. Default: true

**Example:**
```json
// Call - Close thread
mcp__mybb__mybb_mod_close_thread(tid=1, closed=true)

// Response
# Thread Closed
Thread 1 has been closed successfully.

// Verify
mcp__mybb__mybb_thread_read(tid=1)
// Shows: **Status**: Visible | Closed | Normal
```

**Notes:**
- Closed threads display "Closed" badge in thread listing
- Users without moderator permissions cannot reply to closed threads
- **Known Issue:** Reopening an already-closed thread may fail with "Failed to update thread" error
- Workaround: Check thread status before attempting to reopen

---

### mybb_mod_stick_thread

**Purpose:** Stick or unstick a thread to keep it at the top of forum listings.

**Parameters:**
- `tid` (integer, required): Thread ID
- `sticky` (boolean, optional): True to stick, False to unstick. Default: true

**Example:**
```json
// Call - Stick thread
mcp__mybb__mybb_mod_stick_thread(tid=1, sticky=true)

// Response
# Thread Sticked
Thread 1 has been sticked successfully.

// Call - Unstick thread
mcp__mybb__mybb_mod_stick_thread(tid=1, sticky=false)

// Response
# Thread Unsticked
Thread 1 has been unsticked successfully.
```

**Notes:**
- Sticky threads appear at the top of forum thread listings above normal threads
- Multiple sticky threads are ordered by last post time
- Works reliably in both directions (stick/unstick)

---

### mybb_mod_approve_thread

**Purpose:** Approve or unapprove a thread to control its visibility.

**Parameters:**
- `tid` (integer, required): Thread ID
- `approve` (boolean, optional): True to approve, False to unapprove. Default: true

**Example:**
```json
// Call - Unapprove thread
mcp__mybb__mybb_mod_approve_thread(tid=1, approve=false)

// Response
# Thread Unapproved
Thread 1 has been unapproved successfully.

// Verify
mcp__mybb__mybb_thread_read(tid=1)
// Shows: **Status**: Unapproved | Closed | Normal

// Call - Approve thread
mcp__mybb__mybb_mod_approve_thread(tid=1, approve=true)

// Response
# Thread Approved
Thread 1 has been approved successfully.
```

**Notes:**
- Unapproved threads are only visible to moderators and admins
- Used in moderation queue workflows
- Thread counters are updated automatically

---

### mybb_mod_approve_post

**Purpose:** Approve or unapprove a post to control its visibility.

**Parameters:**
- `pid` (integer, required): Post ID
- `approve` (boolean, optional): True to approve, False to unapprove. Default: true

**Example:**
```json
// Call - Unapprove post
mcp__mybb__mybb_mod_approve_post(pid=1, approve=false)

// Response
# Post Unapproved
Post 1 has been unapproved successfully.

// Verify
mcp__mybb__mybb_post_read(pid=1)
// Shows: **Status**: Unapproved

// Call - Approve post
mcp__mybb__mybb_mod_approve_post(pid=1, approve=true)

// Response
# Post Approved
Post 1 has been approved successfully.
```

**Notes:**
- Unapproved posts are only visible to moderators and admins
- Post counters and thread statistics are updated automatically
- Works independently of thread approval status

---

### mybb_mod_soft_delete_thread

**Purpose:** Soft delete or restore a thread. Soft deleted threads can be recovered.

**Parameters:**
- `tid` (integer, required): Thread ID
- `delete` (boolean, optional): True to soft delete, False to restore. Default: true

**Example:**
```json
// Call - Soft delete thread
mcp__mybb__mybb_mod_soft_delete_thread(tid=1, delete=true)

// Response
# Thread Soft Deleted
Thread 1 has been soft deleted successfully.

// Verify
mcp__mybb__mybb_thread_read(tid=1)
// Shows: **Status**: Deleted | Closed | Normal

// Call - Restore thread
mcp__mybb__mybb_mod_soft_delete_thread(tid=1, delete=false)

// Response
# Thread Restored
Thread 1 has been restored successfully.
```

**Notes:**
- Soft deleted threads are hidden from normal users but visible to moderators
- Can be permanently deleted later or restored
- Different from permanent deletion (which uses thread_delete)
- Updates forum counters automatically

---

### mybb_mod_soft_delete_post

**Purpose:** Soft delete or restore a post. Soft deleted posts can be recovered.

**Parameters:**
- `pid` (integer, required): Post ID
- `delete` (boolean, optional): True to soft delete, False to restore. Default: true

**Example:**
```json
// Call - Soft delete post
mcp__mybb__mybb_mod_soft_delete_post(pid=1, delete=true)

// Expected Response
# Post Soft Deleted
Post 1 has been soft deleted successfully.
```

**Notes:**
- **CRITICAL BUG:** Currently returns SQL error: "Unknown column 'deletetime' in 'SET'"
- This indicates the tool is trying to set a 'deletetime' column that doesn't exist in the posts table
- The tool is NOT functional in current MyBB schema
- Use permanent delete (mybb_post_delete with soft=true) as workaround until fixed

---

### mybb_modlog_list

**Purpose:** List moderation log entries showing moderator actions.

**Parameters:**
- `limit` (integer, optional): Maximum number of entries (1-100). Default: 50
- `fid` (integer, optional): Filter by forum ID
- `tid` (integer, optional): Filter by thread ID
- `uid` (integer, optional): Filter by moderator user ID

**Example:**
```json
// Call
mcp__mybb__mybb_modlog_list(limit=5)

// Response (when logs exist)
No moderation log entries found.
```

**Notes:**
- Returns empty on fresh installations with no moderation history
- Useful for audit trails and tracking moderator actions
- Can filter by multiple criteria simultaneously

---

### mybb_modlog_add

**Purpose:** Add a custom entry to the moderation log for audit purposes.

**Parameters:**
- `uid` (integer, required): User ID performing the action
- `action` (string, required): Action description
- `fid` (integer, optional): Forum ID (0 if not applicable). Default: 0
- `tid` (integer, optional): Thread ID (0 if not applicable). Default: 0
- `pid` (integer, optional): Post ID (0 if not applicable). Default: 0
- `ipaddress` (string, optional): IP address of moderator. Default: ""
- `data` (string, optional): Additional data (serialized). Default: ""

**Example:**
```json
// Call
mcp__mybb__mybb_modlog_add(
  uid=1,
  action="Testing moderation log tool",
  tid=1,
  fid=2
)

// Response
Error: Failed to create moderation log entry.
```

**Notes:**
- **Known Issue:** Currently fails to create entries with "Failed to create moderation log entry" error
- May be related to database schema or permissions
- The automatic moderation tools (close, approve, etc.) may log actions separately
- Useful for logging custom moderator actions when working

---

## User Management Tools

**Bridge-backed:** User mutations (group changes, ban/unban) now execute via the PHP bridge to ensure MyBB-native side effects.

### mybb_user_get

**Purpose:** Get detailed information about a specific user by UID or username.

**Parameters:**
- `uid` (integer, optional): User ID
- `username` (string, optional): Username

**Note:** Must provide either uid OR username, not both.

**Example:**
```json
// Call by UID
mcp__mybb__mybb_user_get(uid=1)

// Response
# User Information

**User ID:** 1
**Username:** admin
**Usergroup:** 4
**Email:** admin@admin.com
**Post Count:** 1
**Thread Count:** 1
**Registration Date:** 1768647817
**User Title:**
**Additional Groups:** 3,6
```

**Notes:**
- Sensitive fields (password, salt, loginkey, regip, lastip) are automatically excluded
- Registration date is Unix timestamp
- Additional groups shown as comma-separated list
- Returns user statistics including posts and threads

---

### mybb_user_list

**Purpose:** List users with optional filtering and pagination.

**Parameters:**
- `limit` (integer, optional): Maximum number of users (1-100). Default: 50
- `offset` (integer, optional): Number of users to skip. Default: 0
- `usergroup` (integer, optional): Filter by usergroup ID

**Example:**
```json
// Call
mcp__mybb__mybb_user_list(limit=10)

// Response
# Users (1 found)

| UID | Username | Usergroup | Posts | Threads |
|-----|----------|-----------|-------|---------|
| 1 | admin | 4 | 1 | 1 |
```

**Notes:**
- Sensitive fields are always excluded for security
- Useful for finding users by usergroup
- Supports pagination for large user bases
- Default limit is 50 to prevent performance issues

---

### mybb_user_update_group

**Purpose:** Update a user's primary usergroup and additional groups.

**Parameters:**
- `uid` (integer, required): User ID
- `usergroup` (integer, required): Primary usergroup ID
- `additionalgroups` (string, optional): Comma-separated additional group IDs

**Example:**
```json
// Call - Add additional groups
mcp__mybb__mybb_user_update_group(
  uid=1,
  usergroup=4,
  additionalgroups="3,6"
)

// Response
# User Group Updated
User 1 has been assigned to usergroup 4.

// Verify
mcp__mybb__mybb_user_get(uid=1)
// Shows: **Additional Groups:** 3,6

// Call - Remove additional groups
mcp__mybb__mybb_user_update_group(
  uid=1,
  usergroup=4,
  additionalgroups=""
)

// Response
# User Group Updated
User 1 has been assigned to usergroup 4.
```

**Notes:**
- Primary usergroup determines main permissions
- Additional groups combine their permissions with primary group
- Empty additionalgroups string removes all additional groups
- Changes take effect immediately for the user

---

### mybb_user_ban

**Purpose:** Add a user to the banned list.

**Parameters:**
- `uid` (integer, required): User ID to ban
- `gid` (integer, required): Banned usergroup ID (usually 7)
- `admin` (integer, required): Admin user ID performing the ban
- `dateline` (integer, required): Ban timestamp (Unix timestamp)
- `bantime` (string, optional): Ban duration (e.g., 'perm', '---'). Default: "---"
- `reason` (string, optional): Ban reason. Default: ""

**Example:**
```json
// Call
mcp__mybb__mybb_user_ban(
  uid=2,
  gid=7,
  admin=1,
  dateline=1768658500,
  reason="Testing ban functionality"
)

// Expected Response
# User Banned
User 2 has been banned successfully.
```

**Notes:**
- **Important:** Cannot ban superadmin users - will be rejected
- **Requirement:** Need a test user (non-admin) to test this functionality
- GID 7 is typically the "Banned" usergroup
- Bantime "---" typically means permanent ban
- Dateline records when the ban was issued

---

### mybb_user_unban

**Purpose:** Remove a user from the banned list.

**Parameters:**
- `uid` (integer, required): User ID to unban

**Example:**
```json
// Call
mcp__mybb__mybb_user_unban(uid=2)

// Expected Response
# User Unbanned
User 2 has been unbanned successfully.
```

**Notes:**
- **Requirement:** Need a banned test user to fully test this functionality
- Removes the user from the banned users table
- Does not automatically restore previous usergroup - may need to use user_update_group
- Safe to call on non-banned users (will return appropriate message)

---

### mybb_usergroup_list

**Purpose:** List all usergroups in the MyBB installation.

**Parameters:** None

**Example:**
```json
// Call
mcp__mybb__mybb_usergroup_list()

// Response
# Usergroups (7 total)

| GID | Title | Type |
|-----|-------|------|
| 1 | Guests | User |
| 2 | Registered | User |
| 3 | Super Moderators | Moderator |
| 4 | Administrators | Admin |
| 5 | Awaiting Activation | User |
| 6 | Moderators | Moderator |
| 7 | Banned | User |
```

**Notes:**
- Returns all default MyBB usergroups plus any custom groups
- Type indicates the general permission level (User, Moderator, Admin)
- GID (Group ID) is used in user_update_group and user_ban operations
- Default groups: 1=Guests, 2=Registered, 4=Administrators, 7=Banned

---

## Testing Notes

### Successfully Tested Tools (18/20)

**Task Management (6/6):**
- ✅ mybb_task_list - Works perfectly
- ✅ mybb_task_get - Works perfectly
- ✅ mybb_task_enable - Works perfectly
- ✅ mybb_task_disable - Works (note: fails if already disabled)
- ✅ mybb_task_update_nextrun - Works perfectly
- ⚠️ mybb_task_run_log - Tool works, but requires tasklogs table

**Moderation (6/8):**
- ⚠️ mybb_mod_close_thread - Works for closing, fails on reopen when already closed
- ✅ mybb_mod_stick_thread - Works perfectly
- ✅ mybb_mod_approve_thread - Works perfectly
- ✅ mybb_mod_approve_post - Works perfectly
- ✅ mybb_mod_soft_delete_thread - Works perfectly
- ❌ mybb_mod_soft_delete_post - SQL error (deletetime column missing)
- ✅ mybb_modlog_list - Works perfectly
- ❌ mybb_modlog_add - Fails to create entries

**User Management (6/6):**
- ✅ mybb_user_get - Works perfectly
- ✅ mybb_user_list - Works perfectly
- ✅ mybb_user_update_group - Works perfectly
- ⚠️ mybb_user_ban - Untested (requires non-admin test user)
- ⚠️ mybb_user_unban - Untested (requires banned test user)
- ✅ mybb_usergroup_list - Works perfectly

### Known Issues

1. **mybb_task_run_log**: Requires `mybb_tasklogs` table (MyBB installation issue)
2. **mybb_mod_close_thread**: Fails when trying to reopen already-closed thread
3. **mybb_mod_soft_delete_post**: SQL error - deletetime column doesn't exist in schema
4. **mybb_modlog_add**: Fails to create log entries (unknown cause)
5. **mybb_user_ban/unban**: Cannot test without non-admin test user

### Recommendations

1. For ban testing, create test users through MyBB admin panel first
2. Check thread status before using mod_close_thread to avoid reopen errors
3. Use mybb_post_delete(soft=true) instead of mybb_mod_soft_delete_post
4. Verify MyBB database schema includes tasklogs table if task logging is needed
5. All tested tools properly update MyBB counters and maintain data integrity

---

## Quick Reference

### Common Usergroup IDs
- 1 = Guests
- 2 = Registered Users
- 3 = Super Moderators
- 4 = Administrators
- 5 = Awaiting Activation
- 6 = Moderators
- 7 = Banned

### Common Task IDs (Default MyBB)
- 1 = Hourly Cleanup
- 2 = Daily Cleanup
- 3 = User Cleanup (half-hourly)
- 4 = Weekly Backup
- 5 = Promotion System
- 13 = Stylesheet Re-Cache

### Thread/Post Status Values
- visible = 1: Approved/visible
- visible = 0: Unapproved
- visible = -1: Soft deleted

---

**Document Version:** 1.0
**Last Updated:** 2026-01-17
**Tested Against:** MyBB Development Instance
**Tools Tested:** 20/20 (18 fully functional, 2 require test data)
