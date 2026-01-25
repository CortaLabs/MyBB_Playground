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
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def detect_embedded_templates(php_content: str) -> dict:
    """Detect embedded templates in plugin PHP code that need manual conversion.

    Scans for common patterns where plugins embed templates directly in PHP
    instead of using separate template files.

    Args:
        php_content: The PHP source code to analyze

    Returns:
        Dictionary with detection results:
        - has_embedded: bool - True if embedded templates detected
        - patterns_found: list - List of pattern descriptions
        - template_names: list - Extracted template names if detectable
        - recommendations: list - Suggested actions
    """
    result = {
        "has_embedded": False,
        "patterns_found": [],
        "template_names": [],
        "recommendations": []
    }

    # Pattern 1: $templates->set() - Direct template insertion
    templates_set = re.findall(
        r"\$templates->set\s*\(\s*['\"]([^'\"]+)['\"]",
        php_content
    )
    if templates_set:
        result["has_embedded"] = True
        result["patterns_found"].append(f"`$templates->set()` calls ({len(templates_set)} templates)")
        result["template_names"].extend(templates_set)

    # Pattern 2: $db->insert_query("templates" or insert_query_multiple - Raw DB insert
    db_insert_templates = re.findall(
        r"\$db->insert_query(?:_multiple)?\s*\(\s*['\"]templates['\"]",
        php_content
    )
    if db_insert_templates:
        result["has_embedded"] = True
        result["patterns_found"].append(f"Direct DB template inserts ({len(db_insert_templates)} found)")
        # Try to extract template names from nearby 'title' => 'name' patterns
        title_matches = re.findall(
            r"['\"]title['\"]\s*=>\s*['\"]([^'\"]+)['\"]",
            php_content
        )
        for title in title_matches:
            if title not in result["template_names"]:
                result["template_names"].append(title)

    # Pattern 3: find_replace_templatesets() - Template modification
    find_replace = re.findall(
        r"find_replace_templatesets\s*\(\s*['\"]([^'\"]+)['\"]",
        php_content
    )
    if find_replace:
        result["has_embedded"] = True
        result["patterns_found"].append(f"`find_replace_templatesets()` calls ({len(find_replace)} templates)")
        result["template_names"].extend(find_replace)

    # Pattern 4: $mybb->settings check with template variable injection
    # This is common but less problematic - just note it
    settings_template = re.findall(
        r"\$templates->get\s*\(\s*['\"]([^'\"]+)['\"]",
        php_content
    )
    # This is normal usage, don't flag

    # Remove duplicates from template names
    result["template_names"] = list(set(result["template_names"]))

    # Generate recommendations
    if result["has_embedded"]:
        result["recommendations"] = [
            "Extract embedded templates to `templates/` directory in workspace",
            "Template files should be named `{codename}_{template_name}.html`",
            "Remove `$templates->set()` calls from `_activate()` - installer handles templates",
            "Update `_deactivate()` to not delete templates (installer handles cleanup)",
            "See CLAUDE.md 'Plugin Templates' section for disk-first workflow"
        ]

    return result


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
    """Activate a plugin using the PHP lifecycle (bridge) after deploying files.

    Args:
        args: Must contain 'name' (plugin codename)
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted activation result
    """
    pname = args.get("name", "").replace(".php", "")
    force = args.get("force", False)
    if not pname:
        return "Error: Plugin codename is required."

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    manager = None
    project = None
    install_result = None

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()
        project = manager.db.get_project(pname)

        if project and project.get("type") == "plugin":
            visibility = project.get("visibility", "public")
            install_result = manager.install_plugin(pname, visibility)
            if not install_result.get("success"):
                return f"# Deploy Failed: {pname}\n\n**Error:** {install_result.get('error', 'Unknown error')}"
    except ImportError:
        manager = None
    except Exception as e:
        logger.warning(f"PluginManager install failed for {pname}: {e}")

    try:
        if manager:
            lifecycle = manager._get_lifecycle()
        else:
            from plugin_manager.lifecycle import PluginLifecycle
            lifecycle = PluginLifecycle(Path(config.mybb_root))

        status = lifecycle.get_status(pname)
        if not status.success:
            return f"Error: Bridge status failed: {status.error or 'unknown error'}"
        if not status.data.get("is_installed"):
            return (
                f"Error: Plugin '{pname}' is not installed. "
                "Use `mybb_plugin_install` or `mybb_plugin_deploy(action='reinstall')` first."
            )

        result = lifecycle.activate(pname, force=force)
        if not result.success:
            return f"Error: Bridge activate failed: {result.error or 'unknown error'}"
    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.exception(f"Error activating plugin {pname}")
        return f"Error activating plugin {pname}: {e}"

    actions = result.data.get("actions_taken", [])
    lines = [f"# Plugin Activated: {pname}\n"]
    lines.append(f"**PHP Lifecycle Actions:** {', '.join(actions) if actions else 'none'}")
    if install_result:
        lines.append(f"**Files Deployed:** {install_result.get('file_count', 0)}")
        if install_result.get("workspace_path"):
            lines.append(f"**Workspace:** `{install_result.get('workspace_path')}`")
    if install_result and install_result.get("warnings"):
        lines.append("")
        lines.append("**Warnings:**")
        for w in install_result["warnings"]:
            lines.append(f"- {w}")

    if manager and project:
        try:
            manager.db.update_project(codename=pname, status="active")
        except Exception:
            pass

    return "\n".join(lines)


