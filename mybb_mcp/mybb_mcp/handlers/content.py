"""Content handlers for MyBB MCP tools (forums, threads, posts)."""

from datetime import datetime
import time
from typing import Any

from ..bridge import MyBBBridgeClient


# ==================== Forum Handlers ====================

async def handle_forum_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all forums with hierarchy information.

    Args:
        args: Tool arguments (unused)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Forums as markdown table
    """
    forums = db.list_forums()
    if not forums:
        return "No forums found."

    lines = ["# MyBB Forums\n", "| FID | Name | Type | Parent | Threads | Posts |", "|-----|------|------|--------|---------|-------|"]
    for f in forums:
        forum_type = "Category" if f['type'] == 'c' else "Forum"
        lines.append(f"| {f['fid']} | {f['name']} | {forum_type} | {f['pid']} | {f['threads']} | {f['posts']} |")
    return "\n".join(lines)


async def handle_forum_read(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get forum details by fid.

    Args:
        args: Tool arguments containing 'fid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Forum details as markdown
    """
    fid = args.get("fid")
    if not fid:
        return "Error: 'fid' is required."

    forum = db.get_forum(fid)
    if not forum:
        return f"Forum {fid} not found."

    forum_type = "Category" if forum['type'] == 'c' else "Forum"
    status = "Active" if forum['active'] else "Inactive"
    posting = "Open" if forum['open'] else "Closed"

    return (
        f"# Forum: {forum['name']}\n\n"
        f"**FID**: {forum['fid']}\n"
        f"**Type**: {forum_type}\n"
        f"**Description**: {forum['description']}\n"
        f"**Parent**: {forum['pid']}\n"
        f"**Status**: {status} | {posting}\n"
        f"**Order**: {forum['disporder']}\n\n"
        f"## Statistics\n"
        f"- Threads: {forum['threads']}\n"
        f"- Posts: {forum['posts']}\n"
        f"- Unapproved Threads: {forum['unapprovedthreads']}\n"
        f"- Unapproved Posts: {forum['unapprovedposts']}"
    )


