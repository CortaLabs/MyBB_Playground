# CLAUDE.md - MyBB Playground

## Project Overview

AI-assisted MyBB development toolkit providing MCP tools for Claude Code to interact with MyBB installations. The goal is to make MyBB plugin and theme development accessible through natural language.

**Key Components:**
- `mybb_mcp/` — Python MCP server exposing 85+ MyBB tools to Claude
- `TestForum/` — Local MyBB 1.8.x installation for development
- `mybb_sync/` — Template/stylesheet disk sync with live file watching
- `plugin_manager/` — Plugin/theme workspace with deployment and PHP lifecycle execution

**Notes for the Main Claude Code Orchestrator:**
- Always try to conserve your context window, delegate fixes and research as needed.  Use the subagents rather than trying to do everything yourself.
- Always wait for subagents to complete, rather than checking on them.  This is a huge context killer.
- Append Entry audit notes regularly, as the orchestrator this is a real solid approach to passing context to downstream agents.

## Forbidden Operations

**NEVER use destructive commands without explicit user confirmation:**
- `rm -rf` is BANNED. Period.
- `rm -r` requires explicit user approval before execution.
- Any deletion of directories containing code requires user confirmation.
- If something "needs to be deleted and recreated", ASK FIRST.

**Before deleting anything:**
1. State exactly what will be deleted
2. Explain why deletion is necessary
3. WAIT for user confirmation
4. If there's any doubt, don't delete

**Plugin Manager workflow is mandatory:**
- Use `mybb_create_plugin` to create plugins - never create workspace files directly
- Use `mybb_plugin_install` to deploy - never copy files to TestForum manually
- Check if a plugin exists in the system BEFORE assuming it doesn't
- The correct database is `.plugin_manager/projects.db` at repo root

**When things go wrong:**
- Don't try to "fix" by deleting and recreating
- Investigate why the system doesn't recognize something
- Read the docs (CLAUDE.md, wiki) before assuming infrastructure is broken
- Ask the user before taking destructive action

## Development Environment

### Prerequisites
- Python 3.10+
- PHP 8.0+ (installed via `setup_dev_env.sh`)
- MariaDB (installed via `setup_dev_env.sh`)
- Claude Code with MCP support

### Quick Start
```bash
# First time setup
./setup_dev_env.sh

# Start MyBB server (port 8022)
./start_mybb.sh

# MCP server is configured at local scope for this project
# Restart Claude Code to load it
```

### Environment Variables
All config is in `.env` at project root:
```
MYBB_DB_HOST=localhost
MYBB_DB_NAME=mybb_dev
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=<password>
MYBB_DB_PREFIX=mybb_
MYBB_ROOT=/home/austin/projects/MyBB_Playground/TestForum
MYBB_URL=http://localhost:8022
```

## Architecture

### MCP Server (`mybb_mcp/`)
```
mybb_mcp/
├── server.py           # Main server, all tool handlers
├── config.py           # Env/config loading
├── db/connection.py    # MySQL wrapper with MyBB-specific methods
└── tools/plugins.py    # Plugin scaffolding + hooks reference
```

**Tool Categories (85+ tools):**
- Templates (9): list, read, write, batch operations, find/replace, outdated detection
- Themes/Stylesheets (6): list, read, write, create themes
- Plugins (15): CRUD, hooks discovery, lifecycle management (install/uninstall with PHP execution)
- Forums/Threads/Posts (17): full content management
- Users/Moderation (14): user management, mod actions, mod logging
- Search (4): posts, threads, users, advanced combined search
- Admin/Settings (11): settings, cache, statistics
- Tasks (6): scheduled task management
- Disk Sync (5): export, import, watcher control

See [MCP Tools Reference](docs/wiki/mcp_tools/index.md) for complete documentation.

### MyBB Template Inheritance
```
sid = -2  → Master templates (base, never delete)
sid = -1  → Global templates (shared)
sid >= 1  → Template set overrides (custom versions)
```

When writing templates, always check for master first. Custom templates override master.

### Disk Sync System
Templates and stylesheets sync between disk and database:
- **Location:** `mybb_sync/template_sets/` and `mybb_sync/themes/`
- **Export:** `mybb_sync_export_templates("Default Templates")` or `mybb_sync_export_stylesheets("Default")`
- **Watcher:** `mybb_sync_start_watcher()` monitors disk changes → syncs to DB
- **Workflow:** Edit files on disk, watcher auto-syncs — this is the primary development workflow

