# Research: Prior Audits, Tool Inventory, and Critical Constraints

**Author:** Research-Audits
**Date:** 2026-01-18 03:49 UTC
**Project:** plugin-theme-manager
**Status:** COMPLETE
**Confidence:** 0.95

---

## Executive Summary

This research completes the audit phase by systematically cataloging:
1. **60+ verified MCP tools** in 12 categories (from `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/server.py`)
2. **Prior ecosystem audit findings** (390 log entries documenting MyBB hooks, plugin patterns, database schema)
3. **Existing research documents** (workflow mapping, sync system integration)
4. **Critical architectural constraints** that must inform design decisions

**Key Verdict:** Zero new MCP tools required. All plugin-theme-manager functionality can be built by orchestrating existing MCP tools with additional Python/CLI logic for file operations, SQLite management, and workflow composition.

---

## 1. Complete MCP Tool Inventory

### 1.1 Tools by Category

| Category | Count | Tools | Purpose |
|----------|-------|-------|---------|
| **Templates** | 9 | list, read, write, batch, find/replace, outdated | Template management and inheritance |
| **Themes/Stylesheets** | 4 | list, read, write | Theme CSS management |
| **Plugin Development** | 6 | create, read, list hooks, discover, usage | Plugin scaffolding and hook integration |
| **Plugin Analysis** | 1 | analyze | Plugin structure audit |
| **Plugin Lifecycle** | 4 | list, info, activate, deactivate, is_installed | Plugin state management |
| **Scheduled Tasks** | 6 | list, get, enable, disable, update, log | Task scheduling and execution |
| **Database** | 1 | query (read-only SELECT) | Data exploration |
| **Content CRUD** | 16 | Forums (5), Threads (6), Posts (5) | Forum/thread/post management |
| **Disk Sync** | 5 | export templates, export stylesheets, start/stop watcher, status | File-database synchronization |
| **Search** | 4 | posts, threads, users, advanced | Content search |
| **Admin** | 10 | Settings (4), Cache (4), Stats (2) | System settings and statistics |
| **Moderation** | 8 | Close, stick, approve threads/posts, soft delete, modlog | Content moderation |
| **User Management** | 7 | Get, list, update groups, ban, unban, usergroups | User account management |
| **TOTAL** | **60+** | | |

**Source:** `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/server.py` (lines 51-1049, 2839 total lines)

---

## 2. Critical Tools for Plugin-Theme Manager

### 2.1 Absolute Requirements (CRITICAL)
- `mybb_create_plugin` - Scaffold plugin structure
- `mybb_list_plugins` - Enumerate plugins
- `mybb_analyze_plugin` - Audit plugin internals
- `mybb_plugin_activate` - Enable plugin cache entry
- `mybb_plugin_deactivate` - Disable plugin cache entry
- `mybb_plugin_info` - Extract plugin metadata
- `mybb_plugin_is_installed` - Check installation status

### 2.2 High Priority (for deployment)
- `mybb_list_templates` - Find plugin templates
- `mybb_write_template` - Deploy plugin templates
- `mybb_template_batch_write` - Deploy multiple templates atomically
- `mybb_read_stylesheet` - Inspect plugin CSS
- `mybb_write_stylesheet` - Deploy plugin CSS
- `mybb_setting_set` - Configure plugin settings
- `mybb_cache_rebuild` - Verify deployment
- `mybb_stats_board` - Validate state

### 2.3 Supporting (optional but useful)
- `mybb_hooks_discover` - Find hook injection points
- `mybb_hooks_usage` - Verify hook integration
- `mybb_setting_list` - Enumerate available settings
- `mybb_db_query` - Validate custom plugin tables
- `mybb_template_find_replace` - Bulk template modification

---

## 3. Prior Research Findings (Ecosystem Audit)

### 3.1 Audit Scope (390 log entries)
The comprehensive MyBB Ecosystem Audit project investigated:

1. **MyBB Core Hooks System**
   - Hook categories: index, showthread, member, admin, global, and more
   - Execution lifecycle and plugin attachment mechanisms
   - Undocumented hooks discovered via `$plugins->run_hooks()` calls

2. **Admin CP Structure**
   - Modules organization: index.php → modules/ subdirectory
   - Settings management API
   - User/forum/plugin/theme management workflows

3. **Plugin Development Patterns**
   - Required functions: `_info()`, `_activate()`, `_deactivate()`, `_install()`, `_uninstall()`, `_is_installed()`
   - Plugin APIs: settings, templates, database tables, scheduled tasks, alerts
   - Common patterns from existing plugins

