# Phase Plan - MyBB Forge v2

**Author:** MyBB-ArchitectAgent
**Version:** v1.1 (Revised Phase 4+5 per R8+R9 Research)
**Status:** Ready for Implementation
**Last Updated:** 2026-01-19
**Confidence:** 0.95

**Revision History:**
- v1.1 (2026-01-19): Revised Phase 4 and Phase 5 based on R8+R9 research findings. Phase 4 scope reduced from 500+ lines to ~160 lines by leveraging existing db-sync infrastructure. Added multi-theme support to Phase 5. Moved Bulk Update to Phase 6.

> Implementation roadmap for MyBB Forge v2 refactoring. Each phase contains bounded task packages that coders can execute independently.

---

## Phase Overview
<!-- ID: phase_overview -->

| Phase | Goal | Task Packages | Est. Effort | Dependencies |
|-------|------|---------------|-------------|--------------|
| Phase 1 | Foundation & Config | 4 packages | 4-6 hours | None |
| Phase 2 | Server Modularization (Simple) | 4 packages | 6-8 hours | Phase 1 |
| Phase 3 | Server Modularization (Complex) | 5 packages | 8-10 hours | Phase 2 |
| Phase 4 | **Plugin Template Disk-First Sync** (REVISED) | 6 packages | 4-6 hours | Phase 1 |
| Phase 5 | **DB-Sync Optimizations + Multi-Theme** (REVISED) | 3 packages | 4-6 hours | Phase 4 |
| Phase 6 | Git Subtree & Finalization | 5 packages | 6-8 hours | All |

**Total Estimated Effort:** 32-44 hours of coder time

**Revision Notes (2026-01-19):**
- Phase 4 revised based on R8+R9 research: db-sync is 90% complete, only ~145 lines needed
- Phase 5 revised: Added multi-theme support, moved Bulk Update to Phase 6
- Phase 4 scope REDUCED from 8-10 hours to 4-6 hours (leveraging existing infrastructure)

---

## Phase 1 - Foundation & Configuration
<!-- ID: phase_1 -->

**Objective:** Establish configuration system and prepare infrastructure for subsequent phases.

**Why First:** All other phases depend on ForgeConfig for defaults and settings.

### Task Package 1.1: Create ForgeConfig Class

**Scope:** Create the YAML+ENV configuration loader

**Files to Create:**
- `plugin_manager/forge_config.py` (new, ~120 lines)

**Files to Modify:**
- None

**Specifications:**
1. Create `ForgeConfig` class with constructor accepting `repo_root: Path`
2. Implement `_load()` method that:
   - Loads defaults first
   - Merges `.mybb-forge.yaml` if exists
   - Loads `.mybb-forge.env` values
3. Implement `_get_defaults()` returning default config dict
4. Implement `_deep_merge()` for recursive dict merging
5. Add properties: `developer_name`, `developer_website`, `developer_email`
6. Add method: `get_subtree_remote(subtree_key: str) -> Optional[str]`
7. Add method: `get_subtree_config(prefix: str) -> Optional[dict]`
8. Add method: `get_sync_settings() -> dict`

**Verification:**
- [ ] `pytest tests/plugin_manager/test_forge_config.py` passes
- [ ] Config loads with no files present (uses defaults)
- [ ] Config merges YAML correctly
- [ ] ENV variables resolve for subtree remotes

**Out of Scope:**
- Do NOT modify manager.py yet (Task 1.4)
- Do NOT create example files yet (Task 1.2)

---

### Task Package 1.2: Create Configuration Example Files

**Scope:** Create template config files for new users

**Files to Create:**
- `.mybb-forge.yaml.example` (~30 lines)
- `.mybb-forge.env.example` (~10 lines)

**Files to Modify:**
- `.gitignore` - add `.mybb-forge.env`

**Specifications:**
1. `.mybb-forge.yaml.example` must include:
   - `developer:` section with placeholder values
   - `defaults:` section with compatibility, license, visibility
   - `subtrees:` section with commented example
   - `sync:` section with debounce_ms, batch_window_ms, enable_cache_refresh
2. `.mybb-forge.env.example` must include:
   - `PRIVATE_PLUGINS_REMOTE=` (empty)
   - `PRIVATE_THEMES_REMOTE=` (empty)
   - Comment explaining this file is gitignored
3. Add `.mybb-forge.env` to `.gitignore`

**Verification:**
- [ ] Example files exist and are valid YAML/ENV
- [ ] `.gitignore` updated
- [ ] `cat .mybb-forge.yaml.example` shows complete template

**Out of Scope:**
- Do NOT create actual config files (user does this)

---

### Task Package 1.3: Create ForgeConfig Unit Tests

**Scope:** Comprehensive test coverage for config loader

