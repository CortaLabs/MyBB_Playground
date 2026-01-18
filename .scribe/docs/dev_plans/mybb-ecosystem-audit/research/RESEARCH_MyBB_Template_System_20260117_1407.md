# 🔬 MyBB Template System Deep Dive — mybb-ecosystem-audit
**Author:** ResearchAgent-MyBB
**Version:** v1.0
**Status:** Complete
**Last Updated:** 2026-01-17 14:08 UTC

> **Research Goal:** Comprehensive analysis of MyBB's template system architecture, syntax, compilation, caching mechanisms, and MCP integration gaps to inform downstream development and tool enhancement.

---
## Executive Summary
<!-- ID: executive_summary -->

**Primary Objective:** Document MyBB 1.8's template system architecture to identify MCP tool gaps and provide technical reference for plugin/theme development.

**Key Takeaways:**
- MyBB uses **eval()-based template rendering** with PHP variable interpolation syntax (`{$variable}`)
- **3-tier inheritance system** (sid: -2=master, -1=global, N=custom) enables template customization
- **No template-level conditional syntax** - logic handled via PHP-side conditional template selection
- **Batch caching** via `$templatelist` declarations optimizes database queries
- **Version tracking** enables detection of outdated custom templates after MyBB upgrades
- **MCP tools provide basic CRUD** but lack advanced features (batch operations, diff/merge, validation, variable introspection)

**Research Confidence:** 0.94 (High) - All findings verified through direct code analysis and database inspection.

---
## Research Scope
<!-- ID: research_scope -->

**Research Lead:** ResearchAgent-MyBB
**Investigation Window:** 2026-01-17
**Target Location:** `/home/austin/projects/MyBB_Playground/TestForum/`

**Focus Areas:**
- [x] Template variable syntax and available variables
- [x] Template conditionals and logic mechanisms
- [x] Template groups and organization
- [x] Master templates vs custom templates (inheritance)
- [x] Template versioning system
- [x] How templates are compiled/cached
- [x] Dynamic template loading
- [x] Template editing via code (programmatic API)
- [x] Gaps in MCP template tools

**Dependencies & Constraints:**
- Read-only analysis (no modifications to MyBB installation)
- MyBB 1.8 codebase (version codes observed: 1800-1838 range)
- Database schema: MySQL-based with mybb_* table prefix

**Files Analyzed:**
- `inc/class_templates.php` (core template engine)
- `inc/adminfunctions_templates.php` (manipulation functions)
- `admin/modules/style/templates.php` (ACP interface)
- `inc/functions_post.php` (template usage example)
- `mybb_mcp/mybb_mcp/server.py` (MCP tool definitions)

---
## Findings
<!-- ID: findings -->

### Finding 1: Eval()-Based Template Engine with PHP Variable Syntax
**File:** `inc/class_templates.php:64-124`

**Summary:** Templates use standard PHP variable interpolation (`{$variable_name}`) and are rendered via `eval()` execution.

**Evidence:**
```php
// Template rendering flow (class_templates.php)
function render($template, $eslashes=true, $htmlcomments=true) {
    return 'return "'.$this->get($template, $eslashes, $htmlcomments).'";';
}

// Usage pattern (from plugins/functions)
$output = eval($templates->render('template_name'));
```

**Technical Details:**
- Templates fetched from database as HTML strings with `{$var}` placeholders
- `render()` wraps template in `return "...";` for eval() execution
- Eval context inherits all PHP global variables in scope
- `addslashes()` preprocessing enables proper string escaping

**Confidence:** High (0.95) - Verified through code inspection and plugin examples

---

### Finding 2: 3-Tier Template Inheritance System
**Files:** `class_templates.php:39-104`, Database: `mybb_templates.sid`

**Summary:** Templates use sid (set ID) for inheritance: -2 (master), -1 (global), positive integers (custom sets).

**Evidence:**
```sql
-- Query pattern from class_templates.php:49
SELECT title, template FROM templates
WHERE title IN (...)
AND sid IN ('-2', '-1', '{$theme['templateset']}')
ORDER BY sid ASC
```

