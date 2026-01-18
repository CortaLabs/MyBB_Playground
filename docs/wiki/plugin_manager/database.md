# Database Schema

**Module:** `plugin_manager/database.py` (460 lines)
**Class:** `ProjectDatabase`
**Database:** `plugin_manager/projects.db` (SQLite)

## Overview

The ProjectDatabase manages a SQLite database for tracking plugin/theme projects, deployment manifests, and action history. All project metadata, file deployment tracking, and lifecycle events are stored here.

## ProjectDatabase Class

### Initialization

```python
from plugin_manager.database import ProjectDatabase

db = ProjectDatabase(db_path: str | Path)
```

**Database Path:** `plugin_manager/projects.db` (default)

**Auto-initialization:** Tables created on first connection if not exist

**Connection:** SQLite connection with row factory for dict-like access

### Database Schema

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

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER | Primary key (auto-increment) |
| `codename` | TEXT | Unique plugin/theme codename (lowercase, underscores) |
| `display_name` | TEXT | Human-readable name |
| `type` | TEXT | Project type: 'plugin' or 'theme' |
| `visibility` | TEXT | Workspace visibility: 'public' or 'private' |
| `status` | TEXT | Lifecycle status (see below) |
| `version` | TEXT | Semantic version (e.g., "1.0.0") |
| `description` | TEXT | Project description |
| `author` | TEXT | Author name |
| `mybb_compatibility` | TEXT | MyBB version compatibility (e.g., "18*") |
| `workspace_path` | TEXT | Absolute path to workspace directory |
| `deployed_files` | TEXT | Deployment manifest JSON (see below) |
| `created_at` | TEXT | ISO 8601 timestamp of creation |
| `updated_at` | TEXT | ISO 8601 timestamp of last update |
| `installed_at` | TEXT | ISO 8601 timestamp of installation (NULL if not installed) |

**Status Values:**
- `development` — Created in workspace, not deployed
- `testing` — Under testing (custom status)
- `installed` — Files deployed to TestForum
- `active` — PHP lifecycle activated
- `archived` — No longer in use

**Indexes:**
```sql
CREATE INDEX idx_projects_type ON projects(type);
CREATE INDEX idx_projects_visibility ON projects(visibility);
```

---

#### deployed_files Column (Deployment Manifest)

Stores deployment manifest as JSON string:

```json
{
  "deployed_at": "2026-01-18T08:15:00.000000",
  "files": [
    {
      "path": "/absolute/path/in/TestForum",
      "source": "/absolute/path/in/workspace",
      "size": 2048,
      "mtime": "2026-01-18T08:15:00.000000",
      "checksum": "md5hashvalue",
      "deployed_at": "2026-01-18T08:15:00.000000"
    }
  ],
  "directories": ["/path/to/created/dir"],
  "backups": ["/path/to/backup"],
  "file_count": 5,
  "dir_count": 3
}
```

**Backward Compatibility:** Supports legacy formats:
- Simple list: `["file1", "file2"]`
- Old dict format: `{"files": ["file1"], "dirs": ["dir1"]}`

---

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

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER | Primary key (auto-increment) |
| `project_id` | INTEGER | Foreign key to projects.id |
| `action` | TEXT | Action type (see below) |
| `details` | TEXT | Optional JSON or text details |
| `timestamp` | TEXT | ISO 8601 timestamp of action |

**Action Types:**
- `created` — Project created in workspace
- `updated` — Project metadata updated
- `installed` — Files deployed to TestForum
- `activated` — PHP lifecycle activated
- `deactivated` — PHP lifecycle deactivated
- `uninstalled` — Files removed from TestForum

**Indexes:**
```sql
CREATE INDEX idx_history_project_id ON history(project_id);
```

**Cascade Delete:** When project deleted, all history entries deleted automatically.

---

## Deployment Manifest Management

### set_deployed_manifest()

```python
def set_deployed_manifest(
    self,
    codename: str,
    files: List[Dict[str, Any]],
    directories: List[str],
    backups: Optional[List[str]] = None
) -> bool:
    """Store the deployment manifest for a project with full metadata.

    Args:
        codename: Plugin/theme codename
        files: List of file metadata dictionaries
        directories: List of created directory paths
        backups: Optional list of backup file paths

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If project not found
    """
```

