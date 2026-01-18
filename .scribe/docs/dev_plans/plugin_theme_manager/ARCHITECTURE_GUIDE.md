
# Architecture Guide -- plugin-theme-manager
**Author:** ArchitectAgent
**Version:** v1.1
**Status:** Approved
**Last Updated:** 2026-01-18 04:42:00 UTC

> A Nexus Mods-style management system for MyBB plugins AND themes built with AI-assisted development.

---
## 1. Problem Statement
<!-- ID: problem_statement -->

**Context:** MyBB plugin AND theme development currently lacks organization:
- Plugins live directly in `TestForum/inc/plugins/` with no isolation
- Themes/stylesheets edited directly in database with no version control
- No project metadata tracking (version, status, dependencies)
- No way to manage private vs public plugins/themes
- Manual deployment via copy/paste
- 60+ MCP tools exist but need orchestration, not more tools

**Goals:**
- Organize plugins AND themes in isolated development folders with proper structure
- Track project metadata in a SQLite database (unified for both types)
- Support private (gitignored) and public (uploadable) plugins and themes
- Enable clean AI-assisted plugin development workflows
- Enable clean AI-assisted theme development workflows
- Integrate with existing MCP tools without creating new ones

**Non-Goals (v1):**
- Creating new MCP tools (pure Python orchestration layer)
- Automating PHP hook execution (ACP required for `_activate()`/`_deactivate()`)
- Multi-forum deployment (single TestForum focus)

**Success Metrics:**
- All plugins in isolated, well-structured folders
- All themes in isolated, well-structured folders
- Full metadata and history tracking for every project (plugins and themes)
- Create -> Develop -> Test -> Install workflow in clean steps (plugins)
- Create -> Develop -> Test -> Install workflow in clean steps (themes)
- Zero new MCP tools; pure orchestration
- Clear separation of public/private work (both types)

---
## 2. Requirements & Constraints
<!-- ID: requirements_constraints -->

**Functional Requirements (Plugins):**
- FR1: Create new plugin with workspace directory, scaffold PHP, generate meta.json, register in SQLite
- FR2: Install plugin by copying files to TestForum and updating MCP cache
- FR3: Sync development changes from workspace to TestForum
- FR4: Export plugin as distributable ZIP with proper structure
- FR5: Import external plugins by extracting and analyzing structure

**Functional Requirements (Themes):**
- FR6: Create new theme with workspace directory, scaffold CSS, generate meta.json, register in SQLite
- FR7: Install theme by deploying stylesheets via MCP and updating cache
- FR8: Sync theme changes from workspace to TestForum via MCP stylesheet tools
- FR9: Export theme as distributable ZIP with proper structure
- FR10: Support template overrides in theme workspace

**Non-Functional Requirements:**
- NFR1: Zero new MCP tools - pure Python orchestration
- NFR2: File operations via Python pathlib (not MCP)
- NFR3: SQLite for metadata persistence (no migrations, just recreate)
- NFR4: Compatible with existing mybb_sync infrastructure
- NFR5: Unified database schema supporting both plugins and themes via `type` field

**Critical Constraints (from Research):**
| Constraint | Impact | Workaround |
|------------|--------|------------|
| MCP `mybb_plugin_activate` only updates cache | Cannot trigger `_activate()` PHP hooks | Document ACP step requirement clearly |
| No MCP file copy/move tools | Cannot deploy plugin files via MCP | Use Python pathlib for all file ops |
| No MCP SQLite write access | Cannot write to projects.db via MCP | Use Python sqlite3 directly |
| Sync system only handles templates/styles | Plugin templates not currently synced | Extend PathRouter for `plugins/` route |
| Theme stylesheets already supported by MCP | Can use existing `mybb_write_stylesheet` | Leverage existing tools for theme sync |

**Assumptions:**
- Python 3.10+ runtime available
- Filesystem read/write access to workspace and TestForum
- MCP server running and accessible
- Single developer workflow (no concurrent edits)

**Risks & Mitigations:**
| Risk | Severity | Mitigation |
|------|----------|------------|
| User forgets ACP activation step | High | Prominent warning in all install outputs |
| Plugin template conflicts | Medium | Enforce `{codename}_` prefix convention |
| Theme stylesheet ID mapping | Medium | Use `mybb_list_stylesheets` to resolve IDs |
| SQLite corruption | Low | Simple schema, recreate from scratch if needed |

