---
id: cortex_audit-phase-plan
title: "\u2699\uFE0F Phase Plan \u2014 cortex-audit"
doc_name: phase_plan
category: engineering
status: draft
version: '0.1'
last_updated: '2026-01-18'
maintained_by: Corta Labs
created_by: Corta Labs
owners: []
related_docs: []
tags: []
summary: ''
---

# ⚙️ Phase Plan — cortex-audit
**Author:** Scribe
**Version:** Draft v0.1
**Status:** active
**Last Updated:** 2026-01-18 13:02:39 UTC

> Execution roadmap for cortex-audit.

---
## Phase Overview
<!-- ID: phase_overview -->
## Phase Overview

| Phase | Goal | Key Deliverables | Est. Time | Confidence |
|-------|------|------------------|-----------|------------|
| Phase 1 | MyBB Settings Integration | Settings group + 7 settings in _install/_uninstall | 30 min | 0.95 |
| Phase 2 | SecurityPolicy Enhancement | Constructor, denied_functions, expression length limit | 30 min | 0.95 |
| Phase 3 | Parser Nesting Depth | max_nesting_depth tracking and enforcement | 20 min | 0.90 |
| Phase 4 | Cache TTL | TTL parameter in Cache, expiration check in get() | 20 min | 0.95 |
| Phase 5 | Config Building | cortex_init() merges ACP settings with config.php fallback | 20 min | 0.90 |
| Phase 6 | Integration & Testing | Wire components, deploy, manual testing | 30 min | 0.85 |

**Total Estimated Time:** 2.5 hours

**Dependencies:**
- Phase 2-4 can be done in parallel (independent component changes)
- Phase 5 depends on Phase 1 (needs settings to exist)
- Phase 6 depends on all previous phases
<!-- ID: phase_0 -->
## Phase 1 - MyBB Settings Integration

**Objective:** Add MyBB ACP settings to Cortex plugin lifecycle.

**Files Modified:**
- `cortex.php` - Add _install(), _uninstall(), update _is_installed()
- `cortex.lang.php` - Add setting title/description strings

**Task Package 1.1: Add cortex_install() function**

**Scope:** Create setting group and 7 settings in database
**Lines to modify:** After line 142 (after cortex_uninstall)

```php
function cortex_install(): void
{
    global $db, $lang;
    $lang->load('cortex', false, true);

    // Create setting group
    $setting_group = [
        'name'        => 'cortex',
        'title'       => $lang->cortex_settings_title ?? 'Cortex Template Engine',
        'description' => $lang->cortex_settings_desc ?? 'Settings for the Cortex secure template conditionals plugin',
        'disporder'   => 100,
        'isdefault'   => 0
    ];
    $gid = $db->insert_query('settinggroups', $setting_group);

    // Settings array
    $settings = [
        ['name' => 'cortex_enabled', 'title' => 'Enable Cortex', 'description' => 'Enable or disable Cortex template processing', 'optionscode' => 'yesno', 'value' => '1', 'disporder' => 1],
        ['name' => 'cortex_debug_mode', 'title' => 'Debug Mode', 'description' => 'Log parsing errors to PHP error log', 'optionscode' => 'yesno', 'value' => '0', 'disporder' => 2],
        ['name' => 'cortex_cache_enabled', 'title' => 'Enable Cache', 'description' => 'Enable disk caching of compiled templates', 'optionscode' => 'yesno', 'value' => '1', 'disporder' => 3],
        ['name' => 'cortex_cache_ttl', 'title' => 'Cache TTL (seconds)', 'description' => 'Cache expiration time in seconds. 0 = never expires', 'optionscode' => 'numeric', 'value' => '0', 'disporder' => 4],
        ['name' => 'cortex_max_nesting_depth', 'title' => 'Max Nesting Depth', 'description' => 'Maximum nested if-block depth. 0 = unlimited', 'optionscode' => 'numeric', 'value' => '10', 'disporder' => 5],
        ['name' => 'cortex_max_expression_length', 'title' => 'Max Expression Length', 'description' => 'Maximum expression length in characters. 0 = unlimited', 'optionscode' => 'numeric', 'value' => '1000', 'disporder' => 6],
        ['name' => 'cortex_denied_functions', 'title' => 'Denied Functions', 'description' => 'Comma-separated list of functions to block (e.g., strlen,substr)', 'optionscode' => 'textarea', 'value' => '', 'disporder' => 7],
    ];

    foreach ($settings as $setting) {
        $setting['gid'] = $gid;
        $db->insert_query('settings', $setting);
    }

    rebuild_settings();
}
```

