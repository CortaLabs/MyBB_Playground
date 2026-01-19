# Architecture Guide - MyBB Forge v2

**Author:** MyBB-ArchitectAgent
**Version:** v1.0
**Status:** Complete
**Last Updated:** 2026-01-19
**Confidence:** 0.92

> Complete system architecture for MyBB Forge v2 - a major refactoring of MyBB Playground to enable optimized multi-agent development, disk-first plugin templates, and modular MCP server architecture.

---

## 1. Problem Statement
<!-- ID: problem_statement -->

### Context

MyBB Playground is a functional AI-assisted MyBB development toolkit with 85+ MCP tools. However, several pain points limit its effectiveness:

1. **Plugin Template Management**: Templates are created by PHP lifecycle functions, not tracked as files. Agents editing templates get overwritten on deployment.
2. **Monolithic MCP Server**: `server.py` is 3,794 lines with a single 2,642-line if-elif handler chain - difficult to maintain and test.
3. **No Private Repository Strategy**: No clean way to manage proprietary plugins/themes alongside open source work.
4. **Manifest Tracking Gap**: Deployment manifest exists in SQLite but not in `meta.json` - can drift out of sync.
5. **DB-Sync Latency**: 0.5s debounce per file creates noticeable delay; no request batching.
6. **Direct SQL in MCP Tools**: 4 operations bypass the wrapper layer, risking inconsistency.

### Goals

- **Plugin Architecture v2**: Disk-first templates, embedded manifest in meta.json, consistent directory structure
- **Configuration System**: YAML config + .env secrets for developer metadata and subtree remotes
- **Git Subtree Integration**: Clean workflow for private repo management without submodule complexity
- **Server Modularization**: Split 3,794-line server.py into 12 focused handler modules
- **DB-Sync Optimization**: Reduce perceived latency to sub-100ms with smart batching
- **MCP Tool Hygiene**: Eliminate direct SQL, add missing bulk update methods

### Non-Goals

- Git worktrees for parallel agents (research R1 concluded database sharing makes this impractical)
- Theme development workflow overhaul (future project)
- MyBB core modifications

### Success Metrics

- All 85+ MCP tools continue functioning after modularization
- Plugin templates can be version-controlled and edited on disk
- New plugins auto-populated with developer info from YAML config
- Private plugins push to separate repos via single command
- DB-sync feels instant (<100ms perceived latency)
- Zero direct SQL in MCP handlers

---

## 2. Requirements & Constraints
<!-- ID: requirements_constraints -->

### Functional Requirements

| Requirement | Source | Priority |
|-------------|--------|----------|
| Disk-first template management for plugins | REQUIREMENTS_BRIEF | P0 |
| Manifest embedded in meta.json | R2 Finding | P0 |
| YAML config for developer defaults | R7 / User Request | P1 |
| Git subtree MCP tools | R1 Recommendation | P1 |
| Server handler modularization | R6 Finding | P1 |
| Debounce reduction with batching | R4 Finding | P2 |
| Bulk post update wrapper methods | R3 Finding | P2 |

### Non-Functional Requirements

- **Backward Compatibility**: All existing MCP tool names, signatures, and return formats preserved
- **Open Source Ready**: No hardcoded organization names; all config is user-configurable
- **Graceful Degradation**: System works without config files (uses defaults)
- **Testability**: Handler modules independently unit-testable

### Assumptions

- Python 3.10+ runtime available
- PyYAML and python-dotenv available (verified in dependencies)
- Single-agent operation (worktrees rejected due to DB sharing)
- TestForum is local development environment

### Constraints

- MyBB 1.8.x architecture constraints (hooks, template inheritance, datacache)
- FastMCP Server interface requirements
- Existing plugin_manager SQLite schema

### Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Handler extraction breaks tool routing | High | Phased migration with integration tests after each phase |
| Config changes break existing setups | Medium | Optional config files, graceful defaults |
| Template disk/DB sync conflicts | Medium | Clear source-of-truth: disk is canonical, DB is derived |
| Git subtree history pollution | Low | Use --squash flag for clean commits |

---

## 3. Architecture Overview
<!-- ID: architecture_overview -->

### System Context Diagram

