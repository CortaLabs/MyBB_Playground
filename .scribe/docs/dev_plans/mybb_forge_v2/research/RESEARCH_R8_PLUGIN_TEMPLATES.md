
# 🔬 Research R8 Plugin Templates — mybb-forge-v2
**Author:** MyBB-ResearchAgent
**Version:** v1.0
**Status:** Complete
**Last Updated:** 2026-01-19 06:35:00 UTC

> Investigation of how existing MyBB plugins (dice_roller, cortex, invite_system) handle template definitions and proposed disk-first loading pattern for Phase 4 implementation.

---
## Executive Summary
<!-- ID: executive_summary -->
High-level overview of template handling patterns in existing MyBB plugins and proposed migration to disk-first loading.

**Primary Objective:** Investigate how dice_roller, cortex, and invite_system plugins define and load templates, then propose a disk-first approach where templates are read from workspace files instead of hardcoded PHP strings.

**Key Takeaways:**
- **Current Pattern:** All plugins with templates use hardcoded PHP string arrays in `_install()` function
- **Export Works:** mybb_sync already exports plugin templates to disk (e.g., `Dice Templates/`, `Invite System Templates/`)
- **Schema Ready:** meta.json has `templates: []` field for tracking template names
- **Migration Path Clear:** Propose `templates/` directory in plugin workspace + helper function to load `.html` files during installation
- **Confidence:** 0.95 - Strong evidence, clear implementation path


---
## Research Scope
<!-- ID: research_scope -->
**Research Lead:** MyBB-ResearchAgent

**Investigation Window:** 2026-01-19

**Focus Areas:**
- [x] How dice_roller plugin defines templates (hardcoded strings vs files)
- [x] How invite_system plugin defines templates (larger scale example)
- [x] How cortex plugin handles NO templates (baseline)
- [x] The _install() insertion pattern for all plugins
- [x] The _deactivate() cleanup pattern for all plugins
- [x] mybb_sync export structure for plugin templates
- [x] meta.json schema for template tracking
- [x] Feasibility of disk-first loading approach

**Dependencies & Constraints:**
- Plugins are deployed from `plugin_manager/` workspace to `TestForum/inc/plugins/`
- Templates must be inserted into MyBB `templates` table with sid=-2 (master)
- mybb_sync already handles template export/import (watcher sync works)
- Helper function approach needed for backward compatibility


---
## Findings
<!-- ID: findings -->

### Finding 1: Current Template Definition Pattern (Hardcoded PHP Strings)
- **Summary:** All plugins with templates use hardcoded PHP string arrays in `_install()` function. No plugins currently read templates from external files during installation.
- **Evidence:**
  - **dice_roller.php:125-152**: Single `$templates` array with 3 templates (dice_roller_result, dice_roller_result_crit, dice_roller_result_fail), each 10-20 lines of HTML
  - **invite_system.php:76-86**: Individual template creation with `$template = array()` pattern
  - **invite_system.php:111-370**: Multiple arrays (`$templates_to_add` with 5 templates, `$tree_templates` with 4 templates)
  - Both use: `$db->escape_string($template_html)` and `$db->insert_query('templates', $template_data)`
- **Confidence:** High (0.95)

### Finding 2: Template Lifecycle (Install/Deactivate)
- **Summary:** Standard pattern: foreach loop + insert_query on install, delete_query on deactivate. All templates use sid=-2 (master templates).
- **Evidence:**
  - **Install pattern** (dice_roller.php:154-164):
    ```php
    foreach($templates as $title => $template) {
        $template_data = array(
            'title'    => $title,
            'template' => $db->escape_string($template),
            'sid'      => -2,  // Master template
            'version'  => '',
            'dateline' => TIME_NOW
        );
        $db->insert_query('templates', $template_data);
    }
    ```
  - **Deactivate pattern** (dice_roller.php:180):
    ```php
    $db->delete_query('templates', "title LIKE 'dice_roller_%'");
    ```
  - **Invite system uses explicit name array** (invite_system.php:928-953):
    ```php
    $templates_to_delete = array('invite_register_field', ...);
    $templates_list = "'" . implode("','", $templates_to_delete) . "'";
    $db->delete_query('templates', "title IN ({$templates_list})");
    ```
- **Confidence:** High (0.95)

### Finding 3: mybb_sync Already Handles Plugin Templates
- **Summary:** Plugin templates ARE exported to mybb_sync directory structure. File watcher already syncs changes.
- **Evidence:**
  - **Disk location**: `mybb_sync/template_sets/Default Templates/Dice Templates/`
    - dice_roller_result.html (319 bytes)
    - dice_roller_result_crit.html (394 bytes)
    - dice_roller_result_fail.html (388 bytes)
  - **Invite system**: `mybb_sync/template_sets/Default Templates/Invite System Templates/` (13+ files)
  - **Naming convention**: `{Template Set}/{Group Name Templates}/{template_name}.html`
  - **Content matches**: disk files contain same HTML as hardcoded strings in PHP
