---
id: cortex_audit-architecture
title: "\U0001F3D7\uFE0F Architecture Guide \u2014 cortex-audit"
doc_name: architecture
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

# 🏗️ Architecture Guide — cortex-audit
**Author:** Scribe
**Version:** Draft v0.1
**Status:** Draft
**Last Updated:** 2026-01-18 13:02:39 UTC

> Architecture guide for cortex-audit.

---
## 1. Problem Statement
<!-- ID: problem_statement -->
## 1. Problem Statement

**Context:** The Cortex plugin provides secure template conditionals for MyBB 1.8.x. It currently uses a file-based configuration system (`config.php`) with 7 configuration options defined, but only 3 are actually implemented. Additionally, file-based config requires FTP/SSH access to modify, which is not accessible to forum administrators.

**Current State:**
- `config.php` defines: `enabled`, `cache_enabled`, `cache_ttl`, `debug`, `additional_allowed_functions`, `denied_functions`, `max_nesting_depth`, `max_expression_length`
- Actually implemented: `enabled`, `cache_enabled`, `debug`
- NOT implemented: `cache_ttl`, `denied_functions`, `max_nesting_depth`, `max_expression_length`
- BUG: SecurityPolicy has no constructor - Runtime.php passes constructor arguments that are silently ignored

**Goals:**
1. Implement all 4 missing configuration options
2. Migrate configuration from `config.php` to MyBB ACP Settings
3. Allow admins to configure Cortex through Admin CP > Configuration > Settings
4. Maintain `config.php` as fallback defaults for upgrades

**Non-Goals:**
- Changing Cortex's core parsing/compilation logic
- Adding new template syntax features
- Modifying the security whitelist/blacklist (beyond making denied_functions configurable)

**Success Metrics:**
- All 7 configuration options work as documented
- Settings visible and editable in MyBB Admin CP
- Existing Cortex installations continue working after upgrade
- cache_ttl actually expires cached templates
- denied_functions actually blocks specified functions
- max_nesting_depth prevents deeply nested conditionals
- max_expression_length rejects oversized expressions
<!-- ID: requirements_constraints -->
## 2. Requirements & Constraints

**Functional Requirements:**
1. **MyBB Settings Integration**
   - Create setting group "Cortex Template Engine" in ACP
   - 7 settings: enabled, debug_mode, cache_enabled, cache_ttl, max_nesting_depth, max_expression_length, denied_functions
   - Settings created on `_install()`, removed on `_uninstall()`
   - `rebuild_settings()` called after changes

2. **cache_ttl Implementation**
   - Cache.php `get()` must check file modification time against TTL
   - TTL of 0 = never expires (current behavior)
   - TTL > 0 = expire cache files older than TTL seconds

3. **denied_functions Implementation**
   - SecurityPolicy needs constructor to accept denied_functions array
   - `isAllowedFunction()` must check denied list BEFORE allowed list
   - Denied functions from settings override config.php defaults

4. **max_nesting_depth Implementation**
   - Parser must track nesting depth of `<if>` blocks
   - Throw ParseException if depth exceeds configured limit
   - Limit of 0 = unlimited (current behavior)

5. **max_expression_length Implementation**
   - Validate expression length before parsing
   - Throw SecurityException if length exceeds limit
   - Limit of 0 = unlimited (current behavior)

**Non-Functional Requirements:**
- Backward compatible: existing installations must continue working
- No performance degradation for templates not using limits
- Config.php remains as fallback when settings not present
- Clear error messages when limits are exceeded

**Assumptions:**
- MyBB 1.8.x database schema unchanged
- Plugin has write access to settings/settinggroups tables
- PHP 8.1+ (already required by Cortex)

**Constraints:**
- Cannot modify MyBB core files
- Must use MyBB's standard settings API
- Settings must work with MyBB's cache system

