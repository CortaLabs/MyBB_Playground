# Cortex Template Compiler

**Purpose:** Practical guide for using Cortex template syntax in MyBB development.

**When to read this:** You're creating or editing MyBB templates and need dynamic content, conditionals, or expressions.

**Quick Links:**
- Full reference: `docs/wiki/plugins/cortex.md` (416 lines)
- Plugin code: `plugin_manager/plugins/public/cortex/`
- Configuration: Admin CP > Settings > Cortex

---

## Decision Tree: Cortex vs PHP

```
Do you need logic in a template?
├─ YES → Next question
└─ NO → Use plain HTML

Is it display logic (showing/hiding, formatting)?
├─ YES → Use Cortex
└─ NO → Next question

Does it involve database queries or complex business logic?
├─ YES → Use PHP plugin code (hook handler)
└─ NO → Could go either way, prefer Cortex for simplicity

Examples:
✓ Cortex: Show admin panel link if usergroup == 4
✓ Cortex: Format date, calculate posts per day
✓ Cortex: Conditional CSS classes based on user data
✗ PHP: Database queries, API calls, email sending
✗ PHP: Complex calculations (>50 lines), multi-step workflows
✗ PHP: Security-sensitive operations, permission checks
```

**Golden Rule:** If you need to query the database or modify data, use PHP. If you're just displaying/formatting existing data, use Cortex.

---

## Quick Syntax Reference

### Conditionals
```html
<!-- Basic if/else -->
<if $mybb->user['uid'] > 0 then>
    Logged in content
<else>
    Guest content
</if>

<!-- Multiple conditions (else if) -->
<if $mybb->user['usergroup'] == 4 then>
    Admin
<else if $mybb->user['usergroup'] == 3 then>
    Super Mod
<else if $mybb->user['usergroup'] == 2 then>
    Member
<else>
    Guest
</if>

<!-- Nested conditionals -->
<if $mybb->user['uid'] > 0 then>
    <if $mybb->user['postnum'] > 100 then>
        Veteran
    <else>
        Newbie
    </if>
</if>

<!-- Complex conditions -->
<if ($mybb->user['uid'] > 0 && $mybb->user['postnum'] > 50) || $mybb->user['usergroup'] == 4 then>
    Content
</if>
```

**Critical:** Always include `then` keyword: `<if CONDITION then>` (not `<if CONDITION>`)

### Inline Expressions
```html
<!-- Simple expressions -->
{= strtoupper($mybb->settings['bbname']) }
{= round($mybb->user['postnum'] / 30, 1) }

<!-- Ternary operator -->
{= $mybb->user['uid'] > 0 ? 'Member' : 'Guest' }

<!-- Nested function calls -->
{= htmlspecialchars_uni(strtoupper($mybb->user['username'])) }

<!-- Math expressions -->
{= round(($mybb->user['postnum'] / max(1, floor((time() - $mybb->user['regdate']) / 86400))), 2) }

<!-- Array access -->
{= $mybb->user['additionalgroups'] ? count(explode(',', $mybb->user['additionalgroups'])) : 0 }
```

**Critical:** Always use `{= }` for expressions (not `{ }` or `{{ }}`)

### Template Variables
```html
<!-- Set variables -->
<setvar greeting>Hello World</setvar>
<setvar counter>42</setvar>
<setvar username>$mybb->user['username']</setvar>

<!-- Access variables -->
{= $GLOBALS['tplvars']['greeting'] }
{= $GLOBALS['tplvars']['counter'] }

<!-- Use in conditions -->
<if $GLOBALS['tplvars']['counter'] > 40 then>
    High counter
</if>
```

**Use case:** Complex calculations used multiple times, or readability for long expressions.

### Function Wrapping
```html
<func strtoupper>hello world</func>
<!-- Outputs: HELLO WORLD -->

<func trim>  spaced text  </func>
<!-- Outputs: spaced text -->
```

**Rarely used:** Inline expressions `{= strtoupper('hello') }` are more common.

### Template Includes
```html
<template myplugin_widget>
<template myplugin_user_badge>
```

