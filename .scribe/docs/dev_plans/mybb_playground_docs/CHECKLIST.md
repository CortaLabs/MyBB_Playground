---
id: mybb_playground_docs-checklist
title: "\u2705 Acceptance Checklist \u2014 mybb-playground-docs"
doc_name: checklist
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

# ✅ Acceptance Checklist — mybb-playground-docs
**Author:** Scribe
**Version:** v0.1
**Status:** Draft
**Last Updated:** 2026-01-18 08:09:46 UTC

> Acceptance checklist for mybb-playground-docs.

---
## Documentation Hygiene
<!-- ID: documentation_hygiene -->
**Pre-Implementation Verification:**
- [ ] Architecture guide reviewed and understood
- [ ] Phase plan reviewed and task packages understood
- [ ] Research documents accessible and read

**Per-Document Quality Standards:**
- [ ] No placeholder content (every section complete)
- [ ] All code examples tested where applicable
- [ ] All internal links verified
- [ ] Consistent markdown formatting
- [ ] Proper code block language tags (php, python, bash, json, markdown)
<!-- ID: phase_0 -->
---
## Phase 0: Directory Setup & Index
<!-- ID: phase_0 -->

**Task 0.1: Create Wiki Directory Structure**
- [ ] Created `/docs/wiki/` directory
- [ ] Created `/docs/wiki/getting_started/` subdirectory
- [ ] Created `/docs/wiki/mcp_tools/` subdirectory
- [ ] Created `/docs/wiki/plugin_manager/` subdirectory
- [ ] Created `/docs/wiki/architecture/` subdirectory
- [ ] Created `/docs/wiki/best_practices/` subdirectory

**Task 0.2: Create Main Index**
- [ ] Created `/docs/wiki/index.md`
- [ ] Index contains wiki title and introduction
- [ ] Index contains navigation links to all 5 sections
- [ ] Index contains brief description of each section
- [ ] No placeholder content in index

**Phase 0 Complete:**
- [ ] All 5 subdirectories exist (verified with `ls`)
- [ ] index.md renders correctly

---
## Phase 1: Getting Started Documentation
<!-- ID: phase_1 -->

**Task 1.1: Getting Started Index**
- [ ] Created `/docs/wiki/getting_started/index.md`
- [ ] Contains section overview
- [ ] Contains working links to installation.md and quickstart.md

**Task 1.2: Installation Guide**
- [ ] Created `/docs/wiki/getting_started/installation.md`
- [ ] Documents prerequisites (Python 3.10+, PHP 8.0+, MariaDB)
- [ ] Documents all environment variables from config.py:
  - [ ] MYBB_DB_HOST
  - [ ] MYBB_DB_PORT
  - [ ] MYBB_DB_NAME
  - [ ] MYBB_DB_USER
  - [ ] MYBB_DB_PASS
  - [ ] MYBB_DB_PREFIX
  - [ ] MYBB_DB_POOL_SIZE
  - [ ] MYBB_DB_POOL_NAME
  - [ ] MYBB_ROOT
  - [ ] MYBB_URL
  - [ ] MYBB_PORT
- [ ] Documents MCP server configuration
- [ ] Includes verification steps

**Task 1.3: Quickstart Guide**
- [ ] Created `/docs/wiki/getting_started/quickstart.md`
- [ ] Contains 5-minute tutorial
- [ ] Shows first MCP tool invocation
- [ ] Shows creating a simple plugin example
- [ ] Shows viewing templates example

**Phase 1 Complete:**
- [ ] All 3 files exist and have no placeholder content
- [ ] All internal links work

---
## Phase 2: MCP Tools Reference (85+ Tools)
<!-- ID: phase_2 -->

**Task 2.1: MCP Tools Index**
- [ ] Created `/docs/wiki/mcp_tools/index.md`
- [ ] Lists all 13 tool categories
- [ ] Shows tool count per category
- [ ] Contains working links to all category pages

**Task 2.2: Template Tools**
- [x] Created `/docs/wiki/mcp_tools/templates.md`
- [x] Documents all 9 template tools with parameters tables
- [x] Tools: list_template_sets, list_templates, read_template, write_template, list_template_groups, template_find_replace, template_batch_read, template_batch_write, template_outdated

**Task 2.3: Theme/Stylesheet Tools**
- [x] Created `/docs/wiki/mcp_tools/themes_stylesheets.md`
- [x] Documents all 6 theme/stylesheet tools with parameters tables
- [x] Tools: list_themes, list_stylesheets, read_stylesheet, write_stylesheet, create_theme

**Task 2.4: Plugin Tools**
- [ ] Created `/docs/wiki/mcp_tools/plugins.md`
- [ ] Documents all 15 plugin tools with parameters tables
- [ ] Includes clear distinction between cache-only vs full lifecycle tools

