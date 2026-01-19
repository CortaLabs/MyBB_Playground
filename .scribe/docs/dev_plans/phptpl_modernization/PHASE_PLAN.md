---
id: phptpl_modernization-phase-plan
title: "\u2699\uFE0F Phase Plan \u2014 phptpl-modernization"
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

# ⚙️ Phase Plan — phptpl-modernization
**Author:** Scribe
**Version:** Draft v0.1
**Status:** active
**Last Updated:** 2026-01-18 09:56:19 UTC

> Execution roadmap for phptpl-modernization.

---
## Phase Overview
<!-- ID: phase_overview -->
| Phase | Goal | Key Deliverables | Est. Effort | Confidence |
|-------|------|------------------|-------------|------------|
| Phase 0 | Project scaffold | Plugin workspace, meta.json, file structure | 2 hours | 0.95 |
| Phase 1 | Core parsing | TokenType enum, Token class, Parser | 4 hours | 0.90 |
| Phase 2 | Security policy | SecurityPolicy class, whitelist, validation | 3 hours | 0.92 |
| Phase 3 | Compilation | Compiler class, all token handlers | 4 hours | 0.88 |
| Phase 4 | Runtime integration | Runtime class, hook registration, caching | 4 hours | 0.85 |
| Phase 5 | Testing & QA | Unit tests, integration tests, manual QA | 4 hours | 0.90 |
| Phase 6 | Documentation | README, migration guide, MCP tool (optional) | 2 hours | 0.95 |

**Total Estimated Effort:** ~23 hours
**Overall Confidence:** 0.90

### Phase Dependencies

```
Phase 0 (Scaffold)
    |
    v
Phase 1 (Parser)
    |
    v
Phase 2 (Security)
    |
    v
Phase 3 (Compiler)
    |
    v
Phase 4 (Runtime)
    |
    v
Phase 5 (Testing)
    |
    v
Phase 6 (Docs)
```

Each phase builds on the previous. Testing is deferred to Phase 5 to allow integration testing of all components together.
<!-- ID: phase_0 -->
**Objective:** Create plugin workspace with proper directory structure and metadata.

**Scope:**
- Create `plugin_manager/plugins/public/phptpl/` directory structure
- Create `meta.json` with plugin metadata
- Create placeholder PHP files with proper namespacing
- Create `phpunit.xml` and `composer.json` for testing

### Task Package 0.1: Create Directory Structure

**Files to Create:**
```
plugin_manager/plugins/public/phptpl/
├── inc/
│   ├── plugins/
│   │   ├── phptpl.php
│   │   └── phptpl/
│   │       ├── src/
│   │       │   └── .gitkeep
│   │       └── config.php
│   └── languages/
│       └── english/
│           └── phptpl.lang.php
├── tests/
│   └── .gitkeep
├── meta.json
├── composer.json
├── phpunit.xml
└── README.md
```

**Verification:**
- [ ] All directories exist
- [ ] `meta.json` contains valid JSON
- [ ] `phptpl.php` has basic plugin structure

### Task Package 0.2: Create meta.json

```json
{
  "codename": "phptpl",
  "display_name": "PHP Templates Modernized",
  "version": "3.0.0",
  "author": "PhpTpl Team",
  "description": "Secure template conditionals and expressions for MyBB 1.8.x (PHP 8.3+)",
  "mybb_compatibility": "18*",
  "php_compatibility": ">=8.1",
  "visibility": "public",
  "project_type": "plugin",
  "hooks": [
    {"name": "global_start", "handler": "phptpl_run", "priority": 10},
    {"name": "xmlhttp", "handler": "phptpl_run", "priority": 10}
  ],
  "settings": [],
  "templates": [],
  "files": {
    "plugin": "inc/plugins/phptpl.php",
    "languages": "inc/languages/"
  },
  "has_templates": false,
  "has_database": false
}
```

### Task Package 0.3: Create Plugin Entry Point

Create `phptpl.php` with:
- `IN_MYBB` check
- Autoloader for `PhpTpl\` namespace
- Hook registrations
- `phptpl_info()`, `phptpl_activate()`, `phptpl_deactivate()`, `phptpl_run()` stubs

**Acceptance Criteria:**
- [ ] Plugin appears in MyBB Admin CP plugin list
- [ ] Plugin can be activated without errors
- [ ] `phptpl_run()` is called on page load (verify with error_log)

**Dependencies:** None (first phase)

**Estimated Effort:** 2 hours
<!-- ID: phase_1 -->
**Objective:** Implement the tokenizer that converts template syntax into Token objects.

**Scope:**
- Create `TokenType` enum (PHP 8.1+)
- Create `Token` readonly class
- Create `Parser` class with regex-based tokenization
- Create `ParseException` class

### Task Package 1.1: Create TokenType Enum

**File:** `inc/plugins/phptpl/src/TokenType.php`

```php
<?php
namespace PhpTpl;

