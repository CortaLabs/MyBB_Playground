"""Plugin handlers for MCP tools.

Handlers for plugin operations:
- Plugin listing (workspace and legacy)
- Plugin reading and analysis
- Plugin creation
- Hook discovery and usage
- Plugin lifecycle (install, activate, deactivate, uninstall)
- Plugin status queries
"""

import re
import sys
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_plugin_manager_db_path() -> Path:
    """Get the canonical database path for plugin_manager.

    Uses plugin_manager.Config to get the correct database path,
    ensuring consistency with the plugin_manager module.

    Returns:
        Path to projects.db
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from plugin_manager.config import Config

    config = Config(repo_root=repo_root)
    return config.database_path


# ==================== Plugin Listing Handlers ====================

async def handle_list_plugins(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """List all plugins from workspace and legacy locations.

    Args:
        args: No required arguments
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted list of plugins
    """
    plugins_dir = Path(config.mybb_root) / "inc" / "plugins"

    try:
        # Add plugin_manager to path
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        from plugin_manager.database import ProjectDatabase

        # Get workspace plugins from ProjectDatabase
        db_path = _get_plugin_manager_db_path()
        if db_path.exists():
            project_db = ProjectDatabase(db_path)
            workspace_plugins = project_db.list_projects(type="plugin")
        else:
            workspace_plugins = []

        # Get legacy plugins from filesystem
        legacy_plugins = []
        if plugins_dir.exists():
            all_files = [f.stem for f in plugins_dir.glob("*.php") if f.stem != "index"]
            # Filter out plugins already in workspace
            workspace_codenames = {p['codename'] for p in workspace_plugins}
            legacy_plugins = [p for p in all_files if p not in workspace_codenames]

        # Build response
        lines = ["# Plugins\n"]

        if workspace_plugins:
            lines.append("## Workspace Plugins (Managed)")
            lines.append("| Name | Status | Visibility | Version |")
            lines.append("|------|--------|------------|---------|")
            for p in sorted(workspace_plugins, key=lambda x: x['codename']):
                lines.append(f"| {p['display_name']} (`{p['codename']}`) | {p['status']} | {p['visibility']} | {p['version']} |")
            lines.append("")

        if legacy_plugins:
            lines.append("## Legacy Plugins (Unmanaged)")
            for p in sorted(legacy_plugins):
                lines.append(f"- `{p}` (Not in workspace)")
            lines.append("")

        if not workspace_plugins and not legacy_plugins:
            return "# Plugins\n\nNo plugins found."

        lines.append("\n**Tip:** Use `mybb_create_plugin` to create workspace-managed plugins.")
        return "\n".join(lines)

    except ImportError:
        # Fallback to legacy filesystem scan only
        if not plugins_dir.exists():
            return "Plugins directory not found."
        plugins = [f.stem for f in plugins_dir.glob("*.php") if f.stem != "index"]
        lines = [f"# Plugins ({len(plugins)})\n"]
        for p in sorted(plugins):
            lines.append(f"- `{p}`")
        return "\n".join(lines)


async def handle_read_plugin(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Read a plugin's source code.

    Args:
        args: Must contain 'name' (plugin codename)
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted plugin source with metadata
    """
    plugins_dir = Path(config.mybb_root) / "inc" / "plugins"
    pname = args.get("name", "").replace(".php", "")

    try:
        # Add plugin_manager to path
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        from plugin_manager.database import ProjectDatabase

        # Check workspace first
        db_path = _get_plugin_manager_db_path()
        workspace_path = None
        meta_info = None

        if db_path.exists():
            project_db = ProjectDatabase(db_path)
            project = project_db.get_project(pname)
            if project:
                workspace_path = repo_root / project['workspace_path']
                # Try to read meta.json for additional context
                meta_path = workspace_path / "meta.json"
                if meta_path.exists():
                    with open(meta_path, 'r') as f:
                        meta_info = json.load(f)

        # Read plugin source (workspace or legacy)
        if workspace_path and workspace_path.exists():
            plugin_file = workspace_path / "src" / f"{pname}.php"
            if plugin_file.exists():
                source = plugin_file.read_text()
                location = f"Workspace: `{project['workspace_path']}/src/{pname}.php`"
            else:
                return f"# Plugin: {pname}\n\n**Error:** Plugin found in database but source file missing."
        else:
            # Fallback to legacy TestForum location
            ppath = plugins_dir / f"{pname}.php"
            if not ppath.exists():
                return f"Plugin '{pname}' not found in workspace or TestForum."
            source = ppath.read_text()
            location = f"Legacy: `TestForum/inc/plugins/{pname}.php` (Not managed)"

        # Build response
        lines = [f"# Plugin: {pname}\n"]
        lines.append(f"**Location:** {location}\n")

        if meta_info:
            lines.append("## Metadata")
            lines.append(f"- **Display Name:** {meta_info.get('plugin', {}).get('name', 'N/A')}")
            lines.append(f"- **Version:** {meta_info.get('plugin', {}).get('version', 'N/A')}")
            lines.append(f"- **Author:** {meta_info.get('plugin', {}).get('author', 'N/A')}")
            lines.append(f"- **Visibility:** {meta_info.get('workspace', {}).get('visibility', 'N/A')}")
            lines.append("")

        lines.append("## Source Code\n")
        lines.append(f"```php\n{source}\n```")

        return "\n".join(lines)

    except ImportError:
        # Fallback to legacy read
        ppath = plugins_dir / f"{pname}.php"
        if not ppath.exists():
            return f"Plugin '{pname}' not found."
        return f"# Plugin: {pname}\n\n```php\n{ppath.read_text()}\n```"


