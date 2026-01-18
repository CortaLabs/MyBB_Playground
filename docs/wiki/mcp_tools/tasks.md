# Scheduled Task Tools

Tools for managing MyBB's scheduled task system (cron-like background jobs).

## Tools Overview

| Tool | Description |
|------|-------------|
| `mybb_task_list` | List all scheduled tasks |
| `mybb_task_get` | Get detailed information about a specific task |
| `mybb_task_enable` | Enable a scheduled task |
| `mybb_task_disable` | Disable a scheduled task |
| `mybb_task_update_nextrun` | Update the next run time for a task |
| `mybb_task_run_log` | View task execution history |

---

## mybb_task_list

List all scheduled tasks with their IDs, titles, and next run times.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `enabled_only` | bool | optional | False | Only show enabled tasks |

### Returns

Markdown table of tasks with:
- Task ID (tid)
- Title
- Description
- Enabled status
- Next run time (Unix timestamp)
- Interval (in seconds)
- Last run time

### Example

```
List all enabled tasks:
- enabled_only: true
```

---

## mybb_task_get

Get detailed information about a specific task.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | int | **REQUIRED** | - | Task ID |

### Returns

Full task details including:
- Task ID
- Title and description
- File path (relative to MyBB root)
- Enabled status
- Interval configuration
- Next run time
- Last run time
- Logging enabled status

### Example

```
Get details for task ID 5:
- tid: 5
```

---

## mybb_task_enable

Enable a scheduled task.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | int | **REQUIRED** | - | Task ID to enable |

### Returns

Confirmation message with task title.

### Example

```
Enable task 3:
- tid: 3
```

---

## mybb_task_disable

Disable a scheduled task.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | int | **REQUIRED** | - | Task ID to disable |

### Returns

Confirmation message with task title.

### Example

```
Disable task 7:
- tid: 7
```

---

## mybb_task_update_nextrun

Update the next run time for a task.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | int | **REQUIRED** | - | Task ID |
| `nextrun` | int | **REQUIRED** | - | Unix timestamp for next execution |

### Returns

Confirmation message with updated next run time.

### Example

```
Schedule task 4 to run at specific time:
- tid: 4
- nextrun: 1704931200
```

---

## mybb_task_run_log

View task execution history.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tid` | int | optional | - | Task ID to filter by (omit for all tasks) |
| `limit` | int | optional | 50 | Maximum log entries to return (max 500) |

### Returns

Markdown table of task execution log entries with:
- Log ID
- Task ID and title
- Execution time
- Duration (in seconds)
- Status (success/failed)
- Error message (if failed)

### Example

```
View last 100 executions of task 2:
- tid: 2
- limit: 100

View last 50 executions across all tasks:
- limit: 50
```

---

## Usage Notes

### Task Management Workflow

1. **List tasks** - Use `mybb_task_list` to see all scheduled tasks
2. **View details** - Use `mybb_task_get` to inspect a specific task
3. **Enable/disable** - Use `mybb_task_enable` or `mybb_task_disable` to control execution
4. **Reschedule** - Use `mybb_task_update_nextrun` to change when task runs next
5. **Monitor** - Use `mybb_task_run_log` to view execution history

### Common Use Cases

**Debugging a failing task:**
```
1. mybb_task_run_log(tid=5, limit=10) - check recent failures
2. mybb_task_get(tid=5) - review configuration
3. mybb_task_disable(tid=5) - stop execution while fixing
4. (fix the issue)
5. mybb_task_enable(tid=5) - resume execution
```

**Manually triggering a task:**
```
1. mybb_task_get(tid=3) - note current nextrun time
2. mybb_task_update_nextrun(tid=3, nextrun=<current_time>) - set to run now
3. Wait for task to execute
4. mybb_task_run_log(tid=3, limit=1) - verify execution
```

### Understanding Task Intervals

MyBB tasks run based on intervals (in seconds):
- `60` = Every minute
- `3600` = Every hour
- `86400` = Every day
- `604800` = Every week

The `nextrun` timestamp determines when the task will execute next. MyBB's task system checks for tasks where `nextrun <= current_time`.

### Task Log Retention

- Task logs are stored in the database
- Use `limit` parameter to control how many entries to retrieve
- Maximum limit is 500 entries per query
- Logs include execution time and error details for debugging

---

[← Back to MCP Tools Index](index.md)
