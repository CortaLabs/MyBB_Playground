# MCP Integration Plan: Plugin Manager Tools

**Author:** ArchitectAgent-MCP-Integration
**Version:** v1.0
**Status:** Ready for Implementation
**Created:** 2026-01-18
**Confidence:** 0.95

> Complete integration plan connecting all MCP plugin/theme tools to the plugin_manager system.

---

## Executive Summary

The MyBB MCP server exposes 20 plugin/theme-related tools that currently bypass the `plugin_manager` system. This plan specifies how to refactor **12 tools** to delegate to `PluginManager`, ensuring a unified platform with:

- Single source of truth (plugin_manager)
- Workspace-based development workflow
- Proper meta.json tracking
- Database state consistency
- Export/packaging capabilities

**Strategy:** DELEGATE pattern - MCP tools become thin wrappers calling PluginManager methods.

---

## Integration Strategy

### Pattern: DELEGATE

```
MCP Tool Handler (server.py)
    |
    v
PluginManager.method()    <-- Single source of truth
    |
    v
Workspace + Database + TestForum
```

**Why DELEGATE:**
1. Minimizes code duplication
2. Preserves MCP tool signatures (backward compatible)
3. Leverages full plugin_manager feature set
4. Centralizes business logic in one place

### Import Strategy

The MCP server needs to import `plugin_manager`. Use the same pattern already established in `manager.py:802-804`:

```python
# In server.py, add near top of handle_tool():
import sys
from pathlib import Path

# Add plugin_manager to path (handles different execution contexts)
plugin_manager_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
if str(plugin_manager_path) not in sys.path:
    sys.path.insert(0, str(plugin_manager_path.parent))

from plugin_manager.manager import PluginManager
```

**Alternative:** Add `plugin_manager` as a package dependency in `mybb_mcp/pyproject.toml`. This is cleaner but requires package installation.

### Response Format

MCP tools return **markdown strings** for human readability. Preserve this pattern but enhance with structured data:

```python
def format_manager_result(result: dict, title: str) -> str:
    """Convert PluginManager dict result to markdown response."""
    lines = [f"# {title}\n"]

    if result.get("success"):
        lines.append(f"**Status:** Success")
    else:
        lines.append(f"**Status:** Failed")
        lines.append(f"**Error:** {result.get('error', 'Unknown error')}")
        return "\n".join(lines)

    # Add result details
    for key, value in result.items():
        if key not in ("success", "error"):
            lines.append(f"**{key.replace('_', ' ').title()}:** {value}")

    return "\n".join(lines)
```

---

## Tool-by-Tool Specifications

### Category 1: Plugin Creation & Analysis (4 tools to refactor)

#### 1.1 mybb_create_plugin

**Current:** Creates plugin directly in `TestForum/inc/plugins/` via `tools/plugins.py:create_plugin()`

**Target:** Delegates to `PluginManager.create_plugin()` creating in workspace

**Location:** `server.py:1409-1411`

**Current Implementation:**
```python
elif name == "mybb_create_plugin":
    from .tools.plugins import create_plugin
    return create_plugin(args, config)
```

**New Implementation:**
```python
elif name == "mybb_create_plugin":
    # Import plugin_manager
    import sys
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    # Map MCP args to plugin_manager params
    manager = PluginManager()

    # Convert hooks from list of strings to list of dicts
    hooks_input = args.get("hooks", [])
    hooks = [{"name": h, "handler": f"{args['codename']}_{h}", "priority": 10}
             for h in hooks_input] if hooks_input else None

    # Convert settings flag to settings list (empty list triggers settings creation)
    settings = [] if args.get("has_settings") else None

    result = manager.create_plugin(
        codename=args.get("codename", "").lower().replace(" ", "_"),
        display_name=args.get("name", ""),
        description=args.get("description", ""),
        author=args.get("author", "Developer"),
        version=args.get("version", "1.0.0"),
        visibility="public",  # Default, can add param later
        hooks=hooks,
        settings=settings,
        has_templates=args.get("has_templates", False),
        has_database=args.get("has_database", False)
    )

    # Format response
    if result.get("success"):
        return (
            f"# Plugin Created: {args.get('name')}\n\n"
            f"**Codename:** `{result['codename']}`\n"
            f"**Workspace:** `{result['workspace_path']}`\n"
            f"**Project ID:** {result['project_id']}\n\n"
            f"## Files Created\n" +
            "\n".join(f"- `{f}`" for f in result.get('files_created', [])) +
            f"\n\n**Next Steps:**\n"
            f"1. Edit plugin at `{result['workspace_path']}/{result['codename']}.php`\n"
            f"2. Install to TestForum: Use `mybb_plugin_activate` or Admin CP\n"
            f"3. Export for distribution: Use export workflow"
        )
    else:
        return f"# Error Creating Plugin\n\n{result.get('error', 'Unknown error')}"
```

