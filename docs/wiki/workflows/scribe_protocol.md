# Scribe Protocol

The Scribe orchestration protocol for structured development in MyBB Playground.

## Overview

Scribe is used for tracking development progress, maintaining audit trails, and coordinating multi-agent workflows. This document covers the non-negotiable commandments and the standard PROTOCOL workflow.

**Repository Root:** `/home/austin/projects/MyBB_Playground`

**Key Principles:**
- Every significant action must be logged with reasoning
- Projects track feature/component development
- Multi-agent workflows follow defined phases
- All work is auditable and traceable

---

## Commandments (Non-Negotiable)

These rules are MANDATORY for all agents. Violations = rejection.

### Commandment #0: Always Rehydrate From Progress Log First

**Before ANY work:** Call `read_recent(n=5)` minimum, `query_entries` for targeted history.

**Why:** Progress log is source of truth. Skipping it causes hallucinated priorities and broken invariants.

**Sentinel mode (no project):** `read_recent`/`query_entries` operate on global scope — don't target a project path.

**Implementation:**
```python
# At start of every session
mcp__scribe__read_recent(agent="YourAgent", limit=5)

# For targeted history search
mcp__scribe__query_entries(
    agent="YourAgent",
    search_scope="all_projects",
    query="specific topic"
)
```

---

### Commandment #0.5: Infrastructure Primacy (No Replacement Files)

**Rule:** Work within existing system. NEVER create `enhanced_*`, `*_v2`, `*_new` files to avoid integration.

**Why:** Replacement files create tech debt, split code paths, destroy reliability.

**Comply:** Edit/extend/refactor existing components. If blocked, escalate with a plan — don't fork.

**Examples of violations:**
- ❌ Creating `parameter_validator_v2.py` instead of fixing `parameter_validator.py`
- ❌ Creating `enhanced_error_handler.py` instead of improving `error_handler.py`
- ❌ Creating `new_sync_service.py` instead of refactoring `sync_service.py`

**Correct approach:**
- ✅ Edit existing files directly
- ✅ Refactor in place with proper testing
- ✅ If major changes needed, create a plan and get approval first

---

### Commandment #1: Always Scribe (Log Everything Significant)

**Rule:** Use `append_entry` for EVERY significant action: investigations, decisions, code changes, test results, bugs, plan updates.

**If not Scribed, it didn't happen** — this is your audit trail.

**Orchestrators:** Always pass `project_name` to subagents so they log to the correct project.

**What to log:**
- Code changes (which files, what changed, why)
- Investigation findings
- Design decisions and rationale
- Test results (pass/fail, coverage)
- Bug discoveries
- Architecture choices
- Blockers and resolutions

**Minimum frequency:** Every 2-3 edits or ~5 minutes of work.

---

### Commandment #2: Reasoning Traces Required

**Every `append_entry` MUST include `reasoning` block:**

```python
reasoning = {
    "why": "goal / decision point",
    "what": "constraints / alternatives considered",
    "how": "method / steps / remaining uncertainty"
}
```

**Why:** Creates auditable decision record, prevents shallow "looks good" work.

**Review enforcement:** Missing why/what/how = reject.

**Example:**
```python
mcp__scribe__append_entry(
    agent="CoderAgent",
    message="Implemented authentication token validation",
    status="success",
    meta={
        "files": ["auth/validator.py"],
        "reasoning": {
            "why": "Prevent token reuse attacks identified in security audit",
            "what": "Considered time-based expiry vs single-use tokens; chose single-use for higher security despite performance cost",
            "how": "Added token invalidation on use, tested with 95% coverage, verified no performance regression <10ms"
        }
    }
)
```

---

### Commandment #3: MCP Tool Usage Policy

**If a tool exists, CALL IT DIRECTLY** — no manual scripting or substitutes.

**Log intent AFTER** the tool call succeeds or fails.

**Confirmation flags** (`confirm`, `dry_run`) must be actual tool parameters.

**File reads:** Use `read_file` (scan_only allowed) — no manual/implicit reads.

**Why:** Tool calls are the auditable execution layer. Simulating tools = untrusted output.

**Examples:**
- ✅ Call `mcp__scribe__read_file()` for file contents
- ❌ Use `cat` or shell commands to read files
- ✅ Call `mcp__scribe__manage_docs()` for document updates
- ❌ Manually edit `.scribe/` documents with Write tool

