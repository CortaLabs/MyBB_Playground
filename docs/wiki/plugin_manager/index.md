# Plugin Manager System

**Status:** Stable
**Version:** 1.0
**Location:** `plugin_manager/`

## Overview

The Plugin Manager is a comprehensive system for managing MyBB plugin and theme development, installation, and lifecycle management. It provides workspace-based development with intelligent file deployment, database tracking, and PHP lifecycle integration.

## System Architecture

```
plugin_manager/
├── manager.py              # Main PluginManager orchestrator (25 public methods)
├── workspace.py            # PluginWorkspace & ThemeWorkspace classes
├── installer.py            # PluginInstaller & ThemeInstaller (file deployment)
├── database.py             # ProjectDatabase (SQLite tracking)
├── lifecycle.py            # PluginLifecycle & BridgeResult (PHP bridge)
├── config.py               # Configuration management
└── schema.py               # meta.json validation
```

### Component Dependency Graph

```
manager.py
├── depends: config, database, workspace, installer, schema, lifecycle
└── exports: PluginManager class

workspace.py
├── classes: PluginWorkspace, ThemeWorkspace
└── depends: schema

installer.py
├── classes: PluginInstaller, ThemeInstaller
└── depends: config, database, workspace

database.py
├── class: ProjectDatabase
└── handles: projects table, history table, deployed_files manifest

lifecycle.py
├── classes: PluginLifecycle, BridgeResult
└── executes: subprocess calls to mcp_bridge.php

config.py
├── class: Config
└── handles: workspace paths, mybb_root, database paths

schema.py
└── functions: validate_meta, create_default_meta, load_meta, save_meta
```

## Core Features

### 1. Workspace Management
- Directory structure mirroring MyBB's layout for simple overlay installation
- Separate public/private workspaces
- meta.json schema validation
- Automatic workspace scaffolding

**[→ Workspace Documentation](workspace.md)**

### 2. File Deployment
- Intelligent file copying with checksum tracking
- Automatic backups (stored outside TestForum)
- Complete cleanup on uninstall
- Deployment manifest tracking

**[→ Deployment Documentation](deployment.md)**

### 3. PHP Lifecycle Bridge
- Subprocess execution of MyBB plugin lifecycle functions
- Consistent BridgeResult dataclass responses
- Full compatibility checking
- Cache management integration

**[→ Lifecycle Documentation](lifecycle.md)**

### 4. Project Database
- SQLite database tracking all projects
- Deployment manifest storage
- History tracking for all actions
- Query methods with filtering

**[→ Database Documentation](database.md)**

### 5. Configuration Management
- Flexible configuration with sensible defaults
- User config at `.plugin_manager/config.json`
- Legacy format support
- Path resolution helpers

## Quick Start

### Create a Plugin

```python
from plugin_manager import PluginManager

pm = PluginManager()
result = pm.create_plugin(
    codename="my_plugin",
    display_name="My Plugin",
    description="Plugin description",
    author="Your Name",
    hooks=[
        {"name": "index_start", "handler": "my_plugin_index", "priority": 10}
    ]
)

print(result["workspace_path"])  # plugin_manager/plugins/public/my_plugin/
```

### Install and Activate

```python
# Deploy files to TestForum
pm.install_plugin("my_plugin")

# Run PHP lifecycle (_install, _activate)
pm.activate_full("my_plugin")
```

### Uninstall and Remove

```python
# Deactivate and uninstall via PHP
pm.deactivate_full("my_plugin", uninstall=True)

# Remove files from TestForum
pm.uninstall_plugin("my_plugin")
```

## Documentation Sections

- **[Workspace Management](workspace.md)** — Directory structure, meta.json schema, validation
- **[Deployment System](deployment.md)** — File installation, backups, manifest tracking
- **[Lifecycle Management](lifecycle.md)** — PHP Bridge, BridgeResult, activation workflows
- **[Database Schema](database.md)** — SQLite schema, ProjectDatabase methods, queries

## Key Concepts

### Workspace vs Deployment

- **Workspace** = Development directory structure (`plugin_manager/plugins/public/my_plugin/`)
- **Deployment** = Files copied to TestForum (`TestForum/inc/plugins/my_plugin.php`)

The workspace mirrors MyBB's directory layout, so deployment is a simple overlay operation.

### Plugin Lifecycle States

1. **Development** — Created in workspace, meta.json exists
2. **Installed** — Files deployed to TestForum (tracked in database)
3. **Activated** — PHP _install() and _activate() executed (tracked in MyBB cache)

### Visibility

- **public** — Workspace at `plugin_manager/plugins/public/`
- **private** — Workspace at `plugin_manager/plugins/private/`

Affects workspace location only; doesn't impact deployment to TestForum.

## File Locations

| Path | Purpose |
|------|---------|
| `plugin_manager/plugins/` | Plugin workspace root |
| `plugin_manager/themes/` | Theme workspace root |
| `plugin_manager/backups/` | Backup storage (outside TestForum) |
| `plugin_manager/projects.db` | SQLite project database |
| `.plugin_manager/config.json` | User configuration |
| `TestForum/mcp_bridge.php` | PHP lifecycle bridge |

## Related Documentation

- [MCP Tools Reference](../mcp_tools/README.md) — MCP tool wrappers for Plugin Manager
- [Plugin Development Best Practices](../best_practices/plugins.md) — Guidelines for plugin development
- [Architecture Overview](../architecture/README.md) — System-wide architecture
