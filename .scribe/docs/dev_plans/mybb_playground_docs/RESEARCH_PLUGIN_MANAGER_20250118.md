# Plugin Manager System - Complete Technical Documentation

**Research Date:** 2026-01-18
**Scope:** plugin_manager/ directory analysis
**Status:** Complete
**Confidence:** 0.95

## Executive Summary

The Plugin Manager is a comprehensive system for managing MyBB plugin and theme development, installation, and lifecycle management. It provides:

- **Workspace Management** - Directory structure mirroring MyBB's layout for simple overlay installation
- **Project Database** - SQLite database tracking all projects, deployment manifests, and history
- **File Deployment** - Intelligent file copying with backup, checksum tracking, and complete cleanup on uninstall
- **PHP Lifecycle Bridge** - Subprocess execution of MyBB plugin lifecycle functions (_install, _activate, _deactivate, _uninstall)
- **Configuration Management** - Flexible configuration with sensible defaults and legacy format support
- **Schema Validation** - meta.json validation using JSON Schema for both plugins and themes

---

## 1. Core Components Architecture

### 1.1 Module Dependency Graph

```
plugin_manager/
├── manager.py              # Main PluginManager orchestrator
│   ├── depends: config, database, workspace, installer, schema, lifecycle
│   └── exports: PluginManager class (25 public methods)
├── workspace.py            # Workspace directory management
│   ├── classes: PluginWorkspace, ThemeWorkspace
│   └── depends: schema
├── installer.py            # File deployment and tracking
│   ├── classes: PluginInstaller, ThemeInstaller
│   └── depends: config, database, workspace
├── database.py             # SQLite project tracking
│   ├── class: ProjectDatabase
│   └── handles: projects table, history table, deployed_files manifest
├── lifecycle.py            # PHP bridge execution
│   ├── classes: PluginLifecycle, BridgeResult
│   └── executes: subprocess calls to mcp_bridge.php
├── config.py               # Configuration loading
│   ├── class: Config
│   └── handles: workspace paths, mybb_root, database paths
├── schema.py               # meta.json validation
│   └── functions: validate_meta, create_default_meta, load_meta, save_meta
└── mcp_client.py           # MCP tool integration (external)
```

---

## 2. PluginManager API (manager.py)

**File:** `/home/austin/projects/MyBB_Playground/plugin_manager/manager.py` (1469 lines)
**Class:** `PluginManager` (lines 210-1469)

### 2.1 Initialization

```python
def __init__(self, config: Optional[Config] = None):
    """Initialize plugin manager.

    Args:
        config: Optional Config object (creates default if None)
    """
```

**Behavior:**
- Creates or uses provided Config instance
- Initializes ProjectDatabase
- Creates PluginWorkspace and ThemeWorkspace instances

---

### 2.2 Plugin Creation

```python
def create_plugin(
    self,
    codename: str,
    display_name: str,
    description: str = "",
    author: Optional[str] = None,
    version: str = "1.0.0",
    visibility: str = "public",
    hooks: Optional[List[Dict[str, str]]] = None,
    settings: Optional[List[Dict[str, Any]]] = None,
    has_templates: bool = False,
    has_database: bool = False,
    mybb_compatibility: str = "18*"
) -> Dict[str, Any]:
    """Create a new plugin with full workspace and registration."""
```

**Returns:**
```json
{
  "success": true,
  "message": "Plugin '{display_name}' created successfully",
  "workspace_path": "/path/to/workspace",
  "project_id": 1,
  "codename": "my_plugin",
  "files_created": [
    "/path/to/inc/plugins/my_plugin.php",
    "/path/to/inc/languages/english/my_plugin.lang.php",
    "/path/to/README.md",
    "/path/to/meta.json"
  ],
  "next_steps": ["Edit PHP code...", "Add language strings...", "Use 'install' workflow...", "Activate plugin..."]
}
```

**Workflow:**
1. Creates workspace directory structure
2. Generates meta.json from provided parameters
3. Scaffolds PHP file with hook registrations
4. Creates language file template
5. Generates README.md
6. Registers in database with history entry

