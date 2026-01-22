---
name: mybb-dev
description: MyBB plugin and theme development using the MCP toolkit. Use when creating plugins, editing templates, working with MyBB forums, or when the user mentions MyBB, plugins, templates, hooks, or forum development.
---

# MyBB Development Skill

This skill teaches you how to develop MyBB plugins and themes using the MyBB Playground toolkit. The system provides 100+ MCP tools, a Plugin Manager workflow, and disk-based template sync.

**This is a living skill.** When you learn something new about MyBB development, update the companion files:
- `LEARNINGS.md` — Add discoveries, gotchas, and tips
- `QUICK_REFERENCE.md` — Add useful tool patterns
- `LINKS.md` — Add relevant documentation links
- `CORTEX.md` — Cortex template syntax reference (conditionals, expressions, security)

## The Three Pillars

Everything in this system revolves around three core concepts:

### 1. Plugin Manager Workflow
**Never create plugin files manually.** Always use:
```
mybb_create_plugin(codename, name, description, ...) → Creates workspace
mybb_plugin_install(codename) → Deploys to TestForum + runs PHP lifecycle
```

The workspace (`plugin_manager/plugins/public/` or `private/`) is the source of truth. TestForum is just the deploy target.

### 2. Disk Sync for Templates
**Edit templates on disk, not in the database.** The file watcher syncs automatically:
```
mybb_sync/template_sets/Default Templates/*.html → Database
mybb_sync/themes/Default/*.css → Database
```

Export first if templates don't exist on disk:
```
mybb_sync_export_templates("Default Templates")
```

### 3. Scribe Logging Discipline
**Log every significant action** with reasoning:
```python
append_entry(
    message="What you did",
    status="success",  # info|success|warn|error|bug|plan
    agent="Claude",
    meta={"reasoning": {"why": "...", "what": "...", "how": "..."}}
)
```

If it's not logged, it didn't happen.

---

## Essential Workflows

### Creating a New Plugin

```python
# 1. Create the plugin scaffold
mybb_create_plugin(
    codename="my_plugin",
    name="My Plugin",
    description="What it does",
    hooks=["global_start", "postbit"],
    has_settings=True,
    has_templates=True,
    has_database=False
)

# 2. Edit the PHP file in workspace
# plugin_manager/plugins/public/my_plugin/my_plugin.php

# 3. Deploy to TestForum (runs _install + _activate)
mybb_plugin_install("my_plugin")

# 4. Test in browser at http://localhost:8022
```

### Updating Plugin Templates

**Critical:** `mybb_plugin_install()` alone does NOT update existing templates.

```python
# Full reinstall cycle required for template changes:
mybb_plugin_uninstall(codename="my_plugin", remove_files=True)
mybb_plugin_install(codename="my_plugin")
```

### Editing Core Templates (Without a Plugin)

```python
# 1. Export templates to disk (if not already)
mybb_sync_export_templates("Default Templates")

# 2. Start the watcher
mybb_sync_start_watcher()

# 3. Edit files in mybb_sync/template_sets/Default Templates/
# The watcher auto-syncs changes to database
# Use Cortex syntax for conditionals/expressions - see CORTEX.md

# 4. When done, stop watcher
mybb_sync_stop_watcher()
```

**Template Syntax:** Templates support Cortex enhanced syntax. See [CORTEX.md](CORTEX.md) for conditionals (`<if>...</if>`), expressions (`{= ... }`), and allowed functions.

### Debugging a Problem

```python
# 1. Check server logs for PHP errors
mybb_server_logs(errors_only=True, limit=50)

# 2. Check plugin status
mybb_plugin_status("my_plugin")

# 3. Check if plugin is installed
mybb_plugin_is_installed("my_plugin")

# 4. Analyze plugin structure
mybb_analyze_plugin("my_plugin")

# 5. List hooks to find the right one
mybb_list_hooks(search="postbit")
mybb_hooks_discover(search="postbit")
```

### Adding Settings to a Plugin

Settings are created in `_install()` and removed in `_uninstall()`:

```php
// In _install():
$setting_group = array(
    'name' => 'myplugin_settings',
    'title' => 'My Plugin Settings',
    'description' => 'Settings for My Plugin',
    'disporder' => 1,
    'isdefault' => 0
);
$gid = $db->insert_query("settinggroups", $setting_group);

$setting = array(
    'name' => 'myplugin_enabled',
    'title' => 'Enable Plugin',
    'description' => 'Turn this plugin on or off',
    'optionscode' => 'yesno',
    'value' => '1',
    'disporder' => 1,
    'gid' => $gid
);
$db->insert_query("settings", $setting);
rebuild_settings();
```

---

## Forbidden Operations

### Absolutely Banned
- **`rm -rf`** — Never. Ask user for confirmation before any recursive delete.
- **Editing TestForum/ core files** — Use plugins/templates instead.
- **Creating `*_v2` or `enhanced_*` files** — Fix the original, don't fork.
- **Delete-and-recreate as a fix** — Investigate root cause first.

### Why These Matter
- TestForum files get overwritten on MyBB upgrades
- Forked files create maintenance nightmares
- Deleting without understanding hides the real problem

