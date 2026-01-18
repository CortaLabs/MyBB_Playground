
# Phase Plan -- plugin-theme-manager
**Author:** ArchitectAgent
**Version:** v1.1
**Status:** Active
**Last Updated:** 2026-01-18 04:35:00 UTC

> Execution roadmap for plugin-theme-manager implementation covering BOTH plugins AND themes.

---
## Phase Overview
<!-- ID: phase_overview -->

| Phase | Goal | Key Deliverables | Est. Complexity | Confidence |
|-------|------|------------------|-----------------|------------|
| Phase 1 | Foundation | Directory structure for plugins AND themes, SQLite DB with type field, unified meta.json schema | Low | 0.95 |
| Phase 2 | Create Workflow | Scaffold plugin OR theme in workspace with full registration | Medium | 0.90 |
| Phase 3 | Install Workflow | Deploy plugin OR theme to TestForum with MCP integration | Medium | 0.85 |
| Phase 4 | Sync Workflow | Push plugin/theme changes, integrate with mybb_sync | Medium-High | 0.80 |
| Phase 5 | Export Workflow | Package plugin OR theme for distribution as ZIP | Low | 0.90 |
| Phase 6 | MCP Integration | Refactor 12 MCP tools to delegate to PluginManager | Medium | 0.95 |

**Scope Note:** This plan covers BOTH plugins AND themes as first-class citizens. Each phase includes parallel workflows for both project types.

**Total Estimated LOC:** 1200-1700 lines Python (including MCP integration)
**Dependencies:** Python 3.10+, sqlite3, pathlib, zipfile, existing MCP server

---
## Phase 1 -- Foundation
<!-- ID: phase_1 -->

**Objective:** Create the infrastructure for plugin AND theme management - directories, database, and configuration schemas supporting both project types.

**Key Tasks:**

1. **Create directory structure (Plugins AND Themes)**
   - `plugins/public/` - Public plugins (git tracked)
   - `plugins/private/` - Private plugins (gitignored)
   - `themes/public/` - Public themes (git tracked)
   - `themes/private/` - Private themes (gitignored)
   - `.plugin_manager/` - Manager state directory (handles both types)
   - `.plugin_manager/schema/` - SQL schema files

2. **Implement ProjectDatabase class (Unified for Both Types)**
   - SQLite connection management
   - `create_tables()` - Execute schema.sql
   - `add_project(type='plugin'|'theme')` - Insert new project with type
   - `get_project()` - Retrieve by codename
   - `update_project()` - Update fields
   - `list_projects(type=None)` - Filter by visibility/status/type
   - `add_history()` - Log actions
   - **Type field** in projects table distinguishes plugins from themes

3. **Create schema files**
   - `.plugin_manager/schema/projects.sql` - Tables and indexes with `type` column
   - Simple recreate strategy (no migrations)

4. **Define meta.json schema (Unified with Type-Specific Fields)**
   - JSON Schema file supporting both plugins and themes
   - Validation helper function with type-aware validation
   - Default template for new plugins
   - Default template for new themes (includes stylesheets, parent_theme, color_scheme)

5. **Update .gitignore**
   - Add `plugins/private/`
   - Add `themes/private/`
   - Add `.plugin_manager/projects.db`

**Deliverables:**
- `plugin_manager/database.py` - ProjectDatabase class (unified for plugins/themes)
- `plugin_manager/schema.py` - meta.json validation (type-aware)
- `.plugin_manager/schema/projects.sql` - Database schema with type field
- Directory structure for BOTH plugins and themes created

**Acceptance Criteria:**
- [ ] ProjectDatabase can CRUD plugin projects
- [ ] ProjectDatabase can CRUD theme projects (type='theme')
- [ ] `list_projects(type='plugin')` returns only plugins
- [ ] `list_projects(type='theme')` returns only themes
- [ ] meta.json validation works for plugin schema
- [ ] meta.json validation works for theme schema
- [ ] Schema recreates cleanly from SQL file
- [ ] Private directories are gitignored (plugins AND themes)

**Dependencies:** None (first phase)

**Estimated LOC:** 200-250

---
## Phase 2 -- Create Workflow
<!-- ID: phase_2 -->

**Objective:** Implement create workflows for BOTH plugins AND themes with full structure and registration.

### Plugin Creation Workflow

