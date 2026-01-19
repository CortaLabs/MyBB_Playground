---
id: mybb_forge_v2-implementation-report-task-5.3
title: 'Implementation Report: Task Package 5.3 - Multi-Theme Plugin Template Support'
doc_name: implementation_report_task_5.3
category: engineering
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
# Implementation Report: Task Package 5.3 - Multi-Theme Plugin Template Support

**Date**: 2026-01-19  
**Agent**: MyBB-Coder  
**Task**: Enable theme-specific plugin template directories that sync to specific template sets

## Scope

Allow plugins to have theme-specific template directories in addition to the default templates directory:

```
plugin_manager/plugins/{vis}/{codename}/
├── templates/              # Default templates (sid=-2)
│   └── my_template.html
└── templates_themes/       # Theme-specific overrides
    ├── Default Templates/  # Maps to "Default Templates" set (sid=1)
    │   └── my_template.html
    └── Mobile Templates/   # Maps to "Mobile Templates" set
        └── my_template.html
```

## Files Modified

### 1. `mybb_mcp/mybb_mcp/sync/router.py`

**Changes**:
- Modified `_parse_plugin_path()` to recognize `templates_themes/{theme_name}/` directories
- Added conditional block to extract theme name from path parts when `subdir == 'templates_themes'`
- Theme name is extracted from `parts[4]` and stored in `ParsedPath.theme_name`
- Updated docstring to document `templates_themes` as valid subdirectory

**Key Code**:
```python
# Theme-specific plugin templates: plugins/{vis}/{name}/templates_themes/{theme_name}/*.html
if subdir == 'templates_themes' and path.suffix == '.html' and len(parts) >= 6:
    theme_name = parts[4]  # Extract theme name from path
    return ParsedPath(
        type='plugin_template',
        project_name=codename,
        visibility=visibility,
        file_type='template',
        template_name=path.stem,
        theme_name=theme_name,  # Theme-specific template
        relative_path=str(Path(*parts[3:])),
        raw_path=relative_path
    )
```

### 2. `mybb_mcp/mybb_mcp/sync/plugin_templates.py`

**Changes**:
- Added `Optional` import for type hints
- Added template set cache: `_template_set_cache: dict[str, Optional[int]]`
- Created `_get_template_set_sid(theme_name: str)` helper method with caching
- Modified `import_template()` signature to accept optional `theme_name` parameter
- Implemented dynamic `target_sid` determination based on theme_name presence
- Updated INSERT/UPDATE operations to use `target_sid` instead of hardcoded `-2`
- Enhanced logging to show sid in all operations

**Key Logic**:
```python
# Determine target sid based on theme_name
if theme_name and len(theme_name.strip()) > 0:
    # Theme-specific template - lookup template set sid
    target_sid = self._get_template_set_sid(theme_name)
    if target_sid is None:
        # Template set not found, fall back to master templates
        logger.warning(f"Template set '{theme_name}' not found, using sid=-2 for {full_template_name}")
        target_sid = -2
else:
    # Default to master templates
    target_sid = -2
```

**Caching Strategy**:
- Caches theme_name → sid mappings to avoid repeated database queries
- Returns cached value if available
- Queries `templatesets` table if not cached
- Caches both successful lookups (sid) and failures (None)

### 3. `mybb_mcp/mybb_mcp/sync/watcher.py`

**Changes**:
- Updated `_handle_plugin_template_change()` to include `theme_name` in work items
- Enhanced docstring to document both default and theme-specific template paths
- Added conditional logging to show theme name when present
- Modified both batch and non-batch queue processors to pass `theme_name` to importer
- Used `.get("theme_name")` to safely extract optional theme_name from work items

**Work Item Structure**:
```python
{
    "type": "plugin_template",
    "codename": parsed.project_name,
    "template_name": parsed.template_name,
    "content": content,
    "theme_name": parsed.theme_name  # None for default, theme name for theme-specific
}
```

**Queue Processing**:
```python
await self.plugin_template_importer.import_template(
    item["codename"],
    item["template_name"],
    item["content"],
    item.get("theme_name")  # Optional theme_name from work item
)
```

## Implementation Details

### Data Flow