**Task 2.5: Forum/Thread/Post Tools**
- [ ] Created `/docs/wiki/mcp_tools/forums_threads_posts.md`
- [ ] Documents all 17 content tools with parameters tables
- [ ] Forum tools (5): list, read, create, update, delete
- [ ] Thread tools (6): list, read, create, update, delete, move
- [ ] Post tools (5): list, read, create, update, delete

**Task 2.6: User/Moderation Tools**
- [ ] Created `/docs/wiki/mcp_tools/users_moderation.md`
- [ ] Documents all 14 user/mod tools with parameters tables
- [ ] User tools (6): get, list, update_group, ban, unban, usergroup_list
- [ ] Mod tools (8): close_thread, stick_thread, approve_thread, approve_post, soft_delete_thread, soft_delete_post, modlog_list, modlog_add

**Task 2.7: Search Tools**
- [ ] Created `/docs/wiki/mcp_tools/search.md`
- [ ] Documents all 4 search tools with parameters tables
- [ ] Tools: search_posts, search_threads, search_users, search_advanced

**Task 2.8: Admin/Settings Tools**
- [ ] Created `/docs/wiki/mcp_tools/admin_settings.md`
- [ ] Documents all 11 admin tools with parameters tables
- [ ] Setting tools (4): get, set, list, settinggroup_list
- [ ] Cache tools (4): read, rebuild, list, clear
- [ ] Stats tools (2): forum, board

**Task 2.9: Task Tools**
- [ ] Created `/docs/wiki/mcp_tools/tasks.md`
- [ ] Documents all 5 task tools with parameters tables
- [ ] Tools: list, get, enable, disable, run_log

**Task 2.10: Disk Sync Tools**
- [ ] Created `/docs/wiki/mcp_tools/disk_sync.md`
- [ ] Documents all 5 sync tools with parameters tables
- [ ] Tools: export_templates, export_stylesheets, start_watcher, stop_watcher, status

**Task 2.11: Database Tool**
- [ ] Created `/docs/wiki/mcp_tools/database.md`
- [ ] Documents db_query tool with parameters table
- [ ] Clearly notes read-only (SELECT only) constraint

**Phase 2 Complete:**
- [ ] All 11 files exist
- [ ] All 85+ tools documented with parameters tables
- [ ] Every tool has: description, parameters (with types/defaults), returns, example

---
## Phase 3: Plugin Manager Documentation
<!-- ID: phase_3 -->

**Task 3.1: Plugin Manager Index**
- [ ] Created `/docs/wiki/plugin_manager/index.md`
- [ ] Contains system overview
- [ ] Contains component diagram
- [ ] Contains working links to all subsections

