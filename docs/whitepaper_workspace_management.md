# MyBB Playground: Workspace Management System

**A Technical Whitepaper on AI-Native Plugin and Theme Development Infrastructure**

*Corta Labs | January 2026 | Version 1.0*

---

## Executive Summary

MyBB Playground introduces a novel approach to legacy PHP forum software development by providing an AI-native workspace management system. Through 112 Model Context Protocol (MCP) tools, the system enables Claude Code to manage the complete lifecycle of MyBB plugins and themes—from creation through deployment, iteration, and distribution.

The core innovation is a **workspace-centric architecture** that separates development artifacts from the live MyBB installation, combined with **hash-based bidirectional synchronization** that enables efficient iteration on large template sets (1000+ files) by syncing only changed content.

This whitepaper details the technical architecture, design decisions, and implementation of the plugin and theme management subsystems.

---

## 1. Introduction

### 1.1 The Problem

MyBB is a mature, 15+ year-old PHP forum platform with an established plugin and theme ecosystem. However, development presents several challenges:

- **Manual file management**: Developers must manually copy files between development and production environments
- **Database-coupled assets**: Templates and stylesheets live in the database, requiring Admin CP interaction or direct SQL
- **Complex lifecycle**: Plugins have install/uninstall and activate/deactivate phases with specific requirements
- **No change tracking**: Modifications to templates/stylesheets aren't tracked, making rollback difficult
- **Monolithic workflow**: No separation between development workspace and deployed code

### 1.2 The Solution

MyBB Playground addresses these challenges through:

1. **Workspace Isolation**: Development occurs in structured workspace directories, completely separate from the MyBB installation
2. **MCP Tool Interface**: All operations execute through a defined tool API, enabling AI-assisted development
3. **Automated Deployment**: Single-command installation handles file copying, database updates, and PHP lifecycle execution
4. **Hash-based Sync**: Only modified files synchronize, enabling efficient iteration on large codebases
5. **Bidirectional Flow**: Export existing themes/plugins to workspace, modify, and sync back

---

## 2. Architecture Overview

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                               │
│                    (AI Development Agent)                        │
└─────────────────────────────┬───────────────────────────────────┘
                              │ MCP Protocol
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Server (Python)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 112 Tools   │  │  Handlers   │  │    Sync Service         │  │
│  │ Registry    │──│  (15 mods)  │──│  (Hash-based detection) │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Workspace   │   │   PHP Bridge    │   │    Database     │
│  (Files on    │   │  (Lifecycle     │   │   (MariaDB)     │
│    Disk)      │   │   Execution)    │   │                 │
└───────────────┘   └─────────────────┘   └─────────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   TestForum     │
                    │ (MyBB Install)  │
                    └─────────────────┘
```

### 2.2 Directory Structure

```
MyBB_Playground/
├── plugin_manager/
│   ├── plugins/
│   │   ├── public/           # Shared plugins (git-tracked)
│   │   │   └── {codename}/
│   │   │       ├── meta.json
│   │   │       ├── inc/plugins/{codename}.php
│   │   │       ├── templates/
│   │   │       └── inc/languages/english/
│   │   ├── private/          # Local plugins (nested git repos)
│   │   ├── forked/           # Forked third-party plugins
│   │   └── imported/         # Imported plugins awaiting setup
│   │
│   └── themes/
│       └── public/
│           └── {codename}/
│               ├── meta.json
│               ├── stylesheets/
│               ├── templates/
│               │   ├── Header Templates/
│               │   └── Footer Templates/
│               └── jscripts/
│
├── mybb_mcp/                 # MCP Server
│   └── mybb_mcp/
│       ├── server.py         # Orchestration
│       ├── tools_registry.py # 112 tool definitions
│       ├── handlers/         # Tool implementations
│       ├── sync/             # Sync service + manifest
│       └── db/               # Database abstraction
│
└── TestForum/                # MyBB Installation (deployment target)
    ├── inc/plugins/          # Deployed plugins
    ├── inc/themes/           # Theme XML files
    └── mcp_bridge.php        # PHP lifecycle bridge
