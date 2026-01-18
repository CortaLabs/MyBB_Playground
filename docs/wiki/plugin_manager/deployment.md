# Deployment System

**Module:** `plugin_manager/installer.py` (674 lines)
**Classes:** `PluginInstaller`, `ThemeInstaller`

## Overview

The deployment system handles intelligent file copying from workspace to TestForum with automatic backup, checksum tracking, and complete cleanup on uninstall. All deployed files and directories are tracked in a deployment manifest stored in the project database.

## PluginInstaller Class

### Initialization

```python
from plugin_manager.installer import PluginInstaller

installer = PluginInstaller(
    config: Config,
    db: ProjectDatabase,
    plugin_workspace: PluginWorkspace
)
```

**Key Properties:**
- `self.backup_root = config.repo_root / "plugin_manager" / "backups"`
- Backups stored OUTSIDE TestForum (safety measure)

### Workspace Structure

Before deployment, plugin workspace must follow this structure:

```
plugins/{visibility}/{codename}/
├── inc/
│   ├── plugins/                    # Plugin PHP files (REQUIRED)
│   └── languages/
│       └── english/                # Language files (REQUIRED)
├── jscripts/                       # Optional JavaScript
├── images/                         # Optional images
└── meta.json                       # Project metadata
```

### Installation Process

#### install_plugin()

```python
def install_plugin(
    self,
    codename: str,
    visibility: Optional[str] = None
) -> Dict[str, Any]:
    """Deploy plugin to TestForum using directory overlay.

    Args:
        codename: Plugin codename
        visibility: Workspace visibility ('public' or 'private')

    Returns:
        Installation result dictionary

    Raises:
        ValueError: If workspace not found or invalid
        FileNotFoundError: If required files missing
    """
```

**Installation Steps:**
1. Loads plugin metadata from workspace
2. Overlays `inc/` directory to `TestForum/inc/`
3. Overlays `jscripts/` if exists (optional)
4. Overlays `images/` if exists (optional)
5. Verifies plugin file exists in destination
6. Stores complete deployment manifest in database

**Returns:**
```python
{
    "success": True,
    "plugin": "my_plugin",
    "workspace_path": "/path/to/workspace",
    "deployed_at": "2026-01-18T08:15:00.000000",
    "files_deployed": [
        {
            "path": "inc/plugins/my_plugin.php",
            "size": 2048,
            "checksum": "abc123..."
        },
        {
            "path": "inc/languages/english/my_plugin.lang.php",
            "size": 512,
            "checksum": "def456..."
        }
    ],
    "dirs_created": ["inc/plugins", "inc/languages/english"],
    "backups_created": [],
    "total_size": 2560,
    "file_count": 2,
    "dir_count": 2,
    "warnings": []
}
```

### File Tracking Metadata

Each deployed file includes comprehensive tracking:

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

**Checksum:** MD5 hash of file content for integrity verification

### Directory Overlay System

#### _overlay_directory()

```python
def _overlay_directory(
    self,
    src_dir: Path,
    dest_dir: Path,
    codename: str
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Overlay source directory to destination, creating backups.

    Args:
        src_dir: Source directory in workspace
        dest_dir: Destination directory in TestForum
        codename: Plugin codename (for backup naming)

    Returns:
        Tuple of (files_metadata, directories_created, backups)
    """
```

**Behavior:**
- Copies files from source to destination recursively
- Creates backups of existing files (outside TestForum)
- Tracks new directories created
- Returns metadata for all files, directories, and backups

**Backup Location:** `plugin_manager/backups/{codename}/{timestamp}/`

**Example Backup Structure:**
```
plugin_manager/backups/
└── my_plugin/
    └── 20260118_081500/
        └── inc/
            └── plugins/
                └── my_plugin.php.backup
```

### Plugin Uninstallation

#### uninstall_plugin()

```python
def uninstall_plugin(
    self,
    codename: str,
    visibility: Optional[str] = None
) -> Dict[str, Any]:
    """Remove plugin files from TestForum using deployment manifest.

    Args:
        codename: Plugin codename
        visibility: Optional workspace visibility filter

    Returns:
        Uninstallation result dictionary

    Raises:
        ValueError: If plugin not installed or manifest missing
    """
```

**Uninstallation Steps:**
1. Retrieves deployment manifest from database
2. Restores files from backups (if exist)
3. Removes files deployed by us
4. Removes directories we created (if empty)
5. Clears deployment manifest

**Returns:**
```python
{
    "success": True,
    "plugin": "my_plugin",
    "files_removed": [
        "/path/to/inc/plugins/my_plugin.php",
        "/path/to/inc/languages/english/my_plugin.lang.php"
    ],
    "dirs_removed": ["/path/to/inc/plugins"],
    "restored_from_backup": [],
    "warnings": []
}
```

**Safety:** Only removes files/directories tracked in deployment manifest. Never removes files created by MyBB or other plugins.

## ThemeInstaller Class

Same interface as `PluginInstaller` but for themes.

### Theme-Specific Behavior

**Workspace Structure:**
```
themes/{visibility}/{codename}/
├── stylesheets/                    # CSS files
├── templates/                      # Template overrides
├── images/                         # Theme images
└── meta.json                       # Theme metadata
```

**Deployment Targets:**
- `stylesheets/` → Imported to MyBB theme system (not direct file copy)
- `templates/` → Imported to MyBB template system (not direct file copy)
- `images/` → Copied to TestForum images directory