**Key Parameters:**
- `hooks`: List of hook dicts with 'name' key - converted to handler objects with priority=10
- `settings`: List of setting dicts with 'name', 'title', 'type'
- `has_templates`: Enables template caching boilerplate in PHP
- `has_database`: Enables database table creation boilerplate

---

### 2.3 Theme Creation

```python
def create_theme(
    self,
    codename: str,
    display_name: str,
    description: str = "",
    author: Optional[str] = None,
    version: str = "1.0.0",
    visibility: str = "public",
    parent_theme: Optional[str] = None,
    color_scheme: Optional[Dict[str, str]] = None,
    stylesheets: Optional[List[str]] = None,
    template_overrides: Optional[List[str]] = None,
    mybb_compatibility: str = "18*"
) -> Dict[str, Any]:
    """Create a new theme with full workspace and registration."""
```

**Returns:** Similar structure to create_plugin with stylesheet files instead of PHP

**Workflow:**
1. Validates parent theme if specified
2. Creates workspace directory structure (stylesheets/, templates/, images/)
3. Generates meta.json with theme-specific fields
4. Creates CSS stylesheet files
5. Generates README.md
6. Registers in database

---

### 2.4 Installation Methods

```python
def install_plugin(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
    """Deploy plugin files to TestForum."""

def uninstall_plugin(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
    """Remove plugin files from TestForum."""

def install_theme(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
    """Deploy theme files to TestForum."""

def uninstall_theme(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
    """Remove theme files from TestForum."""
```

These delegate to PluginInstaller and ThemeInstaller classes.

---

### 2.5 Full Lifecycle Methods

```python
def activate_full(
    self,
    codename: str,
    visibility: Optional[str] = None,
    force: bool = False
) -> Dict[str, Any]:
    """Full plugin activation: deploy files + execute PHP lifecycle."""
```

**Steps:**
1. Deploys plugin files from workspace to TestForum
2. Executes PHP _install() function (if not installed)
3. Executes PHP _activate() function via PHP bridge
4. Updates MyBB plugin cache
5. Updates database status to "active"

**Returns:**
```json
{
  "success": true,
  "codename": "my_plugin",
  "files_deployed": [...],
  "workspace_path": "...",
  "file_count": 5,
  "dir_count": 3,
  "total_size": 8192,
  "deployed_at": "2026-01-18T08:15:00.000000",
  "php_lifecycle": {
    "success": true,
    "actions_taken": ["install", "activate"],
    "error": null
  },
  "warnings": []
}
```

```python
def deactivate_full(
    self,
    codename: str,
    uninstall: bool = False,
    remove_files: bool = False,
    visibility: Optional[str] = None
) -> Dict[str, Any]:
    """Full plugin deactivation: execute PHP lifecycle + optionally remove files."""
```

**Steps:**
1. Executes PHP _deactivate() function
2. Optionally executes PHP _uninstall() function
3. Optionally removes plugin files from TestForum
4. Updates database status

---

### 2.6 Query Methods

```python
def get_project(self, codename: str) -> Optional[Dict[str, Any]]:
    """Get project by codename from database."""

def list_projects(
    self,
    type: Optional[str] = None,
    visibility: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List projects with optional filters."""

def get_installed_plugins(self) -> List[str]:
    """List plugins currently installed in TestForum."""
```

---

### 2.7 Internal Scaffold Methods

```python
def _scaffold_plugin_php(
    self,
    codename: str,
    plugin_name: str,
    description: str,
    author: str,
    version: str,
    hooks: List[str],
    has_settings: bool,
    has_templates: bool,
    has_database: bool,
    compatibility: str
) -> str:
    """Generate PHP scaffold for plugin."""
```

Generates PHP code with:
- Hook registrations
- Hook handler functions with CSRF verification
- Template caching boilerplate (if has_templates)
- Settings group creation (if has_settings)
- Database table creation boilerplate (if has_database)

```python
def _generate_plugin_readme(
    self,
    codename: str,
    display_name: str,
    description: str,
    author: str,
    version: str,
    visibility: str,
    compatibility: str,
    workspace_path: str,
    has_templates: bool
) -> str:
    """Generate README.md for plugin."""

def _generate_theme_readme(
    self,
    codename: str,
    display_name: str,
    description: str,
    author: str,
    version: str,
    visibility: str,
    compatibility: str,
    parent_theme: Optional[str],
    stylesheets: List[str],
    workspace_path: str
) -> str:
    """Generate README.md for theme."""
```

