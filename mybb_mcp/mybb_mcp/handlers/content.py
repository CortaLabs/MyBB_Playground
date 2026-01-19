"""Content handlers for MyBB MCP tools (forums, threads, posts)."""

from datetime import datetime
import time
from typing import Any


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

    fid = db.create_forum(
        name=name,
        description=args.get("description", ""),
        forum_type=args.get("type", "f"),
        pid=args.get("pid", 0),
        parentlist=args.get("parentlist", ""),
        disporder=args.get("disporder", 1)
    )

    return f"# Forum Created\n\nForum '{name}' created with FID: {fid}"


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

    # Build kwargs from args
    updates = {}
    for key in ['name', 'description', 'type', 'disporder', 'active', 'open']:
        if key in args and args[key] is not None:
            updates[key] = args[key]

    if not updates:
        return "Error: No update fields provided."

    success = db.update_forum(fid, **updates)
    if success:
        return f"# Forum Updated\n\nForum {fid} updated successfully."
    else:
        return f"Error: Failed to update forum {fid}."


async def handle_forum_delete(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Delete a forum.

    Args:
        args: Tool arguments containing 'fid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message

    Note:
        Does not handle content migration. Ensure forum is empty first.
    """
    fid = args.get("fid")
    if not fid:
        return "Error: 'fid' is required."

    # Check if forum has content
    forum = db.get_forum(fid)
    if not forum:
        return f"Error: Forum {fid} not found."

    if forum['threads'] > 0 or forum['posts'] > 0:
        return (
            f"# Cannot Delete Forum\n\n"
            f"Forum {fid} has {forum['threads']} threads and {forum['posts']} posts.\n"
            f"Please move or delete all content first."
        )

    success = db.delete_forum(fid)
    if success:
        return f"# Forum Deleted\n\nForum {fid} deleted successfully."
    else:
        return f"Error: Failed to delete forum {fid}."


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

    uid = args.get("uid", 1)
    username = args.get("username", "Admin")
    prefix = args.get("prefix", 0)

    # Atomic creation: first post, then thread
    # Create the post first (we need its pid for thread.firstpost)
    pid = db.create_post(
        tid=0,  # Temporary, will update after thread creation
        fid=fid,
        subject=subject,
        message=message,
        uid=uid,
        username=username
    )

    # Create the thread with the first post pid
    tid = db.create_thread(
        fid=fid,
        subject=subject,
        uid=uid,
        username=username,
        firstpost_pid=pid,
        message=message,
        prefix=prefix
    )

    # Update the post's tid
    db.update_post_field(pid, "tid", tid)

    # Update forum counters
    db.update_forum_counters(fid, threads_delta=1, posts_delta=1)

    return f"# Thread Created\n\nThread '{subject}' created with TID: {tid} (First post PID: {pid})"


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

    # Build kwargs from args
    updates = {}
    for key in ['subject', 'prefix', 'fid', 'closed', 'sticky', 'visible']:
        if key in args and args[key] is not None:
            updates[key] = args[key]

    if not updates:
        return "Error: No update fields provided."

    success = db.update_thread(tid, **updates)
    if success:
        return f"# Thread Updated\n\nThread {tid} updated successfully."
    else:
        return f"Error: Failed to update thread {tid}."


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

    # Get thread info for counter updates
    thread = db.get_thread(tid)
    if not thread:
        return f"Error: Thread {tid} not found."

    # Delete thread
    success = db.delete_thread(tid, soft=soft)
    if success:
        # Update forum counters (only for soft delete, hard delete should handle separately)
        if soft:
            # Soft delete: decrement by making negative (threads counter stays same in MyBB)
            # Actually, MyBB keeps soft-deleted in counters until permanent delete
            pass
        else:
            # Hard delete: update counters
            post_count = thread['replies'] + 1  # replies + first post
            db.update_forum_counters(thread['fid'], threads_delta=-1, posts_delta=-post_count)

        delete_type = "soft deleted" if soft else "permanently deleted"
        return f"# Thread Deleted\n\nThread {tid} {delete_type} successfully."
    else:
        return f"Error: Failed to delete thread {tid}."


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

    # Get thread info
    thread = db.get_thread(tid)
    if not thread:
        return f"Error: Thread {tid} not found."

    old_fid = thread['fid']
    if old_fid == new_fid:
        return "Error: Thread is already in that forum."

    # Move thread
    success = db.move_thread(tid, new_fid)
    if success:
        # Update counters for both forums
        post_count = thread['replies'] + 1
        db.update_forum_counters(old_fid, threads_delta=-1, posts_delta=-post_count)
        db.update_forum_counters(new_fid, threads_delta=1, posts_delta=post_count)

        # Update all posts in thread to new forum
        db.update_posts_by_thread(tid, fid=new_fid)

        return f"# Thread Moved\n\nThread {tid} moved from forum {old_fid} to {new_fid}."
    else:
        return f"Error: Failed to move thread {tid}."


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

    # Get thread info
    thread = db.get_thread(tid)
    if not thread:
        return f"Error: Thread {tid} not found."

    subject = args.get("subject", f"RE: {thread['subject']}")
    uid = args.get("uid", 1)
    username = args.get("username", "Admin")
    replyto = args.get("replyto", 0)

    # Create post
    pid = db.create_post(
        tid=tid,
        fid=thread['fid'],
        subject=subject,
        message=message,
        uid=uid,
        username=username,
        replyto=replyto
    )

    # Update counters
    db.update_thread_counters(tid, replies_delta=1)
    db.update_forum_counters(thread['fid'], posts_delta=1)

    # Update thread lastpost
    dateline = int(time.time())
    db.update_thread_lastpost(tid, dateline, username, uid)

    return f"# Post Created\n\nPost created with PID: {pid} in thread {tid}"


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
    edituid = args.get("edituid")
    editreason = args.get("editreason", "")

    if not any([message, subject]):
        return "Error: Provide at least 'message' or 'subject' to update."

    success = db.update_post(
        pid=pid,
        message=message,
        subject=subject,
        edituid=edituid,
        editreason=editreason
    )

    if success:
        return f"# Post Updated\n\nPost {pid} updated successfully."
    else:
        return f"Error: Failed to update post {pid}."


async def handle_post_delete(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Delete a post (soft delete by default, updates counters).

    Args:
        args: Tool arguments containing 'pid' and optional 'soft' parameter
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

    if not pid:
        return "Error: 'pid' is required."

    # Get post info for counter updates
    post = db.get_post(pid)
    if not post:
        return f"Error: Post {pid} not found."

    # Don't allow deleting first post (should delete thread instead)
    thread = db.get_thread(post['tid'])
    if thread and thread['firstpost'] == pid:
        return "Error: Cannot delete first post. Delete the thread instead."

    # Delete post
    success = db.delete_post(pid, soft=soft)
    if success:
        # Update counters (only for hard delete)
        if not soft:
            db.update_thread_counters(post['tid'], replies_delta=-1)
            db.update_forum_counters(post['fid'], posts_delta=-1)

        delete_type = "soft deleted" if soft else "permanently deleted"
        return f"# Post Deleted\n\nPost {pid} {delete_type} successfully."
    else:
        return f"Error: Failed to delete post {pid}."


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
