
# Plugin Template Deployment Flow — Architectural Research

**Author:** MyBB-ResearchAgent
**Version:** v1.0
**Status:** Complete
**Last Updated:** 2026-01-19 10:03 UTC
**Confidence:** 0.95

---
## Executive Summary

The plugin template deployment system uses **TWO coordinated pathways** working in parallel:

1. **MCP Disk-Sync (Development):** Watches `plugin_manager/plugins/*/templates/` → syncs to MyBB DB in real-time
2. **Plugin Installer (Deployment):** Copies workspace code files (`inc/`, `jscripts/`, `images/`) but **NOT** templates

Both mechanisms read from the same workspace source. **There is NO architectural mismatch** — this is intentional design. Templates are managed through the database, not the filesystem.

**Key Takeaways:**
- Templates live in workspace `plugins/{codename}/templates/` — single source of truth
- MCP disk-sync syncs templates to DB (sid=-2) in real-time during development
- Plugin installer does NOT copy templates because they belong in the database
- Theme installer uses a different path: deploys templates at installation time
- Configuration gap: `workspace_root` must be set for watcher to monitor plugins


---
## Research Scope

**Research Lead:** MyBB-ResearchAgent

**Investigation Window:** 2026-01-19 10:01 — 10:03 UTC

**Focus Areas:**
- Plugin template workspace structure and naming conventions
- MCP disk-sync watcher configuration and workspace monitoring
- Path routing logic for plugin template identification
- PluginTemplateImporter sync mechanism (DB insert/update)
- Plugin installer file deployment strategy
- Theme installer template deployment path
- Coordination between disk-sync and installer mechanisms

**Files Examined:**
- `plugin_manager/installer.py` — File deployment logic
- `plugin_manager/manager.py` — Scaffold and template directory creation
- `mybb_mcp/mybb_mcp/sync/watcher.py` — File watcher and event handler
- `mybb_mcp/mybb_mcp/sync/router.py` — Path parsing for plugin templates
- `mybb_mcp/mybb_mcp/sync/plugin_templates.py` — Database sync logic

**Dependencies & Constraints:**
- Analysis assumes MyBB 1.8.x architecture with existing plugin/template system
- Workspace structure follows `plugin_manager/plugins/{visibility}/{codename}/` pattern
- MCP tools assume database access and MyBB installation at TestForum/
- `workspace_root` configuration is optional but required for plugin template sync


---
## Findings

### Finding 1: Single Workspace Source for Plugin Templates

**Summary:** All plugin templates are created and maintained in a single workspace directory: `plugin_manager/plugins/{visibility}/{codename}/templates/`

**Evidence:**
- `plugin_manager/manager.py:310-338` — Scaffold creates `templates/` directory when `has_templates=True`
- Template README documents the path convention
- No other template source locations exist in the codebase

**Confidence:** 0.99 — Direct code confirmation

---

### Finding 2: MCP Watcher Monitors Both Sync Root AND Workspace

**Summary:** The file watcher is configured to watch TWO directories in parallel:
1. `mybb_sync/` (for core MyBB templates/stylesheets)
2. `plugin_manager/plugins/` (for plugin templates, if workspace_root is set)

**Evidence:**
- `mybb_mcp/mybb_mcp/sync/watcher.py:524-548` — Start method schedules observer for both paths
- `workspace_root` parameter is optional: `workspace_root: Optional[Path] = None`
- Conditional scheduling: `if self.workspace_root and self.workspace_root.exists()`

**Confidence:** 0.98 — Code inspection shows explicit dual-watching behavior

**Critical Gap:** The `workspace_root` configuration is **not automatically set**. Users must explicitly configure it for plugin template watching to work.

---

### Finding 3: PathRouter Identifies Plugin Templates

**Summary:** The PathRouter class identifies plugin template files using two patterns:
1. `plugins/{visibility}/{codename}/templates/*.html` → type='plugin_template'
2. `plugins/{visibility}/{codename}/templates_themes/{theme_name}/*.html` → type='plugin_template' with theme_name

**Evidence:**
- `mybb_mcp/mybb_mcp/sync/router.py:155-225` — _parse_plugin_path() method
- Lines 178-187: Default template pattern recognition
- Lines 190-201: Theme-specific template pattern recognition

**Confidence:** 0.99 — Direct code inspection

