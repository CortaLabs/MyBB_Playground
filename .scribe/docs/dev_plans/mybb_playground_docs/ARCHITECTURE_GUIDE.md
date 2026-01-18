---
id: mybb_playground_docs-architecture
title: "\U0001F3D7\uFE0F Architecture Guide \u2014 mybb-playground-docs"
doc_name: architecture
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

# 🏗️ Architecture Guide — mybb-playground-docs
**Author:** Scribe
**Version:** Draft v0.1
**Status:** Draft
**Last Updated:** 2026-01-18 08:09:46 UTC

> Architecture guide for mybb-playground-docs.

---
## 1. Problem Statement
<!-- ID: problem_statement -->
**Context:**
The MyBB Playground project contains a comprehensive MCP (Model Context Protocol) server with 85+ tools, a Plugin Manager system with 7 components, a PHP Bridge for plugin lifecycle management, and a Disk Sync service for bidirectional template/stylesheet synchronization. This codebase lacks comprehensive documentation that developers can reference to understand and use these systems effectively.

**Goals:**
1. Create a `/docs/wiki/` directory with factual, code-accurate documentation
2. Document all 85+ MCP tools with parameters, return values, and usage examples
3. Document the Plugin Manager workspace structure, file deployment, and lifecycle management
4. Document the PHP Bridge actions and Python wrapper integration
5. Document the Disk Sync service architecture and workflows
6. Update CLAUDE.md with operational instructions referencing the new wiki
7. Provide MyBB-specific best practices for plugin and theme development

**Success Criteria:**
- Documentation is 100% factual to code (no speculation, all claims verifiable)
- Every MCP tool has complete parameter documentation with types and defaults
- Developers can use the wiki as their primary reference without reading source code
- CLAUDE.md references wiki for detailed documentation

**Non-Goals:**
- Auto-generated API documentation (this is hand-crafted wiki content)
- Video tutorials or interactive content
- Documentation of MyBB core (only our extensions)
<!-- ID: requirements_constraints -->
**Functional Requirements:**
1. **Documentation Completeness**
   - Every MCP tool documented with: name, description, parameters (with types/defaults), return format, usage examples
   - Plugin Manager API fully documented with method signatures and workflows
   - PHP Bridge actions documented with CLI signatures and JSON response formats
   - Disk Sync service documented with directory structure and synchronization behavior

2. **Documentation Accuracy**
   - All tool parameters verified against server.py source
   - All method signatures verified against implementation files
   - Code examples must be copy-paste ready and tested

3. **Navigation & Organization**
   - Hierarchical structure with clear progression from basics to advanced
   - Cross-references between related topics
   - Index/table of contents for quick lookup

**Technical Constraints:**
- Documentation files must be Markdown (.md) format
- File names must use underscores and lowercase (e.g., `mcp_tools_reference.md`)
- All paths must be relative to `/docs/wiki/`
- Maximum recommended file size: 500 lines per document (split if larger)
- UTF-8 encoding required

**Dependencies:**
- Research documents provide authoritative source material:
  - `RESEARCH_MCP_SERVER_ARCHITECTURE_20250118_0811.md` (85+ tools)
  - `RESEARCH_PLUGIN_MANAGER_20250118.md` (7 components)
  - `RESEARCH_PHP_BRIDGE_20250118_0810.md` (7 actions)
  - `RESEARCH_DISK_SYNC_SERVICE.md` (6 modules)

**Quality Standards:**
- No placeholder content (every section must be complete)
- No speculation or assumptions (only verified facts)
- Consistent formatting across all documents
- Code blocks with proper language tags (php, python, bash, json)
<!-- ID: architecture_overview -->
**Solution Summary:**
Create a hierarchical wiki documentation system in `/docs/wiki/` that provides comprehensive, code-accurate reference material for the MyBB Playground ecosystem.