- **Confidence:** High (0.95)

### Finding 4: meta.json Schema Supports Template Tracking
- **Summary:** Plugin metadata schema already has `templates: []` field for listing template names.
- **Evidence:**
  - **schema.py:116-122**:
    ```python
    "templates": {
        "type": "array",
        "items": {
            "type": "string"
        },
        "description": "Template names used by this plugin (plugin-specific)"
    }
    ```
  - **Current usage** (dice_roller/meta.json:38): `"templates": []` (empty, not populated)
  - **Current usage** (cortex/meta.json:43,50): `"templates": []`, `"has_templates": false`
- **Confidence:** High (0.95)

### Finding 5: Cortex Plugin Has NO Templates
- **Summary:** Not all plugins require templates. Cortex is a pure processing/hook plugin with only settings.
- **Evidence:**
  - **cortex.php:128-160**: `_install()` creates settings only, no template insertion
  - No `$db->insert_query('templates')` calls in entire plugin
  - Only creates cache directory and settings in _activate()/_install()
- **Confidence:** High (0.95)

### Additional Notes
- **Template Groups**: MyBB organizes templates into "groups" for Admin CP display (e.g., "Dice Templates", "Invite System Templates")
- **find_replace_templatesets()**: Some plugins inject code into CORE templates (invite_system modifies member_register template)
- **Duplicate Prevention**: invite_system checks for existing templates before insert: `$db->simple_select('templates', 'tid', "title='{$title}' AND sid IN (-2, -1)")`


---
## Technical Analysis
<!-- ID: technical_analysis -->

**Code Patterns Identified:**
1. **Hardcoded Template Strings** (Current Anti-Pattern)
   - Templates embedded in PHP as multi-line strings
   - Makes editing difficult (no syntax highlighting, must escape quotes)
   - Separates template content from version control diffs
   - Difficult to maintain for large templates (invite_system has 150+ line templates)

2. **Database Insertion Pattern** (Standard MyBB)
   - All plugins use `$db->insert_query('templates', $template_data)`
   - Template data structure:
     ```php
     array(
         'title'    => 'template_name',
         'template' => $db->escape_string($html),
         'sid'      => -2,      // Master template
         'version'  => '',
         'dateline' => TIME_NOW
     )
     ```
   - sid=-2 indicates master templates (shipped with plugin)
   - sid>=1 would be custom overrides per template set

3. **Template Group Organization**
   - Templates organized into "groups" for Admin CP
   - Group names are title case with spaces (e.g., "Dice Templates")
   - MyBB exports to disk using this structure

**System Interactions:**
- **plugin_manager → TestForum deployment**: Files copied during `mybb_plugin_install`
- **mybb_sync ↔ Database**: Bi-directional sync between disk and `mybb_templates` table
- **Admin CP**: Template editing triggers disk sync via watcher
- **Phase 4 Proposal**: `plugin_manager/plugins/{codename}/templates/ → _install() → Database`

**Proposed Disk-First Workflow:**
```
1. Developer creates: plugin_manager/plugins/dice_roller/templates/
   - dice_roller_result.html
   - dice_roller_result_crit.html
   - dice_roller_result_fail.html

2. meta.json updated: "templates": ["dice_roller_result", "dice_roller_result_crit", "dice_roller_result_fail"]

3. _install() uses helper function:
   $templates = load_plugin_templates(__DIR__);
   foreach($templates as $title => $html) {
       // Standard insertion pattern
   }

4. Templates deployed with plugin, no hardcoded strings needed
```

**Risk Assessment:**
- ✅ **Low Risk**: mybb_sync already handles plugin templates correctly
- ✅ **Low Risk**: Schema supports template tracking in meta.json
- ⚠️ **Medium Risk**: Backward compatibility - existing plugins have hardcoded strings
  - **Mitigation**: Helper function approach allows gradual migration
  - **Mitigation**: Scaffold generates both templates/ directory AND populates meta.json
- ⚠️ **Medium Risk**: Template group naming conventions
  - **Mitigation**: Auto-derive from plugin name (e.g., "dice_roller" → "Dice Roller Templates")
- ✅ **Low Risk**: Deployment complexity - installer already copies files recursively


---
## Recommendations
<!-- ID: recommendations -->

### Immediate Next Steps (Phase 4 Implementation)

#### 4.1 - Schema Update (CRITICAL - Do First)
- [ ] Update `plugin_manager/schema.py` to:
  - Change `templates` field from array of strings to array of objects
  - Add template metadata: `{"name": "template_name", "group": "Template Group", "description": "..."}`
  - Add `template_tracking` to workspace state for deployment verification
- [ ] Update `workspace.py` to validate template files exist when listed in meta.json

