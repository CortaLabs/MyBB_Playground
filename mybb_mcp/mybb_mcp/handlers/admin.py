"""Admin and cache management handlers for MyBB MCP tools."""

from typing import Any
from datetime import datetime

from ..bridge import MyBBBridgeClient


# ==================== Settings Handlers ====================

async def handle_setting_get(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get a MyBB setting by name.

    Args:
        args: Tool arguments containing 'name' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Setting details as formatted markdown
    """
    setting_name = args.get("name")
    if not setting_name:
        return "Error: 'name' parameter is required."

    setting = db.get_setting(setting_name)
    if not setting:
        return f"Setting '{setting_name}' not found."

    lines = [
        f"# Setting: {setting['title']}\n",
        f"**Name:** `{setting['name']}`",
        f"**Value:** `{setting['value']}`",
        f"**Description:** {setting['description']}",
        f"**Group ID:** {setting['gid']}",
        f"**Display Order:** {setting['disporder']}",
        f"**Options Code:** {setting['optionscode']}",
    ]
    return "\n".join(lines)


async def handle_setting_set(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Update a MyBB setting value.

    Args:
        args: Tool arguments containing 'name' and 'value' parameters
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Success message or error
    """
    setting_name = args.get("name")
    value = args.get("value")
    if not setting_name or value is None:
        return "Error: 'name' and 'value' parameters are required."

    # Use bridge for setting update
    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"

    supported = info.data.get("supported_actions", [])
    if "setting:set" not in supported:
        return "Error: Bridge does not support 'setting:set' yet."

    result = await bridge.call_async("setting:set", name=setting_name, value=value)
    if not result.success:
        return f"Error: Bridge setting:set failed: {result.error or 'unknown error'}"

    return f"# Setting Updated (Bridge)\n\nSetting '{setting_name}' updated to '{value}'. Settings cache rebuilt automatically."


async def handle_setting_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all MyBB settings or filter by group.

    Args:
        args: Tool arguments containing optional 'gid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Settings list as markdown table
    """
    gid = args.get("gid")
    settings = db.list_settings(gid=gid)

    if not settings:
        return "No settings found."

    lines = [f"# MyBB Settings ({len(settings)} total)\n"]
    if gid is not None:
        lines[0] = f"# MyBB Settings for Group {gid} ({len(settings)} total)\n"

    lines.extend([
        "| Name | Title | Value | Group |",
        "|------|-------|-------|-------|"
    ])

    for setting in settings[:100]:
        value_preview = setting['value'][:50] if setting['value'] else ""
        if len(setting['value']) > 50:
            value_preview += "..."
        lines.append(
            f"| {setting['name']} | {setting['title']} | {value_preview} | {setting['gid']} |"
        )

    if len(settings) > 100:
        lines.append(f"\n*...{len(settings) - 100} more*")

    return "\n".join(lines)


async def handle_settinggroup_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all MyBB setting groups.

    Args:
        args: Tool arguments (unused)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Setting groups as markdown table
    """
    groups = db.list_setting_groups()

    if not groups:
        return "No setting groups found."

    lines = [
        f"# MyBB Setting Groups ({len(groups)} total)\n",
        "| GID | Name | Title | Description |",
        "|-----|------|-------|-------------|"
    ]

    for group in groups:
        desc_preview = group['description'][:50] if group['description'] else ""
        if len(group['description']) > 50:
            desc_preview += "..."
        lines.append(
            f"| {group['gid']} | {group['name']} | {group['title']} | {desc_preview} |"
        )

    return "\n".join(lines)


# ==================== Cache Handlers ====================

async def handle_cache_read(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Read a MyBB cache entry.

    Args:
        args: Tool arguments containing 'title' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Cache data with size information
    """
    title = args.get("title")
    if not title:
        return "Error: 'title' parameter is required."

    cache_data = db.read_cache(title)
    if cache_data is None:
        return f"Cache '{title}' not found."

    # Return cache data with size info
    size = len(cache_data)
    lines = [
        f"# Cache: {title}\n",
        f"**Size:** {size} bytes",
        f"**Data Type:** PHP serialized",
        "\n```",
        cache_data[:1000] if len(cache_data) <= 1000 else cache_data[:1000] + "\n... (truncated)",
        "```"
    ]
    if size > 1000:
        lines.append(f"\n*Full size: {size} bytes (showing first 1000)*")

    return "\n".join(lines)


async def handle_cache_rebuild(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Rebuild (clear) MyBB cache entries.

    Args:
        args: Tool arguments containing optional 'cache_type' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success message with affected row count
    """
    cache_type = args.get("cache_type", "all")
    result = db.rebuild_cache(cache_type)

    return f"**{result['message']}** ({result['rows_affected']} cache entries cleared)\n\nMyBB will regenerate these caches on next access."


async def handle_cache_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all MyBB cache entries.

    Args:
        args: Tool arguments (unused)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Cache entries as markdown table with total size
    """
    caches = db.list_caches()

    if not caches:
        return "No cache entries found."

    lines = [
        f"# MyBB Cache Entries ({len(caches)} total)\n",
        "| Title | Size (bytes) |",
        "|-------|--------------|"
    ]

    for cache in caches:
        lines.append(f"| {cache['title']} | {cache['size']:,} |")

    total_size = sum(c['size'] for c in caches)
    lines.append(f"\n**Total Cache Size:** {total_size:,} bytes")

    return "\n".join(lines)


async def handle_cache_clear(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Clear a specific cache entry or all caches.

    Args:
        args: Tool arguments containing optional 'title' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success message or error
    """
    title = args.get("title")
    success = db.clear_cache(title)

    if not success:
        if title:
            return f"Cache '{title}' not found or already cleared."
        else:
            return "No caches found to clear."

    if title:
        return f"Cache '{title}' cleared successfully."
    else:
        return "All caches cleared successfully."


# ==================== Statistics Handlers ====================

async def handle_stats_forum(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get forum statistics.

    Args:
        args: Tool arguments (unused)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Forum statistics as formatted markdown
    """
    stats = db.get_forum_stats()

    lines = [
        "# Forum Statistics\n",
        f"**Total Users:** {stats['total_users']:,}",
        f"**Total Threads:** {stats['total_threads']:,}",
        f"**Total Posts:** {stats['total_posts']:,}",
    ]

    if stats['newest_member']:
        reg_date = datetime.fromtimestamp(stats['newest_member']['regdate']).strftime('%Y-%m-%d %H:%M:%S')
        lines.extend([
            "\n## Newest Member",
            f"**Username:** {stats['newest_member']['username']}",
            f"**UID:** {stats['newest_member']['uid']}",
            f"**Registered:** {reg_date}",
        ])

    return "\n".join(lines)


async def handle_stats_board(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get comprehensive board statistics.

    Args:
        args: Tool arguments (unused)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Board statistics as formatted markdown
    """
    stats = db.get_board_stats()

    lines = [
        "# Board Statistics\n",
        "## Overview",
        f"**Total Forums:** {stats['total_forums']:,}",
        f"**Total Users:** {stats['total_users']:,}",
        f"**Total Threads:** {stats['total_threads']:,}",
        f"**Total Posts:** {stats['total_posts']:,}",
        f"**Total Private Messages:** {stats['total_private_messages']:,}",
    ]

    if stats['latest_post']:
        post_date = datetime.fromtimestamp(stats['latest_post']['dateline']).strftime('%Y-%m-%d %H:%M:%S')
        lines.extend([
            "\n## Latest Post",
            f"**Subject:** {stats['latest_post']['subject']}",
            f"**Author:** {stats['latest_post']['username']}",
            f"**Date:** {post_date}",
            f"**Post ID:** {stats['latest_post']['pid']}",
            f"**Thread ID:** {stats['latest_post']['tid']}",
        ])

    if stats['most_active_forum']:
        lines.extend([
            "\n## Most Active Forum",
            f"**Name:** {stats['most_active_forum']['name']}",
            f"**Threads:** {stats['most_active_forum']['threads']:,}",
            f"**Posts:** {stats['most_active_forum']['posts']:,}",
            f"**Forum ID:** {stats['most_active_forum']['fid']}",
        ])

    return "\n".join(lines)


async def handle_bridge_health_check(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Run bridge health check / smoke test.

    Args:
        args: Tool arguments containing 'mode' and 'format' parameters
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Health check results as formatted markdown or JSON
    """
    mode = args.get("mode", "quick")
    output_format = args.get("format", "summary")

    if mode not in ("quick", "full"):
        return "Error: mode must be 'quick' or 'full'"

    # Use bridge for health check
    bridge = MyBBBridgeClient(config.mybb_root)
    result = await bridge.call_async("bridge:health_check", mode=mode)

    if not result.success:
        return f"Error: Health check failed: {result.error or 'Unknown error'}"

    data = result.data

    if output_format == "json":
        import json
        return json.dumps(data, indent=2)

    # Summary format
    health = data.get("health", "UNKNOWN")
    core = data.get("core", {})
    ctx = data.get("forum_context", {})
    subs = data.get("subsystems", {})

    health_icon = "✅" if health == "HEALTHY" else "⚠️" if health == "DEGRADED" else "❌"

    lines = [
        f"# Bridge Health Check - {health_icon} {health}\n",
        "━" * 40,
        f"**MyBB:** {core.get('mybb_version', '?')} | **PHP:** {core.get('php_version', '?')} | **DB:** {core.get('db_engine', '?')}",
        "",
        f"**Forum:** {ctx.get('board_name', 'Unknown')}",
        f"**Users:** {ctx.get('total_users', 0):,} | **Threads:** {ctx.get('total_threads', 0):,} | **Posts:** {ctx.get('total_posts', 0):,}",
        "",
        f"**Subsystems:** {len([s for s in subs.values() if s.get('read')])} / {len(subs)} OK",
        f"**Actions:** {data.get('action_count', 0)} supported",
    ]

    # Write tests summary if full mode
    write_tests = data.get("write_tests", {})
    if write_tests.get("enabled"):
        results = write_tests.get("results", {})
        passed = len([r for r in results.values() if r.get("pass")])
        total = len(results)
        duration = write_tests.get("duration_ms", 0)
        lines.append("")
        lines.append(f"**Write Tests:** {passed}/{total} PASS ({duration}ms)")

    # Issues if any
    issues = data.get("issues", [])
    if issues:
        lines.append("")
        lines.append("## Issues")
        for issue in issues:
            lines.append(f"  ⚠️ {issue}")

    return "\n".join(lines)


# ==================== Template Groups Handler ====================

async def handle_list_template_groups(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all MyBB template groups.

    Args:
        args: Tool arguments (unused)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Template groups as markdown table
    """
    with db.cursor() as cur:
        cur.execute(f"SELECT prefix, title FROM {db.table('templategroups')} ORDER BY title")
        groups = cur.fetchall()

    if not groups:
        return "No template groups found."

    lines = ["# Template Groups\n", "| Prefix | Title |", "|--------|-------|"]
    for g in groups:
        lines.append(f"| {g['prefix']} | {g['title']} |")
    return "\n".join(lines)


# Handler registry for admin tools
ADMIN_HANDLERS = {
    "mybb_setting_get": handle_setting_get,
    "mybb_setting_set": handle_setting_set,
    "mybb_setting_list": handle_setting_list,
    "mybb_settinggroup_list": handle_settinggroup_list,
    "mybb_cache_read": handle_cache_read,
    "mybb_cache_rebuild": handle_cache_rebuild,
    "mybb_cache_list": handle_cache_list,
    "mybb_cache_clear": handle_cache_clear,
    "mybb_stats_forum": handle_stats_forum,
    "mybb_stats_board": handle_stats_board,
    "mybb_bridge_health_check": handle_bridge_health_check,
    "mybb_list_template_groups": handle_list_template_groups,
}