---
## 3. Architecture Overview
<!-- ID: architecture_overview -->

**Solution Summary:** Python orchestration layer that composes existing MCP tools with native file operations to provide a Nexus Mods-style plugin AND theme management experience.

```
+-------------------+     +------------------+     +-------------------+
|   Claude Code     |---->|  Plugin Manager  |---->|   MCP Tools       |
|   (User Request)  |     |  (Orchestrator)  |     |   (60+ existing)  |
+-------------------+     +------------------+     +-------------------+
                               |      |
                               v      v
                    +----------+  +----------+
                    | pathlib  |  | sqlite3  |
                    | (files)  |  | (meta)   |
                    +----------+  +----------+
```

**Component Breakdown:**

1. **PluginManager** (Main Orchestrator)
   - Purpose: Coordinate all plugin AND theme workflows
   - Interface: Python class with workflow methods for both types
   - Dependencies: ProjectDatabase, PluginWorkspace, ThemeWorkspace, SyncIntegration

2. **ProjectDatabase** (SQLite Wrapper)
   - Purpose: Store plugin AND theme metadata, history
   - Interface: CRUD operations for projects table with `type` field
   - Location: `.plugin_manager/projects.db`
   - Supports: `type='plugin'` and `type='theme'`

3. **PluginWorkspace** (Plugin Directory Management)
   - Purpose: Manage plugin development folders
   - Interface: Create, validate, and organize plugin directories
   - Location: `plugins/{public,private}/{codename}/`

4. **ThemeWorkspace** (Theme Directory Management)
   - Purpose: Manage theme development folders
   - Interface: Create, validate, and organize theme directories
   - Location: `themes/{public,private}/{codename}/`
   - Structure: `stylesheets/`, `templates/`, `images/`

5. **SyncIntegration** (mybb_sync Extension)
   - Purpose: Enable disk sync for plugin templates and theme stylesheets
   - Interface: Extend PathRouter for `plugins/` route
   - Depends on: Existing `mybb_mcp/sync/` infrastructure
   - Note: Theme stylesheets already supported via existing sync tools

**Data Flow (Plugin Install Workflow):**
```
1. User: "Install my_plugin to forum"
2. PluginManager.install_plugin("my_plugin")
3. ProjectDatabase.get_project("my_plugin") -> meta.json path
4. PluginWorkspace.read_meta("my_plugin") -> file mappings
5. pathlib: Copy plugin.php -> TestForum/inc/plugins/
6. pathlib: Copy languages/* -> TestForum/inc/languages/english/
7. MCP: mybb_template_batch_write() for templates
8. MCP: mybb_plugin_activate() for cache
9. ProjectDatabase.update_status("my_plugin", "installed")
10. Output: "Installed. Visit ACP > Plugins to activate hooks."
```

**Data Flow (Theme Install Workflow):**
```
1. User: "Install my_theme to forum"
2. PluginManager.install_theme("my_theme")
3. ProjectDatabase.get_project("my_theme") -> meta.json path
4. ThemeWorkspace.read_meta("my_theme") -> stylesheet mappings
5. MCP: mybb_list_stylesheets(tid) -> get stylesheet IDs
6. MCP: mybb_write_stylesheet(sid, css) for each stylesheet
7. MCP: mybb_template_batch_write() for template overrides
8. ProjectDatabase.update_status("my_theme", "installed")
9. Output: "Installed. Visit ACP > Themes to set as default."
```

**External Integrations:**
- MCP Tools (Plugins): mybb_create_plugin, mybb_analyze_plugin, mybb_template_batch_write, mybb_plugin_activate
- MCP Tools (Themes): mybb_list_themes, mybb_list_stylesheets, mybb_read_stylesheet, mybb_write_stylesheet, mybb_sync_export_stylesheets
- mybb_sync: PathRouter extension for plugin template sync
- Scribe: Optional project tracking integration

---
## 4. Detailed Design
<!-- ID: detailed_design -->

### 4.1 PluginManager Class

