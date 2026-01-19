# MyBB Forge Development Protocol

> SPEC → Research → Architect → Code → Review → Documentation

## Overview

This protocol defines the standard workflow for developing MyBB plugins, themes, and infrastructure within the MyBB Forge system. It ensures quality, auditability, and consistency across all development work.

## Protocol Phases

### Phase 1: SPEC (Specification)

**Who:** User + Orchestrator
**Purpose:** Define what we're building and why

**Steps:**
1. User describes the feature/fix needed
2. Orchestrator discusses approach, asks clarifying questions
3. Create Scribe project: `set_project(name="feature-name", ...)`
4. Write SPEC document capturing:
   - Problem statement
   - Goals and non-goals
   - High-level approach
   - Success criteria

**Output:** Scribe project created, SPEC documented in progress log

---

### Phase 2: Research

**Who:** Research Agent swarm (haiku model for speed)
**Purpose:** Gather all technical context needed

**Steps:**
1. Investigate existing codebase using MCP tools
2. Verify against actual code (never trust assumptions)
3. Utilize and build upon previous research
4. Document findings in research docs

**Create research docs:**
```python
manage_docs(
    action="create",
    doc_name="RESEARCH_<topic>_<YYYYMMDD>",
    metadata={"doc_type": "research", "research_goal": "..."}
)
```

**Output:** RESEARCH_*.md documents with verified findings

---

### Phase 3: Architect

**Who:** Architect Agent (opus model for complex reasoning)
**Purpose:** Transform SPEC + Research into implementation plan

**Steps:**
1. Read SPEC and all research documents
2. Verify research claims against code
3. Design implementation with small, scoped task packages
4. Create architecture documents

**Produces:**
- `ARCHITECTURE_GUIDE.md` - System design, component specs
- `PHASE_PLAN.md` - Ordered phases with task packages
- `CHECKLIST.md` - Verification criteria

**Task Package Requirements:**
- 1-3 files per task
- <500 lines changed
- Clear verification criteria
- No ambiguity

**Output:** Complete implementation blueprint

---

### Phase 4: Code

**Who:** Coder Agent swarm (sonnet model)
**Purpose:** Execute task packages

**Execution Rules:**
- **Sequential** if tasks touch same files
- **Concurrent** if tasks touch different files
- Each coder gets ONE bounded task package
- No freestyling - execute exactly what's specified

**Steps:**
1. Read assigned task package from PHASE_PLAN.md
2. Implement exactly as specified
3. Run verification criteria
4. Log completion with `append_entry`

**Output:** Working code matching specifications

---

### Phase 5: Review

**Who:** Review Agent (sonnet/opus model)
**Purpose:** Validate work against plan

**Review Types:**
- **Pre-implementation** (optional): Review architecture before coding
- **Post-implementation** (required): Review code against plan

**Grading Criteria:**
- Code matches specifications
- All verification criteria pass
- No hacky workarounds
- MyBB best practices followed
- Documentation complete

**Grade Threshold:** ≥93% to pass

**Output:** Review report with grades and feedback

---

### Phase 6: Documentation

**Who:** Coder or dedicated doc pass
**Purpose:** Complete all documentation

**Required:**
1. **README.md** - All TODO sections filled:
   - Overview (WHY this exists)
   - Features (bullet list)
   - Configuration (each setting documented)
   - Usage (how users interact)
   - Changelog (version history)

2. **Wiki updates** (if infrastructure work):
   - Update relevant wiki pages
   - Follow existing documentation patterns

3. **Code comments** (where non-obvious)

**Verification:**
- No `<!-- TODO:` markers remain in README
- All user-facing features documented

**Output:** Complete, polished documentation

---

## Plugin Manager Workflow

All plugin/theme development MUST use Plugin Manager:

```bash
# Create
mybb_create_plugin(codename, name, description, ...)

# Develop
Edit files in plugin_manager/plugins/{public,private}/{codename}/

# Deploy
mybb_plugin_install(codename)

# Test
Activate in MyBB Admin CP, test functionality

# Iterate
mybb_plugin_uninstall(codename)
# Make changes
mybb_plugin_install(codename)

# Delete (if needed)
mybb_delete_plugin(codename)  # Archives by default
```

**NEVER:**
- Create plugin files manually outside workspace
- Copy files directly to TestForum
- Edit TestForum files directly

---

## Git Hygiene for Private Plugins/Themes

Private plugins and themes are managed as **nested git repositories** - each plugin/theme has its own git repo independent of the main MyBB Playground repo.

### Workspace Structure

```
plugin_manager/
├── plugins/
│   ├── public/           # Tracked in parent repo (default plugins)
│   │   ├── cortex/       # Ships with playground
│   │   └── dice_roller/  # Ships with playground
│   └── private/          # Gitignored - nested repos
│       └── invite_system/
│           └── .git/     # Independent git repo
└── themes/               # Gitignored - nested repos
    └── my_theme/
        └── .git/         # Independent git repo
```

### Git Tools for Plugins/Themes

