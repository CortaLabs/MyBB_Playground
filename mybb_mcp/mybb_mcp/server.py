"""MyBB MCP Server - AI-assisted MyBB development tools.

This server provides tools for Claude to interact with MyBB:
- Template management (list, read, write with inheritance)
- Theme/stylesheet management with cache refresh
- Plugin scaffolding and hook reference
"""

import asyncio
import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import load_config, MyBBConfig
from .db import MyBBDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mybb-mcp")


def create_server(config: MyBBConfig) -> Server:
    """Create and configure the MCP server with all tools."""
    from pathlib import Path
    from .sync import DiskSyncService, SyncConfig

    server = Server("mybb-mcp")
    db = MyBBDatabase(config.db)

    # Initialize DiskSync service
    # Use mybb_root's parent (repo root) for sync directory
    sync_root = config.mybb_root.parent / "mybb_sync"
    sync_root.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    sync_config = SyncConfig(sync_root=sync_root)
    sync_service = DiskSyncService(db, sync_config, config.mybb_url)

    # Auto-start file watcher (dev server - always want sync on)
    sync_service.start_watcher()
    logger.info(f"File watcher started: {sync_root}")

    # All tools in a combined list
    all_tools: list[Tool] = []

    # ==================== Template Tools ====================

    all_tools.extend([
        Tool(
            name="mybb_list_template_sets",
            description="List all MyBB template sets. Template sets are collections of templates for a theme.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="mybb_list_templates",
            description="List templates. Filter by set ID (sid) or search term. sid=-2 for master templates, sid=-1 for global.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sid": {"type": "integer", "description": "Template set ID. Use -2 for master, -1 for global."},
                    "search": {"type": "string", "description": "Search term for template names."},
                },
            },
        ),
        Tool(
            name="mybb_read_template",
            description="Read a template's HTML content. Shows both master and custom version if exists.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Template title to read."},
                    "sid": {"type": "integer", "description": "Template set ID (default checks master and custom)."},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="mybb_write_template",
            description="Update or create a template. Handles inheritance automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Template title."},
                    "template": {"type": "string", "description": "Template HTML content."},
                    "sid": {"type": "integer", "description": "Template set ID. Use -2 for master, positive for specific set.", "default": 1},
                },
                "required": ["title", "template"],
            },
        ),
        Tool(
            name="mybb_list_template_groups",
            description="List template groups for organization (calendar, forum, usercp, etc.).",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ])

    # ==================== Theme/Style Tools ====================

    all_tools.extend([
        Tool(
            name="mybb_list_themes",
            description="List all MyBB themes.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="mybb_list_stylesheets",
            description="List stylesheets, optionally for a specific theme.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tid": {"type": "integer", "description": "Theme ID to filter by."},
                },
            },
        ),
        Tool(
            name="mybb_read_stylesheet",
            description="Read a stylesheet's CSS content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sid": {"type": "integer", "description": "Stylesheet ID."},
                },
                "required": ["sid"],
            },
        ),
        Tool(
            name="mybb_write_stylesheet",
            description="Update a stylesheet's CSS and refresh cache.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sid": {"type": "integer", "description": "Stylesheet ID."},
                    "stylesheet": {"type": "string", "description": "New CSS content."},
                },
                "required": ["sid", "stylesheet"],
            },
        ),
    ])

    # ==================== Plugin Tools ====================

    all_tools.extend([
        Tool(
            name="mybb_list_plugins",
            description="List plugins in the MyBB plugins directory.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="mybb_read_plugin",
            description="Read a plugin's PHP source code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plugin filename (without .php)."},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="mybb_create_plugin",
            description="Create a new MyBB plugin with proper structure, hooks, settings, templates, and database tables.",
            inputSchema={
                "type": "object",
                "properties": {
                    "codename": {"type": "string", "description": "Plugin codename (lowercase, underscores)."},
                    "name": {"type": "string", "description": "Plugin display name."},
                    "description": {"type": "string", "description": "Plugin description."},
                    "author": {"type": "string", "description": "Author name.", "default": "Developer"},
                    "version": {"type": "string", "description": "Version.", "default": "1.0.0"},
                    "hooks": {"type": "array", "items": {"type": "string"}, "description": "Hooks to attach (e.g., 'index_start', 'postbit')."},
                    "has_settings": {"type": "boolean", "description": "Create ACP settings.", "default": False},
                    "has_templates": {"type": "boolean", "description": "Create templates.", "default": False},
                    "has_database": {"type": "boolean", "description": "Create database table.", "default": False},
                },
                "required": ["codename", "name", "description"],
            },
        ),
        Tool(
            name="mybb_list_hooks",
            description="List available MyBB hooks for plugin development.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category: index, showthread, member, admin, global, etc."},
                    "search": {"type": "string", "description": "Search term."},
                },
            },
        ),
    ])

    # ==================== Analysis Tools ====================

    all_tools.extend([
        Tool(
            name="mybb_analyze_plugin",
            description="Analyze an existing plugin's structure, hooks, settings, and templates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plugin filename (without .php)."},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="mybb_db_query",
            description="Execute a read-only SQL query against MyBB database. For exploration only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT query."},
                },
                "required": ["query"],
            },
        ),
    ])

    # ==================== Disk Sync Tools ====================

    all_tools.extend([
        Tool(
            name="mybb_sync_export_templates",
            description="Export all templates from a template set to disk files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "set_name": {"type": "string", "description": "Template set name (e.g., 'Default Templates')"},
                },
                "required": ["set_name"],
            },
        ),
        Tool(
            name="mybb_sync_export_stylesheets",
            description="Export all stylesheets from a theme to disk files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "theme_name": {"type": "string", "description": "Theme name (e.g., 'Default')"},
                },
                "required": ["theme_name"],
            },
        ),
        Tool(
            name="mybb_sync_start_watcher",
            description="Start the file watcher to automatically sync template and stylesheet changes from disk to database.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="mybb_sync_stop_watcher",
            description="Stop the file watcher.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="mybb_sync_status",
            description="Get current sync service status (watcher state, sync directory, etc.).",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ])

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return all_tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            result = await handle_tool(name, arguments, db, config, sync_service)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.exception(f"Error in tool {name}")
            return [TextContent(type="text", text=f"Error: {e}")]

    return server


