# CLAUDE.md - MyBB Playground

AI-assisted MyBB development toolkit providing MCP tools for Claude Code to interact with MyBB installations.

## Critical Rules (MUST READ FIRST)

**ATTENTION!!!!**
EDIT THE MCP_BRIDGE FROM `install_files` AND COPY IT INTO THE TESTFORUM.

NO AGENT SHOULD EVER EDIT ANYTHING INSIDE THE TESTFORUM.

### Database Access Prohibition

**ABSOLUTE PROHIBITION - NO EXCEPTIONS:**

**NEVER, EVER connect to the MyBB database directly.** This includes:
- ❌ NO direct MySQL/MariaDB connections
- ❌ NO raw SQL queries outside of MCP tools
- ❌ NO database clients or connection attempts
- ❌ NO pymysql, mysql-connector, or any DB libraries
- ❌ NO reading `.env` to get DB credentials for direct access

**ONLY use MCP tools to interact with MyBB:**
- ✅ Use `mybb_*` MCP tools exclusively
- ✅ All database operations go through the MCP server
- ✅ The MCP server handles all DB connections internally
- ✅ If an MCP tool doesn't exist for what you need, REQUEST ONE

**This applies to:**
- The main Claude Code orchestrator
- ALL subagents (research, architect, coder, review, etc.)
- ANY agent spawned for ANY purpose
- Testing, debugging, exploration - NO EXCEPTIONS

**Why this rule exists:**
- The MCP server manages connection pooling and safety
- Direct DB access bypasses cache invalidation
- Multiple connections cause race conditions
- This is a HARD BOUNDARY - violating it breaks the entire system

**If you need database access that an MCP tool doesn't provide:**
1. Document what you need
2. Ask the user
3. Wait for a new MCP tool to be created
4. DO NOT improvise with direct DB access

### Destructive Operations

**NEVER use destructive commands without explicit user confirmation:**
- `rm -rf` is BANNED. Period.
- `rm -r` requires explicit user approval
- Any directory deletion requires user confirmation
- If "delete and recreate" needed - ASK FIRST

**Before deleting anything:**
1. State exactly what will be deleted
2. Explain why deletion is necessary
3. WAIT for user confirmation
4. If any doubt, don't delete

**Extraction means EXTRACTION:**
When told to "extract" code from File A to File B:
1. Copy the code to File B
2. REMOVE the code from File A
3. Wire up imports/references
- End result: same total lines, just reorganized

### Core Orchestration Rules

- **ALWAYS** create or activate a Scribe project before starting work
- **DELEGATE** to subagents for complex tasks - don't browse files yourself
- **NEVER** send single coder on large scope - use bounded task packages
- **Subagents DO NOT commit** - orchestrator handles all commits at defined gates

### Infrastructure Primacy

**NEVER create replacement files:**
- No `*_v2`, `enhanced_*`, `*_new` files to avoid integration
- Edit/extend/refactor existing components
- If blocked, escalate with a plan - don't fork

### Orchestrator Logging (SCRIBE MORE)

**You must log decisions and progress with `append_entry`.** This is not optional.

**Log after:**
- User makes a decision in discussion
- You choose between approaches
- A subagent completes work
- A phase completes
- Something unexpected happens
- Every 2-3 significant actions

**Minimum logging:**
```python
mcp__scribe__append_entry(
    agent="Orchestrator",
    message="<what happened>",
    status="info",  # or success/warn/error/plan
    meta={
        "reasoning": {
            "why": "<goal or decision point>",
            "what": "<constraints or alternatives>",
            "how": "<method or next steps>"
        }
    }
)
```

**If you're not logging, you're doing it wrong.** The progress log is how we maintain context across sessions and audit our work. No excuses.

All agents can and should use **scribe_mcp_read_recent** to read the latest entries to the progress log.

### Template Discovery via Chrome DevTools (IMPORTANT)