**Key Tasks (Plugins):**

1. **Implement PluginWorkspace class**
   - `create_workspace()` - Create plugin directory structure
   - `get_workspace_path()` - Resolve plugin location
   - `read_meta()` - Parse meta.json
   - `write_meta()` - Generate meta.json
   - `validate_workspace()` - Check structure integrity

2. **Implement PluginManager.create_plugin()**
   - Create workspace directory with structure:
     ```
     plugins/{visibility}/{codename}/
     +-- src/
     +-- languages/english/
     +-- templates/
     +-- tests/
     +-- meta.json
     +-- README.md
     ```
   - Call MCP `mybb_create_plugin` for PHP scaffold
   - Move generated files from TestForum to workspace
   - Generate meta.json from parameters
   - Register in ProjectDatabase with type='plugin'
   - Return success message with next steps

3. **MCP Integration (Plugins)**
   - Function to call `mybb_create_plugin` tool
   - Parse response for generated file paths
   - Handle errors gracefully

### Theme Creation Workflow

**Key Tasks (Themes):**

4. **Implement ThemeWorkspace class**
   - `create_workspace()` - Create theme directory structure
   - `get_workspace_path()` - Resolve theme location
   - `read_meta()` - Parse theme meta.json
   - `write_meta()` - Generate theme meta.json
   - `validate_workspace()` - Check theme structure integrity

5. **Implement PluginManager.create_theme()**
   - Create workspace directory with structure:
     ```
     themes/{visibility}/{codename}/
     +-- stylesheets/
     +-- templates/
     +-- images/
     +-- meta.json
     +-- README.md
     ```
   - Generate scaffold CSS files (global.css, colors.css)
   - Generate theme meta.json with theme-specific fields:
     - `stylesheets` array
     - `template_overrides` array
     - `parent_theme` (optional inheritance)
     - `color_scheme` (color variables)
   - Register in ProjectDatabase with type='theme'
   - Return success message with next steps

6. **Template generation (Themes)**
   - Theme README.md template
   - Theme meta.json default template with stylesheet structure
   - Default CSS scaffold with common MyBB selectors

**Deliverables:**
- `plugin_manager/workspace.py` - PluginWorkspace class
- `plugin_manager/theme_workspace.py` - ThemeWorkspace class
- `plugin_manager/manager.py` - PluginManager.create_plugin() AND create_theme()
- `plugin_manager/mcp_client.py` - MCP tool invocation helpers
- Templates for plugin README.md, plugin meta.json
- Templates for theme README.md, theme meta.json

**Acceptance Criteria (Plugins):**
- [ ] `create_plugin("test_plugin", visibility="private")` creates full workspace
- [ ] PHP scaffold is generated and moved to workspace
- [ ] meta.json is valid and contains correct data
- [ ] Project is registered in SQLite database with type='plugin'
- [ ] History entry logged for creation

**Acceptance Criteria (Themes):**
- [ ] `create_theme("test_theme", visibility="private")` creates full workspace
- [ ] Theme directory structure created with stylesheets/, templates/, images/
- [ ] Theme meta.json is valid and contains stylesheets array
- [ ] Theme meta.json includes parent_theme and color_scheme fields
- [ ] Project is registered in SQLite database with type='theme'
- [ ] History entry logged for theme creation

**Dependencies:** Phase 1 (Foundation)

**Estimated LOC:** 300-400

**Task Packages for Coder:**

### Task 2.1: PluginWorkspace Class
**Scope:** Create workspace directory management class for plugins
**Files to Modify:** `plugin_manager/workspace.py` (new file)
**Specifications:**
- `__init__(workspace_root: Path)`
- `create_workspace(codename: str, visibility: str) -> Path`
- `get_workspace_path(codename: str) -> Path | None`
- `read_meta(codename: str) -> dict`
- `write_meta(codename: str, meta: dict) -> None`
- `validate_workspace(codename: str) -> list[str]` (returns validation errors)

**Verification:**
- [ ] Unit tests for all methods pass
- [ ] Directory structure matches spec

