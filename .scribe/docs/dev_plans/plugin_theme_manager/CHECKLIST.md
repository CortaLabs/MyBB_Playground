
# Acceptance Checklist -- plugin-theme-manager
**Author:** ArchitectAgent
**Version:** v1.1
**Status:** Active
**Last Updated:** 2026-01-18 04:38:00 UTC

> Granular implementation checklist for Coder agent verification. Covers BOTH plugins AND themes.

---
## Documentation Hygiene
<!-- ID: documentation_hygiene -->
- [x] Architecture guide updated (proof: ARCHITECTURE_GUIDE.md v1.0)
- [x] Phase plan current (proof: PHASE_PLAN.md v1.0)
- [x] Research documents complete (proof: research/ directory - 5 docs)
- [ ] README.md created for plugin_manager module
- [ ] API documentation generated

---
## Phase 1: Foundation
<!-- ID: phase_1 -->

### Directory Structure (Plugins)
- [ ] `plugins/` directory created at repo root
- [ ] `plugins/public/` directory created
- [ ] `plugins/private/` directory created
- [ ] `.gitkeep` files in empty plugin directories

### Directory Structure (Themes)
- [ ] `themes/` directory created at repo root
- [ ] `themes/public/` directory created
- [ ] `themes/private/` directory created
- [ ] `.gitkeep` files in empty theme directories

### Directory Structure (Shared)
- [ ] `.plugin_manager/` directory created
- [ ] `.plugin_manager/schema/` directory created

### Database Schema
- [ ] `.plugin_manager/schema/projects.sql` created
- [ ] `projects` table defined with all columns
- [ ] `projects.type` column exists (values: 'plugin', 'theme')
- [ ] `history` table defined
- [ ] Indexes defined (`idx_projects_codename`, `idx_history_project`)
- [ ] Schema SQL is valid (can execute without errors)

### ProjectDatabase Class (Plugins)
- [ ] `plugin_manager/database.py` file created
- [ ] `ProjectDatabase.__init__()` connects to SQLite
- [ ] `ProjectDatabase.create_tables()` executes schema
- [ ] `ProjectDatabase.add_project(type='plugin')` inserts plugin
- [ ] `ProjectDatabase.get_project()` retrieves by codename
- [ ] `ProjectDatabase.update_project()` updates fields
- [ ] `ProjectDatabase.list_projects(type='plugin')` filters to plugins only
- [ ] `ProjectDatabase.add_history()` logs actions
- [ ] All database methods handle errors gracefully

### ProjectDatabase Class (Themes)
- [ ] `ProjectDatabase.add_project(type='theme')` inserts theme
- [ ] `ProjectDatabase.list_projects(type='theme')` filters to themes only
- [ ] `ProjectDatabase.list_projects(type=None)` returns both plugins and themes
- [ ] Theme projects have type='theme' in database
- [ ] History entries work for theme projects
- [ ] Theme-specific metadata stored correctly

### meta.json Schema (Plugins)
- [ ] `plugin_manager/schema.py` file created
- [ ] JSON Schema definition for plugin meta.json
- [ ] `validate_meta()` function implemented
- [ ] Default plugin meta.json template defined
- [ ] Plugin validation catches missing required fields
- [ ] Plugin validation catches invalid field types

### meta.json Schema (Themes)
- [ ] JSON Schema definition for theme meta.json
- [ ] Theme-specific fields defined: `stylesheets`, `template_overrides`, `parent_theme`, `color_scheme`
- [ ] `validate_theme_meta()` function implemented or type-aware validation
- [ ] Default theme meta.json template defined
- [ ] Theme validation catches missing `stylesheets` array
- [ ] Theme validation catches invalid `parent_theme` reference

### Gitignore Updates
- [ ] `plugins/private/` added to .gitignore
- [ ] `themes/private/` added to .gitignore
- [ ] `.plugin_manager/projects.db` added to .gitignore

