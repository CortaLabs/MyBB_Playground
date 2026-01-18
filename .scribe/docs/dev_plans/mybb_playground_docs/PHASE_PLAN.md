---
id: mybb_playground_docs-phase-plan
title: "\u2699\uFE0F Phase Plan \u2014 mybb-playground-docs"
doc_name: phase_plan
category: engineering
status: draft
version: '0.1'
last_updated: '2026-01-18'
maintained_by: Corta Labs
created_by: Corta Labs
owners: []
related_docs: []
tags: []
summary: ''
---

# ⚙️ Phase Plan — mybb-playground-docs
**Author:** Scribe
**Version:** Draft v0.1
**Status:** active
**Last Updated:** 2026-01-18 08:09:46 UTC

> Execution roadmap for mybb-playground-docs.

---
## Phase Overview
<!-- ID: phase_overview -->
| Phase | Goal | Key Deliverables | Est. Effort | Confidence |
|-------|------|------------------|-------------|------------|
| Phase 0 | Directory Setup & Index | Wiki directory structure, main index.md | Low | 0.95 |
| Phase 1 | Getting Started Docs | installation.md, quickstart.md (3 files) | Low | 0.95 |
| Phase 2 | MCP Tools Reference | 11 tool category documents (85+ tools) | High | 0.90 |
| Phase 3 | Plugin Manager Docs | 5 documents covering workspace, deployment, lifecycle | Medium | 0.92 |
| Phase 4 | Architecture Docs | 4 documents on system internals | Medium | 0.88 |
| Phase 5 | Best Practices | 4 documents on plugin/theme development, security | Medium | 0.85 |
| Phase 6 | CLAUDE.md Update | Add documentation reference section | Low | 0.98 |

**Total Deliverables:** 26 wiki documents + CLAUDE.md update
**Critical Path:** Phase 0 -> Phase 1 -> Phase 2/3/4/5 (parallel) -> Phase 6
<!-- ID: phase_0 -->
**Objective:** Create the wiki directory structure and main index page.

**Scope:** 1 document + directory creation

### Task Package 0.1: Create Wiki Directory Structure

**Files to Create:**
```
/docs/wiki/
├── getting_started/
├── mcp_tools/
├── plugin_manager/
├── architecture/
└── best_practices/
```

**Verification:**
- [ ] All 5 subdirectories exist
- [ ] Directories are empty (ready for content)

### Task Package 0.2: Create Main Index

**File:** `/docs/wiki/index.md`

**Content Requirements:**
- Wiki title and introduction
- Navigation links to all 5 sections
- Brief description of each section
- Link to CLAUDE.md for quick setup

**Source:** Architecture document section 3 (Wiki Structure Overview)

**Verification:**
- [ ] index.md exists at /docs/wiki/index.md
- [ ] All section links present
- [ ] No placeholder content

**Deliverables:**
- `/docs/wiki/index.md` (main landing page)
- 5 empty subdirectories

**Dependencies:** None (first phase)

**Acceptance Criteria:**
- [ ] Directory structure matches architecture spec
- [ ] Main index provides complete navigation
<!-- ID: phase_1 -->
---
## Phase 1 - Getting Started Documentation
<!-- ID: phase_1 -->

**Objective:** Create the getting started section with installation and quickstart guides.

**Scope:** 3 documents

### Task Package 1.1: Getting Started Index

**File:** `/docs/wiki/getting_started/index.md`

**Content Requirements:**
- Section overview
- Links to installation and quickstart
- Prerequisites summary

**Verification:**
- [ ] Links to installation.md and quickstart.md work
- [ ] No broken internal links

### Task Package 1.2: Installation Guide

**File:** `/docs/wiki/getting_started/installation.md`

**Content Requirements:**
- Prerequisites (Python 3.10+, PHP 8.0+, MariaDB)
- Installation steps from CLAUDE.md
- Environment variables from config.py (MYBB_DB_HOST, MYBB_DB_NAME, etc.)
- MCP server configuration
- Verification steps

**Source:** 
- CLAUDE.md (Development Environment section)
- RESEARCH_MCP_SERVER_ARCHITECTURE (Configuration System section)

**Verification:**
- [ ] All environment variables documented
- [ ] Steps match actual setup process

### Task Package 1.3: Quickstart Guide

**File:** `/docs/wiki/getting_started/quickstart.md`

**Content Requirements:**
- 5-minute getting started tutorial
- First MCP tool invocation
- Creating a simple plugin
- Viewing templates