**Use Chrome DevTools to identify which templates to edit.** MyBB injects HTML comments marking template boundaries:

```html
<!-- start: header_welcomeblock_member -->
...content...
<!-- end: header_welcomeblock_member -->
```

**Workflow:**
1. Navigate to the page in Chrome DevTools: `mcp__chrome-devtools__navigate_page(url="http://localhost:8022")`
2. Get the raw HTML source:
   ```python
   mcp__chrome-devtools__evaluate_script(function="() => document.documentElement.outerHTML")
   ```
3. Search the output for `<!-- start:` markers to find template names
4. Edit the corresponding template in workspace: `plugin_manager/themes/public/{theme}/templates/{Group}/{template}.html`
5. Sync changes: `mybb_workspace_sync(codename="theme_name", type="theme")`
6. Reload in Chrome DevTools to see changes instantly

**Why this matters:**
- MyBB has 900+ templates across 65 groups - grepping is slow and imprecise
- The rendered HTML shows exactly which templates compose each page element
- Template markers reveal the injection hierarchy (parent → child relationships)
- Workspace sync provides instant feedback loop - edit, sync, reload, verify

**Example: Finding where the `<body>` tag lives**
```
// In rendered HTML:
<body>
<!-- start: header -->
<div id="container">
```
This tells you `<body>` is in the page template (e.g., `index.html`), and `header` is injected inside it.

## Quick Reference

### Essential Commands

| Action | Command |
|--------|---------|
| Start MyBB server | `./start_mybb.sh` |
| Server status | `mybb_server_status()` |
| Run tests | `pytest tests/` |
| MCP connection check | `claude mcp get mybb` |

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `TestForum/` | MyBB installation (DO NOT edit core files) |
| `TestForum/inc/plugins/` | Installed plugins |
| `plugin_manager/plugins/` | Plugin workspace (edit here) |
| `plugin_manager/themes/` | Theme workspace |
| `mybb_sync/template_sets/` | Template files (disk sync) |
| `mybb_mcp/` | MCP server code |
| `docs/wiki/` | Documentation |

### Development Credentials

- **URL:** http://localhost:8022
- **Admin CP:** http://localhost:8022/admin/
- **Username:** admin
- **Password:** admin

### Environment

All config in `.env` at project root:
- `MYBB_ROOT=/home/austin/projects/MyBB_Playground/TestForum`
- `MYBB_URL=http://localhost:8022`

### Workspace Sync (Fast Development Iteration)

**Use `mybb_workspace_sync` for fast iteration during development.**

Hash-based change detection ensures only modified files sync - even with 976+ templates, only changed files are written.

```python
# Sync workspace changes TO database (default direction)
mybb_workspace_sync(codename="my_theme", type="theme")
mybb_workspace_sync(codename="my_plugin", type="plugin")

# Export FROM database to workspace (for existing themes/content)
mybb_workspace_sync(codename="my_theme", type="theme", direction="from_db")

# Preview what would sync
mybb_workspace_sync(codename="my_theme", type="theme", dry_run=True)

# Full reinstall when DB/lifecycle changes needed
mybb_workspace_sync(codename="my_theme", type="theme", full_pipeline=True)
```

| Mode | When to Use |
|------|-------------|
| **Incremental to_db** (default) | CSS, template, PHP file edits - only changed files sync |
| **Incremental from_db** | Export templates/stylesheets from existing DB theme to workspace |
| **Full Pipeline** | Settings changes, new hooks, DB schema changes |
| **Dry Run** | Preview file counts before syncing |

**Manifest files:** Each workspace has `.sync_manifest.json` tracking file hashes and DB datelines. These are gitignored and auto-managed.

**Rule:** Use incremental sync for routine edits. Use `full_pipeline=True` only when you've changed plugin settings, added new hooks, or modified `_install()`/`_activate()` functions.

## Skills & Commands

