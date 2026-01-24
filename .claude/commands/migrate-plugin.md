# /migrate-plugin

Guide for migrating a third-party MyBB plugin into the Playground workspace.

This command helps you migrate plugins from external sources (MyBB Mods, GitHub, etc.) into our workspace format with disk-based templates.

## Prerequisites

- Plugin source available in `third_party_plugins/` or accessible path
- MyBB server running (`mybb_server_status()`)

---

## Step 1: Identify Plugin Structure

First, analyze the plugin to understand its structure:

1. **Find the main PHP file** - look for the `{codename}_info()` function
2. **Identify structure pattern:**
   - **OUGC Modular:** `{codename}.php` + `{codename}/` subdirectory with admin modules
   - **Single-File:** Everything in one `.php` file (most common)
   - **Legacy Flat:** Large main file + separate admin modules in same directory

**Analysis Commands:**
```php
// Read the plugin to find _info() function
mybb_read_plugin("plugin_name")

// Analyze structure automatically
mybb_analyze_plugin("plugin_name")
```

---

## Step 2: Import Files

Use the MCP tool to copy files into workspace:

```python
mybb_plugin_import(
    source_path="third_party_plugins/{plugin_name}",
    category="imported"  # or "forked" if you plan to modify
)
```

This creates the workspace directory and basic `meta.json`.

**Categories:**
- `imported` - Third-party plugins brought in for use (gitignored)
- `forked` - Plugins you intend to modify and maintain

---

## Step 3: Extract Templates

Templates are typically embedded in the `_activate()` function. You need to extract them to disk files.

### Pattern A: PluginLibrary Templates

```php
// BEFORE (in _activate)
$PL->templates('codename', 'Plugin Name', array(
    '' => '<div>Base template</div>',       // -> templates/main.html
    'row' => '<div>Row template</div>'      // -> templates/row.html
));
```

**Extraction:**
1. The empty string key `''` becomes `templates/main.html`
2. Named keys like `'row'` become `templates/{name}.html`
3. Copy the HTML content, unescaping `\'` to `'`

### Pattern B: Raw DB Insert

```php
// BEFORE (in _activate)
$templatearray = array(
    'plugin_index' => '<table>...</table>',    // -> templates/index.html
    'plugin_post' => '<div>{$content}</div>'   // -> templates/post.html
);

foreach($templatearray as $name => $template) {
    $db->insert_query('templates', array(
        'title' => $name,
        'template' => $db->escape_string($template),
        'sid' => '-1'
    ));
}
```

**Extraction:**
1. Array keys are template names (strip plugin prefix for filename)
2. Create `templates/{name}.html` for each
3. Unescape PHP quotes: `\'` becomes `'`

### Pattern C: Already Disk-Based

Some plugins already load templates from files:

```php
// Plugin already uses file-based templates
$template_dir = MYBB_ROOT . 'inc/plugins/myplugin/templates/';
$template = file_get_contents($template_dir . 'main.html');
```

**Migration:**
1. Simply reorganize files to match our workspace structure
2. Move templates to `templates/` directory in workspace
3. Update paths in PHP if needed

### Extraction Steps (All Patterns)

1. Create `templates/` directory in workspace
2. For each template in the array:
   - Create `{name}.html` file
   - Copy template content
   - Unescape PHP quotes (`\'` to `'`, `\"` to `"`)
   - Remove plugin prefix from filename (e.g., `myplugin_row` -> `row.html`)

---

## Step 4: Update PHP for Disk-Based Loading

Replace embedded templates with disk-based loading. Add this helper function to the plugin:

```php
function {codename}_load_templates_from_disk()
{
    global $db;

    $templates_dir = MYBB_ROOT . 'inc/plugins/{codename}/templates';
    if (!is_dir($templates_dir)) {
        return;
    }

    foreach (glob($templates_dir . '/*.html') as $file) {
        $template_name = '{codename}_' . basename($file, '.html');
        $content = file_get_contents($file);

        // Check if template already exists
        $existing = $db->simple_select('templates', 'tid',
            "title='" . $db->escape_string($template_name) . "' AND sid=-2");

        if ($db->num_rows($existing) > 0) {
            $row = $db->fetch_array($existing);
            $db->update_query('templates', array(
                'template' => $db->escape_string($content),
                'dateline' => TIME_NOW
            ), "tid={$row['tid']}");
        } else {
            $db->insert_query('templates', array(
                'title' => $db->escape_string($template_name),
                'template' => $db->escape_string($content),
                'sid' => -2,
                'version' => '',
                'dateline' => TIME_NOW
            ));
        }
    }
}
```

Then update `_activate()` to call it:

```php
function {codename}_activate() {
    {codename}_load_templates_from_disk();

    // ... rest of activation (template modifications, etc.)
}
```

**Remove the old embedded template code** from `_activate()` after adding the disk-based loader.

---

## Step 5: Organize Language Files

Move language files to standard locations in the workspace:

| Type | Location |
|------|----------|
| Frontend strings | `inc/languages/english/{codename}.lang.php` |
| Admin CP strings | `inc/languages/english/admin/{codename}.lang.php` |

**Language File Format:**
```php
<?php
$l['codename_welcome'] = 'Welcome message';
$l['codename_error'] = 'Error message';
```

**Validation:**
```python
# Check for missing/unused language definitions
mybb_lang_validate("{codename}")

# Generate stubs for missing definitions
mybb_lang_generate_stub("{codename}")
```

---

## Step 6: Test

1. **Deploy to TestForum:**
   ```python
   mybb_plugin_install("{codename}")
   ```

2. **Check for PHP errors:**
   ```python
   mybb_server_logs(errors_only=True)
   ```

3. **Verify templates loaded:**
   ```python
   mybb_list_templates(search="{codename}")
   ```

4. **Test in browser:**
   - Navigate to http://localhost:8022
   - Test the plugin's functionality
   - Check Admin CP if plugin has settings

---

## Migration Checklist

- [ ] Main PHP file identified and copied
- [ ] `meta.json` created with correct plugin info
- [ ] Templates extracted to `templates/` directory
- [ ] PHP modified for disk-based template loading
- [ ] Old embedded template code removed
- [ ] Language files organized in correct locations
- [ ] Plugin deploys successfully with `mybb_plugin_install()`
- [ ] Templates render correctly in browser
- [ ] No PHP errors in `mybb_server_logs(errors_only=True)`

---

## Common Issues

**Template not found:**
- Check template naming: files use `{name}.html`, database uses `{codename}_{name}`
- Verify `templates/` directory exists in workspace

**Escaping issues:**
- When extracting templates, convert `\'` to `'` (unescape PHP quotes)
- Watch for double-escaping: `\\'` should become `\'`

**Missing language strings:**
- Run `mybb_lang_validate("{codename}")` to find missing definitions
- Check both frontend and admin language files

**PluginLibrary dependency:**
- If plugin requires PluginLibrary, it must be installed first
- Check `_install()` for PluginLibrary checks

**Settings not appearing:**
- Ensure `rebuild_settings()` is called in `_install()`
- Check setting group `gid` is correctly referenced
