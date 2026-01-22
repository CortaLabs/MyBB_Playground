"""Template handlers for MyBB MCP tools."""

import json
from typing import Any

from ..bridge import MyBBBridgeClient

# ==================== Template List Handlers ====================

async def handle_list_template_sets(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all MyBB template sets.

    Args:
        args: Tool arguments (unused)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Template sets as markdown table
    """
    sets = db.list_template_sets()
    if not sets:
        return "No template sets found."
    lines = ["# MyBB Template Sets\n", "| SID | Title |", "|-----|-------|"]
    for s in sets:
        lines.append(f"| {s['sid']} | {s['title']} |")
    lines.extend(["\n**Special SIDs:** -2 = Master templates, -1 = Global templates"])
    return "\n".join(lines)


async def handle_list_templates(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List templates with optional filtering.

    Args:
        args: Tool arguments containing optional 'sid' and 'search' parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Templates as markdown table
    """
    templates = db.list_templates(sid=args.get("sid"), search=args.get("search"))
    if not templates:
        return "No templates found."
    lines = [f"# Templates ({len(templates)} found)\n", "| TID | Title | SID | Version |", "|-----|-------|-----|---------|"]
    for t in templates[:100]:
        lines.append(f"| {t['tid']} | {t['title']} | {t['sid']} | {t['version']} |")
    if len(templates) > 100:
        lines.append(f"\n*...{len(templates) - 100} more*")
    return "\n".join(lines)


# ==================== Template Read/Write Handlers ====================

async def handle_read_template(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Read a template's HTML content.

    Args:
        args: Tool arguments containing 'title' and optional 'sid' parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Template content with master and custom versions
    """
    title = args.get("title")
    sid = args.get("sid")

    # Get master template (-2)
    master = db.get_template(title, -2)
    # Get custom if sid specified
    custom = db.get_template(title, sid) if sid and sid != -2 else None

    if not master and not custom:
        return f"Template '{title}' not found."

    lines = [f"# Template: {title}\n"]

    if master:
        lines.extend([
            "## Master Template (sid=-2)",
            f"- TID: {master['tid']}, Version: {master['version']}",
            "```html", master['template'], "```", ""
        ])

    if custom:
        lines.extend([
            f"## Custom Template (sid={sid})",
            f"- TID: {custom['tid']}, Version: {custom['version']}",
            "```html", custom['template'], "```"
        ])

    if master and not custom:
        lines.append("\n*No custom version exists. Editing will create a custom override.*")

    return "\n".join(lines)


async def handle_write_template(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Update or create a template.

    Args:
        args: Tool arguments containing 'title', 'template', and optional 'sid' parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success message with template details
    """
    title = args.get("title")
    template = args.get("template")
    sid = args.get("sid", 1)

    if not title or not template:
        return "Error: 'title' and 'template' are required."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "template:write" not in supported:
        return "Error: Bridge does not support 'template:write' yet."

    result = await bridge.call_async(
        "template:write",
        title=title,
        template=template,
        sid=sid,
    )

    if not result.success:
        return f"Error: Bridge template:write failed: {result.error or 'unknown error'}"

    tid = result.data.get("tid")
    action = "updated"
    actions_taken = result.data.get("actions_taken", [])
    if "template_created" in actions_taken:
        action = "created"
    return f"Template '{title}' {action} in set {sid} (TID {tid})."



# ==================== Template Find/Replace Handler ====================

async def handle_template_find_replace(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Find and replace in templates across sets.

    Args:
        args: Tool arguments containing 'title', 'find', 'replace', and optional parameters
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Summary of modifications made
    """
    title = args.get("title")
    find = args.get("find")
    replace = args.get("replace")
    template_sets = args.get("template_sets", [])
    use_regex = args.get("regex", True)
    limit = args.get("limit", -1)

    if not title or not find or replace is None:
        return "Error: 'title', 'find', and 'replace' are required."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "template:find_replace" not in supported:
        return "Error: Bridge does not support 'template:find_replace' yet."

    template_sets_csv = ",".join(str(s) for s in template_sets) if template_sets else None
    result = await bridge.call_async(
        "template:find_replace",
        title=title,
        find=find,
        replace=replace,
        template_sets=template_sets_csv,
        regex=1 if use_regex else 0,
        limit=limit,
    )

    if not result.success:
        return f"Error: Bridge template:find_replace failed: {result.error or 'unknown error'}"

    updated = result.data.get("updated", False)
    if not updated:
        return f"No modifications made. Pattern '{find}' not found in template '{title}'."

    return f"# Find/Replace Results for '{title}'\n\nModified templates via bridge."


# ==================== Template Batch Handlers ====================

async def handle_template_batch_read(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Read multiple templates in one call.

    Args:
        args: Tool arguments containing 'templates' list and optional 'sid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Template contents with not-found list
    """
    template_names = args.get("templates", [])
    sid = args.get("sid", -2)

    if not template_names:
        return "Error: 'templates' list is required."

    results = {}
    not_found = []

    for title in template_names:
        template = db.get_template(title, sid)
        if template:
            results[title] = template['template']
        else:
            not_found.append(title)

    lines = [f"# Batch Read Results (sid={sid})\n"]

    if results:
        lines.append(f"Successfully read {len(results)} template(s):\n")
        for title, content in results.items():
            lines.extend([
                f"## {title}",
                "```html",
                content,
                "```\n"
            ])

    if not_found:
        lines.append(f"\nNot found ({len(not_found)}):")
        for title in not_found:
            lines.append(f"- {title}")

    return "\n".join(lines)


async def handle_template_batch_write(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Write multiple templates in one atomic call.

    Args:
        args: Tool arguments containing 'templates' list and optional 'sid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Summary of created and updated templates
    """
    templates = args.get("templates", [])
    sid = args.get("sid", 1)

    if not templates:
        return "Error: 'templates' list is required."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "template:batch_write" not in supported:
        return "Error: Bridge does not support 'template:batch_write' yet."

    templates_json = json.dumps(templates)
    result = await bridge.call_async(
        "template:batch_write",
        sid=sid,
        templates_json=templates_json,
    )

    if not result.success:
        return f"Error: Bridge template:batch_write failed: {result.error or 'unknown error'}"

    created = result.data.get("created", 0)
    updated = result.data.get("updated", 0)
    lines = [f"# Batch Write Results (sid={sid})\n"]
    lines.append(f"Created {created} template(s).")
    lines.append(f"Updated {updated} template(s).")
    return "\n".join(lines)


# ==================== Template Outdated Handler ====================

async def handle_template_outdated(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Find templates that differ from master (outdated after MyBB upgrade).

    Args:
        args: Tool arguments containing 'sid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Outdated templates as markdown table
    """
    sid = args.get("sid")

    if not sid:
        return "Error: 'sid' is required."

    if sid == -2:
        return "Error: Cannot check master templates (sid=-2) for outdated versions."

    outdated = db.find_outdated_templates(sid)

    if not outdated:
        return f"No outdated templates found in template set {sid}. All templates are up to date."

    lines = [
        f"# Outdated Templates in Set {sid}\n",
        f"Found {len(outdated)} outdated template(s):\n",
        "| Template | Custom Version | Master Version | TID |",
        "|----------|----------------|----------------|-----|"
    ]

    for template in outdated:
        lines.append(
            f"| {template['title']} | {template['custom_version']} | "
            f"{template['master_version']} | {template['tid']} |"
        )

    lines.append("\n*Note: Custom templates with version < master version are outdated and may need updating.*")
    return "\n".join(lines)


# Handler registry for template tools
TEMPLATE_HANDLERS = {
    "mybb_list_template_sets": handle_list_template_sets,
    "mybb_list_templates": handle_list_templates,
    "mybb_read_template": handle_read_template,
    "mybb_write_template": handle_write_template,
    "mybb_template_find_replace": handle_template_find_replace,
    "mybb_template_batch_read": handle_template_batch_read,
    "mybb_template_batch_write": handle_template_batch_write,
    "mybb_template_outdated": handle_template_outdated,
}