async def handle_plugin_deactivate(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Deactivate a plugin using the PHP lifecycle (bridge).

    Args:
        args: Must contain 'name' (plugin codename)
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted deactivation result
    """
    pname = args.get("name", "").replace(".php", "")
    if not pname:
        return "Error: Plugin codename is required."

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    manager = None
    project = None

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()
        project = manager.db.get_project(pname)
    except ImportError:
        manager = None
    except Exception as e:
        logger.warning(f"PluginManager init failed for {pname}: {e}")

    try:
        if manager:
            lifecycle = manager._get_lifecycle()
        else:
            from plugin_manager.lifecycle import PluginLifecycle
            lifecycle = PluginLifecycle(Path(config.mybb_root))

        result = lifecycle.deactivate(pname, uninstall=False)
        if not result.success:
            return f"Error: Bridge deactivate failed: {result.error or 'unknown error'}"
    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.exception(f"Error deactivating plugin {pname}")
        return f"Error deactivating plugin {pname}: {e}"

    actions = result.data.get("actions_taken", [])
    lines = [f"# Plugin Deactivated: {pname}\n"]
    lines.append(f"**PHP Lifecycle Actions:** {', '.join(actions) if actions else 'none'}")

    if manager and project:
        try:
            manager.db.update_project(codename=pname, status="installed")
        except Exception:
            pass

    return "\n".join(lines)


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


async def handle_plugin_deploy(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Deploy plugin lifecycle wrapper for activate/deactivate or full reinstall."""
    codename = (args.get("codename") or args.get("name") or "").replace(".php", "")
    action = args.get("action", "")
    force = args.get("force", False)

    if not codename:
        return "Error: Plugin codename is required."
    if action not in {"activate", "deactivate", "reinstall"}:
        return "Error: action must be one of: activate, deactivate, reinstall."

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.manager import PluginManager

        manager = PluginManager()
    except ImportError as e:
        return f"Error: plugin_manager not available: {e}"
    except Exception as e:
        return f"Error: failed to initialize plugin_manager: {e}"

    if action == "activate":
        return await handle_plugin_activate({"name": codename, "force": force}, db, config, sync_service)
    if action == "deactivate":
        return await handle_plugin_deactivate({"name": codename}, db, config, sync_service)

    uninstall_result = manager.deactivate_full(codename, uninstall=True, remove_files=True)
    if not uninstall_result.get("success"):
        return f"# Plugin Reinstall Failed: {codename}\n\n**Error:** {uninstall_result.get('error', 'Uninstall failed')}"

    install_result = manager.activate_full(codename, force=force)
    if not install_result.get("success"):
        return f"# Plugin Reinstall Failed: {codename}\n\n**Error:** {install_result.get('error', 'Install failed')}"

    lines = [f"# Plugin Reinstalled: {codename}\n"]
    uninstall_actions = uninstall_result.get("php_lifecycle", {}).get("actions_taken", [])
    install_actions = install_result.get("php_lifecycle", {}).get("actions_taken", [])
    lines.append(f"**Uninstall Actions:** {', '.join(uninstall_actions) if uninstall_actions else 'none'}")
    lines.append(f"**Install Actions:** {', '.join(install_actions) if install_actions else 'none'}")
    if install_result.get("file_count") is not None:
        lines.append(f"**Files Deployed:** {install_result.get('file_count', 0)}")
    if install_result.get("workspace_path"):
        lines.append(f"**Workspace:** `{install_result.get('workspace_path')}`")

    warnings = []
    warnings.extend(uninstall_result.get("warnings", []))
    warnings.extend(install_result.get("warnings", []))
    if warnings:
        lines.append("")
        lines.append("**Warnings:**")
        for w in warnings:
            lines.append(f"- {w}")

    return "\n".join(lines)


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


# ==================== Export/Import Handlers ====================

async def handle_plugin_export(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Export a plugin as a distributable ZIP package.

    Args:
        args: Export configuration including:
            - codename (required): Plugin codename
            - output_path (optional): Where to save ZIP (default: exports/{codename}_v{version}.zip)
            - validate (optional): Whether to validate before export (default: True)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted export result
    """
    # Add plugin_manager to path
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from plugin_manager.workspace import PluginWorkspace
        from plugin_manager.database import ProjectDatabase
        from plugin_manager.packager import PluginPackager

        # Get required args
        codename = args.get("codename")
        if not codename:
            return "# Error: Missing Required Parameter\n\n**Error:** `codename` is required"

        validate = args.get("validate", True)
        output_path = args.get("output_path")

        # Initialize workspace and packager
        db_path = _get_plugin_manager_db_path()
        if not db_path.exists():
            return f"# Error: Plugin Manager Not Initialized\n\n**Error:** Database not found at `{db_path}`"

        project_db = ProjectDatabase(db_path)
        workspace_root = repo_root / "plugin_manager" / "plugins"
        workspace = PluginWorkspace(workspace_root=workspace_root)
        packager = PluginPackager(workspace=workspace, db=project_db)

        # Validate if requested
        if validate:
            validation_result = packager.validate_for_export(codename)
            if not validation_result["valid"]:
                errors_list = "\n".join(f"- ❌ {err}" for err in validation_result["errors"])
                warnings_list = ""
                if validation_result["warnings"]:
                    warnings_list = "\n\n## Warnings\n" + "\n".join(
                        f"- ⚠️ {warn}" for warn in validation_result["warnings"]
                    )
                return (
                    f"# Export Validation Failed: {codename}\n\n"
                    f"## Errors\n{errors_list}{warnings_list}\n\n"
                    f"Fix these errors before exporting, or use `validate=False` to skip validation."
                )

            # If valid but has warnings, include them in the output
            meta = validation_result.get("meta", {})
            version = meta.get("version", "0.0.0")
        else:
            # Get version without full validation
            workspace_path = workspace.get_workspace_path(codename)
            if not workspace_path:
                return f"# Error: Plugin Not Found\n\n**Error:** Plugin `{codename}` not found in workspace"

            meta_path = workspace_path / "meta.json"
            if meta_path.exists():
                import json
                with open(meta_path) as f:
                    meta = json.load(f)
                version = meta.get("version", "0.0.0")
            else:
                version = "0.0.0"

        # Determine output path
        if not output_path:
            exports_dir = repo_root / "exports"
            exports_dir.mkdir(exist_ok=True)
            output_path = exports_dir / f"{codename}_v{version}.zip"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create the ZIP
        result = packager.create_plugin_zip(
            codename=codename,
            output_path=output_path
        )

        # Format response
        if result.get("success"):
            files_list = "\n".join(f"- `{f}`" for f in result.get("files_included", []))
            warnings_section = ""
            if result.get("warnings"):
                warnings_list = "\n".join(f"- ⚠️ {w}" for w in result["warnings"])
                warnings_section = f"\n\n## Warnings\n{warnings_list}"

            return (
                f"# ✅ Plugin Exported Successfully\n\n"
                f"**Plugin:** `{codename}`\n"
                f"**Version:** `{version}`\n"
                f"**Output:** `{result['zip_path']}`\n\n"
                f"## Files Included\n{files_list}{warnings_section}\n\n"
                f"## Next Steps\n"
                f"- Share the ZIP file with users\n"
                f"- Upload to MyBB Extend or GitHub releases\n"
                f"- Users can extract to MyBB root to install"
            )
        else:
            error_msg = result.get("error", "Unknown error")
            warnings_section = ""
            if result.get("warnings"):
                warnings_list = "\n".join(f"- ⚠️ {w}" for w in result["warnings"])
                warnings_section = f"\n\n## Warnings\n{warnings_list}"
            return f"# ❌ Export Failed\n\n**Error:** {error_msg}{warnings_section}"

    except ImportError as e:
        return f"# Error: Plugin Manager Not Available\n\n**Error:** {str(e)}"
    except Exception as e:
        logger.exception(f"Error exporting plugin {args.get('codename')}")
        return f"# Error Exporting Plugin\n\n**Error:** {str(e)}"


# ==================== Import Handler ====================


def generate_meta_from_info(php_content: str, codename: str, visibility: str = "imported") -> dict:
    """Extract plugin info from _info() function using regex.

    Args:
        php_content: The PHP source code containing _info() function
        codename: Plugin codename to use
        visibility: Workspace visibility category (imported, forked, public, private)

    Returns:
        Dictionary matching meta.json schema with extracted info
    """
    meta = {
        "codename": codename,
        "name": codename,
        "display_name": codename,
        "version": "1.0.0",
        "author": "Unknown",
        "description": "",
        "visibility": visibility,
    }

    # Extract common patterns from _info() return array
    patterns = {
        "name": r"['\"]name['\"]\s*=>\s*['\"]([^'\"]+)['\"]",
        "version": r"['\"]version['\"]\s*=>\s*['\"]([^'\"]+)['\"]",
        "author": r"['\"]author['\"]\s*=>\s*['\"]([^'\"]+)['\"]",
        "description": r"['\"]description['\"]\s*=>\s*['\"]([^'\"]+)['\"]",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, php_content)
        if match:
            meta[key] = match.group(1)
            # Keep display_name in sync with name
            if key == "name":
                meta["display_name"] = match.group(1)

    return meta


async def handle_plugin_import(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Import a third-party plugin into workspace for development.

    Copies plugin files into the workspace directory structure and generates
    a basic meta.json from the plugin's _info() function.

    Args:
        args: Import configuration including:
            - source_path (required): Path to plugin (file or directory)
            - codename (optional): Target codename (auto-detected if not provided)
            - category (optional): Workspace category (imported, forked, public, private)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service instance (unused)

    Returns:
        Markdown formatted import result
    """
    from datetime import datetime

    # Add plugin_manager to path
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    temp_dir = None  # Track temp directory for cleanup (defined before try for exception handling)

    try:
        # Get required args
        source_path_str = args.get("source_path")
        if not source_path_str:
            return "# Error: Missing Required Parameter\n\n**Error:** `source_path` is required"

        source_path = Path(source_path_str)
        if not source_path.is_absolute():
            # Try relative to repo root
            source_path = repo_root / source_path

        if not source_path.exists():
            return f"# Error: Source Not Found\n\n**Error:** Source path does not exist: `{source_path_str}`"

        codename = args.get("codename")
        category = args.get("category", "imported")

        # Handle zip files - extract to temp and convert to directory path
        if source_path.is_file() and source_path.suffix == ".zip":
            temp_dir = tempfile.mkdtemp(prefix="mybb_import_")
            try:
                with zipfile.ZipFile(source_path, 'r') as zf:
                    zf.extractall(temp_dir)

                # Find the extracted content - could be at root or in a subfolder
                temp_path = Path(temp_dir)
                extracted_items = list(temp_path.iterdir())

                # If single directory extracted, use that as source
                if len(extracted_items) == 1 and extracted_items[0].is_dir():
                    source_path = extracted_items[0]
                else:
                    source_path = temp_path

                # Auto-detect codename from zip filename if not provided
                if not codename:
                    # Clean up zip filename: "DVZ Shoutbox_#15_stable.zip" -> "dvz_shoutbox"
                    zip_name = source_path_str.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                    zip_name = zip_name.replace(".zip", "")
                    # Take first part before version markers
                    zip_name = re.split(r"[_#\-]\d|_stable|_v\d", zip_name, 1)[0]
                    codename = re.sub(r"[^a-z0-9_]", "_", zip_name.lower()).strip("_")

            except zipfile.BadZipFile:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return f"# Error: Invalid Zip File\n\n**Error:** `{source_path_str}` is not a valid zip file."
            except Exception as e:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return f"# Error: Zip Extraction Failed\n\n**Error:** {str(e)}"

        # Detect Upload/ subfolder (standard MyBB Mods distribution format)
        # Check case-insensitively since some plugins use UPLOAD, Upload, or upload
        if source_path.is_dir():
            upload_subdir = None
            for item in source_path.iterdir():
                if item.is_dir() and item.name.lower() == "upload":
                    upload_subdir = item
                    break
            if upload_subdir:
                source_path = upload_subdir  # Use Upload/ as actual source

        # Validate category
        valid_categories = ["imported", "forked", "public", "private"]
        if category not in valid_categories:
            return f"# Error: Invalid Category\n\n**Error:** Category must be one of: {', '.join(valid_categories)}"

        # Detect source format and find main PHP file
        main_php_path = None
        source_files = []

        if source_path.is_file():
            if source_path.suffix == ".php":
                # Single file plugin
                main_php_path = source_path
                source_files = [source_path]
                codename = codename or source_path.stem
            else:
                return f"# Error: Unsupported File Type\n\n**Error:** Expected `.php` or `.zip` file, got `{source_path.suffix}`"
        elif source_path.is_dir():
            # Directory - find main PHP file containing _info() function
            php_files = list(source_path.glob("*.php"))
            if not php_files:
                # Check for inc/plugins/*.php pattern
                inc_plugins = list(source_path.glob("inc/plugins/*.php"))
                if inc_plugins:
                    php_files = inc_plugins

            if not php_files:
                return f"# Error: No PHP Files Found\n\n**Error:** No PHP files found in `{source_path}`"

            # Find the main plugin file (contains _info() function)
            for php_file in php_files:
                try:
                    content = php_file.read_text(encoding="utf-8", errors="replace")
                    if re.search(r"function\s+\w+_info\s*\(", content):
                        main_php_path = php_file
                        break
                except Exception:
                    continue

            if not main_php_path:
                # Fall back to first PHP file
                main_php_path = php_files[0]
                logger.warning(f"No _info() function found, using first PHP file: {main_php_path}")

            # Collect all files to copy
            source_files = list(source_path.rglob("*"))
            codename = codename or main_php_path.stem
        else:
            return f"# Error: Invalid Source\n\n**Error:** Source path is neither a file nor directory: `{source_path}`"

        # Sanitize codename
        codename = re.sub(r"[^a-z0-9_]", "_", codename.lower())

        # Create workspace directory
        workspace_path = repo_root / "plugin_manager" / "plugins" / category / codename

        if workspace_path.exists():
            return (
                f"# Error: Workspace Already Exists\n\n"
                f"**Error:** Plugin workspace already exists at `{workspace_path}`\n\n"
                f"**Options:**\n"
                f"- Use a different codename: `mybb_plugin_import(source_path=\"...\", codename=\"new_name\")`\n"
                f"- Delete existing workspace first: `mybb_delete_plugin(codename=\"{codename}\")`"
            )

        # Create workspace directory (structure comes from source, not predefined)
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Copy files
        files_copied = []

        if source_path.is_file():
            # Single file - copy to inc/plugins/
            dest = workspace_path / "inc" / "plugins" / source_path.name
            shutil.copy2(source_path, dest)
            files_copied.append(f"inc/plugins/{source_path.name}")
        else:
            # Directory - copy preserving EXACT source structure (no reorganization)
            for src_file in source_files:
                if src_file.is_file():
                    # Calculate relative path from source directory
                    rel_path = src_file.relative_to(source_path)

                    # Skip common non-plugin files
                    skip_patterns = ["README", "readme", "CHANGELOG", "changelog", "LICENSE", "license"]
                    if any(rel_path.name.startswith(p) for p in skip_patterns):
                        continue

                    # Preserve exact structure - just copy to same relative path
                    dest = workspace_path / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest)
                    files_copied.append(str(rel_path))

        # Generate meta.json from _info()
        template_detection = None
        try:
            php_content = main_php_path.read_text(encoding="utf-8", errors="replace")
            meta = generate_meta_from_info(php_content, codename, category)
            # Detect embedded templates that need manual conversion
            template_detection = detect_embedded_templates(php_content)
        except Exception as e:
            logger.warning(f"Failed to read main PHP for meta extraction: {e}")
            meta = {
                "codename": codename,
                "name": codename,
                "version": "1.0.0",
                "author": "Unknown",
                "description": "",
                "visibility": category,
            }

        # Add import tracking fields
        meta["import_source"] = str(source_path)
        meta["import_date"] = datetime.now().isoformat()

        # Write meta.json
        meta_path = workspace_path / "meta.json"
        meta_path.write_text(json.dumps(meta, indent=2))

        # Register in database so mybb_plugin_install can find it
        from plugin_manager.database import ProjectDatabase
        project_db = ProjectDatabase(repo_root / ".plugin_manager" / "projects.db")
        project_db.add_project(
            codename=codename,
            display_name=meta.get("name", codename),
            workspace_path=str(workspace_path),
            type="plugin",
            visibility=category,
            status="imported",
            version=meta.get("version", "1.0.0"),
            description=meta.get("description", ""),
            author=meta.get("author", "Unknown")
        )

        # Clean up temp directory if we extracted from zip
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

        # Format response
        files_list = "\n".join(f"- `{f}`" for f in files_copied[:20])  # Limit to 20 files in output
        if len(files_copied) > 20:
            files_list += f"\n- ... and {len(files_copied) - 20} more files"

        # Build template warning section
        template_warning = ""
        if template_detection and template_detection["has_embedded"]:
            template_warning = "\n## ⚠️ Embedded Templates Detected\n\n"
            template_warning += "**This plugin has templates embedded in PHP code that need manual conversion.**\n\n"
            template_warning += "**Patterns Found:**\n"
            for pattern in template_detection["patterns_found"]:
                template_warning += f"- {pattern}\n"
            if template_detection["template_names"]:
                template_warning += f"\n**Templates to Extract ({len(template_detection['template_names'])}):**\n"
                for tpl_name in template_detection["template_names"][:15]:
                    template_warning += f"- `{tpl_name}`\n"
                if len(template_detection["template_names"]) > 15:
                    template_warning += f"- ... and {len(template_detection['template_names']) - 15} more\n"
            template_warning += "\n**Recommendations:**\n"
            for rec in template_detection["recommendations"]:
                template_warning += f"- {rec}\n"
            template_warning += "\n"

        return (
            f"# Plugin Imported Successfully\n\n"
            f"**Codename:** `{codename}`\n"
            f"**Name:** {meta.get('name', codename)}\n"
            f"**Version:** {meta.get('version', '1.0.0')}\n"
            f"**Author:** {meta.get('author', 'Unknown')}\n"
            f"**Workspace:** `{workspace_path}`\n\n"
            f"## Files Copied ({len(files_copied)} total)\n{files_list}\n\n"
            f"{template_warning}"
            f"## Meta.json Created\n"
            f"```json\n{json.dumps(meta, indent=2)}\n```\n\n"
            f"## Next Steps\n"
            f"1. **Review the imported files** in `{workspace_path}`\n"
            f"2. **Test the plugin:** `mybb_plugin_install(codename=\"{codename}\")`\n"
            f"3. {'**IMPORTANT: Extract embedded templates** before production use' if template_detection and template_detection['has_embedded'] else 'Check for any issues in the PHP code'}\n"
        )

    except ImportError as e:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return f"# Error: Plugin Manager Not Available\n\n**Error:** {str(e)}"
    except Exception as e:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        logger.exception(f"Error importing plugin from {args.get('source_path')}")
        return f"# Error Importing Plugin\n\n**Error:** {str(e)}"


# ==================== Handler Registry ====================

PLUGIN_HANDLERS = {
    "mybb_list_plugins": handle_list_plugins,
    "mybb_read_plugin": handle_read_plugin,
    "mybb_create_plugin": handle_create_plugin,
    "mybb_delete_plugin": handle_delete_plugin,
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
    "mybb_plugin_deploy": handle_plugin_deploy,
    "mybb_plugin_status": handle_plugin_status,
    "mybb_plugin_export": handle_plugin_export,
    "mybb_plugin_import": handle_plugin_import,
}