**Note:** Themes use MyBB's import system, not direct file overlay like plugins.

## Deployment Manifest

### Manifest Format

Stored in `projects.deployed_files` column as JSON:

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
  "directories": [
    "/path/to/created/dir"
  ],
  "backups": [
    "/path/to/backup"
  ],
  "file_count": 5,
  "dir_count": 3
}
```

### Manifest Storage

**Database Methods:**

```python
# Store manifest
db.set_deployed_manifest(
    codename="my_plugin",
    files=[...],
    directories=[...],
    backups=[...]
)

# Retrieve manifest
manifest = db.get_deployed_manifest(codename="my_plugin")

# Clear manifest
db.clear_deployed_manifest(codename="my_plugin")
```

### Backward Compatibility

The system supports legacy manifest formats:
- **Simple list:** `["file1", "file2"]` (old format)
- **Old dict format:** `{"files": ["file1"], "dirs": ["dir1"]}` (deprecated)
- **Current format:** Full metadata with checksums and timestamps

## Backup and Restore Process

### Backup Creation

**When:** File exists at destination before deployment

**Location:** `plugin_manager/backups/{codename}/{timestamp}/`

**Naming:** Original path preserved within backup directory

**Example:**
```
Original: TestForum/inc/plugins/my_plugin.php
Backup:   plugin_manager/backups/my_plugin/20260118_081500/inc/plugins/my_plugin.php
```

### Restore Process

**When:** During uninstallation

**Behavior:**
1. Check if backup exists
2. Copy backup to original location
3. Remove backup directory after successful restore
4. Log restoration in warnings/results

**Safety:** If backup doesn't exist, file is simply removed (not restored).

## Usage Examples

### Full Installation Workflow

```python
from plugin_manager import PluginManager

pm = PluginManager()

# 1. Create workspace
result = pm.create_plugin(
    codename="my_plugin",
    display_name="My Plugin",
    author="Developer"
)

# 2. Develop plugin (edit files in workspace)
# ...

# 3. Deploy files to TestForum
install_result = pm.install_plugin("my_plugin")
print(f"Deployed {install_result['file_count']} files")

# 4. Activate via PHP bridge
activate_result = pm.activate_full("my_plugin")
print(f"Plugin activated: {activate_result.success}")
```

### Full Uninstallation Workflow

```python
# 1. Deactivate via PHP bridge
deactivate_result = pm.deactivate_full("my_plugin", uninstall=True)

# 2. Remove files from TestForum
uninstall_result = pm.uninstall_plugin("my_plugin")
print(f"Removed {len(uninstall_result['files_removed'])} files")

# 3. Optionally delete workspace
pm.delete_project("my_plugin")
```

### Manual Backup Management

```python
from plugin_manager.installer import PluginInstaller

installer = pm._plugin_installer

# Get backup location
backup_root = installer.backup_root / "my_plugin"
backups = sorted(backup_root.glob("*"))  # List by timestamp

# Manually restore from specific backup
# (normally handled automatically by uninstall)
```

## Error Handling

### Common Errors

**ValueError: Workspace not found**
```python
try:
    pm.install_plugin("nonexistent_plugin")
except ValueError as e:
    print(f"Error: {e}")
```

**FileNotFoundError: Required file missing**
```python
# Missing inc/plugins/{codename}.php
try:
    pm.install_plugin("incomplete_plugin")
except FileNotFoundError as e:
    print(f"Error: {e}")
```

**Database Errors:**
```python
try:
    pm.install_plugin("my_plugin")
except Exception as e:
    print(f"Database error: {e}")
```

### Validation Before Deployment

```python
from plugin_manager.workspace import PluginWorkspace

workspace = PluginWorkspace(config.get_workspace_path("plugin"))

# Validate workspace before installation
errors = workspace.validate_workspace("my_plugin")
if errors:
    print(f"Workspace invalid: {errors}")
else:
    # Safe to install
    pm.install_plugin("my_plugin")
```

## Best Practices

### Deployment

✅ **DO:**
- Always validate workspace before installation
- Keep backups until uninstallation complete
- Check deployment manifest before modifying files
- Use deployment manifest for uninstallation
- Store backups outside TestForum

❌ **DON'T:**
- Manually copy files to TestForum
- Delete backups before uninstallation
- Modify deployed files directly
- Remove files not in deployment manifest
- Store backups inside TestForum

### Backup Management

✅ **DO:**
- Preserve original file structure in backups
- Use timestamps in backup directory names
- Verify backup before removing original
- Log all backup operations

❌ **DON'T:**
- Reuse backup directories
- Modify backup files
- Delete backups before restore verification
- Skip backup creation for "safe" operations

### Manifest Tracking

✅ **DO:**
- Update manifest immediately after deployment
- Include all files and directories
- Store complete metadata (checksums, timestamps)
- Clear manifest after successful uninstallation

❌ **DON'T:**
- Modify manifest manually
- Skip checksum calculation
- Delete manifest before uninstallation
- Use manifest for non-deployment operations

## Related Documentation

- [Workspace Management](workspace.md) — Directory structure before deployment
- [Database Schema](database.md) — Manifest storage and queries
- [Plugin Manager Index](index.md) — System overview
- [Lifecycle Management](lifecycle.md) — PHP activation after deployment