**File Metadata Format:**
```python
{
    "path": "/absolute/path",
    "source": "/workspace/path",
    "size": 2048,
    "mtime": "2026-01-18T08:15:00.000000",
    "checksum": "md5hashvalue",
    "deployed_at": "2026-01-18T08:15:00.000000"
}
```

**Side Effects:**
- Updates `updated_at` timestamp
- Creates history entry with action='installed'

**Example:**
```python
db.set_deployed_manifest(
    codename="my_plugin",
    files=[
        {
            "path": "/path/to/TestForum/inc/plugins/my_plugin.php",
            "source": "/workspace/my_plugin/inc/plugins/my_plugin.php",
            "size": 2048,
            "mtime": "2026-01-18T08:15:00.000000",
            "checksum": "abc123",
            "deployed_at": "2026-01-18T08:15:00.000000"
        }
    ],
    directories=["/path/to/TestForum/inc/plugins"],
    backups=[]
)
```

---

### get_deployed_manifest()

```python
def get_deployed_manifest(self, codename: str) -> Dict[str, Any]:
    """Get the deployment manifest for a project.

    Args:
        codename: Plugin/theme codename

    Returns:
        Deployment manifest dictionary or empty dict if not deployed

    Raises:
        ValueError: If project not found
    """
```

**Returns:**
```python
{
    "deployed_at": "2026-01-18T08:15:00.000000",
    "files": [...],
    "directories": [...],
    "backups": [...],
    "file_count": 5,
    "dir_count": 3
}
```

**Backward Compatibility:** Converts legacy formats to current format automatically.

**Example:**
```python
manifest = db.get_deployed_manifest("my_plugin")
if manifest:
    print(f"Deployed {manifest['file_count']} files")
```

---

### clear_deployed_manifest()

```python
def clear_deployed_manifest(self, codename: str) -> bool:
    """Clear the deployment manifest for a project.

    Args:
        codename: Plugin/theme codename

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If project not found
    """
```

**Side Effects:**
- Sets `deployed_files` to NULL
- Updates `updated_at` timestamp
- Creates history entry with action='uninstalled'

**Example:**
```python
db.clear_deployed_manifest("my_plugin")
```

---

## Project Management

### add_project()

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
    """Insert a new project.

    Args:
        codename: Unique plugin/theme codename
        display_name: Human-readable name
        workspace_path: Absolute path to workspace
        type: 'plugin' or 'theme'
        visibility: 'public' or 'private'
        status: Lifecycle status
        version: Semantic version string
        description: Optional description
        author: Optional author name
        mybb_compatibility: MyBB version string

    Returns:
        Project ID (primary key)

    Raises:
        sqlite3.IntegrityError: If codename already exists
    """
```

**Side Effects:** Creates history entry with action='created'

**Example:**
```python
project_id = db.add_project(
    codename="my_plugin",
    display_name="My Plugin",
    workspace_path="/path/to/workspace",
    author="Developer",
    description="Plugin description"
)
```

---

### get_project()

```python
def get_project(self, codename: str) -> Optional[Dict[str, Any]]:
    """Retrieve project by codename.

    Args:
        codename: Plugin/theme codename

    Returns:
        Project dictionary or None if not found
    """
```

**Returns:**
```python
{
    "id": 1,
    "codename": "my_plugin",
    "display_name": "My Plugin",
    "type": "plugin",
    "visibility": "public",
    "status": "development",
    "version": "1.0.0",
    "description": "...",
    "author": "Developer",
    "mybb_compatibility": "18*",
    "workspace_path": "/path/to/workspace",
    "deployed_files": None,
    "created_at": "2026-01-18 08:00:00",
    "updated_at": "2026-01-18 08:00:00",
    "installed_at": None
}
```

**Example:**
```python
project = db.get_project("my_plugin")
if project:
    print(f"Status: {project['status']}")
