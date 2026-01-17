# CLAUDE.md - MyBB Playground

## Project Overview

AI-assisted MyBB development toolkit providing MCP tools for Claude Code to interact with MyBB installations. The goal is to make MyBB plugin and theme development accessible through natural language.

**Key Components:**
- `mybb_mcp/` — Python MCP server exposing MyBB tools to Claude
- `TestForum/` — Local MyBB 1.8.x installation for development
- Template/stylesheet disk sync (planned) — Live file watching with DB sync

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

**Tool Categories:**
- Templates: `mybb_list_template_sets`, `mybb_list_templates`, `mybb_read_template`, `mybb_write_template`
- Themes: `mybb_list_themes`, `mybb_list_stylesheets`, `mybb_read_stylesheet`, `mybb_write_stylesheet`
- Plugins: `mybb_list_plugins`, `mybb_read_plugin`, `mybb_create_plugin`, `mybb_list_hooks`, `mybb_analyze_plugin`
- Database: `mybb_db_query` (SELECT only)

### MyBB Template Inheritance
```
sid = -2  → Master templates (base, never delete)
sid = -1  → Global templates (shared)
sid >= 1  → Template set overrides (custom versions)
```

When writing templates, always check for master first. Custom templates override master.

### Planned: Disk Sync Feature
Will mirror VSCode extension behavior:
- Export templates to `workspace/templates/{set}/{group}/{name}.html`
- Export stylesheets to `workspace/styles/{theme}/{name}.css`
- Watch for file changes → update DB
- Watch for DB changes → update files (via polling or triggers)

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
