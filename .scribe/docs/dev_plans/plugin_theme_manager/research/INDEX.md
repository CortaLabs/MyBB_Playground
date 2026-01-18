# Plugin Manager Research Documentation Index

## Research Documents

### 0. RESEARCH_PLUGIN_ACTIVATION_20260118_0727.md
**Status**: Complete (Latest)
**Date**: 2026-01-18 07:27 UTC
**Scope**: MyBB plugin activation flow, MCP tool capabilities, lifecycle functions, safety considerations

Deep analysis of how MyBB activates plugins through the Admin CP, including 2-stage activation flow, plugin lifecycle functions, and limitations of existing MCP tools for full plugin management.

**Key Findings**:
- Activation is 2-stage: _install() (if new) then _activate()
- Existing MCP activate/deactivate tools are cache-only (do NOT execute PHP functions)
- Full plugin activation requires PHP execution through MyBB infrastructure
- Database table creation NOT available via read-only db_query MCP tool
- Current MCP tools support templates and settings management

**Sections**:
- Executive Summary
- MyBB Plugin Activation Flow (Admin CP analysis)
- Plugin Lifecycle Functions (_info, _is_installed, _install, _activate, _deactivate, _uninstall)
- Existing MCP Tools Audit (9 template, 4 settings, 4 cache, 1 database, 7 plugin tools)
- Plugin Activation Requirements Summary
- Safety Considerations & Backup/Snapshot Approach
- Architectural Handoff Notes
- Confidence Assessment

**For Architect**: Essential for Phase 7 design - reveals cache-only limitation and PHP execution requirement

---

### 1. RESEARCH_WORKFLOW_MAPPING_20260118.md
**Status**: Complete
**Date**: 2026-01-18
**Scope**: Complete workflow composition analysis

Maps all 5 plugin manager workflows (Create, Install, Sync, Export, Import) to existing MCP tools and identifies capability gaps.

**Key Findings**:
- Spec claim "No new MCP tools needed" is technically correct but incomplete
- Orchestration layer required for file operations, ZIP handling, metadata management
- 4 CRITICAL gaps prevent direct MCP implementation
- Feasibility: HIGH with hybrid Python/MCP approach

**Sections**:
- Executive Summary
- Workflow Analysis (1-5 with tool mapping)
- Tool Inventory (60+ tools)
- Missing Capabilities
- Architecture Implications
- Gap Summary by Severity
- Recommendations
- Verification References

**For Architect**: Start here to understand tool capabilities and constraints

---

### 2. RESEARCH_SYNC_SYSTEM_INTEGRATION_20260117_0347.md
**Status**: Complete (Previous Investigation)
**Date**: 2026-01-17
**Scope**: Disk sync service analysis

Analyzes existing FileWatcher and DiskSyncService infrastructure for template/stylesheet synchronization.

**Relevant Findings**:
- FileWatcher exists but watches `mybb_sync/` (templates/stylesheets), not plugin source
- Different scope from plugin sync requirements
- Watcher infrastructure could be extended for plugins

---

## Key Takeaways for Implementation

### Reusable Tools
- `mybb_create_plugin` — PHP scaffolding
- `mybb_analyze_plugin` — Hook/setting extraction
- `mybb_template_batch_write` — Template deployment
- `mybb_plugin_activate` — Cache management
- `mybb_hooks_discover` — Hook discovery

### Blocked Operations
- File copy/move (needs hybrid approach)
- ZIP creation/extraction (needs hybrid approach)
- Database write to projects.db (needs new access pattern)
- Metadata generation (needs orchestration)

### Implementation Path
1. Design orchestration layer (Python skill or CLI)
2. Implement projects.db schema
3. Create meta.json definition
4. Compose workflows using existing tools + file operations
5. Document constraints and error handling

---

## Research Quality Metrics

| Metric | Value |
|--------|-------|
| Research Documents | 7 |
| Workflows Analyzed | 5 |
| Tools Verified | 70+ |
| Confidence (avg) | 0.90 |
| Critical Gaps Found | 5 |
| Source Code References | 20+ |
| Log Entries | 30+ |
| **Latest Focus** | Plugin Activation Flow (2026-01-18) |

