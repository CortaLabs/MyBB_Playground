
# 📋 Documentation Update Log — mybb-dev-protocol
**Maintained By:** Scribe
**Timezone:** UTC

> Track every structured documentation change. Use `log_type="doc_updates"` (or `--log doc_updates`).

---



## Entry Format
```
[EMOJI] [YYYY-MM-DD HH:MM:SS UTC] [Agent: <name>] [Project: mybb-dev-protocol] Message text | doc=<doc_name>; section=<section_id>; action=<action_type>; [additional metadata]
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
[✅] [2026-01-19 11:10:32 UTC] [Agent: Scribe] [Project: mybb-dev-protocol] Created research report: RESEARCH_test_20260119.md | action=create; agent_id=Scribe; agent_name=Scribe; doc=research_report; doc_name=RESEARCH_test_20260119; doc_type=research; document_type=research_report; file_path=/home/austin/projects/MyBB_Playground/.scribe/docs/dev_plans/mybb_dev_protocol/research/RESEARCH_test_20260119.md; file_size=2024; project_name=mybb-dev-protocol; project_root=/home/austin/projects/MyBB_Playground; research_goal=Testing manage_docs research creation; researcher=Scribe; section=; timestamp=2026-01-19 11:10:32 UTC; title=Research Test 20260119; priority=medium; log_type=doc_updates; content_type=log
[✅] [2026-01-19 11:10:33 UTC] [Agent: Scribe] [Project: mybb-dev-protocol] Created bug report: report.md | action=create; agent_id=Scribe; agent_name=Scribe; category=misc; component=testing; doc=bug_report; doc_type=bug; document_type=bug_report; file_path=/home/austin/projects/MyBB_Playground/docs/bugs/misc/2026-01-19_test_bug/report.md; file_size=1884; project_name=mybb-dev-protocol; project_root=/home/austin/projects/MyBB_Playground; reported_at=2026-01-19 11:10:33 UTC; section=; severity=low; slug=test_bug; timestamp=2026-01-19 11:10:33 UTC; title=Test bug report; priority=medium; log_type=doc_updates; content_type=log
[✅] [2026-01-19 11:10:33 UTC] [Agent: Scribe] [Project: mybb-dev-protocol] Created review report: REVIEW_REPORT_unknown_2026-01-19_1110.md | action=create; agent_id=Scribe; agent_name=Scribe; doc=review_report; doc_type=review; document_type=review_report; file_path=/home/austin/projects/MyBB_Playground/.scribe/docs/dev_plans/mybb_dev_protocol/REVIEW_REPORT_unknown_2026-01-19_1110.md; file_size=3010; project_name=mybb-dev-protocol; project_root=/home/austin/projects/MyBB_Playground; review_type=test; section=; stage=unknown; target=protocol docs; timestamp=2026-01-19 11:10:33 UTC; priority=medium; log_type=doc_updates; content_type=log
