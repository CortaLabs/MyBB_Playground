# Cortex

Secure template conditionals and expressions for MyBB 1.8.x (PHP 8.1+)

## Overview

Cortex extends MyBB's template system with safe, sandboxed conditionals and expressions. Write dynamic templates without the security risks of raw PHP eval.

**Key Features:**
- Conditional blocks (`<if>`, `<else if>`, `<else>`)
- Inline expressions (`{= expression }`)
- Template variables (`<setvar>`)
- Function calls with whitelist security
- Nested template includes
- Compiled template caching

## Requirements

- MyBB 1.8.x
- PHP 8.1 or higher

## Installation

1. Copy contents of `inc/` to your MyBB installation's `inc/` directory
2. Go to Admin CP > Configuration > Plugins
3. Find "Cortex" and click Activate

No database tables or settings required.

## Syntax Reference

### Conditionals

Basic if/else:
```html
<if $mybb->user['uid'] > 0 then>
    Welcome back, {$mybb->user['username']}!
<else>
    Please login or register.
</if>
```

Else-if chains:
```html
<if $mybb->user['usergroup'] == 4 then>
    You are an Administrator
<else if $mybb->user['usergroup'] == 3 then>
    You are a Super Moderator
<else if $mybb->user['usergroup'] == 2 then>
    You are a Registered User
<else>
    You are a Guest
</if>
```

Nested conditionals:
```html
<if $mybb->user['uid'] > 0 then>
    <if $mybb->user['postnum'] > 100 then>
        You're a veteran!
    <else>
        Keep posting!
    </if>
<else>
    Login to see your stats.
</if>
```

### Expressions

Inline expressions output values directly:
```html
Board name: {= strtoupper($mybb->settings['bbname']) }
Current time: {= date('Y-m-d H:i:s') }
Posts per day: {= round($mybb->user['postnum'] / max(1, floor((time() - $mybb->user['regdate']) / 86400)), 2) }
```

Ternary expressions:
```html
Status: {= $mybb->user['uid'] > 0 ? 'Logged In' : 'Guest' }
```

### Template Variables

Set variables for use later in the template:
```html
<setvar greeting>Hello from Cortex!</setvar>
<setvar counter>42</setvar>
<setvar username>$mybb->user['username']</setvar>

Greeting: {= $GLOBALS['tplvars']['greeting'] }
Counter: {= $GLOBALS['tplvars']['counter'] }
```

Plain text values are auto-quoted. Use `$variable` or `"string"` for expressions.

### Function Calls

Wrap content in function output:
```html
<func strtoupper>hello world</func>
<!-- Outputs: HELLO WORLD -->
```

### Template Includes

Include other templates dynamically:
```html
<template my_custom_template>
```

## Allowed Functions

Cortex uses a security whitelist. Only these function categories are allowed:

**String Functions:**
`strlen`, `substr`, `strpos`, `strtolower`, `strtoupper`, `trim`, `ltrim`, `rtrim`, `str_replace`, `str_pad`, `sprintf`, `number_format`, `nl2br`, `strip_tags`, `htmlspecialchars`, `htmlentities`, `urlencode`, `urldecode`, `base64_encode`, `base64_decode`, `md5`, `sha1`, `strrev`, `ucfirst`, `ucwords`, `wordwrap`, `str_repeat`, `implode`, `explode`

**Array Functions:**
`count`, `array_key_exists`, `in_array`, `array_merge`, `array_keys`, `array_values`, `array_unique`, `array_reverse`, `array_slice`, `array_search`, `array_pop`, `array_shift`, `array_map`, `array_filter`, `array_column`, `array_combine`, `array_diff`, `array_intersect`, `sort`, `rsort`, `asort`, `arsort`, `ksort`, `krsort`, `usort`, `array_multisort`

**Math Functions:**
`abs`, `ceil`, `floor`, `round`, `max`, `min`, `pow`, `sqrt`, `rand`, `mt_rand`, `fmod`, `intval`, `floatval`, `number_format`

**Date/Time Functions:**
`date`, `time`, `strtotime`, `mktime`, `gmdate`, `checkdate`

**Type Functions:**
`isset`, `empty`, `is_array`, `is_string`, `is_numeric`, `is_int`, `is_float`, `is_bool`, `is_null`, `gettype`, `strval`, `intval`, `floatval`, `boolval`

**JSON Functions:**
`json_encode`, `json_decode`

**Misc:**
`printf` (via sprintf), `defined`, `constant`

## Security

Cortex blocks dangerous operations:
- No `eval()`, `exec()`, `system()`, `shell_exec()`, etc.
- No file operations (`file_get_contents`, `fopen`, etc.)
- No include/require
- No database access
- No object instantiation (`new`)
- No backticks or variable functions

Expressions are validated before compilation. Invalid or dangerous code is rejected.

## Configuration

Edit `inc/plugins/cortex/config.php`:

```php
return [
    'enabled' => true,           // Enable/disable Cortex processing
    'cache_enabled' => true,     // Cache compiled templates to disk
    'debug' => false,            // Log parse errors to PHP error log
    'security' => [
        'additional_allowed_functions' => [],  // Add custom allowed functions
        'denied_functions' => [],              // Block specific functions
        'max_nesting_depth' => 10,             // Max nested conditionals
        'max_expression_length' => 1000,       // Max expression length
    ],
];
```

## How It Works

1. **Hook**: Cortex hooks into `global_start` and wraps MyBB's `$templates` object
2. **Intercept**: When templates are retrieved, Cortex checks for its syntax
3. **Parse**: Templates with Cortex syntax are tokenized
4. **Compile**: Tokens are compiled to PHP expressions compatible with MyBB's eval
5. **Cache**: Compiled templates are cached to disk for performance
6. **Execute**: MyBB's normal eval() runs the compiled template

Templates without Cortex syntax pass through unchanged with zero overhead.

## Files

```
inc/plugins/
├── cortex.php                 # Main plugin file with autoloader
└── cortex/
    ├── config.php             # Configuration
    └── src/
        ├── Cache.php          # Disk cache with atomic writes
        ├── Compiler.php       # Token-to-PHP compiler
        ├── Parser.php         # Template tokenizer
        ├── Runtime.php        # Template wrapper
        ├── SecurityPolicy.php # Function whitelist
        ├── Token.php          # Token data class
        ├── TokenType.php      # Token type enum
        └── Exceptions/
            ├── CompileException.php
            ├── ParseException.php
            └── SecurityException.php
```

## Troubleshooting

**Syntax not processing:**
- Check that Cortex is activated in Admin CP
- Verify PHP 8.1+ (`php -v`)
- Check `config.php` has `'enabled' => true`

**Parse errors:**
- Enable debug mode in config.php
- Check PHP error log for "Cortex parse error" messages
- Verify balanced `<if>`/`</if>` tags

**Cache issues:**
- Ensure `cache/cortex/` directory exists and is writable
- Delete cache files to force recompilation

## License

MIT License - Corta Labs

## Credits

- **Author:** Corta Labs
- **Version:** 1.0.0
