"""Moderation handlers for MyBB MCP tools."""

from datetime import datetime
from typing import Any

from ..bridge import MyBBBridgeClient


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

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "mod:close_thread" not in supported:
        return "Error: Bridge does not support 'mod:close_thread' yet."

    result = await bridge.call_async("mod:close_thread", tid=tid, closed=1 if closed else 0)
    if not result.success:
        return f"Error: Bridge mod:close_thread failed: {result.error or 'unknown error'}"

    status = "closed" if closed else "opened"
    return f"# Thread {status.title()} (Bridge)\n\nThread {tid} has been {status} successfully."


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

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "mod:stick_thread" not in supported:
        return "Error: Bridge does not support 'mod:stick_thread' yet."

    result = await bridge.call_async("mod:stick_thread", tid=tid, sticky=1 if sticky else 0)
    if not result.success:
        return f"Error: Bridge mod:stick_thread failed: {result.error or 'unknown error'}"

    status = "sticked" if sticky else "unsticked"
    return f"# Thread {status.title()} (Bridge)\n\nThread {tid} has been {status} successfully."


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

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "mod:approve_thread" not in supported:
        return "Error: Bridge does not support 'mod:approve_thread' yet."

    result = await bridge.call_async("mod:approve_thread", tid=tid, approve=1 if approve else 0)
    if not result.success:
        return f"Error: Bridge mod:approve_thread failed: {result.error or 'unknown error'}"

    status = "approved" if approve else "unapproved"
    return f"# Thread {status.title()} (Bridge)\n\nThread {tid} has been {status} successfully."


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

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "mod:approve_post" not in supported:
        return "Error: Bridge does not support 'mod:approve_post' yet."

    result = await bridge.call_async("mod:approve_post", pid=pid, approve=1 if approve else 0)
    if not result.success:
        return f"Error: Bridge mod:approve_post failed: {result.error or 'unknown error'}"

    status = "approved" if approve else "unapproved"
    return f"# Post {status.title()} (Bridge)\n\nPost {pid} has been {status} successfully."


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

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    action = "mod:soft_delete_thread" if delete else "mod:restore_thread"
    if action not in supported:
        return f"Error: Bridge does not support '{action}' yet."

    result = await bridge.call_async(action, tid=tid)
    if not result.success:
        return f"Error: Bridge {action} failed: {result.error or 'unknown error'}"

    status = "soft deleted" if delete else "restored"
    return f"# Thread {status.title()} (Bridge)\n\nThread {tid} has been {status} successfully."


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

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    action = "mod:soft_delete_post" if delete else "mod:restore_post"
    if action not in supported:
        return f"Error: Bridge does not support '{action}' yet."

    result = await bridge.call_async(action, pid=pid)
    if not result.success:
        return f"Error: Bridge {action} failed: {result.error or 'unknown error'}"

    status = "soft deleted" if delete else "restored"
    return f"# Post {status.title()} (Bridge)\n\nPost {pid} has been {status} successfully."


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
        "| User ID | Forum | Thread | Post | Action | Date |",
        "|---------|-------|--------|------|--------|------|"
    ]

    for entry in entries:
        dateline = entry.get('dateline', 0)
        date = datetime.fromtimestamp(dateline).strftime('%Y-%m-%d %H:%M') if dateline else "N/A"
        lines.append(
            f"| {entry.get('uid', 0)} | {entry.get('fid', 0)} | {entry.get('tid', 0)} | {entry.get('pid', 0)} | {entry.get('action', '')} | {date} |"
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

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "modlog:add" not in supported:
        return "Error: Bridge does not support 'modlog:add' yet."

    result = await bridge.call_async(
        "modlog:add",
        uid=uid,
        logaction=action,
        fid=fid,
        tid=tid,
        pid=pid,
        data=data,
        ipaddress=ipaddress,
    )

    if not result.success:
        return f"Error: Bridge modlog:add failed: {result.error or 'unknown error'}"

    return "# Moderation Log Entry Added (Bridge)\n\nLog entry created successfully."


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
