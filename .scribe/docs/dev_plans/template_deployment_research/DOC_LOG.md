
# 📋 Documentation Update Log — template-deployment-research
**Maintained By:** Scribe
**Timezone:** UTC

> Track every structured documentation change. Use `log_type="doc_updates"` (or `--log doc_updates`).

---



## Entry Format
```
[EMOJI] [YYYY-MM-DD HH:MM:SS UTC] [Agent: <name>] [Project: template-deployment-research] Message text | doc=<doc_name>; section=<section_id>; action=<action_type>; [additional metadata]
```

**Required Metadata Fields:**
- `doc`: Document name (e.g., "architecture", "phase_plan", "checklist")
- `section`: Section ID being modified (e.g., "directory_structure", "phase_overview")
- `action`: Action type (`replace_section`, `append`, `status_update`, etc.)

**Optional Metadata Fields:**
- `file_path`: Full path to the Markdown file
- `changes_count`: Number of lines changed
- `review_status`: pending/approved/rejected
- `reviewer`: Reviewer name
- `jira_ticket`: Associated ticket number
- `confidence`: Confidence level for the change (0-1)
- `context`: Additional context about the change

---

## Tips for Documentation Updates
- Always specify which document section you're updating via `section=`.
- Include `action=` to indicate the type of modification.
- Reference checklist items or phases when applicable.
- Use `--dry-run` first when making structural changes.
- All documentation changes are automatically tracked and versioned.

---

## Entries will populate below
[✅] [2026-01-19 10:03:25 UTC] [Agent: Scribe] [Project: template-deployment-research] Created research report: RESEARCH_template_deployment_flow.md | action=create; agent_id=Scribe; agent_name=Scribe; doc=research_report; doc_name=RESEARCH_template_deployment_flow; document_type=research_report; file_path=/home/austin/projects/MyBB_Playground/.scribe/docs/dev_plans/template-deployment-research/research/RESEARCH_template_deployment_flow.md; file_size=2046; project_name=template-deployment-research; project_root=/home/austin/projects/MyBB_Playground; research_goal=Plugin template deployment flow; researcher=Scribe; section=; stage=research; timestamp=2026-01-19 10:03:25 UTC; title=Research Template Deployment Flow; priority=medium; log_type=doc_updates; content_type=log