**Wiki Structure Overview:**
```
/docs/wiki/
├── index.md                          # Main landing page with navigation
├── getting_started/
│   ├── index.md                      # Setup overview
│   ├── installation.md               # Prerequisites and installation
│   └── quickstart.md                 # First steps tutorial
├── mcp_tools/
│   ├── index.md                      # Tool categories overview (13 categories)
│   ├── templates.md                  # Template tools (9 tools)
│   ├── themes_stylesheets.md         # Theme/stylesheet tools (6 tools)
│   ├── plugins.md                    # Plugin tools (15 tools)
│   ├── forums_threads_posts.md       # Content tools (17 tools)
│   ├── users_moderation.md           # User/mod tools (14 tools)
│   ├── search.md                     # Search tools (4 tools)
│   ├── admin_settings.md             # Admin tools (11 tools)
│   ├── tasks.md                      # Scheduled task tools (5 tools)
│   ├── disk_sync.md                  # Sync tools (5 tools)
│   └── database.md                   # Database query tool (1 tool)
├── plugin_manager/
│   ├── index.md                      # Plugin Manager overview
│   ├── workspace.md                  # Workspace structure and directories
│   ├── deployment.md                 # File deployment and manifest system
│   ├── lifecycle.md                  # PHP lifecycle bridge integration
│   └── database.md                   # SQLite project tracking
├── architecture/
│   ├── index.md                      # System architecture overview
│   ├── mcp_server.md                 # Server internals and tool registration
│   ├── disk_sync.md                  # Bidirectional sync system
│   └── configuration.md              # Environment and config management
└── best_practices/
    ├── index.md                      # Best practices overview
    ├── plugin_development.md         # MyBB plugin patterns
    ├── theme_development.md          # Theme and stylesheet patterns
    └── security.md                   # Security considerations

Total: 26 documentation files
```

**Component Relationships:**
```
┌─────────────────────────────────────────────────────────────────┐
│                        /docs/wiki/                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │ Getting     │ │ MCP Tools   │ │ Plugin      │ │ Best       │ │
│  │ Started     │ │ Reference   │ │ Manager     │ │ Practices  │ │
│  │ (3 docs)    │ │ (11 docs)   │ │ (5 docs)    │ │ (4 docs)   │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬──────┘ │
│         │               │               │              │         │
│         └───────────────┴───────┬───────┴──────────────┘         │
│                                 │                                 │
│                    ┌────────────┴────────────┐                   │
│                    │   Architecture (4 docs)  │                   │
│                    │   (System Internals)     │                   │
│                    └─────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```
<!-- ID: detailed_design -->
### 4.1 Document Content Specifications

**MCP Tools Reference Format (per tool):**
```markdown
### tool_name
**Description:** Brief description from server.py

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| param1 | string | Yes | - | Description |
| param2 | int | No | 50 | Description |

**Returns:** Description of return format (markdown table, JSON, etc.)

**Example:**
\`\`\`
"tool invocation example"
\`\`\`

**Notes:** Any important caveats or related tools
```

**Plugin Manager Documentation Format:**
- Method signatures with full type hints
- Parameter descriptions with constraints
- Return value structure (JSON schema where applicable)
- Workflow diagrams for multi-step operations
- Code examples for common use cases

**PHP Bridge Documentation Format:**
- CLI signature with all flags
- Required and optional parameters
- JSON response structure with examples
- Error response format
- Python wrapper method mapping

### 4.2 Cross-Reference Strategy

Documents should cross-reference related content using relative links:
- MCP tools reference -> Plugin Manager (for plugin lifecycle tools)
- Plugin Manager -> PHP Bridge (for lifecycle execution)
- Best Practices -> MCP Tools (for recommended tool usage)
- Architecture -> All sections (for implementation details)

### 4.3 CLAUDE.md Integration

Add a new section to CLAUDE.md:
```markdown
## Documentation Reference

Comprehensive documentation is available in `/docs/wiki/`:
- [Getting Started](docs/wiki/getting_started/index.md)
- [MCP Tools Reference](docs/wiki/mcp_tools/index.md) - All 85+ tools
- [Plugin Manager Guide](docs/wiki/plugin_manager/index.md)
- [Architecture Overview](docs/wiki/architecture/index.md)
- [Best Practices](docs/wiki/best_practices/index.md)
```

### 4.4 Content Source Mapping

