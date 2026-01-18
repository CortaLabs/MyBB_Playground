# 🔬 Research: VSCode MyBBBridge Extension Audit — mybb-ecosystem-audit
**Author:** ResearchAgent_EcosystemAudit
**Version:** v1.0
**Status:** Complete
**Last Updated:** 2026-01-17 14:06 UTC

> Comprehensive audit of the VSCode MyBBBridge extension including all features, workflows, database operations, and comparison with MCP implementation to identify gaps and integration opportunities.

---
## Executive Summary
<!-- ID: executive_summary -->

**Primary Objective:** Comprehensively audit the existing VSCode MyBBBridge extension to understand all features, workflows, and capabilities, then compare against the MCP implementation to identify gaps, redundancies, and integration opportunities.

**Key Takeaways:**
- VSCode extension provides sophisticated auto-upload workflow with file-based template/stylesheet editing organized into hierarchical folder structures
- Extension implements master template inheritance detection (sid=-2) and automatic custom template creation
- Dual template grouping system: static templatecontext.json (1568 lines, 52KB) + SQL CASE statement heuristics for comprehensive categorization
- HTTP-based cache refresh mechanism via cachecss.php and cacheform.php endpoints (requires PHP files deployed to MyBB root)
- MCP has feature parity in most areas but implements sync differently (file watcher vs VSCode save events)
- **CRITICAL GAP**: VSCode extension has HTTP logging to log.php endpoint - not present in MCP
- **INTEGRATION OPPORTUNITY**: Both systems could coexist - MCP for Claude/AI workflows, VSCode for human developer UX


---
## Research Scope
<!-- ID: research_scope -->

**Research Lead:** ResearchAgent_EcosystemAudit

**Investigation Window:** 2026-01-17 (single-day comprehensive audit)

**Focus Areas:**
- ✅ VSCode extension command set and user workflows
- ✅ Template editing and organization system
- ✅ Stylesheet editing and cache management
- ✅ Database connection handling and operations
- ✅ Master template inheritance logic
- ✅ Auto-upload on save mechanism
- ✅ Configuration system and requirements
- ✅ Comparison with MCP tool capabilities
- ✅ Integration opportunities identification

**Dependencies & Constraints:**
- VSCode extension requires cachecss.php and cacheform.php deployed to MyBB root directory
- Extension uses .vscode/mbbb.json for configuration (workspace-scoped)
- MCP uses environment variables for configuration (system-scoped)
- Both systems require direct MySQL database access
- Read-only audit - no modifications to either codebase

---
## Findings
<!-- ID: findings -->

### Finding 1: VSCode Extension Architecture
**File:** `vscode-mybbbridge/src/extension.ts`
**Lines:** 15-82 (activate function)

- **Summary:** Extension provides 4 main commands plus auto-save event handler
- **Evidence:**
  - Commands: `extension.createConfig`, `extension.loadTemplateSet`, `extension.loadStyle`, `mybbbridge.logSampleMessage`
  - Event handler: `vscode.workspace.onDidSaveTextDocument` → `onSaveEvent` function
  - Output channel logging with timestamp prefix
  - Override pattern for logging functions to route to both file and Output Channel
- **Confidence:** HIGH (1.0)

### Finding 2: Auto-Upload Workflow
**File:** `vscode-mybbbridge/src/events.ts`
**Lines:** 12-69 (onSaveEvent function)

- **Summary:** Automatic database sync on file save based on path pattern detection
- **Evidence:**
  - Path pattern: `template_sets/{templateset}/{group}/{template}.html` → routes to MyBBTemplateSet.saveElement()
  - Path pattern: `styles/{theme}/{stylesheet}.css` → routes to MyBBStyle.saveElement()
  - Requires `autoUpload: true` in config
  - Parses path components to extract template set name, group name, theme name
  - Error handling with user notifications
- **Confidence:** HIGH (0.95)