**Source:** CLAUDE.md (Quick Start section)

**Verification:**
- [ ] Tutorial is complete and executable
- [ ] No assumptions about prior knowledge

**Deliverables:**
- `/docs/wiki/getting_started/index.md`
- `/docs/wiki/getting_started/installation.md`
- `/docs/wiki/getting_started/quickstart.md`

**Dependencies:** Phase 0 (directories must exist)

**Acceptance Criteria:**
- [ ] All 3 files created
- [ ] Installation steps match CLAUDE.md
- [ ] Environment variables match config.py
<!-- ID: milestone_tracking -->
---
## Phase 2 - MCP Tools Reference (HIGH EFFORT)
<!-- ID: phase_2 -->

**Objective:** Document all 85+ MCP tools organized by category.

**Scope:** 11 documents (largest phase)

### Task Package 2.1: MCP Tools Index

**File:** `/docs/wiki/mcp_tools/index.md`

**Content Requirements:**
- Overview of 13 tool categories
- Tool count per category
- Links to all category pages
- Quick reference table with tool names

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 3)

### Task Package 2.2: Template Tools (9 tools)

**File:** `/docs/wiki/mcp_tools/templates.md`

**Tools to Document:**
1. mybb_list_template_sets
2. mybb_list_templates
3. mybb_read_template
4. mybb_write_template
5. mybb_list_template_groups
6. mybb_template_find_replace
7. mybb_template_batch_read
8. mybb_template_batch_write
9. mybb_template_outdated

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 3.A)

### Task Package 2.3: Theme/Stylesheet Tools (6 tools)

**File:** `/docs/wiki/mcp_tools/themes_stylesheets.md`

**Tools to Document:**
1. mybb_list_themes
2. mybb_list_stylesheets
3. mybb_read_stylesheet
4. mybb_write_stylesheet
5. mybb_create_theme

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 3.B)

### Task Package 2.4: Plugin Tools (15 tools)

**File:** `/docs/wiki/mcp_tools/plugins.md`

**Tools to Document:**
1. mybb_list_plugins
2. mybb_read_plugin
3. mybb_create_plugin
4. mybb_list_hooks
5. mybb_hooks_discover
6. mybb_hooks_usage
7. mybb_analyze_plugin
8. mybb_plugin_list_installed
9. mybb_plugin_info
10. mybb_plugin_activate
11. mybb_plugin_deactivate
12. mybb_plugin_is_installed
13. mybb_plugin_install
14. mybb_plugin_uninstall
15. mybb_plugin_status

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 3.C)

### Task Package 2.5: Forum/Thread/Post Tools (17 tools)

**File:** `/docs/wiki/mcp_tools/forums_threads_posts.md`

**Tools to Document:**
- mybb_forum_list, mybb_forum_read, mybb_forum_create, mybb_forum_update, mybb_forum_delete (5)
- mybb_thread_list, mybb_thread_read, mybb_thread_create, mybb_thread_update, mybb_thread_delete, mybb_thread_move (6)
- mybb_post_list, mybb_post_read, mybb_post_create, mybb_post_update, mybb_post_delete (5)

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Sections 3.F, 3.G, 3.H)

### Task Package 2.6: User/Moderation Tools (14 tools)

**File:** `/docs/wiki/mcp_tools/users_moderation.md`

**Tools to Document:**
- mybb_user_get, mybb_user_list, mybb_user_update_group, mybb_user_ban, mybb_user_unban, mybb_usergroup_list (6)
- mybb_mod_close_thread, mybb_mod_stick_thread, mybb_mod_approve_thread, mybb_mod_approve_post, mybb_mod_soft_delete_thread, mybb_mod_soft_delete_post, mybb_modlog_list, mybb_modlog_add (8)

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Sections 3.L, 3.M)

### Task Package 2.7: Search Tools (4 tools)

**File:** `/docs/wiki/mcp_tools/search.md`

**Tools to Document:**
1. mybb_search_posts
2. mybb_search_threads
3. mybb_search_users
4. mybb_search_advanced

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 3.J)

### Task Package 2.8: Admin/Settings Tools (11 tools)

**File:** `/docs/wiki/mcp_tools/admin_settings.md`

**Tools to Document:**
- mybb_setting_get, mybb_setting_set, mybb_setting_list, mybb_settinggroup_list (4)
- mybb_cache_read, mybb_cache_rebuild, mybb_cache_list, mybb_cache_clear (4)
- mybb_stats_forum, mybb_stats_board (2)

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 3.K)

