# MCP Tools Quick Reference

A curated list of the most useful MCP tools for MyBB development. For full parameter documentation, see [docs/wiki/mcp_tools/](../../../docs/wiki/mcp_tools/index.md).

**Update this file** when you discover useful tool patterns or combinations.

---

## Plugin Tools (Most Used)

| Tool | Purpose | Example |
|------|---------|---------|
| `mybb_create_plugin` | Scaffold new plugin in workspace | `mybb_create_plugin(codename="karma", name="Karma System", hooks=["postbit"])` |
| `mybb_plugin_install` | Deploy workspace → TestForum + run PHP lifecycle | `mybb_plugin_install("karma")` |
| `mybb_plugin_uninstall` | Remove from TestForum, optionally run _uninstall | `mybb_plugin_uninstall("karma", uninstall=True, remove_files=True)` |
| `mybb_plugin_status` | Check installation state, compatibility, info | `mybb_plugin_status("karma")` |
| `mybb_analyze_plugin` | Inspect hooks, settings, templates used | `mybb_analyze_plugin("karma")` |
| `mybb_plugin_is_installed` | Quick boolean check | `mybb_plugin_is_installed("karma")` |

### Plugin Lifecycle Pattern
```python
# Create → Edit → Deploy
mybb_create_plugin(codename="my_plugin", name="My Plugin", description="Does stuff")
# ... edit files in plugin_manager/plugins/public/my_plugin/ ...
mybb_plugin_install("my_plugin")

# Update templates (requires full cycle)
mybb_plugin_uninstall("my_plugin", remove_files=True)
mybb_plugin_install("my_plugin")
```

---

## Template Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `mybb_list_templates` | Find templates by sid or search term | `mybb_list_templates(search="postbit", sid=-2)` |
| `mybb_read_template` | Get template HTML content | `mybb_read_template("postbit")` |
| `mybb_template_batch_read` | Read multiple templates at once | `mybb_template_batch_read(templates=["postbit", "header"])` |
| `mybb_list_template_sets` | List all template sets (themes) | `mybb_list_template_sets()` |
| `mybb_template_find_replace` | Find/replace across templates | `mybb_template_find_replace(title="postbit", find="pattern", replace="new")` |

### Template sid Values
- `sid=-2` → Master templates (base)
- `sid=-1` → Global templates
- `sid>=1` → Theme-specific overrides

---

## Disk Sync Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `mybb_sync_export_templates` | Export DB templates to disk | `mybb_sync_export_templates("Default Templates")` |
| `mybb_sync_export_stylesheets` | Export DB stylesheets to disk | `mybb_sync_export_stylesheets("Default")` |
| `mybb_sync_start_watcher` | Start auto-sync from disk to DB | `mybb_sync_start_watcher()` |
| `mybb_sync_stop_watcher` | Stop the file watcher | `mybb_sync_stop_watcher()` |
| `mybb_sync_status` | Check watcher state | `mybb_sync_status()` |

### Disk Sync Workflow
```python
# One-time export
mybb_sync_export_templates("Default Templates")

# Development session
mybb_sync_start_watcher()
# ... edit files in mybb_sync/template_sets/ ...
# Changes auto-sync to database
mybb_sync_stop_watcher()
```

---

## Server Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `mybb_server_start` | Start PHP dev server | `mybb_server_start()` or `mybb_server_start(port=8022)` |
| `mybb_server_stop` | Stop the server | `mybb_server_stop()` |
| `mybb_server_status` | Check if running, get port/PID | `mybb_server_status()` |
| `mybb_server_logs` | Query PHP/HTTP logs | `mybb_server_logs(errors_only=True, limit=50)` |
| `mybb_server_restart` | Stop + start | `mybb_server_restart()` |

### Debugging with Logs
```python
# All errors
mybb_server_logs(errors_only=True)

# Recent errors only
mybb_server_logs(errors_only=True, since_minutes=5)

# Search for keyword
mybb_server_logs(filter_keyword="Fatal")

# Pagination for large logs
mybb_server_logs(offset=50, limit=50)
```

---

## Hook Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `mybb_list_hooks` | Search documented hooks | `mybb_list_hooks(search="postbit")` |
| `mybb_hooks_discover` | Scan PHP files for actual hooks | `mybb_hooks_discover(search="postbit")` |
| `mybb_hooks_usage` | Find where a hook is used in plugins | `mybb_hooks_usage("postbit")` |

### Finding the Right Hook
```python
# Start with documented hooks
mybb_list_hooks(category="showthread")

# Then check actual codebase
mybb_hooks_discover(path="showthread.php")

# See how other plugins use it
mybb_hooks_usage("postbit")
```

---

## Content Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `mybb_forum_list` | List all forums | `mybb_forum_list()` |
| `mybb_thread_list` | List threads in forum | `mybb_thread_list(fid=2, limit=10)` |
| `mybb_post_list` | List posts in thread | `mybb_post_list(tid=1)` |
| `mybb_thread_create` | Create test thread | `mybb_thread_create(fid=2, subject="Test", message="Content")` |
| `mybb_search_posts` | Search post content | `mybb_search_posts(query="keyword")` |

---

## Database Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `mybb_db_query` | Read-only SQL query | `mybb_db_query("SELECT * FROM mybb_users LIMIT 5")` |
| `mybb_setting_get` | Get a setting value | `mybb_setting_get("bbname")` |
| `mybb_setting_set` | Update a setting | `mybb_setting_set("bbname", "My Forum")` |
| `mybb_cache_rebuild` | Clear/rebuild cache | `mybb_cache_rebuild("all")` |

---

## Language Validation Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `mybb_lang_validate` | Check for missing/unused definitions | `mybb_lang_validate("my_plugin")` |
| `mybb_lang_generate_stub` | Generate placeholder definitions | `mybb_lang_generate_stub("my_plugin")` |
| `mybb_lang_scan_usage` | Scan files for $lang->x usage | `mybb_lang_scan_usage(path="plugin_manager/plugins/public/my_plugin")` |

---

## Git Tools (Plugin Repos)

| Tool | Purpose | Example |
|------|---------|---------|
| `mybb_plugin_git_init` | Initialize git in plugin dir | `mybb_plugin_git_init(codename="karma", visibility="private")` |
| `mybb_plugin_git_status` | Check git status | `mybb_plugin_git_status(codename="karma")` |
| `mybb_plugin_git_commit` | Commit changes | `mybb_plugin_git_commit(codename="karma", message="Add feature")` |
| `mybb_plugin_github_create` | Create GitHub repo | `mybb_plugin_github_create(codename="karma", repo_visibility="private")` |

---

## Tool Patterns to Add

When you discover a useful tool combination or pattern, add it here:

```python
# Example pattern name
# Description of when to use it
tool_call_1(...)
tool_call_2(...)
```

---