### Phase 1 Verification
- [ ] `pytest tests/test_database.py` passes (includes theme tests)
- [ ] `pytest tests/test_schema.py` passes (includes theme schema tests)
- [ ] Manual DB creation/query works for plugins
- [ ] Manual DB creation/query works for themes

---
## Phase 2: Create Workflow
<!-- ID: phase_2 -->

### PluginWorkspace Class
- [ ] `plugin_manager/workspace.py` file created
- [ ] `PluginWorkspace.__init__()` sets workspace root
- [ ] `PluginWorkspace.create_workspace()` creates directory structure
- [ ] Creates `src/` subdirectory
- [ ] Creates `languages/english/` subdirectory
- [ ] Creates `templates/` subdirectory
- [ ] Creates `tests/` subdirectory
- [ ] `PluginWorkspace.get_workspace_path()` finds plugin
- [ ] `PluginWorkspace.read_meta()` parses meta.json
- [ ] `PluginWorkspace.write_meta()` generates meta.json
- [ ] `PluginWorkspace.validate_workspace()` returns errors

### ThemeWorkspace Class
- [ ] `plugin_manager/theme_workspace.py` file created
- [ ] `ThemeWorkspace.__init__()` sets workspace root
- [ ] `ThemeWorkspace.create_workspace()` creates theme directory structure
- [ ] Creates `stylesheets/` subdirectory
- [ ] Creates `templates/` subdirectory (for overrides)
- [ ] Creates `images/` subdirectory
- [ ] `ThemeWorkspace.get_workspace_path()` finds theme
- [ ] `ThemeWorkspace.read_meta()` parses theme meta.json
- [ ] `ThemeWorkspace.write_meta()` generates theme meta.json
- [ ] `ThemeWorkspace.validate_workspace()` returns theme-specific errors

### MCP Client (Plugins)
- [ ] `plugin_manager/mcp_client.py` file created
- [ ] `call_create_plugin()` invokes MCP tool
- [ ] Response parsing extracts file paths
- [ ] Error handling for connection failures
- [ ] Error handling for MCP tool errors

### MCP Client (Themes)
- [ ] `call_list_themes()` invokes `mybb_list_themes`
- [ ] `call_list_stylesheets(tid)` invokes `mybb_list_stylesheets`
- [ ] `call_read_stylesheet(sid)` invokes `mybb_read_stylesheet`
- [ ] Response parsing for theme data
- [ ] Parent theme validation via MCP

### Create Plugin Workflow
- [ ] `plugin_manager/manager.py` file created
- [ ] `PluginManager.__init__()` initializes components
- [ ] `PluginManager.create_plugin()` orchestrates workflow
- [ ] Workspace created with correct structure
- [ ] MCP scaffold generated
- [ ] Files moved from TestForum to workspace
- [ ] meta.json generated with correct data
- [ ] README.md template generated
- [ ] Project registered in database with type='plugin'
- [ ] History entry logged
- [ ] Success message returned with next steps

### Create Theme Workflow
- [ ] `PluginManager.create_theme()` orchestrates theme creation
- [ ] Theme workspace created with correct structure
- [ ] Scaffold CSS files generated (global.css, colors.css)
- [ ] Theme meta.json generated with stylesheets array
- [ ] Theme meta.json includes `parent_theme` field
- [ ] Theme meta.json includes `color_scheme` field
- [ ] Theme meta.json includes `template_overrides` array
- [ ] README.md template generated for theme
- [ ] Project registered in database with type='theme'
- [ ] History entry logged for theme creation
- [ ] Success message returned with next steps

### Phase 2 Verification (Plugins)
- [ ] `pytest tests/test_workspace.py` passes
- [ ] `pytest tests/test_manager.py::test_create_plugin` passes
- [ ] Manual test: `create_plugin("test_plugin")` creates full workspace

