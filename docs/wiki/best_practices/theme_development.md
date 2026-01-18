# Theme Development Best Practices

**Complete guide to creating and packaging MyBB themes with proper inheritance, stylesheets, and template overrides.**

---

## Theme Structure

### Workspace Organization

The Plugin Manager creates this workspace layout for themes:

```
plugin_manager/themes/{visibility}/{codename}/
├── stylesheets/
│   ├── global.css              # Main stylesheet
│   ├── header.css              # Header styles
│   └── custom.css              # Additional stylesheets
├── templates/                   # Template overrides (optional)
├── images/                      # Theme images (optional)
├── meta.json                    # Theme metadata
└── README.md                    # Documentation
```

**Visibility:**
- `public/` - Public themes (shareable)
- `private/` - Private themes (internal use)

### meta.json Structure

```json
{
  "codename": "mytheme",
  "display_name": "My Theme",
  "type": "theme",
  "version": "1.0.0",
  "author": "Author Name",
  "description": "Theme description",
  "mybb_compatibility": "18*",
  "parent_theme": "Default"
}
```

**Required Fields:**
- `codename` - Unique identifier (lowercase, underscores)
- `display_name` - Display name in Admin CP
- `type` - Always "theme"
- `version` - Semantic versioning
- `mybb_compatibility` - MyBB version pattern

**Optional Fields:**
- `parent_theme` - Parent theme name for inheritance
- `author` - Theme author
- `description` - Theme description

---

## Stylesheet Inheritance

### Copy-on-Write Pattern

MyBB themes use a **copy-on-write** inheritance model:

1. **Parent Theme**: Contains base stylesheets
2. **Child Theme**: Inherits parent stylesheets automatically
3. **Override**: Editing a stylesheet in child theme creates a copy (does NOT modify parent)

**Example:**

```
Default (parent)
├── global.css (base styles)
└── header.css (base header)

My Theme (child, inherits from Default)
├── global.css (OVERRIDDEN - custom version)
└── header.css (INHERITED - uses Default's version)
```

### Theme Inheritance Chain

Themes can have multiple inheritance levels:

```
Default
  └── Blue Theme (inherits from Default)
      └── Dark Blue (inherits from Blue Theme)
```

When a stylesheet is requested:
1. Check Dark Blue theme for override
2. If not found, check Blue Theme
3. If not found, use Default theme version

**Implementation:** MyBB walks the inheritance chain using `pid` (parent theme ID) field.

### Creating Stylesheets with Inheritance

If your theme inherits from a parent, reference parent stylesheets via `@import`:

```css
/* global.css - inherits from parent then adds customization */
@import url("../Default/global.css");

/* Custom overrides */
body {
    background-color: #1a1a1a;
    color: #ffffff;
}

.header {
    background: linear-gradient(to right, #2c3e50, #3498db);
}
```

**Best Practice:** Import parent stylesheet first, then add customizations below.

---

## Template Overrides

### Master Template Inheritance

MyBB templates use a three-tier inheritance system:

1. **Master Templates** (sid=-2): Base templates in MyBB core
2. **Global Templates** (sid=-1): Shared across all template sets
3. **Custom Templates** (sid=specific_id): Template set overrides

**Template Resolution Order:**
1. Check custom template for current template set
2. If not found, check global templates
3. If not found, use master template

### Creating Template Overrides

**Via Disk Sync:**

1. Export master templates to disk:
   ```
   mybb_sync_export_templates(set_name="Default Templates")
   ```

2. Templates are organized by group:
   ```
   mybb_sync/template_sets/Default Templates/
   ├── Header Templates/
   │   ├── header.html
   │   └── header_welcomeblock_member.html
   ├── Index Templates/
   │   └── index.html
   └── Forumdisplay Templates/
       └── forumdisplay.html
   ```

3. Edit template file on disk

