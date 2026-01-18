# Cortex Template Engine

**Author:** Corta Labs
**Status:** Ships with MyBB Playground (optional)
**Compatibility:** MyBB 1.8.x

## Overview

Cortex is a secure template enhancement plugin that adds conditionals, expressions, and dynamic content to MyBB templates without compromising security. It's developed by Corta Labs and ships with the MyBB Playground toolkit.

## Features

### Conditionals

```html
<if $mybb->user['uid'] > 0 then>
    Welcome back, {$mybb->user['username']}!
<else>
    Please login or register.
</if>

<!-- Else-if chains -->
<if $mybb->user['usergroup'] == 4 then>
    Administrator
<else if $mybb->user['usergroup'] == 3 then>
    Super Moderator
<else>
    Member
</if>
```

### Inline Expressions

```html
Board: {= strtoupper($mybb->settings['bbname']) }
Posts per day: {= round($mybb->user['postnum'] / max(1, floor((time() - $mybb->user['regdate']) / 86400)), 2) }
Status: {= $mybb->user['uid'] > 0 ? 'Logged In' : 'Guest' }
```

### Template Variables

```html
<setvar greeting>Hello from Cortex!</setvar>
Message: {= $GLOBALS['tplvars']['greeting'] }
```

### Template Includes

```html
<template myplugin_widget>
```

## Security Model

Cortex uses a **whitelist-based security model**:

### Allowed Functions (99 total)

**String Functions (18):**
- `strlen`, `substr`, `strpos`, `strtolower`, `strtoupper`, `ucfirst`, `ucwords`
- `trim`, `ltrim`, `rtrim`, `str_replace`, `str_pad`
- `htmlspecialchars`, `htmlentities`, `urlencode`, `urldecode`
- `sprintf`, `number_format`

**Array Functions (9):**
- `count`, `sizeof`, `array_key_exists`, `in_array`
- `array_merge`, `array_keys`, `array_values`
- `implode`, `explode`

**Math Functions (8):**
- `abs`, `ceil`, `floor`, `round`
- `max`, `min`, `pow`, `sqrt`

**Date Functions (5):**
- `date`, `time`, `strtotime`, `gmdate`, `mktime`

**Type Functions (10):**
- `isset`, `empty`, `is_array`, `is_string`, `is_numeric`, `is_null`
- `intval`, `floatval`, `strval`, `boolval`

**Logic/Comparison:**
- All standard operators: `==`, `!=`, `===`, `!==`, `<`, `>`, `<=`, `>=`
- Boolean operators: `&&`, `||`, `!`, `and`, `or`, `xor`
- Ternary operator: `? :`

### Blocked Operations (31 categories)

- **Code execution:** `eval`, `assert`, `create_function`, `call_user_func*`
- **Shell execution:** `exec`, `system`, `shell_exec`, `passthru`, `proc_open`
- **File operations:** `fopen`, `file_get_contents`, `file_put_contents`, `unlink`, `rmdir`
- **Database access:** `mysql_*`, `mysqli_*`, `pg_*`, `sqlite_*`, `pdo_*`
- **Object instantiation:** `new ClassName` (blocked by parser)
- **Superglobals:** `$_GET`, `$_POST`, `$_SESSION`, `$_COOKIE`, `$_FILES`, `$_SERVER`
- **Stream wrappers:** `php://`, `data://`, `phar://`, `file://`
- **Reflection/introspection:** `get_defined_*`, `class_exists`, `function_exists`

## Configuration

### ACP Settings (Admin CP > Configuration > Settings > Cortex)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| **Enable Cortex** | Yes/No | Yes | Master enable/disable switch for template processing |
| **Debug Mode** | Yes/No | No | Log parsing errors to PHP error_log for troubleshooting |
| **Enable Cache** | Yes/No | Yes | Enable disk caching of compiled templates for performance |
| **Cache TTL** | Numeric | 0 | Cache expiration time in seconds (0 = never expires) |
| **Max Nesting Depth** | Numeric | 10 | Maximum nested if-block depth (0 = unlimited, not recommended) |
| **Max Expression Length** | Numeric | 1000 | Maximum expression length in characters (0 = unlimited) |
| **Denied Functions** | Textarea | (empty) | Comma-separated list of functions to block (e.g., `strlen,substr`) |

**Note:** Changes to settings take effect immediately (cached templates auto-invalidate).

### File-Based Config (Advanced)

For advanced configuration, edit `inc/plugins/cortex/config.php`:

