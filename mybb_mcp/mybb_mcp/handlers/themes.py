"""Theme and stylesheet handlers for MyBB MCP tools."""

import sys
from pathlib import Path
from typing import Any

from ..bridge import MyBBBridgeClient


# ==================== Theme List Handlers ====================

async def handle_list_themes(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all MyBB themes (workspace and installed).

    Args:
        args: Tool arguments (unused)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Themes as markdown list with workspace and MyBB sections
    """
    # Import plugin_manager
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Get workspace themes
    workspace_themes = manager.db.list_projects(type="theme")

    # Get MyBB themes (existing behavior)
    mybb_themes = db.list_themes()

    lines = ["# Themes\n"]

    if workspace_themes:
        lines.append("## Workspace Themes")
        for t in workspace_themes:
            status = "installed" if t['status'] == 'installed' else "workspace"
            lines.append(f"- `{t['codename']}` [{t['visibility']}] ({status})")
        lines.append("")

    lines.append("## MyBB Installed Themes")
    if mybb_themes:
        for t in mybb_themes:
            in_workspace = any(wt['codename'] == t['name'].lower().replace(' ', '_')
                              for wt in workspace_themes)
            marker = " (managed)" if in_workspace else ""
            lines.append(f"- **{t['name']}** (tid: {t['tid']}){marker}")
    else:
        lines.append("No installed themes found.")

    return "\n".join(lines)


# ==================== Stylesheet List Handlers ====================

async def handle_list_stylesheets(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all stylesheets, optionally filtered by theme.

    Args:
        args: Tool arguments containing optional 'tid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Stylesheets as markdown table
    """
    sheets = db.list_stylesheets(tid=args.get("tid"))
    if not sheets:
        return "No stylesheets found."
    lines = [
        "# Stylesheets\n",
        "| SID | Name | Theme TID | Cache File |",
        "|-----|------|-----------|------------|"
    ]
    for s in sheets:
        lines.append(f"| {s['sid']} | {s['name']} | {s['tid']} | {s['cachefile']} |")
    return "\n".join(lines)


# ==================== Stylesheet Read/Write Handlers ====================

async def handle_read_stylesheet(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Read a stylesheet's CSS content.

    Supports hybrid mode: reads from workspace file if theme is managed,
    otherwise reads from database.

    Args:
        args: Tool arguments containing 'sid' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Stylesheet content as markdown with CSS code block
    """
    sid = args.get("sid")
    sheet = db.get_stylesheet(sid)
    if not sheet:
        return f"Stylesheet {sid} not found."

    # HYBRID MODE: Check if this stylesheet belongs to a workspace-managed theme
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Get theme name from tid
    theme = db.get_theme(sheet['tid'])
    if theme:
        # Convert theme name to codename format for matching
        theme_codename = theme['name'].lower().replace(' ', '_')

        # Check if this theme is workspace-managed
        workspace_themes = manager.db.list_projects(type="theme")
        managed_theme = next((t for t in workspace_themes if t['codename'] == theme_codename), None)

        if managed_theme:
            # Read from workspace file
            workspace_path = Path(managed_theme['workspace_path'])
            stylesheet_file = workspace_path / "stylesheets" / sheet['name']

            if stylesheet_file.exists():
                css_content = stylesheet_file.read_text(encoding='utf-8')
                return (
                    f"# Stylesheet: {sheet['name']} (WORKSPACE)\n"
                    f"- Theme: {theme['name']} (managed)\n"
                    f"- Workspace File: `{stylesheet_file}`\n"
                    f"- Attached to: {sheet['attachedto'] or 'All'}\n\n"
                    f"```css\n{css_content}\n```"
                )

    # Fall back to DB read for unmanaged themes
    return (
        f"# Stylesheet: {sheet['name']}\n"
        f"- SID: {sid}, Theme TID: {sheet['tid']}\n"
        f"- Attached to: {sheet['attachedto'] or 'All'}\n\n"
        f"```css\n{sheet['stylesheet']}\n```"
    )


async def handle_write_stylesheet(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Update a stylesheet's CSS content.

    Supports hybrid mode: writes to workspace file if theme is managed
    (and syncs to DB), otherwise writes directly to database.
    Triggers cache refresh after update.

    Args:
        args: Tool arguments containing 'sid' and 'stylesheet' parameters
        db: MyBBDatabase instance
        config: Server configuration (for MyBB URL)
        sync_service: Disk sync service (unused)

    Returns:
        Success or error message
    """
    sid = args.get("sid")
    css = args.get("stylesheet")

    # HYBRID MODE: Check if this stylesheet belongs to a workspace-managed theme
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Get stylesheet info
    sheet = db.get_stylesheet(sid)
    if not sheet:
        return f"Stylesheet {sid} not found."

    # Get theme name from tid
    theme = db.get_theme(sheet['tid'])
    result = ""

    if theme:
        # Convert theme name to codename format for matching
        theme_codename = theme['name'].lower().replace(' ', '_')

        # Check if this theme is workspace-managed
        workspace_themes = manager.db.list_projects(type="theme")
        managed_theme = next((t for t in workspace_themes if t['codename'] == theme_codename), None)

        if managed_theme:
            # Write to workspace file
            workspace_path = Path(managed_theme['workspace_path'])
            stylesheets_dir = workspace_path / "stylesheets"
            stylesheets_dir.mkdir(exist_ok=True)
            stylesheet_file = stylesheets_dir / sheet['name']

            stylesheet_file.write_text(css, encoding='utf-8')
            result = f"Stylesheet {sheet['name']} updated in workspace: `{stylesheet_file}`"
        else:
            result = f"Stylesheet {sid} prepared for bridge update."
    else:
        result = f"Stylesheet {sid} prepared for bridge update."

    bridge = MyBBBridgeClient(config.mybb_root)
    info = await bridge.call_async("info")
    if not info.success:
        return f"Error: Bridge info failed: {info.error or 'unknown error'}"
    supported = info.data.get("supported_actions", [])
    if "stylesheet:write" not in supported:
        return "Error: Bridge does not support 'stylesheet:write' yet."

    bridge_result = await bridge.call_async(
        "stylesheet:write",
        sid=sid,
        stylesheet=css,
    )

    if not bridge_result.success:
        return f"Error: Bridge stylesheet:write failed: {bridge_result.error or 'unknown error'}"

    return f"{result} (Bridge update complete)"


# ==================== Theme Creation Handler ====================

async def handle_create_theme(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Create a new MyBB theme in the plugin_manager workspace.

    Args:
        args: Tool arguments containing:
            - codename: Theme codename (lowercase, underscores)
            - name: Theme display name
            - description: Theme description (optional)
            - author: Author name (optional, default: Developer)
            - version: Version (optional, default: 1.0.0)
            - parent_theme: Parent theme name to inherit from (optional)
            - stylesheets: List of stylesheet names to create (optional)
        db: MyBBDatabase instance (unused)
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Success message with created files or error message
    """
    # Import plugin_manager
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Convert stylesheets to proper format
    stylesheets_input = args.get("stylesheets", ["global.css"])

    result = manager.create_theme(
        codename=args.get("codename", "").lower().replace(" ", "_"),
        display_name=args.get("name", ""),
        description=args.get("description", ""),
        author=args.get("author", "Developer"),
        version=args.get("version", "1.0.0"),
        visibility="public",
        parent_theme=args.get("parent_theme"),
        stylesheets=stylesheets_input
    )

    if result.get("success"):
        return (
            f"# Theme Created: {args.get('name')}\n\n"
            f"**Codename:** `{result['codename']}`\n"
            f"**Workspace:** `{result['workspace_path']}`\n"
            f"**Project ID:** {result['project_id']}\n\n"
            f"## Files Created\n" +
            "\n".join(f"- `{f}`" for f in result.get('files_created', [])) +
            f"\n\n**Next Steps:**\n"
            f"1. Edit stylesheets in `{result['workspace_path']}/stylesheets/`\n"
            f"2. Install to TestForum: Use `mybb_theme_activate` or Admin CP\n"
            f"3. Export for distribution: Use export workflow"
        )
    else:
        return f"# Error Creating Theme\n\n{result.get('error', 'Unknown error')}"


# Handler registry for theme tools
THEME_HANDLERS = {
    "mybb_list_themes": handle_list_themes,
    "mybb_list_stylesheets": handle_list_stylesheets,
    "mybb_read_stylesheet": handle_read_stylesheet,
    "mybb_write_stylesheet": handle_write_stylesheet,
    "mybb_create_theme": handle_create_theme,
}