**Risks & Mitigations:**
| Risk | Mitigation |
|------|------------|
| Settings not present after upgrade | Fall back to config.php values |
| Cache TTL checking impacts performance | Only check TTL on disk cache read, not memory cache |
| Breaking existing templates with new limits | Default limits match current unlimited behavior |
<!-- ID: architecture_overview -->
## 3. Architecture Overview

**Solution Summary:** Migrate Cortex configuration from file-based (`config.php`) to MyBB ACP Settings while implementing the 4 missing configuration options. The settings are read at runtime and merged with config.php defaults, allowing both admin-friendly configuration and fallback behavior.

**Component Breakdown:**

1. **cortex.php (Main Plugin File)**
   - Add `cortex_install()`: Create setting group and 7 settings
   - Add `cortex_uninstall()`: Remove settings and setting group
   - Modify `cortex_init()`: Build config array from `$mybb->settings` with config.php fallback
   - Update `cortex_is_installed()`: Check if setting group exists

2. **SecurityPolicy.php**
   - ADD constructor: `__construct(array $additionalAllowed = [], array $denied = [])`
   - ADD properties: `$additionalAllowedFunctions`, `$deniedFunctions`
   - MODIFY `isAllowedFunction()`: Check denied list first, then combined allowed list

3. **Parser.php**
   - ADD property: `$maxNestingDepth`
   - ADD method: `setMaxNestingDepth(int $depth)`
   - MODIFY `validateStructure()`: Track and enforce nesting depth

4. **Cache.php**
   - ADD property: `$ttl`
   - MODIFY constructor: Accept TTL parameter
   - MODIFY `get()`: Check file mtime against TTL before returning cached content

5. **Runtime.php**
   - MODIFY constructor: Pass `max_nesting_depth` to Parser
   - MODIFY constructor: Pass `cache_ttl` to Cache
   - MODIFY constructor: Pass `max_expression_length` to SecurityPolicy

6. **config.php**
   - NO CHANGES: Remains as default values and fallback

**Data Flow:**
```
MyBB Admin CP Settings
         │
         ▼
┌─────────────────────────────────────┐
│  cortex_init() in cortex.php        │
│  - Read $mybb->settings['cortex_*'] │
│  - Fallback to config.php defaults  │
│  - Build merged config array        │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Runtime constructor                 │
│  - Pass config to SecurityPolicy    │
│  - Pass config to Parser            │
│  - Pass config to Cache             │
└─────────────────────────────────────┘
         │
         ├──────────────────┬──────────────────┐
         ▼                  ▼                  ▼
   SecurityPolicy       Parser              Cache
   - denied_functions   - max_nesting       - cache_ttl
   - additional_allowed - depth tracking    - TTL check
```

**External Integrations:**
- MyBB settings table (`mybb_settings`)
- MyBB setting groups table (`mybb_settinggroups`)
- MyBB settings cache (`$mybb->settings`)
<!-- ID: detailed_design -->
## 4. Detailed Design

### 4.1 MyBB Settings Schema

**Setting Group:**
```php
$setting_group = [
    'name'        => 'cortex',
    'title'       => 'Cortex Template Engine',
    'description' => 'Settings for the Cortex secure template conditionals plugin',
    'disporder'   => 100,
    'isdefault'   => 0
];
```

**Settings:**
| Name | Title | Type | Default | Description |
|------|-------|------|---------|-------------|
| `cortex_enabled` | Enable Cortex | yesno | 1 | Enable/disable Cortex template processing |
| `cortex_debug_mode` | Debug Mode | yesno | 0 | Log parsing errors to PHP error log |
| `cortex_cache_enabled` | Enable Cache | yesno | 1 | Enable disk caching of compiled templates |
| `cortex_cache_ttl` | Cache TTL (seconds) | numeric | 0 | Cache expiration time. 0 = never expires |
| `cortex_max_nesting_depth` | Max Nesting Depth | numeric | 10 | Maximum nested if-block depth. 0 = unlimited |
| `cortex_max_expression_length` | Max Expression Length | numeric | 1000 | Maximum expression characters. 0 = unlimited |
| `cortex_denied_functions` | Denied Functions | textarea | (empty) | Comma-separated list of functions to block |