**Design Insight:** The router supports TWO organizational patterns:
- **Default**: All templates in `templates/` → synced to master (sid=-2)
- **Theme-specific**: Variants in `templates_themes/{theme_name}/` → synced to specific theme set

---

### Finding 4: MCP Sync Handler Queues Templates for Real-Time Database Update

**Summary:** When workspace files change, the SyncEventHandler queues them for batch processing and the PluginTemplateImporter syncs them to the MyBB database in real-time.

**Evidence:**
- `mybb_mcp/mybb_mcp/sync/watcher.py:290-347` — _handle_plugin_template_change() method
- Lines 332-338: Queues work with codename, template_name, content, theme_name
- `mybb_mcp/mybb_mcp/sync/watcher.py:467-478` — Batch processor calls PluginTemplateImporter
- `mybb_mcp/mybb_mcp/sync/plugin_templates.py:79-165` — import_template() creates or updates templates

**Confidence:** 0.98 — Complete call chain traced

---

### Finding 5: Plugin Templates Use Prefixed Naming Convention

**Summary:** Plugin templates in the database are named with the plugin codename prefix: `{codename}_{template_name}`

**Evidence:**
- `mybb_mcp/mybb_mcp/sync/plugin_templates.py:125` — `full_template_name = f"{codename}_{template_name}"`
- Examples: workspace file `welcome.html` becomes DB template `cortex_welcome`
- MyBB access pattern: `$templates->get('cortex_welcome')`

**Confidence:** 0.99 — Direct code confirmation

---

### Finding 6: Plugin Installer Does NOT Copy Templates Directory

**Summary:** The PluginInstaller copies `inc/`, `jscripts/`, and `images/` directories to TestForum, but explicitly does NOT copy the `templates/` directory.

**Evidence:**
- `plugin_manager/installer.py:74-224` — install_plugin() method shows only three overlays:
  - inc/ (lines 127-139)
  - jscripts/ (lines 148-156)
  - images/ (lines 158-166)
- No `templates/` overlay or copy operation exists
- `_overlay_directory()` is only called for these three paths

**Confidence:** 0.99 — Code inspection confirms templates/ is intentionally omitted

**Design Insight:** This is CORRECT behavior because:
1. Templates should live in the MyBB database, not filesystem
2. MCP disk-sync handles template synchronization
3. Plugin installer focuses on code deployment (PHP, languages, images)

---

### Finding 7: Theme Installer Uses Different Template Deployment Strategy

**Summary:** ThemeInstaller deploys templates at installation time using `mybb_template_batch_write()`, creating a different pathway than the plugin installer.

**Evidence:**
- `plugin_manager/installer.py:577-601` — install_theme() method
- Lines 578-599: Reads `templates/` directory and calls `mybb_template_batch_write()`
- This is DIFFERENT from PluginInstaller which skips templates

**Confidence:** 0.98 — Code inspection confirmed

**Design Question:** Why do themes deploy templates at install time while plugins rely on disk-sync?

---

### Finding 8: PluginTemplateImporter Handles Both Default and Theme-Specific Templates

**Summary:** The PluginTemplateImporter implements logic to store templates in either master templates (sid=-2) or theme-specific template sets based on the theme_name parameter.

**Evidence:**
- `mybb_mcp/mybb_mcp/sync/plugin_templates.py:127-137` — Determines target sid
- If theme_name is provided: looks up template set sid by name
- If theme_name is None or not found: falls back to sid=-2
- Lines 139-165: Implements UPDATE-or-INSERT pattern

**Confidence:** 0.98 — Logic chain is clear and complete

**Features:**
- Template set caching for performance
- Cache disabling via `MYBB_SYNC_DISABLE_CACHE` env var
- Fallback strategy (theme not found → use master)
- Defensive empty content validation

---

## Additional Observations

1. **No Deployment to TestForum Filesystem:** Plugin templates never appear in `TestForum/` filesystem. They're synced to database only.

2. **Real-Time Development Sync:** The MCP watcher provides real-time template changes during development. Save file → automatically synced to database.

3. **Codename Prefix Collision Risk:** All plugin templates are prefixed with codename. Two plugins with overlapping template names won't conflict (e.g., `plugin1_header` vs `plugin2_header`).

4. **Theme Support Two Ways:**
   - Default templates: `templates/` synced to sid=-2
   - Theme overrides: `templates_themes/{theme_name}/` synced to specific sid