```python
class PluginManager:
    """Main orchestrator for plugin AND theme workflows."""

    def __init__(self, workspace_root: Path, testforum_root: Path):
        self.plugin_workspace = PluginWorkspace(workspace_root / "plugins")
        self.theme_workspace = ThemeWorkspace(workspace_root / "themes")
        self.db = ProjectDatabase(workspace_root / ".plugin_manager" / "projects.db")
        self.testforum = testforum_root

    # ==================== PLUGIN WORKFLOWS ====================

    def create_plugin(self, codename: str, visibility: str = "public", **kwargs) -> str:
        """Create new plugin with workspace, scaffold, meta.json, and DB registration."""
        # 1. Create workspace directory
        # 2. Call mybb_create_plugin via MCP for PHP scaffold
        # 3. Generate meta.json from kwargs
        # 4. Register in projects.db with type='plugin'
        # 5. Return success message with next steps

    def install_plugin(self, codename: str) -> str:
        """Deploy plugin to TestForum."""
        # 1. Read meta.json for file mappings
        # 2. Copy files via pathlib
        # 3. Deploy templates via MCP
        # 4. Activate in cache via MCP
        # 5. Update status in DB
        # 6. Return success with ACP warning

    def sync_plugin(self, codename: str) -> str:
        """Push workspace changes to TestForum."""
        # 1. Compare workspace vs TestForum files
        # 2. Copy changed files
        # 3. Update templates via MCP
        # 4. Log sync in history table

    def export_plugin(self, codename: str, output_path: Path) -> str:
        """Package plugin for distribution as ZIP."""
        # 1. Validate meta.json completeness
        # 2. Collect all plugin files
        # 3. Generate README from mybb_analyze_plugin
        # 4. Create ZIP archive via zipfile
        # 5. Return path to created archive

    # ==================== THEME WORKFLOWS ====================

    def create_theme(self, codename: str, visibility: str = "public", **kwargs) -> str:
        """Create new theme with workspace, scaffold CSS, meta.json, and DB registration."""
        # 1. Create workspace directory with stylesheets/, templates/, images/
        # 2. Generate scaffold CSS files (global.css, colors.css)
        # 3. Generate meta.json with stylesheets array, parent_theme, color_scheme
        # 4. Register in projects.db with type='theme'
        # 5. Return success message with next steps

    def install_theme(self, codename: str) -> str:
        """Deploy theme to TestForum via MCP stylesheet tools."""
        # 1. Read meta.json for stylesheet mappings
        # 2. MCP: mybb_list_stylesheets(tid) to get existing IDs
        # 3. MCP: mybb_write_stylesheet(sid, css) for each stylesheet
        # 4. MCP: mybb_template_batch_write() for template overrides
        # 5. Update status in DB
        # 6. Return success with ACP instructions

    def sync_theme(self, codename: str) -> str:
        """Push workspace stylesheet/template changes to TestForum."""
        # 1. Detect changed CSS files in workspace
        # 2. MCP: mybb_write_stylesheet(sid, css) for each changed stylesheet
        # 3. Detect changed template override files
        # 4. MCP: mybb_template_batch_write() for changed templates
        # 5. Log sync in history table

    def export_theme(self, codename: str, output_path: Path) -> str:
        """Package theme for distribution as ZIP."""
        # 1. Validate theme meta.json completeness
        # 2. Collect all stylesheets, templates, images
        # 3. Generate README with stylesheet list
        # 4. Create ZIP archive via zipfile
        # 5. Return path to created archive
```

### 4.2 ProjectDatabase Schema

```sql
-- Schema file: .plugin_manager/schema/projects.sql
-- Recreate from scratch if schema changes (no migrations)

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codename TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'plugin',  -- 'plugin' or 'theme'
    visibility TEXT NOT NULL DEFAULT 'public',  -- 'public' or 'private'
    status TEXT NOT NULL DEFAULT 'development',  -- 'development', 'testing', 'installed', 'archived'
    version TEXT NOT NULL DEFAULT '1.0.0',
    description TEXT,
    author TEXT,
    mybb_compatibility TEXT DEFAULT '18*',
    workspace_path TEXT NOT NULL,  -- Relative to workspace root
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    installed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    action TEXT NOT NULL,  -- 'created', 'installed', 'synced', 'exported', 'uninstalled'
    details TEXT,  -- JSON blob with action-specific data
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_projects_codename ON projects(codename);
CREATE INDEX IF NOT EXISTS idx_history_project ON history(project_id);
```

**Note:** Skip `dependencies` and `hook_usage` tables for v1. Add if needed later.

### 4.3 Plugin meta.json Schema