**Inheritance Rules:**
1. Query fetches templates matching: master (-2), global (-1), and active set
2. `ORDER BY sid ASC` means later results override earlier ones
3. Custom templates (sid > 0) take precedence over global (-1) over master (-2)
4. Missing custom templates automatically fall back to global/master

**Database Schema:**
```
mybb_templates:
  - tid (PK, auto_increment)
  - title (varchar) - template identifier
  - template (text) - HTML content
  - sid (FK) - template set ID
  - version (varchar) - MyBB version code
  - status (varchar) - currently unused
  - dateline (int) - Unix timestamp
```

**Confidence:** High (0.98) - Verified via database schema queries and code analysis

---

### Finding 3: PHP-Side Conditionals, Not Template-Level Logic
**File:** `inc/functions_post.php:345-351`

**Summary:** MyBB templates lack conditional syntax (no `<if>` tags). Logic implemented via PHP selecting template variants.

**Evidence:**
```php
// Conditional template selection pattern
if($post['useronline'] == 1) {
    eval("\$post['onlinestatus'] = \"".$templates->get("postbit_online")."\";");
} elseif($post['useronline'] == 0 && $post['away'] == 1) {
    eval("\$post['onlinestatus'] = \"".$templates->get("postbit_away")."\";");
} else {
    eval("\$post['onlinestatus'] = \"".$templates->get("postbit_offline")."\";");
}
```

**Template Variant Pattern:**
- Multiple templates for different states: `postbit_online`, `postbit_away`, `postbit_offline`
- PHP code decides which variant to render based on conditions
- No template parser or conditional language

**Implications:**
- Templates are pure presentation (HTML + variables)
- All business logic remains in PHP
- Plugin modifications require PHP code changes, not template syntax extensions

**Confidence:** High (0.91) - Confirmed via grep searches and code pattern analysis

---

### Finding 4: Batch Caching via $templatelist Declarations
**Files:** `moderation.php:14`, `portal.php:34`, `class_templates.php:39-54`

**Summary:** Pages declare needed templates in `$templatelist` string for batch preloading, reducing database queries.

**Evidence:**
```php
// Page declaration pattern (moderation.php:14)
$templatelist = "changeuserbox,loginbox,moderation_delayedmoderation_custommodtool,...";

// Batch fetch implementation (class_templates.php:49)
$query = $db->simple_select(
    "templates",
    "title,template",
    "title IN (''$sql) AND sid IN ('-2','-1','".(int)$theme['templateset']."')",
    array('order_by' => 'sid', 'order_dir' => 'asc')
);
```

**Performance Strategy:**
1. Single comma-separated string declares all needed templates
2. `cache()` method parses list and executes one multi-row query
3. Templates stored in `$this->cache[]` array for reuse
4. Uncached templates (not in `$templatelist`) fetched individually via `get()`

**Debug Mode:** `$mybb->debug_mode` tracks uncached template fetches in `$this->uncached_templates[]`

**Confidence:** High (0.96) - Verified by tracing cache() implementation and page declarations

---

### Finding 5: Version Tracking for Upgrade Detection
**Files:** `admin/modules/style/templates.php:1294-1343`, Database: `mybb_templates.version`

**Summary:** Templates store MyBB version code (integer format) to detect outdated custom templates after upgrades.

**Evidence:**
```sql
-- Outdated template detection query (templates.php:1298)
SELECT t.tid, t.title, t.sid, t.version
FROM templates t
LEFT JOIN templates m ON (m.title=t.title AND m.sid=-2 AND m.version > t.version)
WHERE t.sid > 0 AND m.tid IS NOT NULL
```

**Version Code Format:**
- `1820` = MyBB 1.8.20
- `1838` = MyBB 1.8.38
- Integer comparison: custom.version < master.version → outdated

**Auto-Versioning:**
```php
// New templates auto-stamped with current version (adminfunctions_templates.php:82)
$insert_template = array(
    "version" => $mybb->version_code,
    "dateline" => TIME_NOW
);
```

