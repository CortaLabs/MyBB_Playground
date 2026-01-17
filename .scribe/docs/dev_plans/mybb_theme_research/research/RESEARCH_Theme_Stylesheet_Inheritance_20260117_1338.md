# MyBB Theme/Stylesheet Inheritance System - Research Report

**Research Date:** 2026-01-17
**Researcher:** ResearchAgent
**Target System:** MyBB Forum Software (TestForum installation)
**Confidence Score:** 0.95

---

## Executive Summary

This research analyzed MyBB's complete theme and stylesheet inheritance system from source code. The system implements a **copy-on-write inheritance model** with runtime optimization through pre-computed stylesheet lists.

### Key Findings

1. **Parent Linkage:** `themes.pid` field stores parent theme ID (pid=0 for master theme)
2. **Inheritance Resolution:** Recursive parent chain traversal with child-overrides-parent semantics
3. **Copy-on-Write:** Editing inherited stylesheets automatically creates theme-specific overrides
4. **Revert Capability:** Deleting overrides exposes parent stylesheets (implicit revert-to-parent)
5. **Runtime Optimization:** Pre-computed stylesheet list cached in `themes.stylesheets` field

---

## Database Schema

### themes Table (Relevant Fields)

| Field | Type | Purpose |
|-------|------|---------|
| `tid` | INT | Theme ID (primary key) |
| `pid` | INT | Parent theme ID (0 = no parent/master) |
| `name` | VARCHAR | Theme display name |
| `stylesheets` | TEXT | Serialized array of resolved stylesheets (computed) |
| `properties` | TEXT | Serialized theme properties with inheritance tracking |

**Example Data:**
- tid=1: "MyBB Master Style" (pid=0) - Master theme with no parent
- tid=2: "Default" (pid=1) - Inherits from Master

### themestylesheets Table

| Field | Type | Purpose |
|-------|------|---------|
| `sid` | INT | Stylesheet ID (primary key) |
| `name` | VARCHAR | Stylesheet filename (e.g., "global.css") |
| `tid` | INT | Theme ID this stylesheet belongs to |
| `attachedto` | TEXT | Which pages/actions use this stylesheet |
| `stylesheet` | TEXT | Actual CSS content |
| `cachefile` | VARCHAR | Cached file path |
| `lastmodified` | INT | Unix timestamp |

**Critical:** No explicit `inherited` field in database - inheritance is computed at query time.

---

## Inheritance Mechanism

### 1. Parent Chain Resolution

**File:** `/admin/inc/functions_themes.php`
**Function:** `make_parent_theme_list($tid)` (Lines 1139-1180)

```php
function make_parent_theme_list($tid)
{
    // Recursively walks pid field to build array:
    // [current_tid, parent_tid, grandparent_tid, ...]

    foreach($themes_by_parent[$tid] as $key => $theme)
    {
        $themes[] = $theme['tid'];
        $parents = make_parent_theme_list($theme['pid']); // Recursive

        if(is_array($parents))
        {
            $themes = array_merge($themes, $parents);
        }
    }

    return $themes;
}
```

**Behavior:** Returns ordered list starting with current theme, walking up parent chain.

**Example:** If theme 5 has pid=3, theme 3 has pid=2, theme 2 has pid=1:
- `make_parent_theme_list(5)` returns `[5, 3, 2, 1]`

### 2. Stylesheet Resolution

**File:** `/admin/inc/functions_themes.php`
**Function:** `update_theme_stylesheet_list($tid, ...)` (Lines 958-1050)

```php
$parent_list = make_parent_theme_list($tid);
$tid_list = implode(',', $parent_list);

// Query with tid DESC ordering - child themes first
$query = $db->simple_select(
    "themestylesheets",
    "*",
    "tid IN ({$tid_list})",
    array('order_by' => 'tid', 'order_dir' => 'desc')
);

while($stylesheet = $db->fetch_array($query))
{
    // First match wins (child overrides parent)
    if(empty($stylesheets[$stylesheet['name']]))
    {
        if($stylesheet['tid'] != $tid)
        {
            $stylesheet['inherited'] = $stylesheet['tid']; // Track origin
        }

        $stylesheets[$stylesheet['name']] = $stylesheet;
    }
}
```

**Key Mechanism:**
1. Query all stylesheets in parent chain
2. Order by `tid DESC` (higher tid = child themes first)
3. First match per `name` wins
4. Track original tid in `inherited` metadata