4. File watcher automatically syncs to database (creates override if doesn't exist)

**Via MCP Tools:**

```
mybb_write_template(
    title="header",
    template="<html>...</html>",
    sid=1  # Template set ID
)
```

This creates a custom override for the template set.

### Template Override Best Practices

- **Override only when necessary**: Don't copy templates just to have them
- **Keep overrides minimal**: Only change what's needed
- **Document changes**: Comment why override was created
- **Test after MyBB upgrades**: Master templates may change

### Template Variables

MyBB templates use `{$variable}` syntax:

```html
<div class="header">
    <h1>{$mybb->settings['bbname']}</h1>
    <span>Welcome, {$mybb->user['username']}</span>
</div>
```

**Available Variables:**
- `{$mybb}` - Core MyBB object (settings, user, etc.)
- `{$lang}` - Language strings
- `{$theme}` - Current theme data
- Custom variables set in plugin/page code

### Template Conditionals

```html
<if $mybb->user['uid'] then>
    <!-- Logged in content -->
    <span>Hello, {$mybb->user['username']}</span>
<else />
    <!-- Guest content -->
    <span>Welcome, Guest</span>
</if>
```

---

## Theme Packaging

### Directory Structure for Distribution

When packaging a theme for distribution:

```
my_theme_v1.0/
├── inc/
│   └── languages/
│       └── english/
│           └── mytheme.lang.php (optional language strings)
├── images/
│   └── mytheme/
│       ├── logo.png
│       └── background.jpg
├── Upload/
│   └── install.php (optional installer script)
├── README.md
└── LICENSE.txt
```

### README.md Template

```markdown
# My Theme v1.0

**Author:** Your Name
**Version:** 1.0.0
**MyBB Compatibility:** 1.8.x
**Parent Theme:** Default (or "None" if standalone)

## Description
Brief description of your theme and its features.

## Installation

1. Upload stylesheet files to Admin CP:
   - ACP → Templates & Style → Themes → Import Theme
   - Or manually via Stylesheets section

2. If template overrides included:
   - Import via Templates section
   - Or use MCP tools: mybb_write_template(...)

3. Set as default theme or allow users to select

## Features
- Feature 1
- Feature 2
- Feature 3

## Customization
How to customize colors, fonts, etc.

## Credits
- Original design: ...
- Icons from: ...

## License
License information (MIT, GPL, etc.)
```

### Stylesheet Cache Management

After modifying stylesheets, **cache must be refreshed**:

**Via MCP:**
```
mybb_write_stylesheet(sid=1, stylesheet="...")
```
This automatically refreshes the cache.

**Manual refresh:**
- Admin CP → Templates & Style → Themes → Theme Name → Rebuild Stylesheet Cache

**Why:** MyBB caches compiled stylesheets for performance. Changes won't appear until cache is refreshed.

---

## Creating Themes via MCP

### Using mybb_create_theme

```
mybb_create_theme(
    codename="mytheme",
    name="My Theme",
    description="A custom theme",
    author="Your Name",
    version="1.0.0",
    parent_theme="Default",
    stylesheets=["global", "header", "footer"]
)
```

This creates:
- Workspace directory structure
- meta.json with metadata
- Stylesheet scaffolds (with parent import if parent_theme specified)
- README.md template

### Stylesheet Scaffold Generation

If `parent_theme` is specified, generated stylesheets include import:

```css
/* global.css - auto-generated */
@import url("../Default/global.css");

/* Add your custom styles below */
```

---

## Disk Sync Workflow

### Export Stylesheets to Disk

```
mybb_sync_export_stylesheets(theme_name="Default")
```

Creates:
```
mybb_sync/styles/Default/
├── global.css
├── header.css
├── footer.css
└── ... (all theme stylesheets)
```

### Live Sync with File Watcher

1. Start file watcher:
   ```
   mybb_sync_start_watcher()
   ```

2. Edit files in `mybb_sync/styles/{theme_name}/`

3. File watcher detects changes and syncs to database automatically

4. Changes appear immediately (after cache refresh)

### Atomic Write Safety

The file watcher handles **atomic writes** properly:

- **Direct writes**: VSCode, nano, vim (on_modified event)
- **Atomic writes**: Write to `.tmp` file, then rename (on_moved event)

**Both patterns are supported** - no special editor configuration needed.

### Debouncing

File watcher uses **0.5 second debounce** to prevent duplicate syncs:

- Multiple rapid saves trigger only one sync
- Prevents race conditions during batch edits
- Thread-safe per-file timestamp tracking

---

## Common Theme Issues

### Stylesheets Not Updating

**Symptoms:** Changes to CSS don't appear on site

**Solutions:**
1. Refresh stylesheet cache (Admin CP or MCP tool)
2. Clear browser cache
3. Verify file watcher is running: `mybb_sync_status()`
4. Check file is in correct directory: `mybb_sync/styles/{theme_name}/`

### Parent Theme Inheritance Not Working

**Symptoms:** Child theme doesn't inherit parent styles

**Solutions:**
1. Verify `parent_theme` in meta.json matches exact theme name
2. Check parent theme exists in database
3. Ensure `@import` path is correct in stylesheets
4. Verify theme hierarchy: Admin CP → Themes → check parent ID (pid)

### Template Overrides Not Appearing

**Symptoms:** Custom template not used, master template shown instead

**Solutions:**
1. Verify template set ID (sid) is correct
2. Check template title matches exactly (case-sensitive)
3. Ensure template cache is rebuilt
4. Verify template was imported to correct template set

### Empty Files Imported

**Symptoms:** Stylesheets/templates become empty after sync

**Solutions:**
1. File watcher validates file size before importing
2. Check file wasn't corrupted during save
3. Re-export from database if file lost
4. Ensure editor saves files completely before file watcher processes

---

## Theme Development Workflow

### 1. Create Theme Workspace

```
mybb_create_theme(
    codename="mytheme",
    name="My Theme",
    parent_theme="Default"
)
```

### 2. Develop Stylesheets

Edit files in `plugin_manager/themes/public/mytheme/stylesheets/`

### 3. Export to Disk Sync (Optional)

For live editing with file watcher:

```
mybb_sync_export_stylesheets(theme_name="My Theme")
mybb_sync_start_watcher()
```

Edit in `mybb_sync/styles/My Theme/` for automatic sync.

### 4. Deploy to TestForum

```
# Deploy theme files
# (Deployment tool TBD - currently manual via Admin CP)
```

### 5. Test Theme

- Set as default or allow user selection
- Test all pages (index, threads, profiles, Admin CP)
- Verify inheritance chain works
- Check responsive design on mobile

### 6. Package for Distribution

- Export final stylesheets
- Create README.md with installation instructions
- Include screenshots
- Test installation on fresh MyBB instance

---

## Security Considerations

### Stylesheet Content

- **No PHP code**: Stylesheets are served as static CSS
- **No user input**: Don't generate CSS from user data
- **No external includes**: Avoid loading CSS from untrusted sources

### Template Overrides

- **Escape variables**: Use `{htmlspecialchars($variable)}` for user input
- **Validate data**: Don't trust template variables to be safe
- **CSRF tokens**: Include `{$mybb->post_code}` in all forms

### Image Files

- **Validate uploads**: Check file types and sizes
- **Store in images directory**: Don't use uploaded files as theme images
- **Sanitize filenames**: No special characters or directory traversal

---

## Performance Best Practices

### Stylesheet Optimization

- **Minimize HTTP requests**: Combine stylesheets when possible
- **Use CSS sprites**: Combine small images into sprite sheets
- **Avoid @import**: Use multiple `<link>` tags instead (faster parallel loading)
- **Minify CSS**: Remove comments and whitespace for production

### Template Optimization

- **Minimize template count**: Don't create unnecessary overrides
- **Cache template variables**: Don't recalculate same value multiple times
- **Lazy load images**: Use loading="lazy" for images below fold
- **Optimize loops**: Avoid expensive operations in template loops

---

## Testing Your Theme

### Compatibility Testing

- [ ] Test on MyBB 1.8.x (exact version specified in compatibility)
- [ ] Test with parent theme changes (if inheriting)
- [ ] Test template overrides after MyBB upgrade
- [ ] Verify all template variables resolve correctly

### Visual Testing

- [ ] All pages render correctly (index, threads, profiles, Admin CP)
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] All colors contrast properly (accessibility)
- [ ] Images load correctly
- [ ] No broken styles or missing elements

### Performance Testing

- [ ] Page load time acceptable (< 2 seconds)
- [ ] No excessive HTTP requests
- [ ] Stylesheet cache working properly
- [ ] No JavaScript errors in console

---

## Additional Resources

- [MCP Theme Tools](../mcp_tools/themes_stylesheets.md) - Theme/stylesheet tools
- [Disk Sync Architecture](../architecture/disk_sync.md) - How sync works
- [Template Tools](../mcp_tools/templates.md) - Template management tools
- [MyBB Theme Documentation](https://docs.mybb.com/1.8/themes/)

---

**Last Updated:** 2026-01-18