**Verification:**
- [ ] Settings group "cortex" created in mybb_settinggroups
- [ ] 7 settings created in mybb_settings with correct gid
- [ ] Settings visible in ACP > Configuration > Settings

**Task Package 1.2: Add cortex_uninstall() function**

**Scope:** Remove settings and setting group on uninstall
**Lines to modify:** Replace existing empty cortex_uninstall()

```php
function cortex_uninstall(): void
{
    global $db;

    // Remove settings
    $db->delete_query('settings', "name LIKE 'cortex_%'");

    // Remove setting group
    $db->delete_query('settinggroups', "name = 'cortex'");

    rebuild_settings();

    // Optionally clear cache directory
    $cacheDir = MYBB_ROOT . 'cache/cortex/';
    if (is_dir($cacheDir)) {
        $files = glob($cacheDir . '*.php');
        if ($files) {
            foreach ($files as $file) {
                @unlink($file);
            }
        }
    }
}
```

**Verification:**
- [ ] Settings removed from mybb_settings
- [ ] Setting group removed from mybb_settinggroups
- [ ] Cache directory cleaned

**Task Package 1.3: Update cortex_is_installed()**

**Scope:** Check if setting group exists
**Lines to modify:** Replace line 115-119

```php
function cortex_is_installed(): bool
{
    global $db;
    $query = $db->simple_select('settinggroups', 'gid', "name = 'cortex'", ['limit' => 1]);
    return (bool) $db->fetch_field($query, 'gid');
}
```

**Verification:**
- [ ] Returns true when settings exist
- [ ] Returns false when settings don't exist

**Task Package 1.4: Add language strings**

**Scope:** Add setting descriptions to language file
**File:** `cortex.lang.php`

```php
$l['cortex_settings_title'] = 'Cortex Template Engine';
$l['cortex_settings_desc'] = 'Settings for the Cortex secure template conditionals plugin';
```

**Verification:**
- [ ] Language strings loaded without errors
<!-- ID: phase_1 -->
## Phase 2 - SecurityPolicy Enhancement

**Objective:** Add constructor, denied functions support, and expression length validation.

**Files Modified:**
- `SecurityPolicy.php` - Add constructor, properties, modify methods
- `SecurityException.php` - Add expressionTooLong() factory method

**Task Package 2.1: Add SecurityPolicy constructor and properties**

**Scope:** Add constructor to accept and store configuration
**File:** `SecurityPolicy.php`
**Location:** After line 26 (after class declaration)

```php
/**
 * Additional allowed functions (from config)
 * @var array<string>
 */
private array $additionalAllowedFunctions = [];

/**
 * Denied functions (takes precedence over allowed)
 * @var array<string>
 */
private array $deniedFunctions = [];

/**
 * Maximum expression length (0 = unlimited)
 */
private int $maxExpressionLength = 0;

/**
 * Constructor
 *
 * @param array $additionalAllowed Additional functions to allow
 * @param array $denied Functions to deny (overrides allowed)
 * @param int $maxExpressionLength Maximum expression length
 */
public function __construct(
    array $additionalAllowed = [],
    array $denied = [],
    int $maxExpressionLength = 0
) {
    $this->additionalAllowedFunctions = array_map('strtolower', array_filter($additionalAllowed));
    $this->deniedFunctions = array_map('strtolower', array_filter($denied));
    $this->maxExpressionLength = $maxExpressionLength;
}
```

**Verification:**
- [ ] Constructor accepts three parameters
- [ ] Properties are initialized correctly
- [ ] array_filter removes empty strings from config

**Task Package 2.2: Modify isAllowedFunction()**

**Scope:** Check denied list before allowed list
**File:** `SecurityPolicy.php`
**Location:** Replace existing isAllowedFunction() at line 530

```php
public function isAllowedFunction(string $func): bool
{
    $func = strtolower(trim($func));
    
    // Denied list takes precedence
    if (in_array($func, $this->deniedFunctions, true)) {
        return false;
    }
    
    // Check built-in whitelist
    if (in_array($func, self::ALLOWED_FUNCTIONS, true)) {
        return true;
    }
    
    // Check additional allowed functions from config
    return in_array($func, $this->additionalAllowedFunctions, true);
}
```

**Verification:**
- [ ] Denied functions return false even if in ALLOWED_FUNCTIONS
- [ ] Additional allowed functions work when not in built-in list
- [ ] Built-in whitelist still works

**Task Package 2.3: Modify validateExpression() for length check**

**Scope:** Add expression length validation at start of method
**File:** `SecurityPolicy.php`
**Location:** Add at start of validateExpression() (line 546)