```
+------------------+     +------------------+     +------------------+
|   Claude Code    |     |   Developer      |     |   Git Remote     |
|   (AI Agent)     |     |   (Human)        |     |   (Private)      |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        ^
         | MCP Protocol           | File Edits             | git subtree push
         v                        v                        |
+------------------------------------------------------------------------+
|                         MyBB Forge v2                                   |
|  +------------------+  +------------------+  +------------------+        |
|  | MCP Server       |  | Plugin Manager   |  | DB-Sync Service  |       |
|  | (Modularized)    |  | (Manifest-aware) |  | (Optimized)      |       |
|  +------------------+  +------------------+  +------------------+        |
|         |                      |                      |                 |
|         +----------------------+----------------------+                 |
|                                |                                        |
|                    +-----------v-----------+                            |
|                    |   MySQL Database      |                            |
|                    |   (MyBB tables)       |                            |
|                    +-----------------------+                            |
+------------------------------------------------------------------------+
         |
         v
+------------------+
|   TestForum      |
|   (MyBB 1.8.x)   |
+------------------+
```

### Component Breakdown

#### 3.1 MCP Server (Modularized)

**Purpose**: Expose 85+ tools to Claude Code via MCP protocol

**Structure After Modularization**:
```
mybb_mcp/mybb_mcp/
├── server.py              # ~150 lines (init + dispatcher call)
├── tools_registry.py      # ~1,080 lines (all tool definitions)
├── config.py              # Configuration (unchanged)
├── handlers/
│   ├── __init__.py
│   ├── dispatcher.py      # Dictionary-based routing (~50 lines)
│   ├── common.py          # Shared utilities (markdown formatters)
│   ├── templates.py       # 9 template handlers
│   ├── themes.py          # 6 theme/stylesheet handlers
│   ├── plugins.py         # 12 plugin handlers (lifecycle included)
│   ├── tasks.py           # 6 scheduled task handlers
│   ├── content.py         # 17 content CRUD handlers
│   ├── sync.py            # 5 disk sync handlers
│   ├── search.py          # 4 search handlers
│   ├── admin.py           # 11 admin/cache handlers
│   ├── moderation.py      # 8 moderation handlers
│   ├── users.py           # 7 user management handlers
│   └── database.py        # 1 database query handler
├── db/                    # Database abstraction (unchanged)
├── sync/                  # Disk sync (optimized)
└── tools/                 # Plugin scaffolding (unchanged)
```

#### 3.2 Plugin Manager (Manifest-Aware)

**Purpose**: Manage plugin workspace, deployment, and lifecycle

**Key Changes**:
- `meta.json` gains embedded manifest with file hashes
- Templates directory added to plugin workspace
- Deployment reads templates from disk, inserts to DB
- Uninstall uses manifest for complete cleanup

**New Workspace Structure**:
```
plugin_manager/plugins/{public,private}/{codename}/
├── meta.json                    # Enhanced with manifest
├── README.md
├── inc/
│   └── plugins/
│       ├── {codename}.php       # Main entry (lean loader)
│       └── {codename}/          # Plugin internals
│           ├── src/             # PHP classes
│           ├── admin/           # Admin CP modules
│           └── handlers/        # Hook handlers
├── templates/                   # NEW: Disk-first templates
│   ├── {codename}_main.html
│   ├── {codename}_row.html
│   └── {codename}_form.html
├── languages/
│   └── english/
│       └── {codename}.lang.php
├── styles/                      # NEW: Plugin stylesheets
│   └── {codename}.css
└── jscripts/                    # Optional JavaScript
```

#### 3.3 Configuration System

**Purpose**: Developer metadata and subtree remote configuration

**Files**:
- `.mybb-forge.yaml` - Structured config (tracked in git)
- `.mybb-forge.env` - Secrets/remotes (gitignored)
- `.mybb-forge.yaml.example` - Template for new users (tracked)
- `.mybb-forge.env.example` - Template for secrets (tracked)

**Location**: Repository root (`/home/austin/projects/MyBB_Playground/`)

#### 3.4 DB-Sync Service (Optimized)

**Purpose**: Sync templates/stylesheets between disk and database