enum TokenType: string
{
    case TEXT = 'text';
    case IF_OPEN = 'if_open';
    case ELSEIF = 'elseif';
    case ELSE = 'else';
    case IF_CLOSE = 'if_close';
    case FUNC_OPEN = 'func_open';
    case FUNC_CLOSE = 'func_close';
    case TEMPLATE = 'template';
    case EXPRESSION = 'expression';
    case SETVAR = 'setvar';
}
```

**Verification:**
- [ ] File exists with correct namespace
- [ ] All 10 token types defined
- [ ] PHP 8.1+ syntax validates

### Task Package 1.2: Create Token Class

**File:** `inc/plugins/phptpl/src/Token.php`

```php
<?php
namespace PhpTpl;

readonly class Token
{
    public function __construct(
        public TokenType $type,
        public string $value,
        public int $position,
        public ?string $condition = null,
        public ?string $funcName = null,
        public ?string $varName = null,
    ) {}
}
```

**Verification:**
- [ ] Readonly class compiles
- [ ] Constructor accepts all parameters
- [ ] Properties are publicly accessible

### Task Package 1.3: Create ParseException

**File:** `inc/plugins/phptpl/src/Exceptions/ParseException.php`

**Verification:**
- [ ] Extends `\Exception`
- [ ] Can be caught and handled

### Task Package 1.4: Create Parser Class

**File:** `inc/plugins/phptpl/src/Parser.php`

**Key Implementation Details:**
- Regex patterns for each construct (see ARCHITECTURE_GUIDE Section 4.3)
- Single-pass tokenization with `preg_match_all`
- Extract text between matches
- Unescape slashes from MyBB's `addslashes()`

**Verification:**
- [ ] `parse('<if $x then>text</if>')` returns 3 tokens (IF_OPEN, TEXT, IF_CLOSE)
- [ ] Nested constructs tokenize correctly
- [ ] Plain text without syntax returns single TEXT token
- [ ] Expression `{= $var }` tokenizes as EXPRESSION

**Dependencies:** Phase 0 (directory structure exists)

**Estimated Effort:** 4 hours
<!-- ID: milestone_tracking -->
## Phase 2 - Security Policy
<!-- ID: phase_2 -->

**Objective:** Implement security controls that prevent dangerous code execution.

**Scope:**
- Create `SecurityPolicy` class with function whitelist
- Create `SecurityException` class
- Implement expression validation with forbidden patterns

### Task Package 2.1: Create SecurityException

**File:** `inc/plugins/phptpl/src/Exceptions/SecurityException.php`

### Task Package 2.2: Create SecurityPolicy Class

**File:** `inc/plugins/phptpl/src/SecurityPolicy.php`

**Key Implementation:**
- `ALLOWED_FUNCTIONS` constant with 39+ whitelisted functions
- `FORBIDDEN_PATTERNS` constant with dangerous regex patterns
- `validateFunction(string $func): string` - throws if not allowed
- `validateExpression(string $expr): string` - throws if forbidden pattern found

**Whitelisted Functions (from research):**
```php
private const ALLOWED_FUNCTIONS = [
    'htmlspecialchars', 'htmlspecialchars_uni', 'intval', 'floatval',
    'urlencode', 'rawurlencode', 'addslashes', 'stripslashes', 'trim',
    'crc32', 'ltrim', 'rtrim', 'chop', 'md5', 'nl2br', 'sha1',
    'strrev', 'strtoupper', 'strtolower', 'my_strtoupper', 'my_strtolower',
    'alt_trow', 'get_friendly_size', 'filesize', 'strlen', 'my_strlen',
    'my_wordwrap', 'random_str', 'unicode_chr', 'bin2hex', 'str_rot13',
    'str_shuffle', 'strip_tags', 'ucfirst', 'ucwords', 'basename',
    'dirname', 'unhtmlentities', 'abs', 'round', 'floor', 'ceil',
    'base64_encode', 'count'
];
```

**Verification:**
- [ ] `validateFunction('htmlspecialchars')` returns `'htmlspecialchars'`
- [ ] `validateFunction('eval')` throws SecurityException
- [ ] `validateExpression('system("ls")')` throws SecurityException
- [ ] `validateExpression('${$var}')` throws SecurityException (variable variables)
- [ ] `validateExpression('`whoami`')` throws SecurityException (backticks)

**Dependencies:** Phase 0 (directory structure)

**Estimated Effort:** 3 hours

---

## Phase 3 - Compilation
<!-- ID: phase_3 -->

**Objective:** Implement the compiler that transforms tokens into eval-ready PHP code.

**Scope:**
- Create `Compiler` class
- Create `CompileException` class
- Implement handlers for all token types
- Handle nested if statement tracking

### Task Package 3.1: Create CompileException

**File:** `inc/plugins/phptpl/src/Exceptions/CompileException.php`

### Task Package 3.2: Create Compiler Class

**File:** `inc/plugins/phptpl/src/Compiler.php`

**Key Implementation:**
- Constructor accepts `SecurityPolicy` for validation
- `compile(array $tokens): string` method
- Private handlers for each token type (see ARCHITECTURE_GUIDE Section 4.4)
- `$ifStack` array to track nested if depth

**Token Compilation Patterns:**
| Token Type | Output Pattern |
|------------|----------------|
| TEXT | Direct pass-through |
| IF_OPEN | `".(($condition)?"` |
| ELSEIF | `":(($condition)?"` |
| ELSE | `":"` |
| IF_CLOSE | `":""` + closing parens |
| FUNC_OPEN | `".$funcName("` |
| FUNC_CLOSE | `")."` |
| TEMPLATE | `".$GLOBALS["templates"]->get("name")."` |
| EXPRESSION | `".strval($expr)."` |
| SETVAR | `".(($GLOBALS["tplvars"]["name"] = ($value))?"":"")."` |