### When You Think Something's Broken
1. Read the error message carefully
2. Check `mybb_server_logs(errors_only=True)`
3. Verify the plugin exists: `mybb_plugin_status(codename)`
4. Check the workspace files exist
5. **Ask the user** before taking destructive action

---

## Decision Framework

**"I need to..."**

| Goal | Approach |
|------|----------|
| Create a plugin | `mybb_create_plugin()` → edit workspace → `mybb_plugin_install()` |
| Edit a template | Export to disk → edit in `mybb_sync/` → watcher syncs |
| Add plugin templates | Create in `workspace/templates/` → full reinstall cycle |
| Debug PHP errors | `mybb_server_logs(errors_only=True)` |
| Find the right hook | `mybb_list_hooks(search="...")` or `mybb_hooks_discover()` |
| Check plugin state | `mybb_plugin_status(codename)` |
| Modify core behavior | Create a plugin with hooks (never edit core) |
| Add admin settings | Use `_install()` with settings API |
| Test in browser | Server at http://localhost:8022, Admin at /admin/ (admin/admin) |

**"Something seems wrong..."**

| Symptom | First Steps |
|---------|-------------|
| Templates not updating | Did you do full reinstall cycle? Check watcher status. |
| Plugin not found | Check workspace exists, check `mybb_plugin_status()` |
| Hook not firing | Verify hook name with `mybb_hooks_discover()`, check function name matches |
| PHP errors | `mybb_server_logs(errors_only=True)` |
| Database errors | Check table prefix, verify connection in `.env` |

---

## Template Inheritance (sid Values)

Understanding `sid` is crucial for template operations:

| sid | Meaning | Use Case |
|-----|---------|----------|
| -2 | Master templates | Base templates, never delete |
| -1 | Global templates | Shared across all themes |
| 1+ | Template set overrides | Theme-specific customizations |

When reading templates:
```python
mybb_read_template("postbit")  # Checks master and custom
mybb_read_template("postbit", sid=1)  # Specific template set
```

---

## Plugin Lifecycle

Two separate concerns:

| Phase | Functions | What It Does |
|-------|-----------|--------------|
| **Install/Uninstall** | `_install()`, `_uninstall()`, `_is_installed()` | Database setup/teardown (settings, tables) |
| **Activate/Deactivate** | `_activate()`, `_deactivate()` | Template injection, hook wiring |

**Full lifecycle for deployment:**
```python
mybb_plugin_install(codename)  # Runs _install() then _activate()
mybb_plugin_uninstall(codename, uninstall=True)  # Runs _deactivate() then _uninstall()
```

---

## Confidence Scoring

When reporting findings, rate your confidence:

| Score | Meaning | Example |
|-------|---------|---------|
| 0.95 | Verified by direct code inspection | "Found in server.py:142" |
| 0.85 | Observed from multiple patterns | "Architecture consistent across 5 files" |
| 0.70 | Based on documented behavior | "Wiki says X, assuming accurate" |
| 0.50 | Unverified assumption | "Might work this way, need to test" |

---

## MCP Tools Quick Reference

See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for the full list. Most common:

**Plugin Operations:**
- `mybb_create_plugin` — Scaffold a new plugin
- `mybb_plugin_install` — Deploy and activate
- `mybb_plugin_uninstall` — Remove and cleanup
- `mybb_plugin_status` — Check current state
- `mybb_analyze_plugin` — Inspect structure

**Template Operations:**
- `mybb_list_templates` — Find templates by name/sid
- `mybb_read_template` — Get template content
- `mybb_sync_export_templates` — Export to disk
- `mybb_sync_start_watcher` — Enable auto-sync

**Server Operations:**
- `mybb_server_start` — Start PHP dev server
- `mybb_server_status` — Check if running
- `mybb_server_logs` — Query PHP/HTTP logs

---

## Maintaining This Skill

**This skill should grow with the project.** When you discover something useful:

1. **New gotcha or tip?** → Add to [LEARNINGS.md](LEARNINGS.md)
2. **Useful tool pattern?** → Add to [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. **Found good documentation?** → Add to [LINKS.md](LINKS.md)

**Update triggers:**
- Solved a tricky problem → Document the solution
- Found an undocumented behavior → Record it
- Created a useful code pattern → Save it for reuse
- Discovered a pitfall → Warn future Claude

---

## Further Learning

**Comprehensive References:**
- [CLAUDE.md](../../../CLAUDE.md) — Full project instructions (900+ lines)
- [AGENTS.md](../../../AGENTS.md) — Operational framework and constraints

**Wiki Documentation:**
- [MCP Tools Reference](../../../docs/wiki/mcp_tools/index.md) — All 100+ tools with parameters
- [Plugin Manager Guide](../../../docs/wiki/plugin_manager/index.md) — Workspace and deployment
- [Best Practices](../../../docs/wiki/best_practices/index.md) — Development patterns

**Specialized Agents:**
When you need deep expertise, delegate to:
- `mybb-research-analyst` — Investigate codebases with MCP tools
- `mybb-architect` — Design plugin/theme architecture
- `mybb-coder` — Implement following Plugin Manager workflow
- `mybb-bug-hunter` — Debug MyBB-specific issues