Invoke skills with `/skillname` in Claude Code.

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| `/mybb-dev` | MyBB development workflow | Starting any MyBB plugin/theme work - loads full MCP toolkit context |
| `/migrate-plugin` | Import external plugins | **IMPORTANT:** Use when importing third-party plugins into Plugin Manager workspace |

**Migration workflow:**
When importing an external plugin (from MyBB Mods site, GitHub, etc.):
1. Run `/migrate-plugin`
2. Follow the guided import process
3. Plugin will be set up in workspace with proper `meta.json`
4. Use `mybb_plugin_install()` to deploy

## Architecture Overview

### System Components

| Component | Purpose | Documentation |
|-----------|---------|---------------|
| MCP Server | 112 tools for MyBB interaction | [MCP Tools](docs/wiki/mcp_tools/index.md) |
| Plugin Manager | Workspace, deployment, PHP lifecycle | [Plugin Manager](docs/wiki/plugin_manager/index.md) |
| Disk Sync | Template/stylesheet file sync | [Disk Sync](docs/wiki/architecture/disk_sync.md) |
| Scribe | Development tracking & audit | [Scribe Protocol](docs/wiki/workflows/scribe_protocol.md) |

### MCP Server Structure

```
mybb_mcp/mybb_mcp/
├── server.py           # Orchestration (116 lines)
├── tools_registry.py   # 112 tool definitions
├── handlers/           # 15 handler modules
│   ├── dispatcher.py   # Dictionary-based routing
│   ├── templates.py    # Template operations
│   ├── themes.py       # Theme operations
│   ├── plugins.py      # Plugin lifecycle
│   └── ...
└── db/connection.py    # Database wrapper
```

### Template Inheritance

```
sid = -2  → Master templates (base, never delete)
sid = -1  → Global templates (shared)
sid >= 1  → Template set overrides (custom)
```

Custom templates override master. Always check for master first when writing.

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

## Task Routing

When working on specific tasks, read the appropriate documentation:

| Task Type | Primary Doc | What You'll Find |
|-----------|-------------|------------------|
| **Plugin development** | [Plugin Development](docs/wiki/best_practices/plugin_development.md) | Lifecycle, hooks, settings, templates |
| **Theme development** | [Theme Development](docs/wiki/best_practices/theme_development.md) | Disk sync, stylesheets, `set_default: true` |
| **Complex features** | [Scribe Protocol](docs/wiki/workflows/scribe_protocol.md) | Research → Architect → Code → Review |
| **MCP tool usage** | [MCP Tools Index](docs/wiki/mcp_tools/index.md) | 112 tools with parameters |
| **Getting started** | [Installation](docs/wiki/getting_started/installation.md) | Setup, prerequisites |

### Quick Decision Guide

- **Simple bug fix:** Implement directly with Scribe logging
- **New feature:** Follow Scribe PROTOCOL workflow
- **Plugin work:** Use Plugin Manager workflow (never create files directly)
- **Theme work:** Use disk sync workflow (edit files, watcher syncs)
- **Template changes:** Always via disk sync, never `mybb_write_template`

## Orchestration Protocol

You are the orchestrator. Your job is to coordinate subagents, not do all the work yourself.

### Project-First Workflow

**ALWAYS create or activate a Scribe project before starting work:**

```python
# New feature/fix
mcp__scribe__set_project(name="feature-name", root="/home/austin/projects/MyBB_Playground", ...)

# Existing project
mcp__scribe__set_project(name="existing-project", root="/home/austin/projects/MyBB_Playground")
```

- Every non-trivial task needs a project for tracking
- Pass the project name to ALL subagents in their prompts
- Check `mcp__scribe__list_projects()` to find existing projects

### Delegate, Don't Browse

**For complex exploration, spawn research agents - don't waste your context browsing files:**

| Situation | Action |
|-----------|--------|
| Need to understand a system | Spawn `mybb-research-analyst` (haiku) |
| Need to find where something is | Spawn `Explore` agent |
| Trivial lookup (specific file/function) | Use Read/Grep yourself |
| Multiple areas to investigate | Spawn **parallel research swarms** |