---

## 3. File Deployment System (installer.py)

**File:** `/home/austin/projects/MyBB_Playground/plugin_manager/installer.py` (674 lines)

### 3.1 PluginInstaller Class

```python
class PluginInstaller:
    """Deploys plugins from workspace to TestForum.

    Tracks all deployed files and directories for complete cleanup on uninstall.
    Backups are stored OUTSIDE TestForum in the workspace/backups/ directory.
    """
```

**Initialization:**
```python
def __init__(
    self,
    config: Config,
    db: ProjectDatabase,
    plugin_workspace: PluginWorkspace
):
```

**Key Properties:**
- `self.backup_root = config.repo_root / "plugin_manager" / "backups"`
- Backups stored OUTSIDE TestForum (safety)

### 3.2 Plugin Installation

```python
def install_plugin(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
    """Deploy plugin to TestForum using directory overlay."""
```

**Workspace Structure:**
```
plugins/{visibility}/{codename}/
├── inc/
│   ├── plugins/                    # Plugin PHP files
│   └── languages/
│       └── english/                # Language files
├── jscripts/                       # Optional JavaScript
├── images/                         # Optional images
└── meta.json
```

**Installation Process:**
1. Loads plugin metadata from workspace
2. Overlays `inc/` directory to `TestForum/inc/`
3. Overlays `jscripts/` if exists (optional)
4. Overlays `images/` if exists (optional)
5. Verifies plugin file exists in destination
6. Stores complete deployment manifest in database

**File Tracking Metadata:**
Each deployed file includes:
```json
{
  "path": "/absolute/path/in/TestForum",
  "source": "/absolute/path/in/workspace",
  "size": 2048,
  "mtime": "2026-01-18T08:15:00.000000",
  "checksum": "md5hashvalue",
  "deployed_at": "2026-01-18T08:15:00.000000"
}
```

**Returns:**
```json
{
  "success": true,
  "plugin": "my_plugin",
  "workspace_path": "/path/to/workspace",
  "deployed_at": "2026-01-18T08:15:00.000000",
  "files_deployed": [
    {"path": "inc/plugins/my_plugin.php", "size": 2048, "checksum": "..."},
    {"path": "inc/languages/english/my_plugin.lang.php", "size": 512, "checksum": "..."}
  ],
  "dirs_created": ["inc/plugins", "inc/languages/english"],
  "backups_created": [],
  "total_size": 2560,
  "file_count": 2,
  "dir_count": 2,
  "warnings": []
}
```

### 3.3 Directory Overlay System

```python
def _overlay_directory(
    self,
    src_dir: Path,
    dest_dir: Path,
    codename: str
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Overlay source directory to destination, creating backups."""
```

**Behavior:**
- Copies files from source to destination
- Creates backups of existing files (outside TestForum)
- Tracks new directories created
- Returns (files_metadata, directories_created, backups)

### 3.4 Plugin Uninstallation

```python
def uninstall_plugin(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
    """Remove plugin files from TestForum using deployment manifest."""
```

**Process:**
1. Retrieves deployment manifest from database
2. Restores files from backups (if exist)
3. Removes files deployed by us
4. Removes directories we created
5. Clears deployment manifest

**Returns:**
```json
{
  "success": true,
  "plugin": "my_plugin",
  "files_removed": ["/path/to/inc/plugins/my_plugin.php", ...],
  "dirs_removed": ["/path/to/inc/plugins", ...],
  "restored_from_backup": ["/path/to/file", ...],
  "warnings": []
}
```

### 3.5 ThemeInstaller Class

Same interface as PluginInstaller but for themes:
- Overlays `stylesheets/`, `templates/`, `images/` directories
- Theme-specific deployment tracking

---

## 4. Database Schema (database.py)

**File:** `/home/austin/projects/MyBB_Playground/plugin_manager/database.py` (460 lines)

### 4.1 ProjectDatabase Class

```python
class ProjectDatabase:
    """Manages SQLite database for tracking plugin/theme projects."""

    def __init__(self, db_path: str | Path):
        """Initialize database connection."""
```