5. **Configuration Dependency:** The entire plugin template sync system depends on `workspace_root` being configured in the MCP watcher initialization.


---
## Technical Analysis

### Architecture Diagram

```
WORKSPACE (plugin_manager/plugins/{visibility}/{codename}/)
├── inc/
│   ├── plugins/{codename}.php
│   ├── plugins/{codename}/core/*.php
│   └── languages/english/{codename}.lang.php
├── templates/                      ← SOURCE OF TRUTH
│   ├── template1.html
│   └── template2.html
├── templates_themes/                ← Theme-specific variants
│   ├── Default Templates/variant.html
│   └── Custom Theme/variant.html
└── meta.json

DEPLOYMENT PATHWAYS:

PATH A: MCP DISK-SYNC (Real-Time Development)
├─ Watcher monitors: plugin_manager/plugins/*/templates/*.html
├─ Router identifies: type='plugin_template'
├─ Handler queues: {codename, template_name, content, theme_name}
├─ PluginTemplateImporter.import_template() executes
└─ Database: INSERT/UPDATE template with title={codename}_{template_name}, sid=-2

PATH B: PLUGIN INSTALLER (File Deployment)
├─ Copies: inc/ → TestForum/inc/
├─ Copies: jscripts/ → TestForum/jscripts/ (if exists)
├─ Copies: images/ → TestForum/images/ (if exists)
├─ DOES NOT copy templates/ directory (intentional)
└─ Plugin PHP accesses templates via: $templates->get('{codename}_{template_name}')

PATH C: THEME INSTALLER (Theme Deployment)
├─ Reads: workspace/templates/*.html
├─ Calls: mybb_template_batch_write(sid=1) at install time
└─ Different from plugin installer; templates deployed with theme
```

### Code Patterns Identified

1. **Template Naming Convention:** All plugin templates follow `{codename}_{name}` pattern
   - Prevents collisions between plugins
   - Unique within MyBB's global template namespace

2. **Dual-Path Sync Architecture:**
   - Real-time: Workspace → DB via MCP disk-sync
   - Deployment: Code files → TestForum via installer (templates handled separately)

3. **Path Routing Pattern:**
   - Router examines file path and categorizes as plugin_template, plugin_php, etc.
   - Supports multiple organizational patterns (templates/ and templates_themes/)

4. **Batch Processing:**
   - Watcher queues changes with deduplication
   - Batch processor runs asynchronously (not blocking filesystem observer)

5. **Theme Support via Optional Metadata:**
   - ParsedPath.theme_name carries theme context through sync pipeline
   - Enables theme-specific template variants without code duplication

### System Interactions

| Component | Inputs | Outputs | Database |
|-----------|--------|---------|----------|
| Scaffold | has_templates flag | `templates/` directory | Meta.json |
| FileWatcher | Filesystem events | Queued work items | (none) |
| PathRouter | File paths | ParsedPath objects | (read-only) |
| SyncEventHandler | Queued items | PluginTemplateImporter calls | (none directly) |
| PluginTemplateImporter | content, codename, theme_name | Template CREATE/UPDATE | `mybb_templates` table |
| PluginInstaller | Workspace path | Files in TestForum | `mybb_plugins_projects` (metadata) |
| ThemeInstaller | Workspace path | MCP tool calls | `mybb_templates` table |

### Risk Assessment

**Risk 1: workspace_root Configuration Gap (MEDIUM)**
- **Issue:** `workspace_root` must be explicitly configured for plugin template sync
- **Impact:** If not set, plugin template changes won't sync in real-time
- **Mitigation:**
  - Add warning when watcher starts without workspace monitoring
  - Document configuration requirement in CLAUDE.md
  - Consider auto-detection: if `plugin_manager/` exists, use it

**Risk 2: Template Deployment Inconsistency (LOW)**
- **Issue:** Plugins use disk-sync; themes use installer
- **Impact:** Users must understand two different patterns
- **Mitigation:**
  - Document why the difference exists (themes need install-time deployment)
  - Standardize on one pattern if possible going forward

**Risk 3: Plugin _install() Function Guidance Mismatch (MEDIUM)**
- **Issue:** CLAUDE.md says "create templates via _install()" but code uses disk-sync
- **Impact:** Plugin developers may create duplicate templates or use wrong approach
- **Mitigation:**
  - Clarify: should _install() create templates, or rely on disk-sync?
  - Update guidance if disk-sync is the intended pattern

