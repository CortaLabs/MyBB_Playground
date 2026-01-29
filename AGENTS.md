# AGENTS.md - Codex Workflow for MyBB Playground

This repo was originally optimized for **Claude Code + MCP**. These instructions adapt the same workflow for **Codex CLI**, with explicit constraints (no subagents) and guardrails that prevent breaking the MyBB/Plugin Manager systems.

## Quick Reference (Do Not Delete)
This is the minimal “Codex can operate safely here” checklist. Keep this section intact; add below it.

Changes to the MCP require a full reload, always ask the USER to restart codex.

### 0) Codex Constraints (Read First)
- No subagents: Codex cannot spawn them here. Use separate `codex -p` invocations when you want parallel, focused work.
- Use Scribe MCP tools for reads/logs; avoid shell reads for file contents.
- Always rehydrate before work: `set_project` then `read_recent(n=10)` minimum; use `query_entries(...)` for targeted history when needed.
- **After every context compaction/reset:** Repeat `set_project` + `read_recent` — project context does not survive compaction.
- Never use destructive commands without explicit user confirmation (`rm -r`, `rm -rf` are banned by default).
- If a tool error occurs, fix the root cause before proceeding. Do not use workarounds.
- If an MCP tool exists for the operation, call the tool (don’t reimplement it with scripts/manual steps).
- This repo has multiple Scribe projects. If the correct project is already in recent logs or context, use it without asking. Only call `list_projects` when the project is genuinely unclear.
- **Initial Scribe project**: start with `mybb-playground` as the staging/default. This is where we connect first for new sessions.
- **Project continuity**: once `set_project` is called, keep using that active project for the rest of the work unless the user explicitly asks to switch.
- **When to split**: if the task becomes its own initiative, ask the user whether to create/switch to a new Scribe project (don’t assume).
- **No coding without a thorough plan.** Planning precedes implementation for all non-trivial work.
- **If you don’t understand the task or scope:** read the `mybb-dev` skill docs before proceeding (see “MyBB Skill Docs”). Ask clarifying questions if still unclear.
- **Single-agent execution:** Codex performs *all* protocol roles (SPEC/Research/Architect/Code/Review/Docs). We still keep the same gates and artifacts—just done by one agent.
- **Parallel Codex sessions:** if you run multiple Codex sessions concurrently, use distinct Scribe `agent` names to avoid session collisions (see the `scribe-mcp-usage` skill for full reference).

### 1) Scribe Session Quickstart (Required)
Every session must start with:
```python
set_project(name="mybb-playground", root="/home/austin/projects/MyBB_Playground")  # staging/default
read_recent(n=10)
append_entry(
  message="Starting <task>",
  status="info",
  agent="Codex",
  meta={"task": "<task>", "reasoning": {"why": "...", "what": "...", "how": "..."}}
)
```
Log after meaningful actions and at completion.

### 1.1) Mandatory Development Protocol (We Don’t Skip Steps)
This repo follows the Forge protocol:

> SPEC → Research → Architect → Code → Review → Documentation

You may do multiple phases yourself, but you must **respect the phase boundaries**:
- **SPEC**: clarify what “done” means and what is out of scope.
- **Research**: inspect the codebase (and/or prior Scribe docs) until you can make verified claims.
- **Architect**: write a thorough plan (scoped tasks + verification) before coding.
- **Code**: implement only what the plan specifies.
- **Review**: verify against the plan; don’t silently widen scope.
- **Documentation**: update wiki/docs when behavior or workflow changes.

Canonical reference: `/.scribe/docs/dev_plans/mybb_dev_protocol/PROTOCOL_SPEC.md`

### 1.1.0) Codex Mode (No Subagents)
Most upstream docs assume a subagent swarm. In **Codex CLI**, treat “agent roles” as *phases you execute yourself*:
- You still do SPEC → Research → Architect → Code → Review → Docs.
- You still produce the same artifacts (plans, checklists, doc updates).
- You still keep the same boundaries (no coding while still in Research/Architect).

### 1.1.1) Truth Principle (Verification Discipline)
Reality (actual code + tool output) > docs > assumptions.

- If you claim “X exists / works this way”, you must be able to point to verification (usually via `mcp__scribe__read_file` or a direct MCP tool result).
- If verifying would require broad scanning or exceeds the current task scope, **stop and ask** (don’t guess).

### 1.2) “No Code Without a Thorough Plan” (Definition)
A thorough plan is not “we’ll add feature X”. It must include:
- **Problem statement** and **success criteria**
- **Scope / Out of scope**
- **Files/areas to touch** (explicit list)
- **Exact operations/tools** (e.g., Plugin Manager vs disk sync vs MCP server changes)
- **Verification steps** (commands, MCP checks, or UI flows)
- **Rollback** (how to undo: uninstall plugin, revert templates, etc.)