#### 4.2 - Scaffold Update
- [ ] Modify `mybb_create_plugin` to:
  - Create `templates/` directory in new plugin workspace
  - Generate sample template files if `has_templates=true`
  - Auto-populate meta.json `templates` array with generated template names
  - Auto-derive template group name from plugin codename

#### 4.3 - PHP Helper Function Template
- [ ] Create `plugin_manager/templates/plugin_helpers.php.template`
  - Function: `load_plugin_templates($plugin_dir)` returns array of template_name => html
  - Reads from `$plugin_dir/templates/*.html`
  - Auto-escapes with `$db->escape_string()`
  - Handles missing templates gracefully
- [ ] Include helper in new plugin scaffolds
- [ ] Document usage pattern in generated plugin README

#### 4.4 - Installer Update
- [ ] Modify `plugin_manager/installer.py`:
  - Copy `templates/` directory during deployment (if exists)
  - Track template files in deployment manifest
  - Verify all meta.json templates have corresponding .html files

#### 4.5 - Integration Test
- [ ] Create `tests/plugin_manager/test_disk_templates.py`
  - Test scaffold creates templates/ directory
  - Test helper function loads templates correctly
  - Test installer deploys template files
  - Test full lifecycle: scaffold → edit templates → deploy → verify in DB

### Long-Term Opportunities

#### Developer Experience Improvements
- **Template Editing**: Developers can edit .html files with syntax highlighting instead of PHP strings
- **Version Control**: Template changes show clean diffs, not escaped PHP strings
- **Reusability**: Templates can be shared between plugins or imported from libraries
- **Testing**: Template HTML can be linted/validated independently of PHP code

#### Migration Strategy for Existing Plugins
1. **Extract Templates Tool**: Create utility to extract hardcoded templates from existing plugins to disk files
2. **Auto-Population**: Scan plugin PHP for template arrays, generate templates/ directory + meta.json
3. **Backward Compatibility**: Keep supporting hardcoded strings for community plugins, but recommend disk-first for new plugins

#### mybb_sync Integration
- **Bi-directional Sync**: Allow developers to edit in mybb_sync OR plugin_manager/templates/
- **Template Diff Tool**: Show differences between workspace templates and deployed DB versions
- **Hot Reload**: Watch templates/ directory, auto-redeploy during development

#### Documentation & Best Practices
- Update wiki with disk-first template development guide
- Create video tutorial showing template workflow
- Document template group naming conventions
- Add template examples for common patterns (forms, lists, admin pages)


---
## Appendix
<!-- ID: appendix -->

### File References

**Plugins Analyzed:**
- `TestForum/inc/plugins/dice_roller.php` (694 lines) - Simple plugin with 3 templates
- `TestForum/inc/plugins/cortex.php` (305 lines) - No templates (baseline)
- `TestForum/inc/plugins/invite_system.php` (2676 lines) - Complex plugin with 9+ templates

**Workspace Structure:**
- `plugin_manager/plugins/public/dice_roller/meta.json` - Current schema (templates: [])
- `plugin_manager/plugins/public/cortex/meta.json` - has_templates: false
- `plugin_manager/schema.py:116-122` - Template field definition

**Disk Sync Structure:**
- `mybb_sync/template_sets/Default Templates/Dice Templates/*.html` (3 files)
- `mybb_sync/template_sets/Default Templates/Invite System Templates/*.html` (13+ files)

### Code Examples

**Current _install() Pattern (dice_roller.php:125-164):**
```php
$templates = array(
    'dice_roller_result' => '<span class="dice-roll">...</span>',
    'dice_roller_result_crit' => '<span class="dice-roll dice-crit-success">...</span>',
    'dice_roller_result_fail' => '<span class="dice-roll dice-crit-fail">...</span>'
);

foreach($templates as $title => $template) {
    $template_data = array(
        'title'    => $title,
        'template' => $db->escape_string($template),
        'sid'      => -2,
        'version'  => '',
        'dateline' => TIME_NOW
    );
    $db->insert_query('templates', $template_data);
}
```

**Proposed Disk-First Pattern:**
```php
// templates/ directory structure:
// plugin_manager/plugins/dice_roller/templates/
//   - dice_roller_result.html
//   - dice_roller_result_crit.html
//   - dice_roller_result_fail.html

require_once __DIR__ . '/plugin_helpers.php';
$templates = load_plugin_templates(__DIR__ . '/templates');

foreach($templates as $title => $template) {
    $template_data = array(
        'title'    => $title,
        'template' => $template, // Already escaped by helper
        'sid'      => -2,
        'version'  => '',
        'dateline' => TIME_NOW
    );
    $db->insert_query('templates', $template_data);
}
```

### Related Documents
- **PHASE_PLAN.md** - Phase 4 task packages for implementation
- **ARCHITECTURE_GUIDE.md** - Plugin Manager architecture overview
- **docs/wiki/plugin_manager/workspace.md** - Workspace structure documentation

---