**Note:** Same as standard MyBB `{$myplugin_widget}` but works with Cortex processing.

---

## Common Patterns & Recipes

### Show Admin Panel Link
```html
<if $mybb->user['usergroup'] == 4 then>
    <a href="admin/index.php">Admin CP</a>
</if>
```

### Post Count Badges
```html
<if $post['postnum'] >= 1000 then>
    <span class="badge veteran">Veteran (1000+ posts)</span>
<else if $post['postnum'] >= 100 then>
    <span class="badge active">Active (100+ posts)</span>
<else>
    <span class="badge newbie">New Member</span>
</if>
```

### Format Dates
```html
Joined: {= my_date('F j, Y', $mybb->user['regdate']) }
Last active: {= my_date('M j, g:i a', $mybb->user['lastactive']) }
Member for: {= floor((time() - $mybb->user['regdate']) / 86400) } days
```

**Use `my_date` (MyBB function) instead of `date` for timezone support.**

### Posts Per Day
```html
{= round($mybb->user['postnum'] / max(1, floor((time() - $mybb->user['regdate']) / 86400)), 2) }
```

**Breakdown:**
- `$mybb->user['postnum']` - total posts
- `time() - $mybb->user['regdate']` - seconds since registration
- `/ 86400` - convert to days
- `max(1, ...)` - prevent division by zero
- `round(..., 2)` - 2 decimal places

### Conditional CSS Classes
```html
<div class="post <if $post['uid'] == $mybb->user['uid'] then>my-post</if>">
    Content
</div>

<!-- Multiple classes -->
<span class="username
    <if $mybb->user['usergroup'] == 4 then>admin</if>
    <if $mybb->user['postnum'] > 1000 then>veteran</if>">
    {$mybb->user['username']}
</span>
```

### Show Content to Specific Usergroups
```html
<if in_array($mybb->user['usergroup'], [3, 4, 6]) then>
    Moderator/Admin content
</if>
```

**Usergroup IDs:**
- 1 = Guests
- 2 = Registered
- 3 = Super Moderators
- 4 = Administrators
- 6 = Moderators

### Safe Username Display
```html
{= htmlspecialchars_uni($mybb->user['username']) }
```

**Always use `htmlspecialchars_uni` (MyBB function) for user input, not `htmlspecialchars`.**

### Alternating Table Rows
```html
<tr class="{= alt_trow() }">
    <td>Row 1</td>
</tr>
<tr class="{= alt_trow() }">
    <td>Row 2</td>
</tr>
```

**`alt_trow()` alternates between `trow1` and `trow2` classes automatically.**

### File Size Formatting
```html
Attachment size: {= get_friendly_size($attachment['filesize']) }
<!-- Outputs: 1.5 MB, 500 KB, etc. -->
```

### Check Array/Value Exists
```html
<if isset($mybb->user['signature']) && !empty($mybb->user['signature']) then>
    <div class="signature">{$mybb->user['signature']}</div>
</if>

<if array_key_exists('custom_field', $mybb->user) then>
    Custom: {$mybb->user['custom_field']}
</if>
```

---

## MyBB-Specific Functions (18 total)

These are **MyBB helper functions** included in Cortex's whitelist for seamless integration:

| Function | Purpose | Example |
|----------|---------|---------|
| `htmlspecialchars_uni` | Unicode-safe HTML encoding | `{= htmlspecialchars_uni($user['username']) }` |
| `my_date` | MyBB date with timezone | `{= my_date('F j, Y', $timestamp) }` |
| `my_strlen`, `my_substr` | Multibyte string ops | `{= my_strlen($mybb->user['username']) }` |
| `my_number_format` | Format numbers | `{= my_number_format($post['views']) }` |
| `alt_trow` | Alternating table rows | `<tr class="{= alt_trow() }">` |
| `get_friendly_size` | Format file sizes | `{= get_friendly_size($bytes) }` |
| `unhtmlentities` | MyBB entity decoder | `{= unhtmlentities($text) }` |
| `get_colored_warning_level` | Warning level colors | `{= get_colored_warning_level($level) }` |

