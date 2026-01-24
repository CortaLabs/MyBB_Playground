"""Sync handlers for MCP tools.

Handlers for disk sync operations:
- Template/stylesheet export
- File watcher control
- Sync status queries
"""

from typing import Any
from datetime import datetime


# ==================== Sync Handlers ====================

async def handle_sync_export_templates(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Export templates from a template set to disk files.

    Args:
        args: Must contain 'set_name' (template set name)
        db: MyBBDatabase instance (unused but required by signature)
        config: Server configuration (unused but required by signature)
        sync_service: Disk sync service instance

    Returns:
        Markdown formatted export results
    """
    set_name = args.get("set_name", "")
    if not set_name:
        return "Error: set_name is required"

    try:
        # Note: service.export_template_set() handles watcher stop/start internally
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


async def handle_sync_export_stylesheets(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Export stylesheets from a theme to disk files.

    Args:
        args: Must contain 'theme_name' (theme name)
        db: MyBBDatabase instance (unused but required by signature)
        config: Server configuration (unused but required by signature)
        sync_service: Disk sync service instance

    Returns:
        Markdown formatted export results
    """
    theme_name = args.get("theme_name", "")
    if not theme_name:
        return "Error: theme_name is required"

    try:
        # Note: service.export_theme() handles watcher pause/resume internally
        stats = await sync_service.export_theme(theme_name)
        return (
            f"# Stylesheets Exported\n\n"
            f"**Theme**: {stats['theme_name']}\n"
            f"**Files**: {stats['files_exported']}\n"
            f"**Directory**: {stats['directory']}"
        )
    except ValueError as e:
        return f"Error: {e}"


async def handle_sync_start_watcher(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Start the file watcher for automatic sync.

    Args:
        args: No required arguments
        db: MyBBDatabase instance (unused but required by signature)
        config: Server configuration (unused but required by signature)
        sync_service: Disk sync service instance

    Returns:
        Markdown formatted watcher status
    """
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


async def handle_sync_stop_watcher(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Stop the file watcher.

    Args:
        args: No required arguments
        db: MyBBDatabase instance (unused but required by signature)
        config: Server configuration (unused but required by signature)
        sync_service: Disk sync service instance

    Returns:
        Markdown formatted watcher status
    """
    stopped = sync_service.stop_watcher()
    if stopped:
        return "# File Watcher Stopped\n\n**Status**: Stopped"
    else:
        return "# File Watcher Not Running\n\nThe watcher was not active."


async def handle_sync_status(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Get current sync service status.

    Args:
        args: No required arguments
        db: MyBBDatabase instance (unused but required by signature)
        config: Server configuration (unused but required by signature)
        sync_service: Disk sync service instance

    Returns:
        Markdown formatted sync status with workspace projects
    """
    status = sync_service.get_status()
    watcher_status = "Running ✓" if status['watcher_running'] else "Stopped"

    # Build base status output
    output = [
        "# Sync Status\n",
        f"**Watcher**: {watcher_status}",
        f"**Sync Root**: {status['sync_root']}",
        f"**MyBB URL**: {status['mybb_url']}"
    ]

    # Add workspace root if available
    if 'workspace_root' in status:
        output.append(f"**Workspace Root**: {status['workspace_root']}")

    # Query workspace projects from ProjectDatabase
    try:
        # Import PluginManager dependencies
        import sys
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent.parent
        plugin_manager_path = repo_root / "plugin_manager"
        if str(plugin_manager_path) not in sys.path:
            sys.path.insert(0, str(plugin_manager_path))

        from database import ProjectDatabase

        # Initialize database
        workspace_root = Path(status.get('workspace_root', repo_root / 'plugin_manager'))
        db_path = workspace_root / '.meta' / 'projects.db'

        if db_path.exists():
            project_db = ProjectDatabase(db_path)

            # Get all plugins and themes
            plugins = project_db.list_projects(type='plugin')
            themes = project_db.list_projects(type='theme')

            if plugins or themes:
                output.append("\n## Workspace Projects\n")

                if plugins:
                    output.append("### Plugins")
                    output.append("| Codename | Status | Version | Last Synced |")
                    output.append("|----------|--------|---------|-------------|")
                    for p in plugins:
                        last_synced = p.get('last_synced_at', 'never')
                        if last_synced and last_synced != 'never':
                            # Format timestamp nicely
                            try:
                                dt = datetime.fromisoformat(last_synced)
                                last_synced = dt.strftime('%Y-%m-%d %H:%M')
                            except:
                                pass
                        output.append(f"| {p['codename']} | {p['status']} | {p['version']} | {last_synced} |")
                    output.append("")

                if themes:
                    output.append("### Themes")
                    output.append("| Codename | Status | Version | Last Synced |")
                    output.append("|----------|--------|---------|-------------|")
                    for t in themes:
                        last_synced = t.get('last_synced_at', 'never')
                        if last_synced and last_synced != 'never':
                            try:
                                dt = datetime.fromisoformat(last_synced)
                                last_synced = dt.strftime('%Y-%m-%d %H:%M')
                            except:
                                pass
                        output.append(f"| {t['codename']} | {t['status']} | {t['version']} | {last_synced} |")
    except Exception as e:
        # If workspace query fails, just continue with base status
        output.append(f"\n*Note: Could not query workspace projects: {e}*")

    return "\n".join(output)


# ==================== Handler Registry ====================

SYNC_HANDLERS = {
    "mybb_sync_export_templates": handle_sync_export_templates,
    "mybb_sync_export_stylesheets": handle_sync_export_stylesheets,
    "mybb_sync_start_watcher": handle_sync_start_watcher,
    "mybb_sync_stop_watcher": handle_sync_stop_watcher,
    "mybb_sync_status": handle_sync_status,
}