**Parameter Mapping:**

| MCP Parameter | PluginManager Parameter | Transformation |
|---------------|-------------------------|----------------|
| `codename` | `codename` | `.lower().replace(" ", "_")` |
| `name` | `display_name` | Direct |
| `description` | `description` | Direct |
| `author` | `author` | Direct (default: "Developer") |
| `version` | `version` | Direct (default: "1.0.0") |
| `hooks` | `hooks` | `List[str]` -> `List[Dict]` with name/handler/priority |
| `has_settings` | `settings` | `bool` -> `[]` or `None` |
| `has_templates` | `has_templates` | Direct |
| `has_database` | `has_database` | Direct |
| (new) `visibility` | `visibility` | Optional, default "public" |

**Breaking Changes:**
- Plugin now created in `plugin_manager/plugins/public/` instead of `TestForum/inc/plugins/`
- Requires separate install step to deploy to TestForum

**Migration:**
- Existing TestForum plugins unaffected
- New plugins go to workspace, must be installed separately

---

#### 1.2 mybb_list_plugins

**Current:** File glob on `TestForum/inc/plugins/` directory

**Target:** Query both workspace AND TestForum, show unified view

**Location:** `server.py:1393-1400`

**New Implementation:**
```python
elif name == "mybb_list_plugins":
    import sys
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Get workspace plugins
    workspace_plugins = manager.db.list_projects(project_type="plugin")

    # Get TestForum plugins (existing behavior)
    testforum_files = list(plugins_dir.glob("*.php"))
    testforum_plugins = [f.stem for f in testforum_files
                         if not f.stem.startswith("__")]

    # Build response
    lines = ["# Plugins\n"]

    if workspace_plugins:
        lines.append("## Workspace Plugins")
        for p in workspace_plugins:
            status = "installed" if p['status'] == 'installed' else "workspace"
            lines.append(f"- `{p['codename']}` [{p['visibility']}] ({status})")

    lines.append("\n## TestForum Plugins")
    for p in sorted(testforum_plugins):
        # Check if in workspace
        in_workspace = any(wp['codename'] == p for wp in workspace_plugins)
        marker = " (managed)" if in_workspace else ""
        lines.append(f"- `{p}`{marker}")

    return "\n".join(lines)
```

**Breaking Changes:** None - output enhanced, not changed

---

#### 1.3 mybb_read_plugin

**Current:** Direct file read from TestForum

**Target:** Read from workspace if managed, TestForum if not

**Location:** `server.py:1402-1407`

**New Implementation:**
```python
elif name == "mybb_read_plugin":
    pname = args.get("name", "").replace(".php", "")

    import sys
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Check workspace first
    project = manager.db.get_project(pname, project_type="plugin")
    if project:
        # Read from workspace
        workspace_path = manager.plugin_workspace.get_workspace_path(
            pname, project['visibility']
        )
        php_path = workspace_path / f"{pname}.php"
        if php_path.exists():
            return f"# Plugin: {pname} (Workspace)\n\n```php\n{php_path.read_text()}\n```"

    # Fallback to TestForum
    ppath = plugins_dir / f"{pname}.php"
    if ppath.exists():
        return f"# Plugin: {pname} (TestForum)\n\n```php\n{ppath.read_text()}\n```"

    return f"Plugin '{pname}' not found in workspace or TestForum."
```

**Breaking Changes:** None - output enhanced

---

#### 1.4 mybb_analyze_plugin

