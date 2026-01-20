# CLAUDE.md - MyBB Playground

## Project Overview

AI-assisted MyBB development toolkit providing MCP tools for Claude Code to interact with MyBB installations. The goal is to make MyBB plugin and theme development accessible through natural language.

**Key Components:**
- `mybb_mcp/` — Python MCP server exposing 94+ MyBB tools to Claude
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

**Extraction means EXTRACTION, not duplication:**
- When told to "extract" code from File A to File B, you MUST:
  1. Copy the code to File B
  2. REMOVE the code from File A
  3. Wire up imports/references so File A uses File B
- If you only copy without removing, you've created DUPLICATE CODE
- Extraction is a refactoring operation - the end result should have the SAME total lines, just reorganized
- Never tell the orchestrator extraction is "complete" if the source file still contains the extracted code

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

### Configuration Files (MyBB Forge v2)

**ForgeConfig System** provides developer metadata and project defaults:

**`.mybb-forge.yaml`** (checked into version control):
```yaml
developer:
  name: "Your Name"
  website: "https://yoursite.com"
  email: "you@example.com"

defaults:
  compatibility: "18*"        # MyBB version compatibility
  license: "MIT"              # Default license for new plugins
  visibility: "public"        # public or private workspace

subtrees:
  plugin_manager/plugins/public/my_plugin:
    remote: PRIVATE_PLUGINS_REMOTE  # References .mybb-forge.env
    branch: main

sync:
  debounce_ms: 100            # File watcher debounce (default: 100)
  batch_window_ms: 100        # Batch window for updates (default: 100)
  enable_cache_refresh: true  # Template set caching (default: true)
```

**`.mybb-forge.env`** (gitignored, for private remotes):
```bash
PRIVATE_PLUGINS_REMOTE=git@github.com:yourname/private-plugins.git
PRIVATE_THEMES_REMOTE=git@github.com:yourname/private-themes.git
```

**Usage:**
- Developer info auto-populates `meta.json` for new plugins
- Subtrees enable private plugin repositories via git subtree
- Sync settings control file watcher behavior and caching
- Use `MYBB_SYNC_DISABLE_CACHE=1` env var to disable template set caching during development

## Architecture

### MCP Server (`mybb_mcp/`)
```
mybb_mcp/mybb_mcp/
├── server.py           # Orchestration layer (116 lines)
├── tools_registry.py   # Tool definitions (94 tools)
├── config.py           # Env/config loading
├── handlers/           # Modular tool handlers (14 modules)
│   ├── dispatcher.py   # Dictionary-based routing
│   ├── templates.py    # 8 handlers
│   ├── themes.py       # 5 handlers
│   ├── plugins.py      # 15 handlers
│   ├── content.py      # 16 handlers (forums/threads/posts)
│   ├── users.py        # 6 handlers
│   ├── moderation.py   # 8 handlers
│   ├── search.py       # 4 handlers
│   ├── admin.py        # 11 handlers
│   ├── tasks.py        # 6 handlers
│   ├── sync.py         # 5 handlers
│   └── database.py     # 1 handler
├── db/connection.py    # MySQL wrapper with MyBB-specific methods
└── tools/plugins.py    # Plugin scaffolding + hooks reference
```

**Tool Categories (99 tools):**
- Templates (9): list, read, write, batch operations, find/replace, outdated detection
- Themes/Stylesheets (6): list, read, write, create themes
- Plugins (15): CRUD, hooks discovery, lifecycle management (install/uninstall with PHP execution)
- Forums/Threads/Posts (17): full content management
- Users/Moderation (14): user management, mod actions, mod logging
- Search (4): posts, threads, users, advanced combined search
- Admin/Settings (11): settings, cache, statistics
- Tasks (6): scheduled task management
- Disk Sync (5): export, import, watcher control
- Server Orchestration (5): start, stop, status, logs, restart PHP dev server

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

### Server Orchestration
MCP tools for managing the PHP development server:

```python
# Check server status
mybb_server_status()

# Start server (auto-detects if already running)
mybb_server_start()
mybb_server_start(port=8022, force=True)  # Force restart on specific port

# Stop server
mybb_server_stop()
mybb_server_stop(force=True)  # Force kill if graceful shutdown fails

# Restart server
mybb_server_restart()

# Query server logs (essential for debugging)
mybb_server_logs()                           # Last 50 entries
mybb_server_logs(errors_only=True)           # Only errors (PHP errors, 4xx/5xx)
mybb_server_logs(errors_only=True, limit=100)  # More error entries
mybb_server_logs(exclude_static=True)        # Filter out .css, .js, images
mybb_server_logs(since_minutes=5)            # Last 5 minutes only
mybb_server_logs(filter_keyword="Fatal")     # Search for keyword
mybb_server_logs(offset=50, limit=50)        # Pagination (page 2)
```

**Log Features:**
- Error categorization: `fatal`, `parse`, `warning`, `notice`, `http_5xx`, `http_4xx`, etc.
- Token guards: max 8000 chars output to prevent context bloat
- Pagination with offset/limit for large logs
- Error breakdown summary in output

**Log file:** `logs/server.log` (gitignored, rotates on server start)

### Browser Testing (Chrome DevTools MCP)
Use Chrome DevTools MCP tools to test MyBB in a real browser:

**Dev Credentials:**
- **URL:** http://localhost:8022
- **Admin CP:** http://localhost:8022/admin/
- **Username:** `admin`
- **Password:** `admin`

**Common Browser Operations:**
```python
# List open pages
mcp__chrome-devtools__list_pages()

# Navigate to MyBB
mcp__chrome-devtools__navigate_page(url="http://localhost:8022", type="url")

# Take a snapshot (preferred over screenshot for understanding page structure)
mcp__chrome-devtools__take_snapshot()

# Click an element by uid from snapshot
mcp__chrome-devtools__click(uid="1_27")  # e.g., Admin CP link

# Fill a form field
mcp__chrome-devtools__fill(uid="1_13", value="search term")

# Take a screenshot (for visual verification)
mcp__chrome-devtools__take_screenshot()

# Check for errors in console
mcp__chrome-devtools__list_console_messages()
```

**Testing Workflow:**
1. Ensure server is running: `mybb_server_status()`
2. Navigate to the page you're testing
3. Take snapshot to understand page structure
4. Interact with elements using uid from snapshot
5. Check console for JavaScript errors
6. Check server logs for PHP errors: `mybb_server_logs(errors_only=True)`

**Notes:**
- **Snapshots** give element uids for interaction (clicking, filling forms)
- **Screenshots** are required for visual verification (CSS, layout, styling issues)
- Use both: snapshot to understand structure, screenshot to see how it looks
- The MCP runs with `--isolated` flag to avoid profile conflicts
- Admin is pre-logged-in during development

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
- **Plugin Templates (v2 Disk-First Sync):**
  - Create templates in workspace: `templates/{template_name}.html` (syncs to sid=-2, master templates)
  - For theme-specific overrides: `templates_themes/{Theme Name}/{template_name}.html`
  - Template naming: `{codename}_{template_name}` (e.g., `myplugin_welcome.html`)
  - File watcher auto-syncs changes to database when editing on disk
  - Templates are deployed during `mybb_plugin_install()` along with PHP files

**Theme Development:**
- Themes live in workspace: `plugin_manager/themes/`
- Stylesheets use copy-on-write inheritance from parent themes
- Use disk sync for editing, not direct DB writes
- See [Theme Development guide](docs/wiki/best_practices/theme_development.md)

**Git Hygiene for Private Plugins/Themes:**

Private plugins and themes use **nested git repositories** — each has its own independent git repo.

```
plugin_manager/
├── plugins/
│   ├── public/           # Tracked in parent repo (default plugins like cortex, dice_roller)
│   └── private/          # Gitignored - each plugin is its own nested repo
│       └── my_plugin/
│           └── .git/     # Independent git repo
└── themes/               # Gitignored - nested repos
```