**Database Path:** `plugin_manager/projects.db`
**Auto-initialization:** Tables created on first connection if not exist

### 4.2 Database Schema

#### Projects Table

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codename TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'plugin',
    visibility TEXT NOT NULL DEFAULT 'public',
    status TEXT NOT NULL DEFAULT 'development',
    version TEXT NOT NULL DEFAULT '1.0.0',
    description TEXT,
    author TEXT,
    mybb_compatibility TEXT DEFAULT '18*',
    workspace_path TEXT NOT NULL,
    deployed_files TEXT DEFAULT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    installed_at TEXT DEFAULT NULL
);
```

**Status Values:** 'development', 'testing', 'installed', 'active', 'archived'

**deployed_files Column:** Stores deployment manifest as JSON:
```json
{
  "deployed_at": "2026-01-18T08:15:00.000000",
  "files": [
    {
      "path": "/absolute/path",
      "source": "/workspace/path",
      "size": 2048,
      "mtime": "2026-01-18T08:15:00.000000",
      "checksum": "md5hashvalue",
      "deployed_at": "2026-01-18T08:15:00.000000"
    }
  ],
  "directories": ["/path/to/created/dir", ...],
  "backups": ["/path/to/backup", ...],
  "file_count": 5,
  "dir_count": 3
}
```

#### History Table

```sql
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

**Action Types:** 'created', 'updated', 'installed', 'activated', 'deactivated', 'uninstalled'

#### Indexes

```sql
CREATE INDEX idx_projects_type ON projects(type);
CREATE INDEX idx_projects_visibility ON projects(visibility);
CREATE INDEX idx_history_project_id ON history(project_id);
```

---

### 4.3 Key Methods

#### Deployment Manifest Management

```python
def set_deployed_manifest(
    self,
    codename: str,
    files: List[Dict[str, Any]],
    directories: List[str],
    backups: Optional[List[str]] = None
) -> bool:
    """Store the deployment manifest for a project with full metadata."""
```

```python
def get_deployed_manifest(self, codename: str) -> Dict[str, Any]:
    """Get the deployment manifest for a project."""
```

Returns with backward compatibility for legacy formats (simple list, old dict format).

```python
def clear_deployed_manifest(self, codename: str) -> bool:
    """Clear the deployment manifest for a project."""
```

#### Project Management

```python
def add_project(
    self,
    codename: str,
    display_name: str,
    workspace_path: str,
    type: str = "plugin",
    visibility: str = "public",
    status: str = "development",
    version: str = "1.0.0",
    description: Optional[str] = None,
    author: Optional[str] = None,
    mybb_compatibility: str = "18*"
) -> int:
    """Insert a new project."""
```

**Side Effects:** Automatically creates history entry with action='created'

```python
def get_project(self, codename: str) -> Optional[Dict[str, Any]]:
    """Retrieve project by codename."""

def update_project(self, codename: str, **kwargs) -> bool:
    """Update project fields."""
```

**Side Effects:** Updates `updated_at` timestamp and creates history entry

```python
def delete_project(self, codename: str) -> bool:
    """Delete a project."""

def list_projects(
    self,
    type: Optional[str] = None,
    visibility: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List projects with optional filters."""
```

#### History Management

```python
def add_history(
    self,
    project_id: int,
    action: str,
    details: Optional[str] = None
) -> int:
    """Log a history entry for a project."""

def get_history(
    self,
    project_id: Optional[int] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get history entries for a project."""
```

---

## 5. Workspace Structure (workspace.py)

**File:** `/home/austin/projects/MyBB_Playground/plugin_manager/workspace.py` (561 lines)

### 5.1 PluginWorkspace Class

**Root Path:** `plugin_manager/plugins`

**Directory Structure:**
```
plugins/
├── public/
│   ├── plugin_one/
│   │   ├── inc/
│   │   │   ├── plugins/
│   │   │   │   └── plugin_one.php
│   │   │   └── languages/
│   │   │       └── english/
│   │   │           └── plugin_one.lang.php
│   │   ├── jscripts/
│   │   ├── images/
│   │   ├── meta.json
│   │   └── README.md
│   └── plugin_two/
│       └── ...
└── private/
    └── internal_plugin/
        └── ...
```

