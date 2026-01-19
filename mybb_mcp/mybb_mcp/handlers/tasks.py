"""Task management handlers for MyBB MCP tools."""

from typing import Any
import datetime


async def handle_task_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all scheduled tasks.

    Args:
        args: Tool arguments containing optional 'enabled_only' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Formatted list of tasks as markdown table
    """
    enabled_only = args.get("enabled_only", False)
    tasks = db.list_tasks(enabled_only=enabled_only)

    if not tasks:
        return "No tasks found."

    lines = [
        f"# Scheduled Tasks ({len(tasks)})\n",
        "| TID | Title | File | Enabled | Next Run | Last Run |",
        "|-----|-------|------|---------|----------|----------|"
    ]

    for task in tasks:
        next_run = datetime.datetime.fromtimestamp(task['nextrun']).strftime('%Y-%m-%d %H:%M')
        last_run = datetime.datetime.fromtimestamp(task['lastrun']).strftime('%Y-%m-%d %H:%M') if task['lastrun'] else "Never"
        enabled = "Yes" if task['enabled'] else "No"
        lines.append(
            f"| {task['tid']} | {task['title']} | {task['file']} | "
            f"{enabled} | {next_run} | {last_run} |"
        )

    return "\n".join(lines)


async def handle_task_get(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get detailed information about a specific task.

    Args:
        args: Tool arguments containing 'tid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Detailed task information as formatted markdown
    """
    tid = args.get("tid")
    task = db.get_task(tid)

    if not task:
        return f"Task {tid} not found."

    next_run = datetime.datetime.fromtimestamp(task['nextrun']).strftime('%Y-%m-%d %H:%M:%S')
    last_run = datetime.datetime.fromtimestamp(task['lastrun']).strftime('%Y-%m-%d %H:%M:%S') if task['lastrun'] else "Never"

    return (
        f"# Task: {task['title']} (TID {tid})\n\n"
        f"**Description**: {task['description']}\n"
        f"**File**: {task['file']}\n"
        f"**Enabled**: {'Yes' if task['enabled'] else 'No'}\n"
        f"**Logging**: {'Yes' if task['logging'] else 'No'}\n"
        f"**Locked**: {task['locked']}\n\n"
        f"## Schedule\n"
        f"**Minute**: {task['minute']}\n"
        f"**Hour**: {task['hour']}\n"
        f"**Day**: {task['day']}\n"
        f"**Month**: {task['month']}\n"
        f"**Weekday**: {task['weekday']}\n\n"
        f"## Execution\n"
        f"**Next Run**: {next_run} (Unix: {task['nextrun']})\n"
        f"**Last Run**: {last_run} (Unix: {task['lastrun']})"
    )


async def handle_task_enable(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Enable a scheduled task.

    Args:
        args: Tool arguments containing 'tid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message
    """
    tid = args.get("tid")
    if db.enable_task(tid):
        return f"Task {tid} enabled successfully."
    else:
        return f"Failed to enable task {tid}. Task may not exist."


async def handle_task_disable(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Disable a scheduled task.

    Args:
        args: Tool arguments containing 'tid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message
    """
    tid = args.get("tid")
    if db.disable_task(tid):
        return f"Task {tid} disabled successfully."
    else:
        return f"Failed to disable task {tid}. Task may not exist."


async def handle_task_update_nextrun(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Update the next run time for a task.

    Args:
        args: Tool arguments containing 'tid' and 'nextrun' parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message
    """
    tid = args.get("tid")
    nextrun = args.get("nextrun")

    if db.update_task_nextrun(tid, nextrun):
        next_run_str = datetime.datetime.fromtimestamp(nextrun).strftime('%Y-%m-%d %H:%M:%S')
        return f"Task {tid} next run updated to {next_run_str} (Unix: {nextrun})."
    else:
        return f"Failed to update task {tid}. Task may not exist."


async def handle_task_run_log(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get task execution log history.

    Args:
        args: Tool arguments containing optional 'tid' and 'limit' parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Task execution logs as markdown table
    """
    tid = args.get("tid")
    limit = args.get("limit", 50)
    logs = db.get_task_logs(tid=tid, limit=limit)

    if not logs:
        return "No task logs found."

    lines = [
        f"# Task Run Log ({len(logs)} entries)\n",
        "| Log ID | Task ID | Time | Data |",
        "|--------|---------|------|------|"
    ]

    for log in logs:
        time_str = datetime.datetime.fromtimestamp(log['dateline']).strftime('%Y-%m-%d %H:%M:%S')
        data = str(log.get('data', ''))[:50]
        lines.append(f"| {log['lid']} | {log['tid']} | {time_str} | {data} |")

    return "\n".join(lines)


# Handler registry for task tools
TASK_HANDLERS = {
    "mybb_task_list": handle_task_list,
    "mybb_task_get": handle_task_get,
    "mybb_task_enable": handle_task_enable,
    "mybb_task_disable": handle_task_disable,
    "mybb_task_update_nextrun": handle_task_update_nextrun,
    "mybb_task_run_log": handle_task_run_log,
}
