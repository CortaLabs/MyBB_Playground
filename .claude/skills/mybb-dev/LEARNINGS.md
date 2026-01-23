# MyBB Development Learnings

A continuously updated collection of discoveries, gotchas, tips, and hard-won knowledge from working with the MyBB Playground system.

**How to use this file:**
- Search for keywords when you hit a problem
- Add new entries when you solve something tricky
- Include the date and context so future readers understand

---

## Quick Rules

**When adding MCP tools:** Update `EXPECTED_TOOL_COUNT` in `tools_registry.py` or the server won't start.

---

## Plugin Development

### Template Updates Require Full Reinstall
**Date:** 2025-01-21
**Context:** Plugin Manager workflow

`mybb_plugin_install()` alone does NOT update templates that already exist in the database. You must do a full uninstall/reinstall cycle:

```python
mybb_plugin_uninstall(codename="my_plugin", remove_files=True)
mybb_plugin_install(codename="my_plugin")
```

This ensures templates, language files, and PHP files are all synced fresh from workspace to TestForum.

---

### Plugin Templates Go in Workspace, Not mybb_sync
**Date:** 2025-01-21
**Context:** Template organization

Plugin templates live in `plugin_manager/plugins/{visibility}/{codename}/templates/`, NOT in `mybb_sync/`. The disk sync system is for editing core/theme templates, not plugin templates.

Plugin template naming: `{codename}_{template_name}.html` (e.g., `myplugin_welcome.html`)

---

### Language Files Must Be Maintained Alongside Code
**Date:** 2025-01-21
**Context:** Internationalization

If you add `$lang->new_key` usage in PHP or `{$lang->new_key}` in templates, you MUST add the definition to the language file:

```php
// inc/languages/english/{codename}.lang.php
$l['new_key'] = 'The display text';
```

Use `mybb_lang_validate(codename)` to check for missing definitions before deploying.

---

## Template System

### Understanding sid Values
**Date:** 2025-01-21
**Context:** Template queries

| sid | What it means |
|-----|---------------|
| -2 | Master templates (base, immutable) |
| -1 | Global templates (shared) |
| 1+ | Custom template set overrides |

When you `mybb_read_template("postbit")`, it checks both master and custom. Specify `sid` explicitly if you need a specific version.

---

### Disk Sync is the Primary Workflow
**Date:** 2025-01-21
**Context:** Template editing

Don't use `mybb_write_template` during development. The workflow is:
1. Export templates to disk: `mybb_sync_export_templates("Default Templates")`
2. Start watcher: `mybb_sync_start_watcher()`
3. Edit files in `mybb_sync/template_sets/`
4. Watcher auto-syncs to database

Direct database writes bypass the audit trail and can conflict with disk versions.

---

## Debugging

### Server Logs Are Your First Stop
**Date:** 2025-01-21
**Context:** Error diagnosis

When something breaks, check server logs FIRST:

```python
mybb_server_logs(errors_only=True, limit=50)
```

This catches PHP fatal errors, parse errors, and HTTP 4xx/5xx responses that you won't see in the browser.

---

### Check Plugin Status Before Assuming It's Missing
**Date:** 2025-01-21
**Context:** Plugin Manager

Before concluding a plugin doesn't exist:

```python
mybb_plugin_status("my_plugin")  # Full status with installation state
mybb_plugin_is_installed("my_plugin")  # Quick boolean check
```

The plugin might exist but be deactivated, or the workspace might exist but not be deployed.

---

## MCP Tools

### hooks_discover vs list_hooks
**Date:** 2025-01-21
**Context:** Finding hooks

- `mybb_list_hooks()` — Shows hooks from the reference database (documented hooks)
- `mybb_hooks_discover()` — Scans actual PHP files for `$plugins->run_hooks()` calls

Use `hooks_discover` when you need to find hooks that might not be in the reference.

---

## Common Gotchas

### Don't Edit TestForum/ Directly
**Date:** 2025-01-21
**Context:** Core files

Files in `TestForum/` get overwritten on MyBB upgrades. All customization must be through:
- Plugins (in workspace, deployed via Plugin Manager)
- Templates (via disk sync)
- Stylesheets (via disk sync)

---

### Workspace Path Matters for Visibility
**Date:** 2025-01-21
**Context:** Plugin organization

- `plugin_manager/plugins/public/` — Shareable plugins (tracked in parent repo)
- `plugin_manager/plugins/private/` — Personal plugins (gitignored, own git repos)

Choose the right location when creating plugins.

---

## Performance Tips

### Use Batch Operations When Possible
**Date:** 2025-01-21
**Context:** MCP efficiency

For multiple templates:
```python
mybb_template_batch_read(templates=["postbit", "header", "footer"])
mybb_template_batch_write(templates=[...])
```