---

### Commandment #4: Structure, Cleanliness, Tests

**Follow repo structure:** Tests in `/tests` using existing layout.

**Don't clutter:** No random files, mirror existing patterns.

**When in doubt:** Search existing code first.

**Best practices:**
- Follow established directory conventions
- Tests go in `/tests` with proper naming (`test_*.py`)
- Don't create files in random locations
- Study existing code before implementing new patterns

---

## PROTOCOL Workflow (6 Phases)

All non-trivial development follows this 6-phase workflow:

```
SPEC → Research → Architect → Code → Review → Documentation
```

### Phase Overview

| Phase | Agent | Purpose |
|-------|-------|---------|
| **SPEC** | User + Orchestrator | Define what we're building, create Scribe project |
| **Research** | `mybb-research-analyst` (haiku) | Gather context, verify against code |
| **Architect** | `mybb-architect` (opus) | Create ARCHITECTURE_GUIDE.md, PHASE_PLAN.md, CHECKLIST.md |
| **Code** | `mybb-coder` (sonnet) | Execute bounded task packages |
| **Review** | `mybb-review-agent` (sonnet) | Validate against plan (≥93% to pass) |
| **Documentation** | Coder/Orchestrator | Fill README, update wiki, no TODOs at release |

### Phase 1: SPEC

**Participants:** User + Orchestrator

**Purpose:** Define what we're building and create the Scribe project for tracking.

**Deliverables:**
- Clear problem statement
- Success criteria
- Scribe project created
- Initial project log entry

**Example:**
```python
# Create project
mcp__scribe__set_project(
    agent="Orchestrator",
    name="feature-name",
    description="What this feature does",
    root="/home/austin/projects/MyBB_Playground",
    tags=["mybb", "feature"]
)

# Log project start
mcp__scribe__append_entry(
    agent="Orchestrator",
    message="Starting feature-name project",
    status="plan",
    meta={
        "reasoning": {
            "why": "User requested this feature",
            "what": "Creating new Scribe project for tracking",
            "how": "Will follow PROTOCOL workflow"
        }
    }
)
```

### Phase 2: Research

**Agent:** `mybb-research-analyst` (haiku model for speed/cost)

**Purpose:** Gather context, investigate existing code, verify assumptions.

**Deliverables:**
- `RESEARCH_*.md` documents
- Codebase analysis
- API/pattern discovery
- Context for architecture phase

**When to use haiku swarms:**
- Initial codebase exploration
- Gathering context from multiple files
- Pattern discovery across the codebase
- Producing research reports

**When to use stronger models:**
- Architecture decisions
- Code implementation
- Complex reasoning

### Phase 3: Architect

**Agent:** `mybb-architect` (opus model for critical decisions)

**Purpose:** Transform research into executable architecture and plans.

**Deliverables:**
- `ARCHITECTURE_GUIDE.md` — System design, component specs, integration points
- `PHASE_PLAN.md` — Task packages with execution order
- `CHECKLIST.md` — Verification criteria

**Critical rules:**
- **Sequential coders** if tasks touch same files; **concurrent** if different files
- **No hacky workarounds** — work within MyBB's systems
- **Documentation is mandatory** — README must have all sections filled
- **Plugin Manager workflow required** — never create files manually

### Phase 4: Code

**Agent:** `mybb-coder` (sonnet model for quality implementation)

**Purpose:** Execute bounded task packages from PHASE_PLAN.md.

**Deliverables:**
- Working code implementing specs
- Test coverage ≥90%
- Implementation reports
- Progress log entries

**Key principle:** Each coder gets ONE bounded task package with exact files, line ranges, and verification criteria.

### Phase 5: Review

**Agent:** `mybb-review-agent` (sonnet model)

**Purpose:** Validate implementation against plan.

**Pass criteria:** ≥93% grade

**What's reviewed:**
- Code matches architecture specs
- All checklist items complete
- Tests pass and coverage adequate
- Logging complete with reasoning
- No commandment violations

### Phase 6: Documentation

**Participants:** Coder/Orchestrator

**Purpose:** Complete all documentation before release.