### Task Package 2.9: Task Tools (5 tools)

**File:** `/docs/wiki/mcp_tools/tasks.md`

**Tools to Document:**
1. mybb_task_list
2. mybb_task_get
3. mybb_task_enable
4. mybb_task_disable
5. mybb_task_run_log

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 3.D)

### Task Package 2.10: Disk Sync Tools (5 tools)

**File:** `/docs/wiki/mcp_tools/disk_sync.md`

**Tools to Document:**
1. mybb_sync_export_templates
2. mybb_sync_export_stylesheets
3. mybb_sync_start_watcher
4. mybb_sync_stop_watcher
5. mybb_sync_status

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 3.I)

### Task Package 2.11: Database Tool (1 tool)

**File:** `/docs/wiki/mcp_tools/database.md`

**Tools to Document:**
1. mybb_db_query

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 3.E)

**Deliverables:** 11 files in `/docs/wiki/mcp_tools/`

**Dependencies:** Phase 0 (directories)

**Acceptance Criteria:**
- [ ] All 85+ tools documented
- [ ] Every tool has parameters table with types/defaults
- [ ] Every tool has return format description

---
## Phase 3 - Plugin Manager Documentation
<!-- ID: phase_3 -->

**Objective:** Document the Plugin Manager system comprehensively.

**Scope:** 5 documents

### Task Package 3.1: Plugin Manager Index

**File:** `/docs/wiki/plugin_manager/index.md`

**Content Requirements:**
- System overview
- Component diagram
- Links to all subsections

**Source:** RESEARCH_PLUGIN_MANAGER (Section 1)

### Task Package 3.2: Workspace Documentation

**File:** `/docs/wiki/plugin_manager/workspace.md`

