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


async def handle_workspace_sync(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Sync workspace files to TestForum/database."""
    codename = args.get("codename")
    sync_type = args.get("type")
    visibility = args.get("visibility")
    direction = args.get("direction", "to_db")
    full_pipeline = args.get("full_pipeline", False)
    dry_run = args.get("dry_run", False)

    # Validate required params
    if not codename:
        return "Error: codename is required"
    if sync_type not in ("plugin", "theme"):
        return "Error: type must be 'plugin' or 'theme'"

    # Import PluginManager for workspace resolution
    from plugin_manager.manager import PluginManager
    manager = PluginManager()

    try:
        if sync_type == "plugin":
            return await _sync_plugin(
                manager, sync_service, codename, visibility,
                full_pipeline, dry_run
            )
        else:  # theme
            return await _sync_theme(
                manager, sync_service, db, codename, visibility,
                full_pipeline, dry_run, direction
            )
    except Exception as e:
        return f"# Sync Error\n\n**Error:** {str(e)}"


# ==================== Formatting Helpers ====================

def _format_incremental_result(codename: str, sync_type: str, result: dict) -> str:
    """Format incremental sync results as markdown.

    Incremental mode only syncs FILES - no database writes.
    Templates are copied as files, not synced to DB.
    """
    if not result.get("success"):
        return f"# Sync Failed\n\n**Error:** {result.get('error', 'Unknown error')}"

    output = [f"# {sync_type.title()} Synced: {codename}\n"]
    output.append("**Mode:** Incremental (files only)")

    if sync_type == "plugin":
        files = result.get("files_synced", [])
        skipped = result.get("files_skipped", [])
        output.append(f"**Files synced:** {len(files)}")
        if skipped:
            output.append(f"**Files unchanged:** {len(skipped)}")
    else:  # theme - syncs both stylesheets AND templates directly to DB
        stylesheets = result.get("stylesheets_synced", [])
        stylesheets_skipped = result.get("stylesheets_skipped", [])
        templates = result.get("templates_synced", [])
        templates_skipped = result.get("templates_skipped", [])
        output.append(f"**Stylesheets synced:** {len(stylesheets)}")
        if stylesheets_skipped:
            output.append(f"**Stylesheets unchanged:** {len(stylesheets_skipped)}")
        output.append(f"**Templates synced:** {len(templates)}")
        if templates_skipped:
            output.append(f"**Templates unchanged:** {len(templates_skipped)}")

    warnings = result.get("warnings", [])
    # Filter out the "no files synced" warning when files were just unchanged
    if sync_type == "plugin":
        skipped_count = len(result.get("files_skipped", []))
        warnings = [w for w in warnings if not (skipped_count > 0 and "No files synced" in w)]

    if warnings:
        output.append(f"\n**Warnings:** {len(warnings)}")
        for w in warnings[:5]:
            output.append(f"- {w}")

    output.append("\n---")
    if sync_type == "plugin":
        output.append("*Use `full_pipeline=True` to update database templates via PHP lifecycle.*")
    else:  # theme
        output.append("*Theme stylesheets and templates sync directly to database (no full_pipeline needed).*")

    return "\n".join(output)


def _format_full_pipeline_result(codename: str, sync_type: str, result: dict) -> str:
    """Format full pipeline results as markdown."""
    if not result.get("success"):
        return f"# Full Pipeline Failed\n\n**Error:** {result.get('error', 'Unknown error')}"

    output = [f"# {sync_type.title()} Reinstalled: {codename}\n"]
    output.append("**Mode:** Full Pipeline (uninstall + install)")

    if sync_type == "plugin":
        output.append(f"**Files deployed:** {result.get('file_count', 0)}")
        php_lifecycle = result.get("php_lifecycle", {})
        actions = php_lifecycle.get("actions_taken", [])
        if actions:
            output.append(f"**PHP actions:** {', '.join(actions)}")
    else:  # theme
        output.append(f"**Stylesheets:** {result.get('stylesheets_deployed', 0)}")

    return "\n".join(output)


def _format_dry_run_plugin(codename: str, workspace_path) -> str:
    """Format dry run preview for plugin workspace overlay.

    Shows ALL files that would be synced from workspace to TestForum,
    following the same pattern as PluginInstaller and DiskSyncService.
    """
    from pathlib import Path
    workspace_path = Path(workspace_path)

    # Files/directories that are workspace-only and should NOT be deployed
    # Mirrors DiskSyncService.WORKSPACE_ONLY
    WORKSPACE_ONLY = {
        "meta.json", "README.md", "readme.md", "README.txt", "readme.txt",
        "tests", ".git", ".gitignore", ".gitkeep", "__pycache__", ".DS_Store",
        "templates", "templates_themes",  # Templates go to DB, not filesystem
    }

    output = [f"# Dry Run: Plugin {codename}\n"]
    output.append("**Would sync (workspace -> TestForum):**\n")

    # Collect all files by destination directory
    files_by_dir: dict = {}
    root_files: list = []
    template_count = 0

    for item in workspace_path.iterdir():
        if item.name in WORKSPACE_ONLY:
            # Count templates separately (they go to DB)
            if item.name == "templates" and item.is_dir():
                template_count = len(list(item.glob("*.html")))
            continue

        if item.is_dir():
            # Count files in this directory
            files = list(item.rglob("*"))
            file_count = sum(1 for f in files if f.is_file())
            if file_count > 0:
                files_by_dir[item.name] = file_count
        elif item.is_file():
            root_files.append(item.name)

    # Format output
    total_files = sum(files_by_dir.values()) + len(root_files)

    if files_by_dir:
        output.append("**Directories:**")
        for dir_name, count in sorted(files_by_dir.items()):
            output.append(f"- `{dir_name}/` -> `TestForum/{dir_name}/` ({count} files)")

    if root_files:
        output.append("\n**Root files:**")
        for f in sorted(root_files):
            output.append(f"- `{f}` -> `TestForum/{f}`")

    if template_count > 0:
        output.append(f"\n**Templates (to database):** {template_count}")

    output.append(f"\n**Total files to deploy:** {total_files}")

    if total_files == 0:
        output.append("\n*Warning: No deployable files found in workspace.*")

    return "\n".join(output)


def _format_dry_run_theme(codename: str, workspace_path) -> str:
    """Format dry run preview for theme."""
    from pathlib import Path
    workspace_path = Path(workspace_path)

    output = [f"# Dry Run: Theme {codename}\n"]
    output.append("**Would sync:**\n")

    # List stylesheets
    css_dir = workspace_path / "stylesheets"
    if css_dir.exists():
        css_files = list(css_dir.glob("*.css"))
        output.append(f"- **Stylesheets:** {len(css_files)}")

    # List templates
    template_dir = workspace_path / "templates"
    if template_dir.exists():
        templates = list(template_dir.glob("*.html"))
        output.append(f"- **Templates:** {len(templates)}")

    return "\n".join(output)


def _resolve_theme_ids(db, codename: str, workspace_path) -> tuple:
    """Resolve theme_tid and template_set_sid from codename.

    Uses meta.json to get theme display name, then queries DB.
    Returns (theme_tid, template_set_sid) or (None, None) if not found.
    """
    import json
    import re
    from pathlib import Path
    workspace_path = Path(workspace_path)

    meta_path = workspace_path / "meta.json"
    if not meta_path.exists():
        return (None, None)

    with open(meta_path) as f:
        meta = json.load(f)

    theme_name = meta.get("name", codename)

    # Query theme by name
    themes = db.list_themes()
    for theme in themes:
        if theme.get("name", "").lower() == theme_name.lower():
            theme_tid = theme.get("tid")
            # Get templateset from theme properties (PHP serialized string)
            properties_str = theme.get("properties", "")
            template_set_sid = 1  # default
            if properties_str and isinstance(properties_str, str):
                # Parse PHP serialized format: s:11:"templateset";i:13; or s:11:"templateset";s:2:"13";
                match = re.search(r'"templateset";(?:i:(\d+)|s:\d+:"(\d+)")', properties_str)
                if match:
                    template_set_sid = int(match.group(1) or match.group(2))
            return (theme_tid, template_set_sid)

    return (None, None)


# ==================== Workspace Sync Helpers ====================

async def _sync_plugin(
    manager,
    sync_service,
    codename: str,
    visibility,
    full_pipeline: bool,
    dry_run: bool
) -> str:
    """Handle plugin sync (incremental or full pipeline)."""

    # Resolve workspace path
    workspace_path = manager.plugin_workspace.get_workspace_path(codename, visibility)
    if not workspace_path or not workspace_path.exists():
        return f"# Plugin Not Found\n\n**{codename}** not found in workspace."

    if dry_run:
        return _format_dry_run_plugin(codename, workspace_path)

    if full_pipeline:
        # Full uninstall/reinstall cycle
        uninstall_result = manager.deactivate_full(
            codename, uninstall=True, remove_files=True
        )
        if not uninstall_result.get("success"):
            return f"# Uninstall Failed\n\n{uninstall_result.get('error', 'Unknown error')}"

        install_result = manager.activate_full(codename)
        return _format_full_pipeline_result(codename, "plugin", install_result)
    else:
        # Incremental sync
        result = sync_service.sync_plugin(
            codename, workspace_path, visibility or "public", direction="to_db"
        )
        return _format_incremental_result(codename, "plugin", result)


async def _sync_theme(
    manager,
    sync_service,
    db,
    codename: str,
    visibility,
    full_pipeline: bool,
    dry_run: bool,
    direction: str = "to_db"
) -> str:
    """Handle theme sync (incremental or full pipeline)."""

    # Resolve workspace path
    workspace_path = manager.theme_workspace.get_workspace_path(codename)
    if not workspace_path or not workspace_path.exists():
        return f"# Theme Not Found\n\n**{codename}** not found in workspace."

    if dry_run:
        return _format_dry_run_theme(codename, workspace_path)

    if full_pipeline:
        # Full uninstall/reinstall cycle
        manager.uninstall_theme(codename)
        install_result = manager.install_theme(codename, mybb_db=db)
        return _format_full_pipeline_result(codename, "theme", install_result)
    else:
        # Incremental sync - need to resolve theme_tid and template_set_sid
        theme_tid, template_set_sid = _resolve_theme_ids(db, codename, workspace_path)
        if theme_tid is None:
            return (
                f"# Theme Not Installed\n\n"
                f"**{codename}** not found in MyBB database. "
                f"Run with `full_pipeline=True` to install first."
            )

        result = sync_service.sync_theme(
            codename, workspace_path, visibility or "public",
            direction=direction, theme_tid=theme_tid,
            template_set_sid=template_set_sid
        )
        return _format_incremental_result(codename, "theme", result)


# ==================== Handler Registry ====================

SYNC_HANDLERS = {
    "mybb_sync_export_templates": handle_sync_export_templates,
    "mybb_sync_export_stylesheets": handle_sync_export_stylesheets,
    "mybb_sync_start_watcher": handle_sync_start_watcher,
    "mybb_sync_stop_watcher": handle_sync_stop_watcher,
    "mybb_sync_status": handle_sync_status,
    "mybb_workspace_sync": handle_workspace_sync,
}