**Visibility:** 'public' or 'private' (affects workspace location)

#### Methods

```python
def create_workspace(self, codename: str, visibility: str = "public") -> Path:
    """Create a new plugin workspace directory structure."""
```

Creates:
- `inc/plugins/`
- `inc/languages/english/`
- `jscripts/`
- `images/`

```python
def get_workspace_path(self, codename: str, visibility: Optional[str] = None) -> Optional[Path]:
    """Find plugin workspace path by codename."""
```

If visibility not specified, searches both public and private.

```python
def read_meta(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
    """Read and parse meta.json from plugin workspace."""

def write_meta(self, codename: str, meta: Dict[str, Any], visibility: Optional[str] = None) -> None:
    """Write meta.json to plugin workspace."""
```

Validates before writing using `validate_meta()`.

```python
def validate_workspace(self, codename: str, visibility: Optional[str] = None) -> List[str]:
    """Validate plugin workspace structure and contents."""
```

Checks:
- Required directories (inc/plugins, inc/languages/english)
- meta.json exists and is valid
- PHP files exist in inc/plugins/

```python
def list_plugins(self, visibility: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all plugins in workspace."""
```

Returns list with codename, visibility, workspace_path, has_meta, display_name, version, type.

---

### 5.2 ThemeWorkspace Class

**Root Path:** `plugin_manager/themes`

**Directory Structure:**
```
themes/
├── public/
│   ├── theme_one/
│   │   ├── stylesheets/
│   │   │   └── global.css
│   │   ├── templates/
│   │   ├── images/
│   │   ├── meta.json
│   │   └── README.md
│   └── theme_two/
│       └── ...
└── private/
    └── ...
```

**Methods:** Same interface as PluginWorkspace

#### Additional Method

```python
def scaffold_stylesheet(self, name: str = 'global.css', parent_theme: Optional[str] = None) -> str:
    """Generate CSS stylesheet content with optional parent theme inheritance."""
```

If parent_theme specified, generates import statement at top.

---

## 6. PHP Lifecycle Bridge (lifecycle.py)

**File:** `/home/austin/projects/MyBB_Playground/plugin_manager/lifecycle.py` (283 lines)

### 6.1 BridgeResult Class

```python
@dataclass
class BridgeResult:
    """Result from a bridge operation."""
    success: bool
    action: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: Optional[str] = None
```

**Creation Methods:**
```python
@classmethod
def from_json(cls, action: str, json_data: Dict[str, Any]) -> 'BridgeResult':
    """Create BridgeResult from JSON response."""

@classmethod
def from_error(cls, action: str, error: str) -> 'BridgeResult':
    """Create error BridgeResult."""
```

---

### 6.2 PluginLifecycle Class

Executes MyBB plugin lifecycle functions via `mcp_bridge.php` subprocess.

```python
class PluginLifecycle:
    """Execute MyBB plugin lifecycle functions via PHP bridge."""

    def __init__(
        self,
        mybb_root: Path,
        php_binary: str = "php",
        timeout: int = 30
    ):
```

**Bridge Location:** `{mybb_root}/mcp_bridge.php`
**Timeout:** 30 seconds (configurable)

#### Core Methods

```python
def get_status(self, codename: str) -> BridgeResult:
    """Get plugin status and info."""
```

Returns data with:
- `is_installed`: Whether _is_installed() returns true
- `is_active`: Whether plugin is in active cache
- `is_compatible`: Whether compatible with MyBB version
- `info`: Plugin info from _info() function

```python
def activate(self, codename: str, force: bool = False) -> BridgeResult:
    """Activate a plugin (runs _install and _activate if needed)."""
```

Steps:
1. Check compatibility (unless force=True)
2. Run _install() if not installed
3. Run _activate()
4. Update plugins cache

```python
def deactivate(self, codename: str, uninstall: bool = False) -> BridgeResult:
    """Deactivate a plugin (optionally uninstall)."""
```

Steps:
1. Run _deactivate()
2. Run _uninstall() if uninstall=True
3. Update plugins cache

