---
id: mybb_forge_v2-task-4-5-plugin-scaffold-templates
title: 'Task 4.5: Plugin Scaffold Templates Directory Implementation'
doc_name: task_4_5_plugin_scaffold_templates
category: implementation
status: draft
version: '0.1'
last_updated: '2026-01-19'
maintained_by: Corta Labs
created_by: Corta Labs
owners: []
related_docs: []
tags: []
summary: ''
---
# Task 4.5: Plugin Scaffold Templates Directory Implementation

## Overview
Implemented templates/ directory creation in plugin scaffold when `has_templates=True` is specified during plugin creation.

## Requirements Met
✅ Create empty `templates/` directory in plugin workspace when `has_templates=True`  
✅ Do NOT create any stub template files (user requirement)  
✅ Update meta.json to have `"templates": []` (empty array)  
✅ Add informative README.md explaining naming conventions and workflow  
✅ Update return dict to include templates/README.md in files_created  
✅ Add template creation guidance to next_steps  

## Files Modified

### 1. `plugin_manager/manager.py`

**Lines 310-338:** Added templates/ directory creation logic
- Creates `templates/` directory when `has_templates=True`
- Generates README.md with:
  - Naming convention: `{template_name}.html` → `{codename}_{template_name}`
  - Workflow explanation (db-sync auto-sync)
  - PHP usage example
  - Multi-theme support mention

**Lines 398-432:** Updated return statement
- Made `files_created` list dynamic
- Made `next_steps` list dynamic
- Conditionally includes templates/README.md when created
- Adds step 3: "Create template files in templates/"

## Implementation Details

### Directory Structure Created
```
plugin_manager/plugins/{visibility}/{codename}/
├── templates/           # Empty directory (has_templates=True only)
│   └── README.md       # Naming convention + workflow docs
├── inc/
│   ├── plugins/{codename}.php
│   └── languages/english/{codename}.lang.php
├── jscripts/
├── images/
├── meta.json           # Contains "templates": []
└── README.md
```

### README.md Content
The templates/README.md provides:
1. **Naming Convention**: Files named `{template_name}.html` become `{codename}_{template_name}` in MyBB
2. **Workflow**: Files auto-sync via db-sync watcher to database (sid=-2)
3. **Usage Example**: PHP code showing how to use templates in plugin
4. **Multi-theme Note**: Reference to `templates_themes/` for theme-specific templates

### String Formatting Fix
Initial implementation used `.format(codename=codename)` which caused `KeyError: 'template_name'` because the README contains `{template_name}` as literal text in examples.

**Solution:** Switched to f-string with escaped braces:
```python
templates_readme = f"""... {codename}_{{template_name}} ..."""
```

## Testing

### Test 1: Plugin with has_templates=True
✅ Creates templates/ directory  
✅ Creates templates/README.md with codename substitution  
✅ templates/ is empty (no stub files)  
✅ meta.json has `"templates": []`  
✅ files_created includes templates/README.md  

### Test 2: Plugin with has_templates=False
✅ Does NOT create templates/ directory  

## Integration Points

### Existing Infrastructure
- **meta.json schema** (`plugin_manager/schema.py`): Already includes `"templates": []` field at line 359
- **Plugin workspace** (`plugin_manager/workspace.py`): Creates MyBB-compatible directory structure
- **db-sync** (Phase 4.1-4.4): Will auto-sync .html files from templates/ to database

### Future Work (Phase 4.1-4.4)
This implementation prepares the workspace structure for:
1. **Phase 4.1**: PluginTemplateImporter will read .html files from templates/
2. **Phase 4.2**: FileWatcher will monitor workspace templates/ directory
3. **Phase 4.3**: SyncEventHandler will route plugin template changes
4. **Phase 4.4**: Queue processor will sync templates/ files to database

## Confidence Score: 0.95

**Reasoning:**
- All requirements met and verified via tests
- No stub files created (user requirement)
- Informative README guides developers
- Integration with existing code is clean
- Both positive and negative test cases passed

**Minor Uncertainty:**
- README wording could be refined based on user feedback
- Multi-theme support is mentioned but not yet implemented (Phase 5.3)

## Next Steps
1. ✅ Task 4.5 COMPLETE - scaffold creates templates/ directory
2. Proceed to Phase 4.6: Integration test for plugin template auto-sync
3. After Phase 4 complete: Implement multi-theme support (Phase 5.3)