```php
public function validateExpression(string $expr): string
{
    // Check expression length first (before unescaping)
    if ($this->maxExpressionLength > 0 && strlen($expr) > $this->maxExpressionLength) {
        throw SecurityException::expressionTooLong(strlen($expr), $this->maxExpressionLength);
    }

    // Unescape MyBB's addslashes() escaping
    $unescaped = $this->unescape($expr);
    
    // ... rest of existing validation ...
}
```

**Verification:**
- [ ] Expressions under limit pass through
- [ ] Expressions over limit throw SecurityException
- [ ] Limit of 0 means no limit

**Task Package 2.4: Add SecurityException::expressionTooLong()**

**Scope:** Add factory method for expression length errors
**File:** `SecurityException.php`

```php
/**
 * Create exception for expression too long
 *
 * @param int $actual Actual length
 * @param int $max Maximum allowed
 * @return self
 */
public static function expressionTooLong(int $actual, int $max): self
{
    return new self(
        "Expression too long: {$actual} characters exceeds maximum of {$max}",
        self::CODE_EXPRESSION_TOO_LONG
    );
}

// Add constant
public const CODE_EXPRESSION_TOO_LONG = 4;
```

**Verification:**
- [ ] Exception creates with correct message
- [ ] Exception has unique error code
<!-- ID: milestone_tracking -->
## Phase 3 - Parser Nesting Depth

**Objective:** Add max nesting depth tracking and enforcement.

**Files Modified:**
- `Parser.php` - Add property, modify constructor, update validateStructure()
- `ParseException.php` - Add nestingTooDeep() factory method

**Task Package 3.1: Add Parser constructor and property**

**Scope:** Accept SecurityPolicy and max nesting depth
**File:** `Parser.php`
**Location:** Add after line 104 (after $templateName property)

```php
/**
 * Maximum nesting depth for if blocks (0 = unlimited)
 */
private int $maxNestingDepth = 0;

/**
 * Constructor
 *
 * @param SecurityPolicy $security Security policy instance
 * @param int $maxNestingDepth Maximum nesting depth (0 = unlimited)
 */
public function __construct(SecurityPolicy $security, int $maxNestingDepth = 0)
{
    $this->maxNestingDepth = $maxNestingDepth;
}
```

**Note:** Parser currently has no constructor - we're adding one. The SecurityPolicy parameter is for future use (already passed from Runtime).

**Verification:**
- [ ] Constructor accepts max depth parameter
- [ ] Property initialized correctly

**Task Package 3.2: Modify validateStructure() for depth tracking**

**Scope:** Track nesting depth and enforce limit
**File:** `Parser.php`
**Location:** Modify validateStructure() starting at line 257

```php
private function validateStructure(array $tokens): void
{
    $ifStack = [];
    $funcStack = [];

    foreach ($tokens as $token) {
        switch ($token->type) {
            case TokenType::IF_OPEN:
                $ifStack[] = $token;
                $currentDepth = count($ifStack);
                
                // Check nesting depth limit
                if ($this->maxNestingDepth > 0 && $currentDepth > $this->maxNestingDepth) {
                    throw ParseException::nestingTooDeep(
                        $currentDepth,
                        $this->maxNestingDepth,
                        $token->position,
                        $this->templateName
                    );
                }
                break;
            
            // ... rest of cases unchanged ...
        }
    }
    
    // ... rest of validation unchanged ...
}
```

**Verification:**
- [ ] Depth tracked correctly as if blocks are pushed
- [ ] Exception thrown when depth exceeds limit
- [ ] Limit of 0 means no limit checking

**Task Package 3.3: Add ParseException::nestingTooDeep()**

**Scope:** Add factory method for nesting depth errors
**File:** `ParseException.php`

```php
/**
 * Create exception for nesting too deep
 *
 * @param int $actual Actual depth
 * @param int $max Maximum allowed
 * @param int $position Position in template
 * @param string|null $templateName Template name
 * @return self
 */
public static function nestingTooDeep(int $actual, int $max, int $position, ?string $templateName = null): self
{
    $context = $templateName ? " in template '{$templateName}'" : '';
    return new self(
        "Nesting too deep: {$actual} levels exceeds maximum of {$max}{$context} at position {$position}"
    );
}
```

**Verification:**
- [ ] Exception creates with correct message
- [ ] Template name included when provided

---

## Phase 4 - Cache TTL

**Objective:** Add TTL support to disk cache.

**Files Modified:**
- `Cache.php` - Add TTL property, modify constructor and get()

**Task Package 4.1: Add TTL to Cache constructor**