```php
<?php

return [
    'enabled' => true,
    'cache_enabled' => true,
    'cache_ttl' => 0,
    'debug' => false,
    'security' => [
        // Functions to add beyond the built-in whitelist (USE WITH EXTREME CAUTION)
        // This setting is ONLY available via file config for security reasons
        'additional_allowed_functions' => [],

        // Functions to block (overrides whitelist)
        // Can also be configured in ACP Settings
        'denied_functions' => [],

        // Security limits
        'max_nesting_depth' => 10,
        'max_expression_length' => 1000,
    ],
];
```

**IMPORTANT:** The `additional_allowed_functions` setting is only available in the file config for security reasons. Adding functions to the whitelist can create security vulnerabilities if not carefully vetted. The ACP settings provide safe configuration options for most use cases.

**Configuration Precedence:** ACP settings override file config when present. File config serves as fallback defaults.

## Usage Examples

### Show Content Based on Usergroup

```html
<if $mybb->user['usergroup'] == 4 then>
    <div class="admin-panel">
        <a href="admin/index.php">Admin CP</a>
    </div>
</if>
```

### Display Post Count Badge

```html
<if $post['postnum'] >= 1000 then>
    <span class="badge veteran">Veteran (1000+ posts)</span>
<else if $post['postnum'] >= 100 then>
    <span class="badge active">Active Member (100+ posts)</span>
<else>
    <span class="badge newbie">New Member</span>
</if>
```

### Format Dates

```html
Joined: {= date('F j, Y', $mybb->user['regdate']) }
Last active: {= date('M j, g:i a', $mybb->user['lastactive']) }
Member for: {= floor((time() - $mybb->user['regdate']) / 86400) } days
```

### Conditional Forum Display

```html
<if in_array($forum['fid'], [1, 5, 10]) then>
    <span class="featured-forum">★ Featured</span>
</if>
```

### Username Display

```html
<if $mybb->user['uid'] > 0 then>
    {= htmlspecialchars($mybb->user['username']) }
<else>
    Guest
</if>
```

### Custom Math Operations

```html
Posts per day: {= round($mybb->user['postnum'] / max(1, floor((time() - $mybb->user['regdate']) / 86400)), 2) }
Percentage: {= round(($forum['threads'] / max(1, $forum['posts'])) * 100, 1) }%
```

## Caching

Cortex uses a 3-tier caching system for optimal performance:

### 1. Memory Cache (Request-Level)
- Compiled templates cached in memory during a single page request
- Shared across multiple calls to the same template
- Automatically cleared at end of request

### 2. Disk Cache (Persistent)
- Compiled templates stored in `cache/cortex/*.php`
- Persists across requests for maximum performance
- Configurable TTL via ACP settings
- Auto-invalidates when source template changes

### 3. Original Fallback
- If compilation fails at any point, original template is returned
- Errors logged if Debug Mode enabled
- Ensures site never breaks due to template syntax errors

### Cache Management

**Clear cache via ACP:**
Admin CP > Tools & Maintenance > Cache Manager > Rebuild Cortex Cache

**Clear cache manually:**
```bash
rm -rf TestForum/cache/cortex/*.php
```

**Cache file naming:**
- Format: `{template_title}_{hash}.php`
- Hash based on template content for automatic invalidation

Cache files auto-expire based on TTL setting (0 = never expires, recommended for production).

## Troubleshooting

### Templates Not Processing

**Symptoms:** Cortex syntax visible in HTML output

**Solutions:**
1. Verify "Enable Cortex" is set to **Yes** in ACP > Settings > Cortex
2. Check plugin is activated in ACP > Plugins > Cortex
3. Check for PHP errors in server error log
4. Try clearing cache manually

### Syntax Errors

**Symptoms:** White page, partial output, or template not rendering

**Solutions:**
1. Enable **Debug Mode** in ACP Settings to log parsing errors
2. Check PHP error log for Cortex error messages
3. Common issues:
   - Missing `then` keyword: `<if $condition then>` (not `<if $condition>`)
   - Unbalanced tags: Every `<if>` needs `</if>`
   - Typos in variable names: `$mybb->user['uid']` (not `$mybb->users['uid']`)
4. Test expressions in isolation to identify problematic code

### Function Not Working

**Symptoms:** Expression returns empty or unexpected result

**Solutions:**
1. Check if function is in the whitelist (see Security Model section)
2. Verify function syntax matches PHP documentation
3. Use Debug Mode to see actual error messages
4. Test in isolation:
   ```html
   Debug: {= var_export($mybb->user, true) }
   ```

### Performance Issues