### Phase 2 Verification (Themes)
- [ ] `pytest tests/test_theme_workspace.py` passes
- [ ] `pytest tests/test_manager.py::test_create_theme` passes
- [ ] Manual test: `create_theme("test_theme")` creates full workspace
- [ ] Theme workspace has stylesheets/, templates/, images/
- [ ] Theme meta.json contains valid stylesheets array

---
## Phase 3: Install Workflow
<!-- ID: phase_3 -->

### File Deployer (Plugins)
- [ ] `plugin_manager/deployer.py` file created
- [ ] `deploy_plugin_file()` copies PHP to TestForum
- [ ] Backup created for existing files
- [ ] `deploy_language_files()` copies language files
- [ ] Handle missing source files gracefully
- [ ] Error messages are clear

### Template Deployer (Plugins)
- [ ] `deploy_templates()` reads workspace templates
- [ ] Templates deployed via `mybb_template_batch_write`
- [ ] Template names follow `{codename}_{name}` convention
- [ ] Templates created with sid=-2 (master)
- [ ] Deployment count returned

### Stylesheet Deployer (Themes)
- [ ] `deploy_stylesheets()` reads workspace CSS files
- [ ] Calls `mybb_list_stylesheets(tid)` to get existing IDs
- [ ] Calls `mybb_write_stylesheet(sid, css)` for each stylesheet
- [ ] Handles mapping of local CSS files to DB stylesheet IDs
- [ ] Deployment count returned
- [ ] Error handling for unknown stylesheets
- [ ] CSS changes visible in forum immediately (auto-cache)

### Template Override Deployer (Themes)
- [ ] `deploy_theme_templates()` reads workspace template overrides
- [ ] Calls `mybb_template_batch_write` with theme's template set sid
- [ ] Template names match master template names
- [ ] Overrides appear in theme's template set
- [ ] Deployment count returned

### Install Plugin Workflow
- [ ] `PluginManager.install_plugin()` implemented
- [ ] File deployment executed
- [ ] Template deployment executed
- [ ] Cache activation via MCP executed
- [ ] Database status updated to 'installed'
- [ ] `installed_at` timestamp set
- [ ] History entry logged
- [ ] ACP WARNING displayed prominently

### Install Theme Workflow
- [ ] `PluginManager.install_theme()` implemented
- [ ] Stylesheet deployment executed via MCP
- [ ] Template override deployment executed via MCP
- [ ] Theme appears in MyBB ACP Themes list
- [ ] Database status updated to 'installed'
- [ ] `installed_at` timestamp set
- [ ] History entry logged for theme installation
- [ ] Instructions displayed for activating theme in ACP

### Phase 3 Verification (Plugins)
- [ ] `pytest tests/test_deployer.py` passes
- [ ] `pytest tests/test_manager.py::test_install_plugin` passes
- [ ] Manual test: Plugin appears in TestForum plugins list
- [ ] Manual test: ACP activation works and hooks execute

### Phase 3 Verification (Themes)
- [ ] `pytest tests/test_deployer.py::test_deploy_stylesheets` passes
- [ ] `pytest tests/test_manager.py::test_install_theme` passes
- [ ] Manual test: Theme stylesheets updated in forum
- [ ] Manual test: Template overrides visible in theme set
- [ ] Manual test: Theme can be set as default in ACP

---
## Phase 4: Sync Workflow
<!-- ID: phase_4 -->

### Manual Plugin Sync
- [ ] `PluginManager.sync_plugin()` implemented
- [ ] Detects changed files in workspace
- [ ] Copies changed PHP files to TestForum
- [ ] Copies changed language files
- [ ] Updates templates via MCP
- [ ] History entry logged
- [ ] Sync statistics returned

### Manual Theme Sync
- [ ] `PluginManager.sync_theme()` implemented
- [ ] Detects changed CSS files in workspace
- [ ] Pushes stylesheet updates via `mybb_write_stylesheet`
- [ ] Detects changed template override files
- [ ] Pushes template updates via `mybb_template_batch_write`
- [ ] History entry logged for theme sync
- [ ] Sync statistics returned