```json
{
    "$schema": "plugin_manager/meta.schema.json",
    "type": "plugin",
    "codename": "my_plugin",
    "display_name": "My Plugin",
    "version": "1.0.0",
    "author": "Developer",
    "description": "Plugin description",
    "mybb_compatibility": "18*",
    "visibility": "public",

    "hooks": [
        {"name": "index_start", "handler": "my_plugin_index", "priority": 10}
    ],

    "settings": [
        {"name": "my_plugin_enabled", "title": "Enable Plugin", "type": "yesno", "default": "1"}
    ],

    "templates": [
        "my_plugin_widget",
        "my_plugin_modal"
    ],

    "files": {
        "plugin": "src/my_plugin.php",
        "languages": "languages/",
        "templates": "templates/"
    }
}
```

### 4.4 Theme meta.json Schema

```json
{
    "$schema": "plugin_manager/meta.schema.json",
    "type": "theme",
    "codename": "my_theme",
    "display_name": "My Custom Theme",
    "version": "1.0.0",
    "author": "Developer",
    "description": "Theme description",
    "mybb_compatibility": "18*",
    "visibility": "public",

    "parent_theme": "Default",
    "color_scheme": {
        "primary": "#3498db",
        "secondary": "#2ecc71",
        "background": "#ffffff",
        "text": "#333333"
    },

    "stylesheets": [
        {"name": "global.css", "attached_to": ["global"]},
        {"name": "colors.css", "attached_to": ["global"]},
        {"name": "forum.css", "attached_to": ["forumdisplay.php", "showthread.php"]}
    ],

    "template_overrides": [
        "header",
        "footer",
        "headerinclude"
    ],

    "images": [
        "logo.png",
        "icons/"
    ],

    "files": {
        "stylesheets": "stylesheets/",
        "templates": "templates/",
        "images": "images/"
    }
}
```

### 4.5 PathRouter Extension (for Sync Integration)

Add to `mybb_mcp/mybb_mcp/sync/router.py`:

```python
# New route type for plugin templates
# Pattern: plugins/{codename}/templates/{template_name}.html

if len(parts) >= 4 and parts[0] == "plugins" and parts[2] == "templates" and path.suffix == ".html":
    return ParsedPath(
        type="plugin_template",
        plugin_codename=parts[1],
        template_name=path.stem,
        raw_path=relative_path,
    )
```

---
## 5. Directory Structure (Keep Updated)
<!-- ID: directory_structure -->

```
MyBB_Playground/
+-- plugins/                        # Plugin development workspace
|   +-- public/                     # Public plugins (git tracked)
|   |   +-- example_plugin/
|   |   |   +-- src/
|   |   |   |   +-- example_plugin.php
|   |   |   +-- languages/
|   |   |   |   +-- english/
|   |   |   |       +-- example_plugin.lang.php
|   |   |   +-- templates/
|   |   |   |   +-- example_plugin_widget.html
|   |   |   +-- tests/
|   |   |   +-- meta.json
|   |   |   +-- README.md
|   |   +-- another_plugin/
|   |
|   +-- private/                    # Private plugins (gitignored)
|       +-- my_secret_plugin/
|
+-- themes/                         # Theme development workspace
|   +-- public/                     # Public themes (git tracked)
|   |   +-- example_theme/
|   |   |   +-- stylesheets/
|   |   |   |   +-- global.css
|   |   |   |   +-- colors.css
|   |   |   |   +-- forum.css
|   |   |   +-- templates/
|   |   |   |   +-- header.html     # Template overrides
|   |   |   |   +-- footer.html
|   |   |   +-- images/
|   |   |   |   +-- logo.png
|   |   |   +-- meta.json
|   |   |   +-- README.md
|   |   +-- another_theme/
|   |
|   +-- private/                    # Private themes (gitignored)
|       +-- my_custom_theme/
|
+-- .plugin_manager/                # Manager state (handles both plugins and themes)
|   +-- projects.db                 # SQLite database (unified for plugins + themes)
|   +-- schema/
|       +-- projects.sql            # Schema definition with type field
|
+-- mybb_sync/                      # Existing template sync (unchanged)
|   +-- template_sets/
|   +-- styles/
|   +-- plugins/                    # NEW: Plugin template sync
|       +-- example_plugin/
|           +-- templates/
|               +-- example_plugin_widget.html
|
+-- TestForum/                      # MyBB installation (unchanged)
    +-- inc/plugins/
    +-- inc/languages/english/
```