See [Disk Sync Architecture](docs/wiki/architecture/disk_sync.md) for implementation details.

## Critical Rules

### DO NOT Edit Core MyBB Files
**Never modify files in `TestForum/` that are part of core MyBB.** All MyBB customization must be done through:
- Plugins (`TestForum/inc/plugins/`)
- Templates (via MCP tools or Admin CP)
- Stylesheets (via MCP tools or Admin CP)
- Language files (`TestForum/inc/languages/*/`)

Core files will be overwritten on MyBB upgrades. Hooks and plugins are the correct extension mechanism.

### MyBB Development Workflow

**Template & Stylesheet Editing:**
- ALWAYS edit via disk sync — edit files in `mybb_sync/`, the watcher syncs to DB automatically
- Export first if templates don't exist on disk: `mybb_sync_export_templates("Default Templates")`
- Never use `mybb_write_template` directly during development — disk sync is the workflow
- Stylesheets work the same way: edit on disk, watcher syncs

**Plugin Development:**
- Develop plugins in workspace: `plugin_manager/plugins/public/` or `private/`
- Use `mybb_plugin_install(codename)` to deploy — this runs actual PHP lifecycle (_install, _activate)
- Don't manually copy files to TestForum — the installer handles file deployment and tracking
- Each plugin has `meta.json` for metadata — see [Plugin Manager docs](docs/wiki/plugin_manager/workspace.md)

**Theme Development:**
- Themes live in workspace: `plugin_manager/themes/`
- Stylesheets use copy-on-write inheritance from parent themes
- Use disk sync for editing, not direct DB writes
- See [Theme Development guide](docs/wiki/best_practices/theme_development.md)

**MyBB Context:**
- MyBB is 15+ year old PHP forum software with a mature but dated architecture
- Work within MyBB's hook/template system — don't try to modernize MyBB itself
- We're building tooling to make MyBB development easier and AI-accessible
- Set realistic expectations — some things are limited by MyBB's design

### Wiki Maintenance

**Mandatory documentation updates:**
- Any code change affecting documented behavior MUST update relevant wiki pages
- New features MUST have wiki documentation upon completion
- Wiki accuracy is not optional — outdated docs are worse than no docs

**What requires wiki updates:**
- New MCP tools → add to `docs/wiki/mcp_tools/` appropriate category
- Changed tool parameters/behavior → update tool documentation
- New Plugin Manager features → update `docs/wiki/plugin_manager/`
- Architecture changes → update `docs/wiki/architecture/`

### Development Standards

**Don't freestyle — follow the system:**
- Use Scribe PROTOCOL for non-trivial features (research → architect → review → code → review)
- Read existing wiki/research docs before implementing
- Check if an MCP tool exists before writing raw queries or file operations
- Understand the existing patterns before adding new ones

**MCP tools exist for a reason:**
- Templates: use disk sync or MCP tools, not raw DB queries
- Plugins: use Plugin Manager workflow, not manual file copying
- Settings/cache: use MCP tools for proper cache invalidation
- Database: `mybb_db_query` is read-only by design — writes go through specialized tools

## Coding Conventions

### Python (MCP Server)
- Python 3.10+ with type hints
- Use `pathlib.Path` for all file operations
- Database queries use parameterized statements (never string interpolation)
- All tools return formatted markdown strings
- Errors are caught and returned as user-friendly messages

### PHP (Plugins)
- Follow MyBB plugin structure: `{codename}_info()`, `_activate()`, `_deactivate()`, `_install()`, `_uninstall()`, `_is_installed()`
- Use `$db->escape_string()` for user input
- Prefix all functions/variables with plugin codename
- Templates use `{$variable}` syntax

### File Naming
- Python: `snake_case.py`
- PHP plugins: `codename.php` (lowercase, underscores)
- Templates: `template_name.html` (matches DB title)
- Stylesheets: `name.css` (matches DB name)

## Scribe Orchestration Protocol

This project uses Scribe for structured development tracking. **Multiple Scribe projects may exist within this repo** — each major feature or component can have its own project.

### Repository Root
**Always pass repo root to Scribe tools:**
```
root: /home/austin/projects/MyBB_Playground
```

### Session Startup (Required)

Every session must follow this workflow:

```python
# 1. Activate project
set_project(name="<project_name>", root="/home/austin/projects/MyBB_Playground")

# 2. Rehydrate context
read_recent(n=5)

# 3. Log session start (REQUIRED)
append_entry(
    message="Starting <task>",
    status="info",
    agent="Claude",
    meta={
        "task": "<task>",
        "reasoning": {"why": "...", "what": "...", "how": "..."}
    }
)
```

### Active Projects
Projects are created per-feature/component:
- `mybb-playground` — Overall project coordination
- `disk-sync` — Template/stylesheet disk sync feature (planned)
- `plugin-builder` — Enhanced plugin scaffolding (planned)

Use `mcp__scribe__list_projects(root="/home/austin/projects/MyBB_Playground")` to see all projects in this repo.

### Scribe Subagent Workflow (PROTOCOL)

For non-trivial features, follow the 5-step PROTOCOL workflow using specialized subagents:

| Step | Agent | Model | Purpose |
|------|-------|-------|---------|
| 1 | `scribe-research-analyst` | **haiku** or sonnet | Deep codebase investigation, gather context, produce RESEARCH_*.md |
| 2 | `scribe-architect` | **opus** | Transform research into architecture docs, phase plans, checklists |
| 3 | `scribe-review-agent` | **sonnet** or opus | Pre-implementation review, verify feasibility (≥93% standard) |
| 4 | `scribe-coder` | **sonnet** or opus | Implement according to plan, log all progress |
| 5 | `scribe-review-agent` | **sonnet** or opus | Post-implementation review, validate, grade agents |

**Model Selection Rules:**
- **Research** → haiku (cheap, fast, good for pattern discovery and context gathering)
- **Architect** → opus (critical decisions require strongest reasoning)
- **Coder** → sonnet or opus (implementation quality matters)
- **Review** → sonnet or opus (needs to catch issues architect/coder missed)

### Using Haiku Swarms for Research

For context gathering, use **haiku model** with the Explore agent or research-analyst:

```python
Task(
    subagent_type="scribe-research-analyst",
    model="haiku",  # Fast, cheap for research swarms
    prompt="""
    Investigate how the VSCode extension handles template sync.
    Repo root: /home/austin/projects/MyBB_Playground
    Focus on: vscode-mybbbridge/src/*.ts
    """
)
```

**When to use haiku swarms:**
- Initial codebase exploration
- Gathering context from multiple files
- Pattern discovery across the codebase
- Producing research reports

**When to use stronger models:**
- Architecture decisions
- Code implementation
- Complex reasoning

### Logging Guidelines

**Reasoning blocks are REQUIRED** in every append_entry:

```python
append_entry(
    message="Completed file watcher implementation",
    status="success",
    agent="Claude",
    meta={
        "task": "disk-sync",
        "reasoning": {
            "why": "Need to sync templates from disk to DB on change",
            "what": "Implemented watchdog-based file observer",
            "how": "Used watchdog library with debouncing for batch updates"
        }
    }
)
```

**Log frequency:** After each meaningful step (every 2-3 edits or ~5 minutes), and after:
- Investigations and discoveries
- Decisions made
- Tests run
- Errors encountered
- Task completions

### Status Types
- `info` — General progress notes
- `success` — Completed tasks/milestones
- `warn` — Concerns, potential issues
- `error` — Failed operations
- `bug` — Bug tracking
- `plan` — Planning decisions

### File Operations

**Use `read_file` for file reads** (not shell reads like cat/head/tail):
```python
mcp__scribe__read_file(
    path="mybb_mcp/server.py",
    mode="scan_only"  # or "chunk", "search", "line_range"
)
```

**Use `manage_docs` for managed docs** in `.scribe/docs/dev_plans/<project>/`:
```python
manage_docs(
    action="replace_section",
    doc_name="architecture",
    section="problem_statement",
    content="Updated content..."
)
```

### Creating a New Feature Project

Before starting a new feature:

```python
# 1. Create the project
set_project(
    name="feature-name",
    description="What this feature does",
    root="/home/austin/projects/MyBB_Playground",
    tags=["mybb", "relevant", "tags"]
)

# 2. Log the start
append_entry(
    message="Starting feature-name project",
    status="plan",
    agent="Claude",
    meta={
        "reasoning": {
            "why": "User requested this feature",
            "what": "Creating new Scribe project for tracking",
            "how": "Will follow PROTOCOL workflow"
        }
    }
)

# 3. Spawn research analyst (haiku) to gather context
Task(
    subagent_type="scribe-research-analyst",
    model="haiku",
    prompt="Research context for feature-name..."
)
```