**Confidence:** High (0.93) - Confirmed via database queries and admin code analysis

---

### Finding 6: Template Groups for Organization
**Database:** `mybb_templategroups`, **File:** `admin/modules/style/templates.php:360-827`

**Summary:** Templates organized by prefix-based groups (e.g., `postbit_*` belongs to `postbit` group).

**Evidence:**
```sql
-- Template groups sample
SELECT gid, prefix, title, isdefault FROM mybb_templategroups;
gid | prefix      | title                      | isdefault
--- | ----------- | -------------------------- | ---------
1   | calendar    | <lang:group_calendar>      | 1
3   | forumbit    | <lang:group_forumbit>      | 1
6   | index       | <lang:group_index>         | 1
```

**Organization Rules:**
- `prefix` field matches template title prefix
- Templates with `postbit_*` pattern belong to `postbit` group
- Groups used for ACP organization and bulk operations
- Language files provide human-readable titles (`<lang:group_name>`)

**Confidence:** High (0.94) - Verified via database queries and admin interface code

---

### Finding 7: Template Variables from Global Scope
**File:** `inc/functions_post.php:20-22`

**Summary:** Templates executed via eval() inherit all PHP global variables declared in scope.

**Evidence:**
```php
// Typical global declaration pattern (functions_post.php)
global $db, $altbg, $theme, $mybb, $postcounter, $profile_fields;
global $titlescache, $page, $templates, $forumpermissions, $attachcache;
global $lang, $ismod, $inlinecookie, $inlinecount, $groupscache, $fid;
```

**Common Template Variables:**
- `$mybb` - Settings object and current user data (`$mybb->settings[]`, `$mybb->user[]`)
- `$lang` - Language strings (`$lang->welcome_guest`)
- `$theme` - Active theme data (`$theme['name']`, `$theme['templateset']`)
- `$post`, `$thread`, `$forum` - Entity-specific data
- `$db` - Database connection object
- `$templates` - Template engine instance

**Documentation Gap:** No centralized variable reference - developers must inspect PHP source to discover available variables.

**Confidence:** Medium (0.88) - Pattern confirmed via code analysis, but variable availability varies by page/context

---

### Finding 8: Programmatic Template Editing via find_replace_templatesets()
**File:** `inc/adminfunctions_templates.php:23-94`

**Summary:** Plugin-based template modifications use `find_replace_templatesets()` function for regex-based find/replace operations.

**Evidence:**
```php
function find_replace_templatesets($title, $find, $replace, $autocreate=1, $sid=false, $limit=-1)
{
    // 1. Find existing custom templates and apply regex replace
    $query = $db->simple_select("templates", "tid, sid, template",
        "title = '".$db->escape_string($title)."' AND (sid{$sqlwhere})");

    $new_template = preg_replace($find, $replace, $template['template'], $limit);
    $db->update_query("templates", $updated_template, "tid='{$template['tid']}'");

    // 2. Auto-create custom versions from master if autocreate=1
    if($autocreate != 0) {
        // Fetches master template, applies modification, creates custom versions
        // for template sets that don't have custom version yet
    }
}
```

**Capabilities:**
- Regex-based find/replace across templates
- Auto-creates custom templates from master when modifications applied
- Selective targeting by sid (all sets or specific set)
- Tracks template inheritance (avoids duplicate custom versions)
- Version stamping with `$mybb->version_code`

**Plugin Usage Pattern:**
```php
// Typical plugin install/uninstall pattern
function myplugin_install() {
    find_replace_templatesets("header", "#\\{\\$pm_notice\\}#", "{$my_notice}\\n{$pm_notice}");
}
```

**Confidence:** High (0.92) - Complete function analysis with usage patterns verified

---

### Finding 9: MCP Tool Gaps
**File:** `mybb_mcp/mybb_mcp/server.py:50-98`

**Summary:** Existing MCP tools provide basic template CRUD but lack advanced features for professional development workflows.