**Task 3.2: Workspace Documentation**
- [ ] Created `/docs/wiki/plugin_manager/workspace.md`
- [ ] Documents directory structure (plugins/public, plugins/private, themes/*)
- [ ] Documents PluginWorkspace class methods
- [ ] Documents ThemeWorkspace class methods
- [ ] Documents meta.json schema with all fields
- [ ] Documents workspace validation

**Task 3.3: Deployment Documentation**
- [ ] Created `/docs/wiki/plugin_manager/deployment.md`
- [ ] Documents PluginInstaller class
- [ ] Documents ThemeInstaller class
- [ ] Documents directory overlay system
- [ ] Documents deployment manifest format (JSON structure)
- [ ] Documents backup and restore process

**Task 3.4: Lifecycle Documentation**
- [ ] Created `/docs/wiki/plugin_manager/lifecycle.md`
- [ ] Documents all 7 PHP Bridge actions:
  - [ ] plugin:status
  - [ ] plugin:activate
  - [ ] plugin:deactivate
  - [ ] plugin:list
  - [ ] cache:read
  - [ ] cache:rebuild
  - [ ] info
- [ ] Documents BridgeResult dataclass
- [ ] Documents PluginLifecycle class methods
- [ ] Documents activate_full workflow
- [ ] Documents deactivate_full workflow

**Task 3.5: Database Documentation**
- [ ] Created `/docs/wiki/plugin_manager/database.md`
- [ ] Documents SQLite schema (projects table)
- [ ] Documents SQLite schema (history table)
- [ ] Documents ProjectDatabase class methods
- [ ] Documents deployment manifest storage
- [ ] Documents query methods

**Phase 3 Complete:**
- [ ] All 5 files exist
- [ ] PHP Bridge fully covered with all 7 actions
- [ ] Database schema complete with SQL

---
## Phase 4: Architecture Documentation
<!-- ID: phase_4 -->

**Task 4.1: Architecture Index**
- [ ] Created `/docs/wiki/architecture/index.md`
- [ ] Contains system overview diagram
- [ ] Contains component relationships
- [ ] Contains working links to detailed pages

**Task 4.2: MCP Server Architecture**
- [ ] Created `/docs/wiki/architecture/mcp_server.md`
- [ ] Documents server initialization
- [ ] Documents tool registration
- [ ] Documents database connection management
- [ ] Documents connection pooling strategy

**Task 4.3: Disk Sync Architecture**
- [ ] Created `/docs/wiki/architecture/disk_sync.md`
- [ ] Documents DiskSyncService orchestrator
- [ ] Documents FileWatcher implementation
- [ ] Documents template import/export workflow
- [ ] Documents stylesheet import/export workflow
- [ ] Documents race condition prevention

**Task 4.4: Configuration Documentation**
- [ ] Created `/docs/wiki/architecture/configuration.md`
- [ ] Documents all MCP server environment variables
- [ ] Documents Plugin Manager configuration
- [ ] Documents Sync configuration
- [ ] Documents configuration loading process

**Phase 4 Complete:**
- [ ] All 4 files exist
- [ ] All system components documented
- [ ] Configuration fully covered

---
## Phase 5: Best Practices Documentation
<!-- ID: phase_5 -->

**Task 5.1: Best Practices Index**
- [ ] Created `/docs/wiki/best_practices/index.md`
- [ ] Contains overview of best practices
- [ ] Contains working links to all guides

**Task 5.2: Plugin Development Guide**
- [ ] Created `/docs/wiki/best_practices/plugin_development.md`
- [ ] Documents plugin structure (_info, _activate, _deactivate, _install, _uninstall)
- [ ] Documents hook usage patterns
- [ ] Documents settings management
- [ ] Documents template management
- [ ] Documents database operations

**Task 5.3: Theme Development Guide**
- [ ] Created `/docs/wiki/best_practices/theme_development.md`
- [ ] Documents theme structure
- [ ] Documents stylesheet inheritance
- [ ] Documents template overrides
- [ ] Documents theme packaging

**Task 5.4: Security Guide**
- [ ] Created `/docs/wiki/best_practices/security.md`
- [ ] Documents input validation
- [ ] Documents CSRF protection
- [ ] Documents SQL injection prevention
- [ ] Documents sensitive data handling

**Phase 5 Complete:**
- [ ] All 4 files exist
- [ ] All best practices documented
- [ ] Security considerations covered

---
## Phase 6: CLAUDE.md Update
<!-- ID: phase_6 -->

**Task 6.1: Update CLAUDE.md**
- [ ] Added "Documentation Reference" section to CLAUDE.md
- [ ] Section contains table with links to all 5 wiki sections
- [ ] All links use correct relative paths
- [ ] Section integrates naturally with existing document structure

**Phase 6 Complete:**
- [ ] CLAUDE.md updated
- [ ] All wiki links resolve correctly
<!-- ID: final_verification -->
---
## Final Verification
<!-- ID: final_verification -->

**Documentation Completeness:**
- [ ] All 26 wiki documents created (see milestone tracking in PHASE_PLAN.md)
- [ ] CLAUDE.md updated with documentation reference section
- [ ] No placeholder content in any document
- [ ] All internal links verified and working

**Quality Assurance:**
- [ ] All MCP tool parameters verified against server.py source
- [ ] All Plugin Manager methods verified against implementation
- [ ] All PHP Bridge actions verified against mcp_bridge.php
- [ ] Code examples are accurate and tested where possible

**Final Sign-off:**
- [ ] Review Agent has validated documentation accuracy
- [ ] All checklist items checked with evidence
- [ ] Documentation is ready for developer use

---
## Evidence Tracking
<!-- ID: evidence_tracking -->

| Document | Created | Verified | Evidence |
|----------|---------|----------|----------|
| /docs/wiki/index.md | [ ] | [ ] | - |
| /docs/wiki/getting_started/index.md | [ ] | [ ] | - |
| /docs/wiki/getting_started/installation.md | [ ] | [ ] | - |
| /docs/wiki/getting_started/quickstart.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/index.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/templates.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/themes_stylesheets.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/plugins.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/forums_threads_posts.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/users_moderation.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/search.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/admin_settings.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/tasks.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/disk_sync.md | [ ] | [ ] | - |
| /docs/wiki/mcp_tools/database.md | [ ] | [ ] | - |
| /docs/wiki/plugin_manager/index.md | [ ] | [ ] | - |
| /docs/wiki/plugin_manager/workspace.md | [ ] | [ ] | - |
| /docs/wiki/plugin_manager/deployment.md | [ ] | [ ] | - |
| /docs/wiki/plugin_manager/lifecycle.md | [ ] | [ ] | - |
| /docs/wiki/plugin_manager/database.md | [ ] | [ ] | - |
| /docs/wiki/architecture/index.md | [ ] | [ ] | - |
| /docs/wiki/architecture/mcp_server.md | [ ] | [ ] | - |
| /docs/wiki/architecture/disk_sync.md | [ ] | [ ] | - |
| /docs/wiki/architecture/configuration.md | [ ] | [ ] | - |
| /docs/wiki/best_practices/index.md | [ ] | [ ] | - |
| /docs/wiki/best_practices/plugin_development.md | [ ] | [ ] | - |
| /docs/wiki/best_practices/theme_development.md | [ ] | [ ] | - |
| /docs/wiki/best_practices/security.md | [ ] | [ ] | - |
| CLAUDE.md (updated) | [ ] | [ ] | - |