### Theme Stylesheet Export
- [ ] Export stylesheets from DB to workspace
- [ ] Uses `mybb_list_stylesheets(tid)` to get IDs
- [ ] Uses `mybb_read_stylesheet(sid)` to get CSS content
- [ ] Writes CSS files to workspace stylesheets/
- [ ] Preserves stylesheet names as filenames

### Theme Template Override Export
- [ ] Export template overrides from DB to workspace
- [ ] Uses `mybb_template_batch_read` with theme's template set sid
- [ ] Only exports templates that differ from master
- [ ] Writes HTML files to workspace templates/

### PathRouter Extension (Optional - Plugins)
- [ ] `plugin_template` type added to ParsedPath
- [ ] Parse pattern: `plugins/{codename}/templates/{name}.html`
- [ ] Build path function for plugin templates
- [ ] Watcher handles plugin template changes (optional)

### mybb_sync Integration (Optional - Themes)
- [ ] Theme stylesheets can leverage existing sync infrastructure
- [ ] `mybb_sync_export_stylesheets` used for bulk export
- [ ] Existing FileWatcher already supports stylesheet sync

### Phase 4 Verification (Plugins)
- [ ] `pytest tests/test_manager.py::test_sync_plugin` passes
- [ ] Manual test: Edit plugin file in workspace, sync, verify in TestForum
- [ ] (Optional) Watcher test: Edit plugin template, auto-syncs

### Phase 4 Verification (Themes)
- [ ] `pytest tests/test_manager.py::test_sync_theme` passes
- [ ] Manual test: Edit CSS in workspace, sync, verify in forum
- [ ] Manual test: Edit template override, sync, verify in forum
- [ ] Export test: Export theme from DB to workspace succeeds
- [ ] (Optional) Integration with existing FileWatcher verified

---
## Phase 5: Export Workflow
<!-- ID: phase_5 -->

### Plugin Validation
- [ ] `validate_for_export()` checks required plugin fields
- [ ] Validates file references exist
- [ ] Returns list of validation errors

### Theme Validation
- [ ] `validate_theme_for_export()` checks required theme fields
- [ ] Validates stylesheet file references exist
- [ ] Validates template override files exist
- [ ] Returns list of validation errors
- [ ] Checks `stylesheets` array is non-empty

### Plugin README Generation
- [ ] Calls `mybb_analyze_plugin` for analysis
- [ ] Generates markdown README
- [ ] Includes installation instructions
- [ ] Includes hook list
- [ ] Includes settings list

### Theme README Generation
- [ ] Generates markdown README for theme
- [ ] Lists included stylesheets
- [ ] Lists template overrides
- [ ] Documents `parent_theme` if set
- [ ] Documents `color_scheme` variables
- [ ] Includes theme installation instructions

### Plugin ZIP Packaging
- [ ] `plugin_manager/packager.py` file created
- [ ] `create_plugin_zip()` implemented
- [ ] Plugin ZIP structure is correct:
  - `{codename}.php` at root
  - `languages/english/{codename}.lang.php`
  - `README.md`
- [ ] Test files excluded
- [ ] Dev artifacts excluded

### Theme ZIP Packaging
- [ ] `create_theme_zip()` implemented
- [ ] Theme ZIP structure is correct:
  - `stylesheets/` directory with CSS files
  - `templates/` directory with override HTML files
  - `images/` directory with assets
  - `README.md`
- [ ] (Optional) MyBB XML export format generated
- [ ] Test files excluded
- [ ] Dev artifacts excluded

### Export Plugin Workflow
- [ ] `PluginManager.export_plugin()` implemented
- [ ] Validation executed first
- [ ] README generated
- [ ] ZIP created
- [ ] Version updated in meta.json
- [ ] History entry logged
- [ ] ZIP path returned