**Gitignore additions:**
```gitignore
# Plugin Manager
plugins/private/
themes/private/
.plugin_manager/projects.db  # Optional: gitignore for local-only tracking
```

---
## 6. Data & Storage
<!-- ID: data_storage -->

**Datastores:**
1. **SQLite** (`.plugin_manager/projects.db`): Project metadata (plugins AND themes), history
2. **JSON** (`meta.json` per project): Plugin/theme configuration and file mappings
3. **Filesystem (Plugins)**: Plugin source files, templates, languages
4. **Filesystem (Themes)**: Stylesheets, template overrides, images

**Schema Management:**
- No migration system - schema is simple enough to recreate
- Schema SQL files stored at `.plugin_manager/schema/`
- On corruption or schema change: delete DB, recreate from schema.sql
- `type` field in projects table: 'plugin' or 'theme'

**Indexes:**
- `idx_projects_codename`: Fast lookup by plugin/theme codename
- `idx_history_project`: Fast history queries per project

**Backup Strategy:**
- SQLite DB is reconstructable from filesystem (meta.json files)
- History is nice-to-have but not critical
- No explicit backup mechanism needed for v1

---
## 7. Testing & Validation Strategy
<!-- ID: testing_strategy -->

**Unit Tests (Plugins):**
- PluginManager plugin workflow methods
- ProjectDatabase CRUD operations (type='plugin')
- PluginWorkspace directory operations
- Plugin meta.json schema validation

**Unit Tests (Themes):**
- PluginManager theme workflow methods
- ProjectDatabase CRUD operations (type='theme')
- ThemeWorkspace directory operations
- Theme meta.json schema validation

**Integration Tests (Plugins):**
- Create plugin end-to-end (workspace + DB + scaffold)
- Install plugin end-to-end (copy + MCP calls)
- Export plugin (ZIP generation)

**Integration Tests (Themes):**
- Create theme end-to-end (workspace + DB + scaffold CSS)
- Install theme end-to-end (MCP stylesheet deployment)
- Export theme (ZIP generation with stylesheets)

**Manual QA (Plugins):**
- Verify ACP activation works after MCP install
- Verify plugin functions correctly in TestForum
- Verify template sync works with extended PathRouter

**Manual QA (Themes):**
- Verify theme stylesheets appear in ACP Themes
- Verify CSS changes visible in forum
- Verify template overrides work correctly

**Test Commands:**
```bash
pytest tests/test_plugin_manager.py -v
pytest tests/test_project_database.py -v
pytest tests/test_workspace.py -v
pytest tests/test_theme_workspace.py -v
```

---
## 8. Deployment & Operations
<!-- ID: deployment_operations -->

**Implementation Options:**

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| Claude Skill | Best UX (`/plugin create`), natural language | Requires skill authoring | **Recommended for v1** |
| Python CLI | Portable, testable | Less integrated with Claude | Good for testing |
| Hybrid | Skill wraps CLI | More code | Best long-term |

**Recommended Approach:** Claude Code Skill

```
# Plugin commands
/plugin create my_plugin --visibility=private --hooks=index_start,postbit
/plugin install my_plugin
/plugin sync my_plugin
/plugin export my_plugin --output=./dist/
/plugin list
/plugin status my_plugin

# Theme commands
/theme create my_theme --visibility=private --parent=Default
/theme install my_theme
/theme sync my_theme
/theme export my_theme --output=./dist/
/theme list
/theme status my_theme
```

**Fallback:** Direct Python invocation for testing/debugging:
```bash
python -m plugin_manager create my_plugin
python -m plugin_manager install my_plugin
python -m plugin_manager create_theme my_theme
python -m plugin_manager install_theme my_theme
```

**Configuration:**
- Environment variables in `.env` (already exists for MCP)
- Add: `PLUGIN_WORKSPACE_ROOT`, `THEME_WORKSPACE_ROOT`, `PLUGIN_MANAGER_DB_PATH`

---
## 9. Open Questions & Follow-Ups
<!-- ID: open_questions -->