**Verification:**
- [ ] Simple if compiles: `<if $x then>Y</if>` -> `".(($x)?"Y":"")."` 
- [ ] Nested if compiles correctly with proper parentheses
- [ ] Func open/close wraps content
- [ ] Expression uses strval() wrapper
- [ ] Security exceptions propagate from SecurityPolicy

**Dependencies:** Phase 1 (Parser), Phase 2 (SecurityPolicy)

**Estimated Effort:** 4 hours

---

## Phase 4 - Runtime Integration
<!-- ID: phase_4 -->

**Objective:** Wire everything together with MyBB through the Runtime wrapper and caching.

**Scope:**
- Create `Cache` class for disk/memory caching
- Create `Runtime` class extending `templates`
- Update `phptpl.php` to use Runtime
- Test full integration

### Task Package 4.1: Create Cache Class

**File:** `inc/plugins/phptpl/src/Cache.php`

**Key Implementation:**
- Constructor accepts cache directory path
- `get(string $title, string $hash): ?string` - returns cached content or null
- `set(string $title, string $hash, string $content): void` - writes cache file
- `invalidate(string $title): void` - removes cache files for template
- Cache file format: `{title}_{hash}.php`

**Verification:**
- [ ] Cache miss returns null
- [ ] Cache set creates file
- [ ] Cache hit returns content
- [ ] Invalidate removes files

### Task Package 4.2: Create Runtime Class

**File:** `inc/plugins/phptpl/src/Runtime.php`

**Key Implementation:**
- `extends \templates`
- Constructor copies properties from original templates object
- Instantiates Parser, Compiler, SecurityPolicy, Cache
- Overrides `get()` method with caching and compilation logic
- Graceful fallback on any exception

**Verification:**
- [ ] `Runtime extends \templates` compiles
- [ ] Constructor copies cache/total/uncached_templates
- [ ] `get()` processes templates with syntax
- [ ] `get()` returns original on parse error
- [ ] Memory cache hits work
- [ ] Disk cache hits work

### Task Package 4.3: Update Plugin Entry Point

**File:** `inc/plugins/phptpl.php`

**Changes:**
- Update `phptpl_run()` to wrap `$templates` with `Runtime`
- Ensure autoloader loads all classes
- Add error logging for debugging

**Verification:**
- [ ] Plugin activates without errors
- [ ] `$templates` is instance of `PhpTpl\Runtime` after hook
- [ ] Templates with `<if>` syntax render correctly
- [ ] Templates without syntax pass through unchanged

