# Workspace Management

**Module:** `plugin_manager/workspace.py` (561 lines)
**Classes:** `PluginWorkspace`, `ThemeWorkspace`

## Overview

Workspace management provides directory structure mirroring MyBB's layout for simple overlay installation. Each project has a dedicated workspace directory with meta.json configuration and source files organized exactly as they'll be deployed to TestForum.

## Directory Structure

### Plugin Workspace

**Root Path:** `plugin_manager/plugins/`

```
plugins/
├── public/
│   ├── plugin_one/
│   │   ├── inc/
│   │   │   ├── plugins/
│   │   │   │   └── plugin_one.php          # Main plugin file
│   │   │   └── languages/
│   │   │       └── english/
│   │   │           └── plugin_one.lang.php # Language file
│   │   ├── jscripts/                       # Optional JavaScript
│   │   ├── images/                         # Optional images
│   │   ├── meta.json                       # Project metadata
│   │   └── README.md                       # Project documentation
│   └── plugin_two/
│       └── ...
└── private/
    └── internal_plugin/
        └── ...
```

**Visibility:** 'public' or 'private' (affects workspace location only)

### Theme Workspace

**Root Path:** `plugin_manager/themes/`

```
themes/
├── public/
│   ├── theme_one/
│   │   ├── stylesheets/
│   │   │   └── global.css                  # CSS files
│   │   ├── templates/                      # Template overrides
│   │   ├── images/                         # Theme images
│   │   ├── meta.json                       # Theme metadata
│   │   └── README.md                       # Theme documentation
│   └── theme_two/
│       └── ...
└── private/
    └── ...
```

## PluginWorkspace Class

### Initialization

```python
from plugin_manager.workspace import PluginWorkspace

workspace = PluginWorkspace(root_path: Path)
```

**Root Path:** Typically `plugin_manager/plugins`

### Methods

#### create_workspace()

```python
def create_workspace(self, codename: str, visibility: str = "public") -> Path:
    """Create a new plugin workspace directory structure.

    Args:
        codename: Plugin codename (lowercase, underscores)
        visibility: 'public' or 'private'

    Returns:
        Path to created workspace
    """
```

**Creates:**
- `inc/plugins/`
- `inc/languages/english/`
- `jscripts/`
- `images/`

**Example:**
```python
workspace_path = workspace.create_workspace("my_plugin", "public")
# Returns: plugin_manager/plugins/public/my_plugin/
```

#### get_workspace_path()

```python
def get_workspace_path(
    self,
    codename: str,
    visibility: Optional[str] = None
) -> Optional[Path]:
    """Find plugin workspace path by codename.

    Args:
        codename: Plugin codename
        visibility: If None, searches both public and private

    Returns:
        Path if found, None otherwise
    """
```

**Behavior:** If visibility not specified, searches both public and private workspaces.

#### read_meta()

```python
def read_meta(
    self,
    codename: str,
    visibility: Optional[str] = None
) -> Dict[str, Any]:
    """Read and parse meta.json from plugin workspace.

    Args:
        codename: Plugin codename
        visibility: Optional workspace visibility filter

    Returns:
        Parsed meta.json data

    Raises:
        FileNotFoundError: If meta.json doesn't exist
        json.JSONDecodeError: If meta.json is invalid
    """
```

#### write_meta()

```python
def write_meta(
    self,
    codename: str,
    meta: Dict[str, Any],
    visibility: Optional[str] = None
) -> None:
    """Write meta.json to plugin workspace.

    Args:
        codename: Plugin codename
        meta: Metadata dictionary
        visibility: Optional workspace visibility filter

    Raises:
        ValueError: If validation fails
    """
```

**Validation:** Calls `validate_meta()` before writing.

#### validate_workspace()

```python
def validate_workspace(
    self,
    codename: str,
    visibility: Optional[str] = None
) -> List[str]:
    """Validate plugin workspace structure and contents.

    Args:
        codename: Plugin codename
        visibility: Optional workspace visibility filter

    Returns:
        List of validation errors (empty if valid)
    """
```

**Checks:**
- Required directories exist (`inc/plugins`, `inc/languages/english`)
- meta.json exists and is valid
- PHP files exist in `inc/plugins/`

**Example:**
```python
errors = workspace.validate_workspace("my_plugin")
if errors:
    print(f"Validation failed: {errors}")
else:
    print("Workspace is valid")
```

#### list_plugins()

```python
def list_plugins(self, visibility: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all plugins in workspace.

    Args:
        visibility: Filter by 'public' or 'private', or None for all

    Returns:
        List of plugin info dictionaries
    """
```

**Returns:**
```python
[
    {
        "codename": "my_plugin",
        "visibility": "public",
        "workspace_path": "/path/to/workspace",
        "has_meta": True,
        "display_name": "My Plugin",
        "version": "1.0.0",
        "type": "plugin"
    },
    ...
]
```

## ThemeWorkspace Class

Same interface as `PluginWorkspace`, but operates on `plugin_manager/themes/` with theme-specific directory structure.

### Additional Method

#### scaffold_stylesheet()