**Optimizations**:
- Reduced debounce: 500ms -> 100ms with smart batching
- Request batching: Group changes within 100ms window
- Template set caching: Avoid redundant lookups
- Async cache refresh: Non-blocking HTTP calls

### Data Flow

#### Plugin Deployment Flow
```
1. Developer edits files in workspace
2. `mybb_plugin_install(codename)` called
3. Plugin Manager reads workspace:
   - Parses meta.json for metadata
   - Scans templates/ directory for .html files
   - Computes file hashes for manifest
4. Files deployed via _overlay_directory()
5. PHP lifecycle executed via bridge:
   - _install() runs (creates DB tables)
   - _activate() runs (inserts templates from manifest)
6. Manifest stored in SQLite + embedded in meta.json
```

#### Template Sync Flow (Disk-First)
```
1. Developer edits template in mybb_sync/template_sets/{set}/
2. File watcher detects change (100ms debounce)
3. Changes batched (group within window)
4. Batch written to database in single transaction
5. Cache refresh triggered asynchronously
```

---

## 4. Detailed Design
<!-- ID: detailed_design -->

### 4.1 Plugin Architecture v2

#### 4.1.1 Enhanced meta.json Schema

```json
{
  "codename": "my_plugin",
  "display_name": "My Plugin",
  "version": "1.0.0",
  "author": "Developer Name",
  "author_website": "https://example.com",
  "description": "Plugin description",
  "mybb_compatibility": "18*",
  "visibility": "public",
  "project_type": "plugin",

  "hooks": [
    {
      "name": "postbit",
      "handler": "my_plugin_postbit",
      "priority": 10
    }
  ],

  "settings": [
    {
      "name": "my_plugin_enabled",
      "title": "Enable Plugin",
      "description": "Enable or disable the plugin",
      "optionscode": "yesno",
      "value": "1",
      "disporder": 1
    }
  ],

  "templates": [
    {
      "name": "my_plugin_main",
      "file": "templates/my_plugin_main.html",
      "group": "my_plugin"
    }
  ],

  "stylesheets": [
    {
      "name": "my_plugin.css",
      "file": "styles/my_plugin.css",
      "attachedto": ""
    }
  ],

  "database_tables": [
    {
      "name": "my_plugin_data",
      "schema": "CREATE TABLE IF NOT EXISTS {PREFIX}my_plugin_data (...)"
    }
  ],

  "manifest": {
    "version": "2.0",
    "generated_at": "2026-01-19T04:30:00Z",
    "files": {
      "inc/plugins/my_plugin.php": {
        "sha512": "abc123...",
        "size": 12345
      },
      "inc/plugins/my_plugin/src/core.php": {
        "sha512": "def456...",
        "size": 5678
      }
    },
    "templates": {
      "my_plugin_main": {
        "file": "templates/my_plugin_main.html",
        "sha512": "ghi789..."
      }
    }
  }
}
```

#### 4.1.2 Template Loading in PHP

The plugin's `_install()` function reads templates from the manifest:

```php
function my_plugin_install() {
    global $db;

    // Read manifest from meta.json
    $meta_path = MYBB_ROOT . 'inc/plugins/my_plugin/meta.json';
    $meta = json_decode(file_get_contents($meta_path), true);

    // Insert templates from disk files
    foreach ($meta['templates'] as $tpl) {
        $template_path = MYBB_ROOT . 'inc/plugins/my_plugin/' . $tpl['file'];
        $content = file_get_contents($template_path);

        $db->insert_query('templates', [
            'title' => $tpl['name'],
            'template' => $db->escape_string($content),
            'sid' => -2,  // Master templates
            'version' => $mybb->version_code,
            'dateline' => TIME_NOW
        ]);
    }
}
```

#### 4.1.3 Clean Uninstall Using Manifest

```php
function my_plugin_uninstall() {
    global $db;

    // Read manifest
    $meta_path = MYBB_ROOT . 'inc/plugins/my_plugin/meta.json';
    $meta = json_decode(file_get_contents($meta_path), true);

    // Remove all tracked templates
    foreach ($meta['templates'] as $tpl) {
        $db->delete_query('templates', "title='".$db->escape_string($tpl['name'])."'");
    }

    // Remove all tracked settings
    foreach ($meta['settings'] as $setting) {
        $db->delete_query('settings', "name='".$db->escape_string($setting['name'])."'");
    }

    // Drop database tables
    foreach ($meta['database_tables'] as $table) {
        $db->drop_table($table['name']);
    }
}
```

