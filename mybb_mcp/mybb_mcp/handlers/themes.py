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


# ==================== Theme Deletion Handler ====================

async def handle_delete_theme(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Permanently delete a theme from workspace and database.

    Args:
        args: Contains codename, archive (default True), force (default False)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Markdown formatted deletion result
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()

        codename = args.get("codename", "")
        archive = args.get("archive", True)
        force = args.get("force", False)

        if not codename:
            return "# Error\n\n**Error:** codename is required"

        result = manager.delete_theme(codename, archive=archive, force=force)

        if result.get("success"):
            lines = [
                f"# Theme Deleted: {codename}",
                "",
                "## Actions Taken"
            ]
            for action in result.get("actions", []):
                lines.append(f"- {action}")

            if result.get("archive_path"):
                lines.append(f"\n**Archived to:** `{result['archive_path']}`")

            if result.get("warnings"):
                lines.append("\n## Warnings")
                for warning in result["warnings"]:
                    lines.append(f"- ⚠️ {warning}")

            return "\n".join(lines)
        else:
            error_msg = result.get("error", "Unknown error")
            warnings = result.get("warnings", [])
            lines = [f"# Error Deleting Theme\n\n**Error:** {error_msg}"]
            if warnings:
                lines.append("\n## Warnings")
                for w in warnings:
                    lines.append(f"- {w}")
            return "\n".join(lines)

    except ImportError as e:
        return f"Error: plugin_manager not available: {e}"
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error deleting theme {args.get('codename')}")
        return f"Error deleting theme: {e}"


async def handle_theme_install(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Deploy theme from workspace to TestForum.

    Creates theme record and imports stylesheets/templates from workspace.

    Args:
        args: Contains codename, visibility (optional)
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Markdown formatted installation result
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()

        codename = args.get("codename", "")
        visibility = args.get("visibility")
        set_default = args.get("set_default", True)  # Default to True - themes should be set as default

        if not codename:
            return "# Error\n\n**Error:** codename is required"

        # Call existing install_theme method
        # NOTE: ThemeInstaller.install_theme() already handles disk sync via DiskSyncService.sync_theme()
        result = manager.install_theme(codename, visibility, mybb_db=db, set_default=set_default)

        if result.get("success"):
            lines = [
                f"# Theme Installed: {result['theme']}",
                "",
                "## Deployment Summary",
                f"- **Stylesheets deployed:** {result.get('stylesheets_deployed', 0)}",
                f"- **Templates deployed:** {result.get('templates_deployed', 0)}",
            ]

            if result.get("theme_id"):
                lines.append(f"- **Theme ID:** {result['theme_id']}")

            if result.get("set_as_default"):
                lines.append("- **Status:** Set as default theme")

            if result.get("warnings"):
                lines.append("\n## Notes")
                for warning in result["warnings"]:
                    lines.append(f"- {warning}")

            return "\n".join(lines)
        else:
            error_msg = result.get("error", "Unknown error")
            warnings = result.get("warnings", [])
            lines = [f"# Error Installing Theme\n\n**Error:** {error_msg}"]
            if warnings:
                lines.append("\n## Warnings")
                for w in warnings:
                    lines.append(f"- {w}")
            return "\n".join(lines)

    except ImportError as e:
        return f"Error: plugin_manager not available: {e}"
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error installing theme {args.get('codename')}")
        return f"Error installing theme: {e}"


async def handle_theme_uninstall(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Remove theme from TestForum.

    Reverts theme customizations and updates project DB status.
    Optionally deletes theme record from MyBB database.

    Args:
        args: Contains codename, remove_from_db (optional)
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Markdown formatted uninstallation result
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()

        codename = args.get("codename", "")
        remove_from_db = args.get("remove_from_db", False)

        if not codename:
            return "# Error\n\n**Error:** codename is required"

        # Call existing uninstall_theme method
        result = manager.uninstall_theme(codename)

        # If remove_from_db is True, also delete theme record and templateset from MyBB database
        if remove_from_db and result.get("success"):
            try:
                # Get theme by name (case-insensitive)
                theme = db.get_theme_by_name(codename)
                if theme:
                    tid = theme["tid"]

                    # Get templateset sid from theme properties
                    import pickle
                    props = theme.get("properties", "")
                    templateset_sid = None
                    if props:
                        try:
                            # MyBB uses PHP serialize, which Python can parse with phpserialize
                            # But properties might already be unserialized dict or raw
                            if isinstance(props, dict):
                                templateset_sid = props.get("templateset")
                            elif isinstance(props, str) and props.startswith("a:"):
                                # PHP serialized - need to parse
                                import re
                                match = re.search(r'"templateset";[si]:(\d+)', props)
                                if match:
                                    templateset_sid = int(match.group(1))
                        except Exception:
                            pass

                    with db.cursor() as cur:
                        # Delete associated stylesheets
                        cur.execute(
                            f"DELETE FROM {db.table('themestylesheets')} WHERE tid = %s",
                            (tid,)
                        )

                        # Delete templateset and its templates if we have a custom one
                        if templateset_sid and templateset_sid > 0:
                            # Delete all templates in this templateset
                            cur.execute(
                                f"DELETE FROM {db.table('templates')} WHERE sid = %s",
                                (templateset_sid,)
                            )
                            templates_deleted = cur.rowcount

                            # Delete the templateset record
                            cur.execute(
                                f"DELETE FROM {db.table('templatesets')} WHERE sid = %s",
                                (templateset_sid,)
                            )
                            result.setdefault("warnings", []).append(
                                f"Templateset deleted (sid={templateset_sid}, {templates_deleted} templates)"
                            )

                        # Delete the theme record
                        cur.execute(
                            f"DELETE FROM {db.table('themes')} WHERE tid = %s",
                            (tid,)
                        )
                    result.setdefault("warnings", []).append(
                        f"Theme record deleted from database (tid={tid})"
                    )
                else:
                    result.setdefault("warnings", []).append(
                        "No theme record found in database to delete"
                    )
            except Exception as e:
                result.setdefault("warnings", []).append(
                    f"Failed to delete theme record from database: {str(e)}"
                )

        if result.get("success"):
            lines = [
                f"# Theme Uninstalled: {result['theme']}",
                "",
                "## Summary",
                "- Theme customizations reverted",
                "- Project status updated to 'development'",
            ]

            if remove_from_db:
                lines.append("- Theme record removal attempted")

            if result.get("warnings"):
                lines.append("\n## Notes")
                for warning in result["warnings"]:
                    lines.append(f"- {warning}")

            return "\n".join(lines)
        else:
            error_msg = result.get("error", "Unknown error")
            warnings = result.get("warnings", [])
            lines = [f"# Error Uninstalling Theme\n\n**Error:** {error_msg}"]
            if warnings:
                lines.append("\n## Warnings")
                for w in warnings:
                    lines.append(f"- {w}")
            return "\n".join(lines)

    except ImportError as e:
        return f"Error: plugin_manager not available: {e}"
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error uninstalling theme {args.get('codename')}")
        return f"Error uninstalling theme: {e}"


# ==================== Theme Status Handler ====================

async def handle_theme_status(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Get comprehensive theme status.

    Checks workspace existence, project database, and MyBB database state.

    Args:
        args: Must contain 'codename'
        db: MyBBDatabase instance for MyBB queries
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Markdown formatted status report
    """
    codename = args.get("codename", "")

    if not codename:
        return "# Error\n\n**Error:** codename is required"

    # Setup path for plugin_manager imports
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()

        lines = [f"# Theme Status: {codename}\n"]

        # 1. Check workspace
        workspace_path = manager.theme_workspace.get_workspace_path(codename)

        if workspace_path:
            lines.append("## Workspace")
            lines.append(f"- **Status:** ✅ Exists")
            lines.append(f"- **Path:** `{workspace_path}`")

            # Try to load meta.json
            try:
                meta = manager.theme_workspace.read_meta(codename)
                lines.append(f"- **Display Name:** {meta.get('name', codename)}")
                lines.append(f"- **Version:** {meta.get('version', 'unknown')}")
                lines.append(f"- **Author:** {meta.get('author', 'unknown')}")
                if meta.get('description'):
                    lines.append(f"- **Description:** {meta.get('description')}")
            except (FileNotFoundError, ValueError) as e:
                lines.append(f"- **Meta:** ⚠️ Missing or invalid meta.json")
        else:
            lines.append("## Workspace")
            lines.append(f"- **Status:** ❌ Not found")

        # 2. Check project database
        lines.append("\n## Project Database")
        project = manager.db.get_project(codename)

        if project:
            lines.append(f"- **Status:** {project.get('status', 'unknown')}")
            lines.append(f"- **Type:** {project.get('project_type', 'unknown')}")
            lines.append(f"- **Created:** {project.get('created_at', 'unknown')}")

            if project.get('installed_at'):
                lines.append(f"- **Installed At:** {project['installed_at']}")
            else:
                lines.append(f"- **Installed:** No")

            # History count
            cursor = manager.db.conn.execute(
                "SELECT COUNT(*) FROM history WHERE project_id = ?",
                (project['id'],)
            )
            history_count = cursor.fetchone()[0]
            lines.append(f"- **History Entries:** {history_count}")
        else:
            lines.append("- **Status:** ❌ Not registered")

        # 3. Check MyBB database
        lines.append("\n## MyBB Database")

        try:
            # Query for theme in MyBB themes table using cursor context manager
            # Note: Theme names in DB may not match codename exactly
            with db.cursor() as cur:
                cur.execute(
                    f"SELECT tid, name, def FROM {db.table('themes')} "
                    f"WHERE LOWER(name) LIKE LOWER(%s)",
                    (f"%{codename}%",)
                )
                theme_record = cur.fetchall()

            if theme_record and len(theme_record) > 0:
                theme = theme_record[0]
                lines.append(f"- **Status:** ✅ Installed")
                lines.append(f"- **Theme ID (tid):** {theme.get('tid')}")
                lines.append(f"- **Theme Name:** {theme.get('name')}")
                lines.append(f"- **Default Theme:** {'Yes' if theme.get('def') == '1' else 'No'}")

                # Get stylesheet count
                with db.cursor() as cur:
                    cur.execute(
                        f"SELECT COUNT(*) as count FROM {db.table('themestylesheets')} "
                        f"WHERE tid = %s",
                        (theme['tid'],)
                    )
                    stylesheet_result = cur.fetchone()

                if stylesheet_result:
                    lines.append(f"- **Stylesheets:** {stylesheet_result.get('count', 0)}")
            else:
                lines.append("- **Status:** ❌ Not installed in MyBB")

        except Exception as e:
            lines.append(f"- **Status:** ⚠️ Error querying database: {e}")

        return "\n".join(lines)

    except ImportError as e:
        return f"# Error\n\n**Error:** plugin_manager not available: {e}"
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error getting theme status for {codename}")
        return f"# Error\n\n**Error:** {e}"


async def handle_export_theme_xml(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Export theme to MyBB-compatible XML format.

    Args:
        args: Tool arguments containing codename, optional output_path, visibility
        db: MyBBDatabase instance (unused)
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Export result as markdown
    """
    codename = args.get("codename")
    if not codename:
        return "# Error\n\n**Error:** codename is required"

    output_path = args.get("output_path")
    visibility = args.get("visibility")

    try:
        # Import plugin_manager
        pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
        if str(pm_path.parent) not in sys.path:
            sys.path.insert(0, str(pm_path.parent))
        from plugin_manager.manager import PluginManager

        manager = PluginManager()
        result = manager.export_theme_xml(codename, output_path, visibility)

        lines = ["# Theme XML Export\n"]

        if result["success"]:
            lines.append(f"**Theme:** `{codename}`")
            lines.append(f"**Stylesheets exported:** {result['stylesheets_count']}")
            lines.append(f"**Templates exported:** {result['templates_count']}")

            if result["path"]:
                lines.append(f"\n**Output file:** `{result['path']}`")
            elif result["xml"]:
                # Truncate XML preview for large content
                xml_preview = result["xml"]
                if len(xml_preview) > 2000:
                    xml_preview = xml_preview[:2000] + "\n... (truncated)"
                lines.append(f"\n**XML Content:**\n```xml\n{xml_preview}\n```")

            if result["errors"]:
                lines.append("\n**Warnings:**")
                for error in result["errors"]:
                    lines.append(f"- {error}")
        else:
            lines.append("**Status:** Failed\n")
            lines.append("**Errors:**")
            for error in result["errors"]:
                lines.append(f"- {error}")

        return "\n".join(lines)

    except ImportError as e:
        return f"# Error\n\n**Error:** plugin_manager not available: {e}"
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error exporting theme XML for {codename}")
        return f"# Error\n\n**Error:** {e}"


async def handle_import_theme_xml(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Import theme from MyBB XML file to workspace.

    Args:
        args: Tool arguments containing xml_path, optional codename, visibility
        db: MyBBDatabase instance (unused)
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Import result as markdown
    """
    xml_path = args.get("xml_path")
    if not xml_path:
        return "# Error\n\n**Error:** xml_path is required"

    codename = args.get("codename")
    visibility = args.get("visibility", "public")

    try:
        # Import plugin_manager
        pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
        if str(pm_path.parent) not in sys.path:
            sys.path.insert(0, str(pm_path.parent))
        from plugin_manager.manager import PluginManager

        manager = PluginManager()
        result = manager.import_theme_xml(xml_path, codename, visibility)

        lines = ["# Theme XML Import\n"]

        if result["success"]:
            lines.append(f"**Theme:** `{result['codename']}`")
            lines.append(f"**Workspace:** `{result['workspace_path']}`")
            lines.append(f"**Stylesheets imported:** {result['stylesheets_count']}")
            lines.append(f"**Templates imported:** {result['templates_count']}")

            if result.get("warnings"):
                lines.append("\n**Warnings:**")
                for warning in result["warnings"]:
                    lines.append(f"- {warning}")

            lines.append("\n**Next steps:**")
            lines.append("1. Review imported stylesheets in `stylesheets/` directory")
            lines.append("2. Review imported templates in `templates/` directory")
            lines.append("3. Update `meta.json` if needed")
            lines.append("4. Use `mybb_theme_install` to deploy to TestForum")
        else:
            lines.append("**Status:** Failed\n")
            lines.append("**Errors:**")
            for error in result["errors"]:
                lines.append(f"- {error}")

            if result.get("warnings"):
                lines.append("\n**Warnings:**")
                for warning in result["warnings"]:
                    lines.append(f"- {warning}")

        return "\n".join(lines)

    except ImportError as e:
        return f"# Error\n\n**Error:** plugin_manager not available: {e}"
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error importing theme XML from {xml_path}")
        return f"# Error\n\n**Error:** {e}"


async def handle_theme_import_to_mybb(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Import theme XML directly to MyBB database via bridge.

    Creates theme record in database without workspace. Use for importing third-party themes.

    Args:
        args: Tool arguments containing:
            - xml_path: Path to XML file or raw XML content (required)
            - name: Optional theme name override
            - parent: Parent theme ID (default: 1)
            - no_stylesheets: Skip stylesheet import
            - no_templates: Skip template import
            - force_version: Bypass version compatibility check
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Import result as markdown
    """
    xml_path = args.get("xml_path")
    if not xml_path:
        return "# Error\n\n**Error:** xml_path is required"

    # Build bridge command arguments
    bridge_args = {"xml": xml_path}

    if args.get("name"):
        bridge_args["name"] = args["name"]
    if args.get("parent"):
        bridge_args["parent"] = str(args["parent"])
    if args.get("no_stylesheets"):
        bridge_args["no_stylesheets"] = True
    if args.get("no_templates"):
        bridge_args["no_templates"] = True
    if args.get("force_version"):
        bridge_args["force_version"] = True

    try:
        # Check bridge support
        bridge = MyBBBridgeClient(config.mybb_root)
        info = await bridge.call_async("info")
        if not info.success:
            return f"# Error\n\n**Error:** Bridge info failed: {info.error or 'unknown error'}"

        supported = info.data.get("supported_actions", [])
        if "theme:import" not in supported:
            return "# Error\n\n**Error:** Bridge does not support 'theme:import' action yet."

        # Call bridge
        result = await bridge.call_async("theme:import", **bridge_args)

        if not result.success:
            return f"# Error\n\n**Error:** Bridge theme:import failed: {result.error or 'unknown error'}"

        # Format success response
        data = result.data or {}
        lines = ["# Theme Import to MyBB\n"]
        lines.append("**Status:** Success\n")

        if data.get("tid"):
            lines.append(f"**Theme ID:** {data['tid']}")
        if data.get("name"):
            lines.append(f"**Theme Name:** {data['name']}")
        if data.get("stylesheets_imported"):
            lines.append(f"**Stylesheets Imported:** {data['stylesheets_imported']}")
        if data.get("templates_imported"):
            lines.append(f"**Templates Imported:** {data['templates_imported']}")

        if data.get("warnings"):
            lines.append("\n**Warnings:**")
            for warning in data["warnings"]:
                lines.append(f"- {warning}")

        lines.append("\n**Next steps:**")
        lines.append("- Theme is now available in MyBB Admin CP")
        lines.append("- Activate the theme for specific forums if needed")

        return "\n".join(lines)

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error importing theme to MyBB from {xml_path}")
        return f"# Error\n\n**Error:** {e}"


# ==================== Bridge-Based Handlers ====================

async def handle_templateset_create(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Create a new templateset.

    Args:
        args: Tool arguments containing 'title' (required)
    """
    title = args.get("title")
    if not title:
        return "Error: 'title' parameter is required"

    bridge = MyBBBridgeClient(config.mybb_root)
    result = await bridge.call_async("templateset:create", title=title)

    if not result.success:
        return f"Error: {result.error or 'Unknown error'}"

    data = result.data
    existed = "already existed" if data.get("existed") else "created"
    return f"Templateset **{data.get('title')}** (sid: {data.get('sid')}) {existed}."


async def handle_templateset_copy_master(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Copy all master templates to a templateset.

    Args:
        args: Tool arguments containing 'sid' (required), 'source_sid' (optional, default -2)
    """
    sid = args.get("sid")
    if not sid:
        return "Error: 'sid' parameter is required"

    source_sid = args.get("source_sid", -2)

    bridge = MyBBBridgeClient(config.mybb_root)
    result = await bridge.call_async("templateset:copy_master", sid=sid, source_sid=source_sid)

    if not result.success:
        return f"Error: {result.error or 'Unknown error'}"

    data = result.data
    return (f"Copied **{data.get('templates_copied')}** templates to templateset "
            f"**{data.get('templateset_title')}** (sid: {data.get('sid')}).")


async def handle_theme_create_db(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Create a theme directly in MyBB database (not workspace).

    For workspace themes, use mybb_create_theme instead.

    Args:
        args: 'name' (required), 'pid' (optional), 'templateset' (optional)
    """
    name = args.get("name")
    if not name:
        return "Error: 'name' parameter is required"

    bridge = MyBBBridgeClient(config.mybb_root)
    result = await bridge.call_async(
        "theme:create",
        name=name,
        pid=args.get("pid", 1),
        templateset=args.get("templateset")
    )

    if not result.success:
        return f"Error: {result.error or 'Unknown error'}"

    data = result.data
    existed = "already existed" if data.get("existed") else "created"
    return (f"Theme **{data.get('name')}** (tid: {data.get('tid')}) {existed}. "
            f"Templateset: {data.get('templateset')}")


async def handle_theme_get(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get theme information by tid or name.

    Args:
        args: 'tid' OR 'name' (one required)
    """
    tid = args.get("tid")
    name = args.get("name")

    if not tid and not name:
        return "Error: Either 'tid' or 'name' parameter is required"

    bridge = MyBBBridgeClient(config.mybb_root)
    result = await bridge.call_async("theme:get", tid=tid, name=name)

    if not result.success:
        return f"Error: {result.error or 'Unknown error'}"

    data = result.data
    props = data.get("properties", {})

    lines = [
        f"# Theme: {data.get('name')}",
        "",
        f"- **TID:** {data.get('tid')}",
        f"- **Parent TID:** {data.get('pid')}",
        f"- **Default:** {'Yes' if data.get('def') else 'No'}",
        f"- **Templateset:** {props.get('templateset', 'N/A')}",
        f"- **Logo:** {props.get('logo', 'N/A')}",
    ]
    return "\n".join(lines)


async def handle_stylesheet_create(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Create or update a stylesheet for a theme.

    Args:
        args: 'tid' (required), 'name' (required), 'content' (required), 'attachedto' (optional)
    """
    tid = args.get("tid")
    name = args.get("name")
    content = args.get("content")

    if not all([tid, name, content]):
        return "Error: 'tid', 'name', and 'content' parameters are required"

    bridge = MyBBBridgeClient(config.mybb_root)
    result = await bridge.call_async(
        "stylesheet:create",
        tid=tid,
        name=name,
        content=content,
        attachedto=args.get("attachedto", "")
    )

    if not result.success:
        return f"Error: {result.error or 'Unknown error'}"

    data = result.data
    updated = "updated" if data.get("updated") else "created"
    return (f"Stylesheet **{data.get('name')}** (sid: {data.get('sid')}) {updated} for theme {tid}. "
            f"Cache: `{data.get('cachefile')}`")


async def handle_theme_set_default(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Set a theme as the default theme.

    Args:
        args: 'tid' (required)
    """
    tid = args.get("tid")
    if not tid:
        return "Error: 'tid' parameter is required"

    bridge = MyBBBridgeClient(config.mybb_root)
    result = await bridge.call_async("theme:set_default", tid=tid)

    if not result.success:
        return f"Error: {result.error or 'Unknown error'}"

    return f"Theme {tid} set as default."


# Handler registry for theme tools
THEME_HANDLERS = {
    "mybb_list_themes": handle_list_themes,
    "mybb_list_stylesheets": handle_list_stylesheets,
    "mybb_read_stylesheet": handle_read_stylesheet,
    "mybb_write_stylesheet": handle_write_stylesheet,
    "mybb_create_theme": handle_create_theme,
    "mybb_delete_theme": handle_delete_theme,
    "mybb_theme_install": handle_theme_install,
    "mybb_theme_uninstall": handle_theme_uninstall,
    "mybb_theme_status": handle_theme_status,
    "mybb_theme_export_xml": handle_export_theme_xml,
    "mybb_theme_import_xml": handle_import_theme_xml,
    "mybb_theme_import_to_mybb": handle_theme_import_to_mybb,
    "mybb_templateset_create": handle_templateset_create,
    "mybb_templateset_copy_master": handle_templateset_copy_master,
    "mybb_theme_create_db": handle_theme_create_db,
    "mybb_theme_get": handle_theme_get,
    "mybb_stylesheet_create": handle_stylesheet_create,
    "mybb_theme_set_default": handle_theme_set_default,
}