**Scope:** Accept and store TTL parameter
**File:** `Cache.php`
**Location:** Modify constructor starting at line 44

```php
/**
 * Cache TTL in seconds (0 = no expiration)
 */
private int $ttl = 0;

/**
 * Constructor
 *
 * @param string $cacheDir Path to cache directory
 * @param int $ttl Cache TTL in seconds (0 = no expiration)
 */
public function __construct(string $cacheDir, int $ttl = 0)
{
    // Ensure trailing slash
    $this->cacheDir = rtrim($cacheDir, '/\\') . '/';
    $this->ttl = $ttl;

    // Auto-create directory if missing
    if (!is_dir($this->cacheDir)) {
        @mkdir($this->cacheDir, 0755, true);
    }

    // Set writable flag
    $this->writable = is_dir($this->cacheDir) && is_writable($this->cacheDir);
}
```

**Verification:**
- [ ] TTL parameter accepted
- [ ] Property initialized correctly
- [ ] Existing functionality unchanged when TTL=0

**Task Package 4.2: Modify get() for TTL check**

**Scope:** Check file modification time against TTL
**File:** `Cache.php`
**Location:** Modify get() starting at line 66

```php
public function get(string $title, string $hash, ?int $tid = null): ?string
{
    $cacheKey = $this->buildCacheKey($title, $hash, $tid);
    $cacheFile = $this->buildCachePath($title, $hash, $tid);

    // Check memory cache first
    if (isset($this->memoryCache[$cacheKey])) {
        return $this->memoryCache[$cacheKey];
    }

    // Check disk cache
    if (!is_file($cacheFile)) {
        return null;
    }

    // TTL check - if TTL is set and file is expired, treat as cache miss
    if ($this->ttl > 0) {
        $mtime = @filemtime($cacheFile);
        if ($mtime !== false && (time() - $mtime) > $this->ttl) {
            // Cache expired - delete stale file and return miss
            @unlink($cacheFile);
            return null;
        }
    }

    $content = @file_get_contents($cacheFile);
    if ($content === false) {
        return null;
    }

    // Store in memory cache for subsequent requests
    $this->memoryCache[$cacheKey] = $content;

    return $content;
}
```

**Verification:**
- [ ] Files older than TTL are deleted and return null
- [ ] Files younger than TTL are returned normally
- [ ] TTL of 0 means no expiration check
- [ ] Memory cache bypasses TTL check (single request scope)

---

## Phase 5 - Config Building

**Objective:** Merge ACP settings with config.php fallback in cortex_init().

**Files Modified:**
- `cortex.php` - Modify cortex_init() to build config from $mybb->settings
- `Runtime.php` - Pass config to components correctly

**Task Package 5.1: Modify cortex_init() config building**

**Scope:** Build config array from ACP settings with file fallback
**File:** `cortex.php`
**Location:** Replace lines 175-185 in cortex_init()

```php
function cortex_init(): void
{
    global $templates, $lang, $mybb;

    // Load language file
    $lang->load('cortex', false, true);

    // Don't run in Admin CP
    if (defined('IN_ADMINCP')) {
        return;
    }

    // Ensure templates object exists and is valid
    if (!is_object($templates)) {
        return;
    }

    // Don't wrap if already wrapped
    if ($templates instanceof \Cortex\Runtime) {
        return;
    }

    // Load file-based config as defaults
    $fileConfig = require CORTEX_PATH . 'config.php';
    
    // Build config from MyBB settings with file fallback
    $config = [
        'enabled' => isset($mybb->settings['cortex_enabled']) 
            ? (bool)$mybb->settings['cortex_enabled'] 
            : ($fileConfig['enabled'] ?? true),
        'cache_enabled' => isset($mybb->settings['cortex_cache_enabled'])
            ? (bool)$mybb->settings['cortex_cache_enabled']
            : ($fileConfig['cache_enabled'] ?? true),
        'cache_ttl' => isset($mybb->settings['cortex_cache_ttl'])
            ? (int)$mybb->settings['cortex_cache_ttl']
            : ($fileConfig['cache_ttl'] ?? 0),
        'debug' => isset($mybb->settings['cortex_debug_mode'])
            ? (bool)$mybb->settings['cortex_debug_mode']
            : ($fileConfig['debug'] ?? false),
        'security' => [
            'additional_allowed_functions' => $fileConfig['security']['additional_allowed_functions'] ?? [],
            'denied_functions' => isset($mybb->settings['cortex_denied_functions'])
                ? array_filter(array_map('trim', explode(',', $mybb->settings['cortex_denied_functions'])))
                : ($fileConfig['security']['denied_functions'] ?? []),
            'max_nesting_depth' => isset($mybb->settings['cortex_max_nesting_depth'])
                ? (int)$mybb->settings['cortex_max_nesting_depth']
                : ($fileConfig['security']['max_nesting_depth'] ?? 10),
            'max_expression_length' => isset($mybb->settings['cortex_max_expression_length'])
                ? (int)$mybb->settings['cortex_max_expression_length']
                : ($fileConfig['security']['max_expression_length'] ?? 1000),
        ],
    ];

    // Skip if disabled
    if (empty($config['enabled'])) {
        return;
    }

    // Wrap templates with Cortex Runtime
    try {
        $runtime = new \Cortex\Runtime($templates, $config);
        $templates = $runtime;
    } catch (\Throwable $e) {
        if (!empty($config['debug'])) {
            error_log('Cortex initialization failed: ' . $e->getMessage());
        }
    }
}
```

