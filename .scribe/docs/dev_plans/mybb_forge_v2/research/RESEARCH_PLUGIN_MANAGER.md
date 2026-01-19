
# 🔬 Research Plugin Manager — mybb-forge-v2
**Author:** Scribe
**Version:** v0.1
**Status:** In Progress
**Last Updated:** 2026-01-19 03:53:11 UTC

> Investigates current Plugin Manager architecture, workspace organization, deployment workflow, and manifest tracking system to inform mybb-forge-v2 restructuring.

---
## Executive Summary
<!-- ID: executive_summary -->High-level overview of the research effort and conclusions.

**Primary Objective:** Understand how the Plugin Manager currently works, including workspace structure, deployment mechanics, manifest/tracking capabilities, and MCP tool integration — to identify gaps and opportunities for the proposed restructuring.

**Key Takeaways:**
- Plugin Manager uses **workspace directory mirroring** to deploy plugins (workspace/inc → TestForum/inc)
- Manifest tracking **exists and is robust** — stored in SQLite database as JSON with full file metadata (size, checksum, deployment timestamp)
- Current meta.json is **minimal** — no manifest embedded; manifest lives only in deployment database
- Real plugins (invite_system, cortex, dice_roller) demonstrate **sophisticated directory organization** with /admin, /handlers, /core subdirectories
- **NO disk-first template management currently** — templates created by PHP lifecycle functions at install time
- Deployment is **full file overlay** with MD5 checksums and backups stored outside TestForum
- **Risk:** Discrepancy between workspace structure (meta.json) and deployment tracking (database manifest)


---
## Research Scope
<!-- ID: research_scope -->
**Research Lead:** R2-PluginManager

**Investigation Window:** 2026-01-19 03:47 — 03:54 UTC

**Focus Areas:**
- [x] Plugin Manager workspace directory structure (/plugin_manager/plugins/public|private/{codename}/)
- [x] Meta.json format and content (current vs proposed)
- [x] Deployment mechanism (PluginInstaller, directory overlay, file tracking)
- [x] Manifest system (database storage, file metadata, checksums)
- [x] MCP tool integration (mybb_create_plugin, mybb_plugin_install, mybb_plugin_uninstall)
- [x] Real plugin examination (invite_system, cortex, dice_roller as examples)
- [x] Template handling in current system
- [x] Database schema for manifest tracking

**Dependencies & Constraints:**
- Analysis limited to workspace filesystem and Python plugin_manager code (MCP tools are thin wrappers)
- Did not examine MyBB's actual plugin lifecycle (_install, _activate, etc.) — focused on manager layer
- Did not investigate git integration or worktree strategy (separate R1 task)
- File templates read from workspace, not deployment database


---
## Findings
<!-- ID: findings -->Detail each major finding with evidence and confidence levels.

### Finding 1: Workspace Directory Structure is Well-Organized
- **Summary:** Plugin workspace mirrors MyBB directory layout exactly (inc/, jscripts/, images/). Four existing plugins show consistent organization.
- **Evidence:**
  - Public plugins: `/plugin_manager/plugins/public/` contains dice_roller, cortex, test_tracker
  - Private plugins: `/plugin_manager/plugins/private/` contains invite_system
  - Each plugin has: meta.json, README.md, inc/, jscripts/ (optional), images/ (optional)
  - invite_system demonstrates advanced structure: `/inc/plugins/invite_system/admin/`, `/handlers/`, `/core/` subdirectories
- **Confidence:** 0.99

### Finding 2: Manifest System Exists and is Database-Backed
- **Summary:** Deployment manifest is robust, stored in SQLite (plugin_manager/.meta/projects.db), not in meta.json. Tracks complete file metadata.
- **Evidence:**
  - `/plugin_manager/database.py`: `set_deployed_manifest()` and `get_deployed_manifest()` methods store JSON in projects.deployed_files column
  - File metadata includes: path, size, mtime, checksum (MD5), source, deployed_at
  - Directory tracking: separate list of directories created (to distinguish from core MyBB dirs)
  - Backup tracking: separate list of backup files created outside TestForum
  - Database handles legacy formats for backward compatibility