```

---

### update_project()

```python
def update_project(self, codename: str, **kwargs) -> bool:
    """Update project fields.

    Args:
        codename: Plugin/theme codename
        **kwargs: Fields to update (display_name, version, status, etc.)

    Returns:
        True if successful, False if project not found

    Raises:
        ValueError: If invalid field provided
    """
```

**Valid Fields:** Any column except `id`, `codename`, `created_at`

**Side Effects:**
- Updates `updated_at` timestamp automatically
- Creates history entry with action='updated'

**Example:**
```python
db.update_project(
    codename="my_plugin",
    status="active",
    version="1.1.0"
)
```

---

### delete_project()

```python
def delete_project(self, codename: str) -> bool:
    """Delete a project.

    Args:
        codename: Plugin/theme codename

    Returns:
        True if deleted, False if not found
    """
```

**Side Effects:** All history entries cascade deleted automatically

**Warning:** Does NOT remove files from workspace or TestForum. Use PluginManager methods for complete cleanup.

**Example:**
```python
db.delete_project("old_plugin")
```

---

### list_projects()

```python
def list_projects(
    self,
    type: Optional[str] = None,
    visibility: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List projects with optional filters.

    Args:
        type: Filter by 'plugin' or 'theme'
        visibility: Filter by 'public' or 'private'
        status: Filter by lifecycle status

    Returns:
        List of project dictionaries
    """
```

**Example:**
```python
# All projects
all_projects = db.list_projects()

# Active plugins only
active_plugins = db.list_projects(type="plugin", status="active")

# Public projects
public_projects = db.list_projects(visibility="public")
```

---

## History Management

### add_history()

```python
def add_history(
    self,
    project_id: int,
    action: str,
    details: Optional[str] = None
) -> int:
    """Log a history entry for a project.

    Args:
        project_id: Project ID (from projects.id)
        action: Action type ('created', 'updated', 'installed', etc.)
        details: Optional JSON or text details

    Returns:
        History entry ID (primary key)

    Raises:
        ValueError: If project_id not found
    """
```

**Example:**
```python
db.add_history(
    project_id=1,
    action="activated",
    details='{"force": false, "success": true}'
)
```

---

### get_history()

```python
def get_history(
    self,
    project_id: Optional[int] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get history entries for a project.

    Args:
        project_id: Optional filter by project ID (None = all projects)
        limit: Maximum entries to return

    Returns:
        List of history entry dictionaries (newest first)
    """
```

**Returns:**
```python
[
    {
        "id": 5,
        "project_id": 1,
        "action": "activated",
        "details": '{"force": false, "success": true}',
        "timestamp": "2026-01-18 08:15:00"
    },
    {
        "id": 4,
        "project_id": 1,
        "action": "installed",
        "details": None,
        "timestamp": "2026-01-18 08:14:00"
    }
]
```

**Example:**
```python
# Get history for specific project
project = db.get_project("my_plugin")
history = db.get_history(project_id=project["id"], limit=10)

for entry in history:
    print(f"{entry['timestamp']}: {entry['action']}")
```

---

## Query Methods

### Additional Query Helpers

#### get_project_by_id()

```python
def get_project_by_id(self, project_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve project by ID.

    Args:
        project_id: Project ID

    Returns:
        Project dictionary or None if not found
    """
```

#### get_installed_projects()

```python
def get_installed_projects(self) -> List[Dict[str, Any]]:
    """Get all projects with deployed_files not NULL.

    Returns:
        List of installed project dictionaries
    """
```

**Example:**
```python
installed = db.get_installed_projects()
print(f"Found {len(installed)} installed projects")
```

#### get_active_projects()

```python
def get_active_projects(self) -> List[Dict[str, Any]]:
    """Get all projects with status='active'.

    Returns:
        List of active project dictionaries
    """
```

---

## Usage Examples

### Complete Project Lifecycle

```python
from plugin_manager.database import ProjectDatabase

db = ProjectDatabase("plugin_manager/projects.db")

# 1. Create project
project_id = db.add_project(
    codename="my_plugin",
    display_name="My Plugin",
    workspace_path="/workspace/my_plugin",
    author="Developer"
)

# 2. Update status after installation
db.update_project("my_plugin", status="installed")

# 3. Store deployment manifest
db.set_deployed_manifest(
    codename="my_plugin",
    files=[...],
    directories=[...]
)

# 4. Update status after activation
db.update_project("my_plugin", status="active", installed_at="2026-01-18T08:15:00")

# 5. View history
project = db.get_project("my_plugin")
history = db.get_history(project_id=project["id"])
for entry in history:
    print(f"{entry['action']} at {entry['timestamp']}")

# 6. Clean up
db.clear_deployed_manifest("my_plugin")
db.update_project("my_plugin", status="development")
```

### Querying Projects

```python
# All plugins
plugins = db.list_projects(type="plugin")

# Active public plugins
active_public = db.list_projects(type="plugin", visibility="public", status="active")

# Check if specific project exists
project = db.get_project("my_plugin")
if project:
    print(f"Found: {project['display_name']}")
```

### Deployment Manifest Workflow

```python
# After deployment
db.set_deployed_manifest(
    codename="my_plugin",
    files=[
        {
            "path": "/TestForum/inc/plugins/my_plugin.php",
            "source": "/workspace/inc/plugins/my_plugin.php",
            "size": 2048,
            "checksum": "abc123",
            "mtime": "2026-01-18T08:15:00",
            "deployed_at": "2026-01-18T08:15:00"
        }
    ],
    directories=["/TestForum/inc/plugins"]
)

# Retrieve for uninstallation
manifest = db.get_deployed_manifest("my_plugin")
for file_info in manifest["files"]:
    # Remove file using path
    os.remove(file_info["path"])

# Clear after cleanup
db.clear_deployed_manifest("my_plugin")
```

---

## Best Practices

### Project Management

✅ **DO:**
- Use codename as primary identifier (unique, immutable)
- Update status after each lifecycle transition
- Store complete workspace_path (absolute)
- Keep version up to date with meta.json

❌ **DON'T:**
- Change codename after creation
- Skip status updates
- Store relative paths
- Manually edit database with SQL

### Deployment Manifest

✅ **DO:**
- Store complete file metadata (checksums, timestamps)
- Include all deployed files and directories
- Clear manifest after uninstallation
- Use get_deployed_manifest() before removal

❌ **DON'T:**
- Store manifest without checksums
- Skip directories or backups
- Delete manifest before cleanup
- Modify manifest JSON manually

### History Tracking

✅ **DO:**
- Log all lifecycle transitions
- Include details for debugging
- Query history for audit trail
- Limit history queries with reasonable limit

❌ **DON'T:**
- Skip history creation
- Store sensitive data in details
- Query entire history without limit
- Delete history entries manually

### Database Integrity

✅ **DO:**
- Let database auto-generate IDs
- Use foreign key constraints
- Trust cascade deletes
- Validate data before insertion

❌ **DON'T:**
- Manually set project IDs
- Bypass foreign key checks
- Delete history without deleting project
- Insert invalid data

---

## Related Documentation

- [Deployment System](deployment.md) — Uses set_deployed_manifest() and get_deployed_manifest()
- [Lifecycle Management](lifecycle.md) — Updates status after PHP operations
- [Workspace Management](workspace.md) — workspace_path references workspace directories
- [Plugin Manager Index](index.md) — System overview

---

## Database Utilities

### Backup Database

```python
import shutil

shutil.copy("plugin_manager/projects.db", "plugin_manager/projects.db.backup")
```

### Query Raw SQL (Advanced)

```python
db = ProjectDatabase("plugin_manager/projects.db")

# Execute raw query
cursor = db.conn.execute("SELECT * FROM projects WHERE status = ?", ("active",))
results = cursor.fetchall()
```

**Warning:** Use ProjectDatabase methods when possible. Raw SQL bypasses validation and side effects.

### Reset Database

```python
import os

# Delete database (recreates on next connection)
os.remove("plugin_manager/projects.db")
db = ProjectDatabase("plugin_manager/projects.db")
# Tables auto-created
```