**Research swarms:** When you need lots of context, spawn multiple research agents in parallel:
```python
# Parallel research - one message, multiple Task calls
Task(subagent_type="mybb-research-analyst", model="haiku", prompt="Investigate area A...")
Task(subagent_type="mybb-research-analyst", model="haiku", prompt="Investigate area B...")
```

### Agent Decision Matrix

| Situation | Agent | Model | Notes |
|-----------|-------|-------|-------|
| Understand existing code | `mybb-research-analyst` | haiku | Fast, cheap context gathering |
| Design architecture | `mybb-architect` | opus | Critical decisions need strong reasoning |
| Pre/post-implementation review | `mybb-review-agent` | sonnet | Catches issues others miss |
| Implement bounded task | `mybb-coder` | sonnet | Quality implementation |
| Debug plugin/template issues | `mybb-bug-hunter` | sonnet | Autonomous debugging |
| Deep plugin guidance | `mybb-plugin-specialist` | sonnet | Consulting on hooks, lifecycle |
| Deep template guidance | `mybb-template-specialist` | sonnet | Consulting on Cortex, inheritance |

### MyBB-Specialized Agents (PREFERRED)

For all MyBB development work, **prefer these specialized agents over the generic Scribe agents**. They have MyBB-specific knowledge baked in and know the Plugin Manager/disk sync workflows.

#### PROTOCOL Workflow Agents

| Step | Agent | Purpose | When to Use |
|------|-------|---------|-------------|
| 1 | `mybb-research-analyst` | Investigate MyBB internals using 112+ MCP tools | Analyzing plugins, hooks, templates before development |
| 2 | `mybb-architect` | Design plugins/templates/themes | Creating architecture for new MyBB features |
| 3 | `mybb-review-agent` | Review MyBB work for workflow compliance | Pre/post-implementation reviews |
| 4 | `mybb-coder` | Implement plugins/templates | Writing PHP, editing templates via disk sync |
| 5 | `mybb-review-agent` | Final validation and grading | Post-implementation verification |
| * | `mybb-bug-hunter` | Diagnose plugin/template issues | Debugging MyBB-specific problems |

#### Deep Specialist Agents (Consultants)

| Agent | Expertise | When to Use |
|-------|-----------|-------------|
| `mybb-plugin-specialist` | Plugin lifecycle, hooks, settings, security patterns | Complex plugin architecture, hook selection, lifecycle debugging |
| `mybb-template-specialist` | Template inheritance, Cortex syntax, disk sync, find_replace | Template modification strategy, Cortex debugging, theme development |

#### MyBB vs Generic Scribe Agents

| Use MyBB Agents When... | Use Generic Scribe Agents When... |
|-------------------------|-----------------------------------|
| Creating/modifying MyBB plugins | Working on MCP server Python code |
| Working with templates or themes | Working on non-MyBB infrastructure |
| Debugging plugin/template issues | General codebase exploration |
| Need MyBB-specific hook/API knowledge | Language-agnostic research |

### Multi-Coder Workflow

**NEVER send a single coder on a large scope.** Break work into bounded task packages:

| Scope Size | Approach |
|------------|----------|
| 1-2 files, <100 lines | Single coder |
| 3-5 files, one component | Single coder with bounded scope |
| Multiple components | **Multiple coders** - one per component |
| Cross-cutting changes | **Sequential coders** - respect dependencies |

**Coder Scoping Rules:**
- Each coder gets ONE bounded task package from PHASE_PLAN.md
- Task package specifies exact files, line ranges, and verification criteria
- **Concurrent coders CANNOT have overlapping file scopes**
- Orchestrator waits for completion before spawning coders that touch same files

### Subagent Prompting