**Current MCP Tools:**
1. `mybb_list_template_sets` - List template sets (no parameters)
2. `mybb_list_templates` - Filter by sid or search term
3. `mybb_read_template` - Read template content (shows master + custom if exists)
4. `mybb_write_template` - Create/update template (handles inheritance automatically)
5. `mybb_list_template_groups` - List template groups for organization

**Identified Gaps:**

#### **Gap 1: No Batch Template Operations**
- **Missing:** Bulk read/write multiple templates in single call
- **Use Case:** Plugin installation needs to create/modify 10+ templates
- **Current Workaround:** 10+ individual MCP calls (slow, verbose)
- **Proposed Solution:** Add `mybb_batch_write_templates(templates: list[{title, template, sid}])`

#### **Gap 2: No Template Diff/Merge Tools**
- **Missing:** Compare master vs custom templates, detect modifications
- **Use Case:** Understanding what customizations exist before upgrade
- **Current Workaround:** Manual read + external diff tool
- **Proposed Solution:** `mybb_diff_template(title, sid)` showing changes from master

#### **Gap 3: No find_replace_templatesets() Exposure**
- **Missing:** Programmatic regex find/replace functionality
- **Use Case:** Plugin development (most common template modification pattern)
- **Current Workaround:** Manual read → regex in agent → write back (error-prone)
- **Proposed Solution:** `mybb_find_replace_template(title, find_regex, replace, autocreate, sid)`

#### **Gap 4: No Version/Outdated Template Detection**
- **Missing:** Identify custom templates older than master versions
- **Use Case:** Pre-upgrade audit, template maintenance
- **Current Workaround:** Complex SQL queries via mybb_db_query
- **Proposed Solution:** `mybb_list_outdated_templates(sid?)` showing upgrade candidates

#### **Gap 5: No Template Variable Introspection**
- **Missing:** Discover available variables for a given template context
- **Use Case:** Template authoring assistance, documentation generation
- **Current Workaround:** Manual PHP code inspection (no automated way)
- **Proposed Solution:** `mybb_analyze_template_context(template_name)` scanning usage patterns

#### **Gap 6: No Template Validation**
- **Missing:** Syntax validation before writing templates
- **Use Case:** Catch malformed templates (unclosed braces, syntax errors) before deployment
- **Current Workaround:** Write → test in browser → debug → rewrite
- **Proposed Solution:** `mybb_validate_template(template_content)` checking syntax

#### **Gap 7: No Template Dependency Tracking**
- **Missing:** Identify which templates include/reference other templates
- **Use Case:** Understanding template relationships for safe modifications
- **Current Workaround:** Text search across all templates
- **Proposed Solution:** `mybb_trace_template_deps(title)` showing inclusion tree

**Priority Ranking:**
1. **Critical:** find_replace_templatesets() exposure (most common operation)
2. **High:** Batch operations (performance/UX improvement)
3. **High:** Diff/merge tools (upgrade workflows)
4. **Medium:** Outdated template detection (maintenance)
5. **Low:** Variable introspection (nice-to-have for authoring)
6. **Low:** Validation (minimal impact, templates are lenient)
7. **Low:** Dependency tracking (advanced use case)

**Confidence:** High (0.97) - Gap analysis based on verified MCP tool inventory and MyBB capabilities

---

## Technical Analysis
<!-- ID: technical_analysis -->

### Code Patterns Identified

**Pattern 1: Template Rendering Flow**
```
1. Page defines $templatelist = "template1,template2,..."
2. templates->cache($templatelist) batch-fetches from database
3. Code execution reaches render point
4. templates->get('template_name') retrieves from cache
5. templates->render() wraps in return "..."; statement
6. eval($templates->render('template_name')) executes and returns HTML
7. Result assigned to variable or concatenated to output
```

