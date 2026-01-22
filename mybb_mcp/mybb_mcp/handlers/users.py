"""User management handlers for MyBB MCP tools."""

from typing import Any

from ..bridge import MyBBBridgeClient


# ==================== User Handlers ====================

async def handle_user_get(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get user by UID or username.

    Args:
        args: Tool arguments containing:
            - uid: User ID (optional, one of uid/username required)
            - username: Username (optional, one of uid/username required)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        User information as markdown or error message
    """
    uid = args.get("uid")
    username = args.get("username")

    if not uid and not username:
        return "Error: Either 'uid' or 'username' is required."

    user = db.get_user(uid=uid, username=username, sanitize=True)

    if not user:
        identifier = f"UID {uid}" if uid else f"username '{username}'"
        return f"Error: User not found ({identifier})."

    # Format user information
    lines = [
        "# User Information\n",
        f"**User ID:** {user['uid']}",
        f"**Username:** {user['username']}",
        f"**Usergroup:** {user['usergroup']}",
        f"**Email:** {user.get('email', 'N/A')}",
        f"**Post Count:** {user.get('postnum', 0)}",
        f"**Thread Count:** {user.get('threadnum', 0)}",
        f"**Registration Date:** {user.get('regdate', 'N/A')}",
        f"**User Title:** {user.get('usertitle', 'N/A')}",
    ]

    if user.get('additionalgroups'):
        lines.append(f"**Additional Groups:** {user['additionalgroups']}")

    return "\n".join(lines)


async def handle_user_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List users with optional filters.

    Args:
        args: Tool arguments containing:
            - usergroup: Optional filter by usergroup ID
            - limit: Maximum users to return (default 50)
            - offset: Number of users to skip (default 0)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        User list as markdown table
    """
    usergroup = args.get("usergroup")
    limit = args.get("limit", 50)
    offset = args.get("offset", 0)

    users = db.list_users(usergroup=usergroup, limit=limit, offset=offset)

    if not users:
        return "No users found."

    lines = [
        f"# Users ({len(users)} found)\n",
        "| UID | Username | Usergroup | Posts | Threads |",
        "|-----|----------|-----------|-------|---------|"
    ]

    for user in users:
        lines.append(
            f"| {user['uid']} | {user['username']} | {user['usergroup']} | {user.get('postnum', 0)} | {user.get('threadnum', 0)} |"
        )

    return "\n".join(lines)


async def handle_user_update_group(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Update user's usergroup and optionally additional groups.

    Args:
        args: Tool arguments containing:
            - uid: User ID (required)
            - usergroup: Primary usergroup ID (required)
            - additionalgroups: Comma-separated additional group IDs (optional)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message as markdown
    """
    uid = args.get("uid")
    usergroup = args.get("usergroup")
    additionalgroups = args.get("additionalgroups")

    if not uid or not usergroup:
        return "Error: 'uid' and 'usergroup' are required."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "user:update_group" not in supported:
        return "Error: Bridge does not support 'user:update_group' yet."

    result = await bridge.call_async(
        "user:update_group",
        uid=uid,
        usergroup=usergroup,
        additionalgroups=additionalgroups,
    )

    if not result.success:
        return f"Error: Bridge user:update_group failed: {result.error or 'unknown error'}"

    return f"# User Group Updated (Bridge)\n\nUser {uid} has been assigned to usergroup {usergroup}."


async def handle_user_ban(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Add user to banned list.

    Args:
        args: Tool arguments containing:
            - uid: User ID to ban (required)
            - gid: Banned usergroup ID (required)
            - admin: Admin user ID performing the ban (required)
            - dateline: Ban timestamp as Unix epoch (required)
            - bantime: Ban duration string (default "---")
            - reason: Ban reason (default "")
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message as markdown
    """
    uid = args.get("uid")
    gid = args.get("gid")
    admin = args.get("admin")
    dateline = args.get("dateline")
    bantime = args.get("bantime", "---")
    reason = args.get("reason", "")

    if not uid or not gid or not admin or not dateline:
        return "Error: 'uid', 'gid', 'admin', and 'dateline' are required."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "user:ban" not in supported:
        return "Error: Bridge does not support 'user:ban' yet."

    result = await bridge.call_async(
        "user:ban",
        uid=uid,
        gid=gid,
        admin=admin,
        dateline=dateline,
        bantime=bantime,
        reason=reason,
    )

    if not result.success:
        return f"Error: Bridge user:ban failed: {result.error or 'unknown error'}"

    return f"# User Banned (Bridge)\n\nUser {uid} has been banned."


async def handle_user_unban(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Remove user from banned list.

    Args:
        args: Tool arguments containing:
            - uid: User ID to unban (required)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message as markdown
    """
    uid = args.get("uid")

    if not uid:
        return "Error: 'uid' is required."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "user:unban" not in supported:
        return "Error: Bridge does not support 'user:unban' yet."

    result = await bridge.call_async("user:unban", uid=uid)
    if not result.success:
        return f"Error: Bridge user:unban failed: {result.error or 'unknown error'}"

    return f"# User Unbanned (Bridge)\n\nUser {uid} has been unbanned successfully."


async def handle_usergroup_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all usergroups.

    Args:
        args: Tool arguments (none required)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Usergroup list as markdown table
    """
    groups = db.list_usergroups()

    if not groups:
        return "No usergroups found."

    lines = [
        f"# Usergroups ({len(groups)} total)\n",
        "| GID | Title | Type |",
        "|-----|-------|------|"
    ]

    for group in groups:
        group_type = "Admin" if group.get('cancp') == 1 else ("Moderator" if group.get('canmodcp') == 1 else "User")
        lines.append(f"| {group['gid']} | {group['title']} | {group_type} |")

    return "\n".join(lines)


# Handler registry for user tools
USER_HANDLERS = {
    "mybb_user_get": handle_user_get,
    "mybb_user_list": handle_user_list,
    "mybb_user_update_group": handle_user_update_group,
    "mybb_user_ban": handle_user_ban,
    "mybb_user_unban": handle_user_unban,
    "mybb_usergroup_list": handle_usergroup_list,
}
