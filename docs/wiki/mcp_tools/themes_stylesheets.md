# Theme & Stylesheet Tools

MyBB MCP provides tools for managing themes and their associated stylesheets. Themes control the visual appearance of MyBB forums, and each theme can have multiple stylesheets for different aspects of the design.

## Tool Reference

### mybb_list_themes

List all MyBB themes installed on the forum.

**Parameters:**
None

**Returns:**
Markdown table of all themes with theme ID, name, and properties.

**Example:**
```
List all themes
```

---

### mybb_list_stylesheets

List stylesheets with optional filtering by theme.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tid` | integer | No | Theme ID to filter by. If omitted, returns stylesheets for all themes |

**Returns:**
Markdown table of stylesheets with stylesheet ID, name, and associated theme information.

**Example:**
```
Show me all stylesheets for the default theme
→ Use tid parameter to filter by theme
```

---

### mybb_read_stylesheet

Read a stylesheet's CSS content.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sid` | integer | **Yes** | Stylesheet ID to read |

**Returns:**
CSS content of the specified stylesheet.

**Example:**
```
Show me the global.css stylesheet
→ First use mybb_list_stylesheets to find the stylesheet ID
```

---

### mybb_write_stylesheet

Update a stylesheet's CSS content and automatically refresh the cache.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sid` | integer | **Yes** | Stylesheet ID to update |
| `stylesheet` | string | **Yes** | New CSS content |

**Returns:**
Confirmation message indicating successful update.

**Behavior:**
- Updates the stylesheet content in the database
- Automatically refreshes the stylesheet cache
- Changes are immediately visible on the forum

**Example:**
```
Update the global.css stylesheet to change the header color
→ Cache is refreshed automatically after update
```

---

### mybb_create_theme

Create a new MyBB theme with proper structure in the plugin_manager workspace.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `codename` | string | **Yes** | - | Theme codename (lowercase, underscores) |
| `name` | string | **Yes** | - | Display name for the theme |
| `description` | string | No | - | Theme description |
| `author` | string | No | - | Author name |
| `version` | string | No | "1.0.0" | Theme version |
| `parent_theme` | string | No | - | Parent theme name to inherit from |
| `stylesheets` | array of strings | No | - | List of stylesheet names to create |

**Returns:**
Confirmation message with theme creation details and workspace path information.

**Behavior:**
- Creates theme structure in the plugin_manager workspace
- Optionally inherits from an existing parent theme
- Can create initial stylesheets during theme creation
- Theme files are created in workspace for development before installation

**Example:**
```
Create a new theme called "my_custom_theme" based on the default theme
→ Creates theme structure with inheritance from parent
```

---

### mybb_delete_theme

Permanently delete a theme from workspace and database. Archives by default (can be recovered). Use force=True for installed themes.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `codename` | string | **Yes** | - | Theme codename to delete |
| `archive` | boolean | No | `True` | Archive workspace instead of deleting (can be recovered) |
| `force` | boolean | No | `False` | Force deletion of installed themes (will uninstall first) |

**Returns:**
Confirmation message with deletion details and archive location (if archived).

**Behavior:**
- By default, archives the theme workspace instead of permanently deleting
- Archived themes can be recovered from the archive directory
- If `archive=False`, permanently deletes theme files
- If theme is currently installed and `force=True`, will uninstall before deleting
- Fails if theme is installed and `force=False` (safety check)

**Example:**
```
Delete and archive "my_old_theme" (can be recovered later)
→ Theme archived to plugin_manager/themes/archived/

Force delete installed theme "test_theme" permanently
→ Uninstalls theme first, then permanently deletes workspace
```

---

### mybb_sync_export_stylesheets

Export all stylesheets from a theme to disk files for editing.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `theme_name` | string | **Yes** | Theme name (e.g., 'Default') to export stylesheets from |

**Returns:**
Confirmation message with count of exported stylesheets and file paths.

**Behavior:**
- Exports all stylesheets from the specified theme to the sync directory
- Creates organized file structure for easy editing
- Part of the disk-sync workflow for live development

**Note:**
This is part of the sync service tools. See [Sync Service Tools](sync_service.md) for complete disk-sync workflow documentation.

**Example:**
```
Export all stylesheets from the Default theme
→ Creates .css files in mybb_sync/themes/Default/
```

## Theme & Stylesheet Architecture

### Themes
Themes in MyBB control the overall visual appearance of the forum. Each theme:
- Has a unique theme ID (`tid`)
- Can inherit from a parent theme
- Contains multiple stylesheets for different aspects of design
- Is associated with a template set

### Stylesheets
Stylesheets are CSS files that define the visual styling. Each stylesheet:
- Has a unique stylesheet ID (`sid`)
- Belongs to a specific theme
- Can be attached to specific pages or actions
- Is cached for performance (cache refreshed automatically on update)

### Theme Inheritance
Themes can inherit from parent themes, allowing you to:
- Create variations of existing themes
- Override only specific stylesheets
- Maintain consistency across related themes

## Common Workflows

### Browsing Themes and Stylesheets
1. Use `mybb_list_themes` to see all available themes
2. Note the theme ID (`tid`) for the theme you want to work with
3. Use `mybb_list_stylesheets` with the `tid` parameter to see that theme's stylesheets
4. Use `mybb_read_stylesheet` with the stylesheet ID (`sid`) to view CSS content

### Modifying Stylesheets
1. Use `mybb_list_stylesheets` to find the stylesheet you want to modify
2. Use `mybb_read_stylesheet` to view current CSS content
3. Make your changes
4. Use `mybb_write_stylesheet` to update the stylesheet (cache refreshes automatically)

### Creating a New Theme
1. Decide if you want to inherit from an existing theme
2. Use `mybb_create_theme` with appropriate parameters
3. Theme structure is created in the workspace
4. Add stylesheets using the `stylesheets` parameter or create them later
5. Install the theme through MyBB Admin CP when ready

### Live Development with Disk Sync
1. Use `mybb_sync_export_stylesheets` to export stylesheets to disk
2. Edit the .css files in your preferred editor
3. File watcher automatically syncs changes to database
4. Changes are immediately visible on the forum

**Note:** The complete disk-sync workflow is documented in [Sync Service Tools](sync_service.md).

## Tips for Theme Development

### Stylesheet Organization
- MyBB uses multiple stylesheets for different purposes (global, layout, navigation, etc.)
- Keep related styles in appropriate stylesheets for maintainability
- Use the Admin CP to see which stylesheet affects which parts of the forum

### Testing Changes
- Always test stylesheet changes on a development forum first
- Use browser developer tools to inspect elements and test CSS
- Cache is refreshed automatically, but browsers may cache CSS files

### Parent Themes
- Inheriting from a parent theme reduces duplication
- Only override stylesheets that need customization
- Parent theme updates don't automatically update child themes

### Performance
- Minimize the number of stylesheets where possible
- MyBB caches stylesheets for performance
- Combine similar styles to reduce HTTP requests