async def handle_create_plugin(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Create a new plugin in the workspace.

    Args:
        args: Plugin configuration including codename, name, description, etc.
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted creation result
    """
    # Add plugin_manager to path
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager
        from forge_config import ForgeConfig

        manager = PluginManager()

        # Load forge config for developer defaults
        forge_config = ForgeConfig(repo_root)

        # Map MCP args to plugin_manager params (forge config provides defaults)
        codename = args.get("codename", "").lower().replace(" ", "_").replace("-", "_")
        display_name = args.get("name", "")
        description = args.get("description", "")
        author = args.get("author", forge_config.developer_name)
        author_site = args.get("author_site", forge_config.developer_website)
        version = args.get("version", "1.0.0")
        visibility = args.get("visibility", forge_config.defaults.get("visibility", "public"))

        # Convert hooks from list of strings to format expected by PluginManager
        hooks_input = args.get("hooks", [])
        hooks = [{"name": h, "handler": f"{codename}_{h}", "priority": 10}
                 for h in hooks_input] if hooks_input else None

        # Convert has_settings flag to settings list
        settings = [] if args.get("has_settings") else None

        result = manager.create_plugin(
            codename=codename,
            display_name=display_name,
            description=description,
            author=author,
            version=version,
            visibility=visibility,
            hooks=hooks,
            settings=settings,
            has_templates=args.get("has_templates", False),
            has_database=args.get("has_database", False)
        )

        # Format response as markdown
        if result.get("success"):
            files_list = "\n".join(f"- `{f}`" for f in result.get('files_created', []))
            return (
                f"# Plugin Created: {display_name}\n\n"
                f"**Codename:** `{result['codename']}`\n"
                f"**Workspace:** `{result['workspace_path']}`\n"
                f"**Project ID:** {result['project_id']}\n"
                f"**Visibility:** {visibility}\n\n"
                f"## Files Created\n{files_list}\n\n"
                f"## Next Steps\n"
                f"1. Edit the plugin at `{result['workspace_path']}/src/{codename}.php`\n"
                f"2. Run `mybb_plugin_activate {codename}` to deploy to TestForum\n"
                f"3. Activate in MyBB Admin CP to run PHP hooks\n"
                f"4. Export for distribution when ready"
            )
        else:
            return f"# Error Creating Plugin\n\n**Error:** {result.get('error', 'Unknown error')}"

    except ImportError as e:
        # Fallback to legacy create_plugin if plugin_manager not available
        from ..tools.plugins import create_plugin
        return create_plugin(args, config)
    except ValueError as e:
        return f"# Error Creating Plugin\n\n**Error:** {str(e)}"
    except Exception as e:
        return f"# Error Creating Plugin\n\n**Error:** {str(e)}"


# ==================== Hook Discovery Handlers ====================

async def handle_list_hooks(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """List available MyBB hooks from the reference.

    Args:
        args: Optional 'category' and 'search' filters
        db: MyBBDatabase instance (unused)
        config: Server configuration (unused)
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted hooks reference
    """
    from ..tools.plugins import get_hooks_reference
    return get_hooks_reference(args.get("category"), args.get("search"))


async def handle_hooks_discover(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Discover hooks by scanning MyBB PHP files.

    Args:
        args: Optional 'path', 'category', and 'search' filters
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted discovered hooks
    """
    from ..tools.hooks_expanded import discover_hooks
    return discover_hooks(
        config.mybb_root,
        path=args.get("path"),
        category=args.get("category"),
        search=args.get("search")
    )


async def handle_hooks_usage(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Find where a hook is used in installed plugins.

    Args:
        args: Must contain 'hook_name' (hook to search for)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted usage results
    """
    from ..tools.hooks_expanded import find_hook_usage
    return find_hook_usage(config.mybb_root, args.get("hook_name"))


# ==================== Plugin Analysis Handlers ====================

async def handle_analyze_plugin(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Analyze a plugin's structure, hooks, settings, and templates.

    Args:
        args: Must contain 'name' (plugin codename)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted plugin analysis
    """
    plugins_dir = Path(config.mybb_root) / "inc" / "plugins"
    pname = args.get("name", "").replace(".php", "")

    try:
        # Add plugin_manager to path
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        from plugin_manager.database import ProjectDatabase

        # Check if workspace plugin
        db_path = _get_plugin_manager_db_path()
        is_workspace = False
        meta_info = None

        if db_path.exists():
            project_db = ProjectDatabase(db_path)
            project = project_db.get_project(pname)
            if project:
                workspace_path = repo_root / project['workspace_path']
                meta_path = workspace_path / "meta.json"
                if meta_path.exists():
                    with open(meta_path, 'r') as f:
                        meta_info = json.load(f)
                    is_workspace = True

        lines = [f"# Plugin Analysis: {pname}\n"]

        if is_workspace and meta_info:
            # Use structured meta.json data
            lines.append(f"**Source:** Workspace (Managed)\n")

            plugin_info = meta_info.get('plugin', {})
            workspace_info = meta_info.get('workspace', {})

            lines.append("## Plugin Information")
            lines.append(f"- **Name:** {plugin_info.get('name', 'N/A')}")
            lines.append(f"- **Author:** {plugin_info.get('author', 'N/A')}")
            lines.append(f"- **Version:** {plugin_info.get('version', 'N/A')}")
            lines.append(f"- **Compatibility:** {plugin_info.get('compatibility', 'N/A')}")
            lines.append(f"- **Visibility:** {workspace_info.get('visibility', 'N/A')}")
            lines.append(f"- **Status:** {project['status']}")

            # Hooks
            hooks = meta_info.get('hooks', [])
            lines.append(f"\n## Hooks ({len(hooks)})")
            for h in hooks[:20]:
                hook_name = h if isinstance(h, str) else h.get('name', 'unknown')
                priority = h.get('priority', 10) if isinstance(h, dict) else 10
                lines.append(f"- `{hook_name}` (priority: {priority})")

            # Settings
            settings = meta_info.get('settings', [])
            lines.append(f"\n## Settings")
            if settings:
                lines.append(f"- **Count:** {len(settings)}")
                for s in settings[:10]:
                    setting_name = s if isinstance(s, str) else s.get('name', 'unknown')
                    lines.append(f"  - `{setting_name}`")
            else:
                lines.append("- None")

            # Templates
            templates = meta_info.get('templates', [])
            lines.append(f"\n## Templates")
            if templates:
                lines.append(f"- **Count:** {len(templates)}")
                for t in templates[:10]:
                    template_name = t if isinstance(t, str) else t.get('name', 'unknown')
                    lines.append(f"  - `{template_name}`")
            else:
                lines.append("- None")

            # Database
            database = meta_info.get('database', {})
            lines.append(f"\n## Database")
            if database and database.get('tables'):
                tables = database.get('tables', [])
                lines.append(f"- **Tables:** {len(tables)}")
                for table in tables[:5]:
                    table_name = table if isinstance(table, str) else table.get('name', 'unknown')
                    lines.append(f"  - `{table_name}`")
            else:
                lines.append("- No database tables")

            return "\n".join(lines)

        else:
            # Fall back to PHP parsing for legacy plugins
            ppath = plugins_dir / f"{pname}.php"
            if not ppath.exists():
                return f"Plugin '{pname}' not found."

            content = ppath.read_text()
            lines = [f"# Plugin Analysis: {pname}\n"]
            lines.append("**Source:** Legacy (Unmanaged)\n")

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

    except ImportError:
        # Fallback to legacy PHP parsing
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


# ==================== Plugin Cache Handlers ====================

async def handle_plugin_list_installed(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """List installed/active plugins from datacache.

    Args:
        args: No required arguments
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted list of installed plugins
    """
    cache = db.get_plugins_cache()
    if not cache["plugins"]:
        return "# Installed Plugins\n\nNo plugins are currently active.\n\n*Note: This shows plugins from datacache. File-based listing available via mybb_list_plugins.*"

    lines = [f"# Installed Plugins ({len(cache['plugins'])})\n"]
    for plugin in sorted(cache["plugins"]):
        lines.append(f"- `{plugin}`")

    lines.append(f"\n**Raw Cache**: `{cache['raw']}`")
    return "\n".join(lines)


async def handle_plugin_info(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Get plugin info by reading the _info() function.

    Args:
        args: Must contain 'name' (plugin codename)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted plugin info
    """
    plugins_dir = Path(config.mybb_root) / "inc" / "plugins"
    pname = args.get("name", "").replace(".php", "")
    ppath = plugins_dir / f"{pname}.php"
    if not ppath.exists():
        return f"Plugin '{pname}' not found in {plugins_dir}"

    content = ppath.read_text()
    info_func = f"{pname}_info"

    if info_func not in content:
        return f"# Plugin: {pname}\n\nNo `{info_func}()` function found."

    # Extract _info function content
    pattern = rf"function\s+{info_func}\s*\(\s*\)\s*\{{([^}}]+(?:\{{[^}}]+\}}[^}}]*)*)\}}"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return f"# Plugin: {pname}\n\nCould not parse `{info_func}()` function."

    info_content = match.group(1)
    lines = [f"# Plugin Info: {pname}\n"]

    # Extract key fields
    for field in ["name", "description", "website", "author", "authorsite", "version", "compatibility", "codename"]:
        field_pattern = rf'"{field}"\s*=>\s*"([^"]+)"'
        field_match = re.search(field_pattern, info_content)
        if field_match:
            lines.append(f"**{field.title()}**: {field_match.group(1)}")

    return "\n".join(lines)


# ==================== Plugin Lifecycle Handlers ====================

async def handle_plugin_activate(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Activate a plugin by deploying to TestForum and updating cache.

    Args:
        args: Must contain 'name' (plugin codename)
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted activation result
    """
    plugins_dir = Path(config.mybb_root) / "inc" / "plugins"
    pname = args.get("name", "").replace(".php", "")

    # Try to use PluginManager for managed plugins
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()

        # Check if this is a managed plugin in the workspace
        project = manager.db.get_project(pname)

        if project and project.get('type') == 'plugin':
            # Use plugin_manager install workflow (copies files to TestForum)
            visibility = project.get('visibility', 'public')
            result = manager.install_plugin(pname, visibility)

            if result.get("success"):
                return (
                    f"# Plugin Installed: {pname}\n\n"
                    f"**Status:** Deployed to TestForum\n"
                    f"**Files Copied:** {result.get('files_copied', 0)}\n"
                    f"**Templates Installed:** {result.get('templates_installed', 0)}\n"
                    f"**Workspace:** `{result.get('workspace_path', 'N/A')}`\n\n"
                    f"**Note:** Plugin files deployed to TestForum. To fully activate (run `{pname}_activate()`), "
                    f"use MyBB Admin CP: {config.mybb_url}/admin/index.php?module=config-plugins"
                )
            else:
                return f"# Install Failed: {pname}\n\n**Error:** {result.get('error', 'Unknown error')}"

    except ImportError:
        pass  # Fall through to legacy behavior
    except Exception as e:
        # Log but continue to legacy if install fails
        logger.warning(f"PluginManager install failed for {pname}: {e}")

    # Legacy behavior: Check if plugin exists in TestForum and update cache
    ppath = plugins_dir / f"{pname}.php"
    if not ppath.exists():
        return f"Error: Plugin '{pname}' not found in TestForum or workspace."

    cache = db.get_plugins_cache()
    if pname in cache["plugins"]:
        return f"Plugin '{pname}' is already active."

    # Add to active plugins (legacy cache-only activation)
    updated_plugins = cache["plugins"] + [pname]
    db.update_plugins_cache(updated_plugins)

    return (
        f"# Plugin Activated: {pname} (Legacy)\n\n"
        f"Added to active plugins cache.\n\n"
        f"**Warning:** This plugin is not managed by plugin_manager. "
        f"Consider recreating it via `mybb_create_plugin` for full workspace features.\n\n"
        f"**Warning:** This does NOT execute the PHP `{pname}_activate()` function. "
        f"For full activation including database setup, templates, and settings, "
        f"use MyBB's Admin CP at {config.mybb_url}/admin/index.php?module=config-plugins"
    )


async def handle_plugin_deactivate(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Deactivate a plugin by removing from TestForum and updating cache.

    Args:
        args: Must contain 'name' (plugin codename)
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted deactivation result
    """
    pname = args.get("name", "").replace(".php", "")

    # Try to use PluginManager for managed plugins
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()

        # Check if this is a managed plugin in the workspace
        project = manager.db.get_project(pname)

        if project and project.get('type') == 'plugin':
            # Use plugin_manager uninstall workflow (removes files from TestForum)
            visibility = project.get('visibility', 'public')
            result = manager.uninstall_plugin(pname, visibility)

            if result.get("success"):
                return (
                    f"# Plugin Uninstalled: {pname}\n\n"
                    f"**Status:** Removed from TestForum\n"
                    f"**Files Removed:** {result.get('files_removed', 0)}\n"
                    f"**Templates Removed:** {result.get('templates_removed', 0)}\n\n"
                    f"**Note:** Plugin files removed from TestForum. "
                    f"Workspace copy preserved at `{result.get('workspace_path', 'N/A')}`\n\n"
                    f"**Reminder:** This does NOT execute the PHP `{pname}_deactivate()` function. "
                    f"For full deactivation including cleanup, use MyBB's Admin CP first."
                )
            else:
                return f"# Uninstall Failed: {pname}\n\n**Error:** {result.get('error', 'Unknown error')}"

    except ImportError:
        pass  # Fall through to legacy behavior
    except Exception as e:
        # Log but continue to legacy if uninstall fails
        logger.warning(f"PluginManager uninstall failed for {pname}: {e}")

    # Legacy behavior: Just update cache
    cache = db.get_plugins_cache()
    if pname not in cache["plugins"]:
        return f"Plugin '{pname}' is not currently active."

    # Remove from active plugins (legacy cache-only deactivation)
    updated_plugins = [p for p in cache["plugins"] if p != pname]
    db.update_plugins_cache(updated_plugins)

    return (
        f"# Plugin Deactivated: {pname} (Legacy)\n\n"
        f"Removed from active plugins cache.\n\n"
        f"**Warning:** This plugin is not managed by plugin_manager.\n\n"
        f"**Warning:** This does NOT execute the PHP `{pname}_deactivate()` function. "
        f"For full deactivation including cleanup, use MyBB's Admin CP at "
        f"{config.mybb_url}/admin/index.php?module=config-plugins"
    )


async def handle_plugin_is_installed(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Check if a plugin is installed/active.

    Args:
        args: Must contain 'name' (plugin codename)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted installation status
    """
    pname = args.get("name", "").replace(".php", "")

    try:
        # Add plugin_manager to path
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        from plugin_manager.database import ProjectDatabase

        # Check workspace database first
        db_path = _get_plugin_manager_db_path()
        workspace_status = None
        workspace_project = None

        if db_path.exists():
            project_db = ProjectDatabase(db_path)
            workspace_project = project_db.get_project(pname)
            if workspace_project:
                workspace_status = workspace_project.get('status')

        # Check MyBB cache
        is_active = db.is_plugin_installed(pname)

        # Build response
        lines = [f"# Plugin Status: {pname}\n"]

        if workspace_project:
            lines.append(f"**Workspace Status:** {workspace_status}")
            lines.append(f"**MyBB Cache Status:** {'Active' if is_active else 'Not Active'}")
            lines.append("")

            if workspace_status == 'installed' and is_active:
                lines.append("Plugin is installed in both workspace database and MyBB cache.")
            elif workspace_status == 'installed' and not is_active:
                lines.append("**Warning:** Plugin marked 'installed' in workspace but not active in MyBB cache.")
                lines.append("   Run `mybb_plugin_activate` to sync.")
            elif workspace_status != 'installed' and is_active:
                lines.append("**Warning:** Plugin active in MyBB but not marked 'installed' in workspace.")
                lines.append("   Workspace status may be out of sync.")
            else:
                lines.append("Plugin is not currently installed/active.")

        else:
            # Legacy plugin (not in workspace)
            lines.append(f"**Source:** Legacy (Unmanaged)")
            lines.append(f"**MyBB Cache Status:** {'Active' if is_active else 'Not Active'}")
            lines.append("")
            if is_active:
                lines.append("Plugin is active in MyBB cache (legacy plugin).")
            else:
                lines.append("Plugin is not active in MyBB cache.")

        return "\n".join(lines)

    except ImportError:
        # Fallback to MyBB cache check only
        is_active = db.is_plugin_installed(pname)

        if is_active:
            return f"# Plugin Status: {pname}\n\n**Status**: Active\n\nPlugin is currently in the active plugins cache."
        else:
            return f"# Plugin Status: {pname}\n\n**Status**: Not Active\n\nPlugin is not in the active plugins cache."


# ==================== Plugin Full Lifecycle Handlers ====================

async def handle_plugin_install(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Full plugin installation: deploy files AND execute PHP lifecycle.

    Args:
        args: Must contain 'codename', optional 'force'
        db: MyBBDatabase instance (unused)
        config: Server configuration (unused)
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted installation result
    """
    codename = args.get("codename", "").replace(".php", "")
    force = args.get("force", False)

    if not codename:
        return "Error: Plugin codename is required."

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()
        result = manager.activate_full(codename, force=force)

        if result.get("success"):
            lines = [f"# Plugin Installed: {codename}\n"]

            # PHP Lifecycle results
            php = result.get("php_lifecycle", {})
            actions = php.get("actions_taken", [])
            lines.append(f"**PHP Lifecycle Actions:** {', '.join(actions) if actions else 'none'}")

            # Files deployed
            files = result.get("files_deployed", [])
            if files:
                lines.append(f"**Files Deployed:** {len(files)}")

            # Workspace path
            if result.get("workspace_path"):
                lines.append(f"**Workspace:** `{result['workspace_path']}`")

            lines.append("")
            lines.append("Plugin is now fully installed and active in MyBB.")

            # Warnings
            if result.get("warnings"):
                lines.append("")
                lines.append("**Warnings:**")
                for w in result["warnings"]:
                    lines.append(f"- {w}")

            return "\n".join(lines)
        else:
            return f"# Plugin Install Failed: {codename}\n\n**Error:** {result.get('error', 'Unknown error')}"

    except ImportError as e:
        return f"Error: plugin_manager not available: {e}"
    except Exception as e:
        logger.exception(f"Error in mybb_plugin_install for {codename}")
        return f"Error installing plugin {codename}: {e}"


async def handle_plugin_uninstall(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Full plugin uninstallation: execute PHP lifecycle AND optionally remove files.

    Args:
        args: Must contain 'codename', optional 'uninstall' and 'remove_files'
        db: MyBBDatabase instance (unused)
        config: Server configuration (unused)
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted uninstallation result
    """
    codename = args.get("codename", "").replace(".php", "")
    uninstall = args.get("uninstall", False)
    remove_files = args.get("remove_files", False)

    if not codename:
        return "Error: Plugin codename is required."

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()
        result = manager.deactivate_full(codename, uninstall=uninstall, remove_files=remove_files)

        if result.get("success"):
            lines = [f"# Plugin Uninstalled: {codename}\n"]

            # PHP Lifecycle results
            php = result.get("php_lifecycle", {})
            actions = php.get("actions_taken", [])
            lines.append(f"**PHP Lifecycle Actions:** {', '.join(actions) if actions else 'none'}")

            if php.get("uninstalled"):
                lines.append("**Uninstall Function:** Executed (_uninstall ran)")

            # Files removed
            files = result.get("files_removed", [])
            if files:
                lines.append(f"**Files Removed:** {len(files)}")

            lines.append("")
            if uninstall and remove_files:
                lines.append("Plugin fully uninstalled: PHP cleanup done, settings/tables removed, files deleted.")
            elif uninstall:
                lines.append("Plugin uninstalled: PHP cleanup done, settings/tables removed. Files remain in TestForum.")
            elif remove_files:
                lines.append("Plugin deactivated and files removed. Settings/tables preserved (use uninstall=true to remove).")
            else:
                lines.append("Plugin deactivated. Files and settings preserved.")

            # Warnings
            if result.get("warnings"):
                lines.append("")
                lines.append("**Warnings:**")
                for w in result["warnings"]:
                    lines.append(f"- {w}")

            return "\n".join(lines)
        else:
            return f"# Plugin Uninstall Failed: {codename}\n\n**Error:** {result.get('error', 'Unknown error')}"

    except ImportError as e:
        return f"Error: plugin_manager not available: {e}"
    except Exception as e:
        logger.exception(f"Error in mybb_plugin_uninstall for {codename}")
        return f"Error uninstalling plugin {codename}: {e}"


async def handle_plugin_status(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Get comprehensive plugin status via PHP bridge.

    Args:
        args: Must contain 'codename'
        db: MyBBDatabase instance (unused)
        config: Server configuration (unused)
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted status information
    """
    codename = args.get("codename", "").replace(".php", "")

    if not codename:
        return "Error: Plugin codename is required."

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()
        result = manager.get_plugin_status(codename)

        if result.get("success"):
            lines = [f"# Plugin Status: {codename}\n"]

            # Plugin info
            info = result.get("info", {})
            if info:
                lines.append(f"**Name:** {info.get('name', codename)}")
                lines.append(f"**Version:** {info.get('version', 'unknown')}")
                lines.append(f"**Author:** {info.get('author', 'unknown')}")
                lines.append(f"**Compatibility:** {info.get('compatibility', '*')}")
                lines.append("")

            # Status flags
            lines.append("**Status:**")
            lines.append(f"- Installed: {'Yes' if result.get('is_installed') else 'No'}")
            lines.append(f"- Active: {'Yes' if result.get('is_active') else 'No'}")
            lines.append(f"- Compatible: {'Yes' if result.get('is_compatible') else 'No'}")

            # Available functions
            lines.append("")
            lines.append("**Available Functions:**")
            funcs = []
            if result.get('has_install'):
                funcs.append('_install')
            if result.get('has_uninstall'):
                funcs.append('_uninstall')
            if result.get('has_activate'):
                funcs.append('_activate')
            if result.get('has_deactivate'):
                funcs.append('_deactivate')
            lines.append(f"- {', '.join(funcs) if funcs else 'none'}")

            # File path
            if result.get('file_path'):
                lines.append("")
                lines.append(f"**File:** `{result['file_path']}`")

            return "\n".join(lines)
        else:
            return f"# Plugin Status: {codename}\n\n**Error:** {result.get('error', 'Plugin not found or error occurred')}"

    except ImportError as e:
        return f"Error: plugin_manager not available: {e}"
    except Exception as e:
        logger.exception(f"Error in mybb_plugin_status for {codename}")
        return f"Error getting plugin status for {codename}: {e}"


# ==================== Delete Handlers ====================

async def handle_delete_plugin(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Permanently delete a plugin from workspace and database.

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

        result = manager.delete_plugin(codename, archive=archive, force=force)

        if result.get("success"):
            lines = [
                f"# Plugin Deleted: {codename}",
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
            lines = [f"# Error Deleting Plugin\n\n**Error:** {error_msg}"]
            if warnings:
                lines.append("\n## Warnings")
                for w in warnings:
                    lines.append(f"- {w}")
            return "\n".join(lines)

    except ImportError as e:
        return f"Error: plugin_manager not available: {e}"
    except Exception as e:
        logger.exception(f"Error deleting plugin {args.get('codename')}")
        return f"Error deleting plugin: {e}"


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
        logger.exception(f"Error deleting theme {args.get('codename')}")
        return f"Error deleting theme: {e}"


# ==================== Handler Registry ====================

PLUGIN_HANDLERS = {
    "mybb_list_plugins": handle_list_plugins,
    "mybb_read_plugin": handle_read_plugin,
    "mybb_create_plugin": handle_create_plugin,
    "mybb_delete_plugin": handle_delete_plugin,
    "mybb_delete_theme": handle_delete_theme,
    "mybb_list_hooks": handle_list_hooks,
    "mybb_hooks_discover": handle_hooks_discover,
    "mybb_hooks_usage": handle_hooks_usage,
    "mybb_analyze_plugin": handle_analyze_plugin,
    "mybb_plugin_list_installed": handle_plugin_list_installed,
    "mybb_plugin_info": handle_plugin_info,
    "mybb_plugin_activate": handle_plugin_activate,
    "mybb_plugin_deactivate": handle_plugin_deactivate,
    "mybb_plugin_is_installed": handle_plugin_is_installed,
    "mybb_plugin_install": handle_plugin_install,
    "mybb_plugin_uninstall": handle_plugin_uninstall,
    "mybb_plugin_status": handle_plugin_status,
}