### 4.2 SecurityPolicy Changes

**New Constructor:**
```php
private array $additionalAllowedFunctions = [];
private array $deniedFunctions = [];
private int $maxExpressionLength = 0;

public function __construct(
    array $additionalAllowed = [],
    array $denied = [],
    int $maxExpressionLength = 0
) {
    $this->additionalAllowedFunctions = array_map('strtolower', $additionalAllowed);
    $this->deniedFunctions = array_map('strtolower', $denied);
    $this->maxExpressionLength = $maxExpressionLength;
}
```

**Modified isAllowedFunction():**
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
    
    // Check additional allowed functions
    return in_array($func, $this->additionalAllowedFunctions, true);
}
```

**Modified validateExpression():**
```php
public function validateExpression(string $expr): string
{
    // Check expression length first
    if ($this->maxExpressionLength > 0 && strlen($expr) > $this->maxExpressionLength) {
        throw SecurityException::expressionTooLong(strlen($expr), $this->maxExpressionLength);
    }
    
    // ... existing validation ...
}
```

### 4.3 Parser Changes

**New Properties and Methods:**
```php
private int $maxNestingDepth = 0;
private SecurityPolicy $security;

public function __construct(SecurityPolicy $security, int $maxNestingDepth = 0)
{
    $this->security = $security;
    $this->maxNestingDepth = $maxNestingDepth;
}
```

**Modified validateStructure():**
```php
private function validateStructure(array $tokens): void
{
    $ifStack = [];
    $funcStack = [];
    $maxDepthReached = 0;

    foreach ($tokens as $token) {
        switch ($token->type) {
            case TokenType::IF_OPEN:
                $ifStack[] = $token;
                $currentDepth = count($ifStack);
                $maxDepthReached = max($maxDepthReached, $currentDepth);
                
                // Check nesting depth limit
                if ($this->maxNestingDepth > 0 && $currentDepth > $this->maxNestingDepth) {
                    throw ParseException::nestingTooDeep($currentDepth, $this->maxNestingDepth, $token->position, $this->templateName);
                }
                break;
            // ... rest unchanged ...
        }
    }
}
```

### 4.4 Cache Changes

**Modified Constructor:**
```php
private int $ttl = 0;

public function __construct(string $cacheDir, int $ttl = 0)
{
    $this->cacheDir = rtrim($cacheDir, '/\\') . '/';
    $this->ttl = $ttl;
    // ... rest unchanged ...
}
```

**Modified get():**
```php
public function get(string $title, string $hash, ?int $tid = null): ?string
{
    // ... memory cache check unchanged ...
    
    // Check disk cache
    if (!is_file($cacheFile)) {
        return null;
    }
    
    // TTL check - if TTL is set and file is expired, treat as cache miss
    if ($this->ttl > 0) {
        $mtime = filemtime($cacheFile);
        if ($mtime !== false && (time() - $mtime) > $this->ttl) {
            // Cache expired - delete and return miss
            @unlink($cacheFile);
            return null;
        }
    }
    
    // ... rest unchanged ...
}
```

### 4.5 Runtime Changes

**Modified Constructor:**
```php
public function __construct(\templates $original, array $config = [])
{
    // ... property copying unchanged ...
    
    $this->config = $config;
    $this->enabled = $config['enabled'] ?? true;

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
}
```

### 4.6 cortex_init() Config Building

```php
function cortex_init(): void
{
    global $templates, $lang, $mybb;

    // ... existing checks unchanged ...

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

    // ... rest unchanged ...
}
```
<!-- ID: directory_structure -->
## 5. Directory Structure

```
plugin_manager/plugins/public/cortex/
├── inc/
│   ├── plugins/
│   │   ├── cortex.php                 # Main plugin - MODIFY for settings
│   │   └── cortex/
│   │       ├── config.php             # Default config - NO CHANGES
│   │       └── src/
│   │           ├── Cache.php          # MODIFY: Add TTL support
│   │           ├── Compiler.php       # NO CHANGES
│   │           ├── Parser.php         # MODIFY: Add nesting depth limit
│   │           ├── Runtime.php        # MODIFY: Pass config to components
│   │           ├── SecurityPolicy.php # MODIFY: Add constructor, denied list
│   │           ├── Token.php          # NO CHANGES
│   │           ├── TokenType.php      # NO CHANGES
│   │           └── Exceptions/
│   │               ├── ParseException.php     # MODIFY: Add nestingTooDeep()
│   │               └── SecurityException.php  # MODIFY: Add expressionTooLong()
│   └── languages/english/
│       └── cortex.lang.php            # MODIFY: Add setting descriptions
└── meta.json                          # NO CHANGES