**Always prefer MyBB functions over PHP equivalents for proper internationalization and timezone support.**

---

## Security Best Practices

### Always Sanitize User Input
```html
<!-- ✓ SAFE -->
{= htmlspecialchars_uni($post['username']) }
{= htmlspecialchars_uni($thread['subject']) }

<!-- ✗ DANGEROUS -->
{= $post['username'] }  <!-- XSS risk! -->
```

### Don't Trust Plugin Variables
```html
<!-- If your plugin passes variables to templates, sanitize in PHP: -->

// ✓ In plugin hook:
$post['myplugin_field'] = htmlspecialchars_uni($unsafe_data);

// Then in template:
{= $post['myplugin_field'] }
```

### Check Permissions in PHP
```html
<!-- ✗ BAD: Permission check in template -->
<if $mybb->user['usergroup'] == 4 then>
    <form action="delete_user.php">...</form>
</if>

<!-- ✓ GOOD: Permission check in PHP plugin code -->
```

**Why:** Template editors may not have proper permissions. Always enforce security in PHP, use templates only for display.

### Never Use Additional Allowed Functions
```php
// ✗ DANGEROUS: Don't add to config.php
'additional_allowed_functions' => ['file_get_contents', 'unlink']
```

**150+ whitelisted functions are sufficient for 99.9% of use cases. If you need more, your logic belongs in PHP.**

---

## Troubleshooting Guide

### Syntax Not Processing (Cortex tags visible in HTML)

**Symptoms:** `<if ...>` tags appear in page source

**Solutions:**
1. Check plugin activated: Admin CP > Plugins > Cortex = **Active**
2. Check setting enabled: Admin CP > Settings > Cortex > Enable Cortex = **Yes**
3. Check PHP version: `php -v` must be 8.1+
4. Check error log: Enable debug mode, check PHP error_log
5. Clear cache: Admin CP > Tools > Cache Manager > Rebuild Cortex Cache

**Common cause:** Cortex skips Admin CP - only works on frontend templates.

### Parse Error / White Page

**Symptoms:** Blank page, partial output, or error message

**Solutions:**
1. **Enable debug mode:** Admin CP > Settings > Cortex > Debug Mode = **Yes**
2. **Check PHP error log:** Look for "Cortex parse error" messages
3. **Common syntax errors:**
   - Missing `then` keyword: `<if $condition then>` ✓ not `<if $condition>`
   - Unbalanced tags: Every `<if>` needs `</if>`
   - Typo in variable name: `$mybb->user['uid']` ✓ not `$mybb->users['uid']`
   - Missing quotes in expressions: `{= "string" }` or `{= $var }`
4. **Test in isolation:** Comment out sections to identify problematic code
5. **Fallback:** Cortex returns original template if compilation fails

**Debug example:**
```html
<!-- Test variable exists -->
{= isset($mybb->user['uid']) ? 'exists' : 'missing' }

<!-- Dump variable -->
{= '<pre>' . htmlspecialchars(print_r($mybb->user, true)) . '</pre>' }
```

### Function Not Working

**Symptoms:** Expression returns empty or unexpected result

**Solutions:**
1. **Check whitelist:** See "Allowed Functions" below or full list in wiki
2. **Verify syntax:** Match PHP documentation exactly
3. **Enable debug mode:** Error messages show which function failed
4. **Common issues:**
   - Using `printf` (not allowed - outputs directly)
   - Using `$_GET`, `$_POST` (superglobals blocked)
   - Using callback functions: `array_map('trim', $array)` (callbacks not allowed)

**Alternative:** If function not whitelisted, do it in PHP plugin code instead.

### Cache Not Clearing

**Symptoms:** Template changes not appearing

**Solutions:**
1. **Auto-clear:** Cortex auto-clears on template edits via Admin CP
2. **Manual clear:** Admin CP > Tools > Cache Manager > Rebuild Cortex Cache
3. **File system:** `rm -rf TestForum/cache/cortex/*.php`
4. **Disk sync:** File watcher triggers cache clear automatically
5. **Verify cache enabled:** Admin CP > Settings > Cortex > Enable Cache = **Yes**