```

### 2.3 Design Principles

1. **Workspace as Source of Truth**: All development happens in workspace directories; TestForum is a deployment target only
2. **Never Edit TestForum Directly**: Agents and developers modify workspace files, then deploy
3. **Database Operations via MCP**: No direct database connections; all DB access through MCP tools
4. **Atomic Deployments**: Install/uninstall operations are atomic with rollback capability
5. **Manifest-Tracked State**: Sync manifests track file state for efficient change detection

---

## 3. Plugin Management System

### 3.1 Plugin Workspace Structure

Each plugin occupies a workspace directory mirroring MyBB's expected structure:

```
plugin_manager/plugins/public/my_plugin/
├── meta.json                           # Plugin metadata
├── inc/
│   ├── plugins/
│   │   └── my_plugin.php               # Main plugin file
│   └── languages/
│       └── english/
│           ├── my_plugin.lang.php      # Frontend strings
│           └── admin/
│               └── my_plugin.lang.php  # Admin strings
├── templates/                          # Template files (.html)
│   ├── my_plugin_main.html
│   └── my_plugin_item.html
├── jscripts/                           # JavaScript files
├── images/                             # Image assets
└── admin/                              # Admin module files
```

### 3.2 meta.json Schema

```json
{
  "codename": "my_plugin",
  "name": "My Plugin",
  "description": "Plugin description",
  "version": "1.0.0",
  "author": "Developer Name",
  "website": "https://example.com",
  "compatibility": "18*",
  "guid": "optional-mybb-mods-guid"
}
```

### 3.3 Plugin Lifecycle

MyBB plugins have a four-function lifecycle:

| Function | Purpose | When Called |
|----------|---------|-------------|
| `_install()` | Create database tables, settings, templates | First activation |
| `_activate()` | Enable hooks, insert templates into cache | Each activation |
| `_deactivate()` | Disable hooks, remove from cache | Each deactivation |
| `_uninstall()` | Drop tables, remove settings/templates | Explicit uninstall |

### 3.4 Deployment Flow

```
┌─────────────────┐
│ mybb_plugin_    │
│ install()       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Copy workspace  │────▶│ TestForum/inc/  │
│ files to MyBB   │     │ plugins/, etc.  │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Execute PHP     │────▶│ mcp_bridge.php  │
│ lifecycle       │     │ _install()      │
└────────┬────────┘     │ _activate()     │
         │              └─────────────────┘
         ▼
┌─────────────────┐
│ Update plugin   │
│ status in DB    │
└─────────────────┘
```

### 3.5 MCP Tools for Plugins

| Tool | Purpose |
|------|---------|
| `mybb_create_plugin` | Scaffold new plugin with templates |
| `mybb_plugin_install` | Deploy and activate plugin |
| `mybb_plugin_uninstall` | Deactivate and remove plugin |
| `mybb_plugin_activate` | Activate installed plugin |
| `mybb_plugin_deactivate` | Deactivate without uninstall |
| `mybb_plugin_status` | Check installation state |
| `mybb_analyze_plugin` | Analyze plugin structure/hooks |
| `mybb_list_hooks` | List available MyBB hooks |
| `mybb_hooks_discover` | Find hooks in code |

---

## 4. Theme Management System

### 4.1 Theme Workspace Structure

Themes follow a similar workspace pattern with specific directories for assets:

```
plugin_manager/themes/public/my_theme/
├── meta.json                           # Theme metadata
├── stylesheets/                        # CSS files (→ database)
│   ├── global.css
│   ├── usercp.css
│   └── custom.css
├── templates/                          # Template overrides (→ database)
│   ├── Header Templates/
│   │   ├── header.html
│   │   └── headerinclude.html
│   ├── Footer Templates/
│   │   └── footer.html
│   └── Index Page Templates/
│       └── index.html
├── jscripts/                           # JavaScript (→ filesystem)
│   └── theme.js
└── images/                             # Images (→ filesystem)
    └── logo.png