### Export Theme Workflow
- [ ] `PluginManager.export_theme()` implemented
- [ ] Theme validation executed first
- [ ] Theme README generated
- [ ] Theme ZIP created with stylesheets/templates/images
- [ ] Version updated in theme meta.json
- [ ] History entry logged for theme export
- [ ] ZIP path returned

### Phase 5 Verification (Plugins)
- [ ] `pytest tests/test_packager.py` passes
- [ ] `pytest tests/test_manager.py::test_export_plugin` passes
- [ ] Manual test: Plugin ZIP can be installed in fresh MyBB

### Phase 5 Verification (Themes)
- [ ] `pytest tests/test_packager.py::test_theme_packaging` passes
- [ ] `pytest tests/test_manager.py::test_export_theme` passes
- [ ] Manual test: Theme ZIP has correct structure
- [ ] Manual test: Theme README contains stylesheet list
- [ ] (Optional) XML export can be imported via ACP

---
## Phase 6: MCP Integration
<!-- ID: phase_6 -->

**Sub-Plan:** `architecture/mcp_integration/MCP_INTEGRATION_PLAN.md`

### Phase 6a: Core Plugin Tools (HIGH PRIORITY)

#### mybb_create_plugin Refactoring
- [ ] Handler in `server.py:1409-1411` updated
- [ ] Maps MCP args to PluginManager.create_plugin() params
- [ ] Converts hooks from List[str] to List[Dict] format
- [ ] Returns workspace path in response
- [ ] Returns project ID in response
- [ ] Creates plugin in workspace (not TestForum directly)

#### mybb_plugin_activate Refactoring
- [ ] Handler in `server.py:1511-1531` updated
- [ ] Checks if plugin is managed (in plugin_manager DB)
- [ ] Managed plugins: Calls PluginManager.install_plugin()
- [ ] Unmanaged plugins: Legacy cache update with warning
- [ ] Response indicates managed vs legacy mode

#### mybb_plugin_deactivate Refactoring
- [ ] Handler in `server.py:1533-1550` updated
- [ ] Checks if plugin is managed
- [ ] Managed plugins: Calls PluginManager.uninstall_plugin()
- [ ] Unmanaged plugins: Legacy cache removal with warning
- [ ] Workspace copy preserved after uninstall

#### Deprecation Warning
- [ ] `tools/plugins.py:create_plugin()` logs deprecation warning
- [ ] Warning directs users to MCP tool workflow

### Phase 6b: List/Query Tools (MEDIUM PRIORITY)

#### mybb_list_plugins Refactoring
- [ ] Queries workspace plugins via plugin_manager DB
- [ ] Queries TestForum plugins directory
- [ ] Shows unified view with source indicators
- [ ] Marks managed plugins distinctly

#### mybb_read_plugin Refactoring
- [ ] Checks workspace first for managed plugins
- [ ] Falls back to TestForum for unmanaged
- [ ] Response indicates source (Workspace vs TestForum)

#### mybb_analyze_plugin Refactoring
- [ ] Loads meta.json for managed plugins
- [ ] Regex fallback for unmanaged plugins
- [ ] Shows hooks from meta.json (not regex)
- [ ] Shows settings from meta.json
- [ ] Shows workspace status and visibility

#### mybb_plugin_is_installed Refactoring
- [ ] Checks plugin_manager DB for workspace status
- [ ] Checks MyBB cache for activation status
- [ ] Checks TestForum for file existence
- [ ] Response shows all three status dimensions

### Phase 6c: Theme Tools (MEDIUM PRIORITY)

#### mybb_create_theme Tool (NEW)
- [ ] Tool definition added to `all_tools` list in server.py
- [ ] Input schema defined (codename, name, description, author, etc.)
- [ ] Handler delegates to PluginManager.create_theme()
- [ ] Returns workspace path and project ID
- [ ] Supports stylesheets parameter
- [ ] Supports parent_theme parameter

