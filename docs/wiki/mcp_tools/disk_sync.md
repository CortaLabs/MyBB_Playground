# Disk Sync Tools

Tools for synchronizing MyBB templates and stylesheets between the database and disk files.

## Tools Overview

| Tool | Description |
|------|-------------|
| `mybb_sync_export_templates` | Export all templates from a template set to disk files |
| `mybb_sync_export_stylesheets` | Export all stylesheets from a theme to disk files |
| `mybb_sync_start_watcher` | Start the file watcher to sync disk changes to database |
| `mybb_sync_stop_watcher` | Stop the file watcher |
| `mybb_sync_status` | Get current sync service status |

---

## mybb_sync_export_templates

Export all templates from a template set to disk files.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `set_name` | string | **REQUIRED** | - | Template set name (e.g., "Default Templates") |

### Returns

Confirmation message with:
- Number of templates exported
- Export directory path
- File paths for exported templates

### Behavior

- Exports templates to `mybb_sync/template_sets/{set_name}/` directory
- Creates subdirectories by template group (e.g., `Forum Templates/`, `Header Templates/`)
- Each template saved as `{template_name}.html`
- Existing files are overwritten

### Example

```
Export "Default Templates" set:
- set_name: "Default Templates"

Result: Templates exported to mybb_sync/template_sets/Default Templates/
```

---

## mybb_sync_export_stylesheets

Export all stylesheets from a theme to disk files.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `theme_name` | string | **REQUIRED** | - | Theme name (e.g., "Default") |

### Returns

Confirmation message with:
- Number of stylesheets exported
- Export directory path
- File paths for exported stylesheets

### Behavior

- Exports stylesheets to `mybb_sync/themes/{theme_name}/` directory
- Each stylesheet saved as `{stylesheet_name}.css`
- Existing files are overwritten

### Example

```
Export "Default" theme stylesheets:
- theme_name: "Default"

Result: Stylesheets exported to mybb_sync/themes/Default/
```

---

## mybb_sync_start_watcher

Start the file watcher to automatically sync disk changes to database.

### Parameters

None

### Returns

Confirmation message indicating watcher has started.

### Behavior

- Monitors `mybb_sync/` directory for file changes
- Automatically updates database when template/stylesheet files are modified
- Runs continuously in background until stopped
- Uses file system events for efficient monitoring

### Example

```
Start file watcher:
(no parameters)

Result: File watcher started, monitoring mybb_sync/ directory
```

---

## mybb_sync_stop_watcher

Stop the file watcher.

### Parameters

None

### Returns

Confirmation message indicating watcher has stopped.

### Example

```
Stop file watcher:
(no parameters)

Result: File watcher stopped
```

---

## mybb_sync_status

Get current sync service status.

### Parameters

None

### Returns

Status information including:
- Watcher state (running/stopped)
- Sync directory path
- Number of files being watched
- Last sync timestamp (if applicable)

### Example

```
Check sync status:
(no parameters)

Result:
- Watcher: running
- Directory: /path/to/mybb_sync/
- Files watched: 347
- Last sync: 2026-01-18 08:30:15
```

---

## Usage Notes

### Disk Sync Workflow

**Initial Export:**
1. Use `mybb_sync_export_templates` to export template sets from database to disk
2. Use `mybb_sync_export_stylesheets` to export themes from database to disk
3. This creates the initial `mybb_sync/` directory structure

**Enable Live Sync:**
4. Use `mybb_sync_start_watcher` to begin monitoring file changes
5. Now you can edit template/stylesheet files in your code editor
6. Changes are automatically synced to the database

**Stop Sync:**
7. Use `mybb_sync_stop_watcher` when you want to stop automatic syncing
8. Use `mybb_sync_status` to verify watcher has stopped

### Directory Structure

After export, files are organized as:

```
mybb_sync/
├── template_sets/
│   └── Default Templates/
│       ├── Forum Templates/
│       │   ├── forumbit_depth1.html
│       │   └── forumbit_depth2.html
│       ├── Header Templates/
│       │   ├── header.html
│       │   └── header_welcomeblock_guest.html
│       └── ...
└── themes/
    └── Default/
        ├── global.css
        ├── usercp.css
        └── ...
```

### File Watching Behavior

The file watcher:
- Detects file modifications, creations, and deletions
- Automatically updates the database with file changes
- Supports both templates (.html) and stylesheets (.css)
- Processes changes in batches for efficiency
- Logs all sync operations

### Common Use Cases

**VSCode/Editor Workflow:**
```
1. Export templates to disk: mybb_sync_export_templates(set_name="Default Templates")
2. Start watcher: mybb_sync_start_watcher()
3. Open mybb_sync/ in your code editor
4. Edit templates with syntax highlighting and autocomplete
5. Changes automatically sync to database
6. Refresh browser to see changes
```

**One-Time Export (No Live Sync):**
```
1. Export templates: mybb_sync_export_templates(set_name="Default Templates")
2. Copy files to version control or backup
3. Do NOT start watcher
```

**Status Monitoring:**
```
1. Check if watcher is running: mybb_sync_status()
2. If needed, stop watcher: mybb_sync_stop_watcher()
3. Make bulk database changes via other tools
4. Restart watcher: mybb_sync_start_watcher()
```

### Performance Considerations

- **Export operations** may take 10-30 seconds for large template sets (100+ templates)
- **File watcher** uses minimal resources when idle
- **Sync operations** are debounced to avoid duplicate updates during rapid editing
- **Large themes** (many stylesheets) may take longer to export

### Caveats

- Watcher only syncs changes **FROM disk TO database**
- Database changes made via other tools are NOT synced to disk automatically
- Re-export templates/stylesheets to update disk files after database changes
- Template set name and theme name must match exactly (case-sensitive)

---

[← Back to MCP Tools Index](index.md)