Plan template (copy/paste):
```markdown
## Plan
**Goal:** ...
**Out of Scope:** ...

### Changes
1. ...
2. ...

### Files / Areas
- ...

### Verification
- [ ] ...
- [ ] ...

### Rollback
- ...
```

### 1.3) Planning Deliverables (Scribe + Chat)
For non-trivial work, plans must exist in two places:
- **Scribe docs** (durable): update/create `ARCHITECTURE_GUIDE`, `PHASE_PLAN`, `CHECKLIST` using `manage_docs`.
- **Chat plan** (execution tracking): use the `update_plan` tool so progress is visible and enforceable.

### 1.3.0) Task Packaging (How Plans Become Executable)
Plans should be broken into small task packages (even if you execute them yourself):
- 1–3 files per task
- ideally <500 lines changed per task
- explicit verification for each task

Task package template:
```markdown
## Task Package: <name>
**Scope:** ...
**Files to Modify:** ...
**Out of Scope:** ...

### Steps
1. ...
2. ...

### Verification
- [ ] ...
```

### 1.3.1) Minimum Logging Standard
We use Scribe logs as the audit trail. Minimum acceptable logging:
- **Start**: one `append_entry` stating task + why/what/how.
- **Plan**: one `append_entry` summarizing the plan and verification approach (or linking to Scribe docs).
- **Finish**: one `append_entry` stating what changed and how it was verified.

Recommended (for anything non-trivial):
- Log after investigations, decisions, tool runs, and verification (roughly every 2–3 meaningful steps).

For architecture-heavy work, follow the stronger `/.claude/agents/mybb-architect.md` discipline (frequent decision logs + doc creation via `manage_docs`).

### 1.4) manage_docs: Required Usage Pattern
Use Scribe `manage_docs` to create/update planning docs (don’t “handwave” doc creation).

Common actions:
- `replace_section` to update anchored sections
- `append` for incremental notes
- `status_update` to mark checklist items done with proof

Example (replace a section in architecture doc):
```python
manage_docs(
  agent="Codex",
  action="replace_section",
  doc_name="architecture",
  section="problem_statement",
  content="## Problem Statement\n..."
)
```

Example (create a scoped sub-plan doc):
```python
manage_docs(
  agent="Codex",
  action="create",
  doc_name="INVITE_SYSTEM_ARCHITECTURE_GUIDE",
  target_dir="architecture/invite_system",
  metadata={"doc_type": "custom", "body": "# Architecture Guide: Invite System\n\n..."}
)
```

### 2) File Operations Policy

| Operation | MUST Use | NEVER Use |
|-----------|----------|-----------|
| Read file contents | `scribe.read_file` | `cat`, `head`, `tail`, native `Read` for audited work |
| Multi-file search | `scribe.search` | `grep`, `rg`, `find`, Bash search |
| Edit files | `scribe.edit_file` | `sed`, `awk` |
| Create/edit managed docs | `scribe.manage_docs` | `Write`, `Edit`, `echo` |

- **Hook Enforcement:** Direct `Write`/`Edit` on `.scribe/docs/dev_plans/` paths is **blocked by a Claude Code hook** (exit code 2). You MUST use `manage_docs`.
- `edit_file` requires `read_file` on the same path first (tool-enforced). Defaults to `dry_run=True`.
- Native `Read`/`Edit` is acceptable for plugin workspace files (`plugin_manager/`, `mybb_sync/`) which are not Scribe-managed.
- Only edit within repo paths.

### 3) MyBB Ground Rules (Non-Negotiable)
- Do not edit core MyBB files in `TestForum/`.
- Plugin development must use Plugin Manager tools; do not copy files into `TestForum/` manually.
- Disk sync is the template/stylesheet workflow; edit files in `mybb_sync/` and let the watcher sync.
- For plugin template updates, do a full uninstall/reinstall cycle.

#### TestForum Is Disposable
- `TestForum/` is a **throwaway playground**; it should never contain important or irreplaceable data.
- If it breaks, prefer **reinstall/reset** over manual patching inside `TestForum/`.

#### Edit Outside TestForum (Default)
- Author plugins/themes in `plugin_manager/` and deploy via the Plugin Manager / MCP tools.
- Edit templates/stylesheets on disk via `mybb_sync/` (watcher syncs into the DB).
- Avoid “quick fixes” inside `TestForum/`—they don’t survive reinstall and break repeatable workflows.