TestForum/inc/plugins/cortex/         # Deployed copy (via mybb_plugin_install)
```

**Files Modified (8 total):**
1. `cortex.php` - Add settings lifecycle, modify config building
2. `Cache.php` - Add TTL property and expiration check
3. `Parser.php` - Add nesting depth tracking and limit
4. `Runtime.php` - Pass new config options to components
5. `SecurityPolicy.php` - Add constructor, denied functions, expression length
6. `ParseException.php` - Add `nestingTooDeep()` factory method
7. `SecurityException.php` - Add `expressionTooLong()` factory method
8. `cortex.lang.php` - Add language strings for settings
<!-- ID: data_storage -->
## 6. Data & Storage

**Database Tables Used:**
- `mybb_settinggroups` - Stores Cortex setting group (1 row)
- `mybb_settings` - Stores 7 Cortex settings

**Settings Storage:**
```sql
-- Setting group (created in _install)
INSERT INTO mybb_settinggroups (name, title, description, disporder, isdefault)
VALUES ('cortex', 'Cortex Template Engine', '...', 100, 0);

-- Settings (created in _install)
INSERT INTO mybb_settings (name, title, description, optionscode, value, disporder, gid)
VALUES ('cortex_enabled', '...', '...', 'yesno', '1', 1, {gid});
-- ... 6 more settings ...
```

**Cache:**
- Compiled templates: `cache/cortex/{tid}_{template}_{hash}.php`
- TTL check uses file modification time (`filemtime()`)
- No database caching - disk cache only

**Runtime Access:**
- Settings loaded via `$mybb->settings['cortex_*']` (cached by MyBB)
- File config loaded via `require CORTEX_PATH . 'config.php'`
- Merged config passed to Runtime constructor
<!-- ID: testing_strategy -->
## 7. Testing & Validation Strategy

**Manual Testing (via MyBB Admin CP):**

1. **Settings Installation Test**
   - Install plugin via ACP > Configuration > Plugins
   - Verify "Cortex Template Engine" appears in Settings
   - Verify all 7 settings are present with correct defaults

2. **Settings Modification Test**
   - Change each setting value in ACP
   - Verify changes persist after page reload
   - Test yesno toggles, numeric inputs, textarea

3. **cache_ttl Test**
   - Set cache_ttl to 60 seconds
   - Load a page with Cortex templates (creates cache)
   - Wait 70 seconds, reload
   - Verify cache file was regenerated (check mtime)

4. **denied_functions Test**
   - Add "strlen" to denied functions in settings
   - Create template: `{= strlen($test) }`
   - Verify template returns original (function blocked)
   - Remove "strlen", verify template works again

5. **max_nesting_depth Test**
   - Set max_nesting_depth to 3
   - Create template with 4 nested `<if>` blocks
   - Verify ParseException is thrown (graceful fallback)
   - Set to 0 (unlimited), verify deep nesting works

6. **max_expression_length Test**
   - Set max_expression_length to 50
   - Create expression longer than 50 chars
   - Verify SecurityException is thrown
   - Set to 0, verify long expressions work

7. **Upgrade Compatibility Test**
   - Install old version (without settings)
   - Upgrade to new version
   - Verify config.php fallback values work
   - Install settings, verify ACP values override

**Verification Commands:**
```sql
-- Check settings exist
SELECT * FROM mybb_settings WHERE name LIKE 'cortex_%';

