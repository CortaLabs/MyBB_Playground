# Template Management Tools

MyBB MCP provides comprehensive template management tools for reading, writing, and maintaining MyBB templates. Templates in MyBB use an inheritance system with master templates (sid=-2), global templates (sid=-1), and custom template sets (sid≥1).

## Tool Reference

### mybb_list_template_sets

List all MyBB template sets. Template sets are collections of templates for a theme.

**Parameters:**
None

**Returns:**
Markdown table of template sets with SID (Set ID) and title.

**Example:**
```
List all MyBB template sets
```

---

### mybb_list_templates

List templates with optional filtering by template set or search term.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sid` | integer | No | Template set ID. Use -2 for master templates, -1 for global templates |
| `search` | string | No | Filter templates by name (partial match) |

**Returns:**
Markdown table of templates (maximum 100 rows).

**Example:**
```
List all header templates
→ Uses search parameter to filter
```

---

### mybb_read_template

Read a template's HTML content. Shows both master and custom versions if a custom version exists.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | **Yes** | Template name to read |
| `sid` | integer | No | Template set ID. If omitted, checks both master and custom versions |

**Returns:**
Template HTML content. If a custom version exists, returns both master and custom for comparison.

**Example:**
```
Show me the header template
→ Returns master template and any custom overrides
```

---

### mybb_write_template

Update or create a template. Handles template inheritance automatically.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | string | **Yes** | - | Template name |
| `template` | string | **Yes** | - | Template HTML content |
| `sid` | integer | No | 1 | Template set ID (-2 for master, positive for custom sets) |

**Returns:**
Confirmation message indicating successful update.

**Behavior:**
- Automatically handles template inheritance
- Creates template if it doesn't exist
- Updates existing template if found

**Example:**
```
Update the header template to include a banner
→ Creates custom override in default template set
```

---

### mybb_list_template_groups

List template groups for organization (calendar, forum, usercp, etc.).

**Parameters:**
None

**Returns:**
List of template group categories used to organize templates in the MyBB Admin CP.

**Example:**
```
What template groups exist?
```

---

### mybb_template_find_replace

Perform find/replace operations across template sets. Mirrors MyBB's find_replace_templatesets() function - the most common plugin operation for template modification.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | string | **Yes** | - | Template name to modify |
| `find` | string | **Yes** | - | String or regex pattern to find |
| `replace` | string | **Yes** | - | Replacement text |
| `template_sets` | array of integers | No | [] (all sets) | List of template set IDs to modify. Empty array applies to all sets |
| `regex` | boolean | No | true | Use regex mode for pattern matching |
| `limit` | integer | No | -1 | Maximum replacements per template (-1 for unlimited) |

**Returns:**
Count of replacements made across all template sets.

**Note:**
This is the most common plugin operation for template modifications, mirroring MyBB's core find_replace_templatesets() function.

**Example:**
```
Replace {$header} with {$header}{$banner} in the header template
→ Uses regex mode by default
```

---

### mybb_template_batch_read

Read multiple templates in one call for efficiency.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `templates` | array of strings | **Yes** | - | List of template names to read |
| `sid` | integer | No | -2 (master) | Template set ID |

**Returns:**
All requested templates with their content.

**Example:**
```
Read header, footer, and index templates
→ Returns all three in one operation
```

---

### mybb_template_batch_write

Write multiple templates in one call. Operation is atomic (all or nothing).

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `templates` | array of objects | **Yes** | - | Array of template objects, each with `title` and `template` properties |
| `sid` | integer | No | 1 | Template set ID for all templates |

**Returns:**
Confirmation message indicating successful batch update.

**Behavior:**
- Atomic operation: either all templates succeed or all fail
- Ensures consistency when updating multiple related templates

**Example:**
```
Update multiple templates at once
→ Pass array of {title, template} objects
```

---

### mybb_template_outdated

Find templates that differ from master (outdated after MyBB upgrade). Compares version numbers to identify templates needing updates.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sid` | integer | **Yes** | Template set ID to check for outdated templates |

**Returns:**
List of outdated templates that differ from their master versions.

**Use Case:**
Finding templates that need updates after a MyBB upgrade. When MyBB core is updated, custom template overrides may become outdated if the master template changed.

**Example:**
```
Check which templates are outdated in template set 1
→ Compares against master templates
```

## Template Inheritance System

MyBB templates use a hierarchical inheritance system:

- **sid = -2**: Master templates (base templates, never delete)
- **sid = -1**: Global templates (shared across all sets)
- **sid ≥ 1**: Custom template sets (override master templates)

When you write a template to a custom set, it creates an override of the master template. The master template is preserved for reference and can be restored if needed.

## Common Workflows

### Reading Templates
1. Use `mybb_list_template_sets` to find the template set ID
2. Use `mybb_list_templates` to browse available templates
3. Use `mybb_read_template` to view specific template content

### Modifying Templates
1. Use `mybb_read_template` to view current content
2. Use `mybb_write_template` to create a custom override
3. Use `mybb_template_find_replace` for surgical modifications (preferred for plugins)

### Batch Operations
1. Use `mybb_template_batch_read` to read multiple related templates
2. Make modifications as needed
3. Use `mybb_template_batch_write` to update all at once (atomic operation)

### Maintenance
1. Use `mybb_template_outdated` after MyBB upgrades to find templates needing updates
2. Review outdated templates and merge changes from updated master templates