**Every subagent prompt MUST include:**
1. **Project name:** `Project: feature-name`
2. **Root path:** `Root: /home/austin/projects/MyBB_Playground`
3. **Clear scope:** What files, what changes, what NOT to touch
4. **Verification criteria:** How to know the task is complete
5. **Link to phase plan:** Subagents need the full context

### Commit Discipline

**Subagents DO NOT commit.** The orchestrator handles all commits at defined gates:

| Gate | What to Commit | Where | How |
|------|---------------|-------|-----|
| After Research | Scribe research docs | Parent repo | CLI `git commit` |
| After Architecture | Scribe architecture docs | Parent repo | CLI `git commit` |
| After Code Phase | Plugin code changes | Plugin repo | MCP `mybb_workspace_git_commit` |
| After Review | Final cleanup | Both if needed | CLI + MCP |

**Why orchestrator commits, not agents:**
- Scribe docs are in parent repo, not plugin workspaces
- Multiple agents would commit each other's work
- Orchestrator has full visibility for atomic, meaningful commits

### Using Haiku Swarms for Research

For context gathering, use **haiku model** with research agents:

```python
Task(
    subagent_type="mybb-research-analyst",
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
- Architecture decisions (opus)
- Code implementation (sonnet/opus)
- Complex reasoning tasks

### Example: Multi-Phase Coder Workflow

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

## Scribe Commandments (Non-Negotiable)

These rules are MANDATORY for all agents. Violations = rejection.

### #0 — Always Rehydrate From Progress Log First
- **Before ANY work:** Call `read_recent(n=5)` minimum, `query_entries` for targeted history
- **Why:** Progress log is source of truth. Skipping it causes hallucinated priorities and broken invariants
- **Sentinel mode (no project):** `read_recent`/`query_entries` operate on global scope

### #0.5 — Infrastructure Primacy (No Replacement Files)
- **Rule:** Work within existing system. NEVER create `enhanced_*`, `*_v2`, `*_new` files
- **Why:** Replacement files create tech debt, split code paths, destroy reliability
- **Comply:** Edit/extend/refactor existing components. If blocked, escalate with a plan

### #1 — Always Scribe (Log Everything Significant)
- **Rule:** Use `append_entry` for EVERY significant action
- **If not Scribed, it didn't happen** — this is your audit trail
- **Orchestrators:** Always pass `project_name` to subagents

### #2 — Reasoning Traces Required
- **Every `append_entry` MUST include `reasoning` block:**
  - `why`: goal / decision point
  - `what`: constraints / alternatives considered
  - `how`: method / steps / remaining uncertainty
- **Review enforcement:** Missing why/what/how = reject

### #3 — MCP Tool Usage Policy
- **If a tool exists, CALL IT DIRECTLY** — no manual scripting or substitutes
- **Log intent AFTER** the tool call succeeds or fails
- **File reads:** Use `read_file` — no manual/implicit reads
- **Why:** Tool calls are the auditable execution layer

### #4 — Structure, Cleanliness, Tests
- **Follow repo structure:** Tests in `/tests` using existing layout
- **Don't clutter:** No random files, mirror existing patterns
- **When in doubt:** Search existing code first

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

### Development Protocol (REQUIRED)

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
- **Work in the WORKSPACE**  — never editing files within TestForum, or using MCP to edit templates/stylesheets attached to plugins or themes.

For full details, see [Scribe Protocol](docs/wiki/workflows/scribe_protocol.md).

## MCP Tools & Gotchas

112 tools across 15 categories. Full documentation: [MCP Tools Index](docs/wiki/mcp_tools/index.md)

This section covers **CRITICAL gotchas** not in wiki documentation.

### Anti-Pattern: MCP Tools Are Not Importable

**MCP tools are NOT Python module functions. They are handlers dispatched through the MCP server.**

```python
# WRONG - causes AttributeError
import mybb_mcp
result = mybb_mcp.mybb_list_stylesheets(tid=tid)