-- Check setting group exists  
SELECT * FROM mybb_settinggroups WHERE name = 'cortex';
```
<!-- ID: deployment_operations -->
## 8. Deployment & Operations

**Development Workflow:**
1. Edit files in `plugin_manager/plugins/public/cortex/`
2. Deploy with `mybb_plugin_install("cortex")` 
3. Test in browser at `http://localhost:8022`

**Deployment Steps:**
1. Make changes to workspace files
2. Run `mybb_plugin_uninstall("cortex", uninstall=true)` to remove old settings
3. Run `mybb_plugin_install("cortex")` to deploy and activate
4. Verify settings appear in ACP > Configuration > Settings

**Upgrade Path (Existing Installations):**
1. User uploads new plugin files
2. User deactivates plugin in ACP (runs _deactivate)
3. User reactivates plugin in ACP (runs _activate)
4. Settings created on first activation after upgrade
5. Config.php values used as defaults for new settings

**Cache Management:**
- Clear cache after code changes: `cortex_clear_cache()`
- ACP hooks auto-clear cache on template edits
- Cache directory: `TestForum/cache/cortex/`

**Troubleshooting:**
| Issue | Resolution |
|-------|------------|
| Settings not appearing | Check `_install()` ran - reinstall plugin |
| Config changes not taking effect | Clear cache, check `$mybb->settings` populated |
| Old cached templates | Delete `cache/cortex/*.php` files |
<!-- ID: open_questions -->
## 9. Open Questions & Follow-Ups

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Should additional_allowed_functions be ACP configurable? | Architect | DECIDED: NO | Security risk - keep in config.php only |
| Settings in _install or _activate? | Architect | DECIDED: _install | Standard MyBB pattern, settings persist across deactivate |
| Default max_nesting_depth value? | Architect | DECIDED: 10 | Matches config.php, reasonable limit |
| Default max_expression_length? | Architect | DECIDED: 1000 | Matches config.php, allows complex expressions |
| ParseException vs SecurityException for nesting? | Architect | DECIDED: ParseException | Nesting is a structural issue, not security |
<!-- ID: references_appendix -->
## 10. References & Appendix

**Research Documents:**
- `RESEARCH_CORTEX_AUDIT_20260118_1304.md` - Initial Cortex audit findings

**Source Files (Workspace):**
- `plugin_manager/plugins/public/cortex/inc/plugins/cortex.php`
- `plugin_manager/plugins/public/cortex/inc/plugins/cortex/config.php`
- `plugin_manager/plugins/public/cortex/inc/plugins/cortex/src/Runtime.php`
- `plugin_manager/plugins/public/cortex/inc/plugins/cortex/src/Parser.php`
- `plugin_manager/plugins/public/cortex/inc/plugins/cortex/src/SecurityPolicy.php`
- `plugin_manager/plugins/public/cortex/inc/plugins/cortex/src/Cache.php`

**Reference Implementation:**
- `TestForum/inc/plugins/dice_roller.php` - MyBB settings pattern reference

**MyBB Documentation:**
- [Plugin Development](https://docs.mybb.com/1.8/development/plugins/)
- [Plugin Settings](https://docs.mybb.com/1.8/development/plugins/settings/)

**Progress Log:**
- `PROGRESS_LOG.md` - Development progress and decisions