#### Known Gaps (Future Work)
- Some activate/deactivate paths may still be cache-only and not fully routed through the PHP bridge.
- Longer-term: improve sync/deploy tooling so DB/schema/template changes trigger safe reinstall/redeploy workflows automatically.

### 4) Codex-Style Parallelism (No Subagents)
When you need focused research or isolated tasks, use additional Codex invocations:
```bash
codex -p "Research: find existing plugin manager docs for template sync and summarize."
codex -p "Investigate MCP server entrypoints and config loading in mybb_mcp."
```
For concurrent sessions, use distinct Scribe agent names (e.g., `Codex-Plugins`, `Codex-MCP`) to avoid log collisions.

### 5) Plugin Development Workflow (Summary)
1) Create plugin via MCP tool (never manual):
   - `mybb_create_plugin(codename, visibility)`
2) Deploy with lifecycle execution:
   - `mybb_plugin_install(codename)`
3) Update templates/files:
   - `mybb_plugin_uninstall(codename, remove_files=True)`
   - `mybb_plugin_install(codename)`
4) Validate language files:
   - `mybb_lang_validate(codename)`

**Lifecycle Standard (Important):**
- **Activate/Deactivate** handles templates (add/remove) and runtime wiring.
- **Install/Uninstall** handles DB setup/teardown (settings/tables).
- Use `mybb_plugin_deploy` for a full reinstall cycle when needed.

### 6) MCP Server Setup Checklist (No Coding)
Use scripts from repo root:
```bash
./setup_dev_env.sh
./start_mybb.sh
```
Basic MCP check (from Claude tooling):
```bash
claude mcp get mybb
```
If you need to validate DB access manually, use the Python snippet in `CLAUDE.md`.

### Codex MCP
Codex’s supported path is `codex mcp add`, which registers the server in your user Codex config (`~/.codex`). If you want “per-repo” isolation, use a unique server name (e.g. `mybb-playground`)—don’t rely on hidden wrappers.

Add MyBB MCP to Codex:
```bash
codex mcp add mybb -- bash -lc 'cd /home/austin/projects/MyBB_Playground && exec mybb_mcp/.venv/bin/python -m mybb_mcp.server'
codex mcp get mybb
```

### 7) When Unsure
- Read `CLAUDE.md` and `docs/wiki/` before altering workflows.
- Ask for confirmation before anything destructive or cross-cutting.

## How to Use MCP Tools (Practical Guide)
Use the MCP tools as the source of truth for MyBB operations. Prefer them over direct DB edits or manual file copies.

### Common Tasks → Correct Tools
- **Create/deploy plugin**: `mybb_create_plugin` → edit workspace → `mybb_plugin_install`
- **Update plugin templates**: `mybb_plugin_uninstall(remove_files=True)` → `mybb_plugin_install`
- **Edit core templates/styles**: edit `mybb_sync/` + `mybb_sync_start_watcher`
- **Check plugin state**: `mybb_plugin_status`, `mybb_plugin_is_installed`
- **Find hooks**: `mybb_list_hooks` or `mybb_hooks_discover`
- **Investigate errors**: `mybb_server_logs(errors_only=True)`
- **Check server**: `mybb_server_status`, `mybb_server_start`

### MCP Tool Reference
- Full tool list and parameters: `docs/wiki/mcp_tools/index.md`
- Plugin Manager guide: `docs/wiki/plugin_manager/index.md`

## MyBB Skill Docs (Must Know + Reference)
These are part of the `mybb-dev` skill and must be read/known when working in this repo. Reference them when making decisions or documenting behavior.

- `/.codex/skills/mybb-dev/LEARNINGS.md` — hard-won gotchas and critical workflow constraints (e.g., template reinstall rule, plugin scaffold requirements).
- `/.codex/skills/mybb-dev/QUICK_REFERENCE.md` — curated MCP tool patterns and workflows.
- `/.codex/skills/mybb-dev/LINKS.md` — canonical doc index (wiki, plugin manager, architecture, scribe).
- `/.codex/skills/mybb-dev/CORTEX.md` — template syntax rules and when to use Cortex vs PHP.