### 4.2 Configuration System

#### 4.2.1 YAML Config Schema

```yaml
# .mybb-forge.yaml - Developer configuration (TRACKED in git)

# Developer information - auto-fills plugin metadata
developer:
  name: "Your Name"
  website: "https://example.com"
  email: "you@example.com"

# Default values for new plugins
defaults:
  compatibility: "18*"
  license: "MIT"
  visibility: "public"

# Git subtree mappings
subtrees:
  plugins/private:
    remote_env: PRIVATE_PLUGINS_REMOTE  # References .mybb-forge.env
    branch: main
    squash: true
  themes/private:
    remote_env: PRIVATE_THEMES_REMOTE
    branch: main
    squash: true

# Sync settings
sync:
  debounce_ms: 100
  batch_window_ms: 100
  enable_cache_refresh: true
```

#### 4.2.2 Environment File

```bash
# .mybb-forge.env (GITIGNORED - contains credentials)
PRIVATE_PLUGINS_REMOTE=git@github.com:YourOrg/mybb-private-plugins.git
PRIVATE_THEMES_REMOTE=git@github.com:YourOrg/mybb-private-themes.git
```

#### 4.2.3 Config Loader Implementation

**Location**: `plugin_manager/forge_config.py` (new file)

```python
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from dotenv import dotenv_values

class ForgeConfig:
    """MyBB Forge configuration loader with precedence handling."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.yaml_path = repo_root / ".mybb-forge.yaml"
        self.env_path = repo_root / ".mybb-forge.env"
        self._config: Dict[str, Any] = {}
        self._env: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load config with precedence: env vars > yaml > defaults."""
        # 1. Load defaults
        self._config = self._get_defaults()

        # 2. Merge YAML if exists
        if self.yaml_path.exists():
            with open(self.yaml_path) as f:
                yaml_config = yaml.safe_load(f) or {}
            self._deep_merge(self._config, yaml_config)

        # 3. Load .env file
        if self.env_path.exists():
            self._env = dotenv_values(self.env_path)

    def _get_defaults(self) -> Dict[str, Any]:
        return {
            "developer": {
                "name": "Developer",
                "website": "",
                "email": ""
            },
            "defaults": {
                "compatibility": "18*",
                "license": "GPL-3.0",
                "visibility": "public"
            },
            "subtrees": {},
            "sync": {
                "debounce_ms": 100,
                "batch_window_ms": 100,
                "enable_cache_refresh": True
            }
        }

    @property
    def developer_name(self) -> str:
        return self._config.get("developer", {}).get("name", "Developer")

    @property
    def developer_website(self) -> str:
        return self._config.get("developer", {}).get("website", "")

    def get_subtree_remote(self, subtree_key: str) -> Optional[str]:
        """Get subtree remote URL, resolving env var reference."""
        subtree = self._config.get("subtrees", {}).get(subtree_key, {})
        env_key = subtree.get("remote_env")
        if env_key:
            return self._env.get(env_key)
        return None
```

### 4.3 Git Subtree Integration

#### 4.3.1 MCP Tool Specifications

**New Tools**:

| Tool Name | Parameters | Description |
|-----------|------------|-------------|
| `mybb_subtree_add` | prefix, remote_key, branch | Add subtree from configured remote |
| `mybb_subtree_push` | prefix | Push changes to subtree remote |
| `mybb_subtree_pull` | prefix | Pull updates from subtree remote |
| `mybb_subtree_list` | (none) | List configured subtrees and status |

**Example: mybb_subtree_push**

```python
async def handle_mybb_subtree_push(args: dict, config: ForgeConfig) -> str:
    """Push changes to subtree remote."""
    prefix = args.get("prefix")

    # Get subtree config
    subtree_config = config.get_subtree_config(prefix)
    if not subtree_config:
        return f"Error: No subtree configured for prefix '{prefix}'"

    remote = config.get_subtree_remote(prefix)
    if not remote:
        return f"Error: Remote not configured in .mybb-forge.env"

    branch = subtree_config.get("branch", "main")

    # Execute git subtree push
    cmd = f"git subtree push --prefix={prefix} {remote} {branch}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        return f"Successfully pushed {prefix} to {remote} ({branch})"
    else:
        return f"Error: {result.stderr}"
```