**MCP Git Tools (for plugin/theme repos):**
```python
mybb_plugin_git_init(codename, visibility="private")      # Initialize git
mybb_plugin_github_create(codename, visibility, repo_visibility)  # Create GitHub repo
mybb_plugin_git_status(codename, visibility)              # Check status
mybb_plugin_git_commit(codename, visibility, message)     # Commit all changes
mybb_plugin_git_commit(codename, visibility, message, files=[...])  # Commit specific files
mybb_plugin_git_push(codename, visibility)                # Push to remote
mybb_plugin_git_pull(codename, visibility)                # Pull from remote
```

### Orchestrator Commit Discipline

**Subagents DO NOT commit.** The orchestrator handles all commits at defined gates.

| Gate | What to Commit | Where | How |
|------|---------------|-------|-----|
| After Research | Scribe research docs | Parent repo | CLI `git commit` |
| After Architecture | Scribe architecture docs | Parent repo | CLI `git commit` |
| After Code Phase | Plugin code changes | Plugin repo | MCP `mybb_plugin_git_commit` |
| After Review Approval | Final cleanup | Both if needed | CLI + MCP |

**Why orchestrator commits, not agents:**
- Scribe docs (`.scribe/`) are in the parent repo, not plugin workspaces
- Multiple agents (swarms) would commit each other's work
- Orchestrator has full visibility to make atomic, meaningful commits

**Parent repo (MyBB Playground):** CLI `git commit` for:
- Scribe docs (research, architecture, reviews)
- MCP server code
- Install scripts, wiki, default plugins

**Plugin/theme repos:** MCP `mybb_plugin_git_commit` for:
- Plugin PHP code
- Templates, stylesheets
- Language files

**Optional `files` parameter:** When committing plugin repos, use `files=[...]` to commit only specific files. Useful if orchestrator needs to commit partial work or avoid committing unrelated changes.

GitHub repos use prefix from `.mybb-forge.yaml` (e.g., `mybb_playground_my_plugin`).

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

### 🚨 Scribe Commandments (Non-Negotiable)

These rules are MANDATORY for all agents. Violations = rejection.

#### #0 — Always Rehydrate From Progress Log First
- **Before ANY work:** Call `read_recent(n=5)` minimum, `query_entries` for targeted history
- **Why:** Progress log is source of truth. Skipping it causes hallucinated priorities and broken invariants
- **Sentinel mode (no project):** `read_recent`/`query_entries` operate on global scope — don't target a project path

#### #0.5 — Infrastructure Primacy (No Replacement Files)
- **Rule:** Work within existing system. NEVER create `enhanced_*`, `*_v2`, `*_new` files to avoid integration
- **Why:** Replacement files create tech debt, split code paths, destroy reliability
- **Comply:** Edit/extend/refactor existing components. If blocked, escalate with a plan — don't fork

#### #1 — Always Scribe (Log Everything Significant)
- **Rule:** Use `append_entry` for EVERY significant action: investigations, decisions, code changes, test results, bugs, plan updates
- **If not Scribed, it didn't happen** — this is your audit trail
- **Orchestrators:** Always pass `project_name` to subagents so they log to the correct project

#### #2 — Reasoning Traces Required
- **Every `append_entry` MUST include `reasoning` block:**
  - `why`: goal / decision point
  - `what`: constraints / alternatives considered
  - `how`: method / steps / remaining uncertainty
- **Why:** Creates auditable decision record, prevents shallow "looks good" work
- **Review enforcement:** Missing why/what/how = reject

#### #3 — MCP Tool Usage Policy
- **If a tool exists, CALL IT DIRECTLY** — no manual scripting or substitutes
- **Log intent AFTER** the tool call succeeds or fails
- **Confirmation flags** (`confirm`, `dry_run`) must be actual tool parameters
- **File reads:** Use `read_file` (scan_only allowed) — no manual/implicit reads
- **Why:** Tool calls are the auditable execution layer. Simulating tools = untrusted output

#### #4 — Structure, Cleanliness, Tests
- **Follow repo structure:** Tests in `/tests` using existing layout
- **Don't clutter:** No random files, mirror existing patterns
- **When in doubt:** Search existing code first

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

### Development Protocol (REQUIRED)

**Full Specification:** `.scribe/docs/dev_plans/mybb_dev_protocol/PROTOCOL_SPEC.md`