### Finding 3: Template Grouping System (Dual-Source)
**Files:**
- `vscode-mybbbridge/src/loadCommands.ts` (lines 33-138)
- `vscode-mybbbridge/resources/templatecontext.json` (1568 lines)
- `vscode-mybbbridge/src/TemplateGroupManager.ts` (lines 215-259)

- **Summary:** Sophisticated dual-source template grouping with static mapping + SQL heuristics + language string resolution
- **Evidence:**
  - **Primary source:** `templatecontext.json` - 1568-line static mapping of template names to groups
  - **Fallback source:** SQL query with CASE statement for prefix-based categorization (global_, header_, footer_, usercp_, etc.)
  - **Language resolution:** `TemplateGroupManager.langMap` maps `<lang:group_*>` strings to human-readable names (33+ groups)
  - **File sanitization:** `sanitizeGroupName()` removes invalid filesystem characters
  - Handles ungrouped templates gracefully
- **Confidence:** HIGH (0.9)

### Finding 4: Master Template Inheritance Logic
**File:** `vscode-mybbbridge/src/MyBBThemes.ts`
**Lines:** 196-255 (MyBBTemplateSet.saveElement)

- **Summary:** Intelligent handling of master vs custom templates with automatic inheritance management
- **Evidence:**
  - Checks for master template (sid=-2) first
  - Checks for existing custom template (sid=template_set_sid)
  - If master exists + no custom: creates new custom version (INSERT)
  - If master exists + custom exists: updates custom version (UPDATE)
  - If no master + custom exists: updates custom template
  - If no master + no custom: creates new custom template
  - Updates dateline and version fields
  - User feedback via vscode.window.showInformationMessage
- **Confidence:** HIGH (0.95)

### Finding 5: Cache Refresh Mechanisms (Dual Implementation)
**Files:**
- `vscode-mybbbridge/src/MyBBThemes.ts` (lines 348-399)
- `vscode-mybbbridge/cacheStylesheet.js` (entire file)

- **Summary:** Two separate cache refresh implementations - TypeScript HTTP POST and standalone Node.js script
- **Evidence:**
  - **TypeScript implementation:** `MyBBStyle.requestCacheRefresh()` POSTs to `cachecss.php` with form data (theme_name, stylesheet, optional token)
  - **Node.js script:** `cacheStylesheet.js` uses axios to POST to `cacheform.php?action=csscacheclear`
  - Both extract theme/stylesheet names from file paths
  - TypeScript version expects JSON response with {success, message}
  - Node.js version appears to be alternative/backup mechanism
  - **DEPENDENCY:** Requires cachecss.php and cacheform.php uploaded to MyBB root directory
- **Confidence:** MEDIUM (0.85) - unclear why two mechanisms exist

### Finding 6: Configuration System
**File:** `vscode-mybbbridge/src/utils.ts`
**Lines:** 67-88 (getConfig function)

- **Summary:** Workspace-scoped JSON configuration with database credentials and feature flags
- **Evidence:**
  - Config file location: `.vscode/mbbb.json`
  - Required fields: `database {host, port, database, user, password, prefix}`
  - Optional fields: `mybbVersion`, `mybbUrl`, `autoUpload`, `logFilePath`, `token`
  - No environment variable support
  - No encryption for credentials (stored in plain text)
  - Command to create config: `extension.createConfig`
- **Confidence:** HIGH (1.0)

### Finding 7: Database Connection Management
**File:** `vscode-mybbbridge/src/utils.ts`
**Lines:** 16-49 (getConnexion function)

- **Summary:** Connection-per-operation pattern with retry logic but no connection pooling
- **Evidence:**
  - Creates new mysql2.Connection for each operation
  - Retry logic: MAX_RETRIES=3, RETRY_DELAY_MS=1000
  - Connection health check via con.ping() in MyBBSet.query()
  - Reconnects if connection closed
  - **INEFFICIENCY:** No connection pool reuse
- **Confidence:** HIGH (0.95)