```python
def scaffold_stylesheet(
    self,
    name: str = 'global.css',
    parent_theme: Optional[str] = None
) -> str:
    """Generate CSS stylesheet content with optional parent theme inheritance.

    Args:
        name: Stylesheet filename
        parent_theme: Parent theme codename for inheritance

    Returns:
        Generated CSS content string
    """
```

**Behavior:** If `parent_theme` specified, generates import statement at top:

```css
/* Inherit from parent theme */
@import url('../parent_theme/global.css');

/* Custom styles */
body {
    /* ... */
}
```

## meta.json Schema

### Common Fields (Required)

```json
{
  "codename": "my_plugin",
  "display_name": "My Plugin",
  "version": "1.0.0",
  "author": "Developer",
  "description": "Plugin description",
  "mybb_compatibility": "18*",
  "visibility": "public",
  "type": "plugin"
}
```

**Validation Rules:**
- **codename:** Matches `^[a-z][a-z0-9_]*$` (lowercase, underscores only)
- **version:** Matches `^\d+\.\d+\.\d+$` (semantic versioning)
- **visibility:** Enum `["public", "private"]`
- **type:** Enum `["plugin", "theme"]`

### Plugin-Specific Fields

```json
{
  "hooks": [
    {
      "name": "index_start",
      "handler": "my_plugin_index",
      "priority": 10
    }
  ],
  "settings": [
    {
      "name": "my_plugin_enabled",
      "title": "Enable Plugin",
      "type": "yesno",
      "description": "Enable or disable the plugin",
      "default": "1",
      "options": ""
    }
  ],
  "templates": ["my_template_name"],
  "has_templates": false,
  "has_database": false,
  "files": {
    "plugin": "inc/plugins/my_plugin.php",
    "languages": "inc/languages/",
    "jscripts": "jscripts/",
    "images": "images/"
  }
}
```

**Setting Types:**
- `text` — Single-line text input
- `textarea` — Multi-line text input
- `yesno` — Boolean radio buttons
- `select` — Dropdown menu (options in `options` field)
- `radio` — Radio buttons (options in `options` field)

**Options Format:** Newline-separated key=value pairs

### Theme-Specific Fields

```json
{
  "stylesheets": [
    {
      "name": "global.css",
      "attached_to": ["global"],
      "display_order": 1
    }
  ],
  "template_overrides": ["header", "footer"],
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

## Workspace Validation

The `schema.py` module provides comprehensive validation:

### validate_meta()

```python
from plugin_manager.schema import validate_meta

is_valid, errors = validate_meta(meta_dict)
if not is_valid:
    print(f"Validation errors: {errors}")
```

**Validates:**
- Required fields present
- Codename pattern (lowercase, underscores)
- Version semantic versioning
- Visibility enum
- Hooks array structure
- Settings array structure
- Stylesheets array structure
- Template overrides array

### create_default_meta()

```python
from plugin_manager.schema import create_default_meta

meta = create_default_meta(
    codename="my_plugin",
    display_name="My Plugin",
    author="Developer",
    version="1.0.0",
    description="",
    mybb_compatibility="18*",
    visibility="public",
    project_type="plugin"  # or "theme"
)
```

Returns appropriate structure based on `project_type`.

### Convenience Wrappers

```python
from plugin_manager.schema import create_default_plugin_meta, create_default_theme_meta

# Plugin-specific defaults
plugin_meta = create_default_plugin_meta(
    codename="my_plugin",
    display_name="My Plugin",
    author="Developer"
)

# Theme-specific defaults
theme_meta = create_default_theme_meta(
    codename="my_theme",
    display_name="My Theme",
    author="Designer"
)
```

## File I/O Utilities

### load_meta()

```python
from plugin_manager.schema import load_meta

meta_dict, errors = load_meta("/path/to/meta.json")
if errors:
    print(f"Load errors: {errors}")
```

**Returns:** `(parsed_dict, list_of_errors)`

### save_meta()

```python
from plugin_manager.schema import save_meta

success, errors = save_meta(meta_dict, "/path/to/meta.json")
if not success:
    print(f"Save errors: {errors}")
```

**Returns:** `(success, list_of_errors)`

**Validation:** Automatically validates before saving.

## Best Practices

### Directory Structure

✅ **DO:**
- Mirror MyBB's directory layout exactly
- Keep optional directories (jscripts, images) even if empty
- Use lowercase codenames with underscores

❌ **DON'T:**
- Create custom directory structures
- Use dashes or uppercase in codenames
- Store files outside workspace structure

### meta.json Management

✅ **DO:**
- Always validate before saving
- Use `create_default_meta()` for new projects
- Include all required fields
- Follow semantic versioning

❌ **DON'T:**
- Manually edit JSON without validation
- Skip required fields
- Use invalid codename patterns
- Hardcode workspace paths

### Workspace Organization

✅ **DO:**
- Use `public` for shareable plugins
- Use `private` for internal tools
- Keep README.md in each workspace
- Document custom settings/templates

❌ **DON'T:**
- Mix public/private concerns
- Store TestForum files in workspace
- Duplicate code across workspaces

## Related Documentation

- [Deployment System](deployment.md) — How workspace files are deployed to TestForum
- [Database Schema](database.md) — How workspace metadata is tracked
- [Plugin Manager Index](index.md) — System overview
