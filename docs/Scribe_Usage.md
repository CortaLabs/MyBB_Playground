# Scribe Usage (MyBB Playground)

This repo uses **Scribe** as the durable audit trail for planning, research, execution logs, and managed documentation.

If you are working in this repo, you should assume:
- Plans must be written and tracked (not just “in your head”).
- Important actions must be logged with reasoning.
- Architecture/phase/checklist docs must be maintained via `manage_docs` (not handwaved).

## Session Quickstart (Minimum)
```python
set_project(name="mybb-playground", root="/home/austin/projects/MyBB_Playground")
read_recent(n=5)
append_entry(
  message="Starting <task>",
  status="info",
  agent="Codex",
  meta={"task": "<task>", "reasoning": {"why": "...", "what": "...", "how": "..."}}
)
```

## Protocol (Canonical)
The repo workflow is defined here:
- `/.scribe/docs/dev_plans/mybb_dev_protocol/PROTOCOL_SPEC.md`

## manage_docs (Canonical Contract)
The authoritative `manage_docs` tool contract and examples live here:
- `/home/austin/.codex/skills/scribe-mcp-usage/references/manage_docs.md`

Common usage patterns:
- Update an anchored section: `action="replace_section"`
- Append incremental notes: `action="append"`
- Mark checklist items done with proof: `action="status_update"`

## Concurrent Agent Naming Session Isolation
**Problem:** Scribe session identity is effectively `{repo_root}:{transport}:{agent_name}`. If two concurrent sessions use the **same** `agent` name in the **same repo**, logs can collide or land in the wrong project.

**Best practice (required for parallel work):**
- If you run multiple Codex sessions in parallel, use distinct Scribe `agent` names per session, e.g.:
  - `Codex-MCP`, `Codex-Plugins`, `Codex-Docs`
  - or `Codex-<project_slug>`

**Not affected:** a single session switching projects sequentially.

## Notes
- This file is a lightweight “landing page” for humans and agents. The protocol/spec and the manage_docs contract are the sources of truth.