# WRONG - module has no such attribute
from mybb_mcp.handlers.templates import handle_template_batch_write
result = handle_template_batch_write(...)

# CORRECT - use database methods via dependency injection
result = self.mybb_db.list_stylesheets(tid=tid)

# CORRECT - for MCP tool calls, use the MCP interface
mcp__mybb__mybb_list_stylesheets(tid=tid)
```

Non-handler code (like installer.py) must use `MyBBDatabase` methods directly, not MCP tool functions.

### Plugin Lifecycle Gotchas

**Lifecycle distinction:**
- `_install()` / `_uninstall()` - Database setup/teardown (settings, tables)
- `_activate()` / `_deactivate()` - Templates and runtime wiring

**Template update gotcha:**
`mybb_plugin_install()` alone does NOT update templates that already exist in the database.

For template changes, do a full reinstall cycle:
```python
mybb_plugin_uninstall(codename, remove_files=True)  # Remove from TestForum
mybb_plugin_install(codename)                        # Redeploy fresh
```

### Theme Installation Gotchas

**Theme installation order matters:**
1. Create theme record first (get new tid)
2. THEN deploy stylesheets to that tid
3. THEN set templateset property
4. NEVER hardcode `tid=1` (that's Master Style)

```python
# WRONG - goes to Master Style
deploy_stylesheets(tid=1)

# CORRECT
new_tid = create_theme(name="MyTheme", parent=1)
deploy_stylesheets(tid=new_tid)
```

**Templateset property required:**
Themes MUST have `templateset` in their properties or custom templates will not load:
```php
// Without templateset, MyBB only loads sid=-2 (master)
// With templateset=1, MyBB loads sid=-2, sid=-1, AND sid=1
```

### Cache Management

**Direct DB writes bypass cache invalidation.** Always use disk sync workflow, or manually rebuild:
```python
mybb_cache_rebuild('templates')  # After template changes
mybb_cache_rebuild('themes')     # After theme changes
```

**Protected caches - NEVER clear:**
- `version` - Contains MyBB version code (clearing breaks forum)
- `internal_settings` - Contains encryption keys

### Template Set IDs

| SID | Meaning | Usage |
|-----|---------|-------|
| `-2` | Master templates | Base templates, never delete |
| `-1` | Global templates | Shared across themes |
| `>= 1` | Template set overrides | Theme-specific customizations |

### Parameter Conventions

- **Forum/Thread/Post IDs:** Always integers, never strings
- **Template titles:** Exact match required (case-sensitive)
- **Codenames:** Lowercase with underscores (`my_plugin`)
- **Visibility:** `"public"` or `"private"` for workspace location

## Development Workflow

### Plugin Manager Workflow

**MANDATORY: Use Plugin Manager for all plugin development.**

1. **Create plugin:** `mybb_create_plugin(codename, name, description)`
2. **Edit in workspace:** `plugin_manager/plugins/public/{codename}/` or `private/`
3. **Deploy:** `mybb_plugin_install(codename)`
4. **Test in browser:** http://localhost:8022
5. **Iterate:** Full uninstall/reinstall cycle for changes

**NEVER:**
- Create workspace files directly (use `mybb_create_plugin`)
- Copy files to TestForum manually (use `mybb_plugin_install`)
- Edit files in TestForum (edit workspace, then deploy)

**Plugin workspace structure:**
```
plugin_manager/plugins/public/{codename}/
├── {codename}.php           # Main plugin file
├── meta.json                # Plugin metadata
├── templates/               # Template files (.html)
│   └── {codename}_*.html    # Syncs to sid=-2 (master)
├── inc/languages/english/   # Language files
│   └── {codename}.lang.php
└── jscripts/                # JavaScript files (deployed to TestForum)
```

### Disk Sync Workflow

**For template and stylesheet development:**

1. **Export templates:** `mybb_sync_export_templates("Default Templates")`
2. **Edit files in:** `mybb_sync/template_sets/`
3. **Start watcher:** `mybb_sync_start_watcher()`
4. **Changes auto-sync** to database

**ALWAYS edit via disk sync. NEVER use `mybb_write_template` during development.**

The file watcher monitors disk changes and syncs to the database automatically. This is the primary development workflow.

### Theme Development Workflow

**Themes live in workspace:** `plugin_manager/themes/public/{codename}/`

```
plugin_manager/themes/public/{codename}/
├── meta.json                # Theme metadata (name, version, author)
├── stylesheets/             # CSS files (synced to database)
│   ├── global.css
│   └── custom.css
├── templates/               # Template overrides (organized by group)
│   ├── Header Templates/
│   │   └── header.html
│   └── Footer Templates/
│       └── footer.html
└── jscripts/                # JavaScript (deployed to TestForum filesystem)
    └── theme-scripts.js