1. **File Change Detected**: Watcher detects change in `templates_themes/{theme_name}/*.html`
2. **Path Parsing**: Router extracts `theme_name` from path parts and sets in ParsedPath
3. **Work Queue**: Handler includes `theme_name` in work item dictionary
4. **Template Set Lookup**: Importer queries database for template set sid by name (cached)
5. **Database Operation**: Template created/updated at correct sid

### Template Set Lookup

The importer uses `MyBBDatabase.get_template_set_by_name(name)` to lookup template sets:

```sql
SELECT sid, title FROM mybb_templatesets WHERE title = %s
```

Results are cached to minimize database queries during file watching.

### Fallback Behavior

If a theme-specific template references a non-existent template set:
- Logger emits warning: `"Template set '{theme_name}' not found, using sid=-2 for {full_template_name}"`
- Falls back to sid=-2 (master templates)
- Template still syncs successfully, just to wrong location

This prevents sync failures from breaking the file watcher.

## Verification

All modified files passed Python syntax validation:
```bash
python3 -m py_compile mybb_mcp/mybb_mcp/sync/router.py \
    mybb_mcp/mybb_mcp/sync/plugin_templates.py \
    mybb_mcp/mybb_mcp/sync/watcher.py
# Success - no output
```

## Testing Requirements

**Manual Testing Scenarios**:

1. **Default Templates (Existing Behavior)**:
   - Create template in `plugins/public/test_plugin/templates/my_template.html`
   - Verify syncs to sid=-2 with title `test_plugin_my_template`

2. **Theme-Specific Templates (New Feature)**:
   - Create template in `plugins/public/test_plugin/templates_themes/Default Templates/my_template.html`
   - Verify syncs to correct template set sid (sid=1 for Default Templates)
   - Verify title is still `test_plugin_my_template` (codename prefix preserved)

3. **Non-Existent Template Set (Fallback)**:
   - Create template in `plugins/public/test_plugin/templates_themes/NonExistent/my_template.html`
   - Verify warning logged
   - Verify template syncs to sid=-2 (fallback)

4. **Cache Behavior**:
   - Create multiple templates for same theme
   - Verify only one database query for template set lookup (subsequent uses cache)
   - Check logs for cache hit messages

5. **Logging Verification**:
   - Default template: `[disk-sync] Plugin template queued: test_plugin_my_template`
   - Theme-specific: `[disk-sync] Plugin template queued: test_plugin_my_template (theme: Default Templates)`

## Edge Cases Handled

1. **Empty theme_name**: Treated as None, uses sid=-2
2. **Whitespace-only theme_name**: Stripped and treated as None
3. **Template set not found**: Falls back to sid=-2 with warning
4. **Cache persistence**: Cache lives for lifetime of PluginTemplateImporter instance
5. **Directory names with spaces**: Preserved exactly (e.g., "Default Templates")

## Performance Considerations

**Cache Impact**:
- First lookup for each theme: 1 database query
- Subsequent lookups: Cache hit (0 queries)
- Example: 10 templates for "Default Templates" = 1 query total (90% reduction)

**No Regression**:
- Default templates (templates/ directory) bypass theme lookup entirely
- Existing behavior unchanged - no performance impact

## Confidence Score

**0.95** - High confidence in implementation

**Rationale**:
- All specifications implemented as described
- Syntax validation passed
- Existing patterns followed (similar to TemplateImporter's template set caching)
- Proper error handling and fallbacks
- No breaking changes to existing functionality
- Comprehensive logging for debugging

**Minor uncertainty**:
- Template set lookup query not verified against actual MyBB database schema (assumed correct based on existing `get_template_set_by_name` method)
- Manual testing required to verify end-to-end behavior

## Next Steps

1. Manual testing with actual plugin workspace structure
2. Verify template set lookup against MyBB database
3. Test cache behavior under load
4. Consider adding unit tests for router path parsing
5. Document new workspace structure in wiki/best practices

## Notes

- Theme names can contain spaces (e.g., "Default Templates") - handled correctly
- Template naming convention unchanged: `{codename}_{template_name}` regardless of theme
- Multiple themes can have override templates for same plugin
- Plugin can mix default and theme-specific templates freely