**Deliverables:**
- README with all sections filled
- Wiki updates
- No TODO markers at release
- API documentation complete

---

## Multi-Coder Workflow (CRITICAL)

**NEVER send a single coder on a large scope.** Break work into bounded task packages and spawn multiple coders.

### Scope Size Guidelines

| Scope Size | Approach |
|------------|----------|
| 1-2 files, <100 lines | Single coder |
| 3-5 files, one component | Single coder with bounded scope |
| Multiple components | **Multiple coders** - one per component |
| Cross-cutting changes | **Sequential coders** - respect dependencies |

### Coder Scoping Rules

1. **Each coder gets ONE bounded task package** from PHASE_PLAN.md
2. **Task package specifies exact:**
   - Files to modify
   - Line ranges (if applicable)
   - Verification criteria
   - What NOT to touch
3. **Concurrent coders CANNOT have overlapping file scopes** - if two tasks touch the same file, they must be sequential
4. **Orchestrator waits** for each coder to complete before spawning coders that touch the same files

### Parallel vs Sequential

```
Different files, no dependencies → CAN be parallel
Same files touched            → MUST be sequential
Logical dependencies          → MUST be sequential (usually)
```

### Before Spawning Parallel Coders

Verify:
1. ✅ No file overlap between task packages
2. ✅ No logical dependencies (one task's output needed by another)
3. ✅ Each coder has complete context for their isolated scope

### Example: Multi-Coder Implementation

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

---

## Session Startup Protocol

Every session must follow this workflow:

```python
# 1. Activate project
mcp__scribe__set_project(
    agent="YourAgent",
    name="<project_name>",
    root="/home/austin/projects/MyBB_Playground"
)

# 2. Rehydrate context
mcp__scribe__read_recent(agent="YourAgent", limit=5)

# 3. Log session start (REQUIRED)
mcp__scribe__append_entry(
    agent="YourAgent",
    message="Starting <task>",
    status="info",
    meta={
        "task": "<task>",
        "reasoning": {
            "why": "...",
            "what": "...",
            "how": "..."
        }
    }
)
```

**Why this matters:**
- Project activation sets context for all subsequent operations
- Rehydration prevents duplicate work and broken assumptions
- Session logging creates audit trail

---

## Logging Guidelines

### Required Reasoning Block

**Every `append_entry` MUST include reasoning:**

```python
mcp__scribe__append_entry(
    agent="YourAgent",
    message="Completed file watcher implementation",
    status="success",
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

### Log Frequency

After each meaningful step (every 2-3 edits or ~5 minutes), and after:
- Investigations and discoveries
- Decisions made
- Tests run
- Errors encountered
- Task completions

### Status Types

| Status | Purpose | Example |
|--------|---------|---------|
| `info` | General progress notes | "Starting investigation of X" |
| `success` | Completed tasks/milestones | "Implemented feature Y, all tests pass" |
| `warn` | Concerns, potential issues | "Found deprecated API usage in Z" |
| `error` | Failed operations | "Test suite failed: connection timeout" |
| `bug` | Bug tracking | "Discovered race condition in file watcher" |
| `plan` | Planning decisions | "Decided to use approach A over B because..." |

---

## File Operations

### Reading Files

**Use `read_file` for file reads** (not shell reads like cat/head/tail):

```python
mcp__scribe__read_file(
    agent="YourAgent",
    path="mybb_mcp/server.py",
    mode="scan_only"  # or "chunk", "search", "line_range"
)
```

**Available modes:**
- `scan_only` — File structure and metadata
- `search` — Search for patterns with context
- `line_range` — Read specific line range
- `chunk` — Read file in chunks
- `page` — Paginated reading

### Managing Documents

**Use `manage_docs` for managed docs** in `.scribe/docs/dev_plans/<project>/`:

```python
mcp__scribe__manage_docs(
    agent="YourAgent",
    action="replace_section",
    doc_name="architecture",
    section="problem_statement",
    content="Updated content..."
)
```

**Common actions:**
- `create` — Create new document
- `replace_section` — Replace content by section anchor
- `append` — Append content to doc/section
- `apply_patch` — Apply unified diff patch
- `status_update` — Update checklist item status

---

## MyBB-Specialized Agents

For all MyBB development work, **prefer these specialized agents over the generic Scribe agents**. They have MyBB-specific knowledge baked in and know the Plugin Manager/disk sync workflows.

### PROTOCOL Workflow Agents (MyBB-Specialized)

| Step | Agent | Purpose | When to Use |
|------|-------|---------|-------------|
| 1 | `mybb-research-analyst` | Investigate MyBB internals using 94+ MCP tools | Analyzing plugins, hooks, templates before development |
| 2 | `mybb-architect` | Design plugins/templates/themes | Creating architecture for new MyBB features |
| 3 | `mybb-review-agent` | Review MyBB work for workflow compliance | Pre/post-implementation reviews |
| 4 | `mybb-coder` | Implement plugins/templates | Writing PHP, editing templates via disk sync |
| 5 | `mybb-review-agent` | Final validation and grading | Post-implementation verification |
| * | `mybb-bug-hunter` | Diagnose plugin/template issues | Debugging MyBB-specific problems |

### Deep Specialist Agents (Consultants)

| Agent | Expertise | When to Use |
|-------|-----------|-------------|
| `mybb-plugin-specialist` | Plugin lifecycle, hooks, settings, security patterns | Complex plugin architecture decisions, hook selection, debugging lifecycle issues |
| `mybb-template-specialist` | Template inheritance, Cortex syntax, disk sync, find_replace patterns | Template modification strategy, Cortex debugging, theme development |

### MyBB vs Generic Scribe Agents

| Use MyBB Agents When... | Use Generic Scribe Agents When... |
|-------------------------|-----------------------------------|
| Creating/modifying MyBB plugins | Working on MCP server Python code |
| Working with templates or themes | Working on non-MyBB infrastructure |
| Debugging plugin/template issues | General codebase exploration |
| Need MyBB-specific hook/API knowledge | Language-agnostic research |

### Model Selection Rules

| Phase | Model | Rationale |
|-------|-------|-----------|
| Research | **haiku** or sonnet | Cheap, fast, good for pattern discovery and context gathering |
| Architect | **opus** | Critical decisions require strongest reasoning |
| Coder | **sonnet** or opus | Implementation quality matters |
| Review | **sonnet** or opus | Needs to catch issues architect/coder missed |

---

## Creating a New Feature Project

Before starting a new feature:

```python
# 1. Create the project
mcp__scribe__set_project(
    agent="Orchestrator",
    name="feature-name",
    description="What this feature does",
    root="/home/austin/projects/MyBB_Playground",
    tags=["mybb", "relevant", "tags"]
)

# 2. Log the start
mcp__scribe__append_entry(
    agent="Orchestrator",
    message="Starting feature-name project",
    status="plan",
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

---

## Session Completion

Always log completion at end of significant work:

```python
mcp__scribe__append_entry(
    agent="YourAgent",
    message="Completed <task>: <summary>",
    status="success",
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
```

**Include in completion:**
- Summary of what was accomplished
- List of deliverables (files created/modified)
- Confidence score (0.0-1.0)
- Reasoning block explaining the work

---

## Quick Reference

### Essential Commands

```python
# Start session
set_project(agent="Agent", name="project", root="/path/to/repo")
read_recent(agent="Agent", limit=5)

# Log entry
append_entry(
    agent="Agent",
    message="...",
    status="success|info|warn|error|bug|plan",
    meta={"reasoning": {"why": "...", "what": "...", "how": "..."}}
)

# Read files
read_file(agent="Agent", path="...", mode="scan_only|search|line_range")

# Manage docs
manage_docs(
    agent="Agent",
    action="create|replace_section|append",
    doc_name="...",
    content="..."
)
```

### Status Types Quick Reference

- `info` — Progress notes
- `success` — Completions
- `warn` — Concerns
- `error` — Failures
- `bug` — Bug tracking
- `plan` — Planning

### Commandments Quick Check

1. ✅ Rehydrated from progress log?
2. ✅ No replacement files created?
3. ✅ Logging all significant actions?
4. ✅ Reasoning blocks in all logs?
5. ✅ Using MCP tools directly?
6. ✅ Following repo structure?

---

## See Also

- [Plugin Development](../best_practices/plugin_development.md) — MyBB plugin development guide
- [Disk Sync Architecture](../architecture/disk_sync.md) — Template/stylesheet sync system