**Dependencies:** Phase 1, 2, 3

**Estimated Effort:** 4 hours

---

## Phase 5 - Testing & QA
<!-- ID: phase_5 -->

**Objective:** Comprehensive testing to ensure correctness and security.

**Scope:**
- Create PHPUnit test suite
- Write unit tests for Parser, Compiler, SecurityPolicy
- Write integration tests with real templates
- Manual QA checklist

### Task Package 5.1: Setup PHPUnit

**Files:**
- `composer.json` with phpunit dependency
- `phpunit.xml` configuration
- `tests/bootstrap.php`

### Task Package 5.2: Parser Unit Tests

**File:** `tests/ParserTest.php`

Test cases from ARCHITECTURE_GUIDE Section 7.

### Task Package 5.3: SecurityPolicy Unit Tests (CRITICAL)

**File:** `tests/SecurityPolicyTest.php`

**Must test:**
- All 39+ whitelisted functions allowed
- Common dangerous functions blocked (eval, exec, system, etc.)
- All forbidden patterns detected
- Variable variables blocked
- Backtick execution blocked

### Task Package 5.4: Compiler Unit Tests

**File:** `tests/CompilerTest.php`

### Task Package 5.5: Integration Tests

**File:** `tests/IntegrationTest.php`

Test with real MyBB environment (requires TestForum).

### Task Package 5.6: Manual QA

Follow checklist in ARCHITECTURE_GUIDE Section 7.

**Acceptance Criteria:**
- [ ] All unit tests pass
- [ ] PHPStan level 6 passes
- [ ] Security tests have 100% coverage
- [ ] Integration tests pass in TestForum
- [ ] Manual QA checklist complete

**Dependencies:** Phase 0-4

**Estimated Effort:** 4 hours

---

## Phase 6 - Documentation
<!-- ID: phase_6 -->

**Objective:** Complete documentation for users and contributors.

**Scope:**
- README.md with installation and usage
- Migration guide from original PhpTpl
- Optional: MCP template validation tool

### Task Package 6.1: README.md

**Contents:**
- Installation instructions
- Supported syntax with examples
- Breaking changes from v2.1
- Configuration options
- Troubleshooting

### Task Package 6.2: Migration Guide

**Contents:**
- Syntax changes (`<?= ?>` -> `{= }`)
- Removed features (`<?php ?>` blocks)
- Step-by-step migration
- Common migration patterns

### Task Package 6.3: MCP Tool (Optional)

Add `mybb_template_validate` tool to mybb_mcp for editor integration.

**Acceptance Criteria:**
- [ ] README covers all features
- [ ] Migration guide is complete
- [ ] Examples work as documented

**Dependencies:** Phase 5 (testing complete)

**Estimated Effort:** 2 hours

---

## Milestone Tracking
<!-- ID: milestone_tracking -->

| Milestone | Target Date | Owner | Status | Evidence/Link |
|-----------|-------------|-------|--------|---------------|
| Phase 0 Complete | TBD | Coder | Pending | Plugin appears in ACP |
| Phase 1 Complete | TBD | Coder | Pending | Parser unit tests pass |
| Phase 2 Complete | TBD | Coder | Pending | Security tests pass |
| Phase 3 Complete | TBD | Coder | Pending | Compiler tests pass |
| Phase 4 Complete | TBD | Coder | Pending | Integration works |
| Phase 5 Complete | TBD | Coder | Pending | All tests green |
| Phase 6 Complete | TBD | Coder | Pending | Docs reviewed |
| Release v3.0.0 | TBD | Team | Pending | GitHub release |

Update status and evidence as work progresses. Always link to PROGRESS_LOG entries or commits.
<!-- ID: retro_notes -->
### Architecture Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-18 | Use `{= }` instead of `<?= ?>` | Cleaner syntax, avoids confusion with PHP tags |
| 2026-01-18 | Remove `<?php ?>` entirely | Core security vulnerability, not salvageable |
| 2026-01-18 | Hash-based cache keys | Automatic invalidation without explicit clearing |
| 2026-01-18 | Graceful fallback on error | Site stability > syntax enforcement |

### Lessons Learned

- Document lessons after each phase completes
- Note any scope changes or re-planning decisions

### Scope Changes

- None yet (pre-implementation)

---

**Document Status:** COMPLETE
**Author:** ArchitectAgent
**Date:** 2026-01-18
**Confidence:** 0.90