| Item | Owner | Status | Decision |
|------|-------|--------|----------|
| Database gitignored or committed? | Architect | DECIDED | Gitignored - each dev has own tracking |
| Template storage: plugin folder or mybb_sync? | Architect | DECIDED | Both - source in plugin folder, sync to mybb_sync |
| CLI vs Skill implementation? | Architect | DECIDED | Skill for UX, CLI for testing |
| Multi-forum support? | User | DEFERRED | v1 is single-forum only |
| Theme workflows? | Architect | IN SCOPE | Themes are first-class citizens alongside plugins |

---
## 10. MCP Tool Integration
<!-- ID: mcp_integration -->

**Sub-Plan:** `architecture/mcp_integration/MCP_INTEGRATION_PLAN.md`

### Overview

The MCP server (`mybb_mcp/server.py`) exposes 20 plugin/theme tools that originally bypassed the plugin_manager system. Phase 6 integrates these tools to use PluginManager as the single source of truth.

### Integration Strategy: DELEGATE

MCP tools become thin wrappers that delegate to PluginManager methods:

```
MCP Tool Handler (server.py)
    |
    v
PluginManager.method()    <-- Single source of truth
    |
    v
Workspace + Database + TestForum
```

### Tools to Refactor (12 total)

| Tool | Target Method | Priority |
|------|---------------|----------|
| `mybb_create_plugin` | `PluginManager.create_plugin()` | HIGH |
| `mybb_plugin_activate` | `PluginManager.install_plugin()` | HIGH |
| `mybb_plugin_deactivate` | `PluginManager.uninstall_plugin()` | HIGH |
| `mybb_list_plugins` | Query workspace + TestForum | MEDIUM |
| `mybb_read_plugin` | Workspace-aware read | MEDIUM |
| `mybb_analyze_plugin` | Load meta.json for managed | MEDIUM |
| `mybb_plugin_is_installed` | Check both sources | MEDIUM |
| `mybb_list_themes` | Query workspace + DB | MEDIUM |
| `mybb_create_theme` (NEW) | `PluginManager.create_theme()` | MEDIUM |
| `mybb_read_stylesheet` | Hybrid: workspace or DB | LOW |
| `mybb_write_stylesheet` | Hybrid: workspace or DB | LOW |
| `mybb_sync_status` | Add plugin_manager info | LOW |

### Import Strategy

Use sys.path manipulation (established pattern from `manager.py:802-804`):

```python
import sys
from pathlib import Path

pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
if str(pm_path.parent) not in sys.path:
    sys.path.insert(0, str(pm_path.parent))

from plugin_manager.manager import PluginManager
```

### Backward Compatibility

- **Managed plugins:** Full plugin_manager workflow
- **Unmanaged plugins:** Legacy behavior with deprecation warnings
- **Response format:** Preserve markdown, enhance content

### Key Files Modified

| File | Changes |
|------|---------|
| `mybb_mcp/mybb_mcp/server.py` | 12 tool handlers refactored (~200 lines) |
| `mybb_mcp/mybb_mcp/server.py` | Add `mybb_create_theme` tool definition |
| `mybb_mcp/mybb_mcp/tools/plugins.py` | Add deprecation warning to `create_plugin()` |

---
## 11. References & Appendix
<!-- ID: references_appendix -->

**Research Documents:**
- `research/RESEARCH_PRIOR_AUDITS_AND_CONSTRAINTS_20260118.md` - Tool inventory, constraints
- `research/RESEARCH_PLUGIN_STRUCTURE_20250117.md` - MyBB plugin patterns
- `research/RESEARCH_SYNC_SYSTEM_INTEGRATION_20260117_0347.md` - Sync system analysis
- `research/RESEARCH_WORKFLOW_MAPPING_20260118.md` - Workflow gap analysis
- `research/RESEARCH_MCP_INTEGRATION_AUDIT.md` - MCP tool integration audit (Phase 6)
- `architecture/mcp_integration/MCP_INTEGRATION_PLAN.md` - MCP integration sub-plan
- `SPEC_PROPOSAL.md` - Original vision document

**Code References:**
- MCP Server: `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/server.py`
- PathRouter: `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/sync/router.py`
- Plugin Scaffold: `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/tools/plugins.py`
- Reference Plugin: `/home/austin/projects/MyBB_Playground/TestForum/inc/plugins/hello.php`

**External Docs:**
- [MyBB Plugin Development](https://docs.mybb.com/1.8/development/plugins/)
- [MyBB Hooks Reference](https://docs.mybb.com/1.8/development/plugins/hooks/)

---