#### mybb_list_themes Refactoring
- [ ] Queries workspace themes via plugin_manager DB
- [ ] Queries MyBB database themes
- [ ] Shows unified view with source indicators
- [ ] Marks managed themes distinctly

#### Stylesheet Tools Enhancement
- [ ] mybb_read_stylesheet checks workspace for managed themes
- [ ] mybb_write_stylesheet writes to workspace for managed themes
- [ ] Falls back to DB operations for unmanaged themes

### Phase 6d: Sync Enhancement (LOW PRIORITY)

#### mybb_sync_status Enhancement
- [ ] Includes plugin_manager workspace statistics
- [ ] Shows managed plugin count
- [ ] Shows managed theme count
- [ ] Shows installed plugin/theme counts

### Import Strategy Verification
- [ ] sys.path manipulation added to server.py
- [ ] PluginManager imports successfully
- [ ] No circular import issues
- [ ] Works in both direct and MCP execution contexts

### Phase 6 Verification
- [ ] `pytest mybb_mcp/tests/test_plugin_manager_integration.py` passes
- [ ] Manual test: `mybb_create_plugin` creates in workspace
- [ ] Manual test: `mybb_plugin_activate` deploys managed plugin to TestForum
- [ ] Manual test: `mybb_list_plugins` shows both sources
- [ ] Manual test: `mybb_create_theme` creates theme in workspace
- [ ] Legacy plugins still work with deprecation warnings
- [ ] All response formats preserved (markdown)

---
## Integration Tests
<!-- ID: integration_tests -->

### Plugin Integration
- [ ] Full plugin workflow: create -> install -> sync -> export
- [ ] Private plugin visibility works
- [ ] Public plugin visibility works
- [ ] Plugin database state consistent through workflow
- [ ] Plugin history tracking complete

### Theme Integration
- [ ] Full theme workflow: create -> install -> sync -> export
- [ ] Private theme visibility works
- [ ] Public theme visibility works
- [ ] Theme database state consistent through workflow
- [ ] Theme history tracking complete

### Cross-Type Tests
- [ ] `list_projects(type=None)` returns both plugins and themes
- [ ] `list_projects(type='plugin')` returns only plugins
- [ ] `list_projects(type='theme')` returns only themes
- [ ] Plugin and theme with same codename handled correctly (if allowed)
- [ ] Mixed workflows don't interfere with each other

### MCP Integration Tests (Phase 6)
- [ ] Full MCP workflow: mybb_create_plugin -> mybb_plugin_activate -> mybb_plugin_deactivate
- [ ] Full MCP theme workflow: mybb_create_theme -> theme activation
- [ ] Mixed workflow: Create via MCP, manage via plugin_manager CLI (if any)
- [ ] Legacy plugin activation still works with warning
- [ ] mybb_list_plugins shows both workspace and TestForum plugins
- [ ] mybb_analyze_plugin works for both managed and unmanaged plugins

---
## Final Verification
<!-- ID: final_verification -->

- [ ] All plugin checklist items checked with proofs attached
- [ ] All theme checklist items checked with proofs attached
- [ ] All pytest tests pass (`pytest tests/ -v`)
- [ ] Manual QA completed for plugin workflows
- [ ] Manual QA completed for theme workflows
- [ ] Review Agent approved implementation (plugins AND themes)
- [ ] Documentation complete
- [ ] Retro completed and lessons learned documented

---
## Post-MVP (Deferred)
<!-- ID: post_mvp -->

- [ ] Claude Code Skill interface (`/plugin` commands)
- [ ] Claude Code Skill interface (`/theme` commands)
- [ ] Dependency management between plugins
- [ ] Auto-sync via extended FileWatcher (plugins)
- [ ] Auto-sync via extended FileWatcher (themes)
- [ ] Multi-forum deployment support
- [ ] Theme inheritance validation (parent_theme chain)
- [ ] MyBB XML theme import/export support

---