**Files to Create:**
- `tests/plugin_manager/test_forge_config.py` (~150 lines)

**Files to Modify:**
- None

**Specifications:**
1. Test `test_defaults_when_no_files()` - config loads with defaults
2. Test `test_yaml_merge()` - YAML overrides defaults
3. Test `test_env_loading()` - ENV values accessible
4. Test `test_subtree_remote_resolution()` - ENV var reference works
5. Test `test_developer_properties()` - all properties return correct values
6. Test `test_sync_settings()` - sync config accessible
7. Use `tmp_path` fixture for isolated test directories
8. Create helper to write test YAML/ENV files

**Verification:**
- [ ] `pytest tests/plugin_manager/test_forge_config.py -v` - all pass
- [ ] Coverage >90% for forge_config.py

**Out of Scope:**
- Do NOT test integration with PluginManager yet

---

### Task Package 1.4: Integrate ForgeConfig with Plugin Manager

**Scope:** Wire ForgeConfig into PluginManager for auto-fill

**Files to Modify:**
- `plugin_manager/manager.py` - add ForgeConfig loading
- `mybb_mcp/mybb_mcp/tools/plugins.py` - update PLUGIN_TEMPLATE

**Specifications:**
1. In `PluginManager.__init__()`:
   - Import and instantiate `ForgeConfig`
   - Store as `self.forge_config`
   - Handle missing config gracefully (use defaults)
2. In `create_plugin()` method:
   - Use `forge_config.developer_name` for author field if not provided
   - Use `forge_config.developer_website` for author_website
   - Use `forge_config.defaults` for compatibility, visibility if not provided
3. Update PLUGIN_TEMPLATE in tools/plugins.py:
   - Add `author_website` placeholder
   - Ensure template uses passed values

**Verification:**
- [ ] `mybb_create_plugin` auto-fills author from config
- [ ] Works without config file (uses defaults)
- [ ] Explicit parameters override config values

**Out of Scope:**
- Do NOT modify installer.py (Phase 4)
- Do NOT add subtree functionality yet (Phase 6)

---

## Phase 2 - Server Modularization (Simple Categories)
<!-- ID: phase_2 -->

**Objective:** Extract simple, low-dependency handler categories from server.py monolith.

**Why Second:** Establishes modularization pattern before tackling complex categories.

### Task Package 2.1: Create Handler Infrastructure

**Scope:** Set up handlers/ directory and common utilities

**Files to Create:**
- `mybb_mcp/mybb_mcp/handlers/__init__.py`
- `mybb_mcp/mybb_mcp/handlers/common.py` (~80 lines)
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py` (~60 lines)

**Files to Modify:**
- None yet (server.py modified in later tasks)

**Specifications:**
1. `common.py` must include:
   - `format_markdown_table(headers: list, rows: list) -> str`
   - `format_code_block(content: str, lang: str = "") -> str`
   - `format_error(message: str) -> str`
   - `format_success(message: str) -> str`
2. `dispatcher.py` must include:
   - Empty `HANDLER_REGISTRY: Dict[str, Callable] = {}`
   - `async def dispatch_tool(name, args, db, config, sync_service) -> str`
   - Import placeholders for future handler modules (commented)
3. `__init__.py` exports `dispatch_tool` and `HANDLER_REGISTRY`

**Verification:**
- [ ] `from mybb_mcp.handlers import dispatch_tool` works
- [ ] `format_markdown_table` produces valid markdown
- [ ] Dispatcher returns "Unknown tool" for unregistered tools

**Out of Scope:**
- Do NOT modify server.py yet
- Do NOT create actual handler modules yet

---

### Task Package 2.2: Extract Database Query Handler

**Scope:** Extract the simplest handler (1 tool) as pattern template

**Files to Create:**
- `mybb_mcp/mybb_mcp/handlers/database.py` (~40 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py` - import and register

**Specifications:**
1. Extract `mybb_db_query` handler from server.py (around line 2556)
2. Create async function `handle_db_query(args, db, config, sync_service)`
3. Preserve exact behavior and return format
4. Create `DATABASE_HANDLERS` dict mapping tool name to handler
5. Update dispatcher.py to import and merge DATABASE_HANDLERS

**Verification:**
- [ ] `mybb_db_query` tool works identically to before
- [ ] Handler module is <50 lines
- [ ] `len(HANDLER_REGISTRY)` == 1

**Out of Scope:**
- Do NOT remove handler from server.py yet (final cleanup in Phase 3)

---

### Task Package 2.3: Extract Task Handlers

**Scope:** Extract 6 scheduled task handlers

