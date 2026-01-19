"""Moderation handlers for MyBB MCP tools."""

from datetime import datetime
from typing import Any


# ==================== Moderation Action Handlers ====================

async def handle_mod_close_thread(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Close or open a thread.

    Args:
        args: Tool arguments containing:
            - tid: Thread ID (required)
            - closed: True to close, False to open (default True)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message as markdown
    """
    tid = args.get("tid")
    closed = args.get("closed", True)

    if not tid:
        return "Error: 'tid' is required."

    success = db.close_thread(tid, closed)
    if success:
        status = "closed" if closed else "opened"
        return f"# Thread {status.title()}\n\nThread {tid} has been {status} successfully."
    else:
        return f"Error: Failed to update thread {tid}."


async def handle_mod_stick_thread(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Stick or unstick a thread.

    Args:
        args: Tool arguments containing:
            - tid: Thread ID (required)
            - sticky: True to stick, False to unstick (default True)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message as markdown
    """
    tid = args.get("tid")
    sticky = args.get("sticky", True)

    if not tid:
        return "Error: 'tid' is required."

    success = db.stick_thread(tid, sticky)
    if success:
        status = "sticked" if sticky else "unsticked"
        return f"# Thread {status.title()}\n\nThread {tid} has been {status} successfully."
    else:
        return f"Error: Failed to update thread {tid}."


async def handle_mod_approve_thread(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Approve or unapprove a thread.

    Args:
        args: Tool arguments containing:
            - tid: Thread ID (required)
            - approve: True to approve, False to unapprove (default True)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message as markdown
    """
    tid = args.get("tid")
    approve = args.get("approve", True)

    if not tid:
        return "Error: 'tid' is required."

    success = db.approve_thread(tid, approve)
    if success:
        status = "approved" if approve else "unapproved"
        return f"# Thread {status.title()}\n\nThread {tid} has been {status} successfully."
    else:
        return f"Error: Failed to update thread {tid}."


async def handle_mod_approve_post(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Approve or unapprove a post.

    Args:
        args: Tool arguments containing:
            - pid: Post ID (required)
            - approve: True to approve, False to unapprove (default True)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message as markdown
    """
    pid = args.get("pid")
    approve = args.get("approve", True)

    if not pid:
        return "Error: 'pid' is required."

    success = db.approve_post(pid, approve)
    if success:
        status = "approved" if approve else "unapproved"
        return f"# Post {status.title()}\n\nPost {pid} has been {status} successfully."
    else:
        return f"Error: Failed to update post {pid}."


async def handle_mod_soft_delete_thread(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Soft delete or restore a thread.

    Args:
        args: Tool arguments containing:
            - tid: Thread ID (required)
            - delete: True to soft delete, False to restore (default True)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message as markdown
    """
    tid = args.get("tid")
    delete = args.get("delete", True)

    if not tid:
        return "Error: 'tid' is required."

    # Use existing delete_thread method with soft parameter
    success = db.delete_thread(tid, soft=delete)
    if success:
        status = "soft deleted" if delete else "restored"
        return f"# Thread {status.title()}\n\nThread {tid} has been {status} successfully."
    else:
        return f"Error: Failed to update thread {tid}."


async def handle_mod_soft_delete_post(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Soft delete or restore a post.

    Args:
        args: Tool arguments containing:
            - pid: Post ID (required)
            - delete: True to soft delete, False to restore (default True)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message as markdown
    """
    pid = args.get("pid")
    delete = args.get("delete", True)

    if not pid:
        return "Error: 'pid' is required."

    success = db.soft_delete_post(pid, delete)
    if success:
        status = "soft deleted" if delete else "restored"
        return f"# Post {status.title()}\n\nPost {pid} has been {status} successfully."
    else:
        return f"Error: Failed to update post {pid}."


# ==================== Moderation Log Handlers ====================

async def handle_modlog_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List moderation log entries with optional filters.

    Args:
        args: Tool arguments containing:
            - uid: Optional filter by moderator user ID
            - fid: Optional filter by forum ID
            - tid: Optional filter by thread ID
            - limit: Maximum entries to return (default 50)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Moderation log entries as markdown table
    """
    uid = args.get("uid")
    fid = args.get("fid")
    tid = args.get("tid")
    limit = args.get("limit", 50)

    entries = db.list_modlog_entries(uid=uid, fid=fid, tid=tid, limit=limit)

    if not entries:
        return "No moderation log entries found."

    lines = [
        f"# Moderation Log ({len(entries)} entries)\n",
        "| Log ID | User ID | Forum | Thread | Post | Action | Date |",
        "|--------|---------|-------|--------|------|--------|------|"
    ]

    for entry in entries:
        date = datetime.fromtimestamp(entry['dateline']).strftime('%Y-%m-%d %H:%M')
        lines.append(
            f"| {entry['lid']} | {entry['uid']} | {entry['fid']} | {entry['tid']} | {entry['pid']} | {entry['action']} | {date} |"
        )

    return "\n".join(lines)


async def handle_modlog_add(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Add a moderation log entry.

    Args:
        args: Tool arguments containing:
            - uid: User ID performing the action (required)
            - action: Action description (required)
            - fid: Forum ID (default 0)
            - tid: Thread ID (default 0)
            - pid: Post ID (default 0)
            - data: Additional data (default "")
            - ipaddress: IP address of moderator (default "")
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message as markdown
    """
    uid = args.get("uid")
    fid = args.get("fid", 0)
    tid = args.get("tid", 0)
    pid = args.get("pid", 0)
    action = args.get("action")
    data = args.get("data", "")
    ipaddress = args.get("ipaddress", "")

    if not uid or not action:
        return "Error: 'uid' and 'action' are required."

    log_id = db.add_modlog_entry(uid, fid, tid, pid, action, data, ipaddress)

    if log_id:
        return f"# Moderation Log Entry Added\n\nLog entry created with ID {log_id}."
    else:
        return "Error: Failed to create moderation log entry."


# Handler registry for moderation tools
MODERATION_HANDLERS = {
    "mybb_mod_close_thread": handle_mod_close_thread,
    "mybb_mod_stick_thread": handle_mod_stick_thread,
    "mybb_mod_approve_thread": handle_mod_approve_thread,
    "mybb_mod_approve_post": handle_mod_approve_post,
    "mybb_mod_soft_delete_thread": handle_mod_soft_delete_thread,
    "mybb_mod_soft_delete_post": handle_mod_soft_delete_post,
    "mybb_modlog_list": handle_modlog_list,
    "mybb_modlog_add": handle_modlog_add,
}
