"""Template handlers for MyBB MCP tools."""

import re
from typing import Any


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

    # Check for existing templates
    master = db.get_template(title, -2)
    custom = db.get_template(title, sid) if sid != -2 else None

    if sid == -2:
        # Updating master template
        if master:
            db.update_template(master['tid'], template)
            return f"Master template '{title}' updated (TID {master['tid']})."
        else:
            tid = db.create_template(title, template, -2)
            return f"Master template '{title}' created (TID {tid})."
    else:
        # Creating/updating custom template
        if custom:
            db.update_template(custom['tid'], template)
            return f"Custom template '{title}' updated in set {sid} (TID {custom['tid']})."
        else:
            tid = db.create_template(title, template, sid)
            msg = f"Custom template '{title}' created in set {sid} (TID {tid})."
            if master:
                msg += f" (Overrides master TID {master['tid']})"
            return msg


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

    # Get all matching templates
    templates = db.find_templates_for_replace(title, template_sets)

    if not templates:
        return f"No templates found matching '{title}' in specified template sets."

    modified_count = 0
    modified_templates = []

    for template in templates:
        original = template['template']

        # Perform replacement
        if use_regex:
            try:
                if limit == -1:
                    new_content = re.sub(find, replace, original)
                else:
                    new_content = re.sub(find, replace, original, count=limit)
            except re.error as e:
                return f"Error: Invalid regex pattern: {e}"
        else:
            # Literal string replacement
            if limit == -1:
                new_content = original.replace(find, replace)
            else:
                new_content = original.replace(find, replace, limit)

        # Only update if content changed
        if new_content != original:
            db.update_template(template['tid'], new_content)
            modified_count += 1
            modified_templates.append(f"- TID {template['tid']} (sid={template['sid']})")

    if modified_count == 0:
        return f"No modifications made. Pattern '{find}' not found in template '{title}'."

    lines = [
        f"# Find/Replace Results for '{title}'",
        f"\nModified {modified_count} template(s):\n"
    ]
    lines.extend(modified_templates)
    return "\n".join(lines)


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

    # Atomic operation: collect all changes first
    operations = []
    for item in templates:
        title = item.get("title")
        content = item.get("template")

        if not title or not content:
            return f"Error: Each template must have 'title' and 'template' fields."

        # Check if template exists
        existing = db.get_template(title, sid)
        operations.append({
            "title": title,
            "content": content,
            "tid": existing['tid'] if existing else None,
            "action": "update" if existing else "create"
        })

    # Execute all operations
    created = []
    updated = []

    for op in operations:
        if op["action"] == "update":
            db.update_template(op["tid"], op["content"])
            updated.append(f"- {op['title']} (TID {op['tid']})")
        else:
            tid = db.create_template(op["title"], op["content"], sid)
            created.append(f"- {op['title']} (TID {tid})")

    lines = [f"# Batch Write Results (sid={sid})\n"]

    if created:
        lines.append(f"Created {len(created)} template(s):")
        lines.extend(created)
        lines.append("")

    if updated:
        lines.append(f"Updated {len(updated)} template(s):")
        lines.extend(updated)

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