**Result:** Child themes automatically override parent stylesheets with same name.

---

## ACP Editing Behavior (Copy-on-Write)

### Edit Inherited Stylesheet

**File:** `/admin/modules/style/themes.php`
**Action:** `edit_stylesheet` (Lines 2051-2200)

**Critical Code (Lines 2086-2090):**
```php
// Theme & stylesheet theme ID do not match, editing inherited - we copy to local theme
if($theme['tid'] != $stylesheet['tid'])
{
    $sid = copy_stylesheet_to_theme($stylesheet, $theme['tid']);
}
```

**Behavior:**
1. Query finds stylesheet using parent_list (may return parent's stylesheet)
2. Check if `stylesheet.tid != current_theme.tid`
3. If true → **copy_stylesheet_to_theme()** creates override
4. New row inserted with same `name` but current theme's `tid`
5. Changes applied to new override, parent remains untouched

**Why This Works:**
- Next resolution will find child's override first (tid DESC ordering)
- Parent theme remains unchanged
- Multiple child themes can have different overrides

### copy_stylesheet_to_theme()

**File:** `/admin/inc/functions_themes.php`
**Function:** Lines 930-949

```php
function copy_stylesheet_to_theme($stylesheet, $tid)
{
    global $db;

    $stylesheet['tid'] = $tid;      // Change to current theme
    unset($stylesheet['sid']);       // Generate new sid

    $sid = $db->insert_query("themestylesheets", $new_stylesheet);

    return $sid;
}
```

**Effect:** Duplicates stylesheet row with new tid, creates override.

---

## Revert to Parent (Delete Override)

**File:** `/admin/modules/style/themes.php`
**Action:** `delete_stylesheet` (Lines 2485-2545)

**Code (Line 2524):**
```php
$db->delete_query("themestylesheets", "sid='{$stylesheet['sid']}'", 1);
```

**Behavior:**
1. Deletes stylesheet row by `sid`
2. Next resolution query won't find child's override
3. Parent's version becomes visible (first match in parent_list)

**This implements implicit "revert to parent":**
- No explicit revert function needed
- Deleting override automatically exposes parent
- Works because resolution always queries full parent chain

**Important:** Cannot delete Master theme stylesheets (tid=1) - line 2510 blocks this.

---

## Runtime Stylesheet Loading

### Pre-Computed List (Performance Optimization)

**File:** `/global.php` (Lines 296-350)

```php
// Unserialize pre-computed stylesheet list
$theme['stylesheets'] = my_unserialize($theme['stylesheets']);

foreach($stylesheet_scripts as $stylesheet_script)
{
    foreach($stylesheet_actions as $stylesheet_action)
    {
        // Look up in pre-computed array
        if(!empty($theme['stylesheets'][$stylesheet_script][$stylesheet_action]))
        {
            foreach($theme['stylesheets'][$stylesheet_script][$stylesheet_action] as $page_stylesheet)
            {
                // Generate stylesheet URL (cache file or css.php)
                $stylesheet_url = ...;
            }
        }
    }
}
```

**Key Points:**
1. **Does NOT query themestylesheets table at runtime**
2. Reads pre-computed list from `themes.stylesheets` (serialized array)
3. Array structure: `[script_name][action] = [stylesheet_urls]`
4. Created/updated by `update_theme_stylesheet_list()` during ACP operations

**Performance Benefit:** Single field read vs. complex JOIN queries on every page load.

### When is themes.stylesheets Updated?

**Function:** `update_theme_stylesheet_list($tid)` called after:
- Theme creation (`build_new_theme`)
- Stylesheet editing (`edit_stylesheet` POST handler)
- Stylesheet deletion (`delete_stylesheet`)
- Stylesheet creation (`add_stylesheet`)

**What It Contains:** Resolved stylesheet URLs after inheritance calculations.

---

## Build New Theme (Inheritance Setup)

**File:** `/admin/inc/functions_themes.php`
**Function:** `build_new_theme($name, $properties, $parent)` (Lines 552-649)

**Key Code (Lines 556-563):**
```php
$new_theme = array(
    "name" => $db->escape_string($name),
    "pid" => (int)$parent,           // Store parent ID
    "def" => 0,
    "allowedgroups" => "all",
    "properties" => "",
    "stylesheets" => ""
);
$tid = $db->insert_query("themes", $new_theme);
```

**Inheritance Copy (Lines 598-625):**
```php
// Copy parent's stylesheets with inheritance tracking
$parent_stylesheets = my_unserialize($parent_theme['stylesheets']);

foreach($parent_stylesheets as $location => $value)
{
    foreach($value as $action => $sheets)
    {
        foreach($sheets as $stylesheet)
        {
            // Copy stylesheet reference
            $stylesheets[$location][$action][] = $stylesheet;

            // Track which theme it came from
            $inherited_check = "{$location}_{$action}";
            if(!empty($parent_stylesheets['inherited'][$inherited_check][$stylesheet]))
            {
                // Preserve original origin
                $stylesheets['inherited'][$inherited_check][$stylesheet] =
                    $parent_stylesheets['inherited'][$inherited_check][$stylesheet];
            }
            else
            {
                // Parent is the origin
                $stylesheets['inherited'][$inherited_check][$stylesheet] = $parent;
            }
        }
    }
}
```

**Behavior:**
1. Child theme copies parent's stylesheet list
2. `inherited` metadata tracks original theme ID for each stylesheet
3. Enables UI to show "Inherited from [Theme Name]"
4. **Important:** This is metadata in `themes.stylesheets`, NOT `themestylesheets.inherited` (which doesn't exist)

---

## Answers to Research Questions

### Q1: How does MyBB resolve which stylesheet to use when a theme inherits from a parent?

**Answer:**
1. Build parent chain using `make_parent_theme_list(tid)` → `[child, parent, grandparent, ...]`
2. Query `themestylesheets` WHERE `tid IN (parent_chain)` ORDER BY `tid DESC`
3. First match per stylesheet `name` wins (child overrides parent)
4. Pre-compute results into `themes.stylesheets` for runtime performance

**Confidence: 1.0** - Verified in source code.

### Q2: The `pid` field in themes table - how is it used?

**Answer:**
- Stores parent theme ID
- `pid = 0` means no parent (master theme)
- `pid > 0` points to parent theme's `tid`
- Recursively traversed by `make_parent_theme_list()` to build inheritance chain
- Child themes copy parent's properties/stylesheets at creation time

**Example:**
- Theme 1 (Master): pid=0
- Theme 2 (Default): pid=1 (inherits from Master)
- Theme 5 (Custom): pid=2 (inherits from Default, which inherits from Master)

**Confidence: 1.0** - Verified in database and source code.

### Q3: How does the ACP handle editing inherited stylesheets? Does it create overrides?

**Answer:**
**Yes, automatic copy-on-write override creation.**

**Mechanism:**
1. User edits stylesheet in child theme
2. Query finds stylesheet (may be from parent via inheritance)
3. Compare `stylesheet.tid` vs `current_theme.tid`
4. If different → call `copy_stylesheet_to_theme()` to create override
5. Apply changes to new override, leave parent untouched
6. Call `update_theme_stylesheet_list()` to rebuild pre-computed list

**Location:** `/admin/modules/style/themes.php` lines 2086-2090

**Confidence: 1.0** - Verified in source code.

### Q4: What happens in the ACP when you edit an inherited stylesheet?

**Answer:**
See Q3 above. Additionally:
- UI shows "Inherited from [Parent Theme Name]" indicator (line 2198-2200)
- Editor loads parent's CSS content for editing
- On save, creates new `themestylesheets` row with child theme's `tid`
- Cache files regenerated for child theme
- Next page load shows child's override

**Confidence: 1.0** - Verified in source code.

### Q5: Is there a "revert to parent" concept?

**Answer:**
**Yes, implemented via deletion of override.**

**Mechanism:**
- `delete_stylesheet` action removes child's override row
- Next resolution query skips deleted row (no longer in database)
- First match becomes parent's version
- Effectively reverts to parent without explicit "revert" function

**Limitations:**
- Cannot delete Master theme (tid=1) stylesheets
- Deleting removes override permanently (no undo unless you re-copy)

**Location:** `/admin/modules/style/themes.php` lines 2485-2545

**Confidence: 1.0** - Verified in source code.

### Q6: When displaying a page, how does MyBB determine which stylesheet file to load?

**Answer:**
**Pre-computed lookup, NOT runtime queries.**

**Process:**
1. `global.php` reads `themes.stylesheets` field (serialized array)
2. Unserializes to get structure: `[script][action] = [urls]`
3. Looks up current script name and action
4. Iterates array to build `<link>` tags
5. Checks cache files, falls back to `css.php?stylesheet=sid`

**Why Pre-Computed:**
- Inheritance resolution is expensive (recursive queries)
- Pre-computing during ACP edits avoids runtime overhead
- Trades storage (serialized array) for speed (no JOINs)

**Location:** `/global.php` lines 296-350

**Confidence: 1.0** - Verified in source code.

---

## Architectural Insights

### Design Patterns

1. **Copy-on-Write Inheritance**
   - Parent data preserved
   - Children create overrides only when modified
   - Efficient storage (no duplication until needed)

2. **Lazy Materialization**
   - Inheritance metadata computed on-demand
   - Cached in `themes.stylesheets` field
   - Invalidated on edits

3. **First-Match Resolution**
   - Simple, predictable behavior
   - tid DESC ordering ensures child wins
   - No complex precedence rules

### Trade-offs

**Pros:**
- Fast runtime (no complex queries)
- Simple mental model (child overrides parent)
- Safe editing (parents never modified)

**Cons:**
- Serialized arrays harder to query
- Must rebuild cache on every edit
- No partial overrides (full stylesheet copy)

---

## Gaps and Uncertainties

### VERIFIED Findings (Confidence: 1.0)
- ✅ pid field usage
- ✅ Inheritance resolution algorithm
- ✅ Copy-on-write mechanism
- ✅ Revert via deletion
- ✅ Runtime loading mechanism
- ✅ Database schema

### UNVERIFIED Areas (Out of Scope)
- ⚠️ Child theme creation UI flow (not analyzed)
- ⚠️ Migration/import of themes (not analyzed)
- ⚠️ Caching behavior under high load (requires live testing)
- ⚠️ Plugin hooks for theme inheritance (noted but not detailed)

---

## Handoff Notes for Downstream Agents

### For Architect
- **Critical:** Any theme/stylesheet MCP tools MUST respect copy-on-write pattern
- **Critical:** Writing tools must call `update_theme_stylesheet_list()` after changes
- **Consider:** Read-only tools can use pre-computed `themes.stylesheets` for performance
- **Consider:** Expose "inherited from" metadata in list/read operations

### For Coder
- **File References:**
  - Theme functions: `/admin/inc/functions_themes.php`
  - ACP handlers: `/admin/modules/style/themes.php`
  - Runtime loading: `/global.php`
- **Key Functions:**
  - `make_parent_theme_list($tid)` - inheritance chain
  - `update_theme_stylesheet_list($tid)` - rebuild cache (MUST call after edits)
  - `copy_stylesheet_to_theme($stylesheet, $tid)` - create override
- **Database Tables:**
  - `themes` - theme metadata, pid, pre-computed stylesheets
  - `themestylesheets` - actual stylesheet content, linked by tid

### For Reviewer
- **Verification Points:**
  - Does write implementation call `update_theme_stylesheet_list()`?
  - Does read implementation handle inherited stylesheets correctly?
  - Are tid/pid relationships preserved?
  - Is Master theme (tid=1) protected from deletion?

---

## File References

| File | Lines | Purpose |
|------|-------|---------|
| `/admin/inc/functions_themes.php` | 552-649 | `build_new_theme()` - theme creation |
| `/admin/inc/functions_themes.php` | 930-949 | `copy_stylesheet_to_theme()` - create override |
| `/admin/inc/functions_themes.php` | 958-1050 | `update_theme_stylesheet_list()` - rebuild cache |
| `/admin/inc/functions_themes.php` | 1139-1180 | `make_parent_theme_list()` - inheritance chain |
| `/admin/modules/style/themes.php` | 2051-2200 | `edit_stylesheet` - ACP edit handler |
| `/admin/modules/style/themes.php` | 2485-2545 | `delete_stylesheet` - revert via delete |
| `/global.php` | 296-350 | Runtime stylesheet loading |

---

## Conclusion

MyBB implements a **well-designed copy-on-write inheritance system** with clear semantics:
- Parent themes are immutable from child perspective
- Overrides are explicit (database rows with child tid)
- Reversion is simple (delete override)
- Runtime is optimized (pre-computed cache)

The system is fully understood and ready for MCP tool implementation. All critical behaviors are verified with source code references.

**Research Status: COMPLETE**
**Confidence: 0.95** (high confidence, minor uncertainties in out-of-scope areas)