| Wiki Document | Primary Research Source | Secondary Sources |
|--------------|------------------------|-------------------|
| mcp_tools/*.md | RESEARCH_MCP_SERVER_ARCHITECTURE | server.py |
| plugin_manager/*.md | RESEARCH_PLUGIN_MANAGER | manager.py, installer.py |
| plugin_manager/lifecycle.md | RESEARCH_PHP_BRIDGE | lifecycle.py, mcp_bridge.php |
| architecture/disk_sync.md | RESEARCH_DISK_SYNC_SERVICE | sync/*.py |
| best_practices/*.md | All research docs | MyBB documentation |
<!-- ID: directory_structure -->
**Target Wiki Structure:**
```
/home/austin/projects/MyBB_Playground/docs/wiki/
├── index.md                              # Wiki home page
├── getting_started/
│   ├── index.md                          # Getting started landing
│   ├── installation.md                   # Setup prerequisites
│   └── quickstart.md                     # 5-minute tutorial
├── mcp_tools/
│   ├── index.md                          # Tool categories (13)
│   ├── templates.md                      # mybb_list_template_sets, etc. (9 tools)
│   ├── themes_stylesheets.md             # mybb_list_themes, etc. (6 tools)
│   ├── plugins.md                        # mybb_create_plugin, etc. (15 tools)
│   ├── forums_threads_posts.md           # mybb_forum_*, thread_*, post_* (17 tools)
│   ├── users_moderation.md               # mybb_user_*, mod_* (14 tools)
│   ├── search.md                         # mybb_search_* (4 tools)
│   ├── admin_settings.md                 # mybb_setting_*, cache_*, stats_* (11 tools)
│   ├── tasks.md                          # mybb_task_* (5 tools)
│   ├── disk_sync.md                      # mybb_sync_* (5 tools)
│   └── database.md                       # mybb_db_query (1 tool)
├── plugin_manager/
│   ├── index.md                          # System overview
│   ├── workspace.md                      # Directory structure
│   ├── deployment.md                     # File installation
│   ├── lifecycle.md                      # PHP bridge
│   └── database.md                       # SQLite tracking
├── architecture/
│   ├── index.md                          # System overview
│   ├── mcp_server.md                     # Server internals
│   ├── disk_sync.md                      # Sync service
│   └── configuration.md                  # Environment vars
└── best_practices/
    ├── index.md                          # Overview
    ├── plugin_development.md             # Plugin patterns
    ├── theme_development.md              # Theme patterns
    └── security.md                       # Security guide
```

**Source Files Being Documented:**
```
/home/austin/projects/MyBB_Playground/
├── mybb_mcp/mybb_mcp/
│   ├── server.py                         # 85+ MCP tools (3794 lines)
│   ├── config.py                         # Configuration (80 lines)
│   ├── db/connection.py                  # Database layer (1921 lines)
│   ├── tools/plugins.py                  # Plugin scaffolding (382 lines)
│   └── sync/                             # Disk sync service
│       ├── service.py                    # Orchestrator (644 lines)
│       ├── watcher.py                    # File watcher (356 lines)
│       ├── templates.py                  # Template sync (207 lines)
│       ├── stylesheets.py                # Stylesheet sync (228 lines)
│       ├── router.py                     # Path routing (376 lines)
│       └── config.py                     # Sync config (47 lines)
├── plugin_manager/
│   ├── manager.py                        # Main API (1469 lines)
│   ├── installer.py                      # File deployment (674 lines)
│   ├── database.py                       # SQLite (460 lines)
│   ├── workspace.py                      # Workspace (561 lines)
│   ├── lifecycle.py                      # PHP bridge wrapper (283 lines)
│   ├── config.py                         # Config (174 lines)
│   └── schema.py                         # Validation (498 lines)
└── TestForum/
    └── mcp_bridge.php                    # PHP bridge (486 lines)
```
<!-- ID: data_storage -->
**Documentation Storage:**
- All wiki files stored as Markdown in `/docs/wiki/`
- No database required for documentation
- Git version control for all changes

**Research Document Sources:**
| Document | Location | Size | Content |
|----------|----------|------|---------|
| RESEARCH_MCP_SERVER_ARCHITECTURE | .scribe/docs/dev_plans/mybb_playground_docs/research/ | 36KB | 85+ MCP tools |
| RESEARCH_PLUGIN_MANAGER | .scribe/docs/dev_plans/mybb_playground_docs/ | 35KB | 7 components |
| RESEARCH_PHP_BRIDGE | .scribe/docs/dev_plans/mybb-playground-docs/research/ | 20KB | 7 PHP actions |
| RESEARCH_DISK_SYNC_SERVICE | .scribe/docs/dev_plans/mybb-playground-docs/research/ | 18KB | 6 sync modules |

**Content Transformation:**
- Research docs contain raw technical analysis with code references
- Wiki docs transform this into user-friendly reference material
- All wiki content must be traceable to research findings
- No content should be invented without code verification
<!-- ID: testing_strategy -->
**Documentation Accuracy Validation:**
1. **Cross-Reference Check**
   - Every tool parameter must match server.py definition
   - Every method signature must match implementation
   - Every example must be executable

2. **Completeness Check**
   - All 85+ MCP tools documented
   - All Plugin Manager methods documented
   - All PHP Bridge actions documented
   - All configuration options documented

3. **Link Validation**
   - All internal wiki links resolve to existing files
   - All external references to source files are valid paths

**Review Checklist (for each document):**
- [ ] All tool names match server.py exactly
- [ ] Parameter types and defaults verified against code
- [ ] Return formats accurately described
- [ ] Code examples tested where possible
- [ ] No placeholder content remains
- [ ] Consistent formatting with other wiki docs
<!-- ID: deployment_operations -->
**Documentation Deployment:**
- Wiki files created directly in `/docs/wiki/`
- No build process required (native Markdown)
- Git commit captures all changes

**Maintenance Workflow:**
1. When source code changes, update corresponding wiki documentation
2. Keep CLAUDE.md documentation reference section current
3. Research documents are frozen after creation (wiki docs may be updated)

**File Organization:**
- Use descriptive file names matching content (e.g., `templates.md` for template tools)
- Group related tools by category (matching MCP server organization)
- Keep individual files under 500 lines where possible
<!-- ID: open_questions -->
| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Exact method count in MyBBDatabase | Coder | Pending | Research estimates 87+, verify during doc writing |
| Disk sync polling vs real-time | Coder | Pending | Clarify during architecture/disk_sync.md writing |
| Template group manager details | Coder | Pending | May need additional code inspection |

**Resolved:**
- Wiki structure finalized (26 documents across 5 sections)
- Document format specifications defined
- Research-to-wiki content mapping established
<!-- ID: references_appendix -->
**Research Documents (Primary Sources):**
1. `RESEARCH_MCP_SERVER_ARCHITECTURE_20250118_0811.md` - MCP tools, config, database
2. `RESEARCH_PLUGIN_MANAGER_20250118.md` - Plugin Manager system
3. `RESEARCH_PHP_BRIDGE_20250118_0810.md` - PHP lifecycle bridge
4. `RESEARCH_DISK_SYNC_SERVICE.md` - Disk sync service

**Source Code References:**
- `mybb_mcp/mybb_mcp/server.py` - MCP tool definitions (lines 53-1131)
- `mybb_mcp/mybb_mcp/config.py` - Configuration system
- `mybb_mcp/mybb_mcp/db/connection.py` - Database operations
- `mybb_mcp/mybb_mcp/tools/plugins.py` - Plugin scaffolding
- `mybb_mcp/mybb_mcp/sync/*.py` - Disk sync modules
- `plugin_manager/*.py` - Plugin Manager components
- `TestForum/mcp_bridge.php` - PHP bridge

**External References:**
- [MyBB Plugin Documentation](https://docs.mybb.com/1.8/development/plugins/)
- [MyBB Hooks Reference](https://docs.mybb.com/1.8/development/plugins/hooks/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

**Related Project Documents:**
- PHASE_PLAN.md - Implementation phases for documentation writing
- CHECKLIST.md - Verification checklist for coder agent
- PROGRESS_LOG.md - Development progress tracking