**Symptoms:** Slow page loads

**Solutions:**
1. Verify **Enable Cache** is set to **Yes**
2. Check `cache/cortex/` directory is writable
3. Reduce complexity of expressions (avoid nested function calls)
4. Consider increasing **Cache TTL** for production
5. Profile with Debug Mode to identify slow templates

## Development

### Adding Cortex to Your Plugin Templates

1. **Create templates normally** via disk sync or ACP
2. **Use Cortex syntax** in template HTML (conditionals, expressions, etc.)
3. **No additional code required** - Cortex automatically processes all templates
4. **Test thoroughly** with Debug Mode enabled during development

### Best Practices

**DO:**
- Use conditionals for usergroup-specific content
- Sanitize output with `htmlspecialchars()` when displaying user input
- Test expressions with Debug Mode enabled during development
- Keep expressions simple and readable
- Use template variables (`<setvar>`) for complex values used multiple times

**DON'T:**
- Don't use Cortex for complex business logic (use PHP plugin code instead)
- Don't trust user input in expressions (always sanitize)
- Don't add functions to `additional_allowed_functions` without security review
- Don't nest if-blocks excessively (use max_nesting_depth limit)
- Don't disable security limits in production

### Testing Expressions

Use Debug Mode during development:

```html
<!-- Test variable availability -->
User ID: {= isset($mybb->user['uid']) ? $mybb->user['uid'] : 'not set' }

<!-- Debug full variable dump -->
{= '<pre>' . htmlspecialchars(print_r($mybb->user, true)) . '</pre>' }
```

### Example: Custom Plugin Integration

```php
// In your plugin's hook handler
function myplugin_postbit(&$post) {
    global $mybb;

    // Calculate value in PHP
    $reputation_level = calculate_reputation_level($post['reputation']);

    // Make available to template
    $post['myplugin_rep_level'] = $reputation_level;
}
```

```html
<!-- In postbit template (processed by Cortex) -->
<if $post['myplugin_rep_level'] > 100 then>
    <span class="rep-elite">Elite Member</span>
<else if $post['myplugin_rep_level'] > 50 then>
    <span class="rep-trusted">Trusted</span>
<else>
    <span class="rep-member">Member</span>
</if>
```

## Security Considerations

### Why Whitelist-Based?

Cortex uses a whitelist (not blacklist) approach because:
- **Secure by default:** Only explicitly allowed functions are available
- **No eval():** Expressions are parsed and compiled, never passed to `eval()`
- **Sandboxed execution:** Compiled code runs in restricted scope
- **Future-proof:** New PHP functions are blocked automatically

### What's Safe to Allow?

**Safe functions:**
- Pure functions with no side effects (string manipulation, math)
- Read-only data access (date, time)
- Output formatting (number_format, htmlspecialchars)

**NEVER allow:**
- File I/O functions
- Database access
- Shell execution
- Code evaluation
- Superglobal access
- Object instantiation

### Admin Responsibility

**If you add functions to `additional_allowed_functions`:**
1. Research the function thoroughly
2. Verify it has no side effects
3. Confirm it cannot access files, execute code, or modify data
4. Test with malicious inputs
5. Document why it was added

**Remember:** Template editors may not have full admin permissions in your forum. Any function you whitelist becomes available to them.

## Architecture Notes

For developers interested in Cortex internals:

- **Parser:** `inc/plugins/cortex/Parser.php` - Tokenizes and parses Cortex syntax
- **Compiler:** `inc/plugins/cortex/Compiler.php` - Converts AST to PHP code
- **SecurityPolicy:** `inc/plugins/cortex/SecurityPolicy.php` - Enforces whitelist/blacklist
- **Runtime:** `inc/plugins/cortex/Runtime.php` - Wraps MyBB's templates object
- **Cache:** `inc/plugins/cortex/Cache.php` - Manages 3-tier caching system

Processing pipeline:
1. Template requested → Runtime intercepts
2. Check memory cache → return if hit
3. Check disk cache → return if hit and valid
4. Parse template → AST
5. Validate security → fail-safe to original
6. Compile to PHP → cache and execute
7. Return result

## Links

- [MyBB Playground Repository](https://github.com/yourusername/MyBB_Playground)
- [Corta Labs](https://cortalabs.com)
- [MyBB Plugin Development Docs](https://docs.mybb.com/1.8/development/plugins/)
- [Report Issues](https://github.com/yourusername/MyBB_Playground/issues)

---

**Last Updated:** 2026-01-18
**Version:** 1.0.0
**License:** MIT