## Protocol Sources (Must Know + Reference)
When you need deeper detail than this file provides, these are the canonical sources to consult (in order):
- Forge phase protocol: `/.scribe/docs/dev_plans/mybb_dev_protocol/PROTOCOL_SPEC.md`
- Architect rules + compliance (manage_docs patterns, verification discipline): `/.claude/agents/mybb-architect.md`
- Plugin lifecycle/hook mastery (activate/deactivate vs install/uninstall): `/.claude/agents/mybb-plugin-specialist.md`
- Templates/disk sync/Cortex patterns: `/.claude/agents/mybb-template-specialist.md`
- manage_docs tool contract (authoritative signature + examples): `/home/austin/.codex/skills/scribe-mcp-usage/references/manage_docs.md`
- In-repo Scribe landing page (human-friendly pointer): `docs/Scribe_Usage.md`

Unless the user asks, do **not** pull in specialist agent docs for bug-hunting/coding/review swarms:
- `/.claude/agents/mybb-bug-hunter.md`
- `/.claude/agents/mybb-coder.md`
- `/.claude/agents/mybb-research-analyst.md`
- `/.claude/agents/mybb-review-agent.md`

## Critical Invariants (Don’t Rediscover These)
These rules exist because breaking them causes repeated, expensive failures.

### Plugin Manager (Source of Truth = Workspace)
- **Never** create plugin files manually: `mybb_create_plugin(...)` must run first (otherwise installs can fail and work can be lost).
- **Never** copy files into `TestForum/` by hand; deploy via `mybb_plugin_install`.
- **Template updates** for plugin templates require a full reinstall cycle: uninstall (remove files) → install.

### Plugin Lifecycle (What Goes Where)
- Hooks are registered at file load time (top of the plugin file), not inside `_activate()`.
- `_install()`/`_uninstall()` are for persistent DB/settings; `_activate()`/`_deactivate()` are for templates + template modifications.

### Templates / Disk Sync (Source of Truth = Filesystem)
- **Never** edit master templates (`sid=-2`) directly.
- **Never** use `mybb_write_template` during development; use disk sync (`mybb_sync_*` + watcher).
- **Never** edit templates in Admin CP for development work (creates drift vs disk).

### Cortex (Template Logic) Safety Rules
- Always use `<if ... then>` and close with `</if>`; expressions use `{= ... }`.
- Sanitize user-facing output (`htmlspecialchars_uni`, `my_date`, etc.). Do permission checks in PHP, not templates.

### Database / Schema Reality Checks
- Verify schema before coding against it (e.g., `mybb_db_query("DESCRIBE mybb_table")`).
- MyBB supports database transactions via `$db->write_link` (don’t invent manual rollback mechanisms by default).

### Language Hygiene (Be Careful With “Unused”)
- Use `mybb_lang_validate(codename)` to find missing keys, but treat “unused” reports as *high-noise*.
- Do not delete language strings based on validator output alone; verify usage in templates/Admin CP flows.

### Parallel Work Safety
- If running multiple Codex sessions in parallel, ensure **zero file overlap** (same-file edits lose work).

## Scribe Logging Expectations (Quick Recall)
- Log start, key actions, and completion.
- Use status: `info | success | warn | error | bug | plan`
- Include reasoning meta: why / what / how.

## 0) Hard Constraints (Non-Negotiable)
- **No subagents in Codex:** use separate `codex -p` runs for parallel, focused work.
- **No destructive operations without explicit user confirmation:**
  - `rm -rf` is banned.
  - `rm -r` requires explicit approval.
  - Do not delete/recreate folders to “fix” issues; investigate first.
- **No coding without a thorough plan.** If a plan doesn’t exist, create one before edits.
- **Do not edit core MyBB files under `TestForum/`.** All customization must be via plugins/templates/stylesheets/language packs.
- **Plugin Manager workflow is mandatory:** never manually copy plugin files into `TestForum/`.
- **Scribe discipline:** use Scribe MCP tools for file reads and progress logging (don’t “freestyle” file reads in shell).

## Claude.md Parity Rules (Codex Must Follow These Too)
- **Plugin Manager workflow is mandatory:** create via `mybb_create_plugin`, deploy via `mybb_plugin_install`; don’t manual-copy into `TestForum/`.
- **“Extraction” means extraction:** copy to new location, remove from source, and wire references.
- **Don’t “fix” infra by deleting:** investigate why the system doesn’t recognize something; ask before any deletion.
- **Avoid replacement files:** don’t create `enhanced_*`, `*_v2`, `*_new` forks to dodge integration.
- **Wiki accuracy is mandatory:** behavior changes require updating `docs/wiki/` (when we start making behavior changes).

## 1) Repo Reality (What This Ecosystem Is)
- `TestForum/` is the local MyBB install used for development (treat as deploy target, not a workspace).
- `plugin_manager/` is the canonical plugin/theme workspace and deploy mechanism.
- `mybb_sync/` is the disk-first template/stylesheet editing workflow (watcher syncs disk → DB).
- `mybb_mcp/` is the Python MCP server exposing MyBB tools (templates, themes, plugins, server orchestration, etc.).