### Session Completion

Always log completion at end of significant work:

```python
append_entry(
    message="Completed <task>: <summary>",
    status="success",
    agent="Claude",
    meta={
        "deliverables": ["file1.py", "file2.py"],
        "confidence": 0.9,
        "reasoning": {
            "why": "Task objectives met",
            "what": "Implemented X, Y, Z",
            "how": "Used approach A, tested with B"
        }
    }
)

## Key Files

| File | Purpose |
|------|---------|
| `mybb_mcp/server.py` | Main MCP server with all tool implementations |
| `mybb_mcp/db/connection.py` | Database operations for templates, themes, plugins |
| `mybb_mcp/tools/plugins.py` | Plugin scaffolding templates and hooks reference |
| `mybb_mcp/config.py` | Configuration loading from .env |
| `.env` | Database credentials and paths (gitignored) |
| `TestForum/inc/plugins/` | Where plugins are installed |
| `TestForum/inc/languages/english/` | Language files for plugins |

## Documentation Reference

Comprehensive technical documentation lives in `/docs/wiki/`. Use these for detailed reference — they're kept in sync with the codebase.

### Quick Links

| Section | Index | What's There |
|---------|-------|--------------|
| **Getting Started** | [index](docs/wiki/getting_started/index.md) | Installation, quickstart tutorial, prerequisites |
| **MCP Tools** | [index](docs/wiki/mcp_tools/index.md) | All 85+ tools with parameters, return formats, examples |
| **Plugin Manager** | [index](docs/wiki/plugin_manager/index.md) | Workspace, deployment, PHP lifecycle, database schema |
| **Architecture** | [index](docs/wiki/architecture/index.md) | MCP server internals, disk sync, configuration |
| **Best Practices** | [index](docs/wiki/best_practices/index.md) | Plugin/theme development patterns, security |

### When to Check the Wiki

- **Before implementing a feature** — check if patterns/tools already exist
- **When using MCP tools** — full parameter docs and examples in `mcp_tools/`
- **Plugin/theme development** — workflows documented in `plugin_manager/` and `best_practices/`
- **Understanding the system** — architecture docs explain how components work together

### Wiki Structure

```
docs/wiki/
├── index.md                    # Main entry point
├── getting_started/            # Installation, quickstart
├── mcp_tools/                  # Tool reference (85+ tools)
│   ├── index.md               # Overview + tool categories
│   ├── templates.md           # 9 template tools
│   ├── themes_stylesheets.md  # 6 theme/style tools
│   ├── plugins.md             # 15 plugin tools
│   ├── forums_threads_posts.md # 17 content tools
│   ├── users_moderation.md    # 14 user/mod tools
│   ├── search.md              # 4 search tools
│   ├── admin_settings.md      # 11 admin tools
│   ├── tasks.md               # 6 task tools
│   ├── disk_sync.md           # 5 sync tools
│   └── database.md            # 1 query tool
├── plugin_manager/             # Plugin Manager system
├── architecture/               # System internals
└── best_practices/             # Development guidelines
```

## Testing

### Test MCP Connection
```bash
claude mcp get mybb
# Should show: Status: ✓ Connected
```

### Test Database Connection
```bash
cd mybb_mcp
source .venv/bin/activate
python -c "from mybb_mcp.config import load_config; from mybb_mcp.db import MyBBDatabase; db = MyBBDatabase(load_config().db); print(db.list_template_sets())"
```

### Test in Claude Code
```
"List MyBB template sets"
"Show me the header template"
"Create a test plugin called 'my_test'"
```

## Common Tasks

### Add a new MCP tool
1. Add tool definition to `all_tools` list in `server.py`
2. Add handler in `handle_tool()` function
3. If complex, add helper function in appropriate `tools/*.py` file

### Modify plugin scaffolding
Edit `PLUGIN_TEMPLATE` in `mybb_mcp/tools/plugins.py`

### Add new hooks to reference
Edit `HOOKS_REFERENCE` dict in `mybb_mcp/tools/plugins.py`

## Links

- [MyBB Plugin Docs](https://docs.mybb.com/1.8/development/plugins/)
- [MyBB Hooks List](https://docs.mybb.com/1.8/development/plugins/hooks/)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Claude Code MCP Docs](https://docs.anthropic.com/en/docs/claude-code/mcp)