4. **VSCode MyBBBridge Extension**
   - Feature audit comparing VSCode extension vs MCP tools
   - Identified unique features, gaps, and parity analysis

5. **MyBB MCP Server Implementation**
   - Comprehensive audit of 20+ tools
   - Architecture and design patterns
   - Security measures (parameterized queries, field exclusion)

6. **MyBB Database Schema**
   - Complete table structure and relationships
   - MCP integration opportunities and coverage gaps
   - Plugin table patterns and metadata storage

7. **Admin Module Organization**
   - Directory structure and file organization
   - Integration points for automated operations

**Confidence Levels:**
- Hook system understanding: 0.90+
- Plugin patterns: 0.92+
- Database schema: 0.95+

---

## 4. Critical Architectural Constraints

### 4.1 Plugin Activation/Deactivation Limitation (HIGH IMPACT)

**Problem:** MCP tools `mybb_plugin_activate` and `mybb_plugin_deactivate` manage cache only.

**What This Means:**
- Adds plugin to `$_DCACHE['plugins']` in memory
- Does NOT trigger `{codename}_activate()` PHP function
- Does NOT trigger `{codename}_deactivate()` PHP function
- Does NOT create plugin database tables (requires `_install()`)
- Does NOT execute any plugin initialization hooks

**Consequence:** Full plugin activation requires manual step through MyBB Admin CP.

**Workaround:** Design workflows to document this requirement prominently. Consider documenting the ACP workflow as a separate step in the UI.

**Confidence:** 0.95

---

### 4.2 File Operations Gap (CRITICAL)

**Problem:** No MCP tool provides file copy, move, delete, or zip operations.

**Critical for Workflows:**
- Install plugin: Copy plugin PHP from `plugins/private/{name}/` → `TestForum/inc/plugins/`
- Install languages: Copy language files from workspace → `TestForum/inc/languages/`
- Export plugin: Zip plugin files for distribution
- Import plugin: Unzip plugin archive

**Solution Options:**
1. **Python CLI Layer** (Recommended): Build Python script that handles file operations, calls MCP tools for DB operations
2. **Bash Scripts**: Provide bash wrapper scripts for common workflows
3. **New Orchestration Tool** (Future): If workflows become complex, could build a high-level orchestration tool that wraps both file ops and MCP calls

**Confidence:** 0.99

---

### 4.3 SQLite Write Access Gap (MODERATE)

**Problem:** Only `mybb_db_query` available (SELECT only), no write access for custom tables.

**Impact:**
- Cannot programmatically create plugin tracking database
- Cannot update plugin installation status in metadata DB
- Requires manual SQL or CLI tool for database maintenance

**Solution:** Build lightweight Python SQLite wrapper or use Django ORM for metadata management.

**Confidence:** 0.98

---

### 4.4 Batch Stylesheet Operations (MINOR)

**Problem:** No batch stylesheet deployment. `mybb_write_stylesheet` requires stylesheet ID, not filename mapping.

**Workaround:** Loop over stylesheets and call tool for each one.

**Impact:** Low—can be mitigated with simple iteration.

**Confidence:** 0.95

---

## 5. Existing Research Documents

### 5.1 RESEARCH_WORKFLOW_MAPPING_20260118.md
- **Scope:** Maps 5 workflows (Create, Install, Sync, Export, Import) to MCP tools
- **Gap Analysis:** Identifies file operations, SQLite access, and workspace management gaps
- **Verdict:** Orchestration layer required above MCP

### 5.2 RESEARCH_SYNC_SYSTEM_INTEGRATION_20260117_0347.md
- **Scope:** Bidirectional file-database sync system for templates and stylesheets
- **Architecture:** DiskSyncService, FileWatcher, TemplateImporter/Exporter, PathRouter (~1,700 LOC)
- **Finding:** Sync system handles MyBB core templates, NOT plugin templates
- **Opportunity:** Could extend path routing to support `plugins/` routes for plugin template sync

---

## 6. Plugin Structure Compliance (from Prior Audit)

### 6.1 Required Plugin Functions
```php
// Metadata
function {codename}_info() {
    return ["name" => "...", "description" => "...", ...];
}

// Activation (called via ACP only, NOT by MCP tool)
function {codename}_activate() { ... }

// Deactivation (called via ACP only, NOT by MCP tool)
function {codename}_deactivate() { ... }

// Installation setup
function {codename}_install() {
    // Create tables, add settings, add templates
}

// Uninstallation cleanup
function {codename}_uninstall() {
    // Drop tables, remove settings
}

// Status check
function {codename}_is_installed() { ... }
```