```

**Full workflow (new theme or major changes):**
```python
mybb_theme_uninstall(codename, remove_from_db=True)  # Clean slate
mybb_theme_install(codename, visibility="public", set_default=True)  # MUST set_default!
```

**Fast iteration workflow (CSS/template edits):**
```python
# Edit files in workspace, then sync only changes
mybb_workspace_sync(codename="my_theme", type="theme")  # Only changed files sync
```

**Export existing theme to workspace:**
```python
# Pull templates from DB to workspace (organized by groups)
mybb_workspace_sync(codename="my_theme", type="theme", direction="from_db")
```

**Theme install deploys:**
- Stylesheets → Database (mybb_themestylesheets table)
- Templates → Database (mybb_templates at theme's templateset sid)
- jscripts/, images/ → TestForum filesystem (tracked for clean uninstall)

**CRITICAL: `set_default=True` is mandatory.** Without it, the `templateset` property isn't set and custom templates won't load (MyBB only loads master templates).

### Language Files

**Location:** `inc/languages/english/{codename}.lang.php`
**Admin:** `inc/languages/english/admin/{codename}.lang.php`

**Format:**
```php
<?php
$l['myplugin_hello'] = 'Hello World';
$l['myplugin_settings'] = 'Plugin Settings';
```

**Usage:**
- PHP: `$lang->myplugin_hello`
- Templates: `{$lang->myplugin_hello}`

**Validation:**
```python
mybb_lang_validate(codename)      # Check for missing/unused keys
mybb_lang_generate_stub(codename) # Generate placeholders for missing
```

**ALWAYS maintain language files alongside code changes.**

### Git Hygiene

**Parent repo (MyBB Playground) - use CLI git:**
- Scribe docs (`.scribe/`)
- MCP server code (`mybb_mcp/`)
- Wiki documentation (`docs/wiki/`)

**Plugin/Theme repos - use MCP workspace git tools:**
```python
mybb_workspace_git_init(codename="my_plugin", visibility="private")
mybb_workspace_git_commit(codename="my_plugin", message="Add feature", visibility="private")
mybb_workspace_git_push(codename="my_plugin", visibility="private")

# For themes, add type="theme"
mybb_workspace_git_commit(codename="my_theme", type="theme", message="Update styles")
```

### Wiki Maintenance

**Mandatory documentation updates:**
- New MCP tools → add to `docs/wiki/mcp_tools/` appropriate category
- Changed tool behavior → update tool documentation
- New Plugin Manager features → update `docs/wiki/plugin_manager/`

**Outdated docs are worse than no docs.**

## Known Issues & Gotchas

### Concurrent Scribe Agent Sessions

**Session collision** occurs when multiple agents with the same name work on different Scribe projects within the same repository concurrently.

**Use scoped agent names:**
```python
# Safe - unique names
agent="CoderAgent-ProjectX"
agent="CoderAgent-ProjectY"