### Task 2.2: ThemeWorkspace Class
**Scope:** Create workspace directory management class for themes
**Files to Modify:** `plugin_manager/theme_workspace.py` (new file)
**Specifications:**
- `__init__(workspace_root: Path)`
- `create_workspace(codename: str, visibility: str) -> Path`
- `get_workspace_path(codename: str) -> Path | None`
- `read_meta(codename: str) -> dict` (theme-specific schema)
- `write_meta(codename: str, meta: dict) -> None`
- `validate_workspace(codename: str) -> list[str]`

**Verification:**
- [ ] Unit tests for all methods pass
- [ ] Theme directory structure matches spec (stylesheets/, templates/, images/)

### Task 2.3: MCP Client Helpers
**Scope:** Wrapper functions for MCP tool calls (plugins and themes)
**Files to Modify:** `plugin_manager/mcp_client.py` (new file)
**Specifications:**
- `call_create_plugin(codename, name, description, hooks, ...) -> dict`
- `call_list_themes() -> list[dict]` (for parent theme validation)
- `call_list_stylesheets(tid: int) -> list[dict]` (for existing CSS reference)
- Parse MCP responses, extract file paths
- Handle connection errors

**Verification:**
- [ ] Can invoke mybb_create_plugin successfully
- [ ] Can invoke mybb_list_themes successfully
- [ ] Error handling tested

### Task 2.4: Create Plugin Workflow
**Scope:** Main create_plugin method
**Files to Modify:** `plugin_manager/manager.py` (new file)
**Specifications:**
- Orchestrate workspace creation + MCP call + DB registration
- Move files from TestForum to workspace
- Generate meta.json and README.md

**Verification:**
- [ ] End-to-end test creates plugin successfully

### Task 2.5: Create Theme Workflow
**Scope:** Main create_theme method
**Files to Modify:** `plugin_manager/manager.py`
**Specifications:**
- Create theme workspace with correct structure
- Generate scaffold CSS files
- Generate theme meta.json with stylesheets array
- Register in DB with type='theme'

**Verification:**
- [ ] End-to-end test creates theme successfully
- [ ] Theme meta.json contains stylesheets array

---
## Phase 3 -- Install Workflow
<!-- ID: phase_3 -->

**Objective:** Implement install workflows for BOTH plugins AND themes, deploying from workspace to TestForum.

### Plugin Install Workflow

**Key Tasks (Plugins):**

1. **Implement file deployment (Plugins)**
   - Copy plugin PHP from workspace to `TestForum/inc/plugins/`
   - Copy language files to `TestForum/inc/languages/english/`
   - Handle file conflicts (backup existing files)

2. **Implement template deployment (Plugins)**
   - Read templates from workspace `templates/` directory
   - Call MCP `mybb_template_batch_write` to deploy to DB
   - Handle template versioning (sid=-2 for master)

3. **Implement MCP activation (Plugins)**
   - Call `mybb_plugin_activate` to update cache
   - Verify activation succeeded

### Theme Install Workflow

**Key Tasks (Themes):**

4. **Implement stylesheet deployment (Themes)**
   - Read CSS files from workspace `stylesheets/` directory
   - Call MCP `mybb_write_stylesheet` for each CSS file
   - Map workspace CSS to MyBB stylesheet IDs via `mybb_list_stylesheets`
   - Handle new stylesheets vs updates to existing

5. **Implement template override deployment (Themes)**
   - Read templates from workspace `templates/` directory
   - Call MCP `mybb_template_batch_write` with appropriate sid (theme set ID)
   - Template overrides inherit from master but customize for theme

6. **Theme registration via existing MyBB mechanisms**
   - Themes don't require PHP activation like plugins
   - Update cache via `mybb_cache_rebuild` if needed
   - Verify theme appears in ACP Themes list

### Shared Tasks

7. **Update database state**
   - Set status = 'installed'
   - Set installed_at timestamp
   - Log history entry

8. **Warning output**
   - Plugins: Prominent message about ACP activation requirement
   - Themes: Instructions for setting as default/forum theme

**Deliverables:**
- `plugin_manager/manager.py` - PluginManager.install_plugin() AND install_theme()
- `plugin_manager/deployer.py` - File deployment helpers (plugins and themes)

**Acceptance Criteria (Plugins):**
- [ ] Plugin PHP copied to TestForum
- [ ] Language files copied correctly
- [ ] Templates deployed via MCP
- [ ] Cache updated via MCP
- [ ] Database status updated
- [ ] ACP warning displayed prominently