**Risk 4: No File-to-DB Validation (LOW)**
- **Issue:** No verification that workspace templates match DB templates
- **Impact:** If watcher fails silently, DB might be stale
- **Mitigation:**
  - Add health check: compare workspace against DB
  - Add sync status logging

**Risk 5: Template Name Collisions Between Plugins (LOW)**
- **Issue:** Codename prefixing prevents collisions BUT both plugins could have `{codename}_header`
- **Impact:** Users must coordinate template names
- **Mitigation:**
  - Document naming conventions
  - Add collision detection in scaffold

---

## Design Insights

### Why Templates Don't Go to TestForum Filesystem

The design is intentional:
1. **MyBB stores templates in database** — that's the primary storage mechanism
2. **Plugin installer focuses on code** — PHP, language files, images, CSS
3. **MCP disk-sync bridges development** — allows real-time edits without database UI
4. **No synchronization needed** — watcher handles DB updates automatically

This is correct and follows MyBB's architecture.

### Why Themes Use Different Path

ThemeInstaller deploys templates at installation time because:
1. **Themes are complete packages** — stylesheets AND template overrides ship together
2. **One-time deployment** — templates are part of theme installation, not development workflow
3. **Simple path** — no watcher needed for theme deployment

### Why No workspace_root Auto-Configuration

The MCP watcher is generic and works for:
- Core MyBB (`mybb_sync/`)
- Plugins (`plugin_manager/plugins/`)
- Custom projects (any filesystem location)

Requiring explicit `workspace_root` keeps it flexible and explicit. Users know what's being watched.


---
## Recommendations

### Immediate Actions (High Priority)

**1. Update CLAUDE.md with Clear Plugin Template Workflow**
- Document that plugin templates are synced to DB via MCP disk-sync, not copied to TestForum
- Clarify the workspace source: `plugin_manager/plugins/{codename}/templates/`
- Explain template naming: workspace `welcome.html` → DB `{codename}_welcome`
- Update _install() guidance: clarify whether templates should be created in _install() or via disk-sync
- Add warning: workspace_root must be configured for disk-sync to watch plugin templates

**2. Fix workspace_root Configuration Visibility**
- Add auto-detection in MCP watcher: if `plugin_manager/` exists in repo root, use it as default workspace_root
- OR: Document explicitly in `mybb_mcp/config.py` that `WORKSPACE_ROOT` env var must be set
- OR: Emit warning when watcher starts without workspace monitoring
- Test: verify watcher watches plugin templates when configured

**3. Document Plugin Template Development Workflow**
- Create wiki page: `docs/wiki/plugin_manager/template_development.md`
- Include:
  - Workspace structure with templates/ examples
  - Real-time sync via MCP disk-sync
  - Theme-specific templates via templates_themes/
  - MyBB template access pattern
  - Debugging: what to do if templates aren't syncing

### Medium Priority

**4. Reconcile _install() vs Disk-Sync Guidance**
- **Decision needed:** Should plugins create templates in _install() or rely on disk-sync?
- If disk-sync: update CLAUDE.md and remove _install() template creation guidance
- If _install(): document the pattern and implement in scaffold
- If both: explain when to use each approach

**5. Consider Plugin Template Deployment Path**
- **Research question:** Should PluginInstaller also read templates and insert via DB?
- Pros: More explicit deployment, less dependent on watcher
- Cons: Duplicates MCP sync logic, adds complexity
- Recommendation: Keep current design (disk-sync for development, installer for code only)

**6. Add Sync Health Check**
- Implement diagnostic command: `mybb_mcp sync_health_check`
- Compare workspace templates against DB templates
- Report missing, outdated, or extra templates
- Help developers verify sync is working

### Long-Term Improvements

**7. Standardize Theme vs Plugin Template Paths**
- Currently: Themes deploy templates at install time, plugins use disk-sync
- Long-term: Consider single path for both if workflow can be unified
- May require redesigning ThemeInstaller to use disk-sync too

**8. Template Collision Detection**
- Add scaffold validation to warn about duplicate template names
- Example: if another plugin already uses `header`, suggest alternative names

**9. Template Organization Tool**
- Create tool to visualize template inheritance and overrides
- Show: which templates are in master, which in theme-specific sets
- Help users understand plugin template layering