**Current:** Regex parsing of PHP file for hooks, functions, features

**Target:** Load meta.json if managed, regex fallback for unmanaged

**Location:** `server.py:1430-1463`

**New Implementation:**
```python
elif name == "mybb_analyze_plugin":
    pname = args.get("name", "").replace(".php", "")

    import sys
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Check for managed plugin
    project = manager.db.get_project(pname, project_type="plugin")
    if project:
        workspace_path = manager.plugin_workspace.get_workspace_path(
            pname, project['visibility']
        )
        meta_path = workspace_path / "meta.json"
        if meta_path.exists():
            import json
            meta = json.loads(meta_path.read_text())

            lines = [f"# Plugin Analysis: {pname} (Managed)\n"]
            lines.append(f"**Display Name:** {meta.get('display_name', pname)}")
            lines.append(f"**Version:** {meta.get('version', 'Unknown')}")
            lines.append(f"**Author:** {meta.get('author', 'Unknown')}")
            lines.append(f"**Visibility:** {project['visibility']}")
            lines.append(f"**Status:** {project['status']}")

            hooks = meta.get('hooks', [])
            lines.append(f"\n## Hooks ({len(hooks)})")
            for h in hooks:
                lines.append(f"- `{h['name']}` -> `{h['handler']}`")

            settings = meta.get('settings', [])
            lines.append(f"\n## Settings ({len(settings)})")
            for s in settings:
                lines.append(f"- `{s['name']}`: {s.get('title', s['name'])}")

            lines.append(f"\n## Features")
            lines.append(f"- Templates: {'Yes' if meta.get('has_templates') else 'No'}")
            lines.append(f"- Database: {'Yes' if meta.get('has_database') else 'No'}")

            return "\n".join(lines)

    # Fallback: Original regex-based analysis for unmanaged plugins
    ppath = plugins_dir / f"{pname}.php"
    if not ppath.exists():
        return f"Plugin '{pname}' not found."

    # ... (keep existing regex logic for unmanaged plugins)
```

**Breaking Changes:** None - enhanced output for managed plugins

---

### Category 2: Plugin Lifecycle (3 tools to refactor)

#### 2.1 mybb_plugin_activate