```python
def list_plugins(self) -> BridgeResult:
    """List all plugins with their status."""

def get_mybb_info(self) -> BridgeResult:
    """Get MyBB installation info."""

def read_cache(self, cache_name: str) -> BridgeResult:
    """Read a MyBB cache entry."""

def rebuild_cache(self) -> BridgeResult:
    """Rebuild all MyBB caches."""
```

#### Private Method

```python
def _call_bridge(self, action: str, **kwargs) -> BridgeResult:
    """Execute a bridge action via subprocess."""
```

**Command Format:**
```bash
php {bridge_path} --action={action} --json [--key=value ...]
```

**Error Handling:**
- TimeoutExpired → timeout error
- JSON parsing error → returns raw output as error
- FileNotFoundError → PHP binary not found

---

## 7. Configuration Management (config.py)

**File:** `/home/austin/projects/MyBB_Playground/plugin_manager/config.py` (174 lines)

### 7.1 Default Configuration

```python
DEFAULT_CONFIG = {
    "workspaces": {
        "plugins": "plugin_manager/plugins",
        "themes": "plugin_manager/themes"
    },
    "database_path": "plugin_manager/projects.db",
    "schema_path": "plugin_manager/schema/projects.sql",
    "mybb_root": "TestForum",
    "default_visibility": "public",
    "default_author": "Developer",
    "default_mybb_compatibility": "18*"
}
```

### 7.2 Config Class

```python
class Config:
    """Plugin Manager configuration."""

    def __init__(self, config_path: Optional[str | Path] = None, repo_root: Optional[str | Path] = None):
```

**Configuration Loading:**
1. Looks for `.plugin_manager/config.json` (relative to repo_root)
2. Merges user config with defaults
3. Falls back to defaults if file missing or invalid

### 7.3 Properties

```python
@property
def workspaces(self) -> Dict[str, str]:
    """Get workspaces configuration dict."""
```

Returns `{"plugins": "path/to/plugins", "themes": "path/to/themes"}`

```python
def get_workspace_path(self, project_type: str = "plugin") -> Path:
    """Get absolute path to workspace for a project type."""
```

Example: `Config.get_workspace_path("plugin")` → `/repo_root/plugin_manager/plugins`

```python
@property
def workspace_root(self) -> Path:
    """Get absolute path to plugins workspace root."""
```

Legacy property - equivalent to `get_workspace_path("plugin")`

```python
@property
def database_path(self) -> Path:
    """Get absolute path to database file."""

@property
def schema_path(self) -> Path:
    """Get absolute path to schema file."""

@property
def mybb_root(self) -> Path:
    """Get absolute path to MyBB installation root (TestForum)."""

@property
def default_visibility(self) -> str:
    """Get default visibility for new projects."""

@property
def default_author(self) -> str:
    """Get default author name."""

@property
def default_mybb_compatibility(self) -> str:
    """Get default MyBB compatibility string."""
```

### 7.4 Utility Methods

```python
def save(self) -> None:
    """Save current configuration to file."""

def get_project_path(
    self,
    codename: str,
    visibility: Optional[str] = None,
    project_type: str = "plugin"
) -> Path:
    """Get absolute path to a project workspace."""
```

Example: `get_project_path("my_plugin", "public")` → `/repo_root/plugin_manager/plugins/public/my_plugin`

```python
def __getitem__(self, key: str) -> Any:
    """Dict-like access to config values."""

def __setitem__(self, key: str, value: Any) -> None:
    """Dict-like assignment to config values."""

def __contains__(self, key: str) -> bool:
    """Dict-like membership test."""
```

---

## 8. Schema Validation (schema.py)

**File:** `/home/austin/projects/MyBB_Playground/plugin_manager/schema.py` (498 lines)

### 8.1 JSON Schema (META_SCHEMA)

Comprehensive JSON Schema validation for meta.json supporting both plugins and themes.

**Required Fields:**
```
codename, display_name, version, author
```

**Codename Pattern:** `^[a-z][a-z0-9_]*$` (lowercase, underscores)

**Version Pattern:** `^\d+\.\d+\.\d+$` (semantic versioning)

### 8.2 Plugin-Specific Fields