**Acceptance Criteria (Themes):**
- [ ] Theme stylesheets deployed via `mybb_write_stylesheet`
- [ ] Template overrides deployed via `mybb_template_batch_write`
- [ ] Theme visible in MyBB ACP Themes list
- [ ] Database status updated to 'installed'
- [ ] History entry logged for theme installation
- [ ] Instructions displayed for activating theme

**Dependencies:** Phase 2 (Create Workflow)

**Estimated LOC:** 250-350

**Task Packages for Coder:**

### Task 3.1: File Deployer (Plugins)
**Scope:** File copy operations for plugin install
**Files to Modify:** `plugin_manager/deployer.py` (new file)
**Specifications:**
- `deploy_plugin_file(workspace_path, testforum_root, codename) -> Path`
- `deploy_language_files(workspace_path, testforum_root, codename) -> list[Path]`
- Backup existing files before overwrite
- Handle missing source files gracefully

**Verification:**
- [ ] Files copied to correct locations
- [ ] Backups created for existing files

### Task 3.2: Template Deployer (Plugins)
**Scope:** Deploy plugin templates via MCP
**Files to Modify:** `plugin_manager/deployer.py`
**Specifications:**
- `deploy_templates(workspace_path, codename) -> int` (returns count)
- Read .html files from workspace templates/
- Call mybb_template_batch_write
- Return deployment stats

**Verification:**
- [ ] Templates appear in MyBB database

### Task 3.3: Stylesheet Deployer (Themes)
**Scope:** Deploy theme stylesheets via MCP
**Files to Modify:** `plugin_manager/deployer.py`
**Specifications:**
- `deploy_stylesheets(workspace_path, theme_codename, theme_tid) -> int`
- Read .css files from workspace stylesheets/
- Call `mybb_list_stylesheets(tid)` to get existing stylesheet IDs
- Call `mybb_write_stylesheet(sid, css)` for each stylesheet
- Handle new stylesheets (may need manual creation in ACP first)
- Return deployment stats

**Verification:**
- [ ] Stylesheets updated in MyBB database
- [ ] CSS changes visible in forum

### Task 3.4: Template Override Deployer (Themes)
**Scope:** Deploy theme template overrides via MCP
**Files to Modify:** `plugin_manager/deployer.py`
**Specifications:**
- `deploy_theme_templates(workspace_path, theme_codename, template_set_sid) -> int`
- Read .html files from workspace templates/
- Call `mybb_template_batch_write` with theme's template set sid
- Template names must match master template names
- Return deployment stats

**Verification:**
- [ ] Template overrides appear in theme's template set

### Task 3.5: Install Plugin Workflow Orchestration
**Scope:** Main install_plugin method
**Files to Modify:** `plugin_manager/manager.py`
**Specifications:**
- Orchestrate file + template + activation + DB update
- Clear error messages for each failure mode
- Prominent ACP activation warning

**Verification:**
- [ ] Plugin visible in TestForum plugins list
- [ ] Warning message displayed

### Task 3.6: Install Theme Workflow Orchestration
**Scope:** Main install_theme method
**Files to Modify:** `plugin_manager/manager.py`
**Specifications:**
- Orchestrate stylesheet + template override deployment
- Update database status
- Display activation instructions

**Verification:**
- [ ] Theme stylesheets deployed
- [ ] Template overrides deployed
- [ ] Theme visible in ACP

---
## Phase 4 -- Sync Workflow
<!-- ID: phase_4 -->

**Objective:** Implement sync workflows for BOTH plugins AND themes, integrating with mybb_sync infrastructure.

### Plugin Sync Workflow

**Key Tasks (Plugins):**

1. **Implement manual plugin sync**
   - Detect changed files in workspace vs TestForum
   - Copy changed PHP/language files
   - Update templates via MCP
   - Log sync in history

2. **Extend PathRouter for plugins (optional)**
   - Add `plugin_template` type to ParsedPath
   - Pattern: `plugins/{codename}/templates/{template}.html`
   - Add handler in watcher for plugin template changes

3. **Implement plugin template exporter**
   - Export plugin templates from DB to workspace
   - Mirror structure of TemplateExporter

4. **Implement plugin template importer**
   - Import plugin templates from workspace to DB
   - Handle template naming convention (`{codename}_{name}`)

### Theme Sync Workflow

**Key Tasks (Themes):**