**Dev workflow:** Cache auto-clears when using disk sync + file watcher. No manual intervention needed.

### Performance Issues

**Symptoms:** Slow page loads

**Solutions:**
1. **Enable caching:** Admin CP > Settings > Cortex > Enable Cache = **Yes**
2. **Check cache directory:** `cache/cortex/` must exist and be writable (0755)
3. **Reduce complexity:** Avoid deeply nested function calls
4. **Move to PHP:** Complex calculations (>50 lines) should be in plugin code
5. **Set TTL:** Production sites can use Cache TTL = 86400 (24 hours)

**Profiling:** Enable debug mode and check error log for slow templates (>100ms).

---

## Allowed Functions Quick Reference

**150+ functions across 8 categories.** See `docs/wiki/plugins/cortex.md` for complete list.

**Most Common:**

**String:** strlen, substr, strpos, strtoupper, strtolower, trim, str_replace, sprintf, number_format, htmlspecialchars

**MyBB:** htmlspecialchars_uni, my_date, my_strlen, alt_trow, get_friendly_size

**Array:** count, in_array, array_key_exists, array_merge, implode, explode

**Math:** abs, ceil, floor, round, max, min, pow, sqrt

**Date:** date, time, strtotime, my_date

**Type:** isset, empty, is_array, is_string, is_numeric, intval, floatval

**Check if function allowed:**
```html
{= function_exists('function_name') ? 'exists' : 'not found' }
```

**Note:** `function_exists` only checks PHP functions, not Cortex whitelist. If unsure, test with debug mode enabled.

---

## Integration with Disk Sync

### Workflow

1. **Edit template on disk:**
   ```
   mybb_sync/template_sets/Default Templates/global/header.html
   ```

2. **File watcher detects change** → syncs to database

3. **Cortex cache auto-invalidates** via template edit hook

4. **Next page load:**
   - Runtime checks cache (miss)
   - Compiles template with Cortex syntax
   - Caches compiled version to `cache/cortex/`

5. **Subsequent loads:** Served from cache (fast)

### Best Practices

**DO:**
- Edit templates via disk sync (`mybb_sync/` directory)
- Use Cortex syntax freely - it processes transparently
- Enable debug mode during development
- Test with file watcher running

**DON'T:**
- Don't manually clear cache - auto-invalidation handles it
- Don't use `mybb_write_template` MCP tool during dev - disk sync is the workflow
- Don't edit templates directly in Admin CP during dev - use disk sync

**Plugin Templates:**
Create in workspace:
```
plugin_manager/plugins/public/myplugin/templates/myplugin_widget.html
```

Use Cortex syntax normally. On `mybb_plugin_install`, templates deploy to database and Cortex processes them automatically.

**Critical:** To update deployed plugin templates, use full uninstall/reinstall cycle:
```python
mybb_plugin_uninstall(codename, remove_files=True)
mybb_plugin_install(codename)
```

Standard `mybb_plugin_install` does NOT update existing templates in database.

---

## When NOT to Use Cortex

### Use PHP Plugin Code Instead When:

1. **Database queries required**
   ```php
   // ✓ PHP plugin code
   $query = $db->simple_select('users', 'COUNT(*) as count', 'usergroup = 4');
   $admin_count = $db->fetch_field($query, 'count');
   ```

2. **Complex business logic** (>50 lines, multi-step workflows)
   ```php
   // ✓ PHP plugin code
   function calculate_reputation_level($user) {
       // 50+ lines of complex logic
   }
   ```

3. **Security-sensitive operations**
   ```php
   // ✓ PHP plugin code
   if (!is_member($mybb->settings['myplugin_allowed_groups'])) {
       error_no_permission();
   }
   ```

4. **API calls, email sending, file operations**
   ```php
   // ✓ PHP plugin code
   $mybb->mail->send(...);
   ```

5. **Data modification**
   ```php
   // ✓ PHP plugin code
   $db->update_query('users', ['postnum' => $postnum + 1], "uid = {$uid}");
   ```