```json
{
  "hooks": [
    {
      "name": "hook_name",
      "handler": "function_name",
      "priority": 10
    }
  ],
  "settings": [
    {
      "name": "setting_id",
      "title": "Setting Title",
      "type": "text|textarea|yesno|select|radio",
      "description": "...",
      "default": "...",
      "options": "newline-separated"
    }
  ],
  "templates": ["template_name", ...],
  "has_templates": false,
  "has_database": false,
  "files": {
    "plugin": "inc/plugins/{codename}.php",
    "languages": "inc/languages/",
    "jscripts": "jscripts/",
    "images": "images/"
  }
}
```

### 8.3 Theme-Specific Fields

```json
{
  "stylesheets": [
    {
      "name": "global.css",
      "attached_to": ["global"],
      "display_order": 1
    }
  ],
  "template_overrides": ["template_name", ...],
  "parent_theme": "parent_codename",
  "color_scheme": {
    "primary": "#000000",
    "secondary": "#ffffff",
    "background": "#f0f0f0",
    "text": "#333333"
  },
  "files": {
    "stylesheets": "stylesheets/",
    "images": "images/"
  }
}
```

### 8.4 Validation Functions

```python
def validate_meta(meta_dict: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate meta.json data against schema.

    Returns:
        (is_valid, list_of_errors)
    """
```

Validates:
- Required fields present
- Codename pattern (lowercase, underscores)
- Version semantic versioning
- Visibility enum (public/private)
- Hooks array structure
- Settings array structure
- Stylesheets array structure
- Template overrides array

```python
def create_default_meta(
    codename: str,
    display_name: str,
    author: str,
    version: str = "1.0.0",
    description: str = "",
    mybb_compatibility: str = "18*",
    visibility: str = "public",
    project_type: str = "plugin"
) -> Dict[str, Any]:
    """Generate default meta.json structure for plugin or theme."""
```

Returns appropriate structure based on project_type.

```python
def create_default_plugin_meta(...) -> Dict[str, Any]:
    """Generate default plugin meta.json structure (convenience wrapper)."""

def create_default_theme_meta(...) -> Dict[str, Any]:
    """Generate default theme meta.json structure (convenience wrapper)."""
```

### 8.5 File I/O Functions

```python
def load_meta(path: str | Path) -> tuple[Optional[Dict[str, Any]], List[str]]:
    """Load and parse meta.json from file.

    Returns:
        (parsed_dict, list_of_errors)
    """
```

```python
def save_meta(meta_dict: Dict[str, Any], path: str | Path) -> tuple[bool, List[str]]:
    """Save meta.json to file.

    Returns:
        (success, list_of_errors)
    """
```

---

## 9. File Structure Summary

### Root Directories

| Path | Purpose |
|------|---------|
| `plugin_manager/plugins/` | Plugin workspace root |
| `plugin_manager/themes/` | Theme workspace root |
| `plugin_manager/backups/` | Backup storage (outside TestForum) |
| `plugin_manager/data/` | Data files and exports |
| `plugin_manager/schema/` | Database schema files |
| `plugin_manager/.meta/` | Internal metadata |

### Configuration & Database

| File | Purpose |
|------|---------|
| `.plugin_manager/config.json` | User configuration |
| `plugin_manager/projects.db` | SQLite project database |
| `plugin_manager/schema/projects.sql` | Database schema SQL |

---

## 10. Installation Process Walkthrough

### Creating and Installing a Plugin

```python
# 1. Create workspace and register
result = manager.create_plugin(
    codename="my_plugin",
    display_name="My Plugin",
    description="A test plugin",
    author="Dev",
    hooks=["index_start", "global_start"],
    settings=[
        {"name": "enabled", "title": "Enable Plugin", "type": "yesno"}
    ]
)
# Files created: my_plugin.php, my_plugin.lang.php, README.md, meta.json

# 2. Install files to TestForum
install_result = manager.install_plugin("my_plugin")
# Files deployed to TestForum/inc/plugins/ and TestForum/inc/languages/

# 3. Activate plugin (runs PHP lifecycle)
activate_result = manager.activate_full("my_plugin")
# Executes _install() and _activate() via PHP bridge
# Updates MyBB plugin cache
```

### Complete Workflow