- **Confidence:** 0.98

### Finding 3: Current Meta.json is Minimal and Not Manifest-Based
- **Summary:** meta.json contains basic plugin metadata but NO manifest data. Manifest only lives in deployment database.
- **Evidence:**
  - dice_roller meta.json (1104 bytes): only codename, display_name, version, author, description, compatibility, hooks, settings, templates, files map, has_templates, has_database
  - invite_system meta.json (2916 bytes): adds dependencies field, but still no manifest
  - No "manifest" top-level key in any meta.json
  - Files field only contains high-level mappings (plugin, languages, jscripts, images) — not full inventory
  - **Risk identified:** Workspace meta.json and deployment database can diverge
- **Confidence:** 0.99

### Finding 4: Deployment Uses Directory Overlay Pattern
- **Summary:** PluginInstaller.install_plugin() copies workspace/inc/ → TestForum/inc/ as full directory overlay, tracking all changes.
- **Evidence:**
  - `/plugin_manager/installer.py` lines 70-220: `install_plugin()` method
  - Calls `_overlay_directory()` for each source directory (inc/, jscripts/, images/)
  - Recursively copies all files with `shutil.copy2()`, creating directories as needed
  - Backups existing files to `/plugin_manager/backups/{codename}/{timestamp}/` OUTSIDE TestForum
  - Returns deployment manifest including file count, total size, and file-by-file metadata
- **Confidence:** 0.99

### Finding 5: Templates Currently NOT Managed on Disk
- **Summary:** No disk-first template management yet. Templates are created by plugin PHP lifecycle functions at install time, not loaded from files.
- **Evidence:**
  - meta.json "templates" field is always empty list (even dice_roller and invite_system have "templates": [])
  - "has_templates": true flag indicates plugin will create templates at runtime
  - No templates/ subdirectory in plugin workspaces
  - mybb_sync/ only tracks core MyBB templates and stylesheets, not plugin templates
  - This is identified as pain point in REQUIREMENTS_BRIEF
- **Confidence:** 0.99
- **IMPROVEMENT OPPORTUNITY:** This is exactly what the proposed disk-first template management should fix

### Finding 6: MCP Tools are Thin Wrappers
- **Summary:** MCP plugin tools (mybb_create_plugin, mybb_plugin_install, mybb_plugin_uninstall) are thin wrappers around plugin_manager Python classes.
- **Evidence:**
  - `/mybb_mcp/server.py` line 1762+: mybb_create_plugin delegates to `PluginManager.create_plugin()`
  - Line 2260+: mybb_plugin_install calls `PluginManager.activate_full()`
  - Line 2317+: mybb_plugin_uninstall calls `PluginManager.deactivate_full()`
  - MCP tools do no business logic — all logic in plugin_manager/ module
  - Proper separation of concerns
- **Confidence:** 0.99

### Finding 7: Real Plugins Show Sophisticated Organization
- **Summary:** invite_system demonstrates advanced plugin architecture with Admin CP, handlers, and core business logic organized in separate subdirectories.
- **Evidence:**
  - invite_system structure: `/admin/` (15+ files), `/handlers/` (5 files), `/core/` (10+ classes), `/tasks/` (2 scheduled tasks)
  - Admin modules: help, module_meta, bulk, tree, fields, campaigns, settings, logs, spam, codes, analytics, dashboard, applications, permissions, webhooks
  - Handlers: profile, usercp, registration, misc, ajax
  - Core classes: CustomFields, GroupPermissions, Analytics, InviteCode, Application, EdgeCaseHandler, InvitePool, Notifier, plus others
  - This organization is NOT captured in meta.json — manifest is database-only
