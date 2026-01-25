
# 🐞 theme:set_property stores templateset as string instead of int

**Author:** MyBBBugHunter
**Version:** v1.0
**Status:** FIXED
**Last Updated:** 2026-01-25 06:43 UTC

> Documents type mismatch bug in theme:set_property bridge action that stores templateset as string instead of integer, causing inconsistency with theme:create.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** 2026-01-25_theme_set_property_type_mismatch

**Reported By:** MyBBBugHunter

**Date Reported:** 2026-01-25

**Severity:** MEDIUM

**Status:** FIXED

**Component:** TestForum/mcp_bridge.php (theme:set_property action)

**Environment:** Local development (affects all environments)

**Customer Impact:** Type inconsistency can cause comparison issues in PHP code expecting integer templateset values. Affects theme reinstalls via installer.py.

---
## Description
<!-- ID: description -->
### Summary
The `theme:set_property` bridge action stores the `templateset` property as a string instead of an integer, creating type inconsistency with `theme:create`.

### Expected Behaviour
When setting `templateset` via `theme:set_property --key=templateset --value=8`, the value should be stored as integer `8` in the theme's properties array, matching the behavior of `theme:create`.

### Actual Behaviour
The `templateset` value is stored as string `"8"` instead of integer `8`. When retrieved via `theme:get`, it returns:
```json
{"templateset": "8"}  // Wrong - string
```

Instead of:
```json
{"templateset": 8}  // Correct - integer
```

### Steps to Reproduce
1. Create a theme: `php mcp_bridge.php --action=theme:create --name="Test" --templateset=8`
2. Verify correct type: `php mcp_bridge.php --action=theme:get --name="Test" | jq '.data.properties.templateset'`
   - Returns: `8` (integer) ✓
3. Update via set_property: `php mcp_bridge.php --action=theme:set_property --tid=<tid> --key=templateset --value=9`
4. Verify type again: `php mcp_bridge.php --action=theme:get --tid=<tid> | jq '.data.properties.templateset'`
   - Returns: `"9"` (string) ✗

---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**

The bug is in `mcp_bridge.php` at line 1104 (before fix):

```php
case 'theme:set_property':
    // ...
    $value = $options['value'] ?? '';  // Line 1083 - always a string from CLI
    // ...
    $properties[$key] = $value;  // Line 1104 - NO TYPE CASTING
```

Command-line arguments are always strings in PHP. The `theme:create` action correctly handles this at line 1240:

```php
case 'theme:create':
    // ...
    if ($templateset !== null) {
        $properties['templateset'] = (int)$templateset;  // ✓ Correct casting
    }
```

But `theme:set_property` lacks this type handling, storing the string value directly.

**Affected Areas:**
- `TestForum/mcp_bridge.php` - `theme:set_property` action (lines 1078-1117)
- `plugin_manager/installer.py` - `install_theme()` method uses set_property to update templateset for existing themes (lines 1007-1018)
- Any code comparing templateset values using strict equality (`===`)

**Related Issues:**
- Original report: Theme templateset NULL after install (turned out to be string `"8"` not NULL)
- Affects theme reinstalls via `mybb_theme_install()` MCP tool

---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] **FIXED:** Added type casting to `theme:set_property` (lines 1105-1110)
- [x] **TESTED:** Verified fix with direct bridge calls
- [x] **VERIFIED:** Confirmed templateset now stored as integer

### Fix Implementation
```php
// Type cast numeric properties (templateset should be int, not string)
if ($key === 'templateset') {
    $properties[$key] = (int)$value;
} else {
    $properties[$key] = $value;
}
```

### Testing Strategy
- [x] Direct bridge test: `theme:set_property --key=templateset --value=9`
- [x] Verification: `theme:get` returns integer `9` not string `"9"`
- [x] Comparison with `theme:create` behavior - now consistent

### Future Considerations
- Consider adding type casting for other numeric properties (`pid`, `def`, etc.)
- Document expected types for all theme properties in bridge API docs

---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Completed | Notes |
| --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 2026-01-25 06:27 UTC | Traced call stack from MCP → installer.py → bridge |
| Root Cause | MyBBBugHunter | 2026-01-25 06:32 UTC | Found missing type cast at line 1104 |
| Fix Development | MyBBBugHunter | 2026-01-25 06:42 UTC | Added conditional type casting |
| Testing | MyBBBugHunter | 2026-01-25 06:42 UTC | Verified with theme:set_property + theme:get |

---
## Appendix
<!-- ID: appendix -->

**Evidence:**
- Theme ID 47 (Flavor): Had `null` templateset (actually string from earlier buggy code)
- Theme ID 48 (Test Bug Hunt): Created via fixed bridge, has integer `7`
- Theme ID 49 (Fresh Test): Created via fixed bridge, has integer `9`
- Theme ID 50 (Type Test): Updated via fixed set_property, has integer `9`

**Fix Location:**
- File: `/home/austin/projects/MyBB_Playground/TestForum/mcp_bridge.php`
- Lines: 1105-1110
- Action: `theme:set_property`

**Comparison:**
| Action | Line | Behavior |
|--------|------|----------|
| `theme:create` | 1240 | ✓ Casts to `(int)$templateset` |
| `theme:set_property` (before) | 1104 | ✗ Direct assignment (string) |
| `theme:set_property` (after) | 1107 | ✓ Casts to `(int)$value` for templateset |

**Open Questions:**
- Should we add similar type casting for `pid`, `def`, and other numeric theme properties?
- Should we create a schema for theme properties to handle all type conversions automatically?

---