#### 4.3.2 Subtree Workflow Documentation

```markdown
## Adding a Private Plugin Repository

1. Configure remote in `.mybb-forge.env`:
   ```bash
   PRIVATE_PLUGINS_REMOTE=git@github.com:YourOrg/mybb-private-plugins.git
   ```

2. Configure subtree mapping in `.mybb-forge.yaml`:
   ```yaml
   subtrees:
     plugin_manager/plugins/private:
       remote_env: PRIVATE_PLUGINS_REMOTE
       branch: main
       squash: true
   ```

3. Add the subtree (first time only):
   ```
   mybb_subtree_add prefix="plugin_manager/plugins/private" remote_key="plugins/private"
   ```

4. Push changes:
   ```
   mybb_subtree_push prefix="plugin_manager/plugins/private"
   ```

5. Pull updates:
   ```
   mybb_subtree_pull prefix="plugin_manager/plugins/private"
   ```
```

### 4.4 Server Modularization

#### 4.4.1 Dispatcher Pattern

**Location**: `mybb_mcp/mybb_mcp/handlers/dispatcher.py`

```python
from typing import Callable, Dict, Any
from .templates import TEMPLATE_HANDLERS
from .themes import THEME_HANDLERS
from .plugins import PLUGIN_HANDLERS
from .content import CONTENT_HANDLERS
from .users import USER_HANDLERS
from .moderation import MODERATION_HANDLERS
from .admin import ADMIN_HANDLERS
from .search import SEARCH_HANDLERS
from .sync import SYNC_HANDLERS
from .tasks import TASK_HANDLERS
from .database import DATABASE_HANDLERS

# Consolidated handler registry
HANDLER_REGISTRY: Dict[str, Callable] = {
    **TEMPLATE_HANDLERS,
    **THEME_HANDLERS,
    **PLUGIN_HANDLERS,
    **CONTENT_HANDLERS,
    **USER_HANDLERS,
    **MODERATION_HANDLERS,
    **ADMIN_HANDLERS,
    **SEARCH_HANDLERS,
    **SYNC_HANDLERS,
    **TASK_HANDLERS,
    **DATABASE_HANDLERS,
}

async def dispatch_tool(
    name: str,
    args: Dict[str, Any],
    db: "MyBBDatabase",
    config: "MyBBConfig",
    sync_service: "DiskSyncService"
) -> str:
    """Route tool call to appropriate handler."""
    handler = HANDLER_REGISTRY.get(name)
    if not handler:
        return f"Unknown tool: {name}"

    return await handler(args, db, config, sync_service)
```

#### 4.4.2 Handler Module Pattern

**Example**: `mybb_mcp/mybb_mcp/handlers/templates.py`

```python
from typing import Dict, Any, Callable
from ..db.connection import MyBBDatabase
from ..config import MyBBConfig
from .common import format_markdown_table

async def handle_list_template_sets(
    args: Dict[str, Any],
    db: MyBBDatabase,
    config: MyBBConfig,
    sync_service: Any
) -> str:
    """List all template sets."""
    sets = db.list_template_sets()

    lines = ["# Template Sets\n"]
    lines.append("| SID | Name | Default |")
    lines.append("|-----|------|---------|")

    for s in sets:
        default = "Yes" if s.get("def") else "No"
        lines.append(f"| {s['sid']} | {s['title']} | {default} |")

    return "\n".join(lines)

async def handle_read_template(
    args: Dict[str, Any],
    db: MyBBDatabase,
    config: MyBBConfig,
    sync_service: Any
) -> str:
    """Read template content."""
    title = args.get("title")
    sid = args.get("sid")

    # Get master template
    master = db.get_template(title, sid=-2)

    # Get custom template if sid specified
    custom = None
    if sid and sid > 0:
        custom = db.get_template(title, sid=sid)

    # Format response
    lines = [f"# Template: {title}\n"]

    if master:
        lines.append("## Master Template (sid=-2)")
        lines.append("```html")
        lines.append(master.get("template", ""))
        lines.append("```\n")

    if custom:
        lines.append(f"## Custom Template (sid={sid})")
        lines.append("```html")
        lines.append(custom.get("template", ""))
        lines.append("```")

    return "\n".join(lines)