```
create_plugin()
  ├── Create workspace directory structure
  ├── Generate meta.json
  ├── Scaffold PHP file with hooks
  ├── Create language file template
  ├── Generate README
  └── Register in database (status: development)

install_plugin()
  ├── Load workspace metadata
  ├── Overlay inc/ to TestForum/inc/
  ├── Overlay jscripts/ (optional)
  ├── Overlay images/ (optional)
  ├── Create file metadata with checksums
  ├── Store deployment manifest in database
  └── Update status: installed

activate_full()
  ├── (Re)deploy files if needed
  ├── Execute PHP _install() via bridge
  ├── Execute PHP _activate() via bridge
  ├── Update plugins cache
  └── Update database status: active
```

---

## 11. Design Patterns & Key Concepts

### 11.1 Workspace-Based Development

The workspace mirrors MyBB's directory layout exactly, enabling simple `cp -r` installation:
- `workspace/inc/` → `TestForum/inc/`
- `workspace/jscripts/` → `TestForum/jscripts/`
- `workspace/images/` → `TestForum/images/`

This design eliminates complex path mapping logic.

### 11.2 Complete Deployment Tracking

Every deployed file is tracked with:
- Absolute path in TestForum
- Source path in workspace
- File size and modification time
- MD5 checksum for integrity verification
- Deployment timestamp

This enables:
- Exact cleanup on uninstall
- Duplicate file detection
- Integrity verification

### 11.3 Backup Strategy

Backups stored OUTSIDE TestForum prevent:
- Accidental deletion of backups
- Sync conflicts
- Performance issues

Backups created during file overlay phase for safe cleanup.

### 11.4 Visibility System

Plugins/themes organized by visibility:
- `public/` - Published or development
- `private/` - Internal or restricted

Enables workspace isolation without filesystem complexity.

### 11.5 PHP Lifecycle Bridge

Subprocess execution of PHP via CLI:
- Proper MyBB bootstrapping
- Uses MyBB's native plugin system
- No reimplementation or workarounds
- Clean error handling

---

## 12. Integration Points

### With MyBB MCP Server

- Uses `mybb_mcp.tools.plugins` patterns for PHP scaffolding
- Compatible with MyBB database operations
- Follows MyBB plugin structure conventions

### With Workspace System

- `PluginManager` orchestrates across workspace, installer, database
- Workspace provides directory structure
- Installer handles file operations
- Database tracks state and deployment

---

## 13. Confidence Assessment

**Overall Confidence: 0.95**

| Component | Confidence | Notes |
|-----------|-----------|-------|
| PluginManager API | 0.98 | Fully documented with examples |
| Workspace Structure | 0.95 | Clear directory layout |
| Database Schema | 0.95 | Full SQL and queries documented |
| File Deployment | 0.98 | Metadata tracking comprehensive |
| Lifecycle Bridge | 0.92 | Subprocess execution with error handling |
| Configuration | 0.98 | Default and custom config patterns clear |
| Schema Validation | 0.95 | JSON Schema with validation rules |

**Uncertainty Areas:**
- Exact PHP bridge protocol details (implementation-specific)
- mcp_bridge.php error handling specifics (not analyzed)
- Performance characteristics under heavy load (not tested)

---

## 14. Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `manager.py` | 1469 | Main orchestrator, plugin/theme creation, lifecycle |
| `workspace.py` | 561 | Directory management for plugins and themes |
| `installer.py` | 674 | File deployment with manifest tracking |
| `database.py` | 460 | Project database and deployment tracking |
| `lifecycle.py` | 283 | PHP bridge subprocess execution |
| `config.py` | 174 | Configuration loading and path resolution |
| `schema.py` | 498 | meta.json validation and generation |

---

## 15. Recommendations for Downstream Use

### For Architects

- Understand workspace-based deployment model before designing extensions
- Consider visibility separation in multi-project scenarios
- Review database schema before adding project tracking features

### For Coders

- Use `PluginManager.create_plugin()` API directly for new plugins
- Don't manually manage workspace directories - use workspace classes
- Always validate meta.json changes using schema validation
- Reference deployment manifest for cleanup operations

### For Integration

- Ensure mcp_bridge.php is properly installed before lifecycle operations
- Consider timeout values for subprocess execution in resource-constrained environments
- Test database migrations for legacy projects with old manifest formats

---

**Research Complete**