**Pattern 2: Template Inheritance Query**
```sql
-- Single template fetch with fallback
SELECT template FROM templates
WHERE title='header' AND sid IN ('-2', '-1', '5')
ORDER BY sid DESC LIMIT 1
-- Returns: custom (sid=5) OR global (sid=-1) OR master (sid=-2)

-- Batch cache with override
SELECT title, template FROM templates
WHERE title IN ('header','footer','postbit') AND sid IN ('-2', '-1', '5')
ORDER BY sid ASC
-- Later rows (higher sid) overwrite earlier rows in $cache[] array
```

**Pattern 3: Plugin Template Modification**
```php
// Installation: Add code to template
function plugin_install() {
    require_once MYBB_ROOT."inc/adminfunctions_templates.php";
    find_replace_templatesets(
        "header",                    // Template to modify
        "#\\{\\$pm_notice\\}#",      // Regex to find
        "{$my_notice}\\n{$pm_notice}", // Replacement
        1,                           // Auto-create custom templates
        false                        // Apply to all sets
    );
}

// Uninstallation: Remove code from template
function plugin_uninstall() {
    find_replace_templatesets(
        "header",
        "#".preg_quote("{$my_notice}\n")."#",
        "",
        0  // Don't create new templates, just modify existing
    );
}
```

### System Interactions

**Database → Template Engine:**
- Templates stored in `mybb_templates` table (text field, can be large)
- Batch queries optimize performance via IN clauses
- Cache stored in PHP memory ($templates->cache array)
- No persistent cache layer (file/memcache) - database per request

**Template Engine → PHP Application:**
- Bidirectional: templates access globals, PHP prepares template variables
- `eval()` execution context is identical to calling scope
- Security: templates can execute arbitrary PHP if injected (admin-only write access critical)

**Admin CP → Database:**
- Direct INSERT/UPDATE queries for template modifications
- No validation layer (trusts admin input)
- Cache refresh not automatic (may require manual clearing)

### Risk Assessment

**Risk 1: eval() Security Implications**
- **Severity:** High (but mitigated)
- **Description:** Templates executed via eval() can run arbitrary PHP code
- **Mitigation:** Template write access restricted to admin accounts only
- **Residual Risk:** Compromised admin account = full code execution
- **Recommendation:** MCP tools should enforce authentication/authorization

**Risk 2: No Template Syntax Validation**
- **Severity:** Low
- **Description:** Malformed templates (unclosed braces, syntax errors) accepted
- **Impact:** Runtime errors, broken pages (not security issue)
- **Mitigation:** Testing/staging environments catch errors before production
- **Recommendation:** Add optional validation to MCP write operations

**Risk 3: Template Version Drift**
- **Severity:** Medium
- **Description:** Custom templates not updated after MyBB upgrades may break
- **Impact:** Missing features, incompatible variable references
- **Current Detection:** Admin CP "Find Updated Templates" feature
- **Recommendation:** MCP tool to automate outdated template detection

**Risk 4: Plugin Template Conflict**
- **Severity:** Medium
- **Description:** Multiple plugins modifying same template = conflicts
- **Impact:** Last-install-wins, plugin uninstall may corrupt template
- **Example:** Plugin A and B both modify `header` template, uninstalling A removes B's changes
- **Recommendation:** Template modification logging/audit trail (not currently tracked)

**Risk 5: No Template Backup/Rollback**
- **Severity:** Low-Medium
- **Description:** Template modifications have no built-in undo/history
- **Impact:** Mistakes require manual restoration or database rollback
- **Recommendation:** MCP tools could implement template versioning/snapshots

---

## Recommendations
<!-- ID: recommendations -->

### Immediate Next Steps

**For MCP Tool Development:**
1. **[ ] Implement find_replace_templatesets() wrapper** (Priority: Critical)
   - Direct exposure of existing MyBB function
   - Enables plugin development workflows
   - Low implementation complexity

2. **[ ] Add mybb_batch_write_templates()** (Priority: High)
   - Accepts array of template objects
   - Reduces MCP call overhead for bulk operations
   - Transactional safety (all-or-nothing)