async def handle_tool(name: str, args: dict, db: MyBBDatabase, config: MyBBConfig, sync_service=None) -> str:
    """Route tool calls to handlers."""
    import time
    import re
    import httpx

    plugins_dir = config.mybb_root / "inc" / "plugins"

    # ==================== Template Handlers ====================

    if name == "mybb_list_template_sets":
        sets = db.list_template_sets()
        if not sets:
            return "No template sets found."
        lines = ["# MyBB Template Sets\n", "| SID | Title |", "|-----|-------|"]
        for s in sets:
            lines.append(f"| {s['sid']} | {s['title']} |")
        lines.extend(["\n**Special SIDs:** -2 = Master templates, -1 = Global templates"])
        return "\n".join(lines)

    elif name == "mybb_list_templates":
        templates = db.list_templates(sid=args.get("sid"), search=args.get("search"))
        if not templates:
            return "No templates found."
        lines = [f"# Templates ({len(templates)} found)\n", "| TID | Title | SID | Version |", "|-----|-------|-----|---------|"]
        for t in templates[:100]:
            lines.append(f"| {t['tid']} | {t['title']} | {t['sid']} | {t['version']} |")
        if len(templates) > 100:
            lines.append(f"\n*...{len(templates) - 100} more*")
        return "\n".join(lines)

    elif name == "mybb_read_template":
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

    elif name == "mybb_write_template":
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

    elif name == "mybb_list_template_groups":
        with db.cursor() as cur:
            cur.execute(f"SELECT prefix, title FROM {db.table('templategroups')} ORDER BY title")
            groups = cur.fetchall()

        if not groups:
            return "No template groups found."

        lines = ["# Template Groups\n", "| Prefix | Title |", "|--------|-------|"]
        for g in groups:
            lines.append(f"| {g['prefix']} | {g['title']} |")
        return "\n".join(lines)

    # ==================== Theme/Style Handlers ====================

    elif name == "mybb_list_themes":
        themes = db.list_themes()
        if not themes:
            return "No themes found."
        lines = ["# MyBB Themes\n", "| TID | Name | Parent | Default |", "|-----|------|--------|---------|"]
        for t in themes:
            lines.append(f"| {t['tid']} | {t['name']} | {t['pid']} | {'Yes' if t['def'] else 'No'} |")
        return "\n".join(lines)

    elif name == "mybb_list_stylesheets":
        sheets = db.list_stylesheets(tid=args.get("tid"))
        if not sheets:
            return "No stylesheets found."
        lines = ["# Stylesheets\n", "| SID | Name | Theme TID | Cache File |", "|-----|------|-----------|------------|"]
        for s in sheets:
            lines.append(f"| {s['sid']} | {s['name']} | {s['tid']} | {s['cachefile']} |")
        return "\n".join(lines)

    elif name == "mybb_read_stylesheet":
        sid = args.get("sid")
        sheet = db.get_stylesheet(sid)
        if not sheet:
            return f"Stylesheet {sid} not found."
        return f"# Stylesheet: {sheet['name']}\n- SID: {sid}, Theme TID: {sheet['tid']}\n- Attached to: {sheet['attachedto'] or 'All'}\n\n```css\n{sheet['stylesheet']}\n```"

    elif name == "mybb_write_stylesheet":
        sid = args.get("sid")
        css = args.get("stylesheet")
        if not db.update_stylesheet(sid, css):
            return f"Failed to update stylesheet {sid}."
        result = f"Stylesheet {sid} updated."
        # Try cache refresh
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{config.mybb_url}/cachecss.php")
                result += " Cache refresh triggered." if resp.status_code == 200 else ""
        except:
            pass
        return result

    # ==================== Plugin Handlers ====================

    elif name == "mybb_list_plugins":
        if not plugins_dir.exists():
            return "Plugins directory not found."
        plugins = [f.stem for f in plugins_dir.glob("*.php") if f.stem != "index"]
        lines = [f"# Plugins ({len(plugins)})\n"]
        for p in sorted(plugins):
            lines.append(f"- `{p}`")
        return "\n".join(lines)

    elif name == "mybb_read_plugin":
        pname = args.get("name", "").replace(".php", "")
        ppath = plugins_dir / f"{pname}.php"
        if not ppath.exists():
            return f"Plugin '{pname}' not found."
        return f"# Plugin: {pname}\n\n```php\n{ppath.read_text()}\n```"

    elif name == "mybb_create_plugin":
        from .tools.plugins import create_plugin
        return create_plugin(args, config)

    elif name == "mybb_list_hooks":
        from .tools.plugins import get_hooks_reference
        return get_hooks_reference(args.get("category"), args.get("search"))

    elif name == "mybb_analyze_plugin":
        pname = args.get("name", "").replace(".php", "")
        ppath = plugins_dir / f"{pname}.php"
        if not ppath.exists():
            return f"Plugin '{pname}' not found."

        content = ppath.read_text()
        lines = [f"# Plugin Analysis: {pname}\n"]

        # Find hooks
        hook_pattern = r"\$plugins->add_hook\s*\(\s*['\"]([^'\"]+)['\"]"
        hooks = re.findall(hook_pattern, content)
        lines.append(f"## Hooks ({len(hooks)})")
        for h in hooks[:20]:
            lines.append(f"- `{h}`")

        # Find _info function
        if f"{pname}_info" in content:
            lines.append("\n## Has _info: Yes")

        # Find functions
        func_pattern = rf"function\s+{pname}_(\w+)"
        funcs = re.findall(func_pattern, content)
        lines.append(f"\n## Functions ({len(funcs)})")
        for f in funcs[:20]:
            lines.append(f"- `{pname}_{f}()`")

        # Check for features
        lines.append("\n## Features")
        lines.append(f"- Settings: {'Yes' if 'settinggroups' in content else 'No'}")
        lines.append(f"- Templates: {'Yes' if 'templates' in content and 'insert_query' in content else 'No'}")
        lines.append(f"- Database: {'Yes' if 'create_table' in content.lower() or 'write_query' in content else 'No'}")

        return "\n".join(lines)

    elif name == "mybb_db_query":
        query = args.get("query", "").strip()
        if not query.upper().startswith("SELECT"):
            return "Error: Only SELECT queries are allowed."

        with db.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

        if not rows:
            return "No results."

        # Format as table
        keys = list(rows[0].keys())
        lines = [" | ".join(keys), " | ".join(["---"] * len(keys))]
        for row in rows[:50]:
            lines.append(" | ".join(str(row[k])[:50] for k in keys))
        if len(rows) > 50:
            lines.append(f"\n*...{len(rows) - 50} more rows*")

        return "\n".join(lines)

    # ==================== Disk Sync Handlers ====================

    elif name == "mybb_sync_export_templates":
        set_name = args.get("set_name", "")
        if not set_name:
            return "Error: set_name is required"

        try:
            stats = await sync_service.export_template_set(set_name)
            groups_str = ', '.join(f"{g} ({c})" for g, c in stats['groups'].items())
            return (
                f"# Templates Exported\n\n"
                f"**Set**: {stats['template_set']}\n"
                f"**Files**: {stats['files_exported']}\n"
                f"**Directory**: {stats['directory']}\n\n"
                f"**Groups**: {groups_str}"
            )
        except ValueError as e:
            return f"Error: {e}"

    elif name == "mybb_sync_export_stylesheets":
        theme_name = args.get("theme_name", "")
        if not theme_name:
            return "Error: theme_name is required"

        try:
            stats = await sync_service.export_theme(theme_name)
            return (
                f"# Stylesheets Exported\n\n"
                f"**Theme**: {stats['theme_name']}\n"
                f"**Files**: {stats['files_exported']}\n"
                f"**Directory**: {stats['directory']}"
            )
        except ValueError as e:
            return f"Error: {e}"

    elif name == "mybb_sync_start_watcher":
        started = sync_service.start_watcher()
        if started:
            return (
                f"# File Watcher Started\n\n"
                f"**Status**: Running\n"
                f"**Monitoring**: {sync_service.config.sync_root}\n\n"
                f"The watcher will automatically import template (.html) and stylesheet (.css) "
                f"changes from disk to the database."
            )
        else:
            return "# File Watcher Already Running\n\nThe watcher is already active."

    elif name == "mybb_sync_stop_watcher":
        stopped = sync_service.stop_watcher()
        if stopped:
            return "# File Watcher Stopped\n\n**Status**: Stopped"
        else:
            return "# File Watcher Not Running\n\nThe watcher was not active."

    elif name == "mybb_sync_status":
        status = sync_service.get_status()
        watcher_status = "Running" if status['watcher_running'] else "Stopped"
        return (
            f"# Sync Status\n\n"
            f"**Watcher**: {watcher_status}\n"
            f"**Sync Root**: {status['sync_root']}\n"
            f"**MyBB URL**: {status['mybb_url']}"
        )

    return f"Unknown tool: {name}"


async def run_server():
    """Run the MCP server."""
    config = load_config()
    logger.info(f"Starting MyBB MCP Server")
    logger.info(f"MyBB Root: {config.mybb_root}")
    logger.info(f"Database: {config.db.database}")

    server = create_server(config)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