**Files to Create:**
- `mybb_mcp/mybb_mcp/handlers/tasks.py` (~180 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py` - import and register

**Specifications:**
1. Extract these handlers from server.py (lines ~2030-2150):
   - `mybb_task_list`
   - `mybb_task_get`
   - `mybb_task_enable`
   - `mybb_task_disable`
   - `mybb_task_update_nextrun`
   - `mybb_task_run_log`
2. Create `TASK_HANDLERS` dict with all 6 mappings
3. Update dispatcher.py to merge TASK_HANDLERS

**Verification:**
- [ ] All 6 task tools work identically
- [ ] `len(HANDLER_REGISTRY)` == 7
- [ ] `pytest tests/mybb_mcp/handlers/test_tasks.py` passes (create basic test)

**Out of Scope:**
- Do NOT modify task-related database methods

---

### Task Package 2.4: Extract Admin/Cache Handlers

**Scope:** Extract 11 admin and cache management handlers

**Files to Create:**
- `mybb_mcp/mybb_mcp/handlers/admin.py` (~300 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py` - import and register

**Specifications:**
1. Extract these handlers from server.py:
   - `mybb_setting_get`
   - `mybb_setting_set`
   - `mybb_setting_list`
   - `mybb_settinggroup_list`
   - `mybb_cache_read`
   - `mybb_cache_rebuild`
   - `mybb_cache_list`
   - `mybb_cache_clear`
   - `mybb_stats_forum`
   - `mybb_stats_board`
   - `mybb_list_template_groups` (move here from line 1246)
2. Create `ADMIN_HANDLERS` dict
3. Update dispatcher.py

**Verification:**
- [ ] All 11 admin tools work identically
- [ ] `len(HANDLER_REGISTRY)` == 18
- [ ] Settings/cache operations verified manually

**Out of Scope:**
- Do NOT modify underlying db methods

---

## Phase 3 - Server Modularization (Complex Categories)
<!-- ID: phase_3 -->

**Objective:** Extract remaining handlers and complete server.py cleanup.

### Task Package 3.1: Extract Template Handlers

**Scope:** Extract 9 template handlers

**Files to Create:**
- `mybb_mcp/mybb_mcp/handlers/templates.py` (~350 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py`

**Specifications:**
1. Extract handlers:
   - `mybb_list_template_sets`
   - `mybb_list_templates`
   - `mybb_read_template`
   - `mybb_write_template`
   - `mybb_template_find_replace`
   - `mybb_template_batch_read`
   - `mybb_template_batch_write`
   - `mybb_template_outdated`
2. Note: `mybb_list_template_groups` already moved to admin.py
3. Create `TEMPLATE_HANDLERS` dict

**Verification:**
- [ ] All 9 template tools work
- [ ] `len(HANDLER_REGISTRY)` increases by 9
- [ ] Template read/write verified manually

**Out of Scope:**
- Do NOT modify template database methods

---

### Task Package 3.2: Extract Theme/Stylesheet Handlers

**Scope:** Extract 6 theme and stylesheet handlers

**Files to Create:**
- `mybb_mcp/mybb_mcp/handlers/themes.py` (~250 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py`

**Specifications:**
1. Extract handlers:
   - `mybb_list_themes`
   - `mybb_list_stylesheets`
   - `mybb_read_stylesheet`
   - `mybb_write_stylesheet`
   - `mybb_create_theme`
2. Create `THEME_HANDLERS` dict

**Verification:**
- [ ] All 6 theme tools work
- [ ] Stylesheet read/write verified

**Out of Scope:**
- Theme installer changes (separate from MCP handlers)

---

### Task Package 3.3: Extract Content CRUD Handlers

**Scope:** Extract 17 forum/thread/post handlers (largest module)

**Files to Create:**
- `mybb_mcp/mybb_mcp/handlers/content.py` (~600 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py`

**Specifications:**
1. Extract handlers (forums):
   - `mybb_forum_list`, `mybb_forum_read`, `mybb_forum_create`, `mybb_forum_update`, `mybb_forum_delete`
2. Extract handlers (threads):
   - `mybb_thread_list`, `mybb_thread_read`, `mybb_thread_create`, `mybb_thread_update`, `mybb_thread_delete`, `mybb_thread_move`
3. Extract handlers (posts):
   - `mybb_post_list`, `mybb_post_read`, `mybb_post_create`, `mybb_post_update`, `mybb_post_delete`
4. Create `CONTENT_HANDLERS` dict

**Verification:**
- [ ] All 17 content tools work
- [ ] Thread create/move work (these have direct SQL to fix later)

**Out of Scope:**
- Direct SQL fix (Task Package 5.2)

---

### Task Package 3.4: Extract Remaining Handlers

**Scope:** Extract search, moderation, user, sync, plugin handlers

**Files to Create:**
- `mybb_mcp/mybb_mcp/handlers/search.py` (~150 lines) - 4 handlers
- `mybb_mcp/mybb_mcp/handlers/moderation.py` (~250 lines) - 8 handlers
- `mybb_mcp/mybb_mcp/handlers/users.py` (~220 lines) - 7 handlers
- `mybb_mcp/mybb_mcp/handlers/sync.py` (~150 lines) - 5 handlers
- `mybb_mcp/mybb_mcp/handlers/plugins.py` (~400 lines) - 12 handlers

**Files to Modify:**
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py` - import all

**Specifications:**
1. Extract all remaining handlers following established pattern
2. Each module exports `{CATEGORY}_HANDLERS` dict
3. Dispatcher imports and merges all handler dicts

**Verification:**
- [ ] `len(HANDLER_REGISTRY)` == 85 (all tools registered)
- [ ] Random sampling of 10 tools work correctly

**Out of Scope:**
- New subtree handlers (Phase 6)

---

### Task Package 3.5: Clean Up server.py and Create tools_registry.py

**Scope:** Final server.py cleanup and tool definition consolidation

**Files to Create:**
- `mybb_mcp/mybb_mcp/tools_registry.py` (~1,080 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/server.py` - major reduction

**Specifications:**
1. Move all tool definitions (lines 51-1130) to `tools_registry.py`
2. Export `ALL_TOOLS` list from tools_registry
3. Modify server.py:
   - Import `ALL_TOOLS` from tools_registry
   - Import `dispatch_tool` from handlers
   - Replace 2,642-line `handle_tool()` with dispatcher call
   - Keep only: imports, create_server(), main()
4. Target server.py size: ~150 lines

**Verification:**
- [ ] `wc -l mybb_mcp/mybb_mcp/server.py` shows ~150 lines
- [ ] All 85 MCP tools work via `claude mcp get mybb`
- [ ] `pytest tests/` passes (existing tests)

**Out of Scope:**
- New functionality (this is pure refactoring)

---

## Phase 4 - Plugin Template Disk-First Sync (REVISED per R8+R9)
<!-- ID: phase_4 -->

**Objective:** Wire db-sync to automatically sync plugin templates from workspace to database.

**Revision Note:** Research R8+R9 revealed db-sync is 90% complete for plugin templates. PathRouter already parses plugin paths, manual sync_plugin() exists. Only ~145 lines needed to complete auto-sync. User requirements: (1) DB-sync as single entry point for templates, (2) NO auto-generated template stubs, (3) _install() reads from disk.

### Task Package 4.1: Create PluginTemplateImporter Class

**Scope:** New importer class following TemplateImporter pattern (~60 lines)

**Files to Create:**
- `mybb_mcp/mybb_mcp/sync/plugin_templates.py` (~60 lines)

**Specifications:**
1. Create `PluginTemplateImporter` class with `__init__(self, db: MyBBDatabase)`
2. Implement async method `import_template(codename: str, template_name: str, content: str) -> bool`:
   - Build full template name: `{codename}_{template_name}`
   - Check if template exists in master templates (sid=-2)
   - If exists: UPDATE existing template
   - If not exists: INSERT new template with sid=-2
3. Add logging for sync operations
4. Follow exact pattern from `templates.py:TemplateImporter`

**Verification:**
- [ ] `pytest tests/mybb_mcp/sync/test_plugin_templates.py` passes
- [ ] Import creates template with correct name prefix
- [ ] Import updates existing template without duplicating

**Out of Scope:**
- Watcher integration (Task 4.3)
- Export from DB (use existing sync_plugin with direction='from_db')

**Dependencies:** None (standalone component)

---

### Task Package 4.2: Extend FileWatcher for Workspace Monitoring

**Scope:** Add workspace_root parameter and second observer schedule (~40 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/sync/watcher.py` - FileWatcher class

**Specifications:**
1. Add `workspace_root: Optional[Path]` parameter to `FileWatcher.__init__()`:
   ```python
   def __init__(
       self,
       sync_root: Path,
       template_importer: TemplateImporter,
       stylesheet_importer: StylesheetImporter,
       plugin_template_importer: PluginTemplateImporter,  # ADD
       cache_refresher: CacheRefresher,
       router: PathRouter,
       workspace_root: Optional[Path] = None  # ADD
   ):
   ```
2. Store `self.workspace_root = workspace_root`
3. Store `self.plugin_template_importer = plugin_template_importer`
4. In `start()` method, add second observer if workspace_root provided:
   ```python
   if self.workspace_root and self.workspace_root.exists():
       self.observer.schedule(self.handler, str(self.workspace_root), recursive=True)
   ```
5. Update `SyncEventHandler.__init__()` to accept plugin_template_importer

**Verification:**
- [ ] FileWatcher accepts new parameters without breaking
- [ ] Observer schedules both directories when workspace_root provided
- [ ] Works without workspace_root (backward compatible)

**Out of Scope:**
- Handler logic (Task 4.3)

**Dependencies:** Task 4.1 (needs PluginTemplateImporter class)

---

### Task Package 4.3: Add Plugin Template Handler to SyncEventHandler

**Scope:** Handle plugin template file changes (~35 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/sync/watcher.py` - SyncEventHandler class

**Specifications:**
1. Update `_handle_file_change()` to detect plugin template paths:
   ```python
   # After existing template/stylesheet checks
   elif path.suffix == '.html' and 'plugins' in path.parts and 'templates' in path.parts:
       self._handle_plugin_template_change(path)
   ```
2. Create `_handle_plugin_template_change(self, path: Path) -> None`:
   - Use PathRouter to parse path (returns type='plugin_template')
   - Validate: parsed.type == 'plugin_template' and parsed.project_name
   - Check file size > 0 (prevent empty file corruption)
   - Read file content
   - Queue work item:
     ```python
     self.work_queue.put_nowait({
         "type": "plugin_template",
         "codename": parsed.project_name,
         "template_name": parsed.template_name,
         "content": content
     })
     ```
3. Add logging: `[disk-sync] Plugin template queued: {codename}_{template_name}`

**Verification:**
- [ ] File change in workspace/plugins/{vis}/{codename}/templates/ triggers handler
- [ ] Work item queued with correct structure
- [ ] Empty files ignored (no corruption)

**Out of Scope:**
- Queue processing (Task 4.4)

**Dependencies:** Task 4.2 (handler needs workspace_root context)

---

### Task Package 4.4: Wire Queue Processor and Service Initialization

**Scope:** Complete the wiring for end-to-end sync (~25 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/sync/watcher.py` - _process_work_queue method
- `mybb_mcp/mybb_mcp/sync/service.py` - DiskSyncService initialization

**Specifications:**
1. In `FileWatcher._process_work_queue()`, add plugin_template case after stylesheet:
   ```python
   elif work_item["type"] == "plugin_template":
       await self.plugin_template_importer.import_template(
           work_item["codename"],
           work_item["template_name"],
           work_item["content"]
       )
       print(f"[disk-sync] Plugin template synced: {work_item['codename']}_{work_item['template_name']}")
   ```
2. In `DiskSyncService.__init__()`:
   - Import PluginTemplateImporter
   - Create instance: `self.plugin_template_importer = PluginTemplateImporter(db)`
   - Update FileWatcher instantiation to pass new parameters:
     ```python
     self.watcher = FileWatcher(
         config.sync_root,
         self.template_importer,
         self.stylesheet_importer,
         self.plugin_template_importer,  # ADD
         self.cache_refresher,
         self.router,
         workspace_root=workspace_root  # ADD
     )
     ```

**Verification:**
- [ ] Template edit in workspace auto-syncs to database
- [ ] `[disk-sync] Plugin template synced:` appears in logs
- [ ] Database shows template with correct sid=-2 and {codename}_ prefix

**Out of Scope:**
- Scaffold changes (Task 4.5)

**Dependencies:** Tasks 4.1, 4.2, 4.3

---

### Task Package 4.5: Update Plugin Scaffold for templates/ Directory

**Scope:** Scaffold creates templates/ directory but NO auto-generated stubs

**Files to Modify:**
- `mybb_mcp/mybb_mcp/tools/plugins.py` - update PLUGIN_TEMPLATE and directory creation
- `plugin_manager/manager.py` - update create_plugin()

**Specifications:**
1. Update `create_plugin()` to create `templates/` directory (empty):
   ```python
   templates_dir = plugin_dir / "templates"
   templates_dir.mkdir(exist_ok=True)
   ```
2. Update PLUGIN_TEMPLATE PHP to include helper function for reading templates from disk:
   ```php
   function {codename}_load_templates_from_disk() {
       global $db;
       $templates_dir = __DIR__ . '/templates';
       if (!is_dir($templates_dir)) return;

       foreach (glob($templates_dir . '/*.html') as $file) {
           $name = '{codename}_' . basename($file, '.html');
           $content = file_get_contents($file);
           // Check if exists, update or insert
           $existing = $db->simple_select('templates', 'tid', "title='" . $db->escape_string($name) . "' AND sid=-2");
           if ($db->num_rows($existing) > 0) {
               $row = $db->fetch_array($existing);
               $db->update_query('templates', ['template' => $db->escape_string($content), 'dateline' => TIME_NOW], "tid={$row['tid']}");
           } else {
               $db->insert_query('templates', [
                   'title' => $db->escape_string($name),
                   'template' => $db->escape_string($content),
                   'sid' => -2,
                   'version' => '',
                   'dateline' => TIME_NOW
               ]);
           }
       }
   }
   ```
3. Update `_install()` in PLUGIN_TEMPLATE to call helper
4. **NO auto-generated template stub files** (user creates templates as needed)
5. Update meta.json template to include `"templates": []` field (populated manually by developer)

**Verification:**
- [ ] New plugin has empty templates/ directory
- [ ] No .html stub files auto-created
- [ ] _install() includes disk-reading helper function
- [ ] meta.json has templates array field

**Out of Scope:**
- Multi-theme support (Phase 5.3)

**Dependencies:** None (can run parallel with 4.1-4.4)

---

### Task Package 4.6: Integration Test - Plugin Template Auto-Sync

**Scope:** End-to-end test of disk-to-DB template workflow

**Files to Create:**
- `tests/plugin_manager/test_plugin_template_sync.py` (~150 lines)

**Specifications:**
1. Test setup: Create test plugin with templates/ directory
2. Test 1: Add template file, verify appears in DB with {codename}_ prefix and sid=-2
3. Test 2: Modify template file, verify DB updated (not duplicated)
4. Test 3: Verify file watcher detects changes in workspace_root
5. Test 4: Full lifecycle - create plugin, add template via disk, install, verify in ACP
6. Cleanup: Remove test plugin and templates

**Verification:**
- [ ] `pytest tests/plugin_manager/test_plugin_template_sync.py` passes
- [ ] Manual: Template visible in MyBB Admin CP under plugin's template group

**Out of Scope:**
- Theme-specific templates (Phase 5.3)

**Dependencies:** Tasks 4.1-4.5 complete

---

## Phase 5 - DB-Sync Optimizations & Multi-Theme Support (REVISED per R8+R9)
<!-- ID: phase_5 -->

**Objective:** Optimize sync performance and add multi-theme template support.

**Revision Note:** Original 5.3 (Bulk Update Wrapper Methods) moved to Phase 6 as it's unrelated to db-sync templates. Added new 5.3 for multi-theme config support per user requirement.

### Task Package 5.1: Implement Smart Batching in Watcher

**Scope:** Add batch collection window to file watcher (benefits all sync including new plugin templates)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/sync/watcher.py` - SyncEventHandler

**Specifications:**
1. Change `DEBOUNCE_SECONDS` from 0.5 to 0.1
2. Add `BATCH_WINDOW_SECONDS = 0.1`
3. Add `_pending_batch: Dict[str, dict]` attribute
4. Add `_batch_timer: Optional[asyncio.TimerHandle]` attribute
5. Create `_queue_for_batch(work_item)` method
6. Create `_flush_batch()` method
7. Modify `_handle_file_change()` to use batch queue
8. Update `_process_work_queue()` to handle batch items
9. Batching applies to all sync types: template, stylesheet, plugin_template

**Verification:**
- [ ] Debounce is 100ms
- [ ] Multiple rapid changes batched together
- [ ] Single transaction for batch
- [ ] Plugin template batch sync works

**Out of Scope:**
- Template set caching (Task 5.2)

**Dependencies:** Phase 4 complete (plugin templates wired)

---

### Task Package 5.2: Add Template Set Caching

**Scope:** Cache template set ID lookups to reduce queries

**Files to Modify:**
- `mybb_mcp/mybb_mcp/sync/templates.py` - add caching to TemplateImporter

**Specifications:**
1. Add `_set_cache: Dict[str, int]` attribute
2. Add `_cache_ttl = 300` (5 minutes)
3. Add `_cache_time: float` attribute
4. Create `_get_template_set_id(set_name)` with cache logic
5. Update `import_template()` to use cached lookup
6. Add cache invalidation on TTL expiry

**Note:** This applies to template sets only. Plugin templates always use sid=-2, no lookup needed.

**Verification:**
- [ ] Second template in same set uses cached ID
- [ ] Cache expires after 5 minutes
- [ ] Reduced query count visible in logs

**Out of Scope:**
- Plugin template caching (not needed - sid=-2 is constant)

**Dependencies:** None (can run parallel with 5.1)

---

### Task Package 5.3: Multi-Theme Plugin Template Support (NEW)

**Scope:** Allow plugins to have theme-specific template directories

**Files to Modify:**
- `mybb_mcp/mybb_mcp/sync/plugin_templates.py` - add theme-aware import
- `mybb_mcp/mybb_mcp/sync/router.py` - extend path parsing for theme dirs
- `plugin_manager/schema.py` - add theme_templates config to meta.json schema

**Specifications:**
1. Extend plugin workspace structure to support theme-specific templates:
   ```
   plugin_manager/plugins/{vis}/{codename}/
   ├── templates/              # Default templates (sid=-2)
   │   └── my_template.html
   └── templates_themes/       # Theme-specific overrides
       ├── Default/            # Maps to "Default Templates" set
       │   └── my_template.html
       └── Mobile/             # Maps to "Mobile Templates" set
           └── my_template.html
   ```
2. Update PathRouter to recognize templates_themes/{theme_name}/ paths
3. Update PluginTemplateImporter to:
   - Detect theme from path
   - If theme specified: insert with sid matching theme's template set
   - If no theme (default templates/): insert with sid=-2
4. Update meta.json schema to include optional `theme_templates` config:
   ```json
   {
     "theme_templates": {
       "Default": ["my_template"],
       "Mobile": ["my_template"]
     }
   }
   ```

**Verification:**
- [ ] Default templates go to sid=-2
- [ ] Theme-specific templates go to correct template set sid
- [ ] Watcher handles both directories
- [ ] meta.json validates new structure

**Out of Scope:**
- Theme inheritance (complex MyBB behavior)

**Dependencies:** Phase 4 complete (plugin template sync working)

---

## Phase 6 - Git Subtree & Finalization (UPDATED)
<!-- ID: phase_6 -->

**Objective:** Add subtree tools, bulk update wrappers, and complete project.

**Update Note:** Task 6.0 added (moved from Phase 5.3) - Bulk Update Wrapper Methods.

### Task Package 6.0: Add Bulk Update Wrapper Methods (Moved from Phase 5.3)

**Scope:** Create missing database wrapper methods for direct SQL replacement

**Files to Modify:**
- `mybb_mcp/mybb_mcp/db/connection.py` - add 2 new methods

**Specifications:**
1. Add `update_post_field(pid, field, value)`:
   - Whitelist allowed fields: tid, fid, visible, message, subject
   - Return bool success
2. Add `update_posts_by_thread(tid, **fields)`:
   - Whitelist allowed fields: fid, visible
   - Return int rowcount
3. Add unit tests for both methods

**Verification:**
- [ ] `update_post_field(1, "tid", 5)` works
- [ ] `update_posts_by_thread(1, fid=2)` updates all posts
- [ ] Invalid field raises ValueError

**Out of Scope:**
- Updating server.py handlers (Task 6.2)

**Dependencies:** None (can start immediately in Phase 6)

---

### Task Package 6.1: Create Subtree Handler Module

**Scope:** New MCP tools for git subtree operations

**Files to Create:**
- `mybb_mcp/mybb_mcp/handlers/subtrees.py` (~200 lines)

**Files to Modify:**
- `mybb_mcp/mybb_mcp/handlers/dispatcher.py` - import subtrees
- `mybb_mcp/mybb_mcp/tools_registry.py` - add 4 tool definitions

**Specifications:**
1. Create `handle_subtree_add(args, ...)` - adds subtree from config
2. Create `handle_subtree_push(args, ...)` - pushes to configured remote
3. Create `handle_subtree_pull(args, ...)` - pulls from configured remote
4. Create `handle_subtree_list(args, ...)` - lists configured subtrees
5. Create `SUBTREE_HANDLERS` dict
6. Add tool definitions to tools_registry.py

**Verification:**
- [ ] `mybb_subtree_list` shows configured subtrees
- [ ] Tools return helpful errors when config missing

**Out of Scope:**
- Actual git operations testing (requires repo setup)

---

### Task Package 6.2: Replace Direct SQL in Handlers

**Scope:** Update handlers to use new wrapper methods

**Files to Modify:**
- `mybb_mcp/mybb_mcp/handlers/content.py` - fix thread_create, thread_move

**Specifications:**
1. In `handle_thread_create`:
   - Replace `cur.execute("UPDATE posts SET tid...")` with `db.update_post_field(pid, "tid", tid)`
2. In `handle_thread_move`:
   - Replace `cur.execute("UPDATE posts SET fid WHERE tid...")` with `db.update_posts_by_thread(tid, fid=new_fid)`
3. Verify no more direct SQL in handlers

**Verification:**
- [ ] `grep -r "cur.execute" handlers/` returns no results
- [ ] Thread create/move work correctly
- [ ] Tests pass

**Out of Scope:**
- mybb_db_query (intentionally direct SQL)

---

### Task Package 6.3: Documentation Updates

**Scope:** Update wiki and CLAUDE.md for v2 changes

**Files to Modify:**
- `CLAUDE.md` - add config file documentation
- `docs/wiki/plugin_manager/workspace.md` - update for templates/
- `docs/wiki/mcp_tools/plugins.md` - add subtree tools

**Specifications:**
1. CLAUDE.md: Add section on .mybb-forge.yaml and .mybb-forge.env
2. CLAUDE.md: Document new plugin structure with templates/
3. Wiki: Update workspace docs for new directory structure
4. Wiki: Add subtree tool documentation

**Verification:**
- [ ] CLAUDE.md has config section
- [ ] Wiki updated with new structure

**Out of Scope:**
- External documentation (readthedocs, etc.)

---

### Task Package 6.4: Final Integration Testing

**Scope:** End-to-end verification of all v2 features

**Files to Create:**
- `tests/integration/test_forge_v2.py` (~300 lines)

**Files to Modify:**
- None

**Specifications:**
1. Test full workflow:
   - Create config files
   - Create plugin with auto-fill
   - Deploy plugin with disk templates
   - Verify MCP tools work (random sample)
   - Verify batch sync latency improved
2. Document any issues found

**Verification:**
- [ ] Integration test passes
- [ ] All 89 MCP tools work (85 original + 4 subtree)
- [ ] Performance: sync latency <200ms measured

**Out of Scope:**
- Performance benchmarking framework

---

## Milestone Tracking
<!-- ID: milestone_tracking -->

| Milestone | Target | Owner | Status | Evidence |
|-----------|--------|-------|--------|----------|
| Phase 1 Complete | Day 1-2 | Coder | Pending | test_forge_config.py |
| Phase 2 Complete | Day 2-3 | Coder | Pending | 18 handlers extracted |
| Phase 3 Complete | Day 3-5 | Coder | Pending | server.py ~150 lines |
| Phase 4 Complete | Day 5-7 | Coder | Pending | disk templates working |
| Phase 5 Complete | Day 7-8 | Coder | Pending | <200ms sync latency |
| Phase 6 Complete | Day 8-10 | Coder | Pending | all tests pass |
| Project Complete | Day 10 | Review | Pending | final review grade |

---

## Coder Assignment Strategy (UPDATED per R8+R9)
<!-- ID: coder_strategy -->

### Parallel Execution Opportunities

These task packages can be worked in parallel (no file overlap):

**Parallel Group A** (after Phase 1):
- Task 2.2 (database handler)
- Task 2.3 (task handlers)
- Task 2.4 (admin handlers)

**Parallel Group B** (after Phase 2):
- Task 3.1 (template handlers)
- Task 3.2 (theme handlers)

**Parallel Group C** (Phase 4 - REVISED sequential chain):
- Task 4.1 (PluginTemplateImporter) - START HERE
- Task 4.2 (FileWatcher extension) - depends on 4.1
- Task 4.3 (SyncEventHandler) - depends on 4.2
- Task 4.4 (Wire queue + service) - depends on 4.1-4.3
- Task 4.5 (Scaffold update) - CAN RUN PARALLEL with 4.1-4.4
- Task 4.6 (Integration test) - depends on 4.1-4.5

**Parallel Group D** (Phase 5 after Phase 4):
- Task 5.1 (Smart batching) - depends on Phase 4 complete
- Task 5.2 (Template set caching) - CAN RUN PARALLEL with 5.1
- Task 5.3 (Multi-theme support) - depends on Phase 4 complete

**Parallel Group E** (Phase 6):
- Task 6.0 (Bulk update wrappers) - CAN START IMMEDIATELY
- Task 6.1 (Subtree handlers) - CAN RUN PARALLEL with 6.0
- Task 6.2 (Replace direct SQL) - depends on 6.0
- Task 6.3 (Documentation) - CAN RUN PARALLEL
- Task 6.4 (Integration test) - depends on all

### Sequential Dependencies

Must be sequential:
- Task 1.1 -> 1.4 (ForgeConfig before integration)
- Task 3.4 -> 3.5 (all handlers before cleanup)
- Task 4.1 -> 4.2 -> 4.3 -> 4.4 (db-sync wiring chain)
- Task 6.0 -> 6.2 (bulk wrappers before SQL replacement)

### Phase 4 Critical Path (NEW)

The revised Phase 4 has a clear dependency chain for the db-sync wiring:

```
4.1 PluginTemplateImporter (standalone, ~60 lines)
    |
    v
4.2 FileWatcher extension (needs 4.1, ~40 lines)
    |
    v
4.3 SyncEventHandler (needs 4.2, ~35 lines)
    |
    v
4.4 Wire queue + service (needs 4.1-4.3, ~25 lines)
    |
    v
4.6 Integration test (needs all)

4.5 Scaffold update runs in PARALLEL (no code dependencies)
```

**Total Phase 4 new code: ~160 lines** (down from original 500+ lines)

---

## Retro Notes & Adjustments
<!-- ID: retro_notes -->

*To be filled after each phase completion*

### Phase 1 Retro
- Date:
- Learnings:
- Adjustments:

### Phase 2 Retro
- Date:
- Learnings:
- Adjustments:

### Phase 3 Retro
- Date:
- Learnings:
- Adjustments:

---

*Phase plan created by MyBB-ArchitectAgent based on ARCHITECTURE_GUIDE.md specifications.*