**Content Requirements:**
- Directory structure (plugins/public, plugins/private, themes/*)
- PluginWorkspace and ThemeWorkspace classes
- meta.json schema
- Workspace validation

**Source:** RESEARCH_PLUGIN_MANAGER (Sections 5, 8)

### Task Package 3.3: Deployment Documentation

**File:** `/docs/wiki/plugin_manager/deployment.md`

**Content Requirements:**
- PluginInstaller and ThemeInstaller classes
- Directory overlay system
- Deployment manifest format
- Backup and restore process

**Source:** RESEARCH_PLUGIN_MANAGER (Section 3)

### Task Package 3.4: Lifecycle Documentation

**File:** `/docs/wiki/plugin_manager/lifecycle.md`

**Content Requirements:**
- PHP Bridge actions (all 7)
- BridgeResult dataclass
- PluginLifecycle class methods
- activate_full and deactivate_full workflows

**Source:** RESEARCH_PHP_BRIDGE (complete), RESEARCH_PLUGIN_MANAGER (Section 6)

### Task Package 3.5: Database Documentation

**File:** `/docs/wiki/plugin_manager/database.md`

**Content Requirements:**
- SQLite schema (projects, history tables)
- ProjectDatabase class methods
- Deployment manifest storage
- Query methods

**Source:** RESEARCH_PLUGIN_MANAGER (Section 4)

**Deliverables:** 5 files in `/docs/wiki/plugin_manager/`

**Dependencies:** Phase 0

**Acceptance Criteria:**
- [ ] All Plugin Manager components documented
- [ ] PHP Bridge fully covered
- [ ] Database schema complete

---
## Phase 4 - Architecture Documentation
<!-- ID: phase_4 -->

**Objective:** Document system internals and architecture.

**Scope:** 4 documents

### Task Package 4.1: Architecture Index

**File:** `/docs/wiki/architecture/index.md`

**Content Requirements:**
- System overview diagram
- Component relationships
- Links to detailed pages

### Task Package 4.2: MCP Server Architecture

**File:** `/docs/wiki/architecture/mcp_server.md`

**Content Requirements:**
- Server initialization
- Tool registration
- Database connection management
- Connection pooling strategy

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Sections 5, 6)

### Task Package 4.3: Disk Sync Architecture

**File:** `/docs/wiki/architecture/disk_sync.md`

**Content Requirements:**
- DiskSyncService orchestrator
- File watcher implementation
- Template/stylesheet import/export
- Race condition prevention

**Source:** RESEARCH_DISK_SYNC_SERVICE (complete)

### Task Package 4.4: Configuration Documentation

**File:** `/docs/wiki/architecture/configuration.md`

**Content Requirements:**
- Environment variables (all)
- Configuration loading
- Plugin Manager config.py
- Sync config

**Source:** Multiple research docs

**Deliverables:** 4 files in `/docs/wiki/architecture/`

**Dependencies:** Phase 0

**Acceptance Criteria:**
- [ ] All system components documented
- [ ] Configuration fully covered

---
## Phase 5 - Best Practices Documentation
<!-- ID: phase_5 -->

**Objective:** Document best practices for MyBB development.

**Scope:** 4 documents

### Task Package 5.1: Best Practices Index

**File:** `/docs/wiki/best_practices/index.md`

**Content Requirements:**
- Overview of best practices
- Links to all guides

### Task Package 5.2: Plugin Development Guide

**File:** `/docs/wiki/best_practices/plugin_development.md`

**Content Requirements:**
- Plugin structure (_info, _activate, _deactivate, _install, _uninstall)
- Hook usage patterns
- Settings management
- Template management
- Database operations

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 4), RESEARCH_PLUGIN_MANAGER

### Task Package 5.3: Theme Development Guide

**File:** `/docs/wiki/best_practices/theme_development.md`

**Content Requirements:**
- Theme structure
- Stylesheet inheritance
- Template overrides
- Theme packaging

**Source:** RESEARCH_DISK_SYNC_SERVICE, RESEARCH_PLUGIN_MANAGER

### Task Package 5.4: Security Guide

**File:** `/docs/wiki/best_practices/security.md`

**Content Requirements:**
- Input validation
- CSRF protection
- SQL injection prevention
- Sensitive data handling

**Source:** RESEARCH_MCP_SERVER_ARCHITECTURE (Section 7), RESEARCH_PHP_BRIDGE

**Deliverables:** 4 files in `/docs/wiki/best_practices/`

**Dependencies:** Phase 0

**Acceptance Criteria:**
- [ ] All best practices documented
- [ ] Security considerations covered

---
## Phase 6 - CLAUDE.md Update
<!-- ID: phase_6 -->

**Objective:** Add documentation reference section to CLAUDE.md.

**Scope:** 1 file modification

### Task Package 6.1: Update CLAUDE.md

**File:** `/home/austin/projects/MyBB_Playground/CLAUDE.md`

**Content to Add:**
```markdown
## Documentation Reference

Comprehensive documentation is available in `/docs/wiki/`:

| Section | Description |
|---------|-------------|
| [Getting Started](docs/wiki/getting_started/index.md) | Installation and quickstart |
| [MCP Tools Reference](docs/wiki/mcp_tools/index.md) | All 85+ MCP tools |
| [Plugin Manager](docs/wiki/plugin_manager/index.md) | Workspace, deployment, lifecycle |
| [Architecture](docs/wiki/architecture/index.md) | System internals |
| [Best Practices](docs/wiki/best_practices/index.md) | Development guidelines |

For detailed tool documentation, see the MCP Tools Reference.
```

**Verification:**
- [ ] Section added to CLAUDE.md
- [ ] All links are correct relative paths
- [ ] Section integrates with existing document structure

**Deliverables:** Updated CLAUDE.md

**Dependencies:** Phases 0-5 (all wiki docs must exist first)

**Acceptance Criteria:**
- [ ] CLAUDE.md references all wiki sections
- [ ] Links resolve correctly

---
## Milestone Tracking
<!-- ID: milestone_tracking -->

| Milestone | Phase | Deliverables | Status | Evidence |
|-----------|-------|--------------|--------|----------|
| Wiki Structure Created | 0 | Directory + index.md | Pending | - |
| Getting Started Complete | 1 | 3 docs | Pending | - |
| MCP Tools Complete | 2 | 11 docs | Pending | - |
| Plugin Manager Complete | 3 | 5 docs | Pending | - |
| Architecture Complete | 4 | 4 docs | Pending | - |
| Best Practices Complete | 5 | 4 docs | Pending | - |
| CLAUDE.md Updated | 6 | 1 file update | Pending | - |
| **Documentation Complete** | All | **26 docs + update** | Pending | - |

**Phase Dependencies:**
```
Phase 0 ──► Phase 1 ──► ┬─► Phase 2 ─┐
                        ├─► Phase 3 ─┼──► Phase 6
                        ├─► Phase 4 ─┤
                        └─► Phase 5 ─┘
```
<!-- ID: retro_notes -->
- Summarise lessons learned after each phase completes.  
- Document any scope changes or re-planning decisions here.


---