# Collision risk
agent="CoderAgent"  # on both projects simultaneously
```

Not affected: Sequential dispatches, different repositories, or single agent switching projects.

### MyBB Context

- MyBB is 15+ year old PHP forum software with mature but dated architecture
- Work within MyBB's hook/template system - don't try to modernize MyBB itself
- We're building tooling to make MyBB development easier and AI-accessible
- Set realistic expectations - some things are limited by MyBB's design

### DO NOT Edit Core MyBB Files

**Never modify files in `TestForum/` that are part of core MyBB.**

All customization must be through:
- Plugins (`TestForum/inc/plugins/`)
- Templates (via MCP tools or Admin CP)
- Stylesheets (via MCP tools or Admin CP)
- Language files (`TestForum/inc/languages/*/`)

Core files will be overwritten on MyBB upgrades. Hooks and plugins are the correct extension mechanism.

### Common Pitfalls

| Pitfall | Correct Approach |
|---------|------------------|
| Editing TestForum files directly | Edit workspace, deploy via Plugin Manager |
| Using `mybb_write_template` in development | Use disk sync workflow |
| Forgetting `set_default=True` for themes | Always include when installing themes |
| Single coder on large scope | Break into bounded task packages |
| Direct database connections | Use MCP tools exclusively |
| Creating `*_v2` replacement files | Edit/extend existing files |

## Key Files

| File | Purpose |
|------|---------|
| `mybb_mcp/mybb_mcp/server.py` | MCP server orchestration |
| `mybb_mcp/mybb_mcp/tools_registry.py` | 112 tool definitions |
| `mybb_mcp/mybb_mcp/handlers/` | Tool handler modules |
| `mybb_mcp/mybb_mcp/db/connection.py` | Database operations |
| `plugin_manager/installer.py` | Plugin/theme deployment |
| `.env` | Database credentials (gitignored) |

## Living Document

These sections are meant to be updated as we work. Add discoveries here.

### Active Scribe Projects

<!-- Update as projects are created/completed -->
Use `mcp__scribe__list_projects()` to see current projects in this repo.

Recent projects:
- `claude-md-rewrite` — This documentation overhaul
- `flavor-theme-rebuild` — Flavor theme with Alpine.js

### Recent Discoveries

<!-- Add new learnings here, move to permanent sections when stable -->

**2026-01-25 (Hash-based Sync):**
- SyncManifest class tracks file hashes (MD5) and DB datelines for change detection
- `direction="from_db"` exports templates organized by groups (Header Templates/, etc.)
- Manifest files (`.sync_manifest.json`) must be excluded from sync to avoid infinite loops
- `WORKSPACE_ONLY_PREFIXES` tuple catches manifest patterns via startswith()
- Sync output now shows "Files unchanged: N" for clarity (not just "Files synced: 0")

**2026-01-25 (Theme Manager v1):**
- Theme `set_default=True` parameter is mandatory for theme installation
- `templateset` property required in theme properties for custom templates to load
- Theme installer must deploy jscripts/images to TestForum filesystem, not just DB
- Stylesheets use `attachedto` field - empty string means "all pages"
- Template overrides go to theme's templateset sid, not master (sid=-2)

**2026-01-24:**
- MCP tools are not importable as Python functions - use MyBBDatabase methods
- Protected caches (`version`, `internal_settings`) must never be cleared
- PHP serialized properties need proper type handling (int vs string for templateset)

### Environment Notes

<!-- WSL quirks, version requirements, local setup notes -->
- **WSL2:** File watcher may need `MYBB_SYNC_DISABLE_CACHE=1` for reliability
- **PHP:** Requires 8.0+ (installed via `setup_dev_env.sh`)
- **Python:** Requires 3.10+ with venv
- **Port:** MyBB runs on 8022 by default (configurable in start_mybb.sh)

## Links

- [MyBB Plugin Docs](https://docs.mybb.com/1.8/development/plugins/)
- [MyBB Hooks List](https://docs.mybb.com/1.8/development/plugins/hooks/)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Claude Code MCP Docs](https://docs.anthropic.com/en/docs/claude-code/mcp)