3. **[ ] Create mybb_diff_template()** (Priority: High)
   - Shows master vs custom differences
   - Returns unified diff format
   - Essential for upgrade workflows

**For Documentation:**
4. **[ ] Create Template Variable Reference Guide**
   - Document common variables by template context
   - Extract from PHP code analysis
   - Assist template authors

5. **[ ] Document Template Inheritance Rules**
   - Clarify sid precedence and fallback behavior
   - Explain autocreate mechanism
   - Provide troubleshooting guide for inheritance issues

### Long-Term Opportunities

**Template System Enhancements:**
- **Template compilation cache:** Pre-compile templates to PHP files (avoid eval() overhead)
- **Template inheritance visualization:** Graphical tool showing master/global/custom relationships
- **Template dependency graph:** Map which templates include/reference others
- **Variable type hinting:** IDE-like autocomplete for template authors
- **Template linting:** Automated best practice checks

**MCP Tool Suite Evolution:**
- **Template testing framework:** Automated rendering tests with mock data
- **Template migration tools:** Bulk update helpers for MyBB upgrades
- **Template conflict detection:** Identify overlapping plugin modifications
- **Template performance profiler:** Identify slow/complex templates

**Developer Experience:**
- **Hot reload:** File-based template sync (already implemented via `mybb_sync_*` tools)
- **Template preview:** Render with sample data without deploying
- **Template search:** Full-text search across template content
- **Template analytics:** Track usage frequency, identify unused templates

---

## Appendix
<!-- ID: appendix -->

### Database Schema Reference

```sql
CREATE TABLE mybb_templates (
  tid int(10) unsigned NOT NULL AUTO_INCREMENT,
  title varchar(120) NOT NULL DEFAULT '',
  template text NOT NULL,
  sid smallint(6) NOT NULL DEFAULT '0',
  version varchar(20) NOT NULL DEFAULT '',
  status varchar(10) NOT NULL DEFAULT '',
  dateline int(10) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (tid),
  KEY sid (sid)
);

CREATE TABLE mybb_templatesets (
  sid smallint(6) NOT NULL AUTO_INCREMENT,
  title varchar(120) NOT NULL DEFAULT '',
  PRIMARY KEY (sid)
);

CREATE TABLE mybb_templategroups (
  gid int(10) unsigned NOT NULL AUTO_INCREMENT,
  prefix varchar(50) NOT NULL DEFAULT '',
  title varchar(100) NOT NULL DEFAULT '',
  isdefault tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (gid)
);
```

### File Reference Matrix

| File | Purpose | Key Functions/Classes |
|------|---------|----------------------|
| `inc/class_templates.php` | Core template engine | `templates->cache()`, `templates->get()`, `templates->render()` |
| `inc/adminfunctions_templates.php` | Template manipulation | `find_replace_templatesets()` |
| `admin/modules/style/templates.php` | ACP interface | Template CRUD operations, outdated detection |
| `inc/functions_post.php` | Usage example | `build_postbit()` showing template rendering |
| `mybb_mcp/mybb_mcp/server.py` | MCP tools | Template tool definitions |

### Research Audit Trail

**Total Append Entries:** 11
**Files Analyzed:** 5 core files + 1 MCP file
**Database Queries:** 8 schema/data queries
**Code Patterns Traced:** 3 major flows
**Confidence Scores:** Average 0.93 (High)

**Cross-Project Research:** No related research found in other projects (first template system analysis)

### Related Documents
- **MCP Server Documentation:** `/home/austin/projects/MyBB_Playground/mybb_mcp/README.md` (if exists)
- **MyBB Official Docs:** https://docs.mybb.com/1.8/development/templates/ (external)
- **Template Syntax Reference:** https://docs.mybb.com/1.8/development/templates/#template-syntax (external)

---

**Research Status:** ✅ **COMPLETE**
**Handoff to Architect:** Ready for tool design and API specification based on identified gaps.
**Handoff to Coder:** Reference document for template-related implementations.
**Handoff to Review:** Validation criteria established via confidence scores and evidence links.