5. **Implement manual theme sync**
   - Detect changed CSS files in workspace
   - Push stylesheet updates via `mybb_write_stylesheet`
   - Detect changed template override files
   - Push template updates via `mybb_template_batch_write`
   - Log sync in history

6. **Integrate with existing mybb_sync stylesheet sync**
   - Leverage `mybb_sync_export_stylesheets` for pulling from DB
   - Leverage existing FileWatcher for auto-sync (stylesheets already supported)
   - Theme workspace stylesheets can be symlinked or copied to mybb_sync directory

7. **Implement theme stylesheet exporter**
   - Export theme stylesheets from DB to workspace
   - Use `mybb_list_stylesheets(tid)` + `mybb_read_stylesheet(sid)`
   - Mirror structure for local editing

8. **Implement theme template override exporter**
   - Export template overrides from DB to workspace
   - Use `mybb_template_batch_read` with theme's template set sid
   - Only export templates that differ from master

**Deliverables:**
- `plugin_manager/manager.py` - PluginManager.sync_plugin() AND sync_theme()
- `mybb_mcp/mybb_mcp/sync/router.py` - Extended PathRouter (optional)
- `mybb_mcp/mybb_mcp/sync/plugin_templates.py` - Plugin template sync (optional)

**Acceptance Criteria (Plugins):**
- [ ] Manual sync copies changed PHP/language files
- [ ] Plugin templates synced via MCP
- [ ] History logged for sync
- [ ] (Optional) PathRouter handles plugin template paths
- [ ] (Optional) FileWatcher triggers on plugin template changes

**Acceptance Criteria (Themes):**
- [ ] Manual sync pushes changed stylesheets via `mybb_write_stylesheet`
- [ ] Manual sync pushes changed template overrides via MCP
- [ ] Theme stylesheets can be exported to workspace
- [ ] Theme template overrides can be exported to workspace
- [ ] History logged for theme sync
- [ ] (Optional) Integration with existing FileWatcher for auto-sync

**Dependencies:** Phase 3 (Install Workflow)

**Estimated LOC:** 300-400

**Note:** PathRouter extension is optional for v1. Manual sync is sufficient. Auto-sync via watcher is a nice-to-have enhancement. Theme stylesheet sync already partially supported via existing mybb_sync infrastructure.

**MCP Tools for Theme Sync:**
- `mybb_list_stylesheets(tid)` - Get stylesheet IDs for theme
- `mybb_read_stylesheet(sid)` - Read CSS content
- `mybb_write_stylesheet(sid, css)` - Write CSS content (auto-caches)
- `mybb_sync_export_stylesheets(theme_name)` - Bulk export to disk
- `mybb_template_batch_read(templates, sid)` - Read template overrides
- `mybb_template_batch_write(templates, sid)` - Write template overrides

---
## Phase 5 -- Export Workflow
<!-- ID: phase_5 -->

**Objective:** Implement export workflows to package BOTH plugins AND themes for distribution.

### Plugin Export Workflow

**Key Tasks (Plugins):**

1. **Implement plugin meta.json validation**
   - Check required fields are present
   - Validate file references exist
   - Return validation errors

2. **Implement plugin README generation**
   - Call MCP `mybb_analyze_plugin` for hook/setting info
   - Generate markdown README from analysis
   - Include installation instructions

3. **Implement plugin ZIP packaging**
   - Collect files per meta.json file mappings
   - Create ZIP with proper structure:
     ```
     {codename}.zip/
     +-- {codename}.php
     +-- languages/english/{codename}.lang.php
     +-- README.md
     ```
   - Exclude test files, dev artifacts

### Theme Export Workflow

**Key Tasks (Themes):**

4. **Implement theme meta.json validation**
   - Check required theme fields (stylesheets array, etc.)
   - Validate stylesheet file references exist
   - Validate template override files exist
   - Return validation errors

5. **Implement theme README generation**
   - List included stylesheets
   - List template overrides
   - Document parent_theme and color_scheme
   - Include installation instructions (ACP import or manual)

6. **Implement theme ZIP packaging**
   - Collect stylesheets from workspace stylesheets/
   - Collect template overrides from workspace templates/
   - Include any images from images/
   - Create ZIP with proper structure:
     ```
     {codename}.zip/
     +-- stylesheets/
     |   +-- global.css
     |   +-- colors.css
     +-- templates/
     |   +-- header.html (overrides)
     +-- images/
     +-- README.md
     ```
   - Optionally generate MyBB XML theme export format