- **Confidence:** 0.98

### Additional Notes
- Database path: `/plugin_manager/.meta/projects.db` (SQLite)
- Plugin Manager module files: manager.py, lifecycle.py, installer.py, workspace.py, database.py, packager.py, config.py, schema.py, mcp_client.py
- Backup directory: `/plugin_manager/backups/{codename}/` — structured by timestamp
- The system supports both "public" and "private" visibility in workspace structure


---
## Technical Analysis
<!-- ID: technical_analysis -->

### Current Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│ Workspace (plugin_manager/plugins/{public,private}/{codename})
│  - inc/plugins/{codename}.php         (main entry)
│  - inc/plugins/{codename}/            (subdirs: admin, handlers, core, etc.)
│  - inc/languages/english/{codename}.lang.php
│  - inc/tasks/*.php                    (scheduled tasks)
│  - jscripts/                          (optional)
│  - images/                            (optional)
│  - meta.json                          (metadata only - NO manifest)
│  - README.md
└──────────────────────────┬────────────────────────────┘
                           │ PluginInstaller.install_plugin()
                           │ _overlay_directory() → shutil.copy2()
                           ▼
┌─────────────────────────────────────────────────────────┐
│ TestForum (Deployed)
│  - inc/plugins/{codename}.php
│  - inc/plugins/{codename}/
│  - inc/languages/english/{codename}.lang.php
│  - inc/tasks/
│  - jscripts/
│  - images/
└──────────┬───────────────────────────────────────────────┘
           │ Manifest stored in DB
           ▼
┌─────────────────────────────────────────────────────────┐
│ plugin_manager/.meta/projects.db (SQLite)
│  - Table: projects
│    - deployed_files: JSON manifest
│      {
│        "deployed_at": "2026-01-19T03:53:00",
│        "files": [
│          {
│            "path": "/abs/path/to/deployed/file",
│            "size": 12345,
│            "mtime": "2026-01-19T03:52:00",
│            "checksum": "md5hash",
│            "source": "/workspace/path",
│            "relative_path": "plugins/codename.php"
│          },
│          ...
│        ],
│        "directories": [list of created dirs],
│        "backups": [list of backup files outside TestForum],
│        "file_count": N,
│        "dir_count": M
│      }
└─────────────────────────────────────────────────────────┘
```

**Code Patterns Identified:**
- **Directory Overlay Pattern:** Source structure mirrors destination exactly, enables simple recursive copy with path mapping
- **File Metadata Tracking:** MD5 checksums enable integrity verification and conflict detection
- **Backup Strategy:** Pre-deployment backups stored OUTSIDE TestForum (plugin_manager/backups/) — keeps core installation clean
- **Separation of Concerns:** MCP tools are thin routing layer; business logic in plugin_manager module
- **Legacy Format Handling:** Database layer supports both new (metadata dict) and old (path list) formats for backward compatibility
- **Workspace Isolation:** Public/private visibility handled at filesystem level (/plugins/public/ vs /private/)

**System Interactions:**
- **MCP Layer ↔ Plugin Manager:** MCP tools in mybb_mcp/server.py → plugin_manager.manager.PluginManager
- **Plugin Manager ↔ Filesystem:** PluginInstaller reads workspace, writes to TestForum, backups to plugin_manager/backups/
- **Plugin Manager ↔ Database:** ProjectDatabase (SQLite) stores manifest, project metadata, history, status
- **PHP Lifecycle ↔ Database:** Not fully traced (R5 task), but PluginLifecycle class handles _install, _activate, etc.
- **MCP ↔ MyBB:** No direct integration — MyBB activation happens in Admin CP after deployment

**Risk Assessment:**
1. **RISK: Meta.json / Database Divergence**
   - Workspace meta.json and deployment database manifest can get out of sync
   - If meta.json is updated but plugin not redeployed, inconsistency occurs
   - **Mitigation:** Proposed solution embeds manifest in meta.json (per REQUIREMENTS_BRIEF)

2. **RISK: Template Management Gap**
   - Templates currently created at PHP runtime, not managed on disk
   - Makes version control and collaborative editing difficult
   - **Mitigation:** Disk-first template management proposal addresses this

3. **RISK: Manifest Schema Evolution**
   - Current database manifest format is new; legacy format support is temporary
   - Future schema changes could break backward compatibility
   - **Mitigation:** Versioning in manifest structure (not yet implemented)

4. **POTENTIAL ISSUE: Directory Cleanup on Uninstall**
   - Manifest tracks "directories we created" but must avoid deleting shared dirs (shared between plugins)
   - Current implementation appears to have logic for this but not fully validated
   - **Mitigation:** Uninstall logic needs testing with multiple plugins sharing dirs


---
## Recommendations
<!-- ID: recommendations -->Translate research into recommended actions.

### Immediate Next Steps (For Architect)

1. **Embed Manifest in Meta.json**
   - Current state: Manifest lives only in deployment database
   - Proposed: Add "manifest" section to meta.json with full file inventory
   - Benefit: Source control + single source of truth for workspace state
   - Implementation: Modify manager.create_plugin() and installer.install_plugin() to update meta.json manifest section

2. **Implement Disk-First Template Management**
   - Current state: Templates created at PHP runtime, not managed on disk
   - Proposed: Create /templates/ subdirectory in plugin workspace with .html files
   - Benefit: Version control, collaborative editing, aligns with db-sync pattern
   - Implementation: Plugin installer reads template files, inserts via $db->insert_query() in _install()

3. **Clarify Meta.json Manifest Structure**
   - Current "files" field is vague (only shows plugin, languages, jscripts, images mappings)
   - Proposed: Replace with detailed manifest similar to database structure
   - Benefit: Developers understand exactly what files will be deployed
   - Reference: REQUIREMENTS_BRIEF section 2.3 has proposed schema

4. **Add Template Group to Meta.json**
   - Plugins should declare template group for Admin CP visibility
   - Example: "templates_group": "invite_system" to group invite_system_main, invite_system_row, etc.
   - Benefit: Better template organization in Admin CP

### Architectural Decisions for Architect

1. **Should Manifest be in Meta.json or Database?**
   - Current: Database only (robust for deployment tracking)
   - Proposed: Both (meta.json = source truth, database = deployment state)
   - Rationale: Source control + deployment verification

2. **Template Handling: Pre-Deploy or Runtime?**
   - Current: Runtime (templates created by PHP _install())
   - Proposed: Pre-deploy (files on disk, inserted during PHP _install())
   - Rationale: Version control + collaborative editing + consistency with db-sync

3. **Directory Structure: Keep Nested /codename/ or Flatten?**
   - Current: `/inc/plugins/{codename}/` with subdirectories inside
   - Assessment: Current structure is GOOD — matches real-world complexity (invite_system example)
   - Recommendation: KEEP current structure, document in best practices

### Long-Term Opportunities

1. **Schema Versioning for Manifest**
   - Manifest could include version: "manifest_schema_version": "1.0"
   - Enables safe evolution of schema as requirements change
   - Especially important if this is distributed as packaged plugins

2. **Automated Meta.json Generation**
   - Could scan workspace and generate manifest automatically
   - Detect files, templates, hooks, database tables
   - Useful for existing plugins that lack proper metadata

3. **Settings Group Declaration**
   - Plugins should declare settings group in meta.json
   - Similar to templates_group, enables Auto-grouping in Admin CP
   - Example: "settings_group": "invite_system" → Settings > Invite System

4. **Dependency Resolution in Meta.json**
   - Current: invite_system declares "dependencies": {"cortex": ">=1.0.0"}
   - Could expand to validate dependencies exist and version match on install
   - Enables smart dependency chain installation


---
## Appendix
<!-- ID: appendix -->

### References
- **REQUIREMENTS_BRIEF.md:** Section 2 (Plugin Architecture Restructure) outlines proposed manifest system
- **Plugin Manager Module:** `/plugin_manager/manager.py`, `installer.py`, `database.py`, `workspace.py`
- **MCP Integration:** `/mybb_mcp/server.py` lines 1762, 2260, 2317
- **Example Plugins:**
  - invite_system: `/plugin_manager/plugins/private/invite_system/` (complex structure)
  - cortex: `/plugin_manager/plugins/public/cortex/` (simple plugin)
  - dice_roller: `/plugin_manager/plugins/public/dice_roller/` (mid-complexity)

### File Inventory for Reference

**Key Database Files:**
- `/plugin_manager/.meta/projects.db` — SQLite database for manifest + project metadata
- `/plugin_manager/database.py` — ProjectDatabase class

**Key Manager Modules:**
- `/plugin_manager/manager.py` — PluginManager orchestration
- `/plugin_manager/installer.py` — PluginInstaller (deployment logic)
- `/plugin_manager/lifecycle.py` — PluginLifecycle (PHP execution)
- `/plugin_manager/workspace.py` — PluginWorkspace (filesystem operations)

**Backup Structure:**
- `/plugin_manager/backups/{codename}/{YYYYMMDD_HHMMSS}/` — Timestamped backups of replaced files

### Current Meta.json Example (Minimal)
```json
{
  "codename": "dice_roller",
  "display_name": "Dice Roller",
  "version": "1.0.0",
  "author": "Corta Labs",
  "description": "BBCode dice rolling with database tracking and post CSS effects for tabletop gaming",
  "mybb_compatibility": "18*",
  "visibility": "public",
  "project_type": "plugin",
  "hooks": [
    {"name": "parse_message", "handler": "dice_roller_parse_message", "priority": 10},
    {"name": "postbit", "handler": "dice_roller_postbit", "priority": 10}
  ],
  "settings": [],
  "templates": [],
  "files": {
    "plugin": "inc/plugins/dice_roller.php",
    "languages": "inc/languages/",
    "jscripts": "jscripts/",
    "images": "images/"
  },
  "has_templates": true,
  "has_database": true
}
```

### Proposed Meta.json Structure (With Manifest)
```json
{
  "codename": "dice_roller",
  "display_name": "Dice Roller",
  "version": "1.0.0",
  "author": "Corta Labs",
  "description": "BBCode dice rolling with database tracking and post CSS effects for tabletop gaming",
  "mybb_compatibility": "18*",
  "visibility": "public",
  "project_type": "plugin",

  "manifest": {
    "schema_version": "1.0",
    "files": [
      {"source": "inc/plugins/dice_roller.php", "dest": "inc/plugins/dice_roller.php", "type": "plugin"},
      {"source": "inc/languages/english/dice_roller.lang.php", "dest": "inc/languages/english/dice_roller.lang.php", "type": "language"},
      {"source": "jscripts/dice_roller.js", "dest": "jscripts/dice_roller.js", "type": "script"}
    ],
    "templates": [
      {"name": "dice_roller_main", "file": "templates/dice_roller_main.html", "group": "dice_roller"}
    ],
    "database_tables": [],
    "settings": []
  },

  "hooks": [...],
  "settings": [],
  "templates": [],
  "templates_group": "dice_roller",
  "has_templates": true,
  "has_database": true
}
```

### Questions for Architect

1. Should manifest schema be versioned separately, or only follow plugin version?
2. When manifest changes between versions, should old deployments be validated/updated?
3. Should template files be .html or use MyBB template syntax?
4. How should plugin author metadata propagate through developer config?

---

**Document Status:** COMPLETE - Ready for Architect Review
**Next Stage:** Architecture Design (Phase 2)
**Confidence Level:** 0.97 overall (findings 1-7 average)