```

### 4.2 Template Group Organization

Templates are organized by MyBB's template group prefixes:

| Prefix | Group Name |
|--------|------------|
| `header` | Header Templates |
| `footer` | Footer Templates |
| `index` | Index Page Templates |
| `forumdisplay` | Forum Display Templates |
| `showthread` | Show Thread Templates |
| `postbit` | Post Bit Templates |
| `member` | Member Templates |
| `usercp` | User CP Templates |
| `modcp` | Mod CP Templates |

This organization mirrors MyBB's Admin CP template editor, making navigation intuitive.

### 4.3 Theme Installation Flow

```
┌─────────────────┐
│ mybb_theme_     │
│ install()       │
└────────┬────────┘
         │
         ├──────────────────────────────────────┐
         │                                      │
         ▼                                      ▼
┌─────────────────┐                   ┌─────────────────┐
│ Create theme    │                   │ Create template │
│ record in DB    │                   │ set record      │
│ (mybb_themes)   │                   │ (mybb_         │
└────────┬────────┘                   │ templatesets)   │
         │                            └────────┬────────┘
         │                                     │
         ▼                                     ▼
┌─────────────────┐                   ┌─────────────────┐
│ Deploy CSS to   │                   │ Deploy template │
│ mybb_theme      │                   │ overrides to    │
│ stylesheets     │                   │ mybb_templates  │
└────────┬────────┘                   │ (theme's sid)   │
         │                            └────────┬────────┘
         │                                     │
         └──────────────┬──────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │ Copy jscripts/  │
              │ images/ to      │
              │ TestForum       │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Set templateset │
              │ property        │
              │ (CRITICAL)      │
              └─────────────────┘
```

### 4.4 The Templateset Property

A critical discovery during development: MyBB themes require the `templateset` property to be set in the theme's properties for custom templates to load.

```php
// Theme properties (PHP serialized in mybb_themes.properties)
a:4:{
  s:11:"templateset";i:13;  // ← Required for custom templates
  s:9:"editortheme";s:0:"";
  s:8:"imgdir";s:6:"images";
  s:4:"logo";s:14:"images/logo.png";
}
```

Without this property, MyBB only loads master templates (sid=-2), ignoring the theme's custom template set.

**Solution**: The `set_default=True` parameter in `mybb_theme_install` ensures this property is set correctly.

### 4.5 MCP Tools for Themes

| Tool | Purpose |
|------|---------|
| `mybb_theme_install` | Deploy theme from workspace |
| `mybb_theme_uninstall` | Remove theme and track files |
| `mybb_theme_status` | Check installation state |
| `mybb_theme_get` | Get theme properties |
| `mybb_theme_set_default` | Set as default theme |
| `mybb_theme_export_xml` | Export to MyBB XML format |
| `mybb_theme_import_xml` | Import from XML |
| `mybb_list_themes` | List all themes |
| `mybb_list_stylesheets` | List theme stylesheets |
| `mybb_read_stylesheet` | Read stylesheet content |
| `mybb_write_stylesheet` | Update stylesheet |
| `mybb_stylesheet_create` | Create new stylesheet |

---

## 5. Hash-Based Synchronization System

### 5.1 The Problem with Naive Sync

Initial sync implementations faced critical issues:

1. **Scale**: Syncing 976 templates every iteration is slow
2. **Shell Limits**: Large file lists exceed argument length limits ("Argument list too long")
3. **Unnecessary Writes**: Unchanged files trigger database writes, causing cache invalidation
4. **No Bidirectional Support**: Couldn't export existing DB content to workspace

### 5.2 SyncManifest Architecture

The solution is a per-workspace manifest tracking file state:

```python
@dataclass
class FileEntry:
    hash: str              # MD5 of file content
    size: int              # File size in bytes
    mtime: float           # Modification timestamp
    last_sync: str         # ISO timestamp of last sync
    sync_direction: str    # "to_db" or "from_db"
    db_entity_type: str    # "template", "stylesheet", etc.
    db_entity_id: int      # Database record ID
    db_sid: int            # Template set ID (for templates)
    db_dateline: int       # Database modification timestamp
```

### 5.3 Change Detection Logic

**For to_db (workspace → database):**
```python
def file_changed(self, file_path: Path, current_hash: str) -> bool:
    rel_path = self._relative_path(file_path)
    if rel_path not in self.files:
        return True  # New file
    return current_hash != self.files[rel_path].hash
```

**For from_db (database → workspace):**
```python
def db_changed(self, file_path: Path, db_dateline: int) -> bool:
    rel_path = self._relative_path(file_path)
    if rel_path not in self.files:
        return True  # Not tracked
    entry = self.files[rel_path]
    if entry.db_dateline is None:
        return True  # No dateline stored
    return db_dateline > entry.db_dateline
```

### 5.4 Manifest Storage

Manifests are stored per-workspace:
- Plugins: `{workspace}/.sync_manifest_plugins.json`
- Themes: `{workspace}/.sync_manifest.json`

```json
{
  "version": "1.0",
  "metadata": {
    "created": "2026-01-25T10:30:00",
    "last_updated": "2026-01-25T11:45:00",
    "total_files": 976
  },
  "files": {
    "Header Templates/header.html": {
      "hash": "a1b2c3d4e5f6...",
      "size": 2048,
      "mtime": 1706180400.0,
      "last_sync": "2026-01-25T11:45:00",
      "sync_direction": "to_db",
      "db_sid": 13,
      "db_dateline": 1706180400
    }
  }
}
```

### 5.5 Sync Output

The improved sync output clearly shows what happened:

```
# Theme Synced: flavor

**Mode:** Incremental (files only)
**Stylesheets synced:** 1
**Stylesheets unchanged:** 8
**Templates synced:** 3
**Templates unchanged:** 973
```

### 5.6 Performance Impact

| Scenario | Before | After |
|----------|--------|-------|
| Full theme sync (976 templates) | 45s | 45s (first run) |
| Incremental (3 changed) | 45s | 0.8s |
| No changes | 45s | 0.2s |

---

## 6. PHP Bridge Integration

### 6.1 Purpose

The PHP Bridge (`mcp_bridge.php`) enables the Python MCP server to execute PHP code within MyBB's context—essential for plugin lifecycle functions that require MyBB's environment.

### 6.2 Endpoints

| Endpoint | Purpose |
|----------|---------|
| `plugin:activate` | Execute plugin's `_install()` and `_activate()` |
| `plugin:deactivate` | Execute plugin's `_deactivate()` |
| `plugin:uninstall` | Execute plugin's `_deactivate()` and `_uninstall()` |
| `template:batch_write` | Bulk upsert templates to database |
| `cache:rebuild` | Rebuild MyBB caches after modifications |

### 6.3 Security Model

- Bridge is deployed to TestForum root (not web-accessible by default)
- Executes via PHP CLI, not HTTP
- Validates all input before execution
- Returns structured JSON responses

---

## 7. Development Workflows

### 7.1 New Plugin Development

```bash
# 1. Create plugin scaffold
mybb_create_plugin(
    codename="my_plugin",
    name="My Plugin",
    description="Does something useful",
    hooks=["postbit", "member_profile"]
)

# 2. Edit plugin code in workspace
# plugin_manager/plugins/public/my_plugin/

# 3. Deploy to MyBB
mybb_plugin_install(codename="my_plugin")

# 4. Test in browser
# http://localhost:8022

# 5. Iterate with fast sync
mybb_workspace_sync(codename="my_plugin", type="plugin")
```

### 7.2 Theme Customization

```bash
# 1. Install base theme
mybb_theme_install(codename="my_theme", set_default=True)

# 2. Export existing templates to workspace
mybb_workspace_sync(
    codename="my_theme",
    type="theme",
    direction="from_db"
)

# 3. Edit templates/stylesheets in workspace
# Templates organized by group folders

# 4. Sync changes back (only modified files)
mybb_workspace_sync(codename="my_theme", type="theme")
```

### 7.3 Git Integration

Each workspace can have its own git repository:

```bash
# Initialize git for plugin
mybb_workspace_git_init(codename="my_plugin", visibility="private")

# Create GitHub repo
mybb_workspace_github_create(
    codename="my_plugin",
    repo_visibility="private"
)

# Commit changes
mybb_workspace_git_commit(
    codename="my_plugin",
    message="Add user badge feature"
)

# Push to remote
mybb_workspace_git_push(codename="my_plugin")
```

---

## 8. Lessons Learned

### 8.1 Critical Discoveries

1. **Templateset Property**: Without the `templateset` property in theme properties, custom templates don't load. This was a significant debugging effort.

2. **Manifest Self-Reference**: Early implementations accidentally tracked the manifest file itself, causing infinite sync loops. Solution: `WORKSPACE_ONLY_PREFIXES` tuple.

3. **PHP Serialization Types**: MyBB's PHP serialized properties are type-sensitive. Integer `i:13` vs string `s:2:"13"` matters.

4. **Protected Caches**: The `version` and `internal_settings` caches must never be cleared—they contain MyBB's version code and encryption keys.

5. **Attachedto Field**: Stylesheet `attachedto` field controls which pages load the CSS. Empty string means "all pages."

### 8.2 Design Decisions

1. **Workspace Isolation**: Keeps development separate from production, enabling safe experimentation

2. **MCP-Only Database Access**: Prevents race conditions and ensures cache invalidation

3. **Hash-Based Detection**: Scales to thousands of files without performance degradation

4. **Group-Organized Templates**: Mirrors MyBB Admin CP structure for intuitive navigation

5. **Bidirectional Sync**: Enables both greenfield development and modification of existing themes

---

## 9. Future Directions

### 9.1 Planned Enhancements

- **Conflict Resolution**: Detect and resolve conflicts when both workspace and DB change
- **Version Control Integration**: Automatic commits on sync operations
- **Theme Inheritance**: Proper parent theme support with override tracking
- **Plugin Dependencies**: Declare and validate plugin dependencies
- **Hot Reload**: Automatic sync on file save with watcher integration

### 9.2 Potential Extensions

- **Theme Marketplace Integration**: Direct publish to MyBB Mods
- **Automated Testing**: PHPUnit integration for plugin testing
- **Documentation Generation**: Auto-generate plugin documentation from code
- **Migration Tools**: Upgrade plugins between MyBB versions

---

## 10. Conclusion

MyBB Playground's workspace management system transforms MyBB development from a manual, error-prone process into a structured, AI-assisted workflow. By separating development from deployment, tracking changes with manifests, and providing comprehensive MCP tools, the system enables rapid iteration while maintaining reliability.

The hash-based synchronization system is particularly significant—it solves the fundamental problem of efficiently syncing large template sets, making theme development practical at scale.

As AI-assisted development becomes more prevalent, infrastructure like MyBB Playground demonstrates how legacy systems can be adapted for modern tooling without requiring changes to the underlying platform.

---

## Appendix A: Tool Reference

See [MCP Tools Index](wiki/mcp_tools/index.md) for complete tool documentation.

## Appendix B: Configuration

See [CLAUDE.md](../CLAUDE.md) for development configuration and workflows.

---

*© 2026 Corta Labs. MIT License.*