## 2) Scribe Session Startup (Required)
Minimum correct start for any non-trivial work:
```python
set_project(name="mybb-playground", root="/home/austin/projects/MyBB_Playground")
read_recent(n=10)
append_entry(
  message="Starting <task>",
  status="info",
  agent="Codex",
  meta={"task": "<task>", "reasoning": {"why": "...", "what": "...", "how": "..."}}
)
```
Log after meaningful actions and at completion.

## 3) File Read / Write Rules
- Use `scribe.read_file` for file contents, `scribe.search` for multi-file search, `scribe.edit_file` for edits
- Direct `Write`/`Edit` on `.scribe/docs/dev_plans/` is **blocked by hook** — use `manage_docs`
- "Extraction" means move, not duplicate (copy-then-delete from source, then wire imports/references).
- Do not create replacement forks like `*_v2`, `enhanced_*`, `*_new` to avoid integration—extend existing components.

## 4) Plugin Development Workflow (Required)
Never create workspace files “by hand”; use the MCP tools:
- Create plugin: `mybb_create_plugin(codename, visibility)`
- Deploy (runs real PHP lifecycle): `mybb_plugin_install(codename)`
- Updating templates/files already in DB requires a full reinstall:
  - `mybb_plugin_uninstall(codename, remove_files=True)`
  - `mybb_plugin_install(codename)`
- Plugin templates live in the plugin workspace (not `mybb_sync/`), typically under `templates/` (and `templates_themes/<Theme Name>/` for theme-specific overrides). Follow the naming convention `{codename}_{template_name}`.
- Language hygiene:
  - `mybb_lang_validate(codename)`
  - `mybb_lang_generate_stub(codename)` (if needed)

Plugin Manager database (for “does this exist?” checks):
- `.plugin_manager/projects.db` at repo root

## Commit Discipline (When Asked)
Codex does **not** commit by default. If the user asks for commits, follow the repo's "orchestrator commit gates" concept:
- Parent repo commits (CLI `git commit`): Scribe docs, MCP server code, scripts, wiki.
- Plugin/theme repo commits (MCP): `mybb_workspace_git_commit(...)` inside the plugin/theme workspace (especially for private repos).

Rationale: Scribe docs live in the parent repo; private plugins/themes are nested repos and should be committed with plugin git tools.

## 5) Templates / Stylesheets: Disk Sync First
- Edit templates/stylesheets on disk in `mybb_sync/` (or plugin workspace template dirs) and rely on the watcher.
- Disk sync is for core/theme templates and styles. Plugin-owned templates live in the plugin workspace (not `mybb_sync/`).
- Avoid direct DB writes for templates during development (`mybb_write_template`, find/replace tools) unless explicitly doing a maintenance operation.

## 6) MCP + Local Dev Setup (No Coding)
Project config lives in `.env` at repo root (DB creds, MyBB root, URL).

ForgeConfig (project defaults + developer metadata):
- `.mybb-forge.yaml` (checked in) — defaults for scaffolding + sync behavior
- `.mybb-forge.env` (gitignored) — private remotes

Helpful env toggles:
- `MYBB_SYNC_DISABLE_CACHE=1` — disable template-set caching during development if you’re not seeing template changes

Common entrypoints:
```bash
./setup_dev_env.sh
./start_mybb.sh
./stop_mybb.sh
```

MyBB local access (TestForum):
- URL: http://localhost:8022/
- Admin: admin / admin

MCP server install (manual, project-scoped):
```bash
cd mybb_mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Claude Code MCP registration (if using Claude tooling):
```bash
claude mcp add --scope project --transport stdio mybb -- $(pwd)/.venv/bin/python -m mybb_mcp.server
claude mcp get mybb
```

## 7) Codex Parallelism Pattern (Replacing Subagents)
Use multiple `codex -p` runs with tightly scoped prompts. Example splits:
```bash
codex -p "Scan docs/wiki/plugin_manager/* and summarize the exact plugin lifecycle + deploy rules."
codex -p "Inspect mybb_mcp entrypoints and document how to run/register the MCP server."
codex -p "Draft README updates for Codex constraints (no subagents, Scribe rules, safe ops)."
```
If running multiple sessions concurrently, use distinct Scribe agent names to avoid collisions (e.g., `Codex-Plugins`, `Codex-MCP`).

## 8) When Unsure
- Read `CLAUDE.md` and `docs/wiki/` before changing workflows.
- Ask before anything destructive or cross-cutting.