This is faster than individual calls and reduces context usage.

---

## Critical Learnings from Project History

These learnings come from real development work across 6+ major projects, 50+ progress log entries, and 14 bug reports.

### CRITICAL: MCP Create Plugin MUST Run Before Coders
**Date:** 2026-01-18
**Context:** cortex, phptpl-modernization projects

Bypassing `mybb_create_plugin` and creating plugin files directly causes installation to fail. **All generated code is lost.**

**What happened:**
- phptpl-modernization created code without MCP initialization
- Plugin scaffold wasn't registered in database
- Installation failed with structure errors
- **4 phases of code were completely lost**
- Project restarted as "cortex" using correct workflow and succeeded

**The correct sequence:**
1. `mybb_create_plugin(codename, name, description)` — creates workspace + registers in DB
2. Coders modify files within workspace
3. `mybb_plugin_install(codename)` — deploys to TestForum

**Never skip step 1. The consequences are catastrophic.**

---

### CRITICAL: Hardcoded Database Paths Cause Data Splits
**Date:** 2026-01-19
**Context:** plugin_manager_db_fix

Multiple database files can coexist when hardcoded paths bypass the canonical location.

**What happened:**
- MCP handlers hardcoded `plugin_manager/data/projects.db` in 4 locations
- Actual config pointed to `.plugin_manager/projects.db`
- Result: Three separate databases with conflicting data
- Symptoms: "UNIQUE constraint" errors, plugins created but not visible

**Fix:** Always use `plugin_manager.Config.database_path`, never hardcode paths.

---

### CRITICAL: Infrastructure Primacy (Commandment #0.5)
**Date:** 2026-01-21
**Context:** invite_email_system

Creating separate admin modules instead of integrating with existing infrastructure violates Commandment #0.5.

**What happened:**
- Coder created `admin/modules/user/invite_emails.php` as a separate module
- This bypassed the existing `module_meta.php` tab system
- Created duplicate navigation, confused users

**The fix:**
1. Deleted the separate module
2. Added action to existing `module_meta.php` action registry
3. Integrated as a tab in existing admin structure

**Rule:** ALWAYS investigate existing infrastructure BEFORE implementing. Integrate, don't create parallel systems.

---

### HIGH: MyBB DOES Support Database Transactions
**Date:** 2026-01-21
**Context:** invite_form_import_export

Initial research incorrectly claimed "no transaction support," leading to overly complex architecture.

**Reality:** `$db->write_link` is the raw mysqli connection with full transaction support:

```php
$db->write_link->begin_transaction();
try {
    $db->insert_query('table1', $data1);
    $db->insert_query('table2', $data2);
    $db->write_link->commit();
} catch (Exception $e) {
    $db->write_link->rollback();
    throw $e;
}
```

**Impact:** Using native transactions is 2-4 hours simpler than manual backup/restore.

---

### HIGH: Schema Mismatches Hide in Old Code
**Date:** 2026-01-21
**Context:** invite_email_system

Code can reference database columns that don't exist. MyBB's database wrapper sometimes fails silently.

**What happened:**
- Code inserted `status`, `tracking_token` fields
- Actual schema didn't have these columns
- Silent failures, data corruption

**Prevention:**
```sql
-- Always verify schema first
DESCRIBE invite_emails;
```

Or use `mybb_db_query("DESCRIBE table_name")` via MCP.

---

### HIGH: Language Validators Have 85%+ False Positive Rate
**Date:** 2026-01-20
**Context:** invite_lang_audit

`mybb_lang_validate` reports "unused" strings that ARE actually used in:
- Admin CP modules (not scanned)
- Templates via `{$lang->key}` syntax
- Dynamic patterns like `$lang->$variable_name`

**What happened:**
- Validator reported 349 unused strings
- Manual review revealed ~300 false positives
- Only 17 were truly safe to remove

**Rule:** Always manually verify before removing language strings. Test Admin CP, templates, and all feature areas.

---

### HIGH: Parallel Coders Must Not Share Files
**Date:** 2026-01-18
**Context:** cortex-audit

When running parallel coders, ensure zero file overlap.

**Safe parallelization:**
```
Coder A: SecurityPolicy.php
Coder B: Parser.php
Coder C: Cache.php
✓ No overlaps → safe to run in parallel
```

**Unsafe:**
```
Coder A: SecurityPolicy.php (add constructor)
Coder B: SecurityPolicy.php (add factory method)
✗ Same file → merge conflicts, lost work
```

---

### MEDIUM: PCRE Regex Patterns Need Delimiters
**Date:** 2026-01-21
**Context:** invite_form_import_export

PHP's `preg_match()` requires delimiters around patterns:

```php
// VALID
preg_match('/^[a-z]+$/', $test);

// INVALID - will fail
preg_match('^[a-z]+$', $test);
```