All non-trivial development follows this 6-phase workflow:

```
SPEC → Research → Architect → Code → Review → Documentation
```

| Phase | Agent | Purpose |
|-------|-------|---------|
| **SPEC** | User + Orchestrator | Define what we're building, create Scribe project |
| **Research** | `mybb-research-analyst` (haiku) | Gather context, verify against code |
| **Architect** | `mybb-architect` (opus) | Create ARCHITECTURE_GUIDE.md, PHASE_PLAN.md, CHECKLIST.md |
| **Code** | `mybb-coder` (sonnet) | Execute bounded task packages |
| **Review** | `mybb-review-agent` (sonnet) | Validate against plan (≥93% to pass) |
| **Documentation** | Coder/Orchestrator | Fill README, update wiki, no TODOs at release |

**Critical Rules:**
- **Sequential coders** if tasks touch same files; **concurrent** if different files
- **No hacky workarounds** — work within MyBB's systems
- **Documentation is mandatory** — README must have all sections filled
- **Plugin Manager workflow required** — never create files manually

### Scribe Subagent Workflow (PROTOCOL)

For non-trivial features, follow the 6-step PROTOCOL workflow using specialized subagents:

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

### MyBB-Specialized Agents (PREFERRED)

For all MyBB development work, **prefer these specialized agents over the generic Scribe agents**. They have MyBB-specific knowledge baked in and know the Plugin Manager/disk sync workflows.

#### PROTOCOL Workflow Agents (MyBB-Specialized)

| Step | Agent | Purpose | When to Use |
|------|-------|---------|-------------|
| 1 | `mybb-research-analyst` | Investigate MyBB internals using 94+ MCP tools | Analyzing plugins, hooks, templates before development |
| 2 | `mybb-architect` | Design plugins/templates/themes | Creating architecture for new MyBB features |
| 3 | `mybb-review-agent` | Review MyBB work for workflow compliance | Pre/post-implementation reviews |
| 4 | `mybb-coder` | Implement plugins/templates | Writing PHP, editing templates via disk sync |
| 5 | `mybb-review-agent` | Final validation and grading | Post-implementation verification |
| * | `mybb-bug-hunter` | Diagnose plugin/template issues | Debugging MyBB-specific problems |

#### Deep Specialist Agents (Consultants)

| Agent | Expertise | When to Use |
|-------|-----------|-------------|
| `mybb-plugin-specialist` | Plugin lifecycle, hooks, settings, security patterns | Complex plugin architecture decisions, hook selection, debugging lifecycle issues |
| `mybb-template-specialist` | Template inheritance, Cortex syntax, disk sync, find_replace patterns | Template modification strategy, Cortex debugging, theme development |

#### MyBB vs Generic Scribe Agents

| Use MyBB Agents When... | Use Generic Scribe Agents When... |
|-------------------------|-----------------------------------|
| Creating/modifying MyBB plugins | Working on MCP server Python code |
| Working with templates or themes | Working on non-MyBB infrastructure |
| Debugging plugin/template issues | General codebase exploration |
| Need MyBB-specific hook/API knowledge | Language-agnostic research |

#### Multi-Coder Workflow (CRITICAL)

**NEVER send a single coder on a large scope.** Break work into bounded task packages and spawn multiple coders:

| Scope Size | Approach |
|------------|----------|
| 1-2 files, <100 lines | Single coder |
| 3-5 files, one component | Single coder with bounded scope |
| Multiple components | **Multiple coders** - one per component |
| Cross-cutting changes | **Sequential coders** - respect dependencies |

**Coder Scoping Rules:**
- Each coder gets ONE bounded task package from PHASE_PLAN.md
- Task package specifies exact files, line ranges, and verification criteria
- **Concurrent coders CANNOT have overlapping file scopes** - if two tasks touch the same file, they must be sequential
- Orchestrator waits for each coder to complete before spawning coders that touch the same files

**Parallel vs Sequential:**
```
Different files, no dependencies → CAN be parallel
Same files touched            → MUST be sequential
Logical dependencies          → MUST be sequential (usually)
```