### 6.2 Template Inheritance (SID Model)
- **SID = -2:** Master templates (base, never delete)
- **SID = -1:** Global templates (shared across themes)
- **SID >= 1:** Custom theme overrides
- Custom templates automatically override master when version matches

---

## 7. Design Recommendations for Architect

### 7.1 Architecture Approach
1. **Core Layer:** Orchestration logic (Python/CLI) that combines:
   - File system operations (copy, move, delete, zip)
   - MCP tool calls for database operations
   - SQLite metadata management

2. **Workflow Layer:** Compose core operations into higher-level workflows:
   - Create plugin (file ops + MCP scaffold)
   - Install plugin (file copy + MCP activate)
   - Sync changes (file watch + MCP write)
   - Export plugin (zip + metadata export)
   - Import plugin (unzip + registration)

3. **Public/Private Registry:** Store metadata in SQLite:
   - Plugin name, version, codename, description
   - Public vs private flag
   - Installation status, file manifest
   - Dependency information

### 7.2 Handling the Activation Limitation
**Option A (Recommended):** Document as required manual step
- CLI output: "Plugin created successfully. To complete activation, visit Admin CP > Plugins and activate manually."
- Rationale: Clear, honest, user understands why

**Option B (Future Enhancement):** Investigate hook invocation patterns
- Could potentially call `_activate()` directly if safe
- Requires extensive testing and security review
- Not recommended for initial release

### 7.3 Critical Implementation Constraints
1. **File Operations Required:** Must implement or integrate file copy/move/delete logic
2. **Workspace Management:** Track plugin source location, build output, test setup
3. **Metadata Persistence:** SQLite or similar for tracking plugin state across sessions
4. **Error Handling:** Clear error messages when MCP tools fail (validation, database errors, etc.)

---

## 8. What's NOT Required

- **New MCP tools:** All 60+ existing tools are sufficient
- **Hook invocation:** Not feasible to implement safely
- **Direct database access:** Parameterized MCP queries sufficient for validation
- **VSCode extension:** Plugin-theme-manager is independent of VSCode integration

---

## 9. Confidence Summary

| Finding | Confidence | Evidence | Risk |
|---------|-----------|----------|------|
| 60+ tools cataloged | 0.99 | Direct code inspection | NONE |
| Tool categories mapped | 0.98 | Tool definitions extracted | LOW |
| Activation limitation | 0.95 | Tool descriptions document cache-only behavior | LOW |
| File operations gap | 0.99 | No file tools in MCP | MEDIUM |
| SQLite write gap | 0.98 | Only SELECT available | MEDIUM |
| Sync system architecture | 0.92 | Code inspection and docs | LOW |
| Prior audit quality | 0.90 | 390 entries reviewed | LOW |

---

## 10. Handoff Notes for Architect

### Must-Know Constraints
1. **Activation is a two-step process:** MCP tool enables cache, ACP manual step triggers hooks
2. **File operations are out of scope for MCP:** Build Python CLI layer
3. **Metadata persistence required:** Choose SQLite or lightweight DB
4. **Template SID model is fixed:** Public/private isolation must work within existing constraints

### Validation Points
Before architecture sign-off:
- Confirm MCP tool list is exhaustive (scan server.py for any missed tools)
- Validate plugin activation behavior (test _activate() hook execution)
- Prototype file operations layer (verify feasibility)
- Design metadata schema (SQLite structure for plugin tracking)

---

## 11. References

**Code:**
- MCP Server: `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/server.py` (2839 lines, 60+ tools)
- Database Layer: `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/db/connection.py`
- Sync Service: `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/sync/service.py` (~1,700 LOC)
- Plugin Tools: `/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/tools/plugins.py`

**Prior Research:**
- RESEARCH_WORKFLOW_MAPPING_20260118.md (workflow-to-tool gap analysis)
- RESEARCH_SYNC_SYSTEM_INTEGRATION_20260117_0347.md (sync system architecture)
- MyBB Ecosystem Audit project (390 entries, hooks/patterns/schema research)

**Documentation:**
- https://docs.mybb.com/1.8/development/plugins/
- https://docs.mybb.com/1.8/development/plugins/hooks/

---

**Ready for:** Architect phase (Stage 2: PROTOCOL workflow)
**Confidence Grade:** 95% (High confidence on critical findings)