# Handler registry for this module
TEMPLATE_HANDLERS: Dict[str, Callable] = {
    "mybb_list_template_sets": handle_list_template_sets,
    "mybb_list_templates": handle_list_templates,
    "mybb_read_template": handle_read_template,
    "mybb_write_template": handle_write_template,
    "mybb_list_template_groups": handle_list_template_groups,
    "mybb_template_find_replace": handle_template_find_replace,
    "mybb_template_batch_read": handle_template_batch_read,
    "mybb_template_batch_write": handle_template_batch_write,
    "mybb_template_outdated": handle_template_outdated,
}
```

### 4.5 DB-Sync Optimizations

#### 4.5.1 Smart Batching Implementation

**Location**: `mybb_mcp/mybb_mcp/sync/watcher.py` (modified)

```python
class SyncEventHandler(FileSystemEventHandler):
    # Reduced debounce with batching
    DEBOUNCE_SECONDS = 0.1  # 100ms (was 500ms)
    BATCH_WINDOW_SECONDS = 0.1  # 100ms batch collection window

    def __init__(self, ...):
        # ... existing init ...
        self._pending_batch: Dict[str, dict] = {}
        self._batch_timer: Optional[asyncio.TimerHandle] = None

    def _queue_for_batch(self, work_item: dict) -> None:
        """Add item to pending batch instead of immediate queue."""
        key = f"{work_item['type']}:{work_item.get('set_name')}:{work_item.get('template_name')}"
        self._pending_batch[key] = work_item

        # Schedule batch flush if not already scheduled
        if self._batch_timer is None:
            loop = asyncio.get_event_loop()
            self._batch_timer = loop.call_later(
                self.BATCH_WINDOW_SECONDS,
                self._flush_batch
            )

    def _flush_batch(self) -> None:
        """Flush all pending items as a batch."""
        if not self._pending_batch:
            return

        # Submit batch to work queue
        self.work_queue.put_nowait({
            "type": "batch",
            "items": list(self._pending_batch.values())
        })

        self._pending_batch.clear()
        self._batch_timer = None
```

#### 4.5.2 Template Set Caching

```python
class TemplateImporter:
    def __init__(self, db: MyBBDatabase):
        self.db = db
        self._set_cache: Dict[str, int] = {}  # name -> sid
        self._cache_ttl = 300  # 5 minutes
        self._cache_time: float = 0

    def _get_template_set_id(self, set_name: str) -> Optional[int]:
        """Get template set ID with caching."""
        now = time.time()

        # Invalidate cache if expired
        if now - self._cache_time > self._cache_ttl:
            self._set_cache.clear()
            self._cache_time = now

        # Return cached value if available
        if set_name in self._set_cache:
            return self._set_cache[set_name]

        # Fetch from database and cache
        template_set = self.db.get_template_set_by_name(set_name)
        if template_set:
            self._set_cache[set_name] = template_set["sid"]
            return template_set["sid"]

        return None
```

### 4.6 MCP Tool Fixes

#### 4.6.1 Direct SQL Replacement

| Line | Current Code | Replacement |
|------|--------------|-------------|
| 1246 | Direct SELECT from templategroups | `db.list_template_groups()` (exists) |
| 2909 | `UPDATE posts SET tid` | New `db.update_post_field(pid, "tid", value)` |
| 2992 | `UPDATE posts SET fid WHERE tid` | New `db.update_posts_by_thread(tid, fid=new_fid)` |

#### 4.6.2 New Wrapper Methods

**Location**: `mybb_mcp/mybb_mcp/db/connection.py` (additions)

```python
def update_post_field(self, pid: int, field: str, value: Any) -> bool:
    """Update a single field on a post.

    Args:
        pid: Post ID
        field: Field name to update
        value: New value

    Returns:
        True if updated successfully
    """
    allowed_fields = {"tid", "fid", "visible", "message", "subject"}
    if field not in allowed_fields:
        raise ValueError(f"Field '{field}' not allowed for update")

    with self.cursor() as cur:
        cur.execute(
            f"UPDATE {self.table('posts')} SET {field} = %s WHERE pid = %s",
            (value, pid)
        )
        return cur.rowcount > 0