### Finding 8: HTTP Logging to PHP Endpoint
**File:** `vscode-mybbbridge/src/MyBBThemes.ts`
**Lines:** 57-81 (logToPHP function)

- **Summary:** Extension logs operations to MyBB via HTTP POST to log.php endpoint
- **Evidence:**
  - Endpoint: `{mybbUrl}/log.php`
  - Form data: `{message, token (optional)}`
  - Uses request-promise-native library
  - Logs to local file as backup via logToFile()
  - **PURPOSE:** Provides audit trail visible in MyBB admin panel
  - **MCP GAP:** MCP has no equivalent HTTP logging functionality
- **Confidence:** HIGH (1.0)

---
## Technical Analysis
<!-- ID: technical_analysis -->

### Code Patterns Identified

**Positive Patterns:**
1. **Dual-source template grouping** - Comprehensive coverage with static mapping + SQL fallback
2. **Master template inheritance** - Proper sid=-2 detection and custom template creation
3. **Retry logic** - Database connection failures handled gracefully
4. **User feedback** - Consistent use of vscode.window.showInformationMessage for operation results
5. **Language string resolution** - langMap for human-readable group names
6. **Path-based routing** - Elegant file path parsing to determine operation type

**Anti-Patterns:**
1. **No connection pooling** - Creates new connection per operation (performance issue)
2. **Plain text credentials** - mbbb.json stores database password unencrypted
3. **Dual cache mechanisms** - Unclear why both TypeScript and Node.js cache refresh exist
4. **Logging function override** - Uses `(logToPHP as any) = function...` to patch functions (fragile pattern)

### System Interactions

**Database:**
- Direct MySQL queries via mysql2 library
- Tables accessed: `templates`, `templatesets`, `templategroups`, `themes`, `themestylesheets`
- Special SID values: -2 (master templates), -1 (global templates)

**HTTP Endpoints Required:**
- `{mybbUrl}/cachecss.php` - Cache refresh for stylesheets (expects JSON response)
- `{mybbUrl}/cacheform.php?action=csscacheclear` - Alternative cache refresh endpoint
- `{mybbUrl}/log.php` - Operation logging endpoint

**File System:**
- Workspace folder structure:
  - `template_sets/{templateset}/{group}/{template}.html`
  - `styles/{theme}/{stylesheet}.css`
- Configuration: `.vscode/mbbb.json`
- Logs: configurable via `logFilePath`

### Risk Assessment

**Security Risks:**
- ⚠️ **HIGH:** Plain text database credentials in `.vscode/mbbb.json`
- ⚠️ **MEDIUM:** Optional authentication token for HTTP endpoints (token field) - unclear if enforced
- ⚠️ **MEDIUM:** SQL injection risk - some queries use string concatenation for table names (prefix + table)

**Performance Risks:**
- ⚠️ **MEDIUM:** No connection pooling - each save creates new database connection
- ⚠️ **LOW:** Large templatecontext.json (52KB) loaded on every template set load

**Reliability Risks:**
- ⚠️ **MEDIUM:** Dependency on external PHP files (cachecss.php, cacheform.php, log.php)
- ⚠️ **LOW:** File path parsing assumes specific folder structure (fragile if user changes structure)

---
## Feature Comparison: VSCode Extension vs MCP