When importing JSON with regex patterns, validate they include delimiters (`/pattern/`, `#pattern#`, etc.).

---

### MEDIUM: Config Options Must Be Tested for Actual Enforcement
**Date:** 2026-01-18
**Context:** cortex-audit

Configuration options might appear implemented but not actually work.

**What happened:**
- Cortex config defined `additional_allowed_functions`
- cortex_init() passed values to SecurityPolicy
- But SecurityPolicy had NO constructor to accept them
- Config values silently ignored

**Prevention:** Trace config from loading → component initialization → actual usage. Test that the config actually affects behavior.

---

## MyBB Template System (CRITICAL UNDERSTANDING)

### How Standard MyBB Plugins Handle Templates
**Date:** 2026-01-22
**Context:** Understanding template lifecycle for SPEC_01

**Standard MyBB approach:** Templates are **embedded as PHP strings** in `_activate()` and inserted into the database:

```php
function myplugin_activate() {
    global $db;

    $templates = array(
        'myplugin_page' => '<div class="page">{$content}</div>',
        'myplugin_row' => '<tr><td>{$data}</td></tr>'
    );

    foreach($templates as $title => $template) {
        $db->insert_query('templates', array(
            'title' => $title,
            'template' => $db->escape_string($template),
            'sid' => -2,  // Master template
            'version' => '',
            'dateline' => TIME_NOW
        ));
    }
}

function myplugin_deactivate() {
    global $db;
    $db->delete_query('templates', "title LIKE 'myplugin_%'");
}
```

**Key points:**
- Templates live in PHP code as strings
- Inserted to `mybb_templates` table on activate
- Deleted from DB on deactivate
- `sid = -2` means master template (base for all themes)

---

### How MyBB Playground Plugins Handle Templates
**Date:** 2026-01-22
**Context:** Understanding our disk-based workflow

**Playground approach:** Templates live as .html files in the plugin folder. The **plugin itself** reads them during `_activate()`:

```
inc/plugins/my_plugin/
├── my_plugin.php
└── templates/
    ├── my_plugin_page.html
    └── my_plugin_row.html
```

```php
// In the plugin's own _activate() function:
function my_plugin_activate() {
    global $db;

    $template_dir = MYBB_ROOT . 'inc/plugins/my_plugin/templates/';
    foreach (glob($template_dir . '*.html') as $file) {
        $title = pathinfo($file, PATHINFO_FILENAME);
        $content = file_get_contents($file);
        $db->insert_query('templates', array(
            'title' => $title,
            'template' => $db->escape_string($content),
            'sid' => -2,
            'dateline' => TIME_NOW
        ));
    }
}
```

**Key point:** The plugin reads its own template files. No special MCP magic. Standard MyBB plugin behavior, just loading from files instead of embedded strings.

---

### Disk Sync System (Separate from Plugin Templates)
**Date:** 2026-01-22
**Context:** Understanding the two template workflows

The **disk sync system** (`mybb_sync/`) is for editing **core/theme templates**, NOT plugin templates:

```
mybb_sync/
├── template_sets/
│   └── Default Templates/
│       └── header.html      ← Core MyBB templates
└── themes/
    └── Default/
        └── global.css       ← Theme stylesheets
```

- `mybb_sync_export_templates()` exports core templates to disk
- `mybb_sync_start_watcher()` watches for changes and syncs to DB
- This is for editing templates that already exist in MyBB

**Plugin templates** live in the plugin folder and are handled by the plugin itself.

---

### Workspace Structure Mirrors MyBB
**Date:** 2026-01-22
**Context:** Plugin import/export planning

The workspace structure should **mirror the deployed MyBB structure** so deployment is just copying:

```
plugin_manager/plugins/public/my_plugin/    # Isolated workspace
├── meta.json                                # Playground metadata
├── inc/
│   ├── plugins/
│   │   └── my_plugin/                       # Plugin folder
│   │       ├── my_plugin.php                # Main file
│   │       ├── src/                         # Classes (optional)
│   │       └── templates/                   # OUR disk templates
│   │           └── my_plugin_page.html
│   ├── languages/
│   │   └── english/
│   │       └── my_plugin.lang.php
│   └── tasks/
│       └── my_plugin_task.php
├── jscripts/
│   └── my_plugin.js
└── admin/
    └── modules/
        └── tools/
            └── my_plugin_admin.php
```

**Deploy = copy workspace contents to TestForum** (minus meta.json)
**Import = copy external plugin into workspace + generate meta.json**
**Export = zip contents with Upload/ wrapper**

No transformation needed because structure already matches.

---

## Add Your Learnings Below

When you discover something useful, add it here with:
- **Date:** When you learned it
- **Context:** What you were working on
- A clear explanation of the learning
- Code examples if applicable

---