```bash
# Initialize git for a plugin
mybb_plugin_git_init(codename="my_plugin", visibility="private")

# Create GitHub repo (uses prefix from .mybb-forge.yaml)
mybb_plugin_github_create(codename="my_plugin", visibility="private", repo_visibility="private")
# Creates: github.com/YourOrg/mybb_playground_my_plugin

# Check status
mybb_plugin_git_status(codename="my_plugin", visibility="private")

# Commit changes
mybb_plugin_git_commit(codename="my_plugin", visibility="private", message="Add feature X")

# Push to remote
mybb_plugin_git_push(codename="my_plugin", visibility="private")

# Pull updates
mybb_plugin_git_pull(codename="my_plugin", visibility="private")
```

### Commit Discipline

**ORCHESTRATOR handles all commits. Subagents DO NOT commit.**

**Why:**
- Scribe docs (`.scribe/`) live in the parent repo, not plugin workspaces
- Research/Architect swarms would commit each other's work
- Orchestrator has full visibility to make atomic, meaningful commits

**Orchestrator Commit Gates:**

| Gate | What | Where | How |
|------|------|-------|-----|
| After Research Phase | Scribe research docs | Parent repo | CLI `git commit` |
| After Architecture Phase | Scribe architecture docs | Parent repo | CLI `git commit` |
| After Code Phase | Plugin code changes | Plugin repo | MCP `mybb_plugin_git_commit` |
| After Review Approval | Final cleanup | Both if needed | CLI + MCP |

**Commit Message Format:**
```
<type>: <description>

Types: feat, fix, docs, refactor, test, chore
```

**Examples:**
```
feat: Add invite code validation
fix: Handle expired codes gracefully
docs: Update README with configuration
refactor: Extract validation to separate class
test: Add unit tests for InviteCode class
chore: Update dependencies
```

### Parent Repo vs Plugin Repos

| Repository | Commit Method | What's Tracked |
|------------|---------------|----------------|
| MyBB Playground (parent) | CLI: `git commit` | Scribe docs, MCP server, install scripts, wiki, default plugins |
| Private plugins | MCP: `mybb_plugin_git_commit` | Plugin PHP code, templates, language files |
| Private themes | MCP: `mybb_plugin_git_commit` | Theme stylesheets, templates |

**Optional `files` parameter:** Use `mybb_plugin_git_commit(..., files=[...])` to commit only specific files when needed.

**Rule:** Orchestrator uses CLI git for parent repo, MCP git tools for plugin/theme repos.

### .mybb-forge.yaml Configuration

```yaml
# GitHub settings
github:
  repo_prefix: "mybb_playground_"  # Prefix for all plugin/theme repos

# Default plugins (tracked in parent repo, NOT nested repos)
default_plugins:
  - cortex
  - dice_roller
```

The gitignore is auto-managed by `ForgeConfig.sync_gitignore()` based on `default_plugins`.

---

## Template/Stylesheet Workflow

**Source of Truth:** Filesystem (`mybb_sync/`)

```bash
# Export from DB to disk (first time)
mybb_sync_export_templates("Default Templates")

# Edit files on disk
# Watcher auto-syncs to DB

# For plugins: templates in workspace
plugin_manager/plugins/{visibility}/{codename}/templates/*.html
```

---

## manage_docs Reference

| doc_type | Purpose | Auto-location |
|----------|---------|---------------|
| `research` | Technical investigation | `research/` |
| `bug` | Bug reports | `docs/bugs/<category>/` |
| `review` | Review reports | auto |
| `agent_card` | Agent report cards | auto |
| `custom` | Custom docs | specify `target_dir` |

**Examples:**
```python
# Research
manage_docs(
    action="create",
    doc_name="RESEARCH_auth_flow_20260119",
    metadata={"doc_type": "research", "research_goal": "Analyze authentication"}
)

# Bug
manage_docs(
    action="create",
    metadata={
        "doc_type": "bug",
        "category": "logic",
        "slug": "null_pointer",
        "severity": "high",
        "title": "Null pointer in handler",
        "component": "auth"
    }
)

# Custom
manage_docs(
    action="create",
    doc_name="MY_DOC",
    metadata={"doc_type": "custom", "body": "# Content", "target_dir": "custom/"}
)
```

---

## Quality Standards

### No Hacky Workarounds
- Work within MyBB's hook/template system
- Use proper MyBB APIs (`$db->`, `$mybb->`, etc.)
- Follow MyBB security patterns (escape, verify CSRF)

### MyBB Best Practices
- Prefix everything with codename
- Use language files for user-facing strings
- Templates use `{$variable}` syntax
- Settings accessible via `$mybb->settings['codename_setting']`

### Documentation Standards
- README must have no TODOs at release
- Changelog maintained from v1.0.0
- All settings documented
- Usage examples provided

---

## Future Considerations

- **Versioning System:** Semantic versioning, release packaging
- **Legacy Plugin Import:** Import community plugins into workspace
- **Export/Distribution:** Package plugins for MyBB Mods site

---

*Protocol Version: 1.0.0*
*Last Updated: 2026-01-19*