**Current:** Updates MyBB plugins cache only (doesn't execute PHP activation)

**Target:** Call `PluginManager.install_plugin()` which handles full workflow

**Location:** `server.py:1511-1531`

**New Implementation:**
```python
elif name == "mybb_plugin_activate":
    pname = args.get("name", "").replace(".php", "")

    import sys
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Check if this is a managed plugin
    project = manager.db.get_project(pname, project_type="plugin")

    if project:
        # Use plugin_manager install workflow
        result = manager.install_plugin(pname, project['visibility'])

        if result.get("success"):
            return (
                f"# Plugin Installed: {pname}\n\n"
                f"**Status:** Deployed to TestForum\n"
                f"**Files Copied:** {result.get('files_copied', 0)}\n"
                f"**Templates Installed:** {result.get('templates_installed', 0)}\n\n"
                f"**Note:** Plugin files deployed. To fully activate (run `{pname}_activate()`), "
                f"use MyBB Admin CP: {config.mybb_url}/admin/index.php?module=config-plugins"
            )
        else:
            return f"# Install Failed: {pname}\n\n**Error:** {result.get('error')}"

    # Unmanaged plugin: Use legacy cache-only activation
    ppath = plugins_dir / f"{pname}.php"
    if not ppath.exists():
        return f"Error: Plugin '{pname}' not found in TestForum or workspace."

    cache = db.get_plugins_cache()
    if pname in cache["plugins"]:
        return f"Plugin '{pname}' is already active."

    updated_plugins = cache["plugins"] + [pname]
    db.update_plugins_cache(updated_plugins)

    return (
        f"# Plugin Activated: {pname} (Legacy)\n\n"
        f"Added to active plugins cache.\n\n"
        f"**Warning:** This plugin is not managed by plugin_manager. "
        f"Consider recreating it via `mybb_create_plugin` for full features.\n\n"
        f"**Warning:** This does NOT execute the PHP `{pname}_activate()` function. "
        f"For full activation, use MyBB Admin CP."
    )
```

**Breaking Changes:**
- Managed plugins now go through full install workflow
- Unmanaged plugins get deprecation warning

---

#### 2.2 mybb_plugin_deactivate

**Current:** Removes plugin from MyBB cache only

**Target:** Call `PluginManager.uninstall_plugin()` for managed plugins

**Location:** `server.py:1533-1550`

**New Implementation:**
```python
elif name == "mybb_plugin_deactivate":
    pname = args.get("name", "").replace(".php", "")

    import sys
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Check if this is a managed plugin
    project = manager.db.get_project(pname, project_type="plugin")

    if project:
        result = manager.uninstall_plugin(pname, project['visibility'])

        if result.get("success"):
            return (
                f"# Plugin Uninstalled: {pname}\n\n"
                f"**Status:** Removed from TestForum\n"
                f"**Files Removed:** {result.get('files_removed', 0)}\n"
                f"**Templates Removed:** {result.get('templates_removed', 0)}\n\n"
                f"**Note:** Plugin files removed from TestForum. "
                f"Workspace copy preserved at `{result.get('workspace_path')}`"
            )
        else:
            return f"# Uninstall Failed: {pname}\n\n**Error:** {result.get('error')}"

    # Unmanaged plugin: Legacy cache removal
    cache = db.get_plugins_cache()
    if pname not in cache["plugins"]:
        return f"Plugin '{pname}' is not currently active."

    updated_plugins = [p for p in cache["plugins"] if p != pname]
    db.update_plugins_cache(updated_plugins)

    return (
        f"# Plugin Deactivated: {pname} (Legacy)\n\n"
        f"Removed from active plugins cache.\n\n"
        f"**Warning:** This plugin is not managed by plugin_manager.\n"
        f"**Warning:** This does NOT execute the PHP `{pname}_deactivate()` function."
    )
```

**Breaking Changes:** None for unmanaged; managed plugins get full uninstall

---

#### 2.3 mybb_plugin_is_installed

**Current:** Checks MyBB cache only

**Target:** Check both plugin_manager status AND MyBB cache

**Location:** `server.py:1552-1559`

**New Implementation:**
```python
elif name == "mybb_plugin_is_installed":
    pname = args.get("name", "").replace(".php", "")

    import sys
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Check plugin_manager
    project = manager.db.get_project(pname, project_type="plugin")

    # Check MyBB cache
    is_active = db.is_plugin_installed(pname)

    # Check if file exists in TestForum
    file_exists = (plugins_dir / f"{pname}.php").exists()

    lines = [f"# Plugin Status: {pname}\n"]

    if project:
        lines.append("## Managed Plugin")
        lines.append(f"- **Workspace Status:** {project['status']}")
        lines.append(f"- **Visibility:** {project['visibility']}")
        lines.append(f"- **Version:** {project.get('version', 'Unknown')}")
    else:
        lines.append("## Unmanaged Plugin")
        lines.append("- Not tracked by plugin_manager")

    lines.append("\n## TestForum Status")
    lines.append(f"- **File Exists:** {'Yes' if file_exists else 'No'}")
    lines.append(f"- **Active in Cache:** {'Yes' if is_active else 'No'}")

    return "\n".join(lines)
```

**Breaking Changes:** None - enhanced output

---

### Category 3: Theme Tools (4 tools to refactor)

#### 3.1 mybb_list_themes

**Current:** Direct DB query for themes table

**Target:** Include workspace themes alongside DB themes

**Location:** `server.py:~1351`

**New Implementation:**
```python
elif name == "mybb_list_themes":
    import sys
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Get workspace themes
    workspace_themes = manager.db.list_projects(project_type="theme")

    # Get MyBB themes (existing behavior)
    mybb_themes = db.list_themes()

    lines = ["# Themes\n"]

    if workspace_themes:
        lines.append("## Workspace Themes")
        for t in workspace_themes:
            status = "installed" if t['status'] == 'installed' else "workspace"
            lines.append(f"- `{t['codename']}` [{t['visibility']}] ({status})")

    lines.append("\n## MyBB Installed Themes")
    for t in mybb_themes:
        in_workspace = any(wt['codename'] == t['name'].lower().replace(' ', '_')
                          for wt in workspace_themes)
        marker = " (managed)" if in_workspace else ""
        lines.append(f"- **{t['name']}** (tid: {t['tid']}){marker}")

    return "\n".join(lines)
```

---

#### 3.2 mybb_create_theme (NEW TOOL)

**Current:** Does not exist

**Target:** Create theme in workspace via `PluginManager.create_theme()`

**Add to tool definitions in `server.py` all_tools list:**

```python
Tool(
    name="mybb_create_theme",
    description="Create a new MyBB theme with proper structure in plugin_manager workspace.",
    inputSchema={
        "type": "object",
        "properties": {
            "codename": {
                "type": "string",
                "description": "Theme codename (lowercase, underscores)"
            },
            "name": {
                "type": "string",
                "description": "Theme display name"
            },
            "description": {
                "type": "string",
                "description": "Theme description"
            },
            "author": {
                "type": "string",
                "description": "Author name"
            },
            "version": {
                "type": "string",
                "description": "Version (default: 1.0.0)"
            },
            "parent_theme": {
                "type": "string",
                "description": "Parent theme name to inherit from"
            },
            "stylesheets": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of stylesheet names to create"
            }
        },
        "required": ["codename", "name"]
    }
)
```

**Handler Implementation:**
```python
elif name == "mybb_create_theme":
    import sys
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    # Convert stylesheets to proper format
    stylesheets_input = args.get("stylesheets", ["global.css"])
    stylesheets = [{"name": s, "attached_to": ["global"]} for s in stylesheets_input]

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
```

---

#### 3.3 mybb_read_stylesheet / 3.4 mybb_write_stylesheet

**Current:** Direct DB read/write

**Target:** HYBRID - Support both workspace and DB operations

For managed themes, read/write from workspace. For unmanaged, use DB.

**Implementation Note:** Keep existing DB operations for unmanaged themes. Add workspace-aware path when theme is managed by plugin_manager.

---

### Category 4: Sync & Export Tools (1 tool enhancement)

#### 4.1 mybb_sync_status

**Current:** Shows DiskSyncService status only

**Target:** Include plugin_manager workspace info

**Enhancement:**
```python
elif name == "mybb_sync_status":
    # ... existing sync_service.get_status() ...

    # Add plugin_manager status
    import sys
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))
    from plugin_manager.manager import PluginManager

    manager = PluginManager()

    plugins = manager.db.list_projects(project_type="plugin")
    themes = manager.db.list_projects(project_type="theme")

    # Add to response
    lines.append("\n## Plugin Manager Status")
    lines.append(f"- **Managed Plugins:** {len(plugins)}")
    lines.append(f"- **Managed Themes:** {len(themes)}")

    installed_plugins = [p for p in plugins if p['status'] == 'installed']
    installed_themes = [t for t in themes if t['status'] == 'installed']
    lines.append(f"- **Installed Plugins:** {len(installed_plugins)}")
    lines.append(f"- **Installed Themes:** {len(installed_themes)}")
```

---

### Category 5: Tools Unchanged (4 tools)

These tools remain unchanged as they serve reference/discovery purposes:

| Tool | Reason |
|------|--------|
| `mybb_list_hooks` | Static reference data, no state |
| `mybb_hooks_discover` | Scans MyBB core, not plugin-specific |
| `mybb_hooks_usage` | Analysis tool, standalone utility |
| `mybb_plugin_info` | Parses PHP `_info()`, useful for unmanaged plugins |

---

## Files to Modify

### Primary Changes

| File | Changes | Lines Affected |
|------|---------|----------------|
| `mybb_mcp/mybb_mcp/server.py` | Update 12 tool handlers | ~200 lines |
| `mybb_mcp/mybb_mcp/server.py` | Add `mybb_create_theme` tool definition | ~30 lines |
| `mybb_mcp/mybb_mcp/tools/plugins.py` | Deprecate `create_plugin()` function | Add deprecation notice |

### Optional: Create Bridge Module

For cleaner imports, optionally create:

```
mybb_mcp/mybb_mcp/adapters/plugin_manager_bridge.py
```

```python
"""Bridge module for plugin_manager integration."""
import sys
from pathlib import Path

def get_plugin_manager():
    """Get PluginManager instance with proper path setup."""
    pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
    if str(pm_path.parent) not in sys.path:
        sys.path.insert(0, str(pm_path.parent))

    from plugin_manager.manager import PluginManager
    return PluginManager()
```

Then handlers become:
```python
from .adapters.plugin_manager_bridge import get_plugin_manager
manager = get_plugin_manager()
```

---

## Testing Strategy

### Unit Tests

For each refactored tool:
1. Test with managed plugin/theme
2. Test with unmanaged plugin/theme (legacy behavior)
3. Test error handling

### Integration Tests

1. Create plugin via MCP -> verify workspace files
2. Install plugin via MCP -> verify TestForum deployment
3. Uninstall plugin via MCP -> verify cleanup
4. Full workflow: create -> install -> sync -> export

### Test Files

Create `mybb_mcp/tests/test_plugin_manager_integration.py`:

```python
def test_create_plugin_uses_plugin_manager():
    """Verify mybb_create_plugin creates in workspace."""
    ...

def test_activate_plugin_installs_managed():
    """Verify mybb_plugin_activate calls PluginManager.install_plugin()."""
    ...

def test_list_plugins_shows_both_sources():
    """Verify mybb_list_plugins shows workspace and TestForum plugins."""
    ...
```

---

## Rollout Plan

### Phase 6a: Core Plugin Tools (HIGH PRIORITY)
1. Refactor `mybb_create_plugin`
2. Refactor `mybb_plugin_activate`
3. Refactor `mybb_plugin_deactivate`
4. Add deprecation warnings to `tools/plugins.py:create_plugin()`

### Phase 6b: List/Query Tools (MEDIUM PRIORITY)
1. Refactor `mybb_list_plugins`
2. Refactor `mybb_read_plugin`
3. Refactor `mybb_analyze_plugin`
4. Refactor `mybb_plugin_is_installed`

### Phase 6c: Theme Tools (MEDIUM PRIORITY)
1. Add `mybb_create_theme` tool
2. Refactor `mybb_list_themes`
3. Enhance stylesheet tools (hybrid mode)

### Phase 6d: Sync Enhancement (LOW PRIORITY)
1. Enhance `mybb_sync_status` with plugin_manager info

---

## Success Criteria

1. All 12 refactored tools delegate to PluginManager
2. New `mybb_create_theme` tool works
3. Legacy (unmanaged) plugins still work with warnings
4. All operations create proper workspace structure
5. All state tracked in ProjectDatabase
6. Tests pass for all scenarios

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Import path issues | High | Use established sys.path pattern from manager.py |
| Breaking existing workflows | Medium | Maintain backward compatibility for unmanaged plugins |
| Database state inconsistency | Medium | Always use PluginManager for state updates |
| Response format changes | Low | Preserve markdown format, enhance not replace |

---

## Appendix: Full Tool Matrix

| Tool | Category | Action | Priority |
|------|----------|--------|----------|
| `mybb_create_plugin` | Creation | Refactor | HIGH |
| `mybb_list_plugins` | Query | Refactor | MEDIUM |
| `mybb_read_plugin` | Query | Refactor | MEDIUM |
| `mybb_analyze_plugin` | Analysis | Refactor | MEDIUM |
| `mybb_plugin_activate` | Lifecycle | Refactor | HIGH |
| `mybb_plugin_deactivate` | Lifecycle | Refactor | HIGH |
| `mybb_plugin_is_installed` | Query | Refactor | MEDIUM |
| `mybb_list_themes` | Query | Refactor | MEDIUM |
| `mybb_create_theme` | Creation | NEW | MEDIUM |
| `mybb_read_stylesheet` | Theme | Hybrid | LOW |
| `mybb_write_stylesheet` | Theme | Hybrid | LOW |
| `mybb_sync_status` | Sync | Enhance | LOW |
| `mybb_list_hooks` | Reference | Unchanged | - |
| `mybb_hooks_discover` | Reference | Unchanged | - |
| `mybb_hooks_usage` | Reference | Unchanged | - |
| `mybb_plugin_info` | Query | Unchanged | - |