### Shared Tasks

7. **Version management**
   - Update version in meta.json
   - Update version in PHP file (plugins only)
   - Tag in history

**Deliverables:**
- `plugin_manager/manager.py` - PluginManager.export_plugin() AND export_theme()
- `plugin_manager/packager.py` - ZIP creation helpers (plugins and themes)

**Acceptance Criteria (Plugins):**
- [ ] Validation catches missing required fields
- [ ] README generated from analysis
- [ ] ZIP created with correct structure
- [ ] ZIP can be installed manually in MyBB
- [ ] History logged for export

**Acceptance Criteria (Themes):**
- [ ] Theme validation catches missing stylesheet references
- [ ] Theme README generated with stylesheet/template list
- [ ] Theme ZIP created with correct structure
- [ ] Theme ZIP includes stylesheets/, templates/, images/
- [ ] (Optional) MyBB XML export format generated
- [ ] History logged for theme export

**Dependencies:** Phase 2 (Create Workflow) - can run in parallel with Phase 3/4

**Estimated LOC:** 200-250

---
## Phase 6 -- MCP Integration
<!-- ID: phase_6 -->

**Objective:** Refactor all MCP plugin/theme tools to delegate to PluginManager, creating a unified system with single source of truth.

**Sub-Plan Document:** `architecture/mcp_integration/MCP_INTEGRATION_PLAN.md`

**Strategy:** DELEGATE pattern - MCP tools become thin wrappers calling PluginManager methods.

### Phase 6a: Core Plugin Tools (HIGH PRIORITY)

**Tasks:**

1. **Refactor `mybb_create_plugin`**
   - Map MCP args to `PluginManager.create_plugin()` params
   - Convert hooks from `List[str]` to `List[Dict]` format
   - Return workspace path and project ID in response
   - File: `server.py:1409-1411`

2. **Refactor `mybb_plugin_activate`**
   - For managed plugins: Call `PluginManager.install_plugin()`
   - For unmanaged plugins: Legacy cache update with deprecation warning
   - File: `server.py:1511-1531`

3. **Refactor `mybb_plugin_deactivate`**
   - For managed plugins: Call `PluginManager.uninstall_plugin()`
   - For unmanaged plugins: Legacy cache removal with deprecation warning
   - File: `server.py:1533-1550`

4. **Add deprecation warning to `tools/plugins.py:create_plugin()`**
   - Log warning when called directly
   - Point users to MCP tool

### Phase 6b: List/Query Tools (MEDIUM PRIORITY)

**Tasks:**

1. **Refactor `mybb_list_plugins`**
   - Query both workspace AND TestForum
   - Show unified view with source indicators
   - Mark managed plugins distinctly

2. **Refactor `mybb_read_plugin`**
   - Check workspace first for managed plugins
   - Fallback to TestForum for unmanaged
   - Indicate source in response

3. **Refactor `mybb_analyze_plugin`**
   - Load meta.json for managed plugins (rich data)
   - Regex fallback for unmanaged plugins
   - Show workspace status in analysis

4. **Refactor `mybb_plugin_is_installed`**
   - Check plugin_manager DB status
   - Check MyBB cache status
   - Check file existence
   - Show comprehensive status

### Phase 6c: Theme Tools (MEDIUM PRIORITY)

**Tasks:**

1. **Add `mybb_create_theme` tool**
   - Add tool definition to `all_tools` list
   - Delegate to `PluginManager.create_theme()`
   - Return workspace path and project ID

2. **Refactor `mybb_list_themes`**
   - Include workspace themes alongside MyBB DB themes
   - Show managed/unmanaged status

3. **Enhance stylesheet tools (hybrid mode)**
   - `mybb_read_stylesheet`: Check workspace for managed themes
   - `mybb_write_stylesheet`: Write to workspace for managed themes

### Phase 6d: Sync Enhancement (LOW PRIORITY)

**Tasks:**

1. **Enhance `mybb_sync_status`**
   - Add plugin_manager workspace statistics
   - Show managed plugin/theme counts
   - Show installation status

### Import Strategy

Add to `server.py` (near top of `handle_tool()`):