**10. Documentation Index**
- Create searchable index of all plugin templates in workspace
- Tool: `mybb_mcp plugin_templates_list` to show all templates across all plugins
- Include: codename, template name, source location, current DB status

---

## Handoff Notes for Architect

### Key Design Decisions to Validate

1. **Disk-Sync is the Right Path:** The research confirms disk-sync is the intended design for plugin template development. It's real-time, doesn't require database UI, and follows the "edit on disk, sync to DB" pattern.

2. **workspace_root Configuration:** This is a critical piece that must be addressed. Without it, plugin templates won't sync. Either:
   - Auto-detect (preferred)
   - Require env var (good)
   - Fail with clear error message (acceptable)

3. **Plugin Installer Correctly Omits Templates:** The fact that PluginInstaller doesn't copy templates/ is correct and intentional. Don't change this.

4. **Theme Installer Different Path is OK:** Themes using `mybb_template_batch_write()` at install time is fine. It's a different use case (package deployment vs. development workflow).

### What the Research Enabled

- **Clear understanding of template flow:** Workspace → MCP watcher → Database
- **No architectural mismatch:** The two systems (disk-sync and installer) work in parallel correctly
- **Identified gaps:** Configuration visibility and documentation
- **Design rationale:** Why templates work this way (MyBB's DB-first architecture)

### Questions for Architect

1. Should plugin templates be created in _install() or rely on disk-sync?
2. Should workspace_root be auto-detected or require configuration?
3. Should templates be added to PluginInstaller as well, or stay disk-sync only?
4. Is the theme/plugin template path difference acceptable or should we unify?

---

## Appendix

### Reference Files

| File | Lines | Purpose |
|------|-------|---------|
| `plugin_manager/manager.py` | 310-338 | Scaffold creates templates/ |
| `plugin_manager/installer.py` | 74-224 | PluginInstaller (code only) |
| `plugin_manager/installer.py` | 502-601 | ThemeInstaller (templates too) |
| `mybb_mcp/mybb_mcp/sync/watcher.py` | 524-548 | FileWatcher watches workspace |
| `mybb_mcp/mybb_mcp/sync/watcher.py` | 290-347 | Plugin template change handler |
| `mybb_mcp/mybb_mcp/sync/router.py` | 155-225 | Path routing for plugins |
| `mybb_mcp/mybb_mcp/sync/plugin_templates.py` | 79-165 | Database sync logic |

### Evidence Chain

1. Workspace templates created: `plugin_manager/manager.py:312`
2. Watcher watches workspace: `mybb_mcp/sync/watcher.py:534-535`
3. Router identifies plugin templates: `mybb_mcp/sync/router.py:178`
4. Handler queues templates: `mybb_mcp/sync/watcher.py:332-338`
5. Importer syncs to DB: `mybb_mcp/sync/plugin_templates.py:154-159`
6. Plugin accesses templates: `$templates->get('{codename}_{name}')`

### Test Cases to Verify

- [ ] Create plugin with `has_templates=True` → templates/ dir created
- [ ] Add file to templates/ → MCP watcher syncs to DB within 5 seconds
- [ ] Edit template file → DB template updates (UPDATE path)
- [ ] Delete template from workspace → DB template remains (intentional)
- [ ] Theme-specific templates → sync to correct template set sid
- [ ] Install plugin → code deployed, templates NOT copied (confirmed by inspection)
- [ ] workspace_root not configured → templates not synced (warning expected)

### Confidence Summary

| Area | Confidence | Notes |
|------|------------|-------|
| Workspace source location | 0.99 | Direct code confirmation |
| MCP watcher dual-watching | 0.98 | Code inspection clear |
| Plugin template routing | 0.99 | Path patterns explicit |
| Database sync logic | 0.98 | Call chain traced |
| Plugin installer behavior | 0.99 | Explicit omission of templates/ |
| Theme installer different path | 0.98 | Code inspection confirmed |
| Configuration gap (workspace_root) | 0.95 | Optional parameter, requires explicit set |

---

**Research Completed:** 2026-01-19 10:03 UTC
**Overall Confidence:** 0.95
**Status:** Ready for Architect


---
## Appendix
<!-- ID: appendix -->
- **References:** [Link to diagrams, ADRs, whitepapers, or related documents]
- **Attachments:** [List supporting artifacts or datasets]


---