def update_posts_by_thread(self, tid: int, **fields) -> int:
    """Update all posts in a thread.

    Args:
        tid: Thread ID
        **fields: Field=value pairs to update

    Returns:
        Number of rows updated
    """
    if not fields:
        return 0

    allowed_fields = {"fid", "visible"}
    for field in fields:
        if field not in allowed_fields:
            raise ValueError(f"Field '{field}' not allowed for bulk update")

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [tid]

    with self.cursor() as cur:
        cur.execute(
            f"UPDATE {self.table('posts')} SET {set_clause} WHERE tid = %s",
            tuple(values)
        )
        return cur.rowcount
```

---

## 5. Directory Structure
<!-- ID: directory_structure -->

### Repository Structure After v2

```
/home/austin/projects/MyBB_Playground/
├── .mybb-forge.yaml              # NEW: Developer config
├── .mybb-forge.env               # NEW: Secrets (gitignored)
├── .mybb-forge.yaml.example      # NEW: Config template
├── .mybb-forge.env.example       # NEW: Secrets template
├── CLAUDE.md                     # Project instructions
├── AGENTS.md                     # Agent governance
│
├── mybb_mcp/
│   └── mybb_mcp/
│       ├── server.py             # MODIFIED: ~150 lines (init + dispatch)
│       ├── tools_registry.py     # NEW: Tool definitions (~1,080 lines)
│       ├── config.py             # Unchanged
│       ├── handlers/             # NEW: Handler modules
│       │   ├── __init__.py
│       │   ├── dispatcher.py     # Dictionary-based routing
│       │   ├── common.py         # Shared utilities
│       │   ├── templates.py      # 9 handlers
│       │   ├── themes.py         # 6 handlers
│       │   ├── plugins.py        # 12 handlers
│       │   ├── content.py        # 17 handlers
│       │   ├── users.py          # 7 handlers
│       │   ├── moderation.py     # 8 handlers
│       │   ├── admin.py          # 11 handlers
│       │   ├── search.py         # 4 handlers
│       │   ├── sync.py           # 5 handlers
│       │   ├── tasks.py          # 6 handlers
│       │   ├── database.py       # 1 handler
│       │   └── subtrees.py       # NEW: 4 git subtree handlers
│       ├── db/
│       │   └── connection.py     # MODIFIED: +2 bulk update methods
│       └── sync/
│           └── watcher.py        # MODIFIED: Smart batching
│
├── plugin_manager/
│   ├── forge_config.py           # NEW: YAML+ENV config loader
│   ├── manager.py                # MODIFIED: Uses ForgeConfig
│   ├── installer.py              # MODIFIED: Template disk loading
│   ├── database.py               # Unchanged
│   └── plugins/
│       ├── public/
│       │   └── {codename}/
│       │       ├── meta.json     # MODIFIED: Manifest embedded
│       │       ├── templates/    # NEW: Disk-first templates
│       │       ├── styles/       # NEW: Plugin stylesheets
│       │       └── ...
│       └── private/              # Git subtree target
│
├── TestForum/                    # MyBB installation
│   ├── mcp_bridge.php            # PHP bridge (unchanged)
│   └── inc/plugins/              # Deployed plugins
│
└── mybb_sync/                    # Disk sync source-of-truth
    ├── template_sets/
    └── styles/