```python
import sys
from pathlib import Path

pm_path = Path(__file__).parent.parent.parent.parent / "plugin_manager"
if str(pm_path.parent) not in sys.path:
    sys.path.insert(0, str(pm_path.parent))

from plugin_manager.manager import PluginManager
```

**Deliverables:**
- `mybb_mcp/mybb_mcp/server.py` - 12 tool handlers refactored (~200 lines)
- `mybb_mcp/mybb_mcp/server.py` - `mybb_create_theme` tool added
- `mybb_mcp/mybb_mcp/tools/plugins.py` - Deprecation warning added
- `mybb_mcp/tests/test_plugin_manager_integration.py` - Integration tests

**Acceptance Criteria (Phase 6a):**
- [ ] `mybb_create_plugin` creates in workspace via PluginManager
- [ ] `mybb_plugin_activate` calls `install_plugin()` for managed
- [ ] `mybb_plugin_deactivate` calls `uninstall_plugin()` for managed
- [ ] Legacy plugins still work with deprecation warnings

**Acceptance Criteria (Phase 6b):**
- [ ] `mybb_list_plugins` shows both workspace and TestForum plugins
- [ ] `mybb_read_plugin` reads from workspace for managed plugins
- [ ] `mybb_analyze_plugin` uses meta.json for managed plugins
- [ ] `mybb_plugin_is_installed` shows comprehensive status

**Acceptance Criteria (Phase 6c):**
- [ ] `mybb_create_theme` tool exists and works
- [ ] `mybb_list_themes` shows workspace themes
- [ ] Stylesheet tools support managed themes

**Acceptance Criteria (Phase 6d):**
- [ ] `mybb_sync_status` includes plugin_manager statistics

**Dependencies:** Phases 1-5 (plugin_manager must be complete)

**Estimated LOC:** 200-250 lines (mostly in server.py)

---
## Milestone Tracking
<!-- ID: milestone_tracking -->

| Milestone | Target | Owner | Status | Evidence |
|-----------|--------|-------|--------|----------|
| Foundation Complete | Phase 1 | Coder | Pending | tests/test_database.py passes |
| Plugin Create Works | Phase 2 | Coder | Pending | Manual test creates plugin |
| Theme Create Works | Phase 2 | Coder | Pending | Manual test creates theme |
| Plugin Install Works | Phase 3 | Coder | Pending | Plugin visible in TestForum |
| Theme Install Works | Phase 3 | Coder | Pending | Theme stylesheets deployed |
| Plugin Sync Works | Phase 4 | Coder | Pending | Plugin changes propagate correctly |
| Theme Sync Works | Phase 4 | Coder | Pending | Theme stylesheet changes propagate |
| Plugin Export Works | Phase 5 | Coder | Pending | Plugin ZIP installs in fresh MyBB |
| Theme Export Works | Phase 5 | Coder | Pending | Theme ZIP installs in fresh MyBB |
| MCP Tools Integrated | Phase 6 | Coder | Pending | `mybb_create_plugin` uses PluginManager |
| Theme MCP Tool Added | Phase 6 | Coder | Pending | `mybb_create_theme` tool works |
| Skill Interface | Post-Phase | Coder | Deferred | `/plugin` and `/theme` commands work |

---
## Implementation Order
<!-- ID: implementation_order -->

```
Phase 1 (Foundation)
    |
    v
Phase 2 (Create) ----+
    |                |
    v                v
Phase 3 (Install)  Phase 5 (Export)  [Can parallelize]
    |
    v
Phase 4 (Sync)
    |
    v
Phase 6 (MCP Integration)  <-- Ties everything together
    |
    v
Skill Interface (Post-MVP)
```

**Recommended Execution:**
1. Complete Phase 1 first (all other phases depend on it)
2. Complete Phase 2 (core workflow, tests create functionality)
3. Phase 3 and Phase 5 can be done in parallel by different sessions
4. Phase 4 last (depends on install working)
5. Phase 6 after Phase 4 (requires all plugin_manager methods working)
6. Skill interface is post-MVP polish

---
## Retro Notes & Adjustments
<!-- ID: retro_notes -->

*Space for lessons learned after each phase completes.*

- Phase 1:
- Phase 2:
- Phase 3:
- Phase 4:
- Phase 5:

---