**Before spawning parallel coders, verify:**
1. No file overlap between task packages
2. No logical dependencies (one task's output needed by another)
3. Each coder has complete context for their isolated scope

**Example: Using MyBB Agents**

```python
# Research phase - use mybb-research-analyst
Task(
    subagent_type="mybb-research-analyst",
    model="haiku",
    prompt="Analyze how reputation plugins work in MyBB..."
)

# Architecture phase - use mybb-architect
Task(
    subagent_type="mybb-architect",
    model="opus",
    prompt="Design a karma plugin based on the research findings..."
)

# Implementation phase - MULTIPLE CODERS for large scope
# Coder 1: Phase 1 (must be first - creates settings)
Task(
    subagent_type="mybb-coder",
    model="sonnet",
    prompt="Implement Phase 1 Task Packages 1.1-1.4: MyBB settings lifecycle..."
)

# After Phase 1 completes, spawn parallel coders for independent work:
# Coder 2, 3, 4 in parallel (independent components)
Task(subagent_type="mybb-coder", prompt="Implement Phase 2: SecurityPolicy...")
Task(subagent_type="mybb-coder", prompt="Implement Phase 3: Parser...")
Task(subagent_type="mybb-coder", prompt="Implement Phase 4: Cache...")

# After all complete, final integration coder
Task(subagent_type="mybb-coder", prompt="Implement Phase 5-6: Wiring and testing...")

# For deep guidance - use specialists
Task(
    subagent_type="mybb-plugin-specialist",
    model="sonnet",
    prompt="Help me understand why my postbit hook isn't firing..."
)
```

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
| `mybb_mcp/mybb_mcp/server.py` | MCP server orchestration (116 lines) |
| `mybb_mcp/mybb_mcp/tools_registry.py` | All 94 tool definitions |
| `mybb_mcp/mybb_mcp/handlers/` | Modular tool handlers (14 modules, 94 handlers) |
| `mybb_mcp/mybb_mcp/handlers/dispatcher.py` | Dictionary-based tool routing |
| `mybb_mcp/mybb_mcp/db/connection.py` | Database operations for templates, themes, plugins |
| `mybb_mcp/mybb_mcp/tools/plugins.py` | Plugin scaffolding templates and hooks reference |
| `mybb_mcp/mybb_mcp/config.py` | Configuration loading from .env |
| `.env` | Database credentials and paths (gitignored) |
| `TestForum/inc/plugins/` | Where plugins are installed |
| `TestForum/inc/languages/english/` | Language files for plugins |

## Documentation Reference

Comprehensive technical documentation lives in `/docs/wiki/`. Use these for detailed reference — they're kept in sync with the codebase.

### Quick Links

| Section | Index | What's There |
|---------|-------|--------------|
| **Getting Started** | [index](docs/wiki/getting_started/index.md) | Installation, quickstart tutorial, prerequisites |
| **MCP Tools** | [index](docs/wiki/mcp_tools/index.md) | All 94+ tools with parameters, return formats, examples |
| **Plugin Manager** | [index](docs/wiki/plugin_manager/index.md) | Workspace, deployment, PHP lifecycle, database schema |
| **Architecture** | [index](docs/wiki/architecture/index.md) | MCP server internals, disk sync, configuration |
| **Best Practices** | [index](docs/wiki/best_practices/index.md) | Plugin/theme development patterns, security |

### Complex Plugin Development (IMPORTANT)

For building production-quality plugins with multiple files, JavaScript, AJAX, Admin CP modules, and proper MyBB standards compliance, see the **[Plugin Development Guide](docs/wiki/best_practices/plugin_development.md)**.

**Key sections:**
- **MyBB Settings vs Config Files** — User-configurable options MUST use MyBB ACP settings, not config files
- **Complex Plugin Architecture** — Multi-file structure, directory organization, meta.json
- **JavaScript Integration** — Loading scripts via hooks, AJAX handlers with CSRF protection
- **Admin CP Modules** — Custom admin pages with proper permissions
- **Template Groups** — Organizing plugin templates for Admin CP visibility

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
├── mcp_tools/                  # Tool reference (94+ tools)
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