### Cortex Is For Display Logic Only

**Think of Cortex as "smart HTML" - not a replacement for PHP.**

---

## Gotchas & Pitfalls

### 1. `then` Keyword Required
```html
<!-- ✗ WRONG -->
<if $mybb->user['uid'] > 0>

<!-- ✓ CORRECT -->
<if $mybb->user['uid'] > 0 then>
```

### 2. Expression Syntax
```html
<!-- ✗ WRONG -->
{{ $mybb->user['username'] }}
{ $mybb->user['username'] }

<!-- ✓ CORRECT -->
{= $mybb->user['username'] }
```

### 3. Always Balance Tags
```html
<!-- ✗ WRONG -->
<if $condition then>
    Content
<!-- Missing </if> -->

<!-- ✓ CORRECT -->
<if $condition then>
    Content
</if>
```

### 4. Sanitize User Input
```html
<!-- ✗ DANGEROUS -->
{= $post['username'] }

<!-- ✓ SAFE -->
{= htmlspecialchars_uni($post['username']) }
```

### 5. Use MyBB Functions
```html
<!-- ✗ WRONG (no timezone support) -->
{= date('F j, Y', $timestamp) }

<!-- ✓ CORRECT (MyBB timezone support) -->
{= my_date('F j, Y', $timestamp) }
```

### 6. Array Access
```html
<!-- ✗ WRONG (PHP 7.4+ syntax) -->
<if $mybb->user['additionalgroups']?[0] then>

<!-- ✓ CORRECT -->
<if isset($mybb->user['additionalgroups']) && $mybb->user['additionalgroups'] then>
```

### 7. Callback Functions Not Allowed
```html
<!-- ✗ WRONG (callbacks blocked) -->
{= array_map('trim', explode(',', $string)) }

<!-- ✓ CORRECT (do in PHP plugin code) -->
```

### 8. Max Nesting Depth
```html
<!-- ✗ BAD (deeply nested) -->
<if 1 then>
  <if 2 then>
    <if 3 then>
      <!-- ... 10+ levels deep -->
    </if>
  </if>
</if>

<!-- ✓ GOOD (flatten with else-if) -->
<if condition1 then>
<else if condition2 then>
<else if condition3 then>
</if>
```

Default limit: 10 levels (configurable via ACP).

---

## Quick Troubleshooting Checklist

**Template not processing:**
- [ ] Cortex plugin activated?
- [ ] Cortex enabled in ACP settings?
- [ ] PHP 8.1+?
- [ ] Frontend template (not Admin CP)?

**Parse error / white page:**
- [ ] Debug mode enabled?
- [ ] Checked PHP error log?
- [ ] All `<if>` tags have `then` keyword?
- [ ] All tags balanced (`<if>...</if>`)?
- [ ] No typos in variable names?

**Function not working:**
- [ ] Function in whitelist? (See wiki)
- [ ] Syntax matches PHP docs exactly?
- [ ] Not using callbacks?
- [ ] Not using superglobals ($_GET, etc.)?

**Cache issues:**
- [ ] Cache enabled in settings?
- [ ] `cache/cortex/` exists and writable?
- [ ] Using disk sync workflow (auto-clears)?

**Performance slow:**
- [ ] Caching enabled?
- [ ] Expressions not too complex?
- [ ] Consider moving logic to PHP?

---

## Links

- **Full Reference:** `docs/wiki/plugins/cortex.md` (416 lines)
- **Plugin Code:** `plugin_manager/plugins/public/cortex/`
- **Configuration:** Admin CP > Configuration > Settings > Cortex
- **Cache Management:** Admin CP > Tools & Maintenance > Cache Manager
- **MyBB Hooks:** [docs.mybb.com/1.8/development/plugins/hooks/](https://docs.mybb.com/1.8/development/plugins/hooks/)

---

**Remember:** Cortex is for display logic. Complex operations belong in PHP plugin code. When in doubt, if you need more than 10-20 lines of template logic, move it to PHP.