| Feature | VSCode Extension | MCP | Notes |
|---------|-----------------|-----|-------|
| **List template sets** | ✅ Via loadTemplateSet command | ✅ mybb_list_template_sets | Both query templatesets table |
| **List templates** | ✅ Via getElements() | ✅ mybb_list_templates | Both support filtering by set |
| **Read template** | ✅ Loads to file | ✅ mybb_read_template | VSCode creates files, MCP returns content |
| **Write template** | ✅ Auto-save or manual | ✅ mybb_write_template | VSCode auto-uploads, MCP manual |
| **Template grouping** | ✅ Dual-source (JSON + SQL) | ✅ mybb_list_template_groups | VSCode more sophisticated |
| **Master template handling** | ✅ Automatic sid=-2 detection | ✅ Shows master + custom | Both handle inheritance |
| **List themes** | ✅ Via loadStyle command | ✅ mybb_list_themes | Feature parity |
| **List stylesheets** | ✅ Via getElements() | ✅ mybb_list_stylesheets | Feature parity |
| **Read stylesheet** | ✅ Loads to file | ✅ mybb_read_stylesheet | VSCode creates files, MCP returns content |
| **Write stylesheet** | ✅ Auto-save + cache refresh | ✅ mybb_write_stylesheet | VSCode includes cache refresh |
| **Cache refresh** | ✅ HTTP POST to cachecss.php | ❌ **MISSING** | **GAP**: MCP has no cache refresh |
| **Auto-sync on save** | ✅ onDidSaveTextDocument event | ✅ File watcher (sync module) | Different implementations |
| **HTTP logging** | ✅ logToPHP to log.php | ❌ **MISSING** | **GAP**: MCP has no HTTP logging |
| **Plugin management** | ❌ **MISSING** | ✅ list/read/create/analyze | **GAP**: VSCode has no plugin tools |
| **Hooks reference** | ❌ **MISSING** | ✅ mybb_list_hooks | **GAP**: VSCode has no hooks tool |
| **Database queries** | ❌ **MISSING** | ✅ mybb_db_query | **GAP**: VSCode has no ad-hoc query tool |
| **Config system** | .vscode/mbbb.json | Environment variables | Different scopes |
| **Connection management** | Per-operation | Connection pool | MCP more efficient |

---
## Recommendations
<!-- ID: recommendations -->

### Immediate Next Steps

**For MCP Enhancement:**
1. ✅ **ADD:** Cache refresh tool (`mybb_refresh_stylesheet_cache`) that calls cachecss.php
   - **Why:** VSCode extension proves this is critical for stylesheet development
   - **How:** Implement HTTP POST to cachecss.php endpoint similar to VSCode's requestCacheRefresh
   - **Priority:** HIGH

2. ✅ **ADD:** HTTP logging tool (optional) to integrate with MyBB's log.php
   - **Why:** Provides audit trail visible to MyBB admins
   - **How:** Optional feature flag to enable HTTP logging alongside local logging
   - **Priority:** MEDIUM

3. ✅ **ENHANCE:** Template grouping to include static templatecontext.json mapping
   - **Why:** More accurate grouping than SQL heuristics alone
   - **How:** Include templatecontext.json as resource file, use as primary source
   - **Priority:** MEDIUM

4. ✅ **DOCUMENT:** Deployment requirements for cachecss.php and cacheform.php
   - **Why:** MCP users may need cache refresh capability
   - **How:** Add docs/deployment/ guide with PHP file requirements
   - **Priority:** LOW (only if cache refresh added)

**For VSCode Extension Improvement:**
1. ⚠️ **SECURITY:** Add encryption for database credentials in mbbb.json
   - **Why:** Plain text credentials are security risk
   - **How:** Use VSCode secret storage API
   - **Priority:** HIGH

2. ⚠️ **PERFORMANCE:** Implement connection pooling
   - **Why:** Current per-operation connections inefficient
   - **How:** Use mysql2 pool instead of createConnection
   - **Priority:** MEDIUM

3. ⚠️ **CLEANUP:** Remove duplicate cache refresh mechanisms
   - **Why:** Unclear why both TypeScript and Node.js versions exist
   - **How:** Consolidate to single implementation
   - **Priority:** LOW

### Long-Term Opportunities

**Integration Architecture:**

Both systems can coexist and complement each other:

```
┌─────────────────────────────────────────────────────┐
│                  MyBB Development                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────┐  ┌────────────────────┐  │
│  │  VSCode Extension    │  │   MCP Server       │  │
│  │                      │  │                    │  │
│  │  • Human UX          │  │  • AI/Claude UX    │  │
│  │  • File editing      │  │  • Tool-based      │  │
│  │  • Auto-upload       │  │  • File watching   │  │
│  │  • Visual feedback   │  │  • Programmatic    │  │
│  │  • Workspace config  │  │  • Env config      │  │
│  └──────────┬───────────┘  └─────────┬──────────┘  │
│             │                        │              │
│             └────────┬───────────────┘              │
│                      ▼                              │
│            ┌──────────────────┐                     │
│            │  MyBB Database   │                     │
│            │  • Templates     │                     │
│            │  • Stylesheets   │                     │
│            │  • Themes        │                     │
│            └──────────────────┘                     │
└─────────────────────────────────────────────────────┘
```

**Use Cases:**
- **Human developers:** Use VSCode extension for interactive editing
- **AI agents (Claude):** Use MCP for automated operations
- **Hybrid workflows:** Human starts work in VSCode, Claude enhances via MCP

**Shared Infrastructure Opportunities:**
1. **Shared cache refresh endpoint** - Both could use same cachecss.php
2. **Shared logging endpoint** - MCP could optionally use log.php
3. **Shared template grouping data** - Both could reference same templatecontext.json
4. **Shared PHP deployment** - Single set of PHP files for both systems

---
## Appendix
<!-- ID: appendix -->

### Files Analyzed

**VSCode Extension (vscode-mybbbridge/):**
1. `package.json` - Extension manifest, commands, dependencies
2. `src/extension.ts` - Main entry point, command registration, activation
3. `src/events.ts` - onSaveEvent handler for auto-upload
4. `src/loadCommands.ts` - loadTemplateSet and loadStyle commands
5. `src/MyBBThemes.ts` - MyBBTemplateSet and MyBBStyle classes, database operations
6. `src/utils.ts` - Configuration, database connection, utilities
7. `src/TemplateGroupManager.ts` - Template grouping logic, langMap
8. `resources/templatecontext.json` - Static template-to-group mapping (1568 lines)
9. `cacheStylesheet.js` - Standalone cache refresh script
10. `README.md` - User documentation, features, setup

**MCP Implementation (mybb_mcp/):**
1. `mybb_mcp/server.py` - Tool routing, handle_tool function
2. `mybb_mcp/sync/` - Discovered sync module (watcher, service, templates, stylesheets, cache)

### Confidence Scores Summary

- **Architecture findings:** HIGH (0.95-1.0) - Direct code inspection
- **Workflow findings:** HIGH (0.9-0.95) - Traced execution paths
- **Cache mechanisms:** MEDIUM (0.85) - Dual implementation unclear
- **Feature comparison:** HIGH (0.9) - Both codebases analyzed
- **Integration recommendations:** HIGH (0.9) - Based on verified capabilities

### References

- VSCode extension repository: https://github.com/paxocial/vscode-mybbbridge
- MyBB database schema: Referenced via SQL queries in code
- MCP server tools: Enumerated from server.py handle_tool function

### Handoff Notes for Architect

**Key Decisions Required:**
1. Should MCP implement cache refresh? (Recommendation: YES - critical for stylesheet workflow)
2. Should MCP implement HTTP logging? (Recommendation: OPTIONAL - nice to have)
3. Should systems share infrastructure? (Recommendation: YES - reduce duplication)

**Critical Dependencies:**
- Cache refresh requires cachecss.php deployed to MyBB root
- HTTP logging requires log.php deployed to MyBB root
- Both systems require direct MySQL database access

**Risk Flags:**
- VSCode extension stores plain text credentials - security concern
- No connection pooling in VSCode extension - performance concern
- Dual cache mechanisms in VSCode extension - cleanup needed

---

**Research Complete:** 2026-01-17 14:06 UTC
**Total Files Analyzed:** 11 (10 VSCode + 1 MCP)
**Total Log Entries:** 12
**Overall Confidence:** HIGH (0.9)