**Verification:**
- [ ] ACP settings override file config when present
- [ ] File config used as fallback when ACP settings missing
- [ ] denied_functions parsed from comma-separated string
- [ ] Empty strings filtered from denied_functions array

**Task Package 5.2: Modify Runtime constructor to pass config**

**Scope:** Pass new config options to components
**File:** `Runtime.php`
**Location:** Modify constructor starting at line 94

```php
// Initialize SecurityPolicy with denied functions and expression length
$this->security = new SecurityPolicy(
    $config['security']['additional_allowed_functions'] ?? [],
    $config['security']['denied_functions'] ?? [],
    $config['security']['max_expression_length'] ?? 0
);

// Initialize Parser with nesting depth limit
$this->parser = new Parser(
    $this->security,
    $config['security']['max_nesting_depth'] ?? 0
);

$this->compiler = new Compiler($this->security);

// Initialize disk cache with TTL
$cacheDir = MYBB_ROOT . 'cache/cortex/';
$cacheTtl = $config['cache_ttl'] ?? 0;
$this->diskCache = new Cache($cacheDir, $cacheTtl);
```

**Verification:**
- [ ] SecurityPolicy receives denied_functions and max_expression_length
- [ ] Parser receives max_nesting_depth
- [ ] Cache receives cache_ttl

---

## Phase 6 - Integration & Testing

**Objective:** Wire all components together, deploy, and verify.

**Tasks:**

**Task 6.1: Deploy updated plugin**
```bash
mybb_plugin_uninstall("cortex", uninstall=true)
mybb_plugin_install("cortex")
```

**Task 6.2: Verify settings in ACP**
- Navigate to Admin CP > Configuration > Settings
- Verify "Cortex Template Engine" group exists
- Verify all 7 settings present with correct defaults

**Task 6.3: Test each configuration option**

1. **cortex_enabled**: Toggle off, verify Cortex syntax not processed
2. **cortex_debug_mode**: Enable, create parsing error, check error log
3. **cortex_cache_enabled**: Toggle off, verify cache files not created
4. **cortex_cache_ttl**: Set to 60s, verify cache expires
5. **cortex_max_nesting_depth**: Set to 3, test with 4 nested ifs
6. **cortex_max_expression_length**: Set to 50, test long expression
7. **cortex_denied_functions**: Add "strlen", test {= strlen($x) }

**Task 6.4: Verify upgrade path**
- Backup current settings
- Remove settings manually from DB
- Reinstall plugin
- Verify config.php fallback works
- Verify new settings created

**Verification Checklist:**
- [ ] All 7 settings appear in ACP
- [ ] Settings persist across page reloads
- [ ] Each setting affects behavior correctly
- [ ] Config.php fallback works when settings missing
- [ ] No PHP errors in error log
- [ ] Existing templates continue working

---

## Milestone Tracking

| Milestone | Target Date | Owner | Status | Evidence |
|-----------|-------------|-------|--------|----------|
| Architecture Complete | 2026-01-18 | Architect | Complete | ARCHITECTURE_GUIDE.md |
| Phase 1 Complete | TBD | Coder | Pending | Settings in ACP |
| Phase 2 Complete | TBD | Coder | Pending | SecurityPolicy working |
| Phase 3 Complete | TBD | Coder | Pending | Nesting depth enforced |
| Phase 4 Complete | TBD | Coder | Pending | Cache TTL working |
| Phase 5 Complete | TBD | Coder | Pending | Config merging works |
| Phase 6 Complete | TBD | Coder | Pending | All tests pass |
<!-- ID: retro_notes -->
- Summarise lessons learned after each phase completes.  
- Document any scope changes or re-planning decisions here.


---