```

---

## 6. Data & Storage
<!-- ID: data_storage -->

### Datastores

| Store | Type | Purpose |
|-------|------|---------|
| MySQL (MyBB) | Relational | Templates, stylesheets, settings, posts, users |
| SQLite (Plugin Manager) | Embedded | Deployment manifest, project tracking |
| Filesystem (YAML) | Config | Developer settings, subtree mappings |
| Filesystem (Templates) | Source | Plugin templates (disk-first) |

### Manifest Storage

**Dual Storage Strategy** (per R2 finding):

1. **SQLite** (`plugin_manager/.meta/projects.db`): Runtime manifest with full deployment metadata
2. **meta.json** (in workspace): Embedded manifest for version control and portability

Both are kept in sync during deployment operations.

### Cache Strategy

| Cache | Location | TTL | Invalidation |
|-------|----------|-----|--------------|
| Template Set IDs | TemplateImporter memory | 5 min | Time-based |
| Config Files | ForgeConfig memory | Session | On-demand reload |
| MyBB datacache | MySQL table | Varies | `$cache->update()` |

---

## 7. Testing & Validation Strategy
<!-- ID: testing_strategy -->

### Unit Tests

| Module | Test File | Coverage Target |
|--------|-----------|-----------------|
| ForgeConfig | `tests/plugin_manager/test_forge_config.py` | 90% |
| Handler modules | `tests/mybb_mcp/handlers/test_*.py` | 85% |
| Batch sync | `tests/mybb_mcp/sync/test_batching.py` | 90% |
| Bulk update methods | `tests/mybb_mcp/db/test_bulk_updates.py` | 95% |

### Integration Tests

- **MCP Tool Routing**: All 85+ tools route correctly after modularization
- **Plugin Deployment**: Template disk-loading works end-to-end
- **Subtree Operations**: Push/pull to test repository

### Verification Commands

```bash
# Run all tests
pytest tests/ -v

# Test specific handler module
pytest tests/mybb_mcp/handlers/test_templates.py -v

# Test plugin deployment with templates
pytest tests/plugin_manager/test_installer.py::test_deploy_with_disk_templates -v

# Verify MCP tool count
python -c "from mybb_mcp.handlers.dispatcher import HANDLER_REGISTRY; print(len(HANDLER_REGISTRY))"
# Expected: 85
```

---

## 8. Deployment & Operations
<!-- ID: deployment_operations -->

### Migration Path

This is a refactoring project - no deployment changes needed. All changes are to the development toolkit.

### Rollback Strategy

- Git revert for any problematic commits
- Handler modules can be rolled back individually
- Old if-elif chain preserved in git history

### Configuration Management

1. Copy `.mybb-forge.yaml.example` to `.mybb-forge.yaml`
2. Copy `.mybb-forge.env.example` to `.mybb-forge.env`
3. Edit with your developer info and remote URLs
4. System works without config (uses defaults)

---

## 9. Open Questions & Follow-Ups
<!-- ID: open_questions -->

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Should manifest use SHA256 or SHA512? | Architect | DECIDED | SHA512 per R5 - matches MyBB verify_files() |
| Where should ForgeConfig live? | Architect | DECIDED | plugin_manager/forge_config.py |
| How to handle template group creation? | TBD | OPEN | May need MyBB ACP for first-time setup |
| Should subtree tools be in plugins.py or separate? | Architect | DECIDED | Separate subtrees.py handler module |

---

## 10. References & Appendix
<!-- ID: references_appendix -->

### Research Documents

| Doc | Key Findings |
|-----|--------------|
| R1: RESEARCH_GIT_WORKTREES.md | Worktrees not viable (DB sharing); subtrees recommended |
| R2: RESEARCH_PLUGIN_MANAGER.md | Manifest exists in SQLite; meta.json is minimal |
| R3: RESEARCH_MCP_TOOLS_AUDIT.md | 4 direct SQL ops; 87 wrapper methods |
| R4: RESEARCH_DBSYNC_PERFORMANCE.md | 0.5s debounce is bottleneck; no batching |
| R5: RESEARCH_MYBB_INTERNALS.md | SHA512 available; datacache for manifest |
| R6: RESEARCH_SERVER_MODULARIZATION.md | 3,794 lines; 12 handler categories |
| R7: Git subtree config | YAML+.env strategy |

### External References

- [MyBB Plugin Docs](https://docs.mybb.com/1.8/development/plugins/)
- [MyBB Hooks List](https://docs.mybb.com/1.8/development/plugins/hooks/)
- [Git Subtree Documentation](https://git-scm.com/book/en/v2/Git-Tools-Advanced-Merging#_subtree_merge)
- [FastMCP Documentation](https://modelcontextprotocol.io/)

---

*Architecture designed by MyBB-ArchitectAgent based on 7 verified research documents.*