async def handle_forum_create(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Create a new forum or category.

    Args:
        args: Tool arguments containing 'name' and optional parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success message with forum FID
    """
    name = args.get("name")
    if not name:
        return "Error: 'name' is required."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "forum:create" not in supported:
        return "Error: Bridge does not support 'forum:create' yet."

    result = await bridge.call_async(
        "forum:create",
        name=name,
        description=args.get("description", ""),
        type=args.get("type", "f"),
        pid=args.get("pid", 0),
        disporder=args.get("disporder", 1),
        active=args.get("active"),
        open=args.get("open"),
    )

    if not result.success:
        return f"Error: Bridge forum:create failed: {result.error or 'unknown error'}"

    fid = result.data.get("fid")
    return f"# Forum Created (Bridge)\n\nForum '{name}' created with FID: {fid}"


async def handle_forum_update(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Update forum properties.

    Args:
        args: Tool arguments containing 'fid' and update fields
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message
    """
    fid = args.get("fid")
    if not fid:
        return "Error: 'fid' is required."

    updates = {}
    for key in ['name', 'description', 'type', 'pid', 'disporder', 'active', 'open']:
        if key in args and args[key] is not None:
            updates[key] = args[key]

    if not updates:
        return "Error: No update fields provided."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "forum:update" not in supported:
        return "Error: Bridge does not support 'forum:update' yet."

    result = await bridge.call_async("forum:update", fid=fid, **updates)
    if not result.success:
        return f"Error: Bridge forum:update failed: {result.error or 'unknown error'}"

    return f"# Forum Updated (Bridge)\n\nForum {fid} updated successfully."


async def handle_forum_delete(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Delete a forum.

    Args:
        args: Tool arguments containing 'fid' parameter
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message

    Note:
        By default, does not delete forums with content. Use force_content_deletion=True
        to delete content via MyBB's Moderation class (proper cleanup with hooks).
        Uses bridge for proper cache invalidation.
    """
    fid = args.get("fid")
    if not fid:
        return "Error: 'fid' is required."

    force_content_deletion = args.get("force_content_deletion", False)

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "forum:delete" not in supported:
        return "Error: Bridge does not support 'forum:delete' yet."

    result = await bridge.call_async("forum:delete", fid=fid, force_content_deletion=force_content_deletion)

    if not result.success:
        # Bridge returns detailed error for content check
        error_msg = result.error or 'unknown error'
        if "has content" in error_msg.lower():
            return f"Error: {error_msg}\n\nUse `force_content_deletion=True` to delete forum and its content."
        return f"Error: Bridge forum:delete failed: {error_msg}"

    actions = result.data.get("actions_taken", [])
    content_deleted = "content_deleted_via_moderation" in actions

    msg = f"# Forum Deleted (Bridge)\n\nForum {fid} deleted successfully."
    if content_deleted:
        msg += "\n\n**Note:** Forum content was deleted via MyBB Moderation class."
    return msg


# ==================== Thread Handlers ====================

async def handle_thread_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List threads in a forum with pagination.

    Args:
        args: Tool arguments containing optional 'fid', 'limit', 'offset' parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Threads as markdown table
    """
    fid = args.get("fid")
    limit = args.get("limit", 50)
    offset = args.get("offset", 0)

    threads = db.list_threads(fid=fid, limit=limit, offset=offset)
    if not threads:
        return "No threads found."

    lines = [f"# Threads ({len(threads)} found)\n", "| TID | Forum | Subject | Author | Replies | Views | Last Post |", "|-----|-------|---------|--------|---------|-------|-----------|"]

    for t in threads:
        lastpost = datetime.fromtimestamp(t['lastpost']).strftime('%Y-%m-%d %H:%M')
        lines.append(f"| {t['tid']} | {t['fid']} | {t['subject']} | {t['username']} | {t['replies']} | {t['views']} | {lastpost} |")

    return "\n".join(lines)


async def handle_thread_read(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get thread details by tid.

    Args:
        args: Tool arguments containing 'tid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Thread details as markdown
    """
    tid = args.get("tid")
    if not tid:
        return "Error: 'tid' is required."

    thread = db.get_thread(tid)
    if not thread:
        return f"Thread {tid} not found."

    created = datetime.fromtimestamp(thread['dateline']).strftime('%Y-%m-%d %H:%M')
    lastpost = datetime.fromtimestamp(thread['lastpost']).strftime('%Y-%m-%d %H:%M')
    visibility = {1: "Visible", 0: "Unapproved", -1: "Deleted"}.get(thread['visible'], "Unknown")

    return (
        f"# Thread: {thread['subject']}\n\n"
        f"**TID**: {thread['tid']}\n"
        f"**Forum**: {thread['fid']}\n"
        f"**Author**: {thread['username']} (UID: {thread['uid']})\n"
        f"**Created**: {created}\n"
        f"**Status**: {visibility} | {'Closed' if thread['closed'] else 'Open'} | {'Sticky' if thread['sticky'] else 'Normal'}\n\n"
        f"## Statistics\n"
        f"- Replies: {thread['replies']}\n"
        f"- Views: {thread['views']}\n"
        f"- First Post: {thread['firstpost']}\n"
        f"- Last Post: {lastpost} by {thread['lastposter']}\n"
        f"- Unapproved Posts: {thread['unapprovedposts']}\n"
        f"- Deleted Posts: {thread['deletedposts']}"
    )


async def handle_thread_create(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Create a new thread with first post (atomic operation).

    Args:
        args: Tool arguments containing 'fid', 'subject', 'message' and optional parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success message with thread TID and first post PID
    """
    fid = args.get("fid")
    subject = args.get("subject")
    message = args.get("message")

    if not all([fid, subject, message]):
        return "Error: 'fid', 'subject', and 'message' are required."

    if args.get("prefix", 0):
        return "Error: 'prefix' is not supported by the bridge yet. Use 0 or omit."

    uid = args.get("uid", 1)
    username = args.get("username", "Admin")

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "thread:create" not in supported:
        return "Error: Bridge does not support 'thread:create' yet."

    result = await bridge.call_async(
        "thread:create",
        fid=fid,
        subject=subject,
        message=message,
        uid=uid,
        username=username,
    )

    if not result.success:
        details = result.data.get("errors") if isinstance(result.data, dict) else None
        return f"Error: Bridge thread:create failed: {result.error or 'unknown error'}{f' | {details}' if details else ''}"

    tid = result.data.get("tid")
    pid = result.data.get("pid")
    visibility = result.data.get("visibility")
    return (
        f"# Thread Created (Bridge)\n\n"
        f"Thread '{subject}' created with TID: {tid} (First post PID: {pid})\n"
        f"Visibility: {visibility}"
    )


async def handle_thread_update(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Update thread properties.

    Args:
        args: Tool arguments containing 'tid' and update fields
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message
    """
    tid = args.get("tid")
    if not tid:
        return "Error: 'tid' is required."

    if args.get("prefix") not in (None, 0):
        return "Error: 'prefix' updates are not supported by the bridge yet."
    if args.get("fid") is not None:
        return "Error: 'fid' updates are not supported by the bridge yet."

    subject = args.get("subject")
    closed = args.get("closed")
    sticky = args.get("sticky")
    visible = args.get("visible")

    if subject is None and closed is None and sticky is None and visible is None:
        return "Error: No update fields provided."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "thread:edit" not in supported:
        return "Error: Bridge does not support 'thread:edit' yet."

    result = await bridge.call_async(
        "thread:edit",
        tid=tid,
        subject=subject,
        closed=closed,
        sticky=sticky,
        visible=visible,
    )

    if not result.success:
        details = result.data.get("errors") if isinstance(result.data, dict) else None
        return f"Error: Bridge thread:edit failed: {result.error or 'unknown error'}{f' | {details}' if details else ''}"

    return f"# Thread Updated (Bridge)\n\nThread {tid} updated successfully."


async def handle_thread_delete(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Delete a thread (soft delete by default, updates counters).

    Args:
        args: Tool arguments containing 'tid' and optional 'soft' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message
    """
    tid = args.get("tid")
    soft = args.get("soft", True)

    if not tid:
        return "Error: 'tid' is required."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "thread:delete" not in supported:
        return "Error: Bridge does not support 'thread:delete' yet."

    result = await bridge.call_async(
        "thread:delete",
        tid=tid,
        soft=True if soft else None,
    )

    if not result.success:
        details = result.data.get("errors") if isinstance(result.data, dict) else None
        return f"Error: Bridge thread:delete failed: {result.error or 'unknown error'}{f' | {details}' if details else ''}"

    delete_type = "soft deleted" if soft else "permanently deleted"
    return f"# Thread Deleted (Bridge)\n\nThread {tid} {delete_type} successfully."


async def handle_thread_move(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Move thread to a different forum (updates counters).

    Args:
        args: Tool arguments containing 'tid' and 'new_fid' parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message
    """
    tid = args.get("tid")
    new_fid = args.get("new_fid")

    if not tid or not new_fid:
        return "Error: 'tid' and 'new_fid' are required."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "thread:move" not in supported:
        return "Error: Bridge does not support 'thread:move' yet."

    result = await bridge.call_async(
        "thread:move",
        tid=tid,
        new_fid=new_fid,
    )

    if not result.success:
        details = result.data.get("errors") if isinstance(result.data, dict) else None
        return f"Error: Bridge thread:move failed: {result.error or 'unknown error'}{f' | {details}' if details else ''}"

    return f"# Thread Moved (Bridge)\n\nThread {tid} moved to forum {new_fid}."


# ==================== Post Handlers ====================

async def handle_post_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List posts in a thread with pagination.

    Args:
        args: Tool arguments containing optional 'tid', 'limit', 'offset' parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Posts as markdown table
    """
    tid = args.get("tid")
    limit = args.get("limit", 50)
    offset = args.get("offset", 0)

    posts = db.list_posts(tid=tid, limit=limit, offset=offset)
    if not posts:
        return "No posts found."

    lines = [f"# Posts ({len(posts)} found)\n", "| PID | TID | Author | Date | Subject | Preview |", "|-----|-----|--------|------|---------|---------|"]

    for p in posts:
        date = datetime.fromtimestamp(p['dateline']).strftime('%Y-%m-%d')
        preview = p['message'][:50].replace('\n', ' ').replace('|', '\\|')
        if len(p['message']) > 50:
            preview += "..."
        lines.append(f"| {p['pid']} | {p['tid']} | {p['username']} | {date} | {p['subject']} | {preview} |")

    return "\n".join(lines)


async def handle_post_read(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get post details by pid.

    Args:
        args: Tool arguments containing 'pid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Post details as markdown
    """
    pid = args.get("pid")
    if not pid:
        return "Error: 'pid' is required."

    post = db.get_post(pid)
    if not post:
        return f"Post {pid} not found."

    created = datetime.fromtimestamp(post['dateline']).strftime('%Y-%m-%d %H:%M')
    visibility = {1: "Visible", 0: "Unapproved", -1: "Deleted"}.get(post['visible'], "Unknown")

    edit_info = ""
    if post['edituid']:
        edit_time = datetime.fromtimestamp(post['edittime']).strftime('%Y-%m-%d %H:%M')
        edit_info = f"\n**Last Edited**: {edit_time} by UID {post['edituid']}"
        if post['editreason']:
            edit_info += f"\n**Edit Reason**: {post['editreason']}"

    return (
        f"# Post {pid}\n\n"
        f"**Thread**: {post['tid']}\n"
        f"**Forum**: {post['fid']}\n"
        f"**Subject**: {post['subject']}\n"
        f"**Author**: {post['username']} (UID: {post['uid']})\n"
        f"**Posted**: {created}\n"
        f"**Status**: {visibility}{edit_info}\n\n"
        f"## Message\n\n{post['message']}"
    )


async def handle_post_create(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Create a new post in a thread (updates counters).

    Args:
        args: Tool arguments containing 'tid', 'message' and optional parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success message with post PID
    """
    tid = args.get("tid")
    message = args.get("message")

    if not tid or not message:
        return "Error: 'tid' and 'message' are required."

    subject = args.get("subject")
    uid = args.get("uid", 1)
    username = args.get("username", "Admin")
    replyto = args.get("replyto", 0)

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "post:create" not in supported:
        return "Error: Bridge does not support 'post:create' yet."

    result = await bridge.call_async(
        "post:create",
        tid=tid,
        message=message,
        subject=subject,
        uid=uid,
        username=username,
        replyto=replyto,
    )

    if not result.success:
        details = result.data.get("errors") if isinstance(result.data, dict) else None
        return f"Error: Bridge post:create failed: {result.error or 'unknown error'}{f' | {details}' if details else ''}"

    pid = result.data.get("pid")
    visibility = result.data.get("visibility")
    return (
        f"# Post Created (Bridge)\n\n"
        f"Post created with PID: {pid} in thread {tid}\n"
        f"Visibility: {visibility}"
    )


async def handle_post_update(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Edit a post (tracks edit history).

    Args:
        args: Tool arguments containing 'pid' and update fields
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message
    """
    pid = args.get("pid")
    if not pid:
        return "Error: 'pid' is required."

    message = args.get("message")
    subject = args.get("subject")
    edit_uid = args.get("edit_uid")
    edituid = edit_uid if edit_uid is not None else args.get("edituid")
    editreason = args.get("editreason", "")
    signature = args.get("signature")
    disablesmilies = args.get("disablesmilies")

    if not any([message, subject]):
        return "Error: Provide at least 'message' or 'subject' to update."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "post:edit" not in supported:
        return "Error: Bridge does not support 'post:edit' yet."

    result = await bridge.call_async(
        "post:edit",
        pid=pid,
        message=message,
        subject=subject,
        edituid=edituid,
        editreason=editreason,
        signature=signature,
        disablesmilies=disablesmilies,
    )

    if not result.success:
        details = result.data.get("errors") if isinstance(result.data, dict) else None
        return f"Error: Bridge post:edit failed: {result.error or 'unknown error'}{f' | {details}' if details else ''}"

    visibility = result.data.get("visibility")
    return (
        f"# Post Updated (Bridge)\n\n"
        f"Post {pid} updated successfully.\n"
        f"Visibility: {visibility}"
    )


async def handle_post_delete(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Delete or restore a post (soft delete by default, updates counters).

    Args:
        args: Tool arguments containing 'pid' and optional 'soft'/'restore' parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message

    Note:
        Cannot delete first post of a thread. Delete the thread instead.
    """
    pid = args.get("pid")
    soft = args.get("soft", True)
    restore = args.get("restore", False)

    if not pid:
        return "Error: 'pid' is required."

    # Read-only check for first post (delete thread instead)
    post = db.get_post(pid)
    if not post:
        return f"Error: Post {pid} not found."
    thread = db.get_thread(post['tid'])
    if not restore and thread and thread['firstpost'] == pid:
        return "Error: Cannot delete first post. Delete the thread instead."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "post:delete" not in supported:
        return "Error: Bridge does not support 'post:delete' yet."

    result = await bridge.call_async(
        "post:delete",
        pid=pid,
        restore=True if restore else None,
        soft=True if (soft and not restore) else None,
    )

    if not result.success:
        details = result.data.get("errors") if isinstance(result.data, dict) else None
        return f"Error: Bridge post:delete failed: {result.error or 'unknown error'}{f' | {details}' if details else ''}"

    if restore:
        return f"# Post Restored (Bridge)\n\nPost {pid} restored successfully."
    delete_type = "soft deleted" if soft else "permanently deleted"
    return f"# Post Deleted (Bridge)\n\nPost {pid} {delete_type} successfully."


# Handler registry for content tools
CONTENT_HANDLERS = {
    # Forum handlers (5)
    "mybb_forum_list": handle_forum_list,
    "mybb_forum_read": handle_forum_read,
    "mybb_forum_create": handle_forum_create,
    "mybb_forum_update": handle_forum_update,
    "mybb_forum_delete": handle_forum_delete,
    # Thread handlers (6)
    "mybb_thread_list": handle_thread_list,
    "mybb_thread_read": handle_thread_read,
    "mybb_thread_create": handle_thread_create,
    "mybb_thread_update": handle_thread_update,
    "mybb_thread_delete": handle_thread_delete,
    "mybb_thread_move": handle_thread_move,
    # Post handlers (6)
    "mybb_post_list": handle_post_list,
    "mybb_post_read": handle_post_read,
    "mybb_post_create": handle_post_create,
    "mybb_post_update": handle_post_update,
    "mybb_post_delete": handle_post_delete,
}
