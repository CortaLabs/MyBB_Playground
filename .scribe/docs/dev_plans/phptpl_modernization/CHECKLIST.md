---
id: phptpl_modernization-checklist
title: "\u2705 Acceptance Checklist \u2014 phptpl-modernization"
doc_name: checklist
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

# ✅ Acceptance Checklist — phptpl-modernization
**Author:** Scribe
**Version:** v0.1
**Status:** Draft
**Last Updated:** 2026-01-18 09:56:19 UTC

> Acceptance checklist for phptpl-modernization.

---
## Documentation Hygiene
<!-- ID: documentation_hygiene -->
- [x] Architecture guide updated (proof: ARCHITECTURE_GUIDE.md - 10 sections, ~35KB)
- [x] Phase plan current (proof: PHASE_PLAN.md - 7 phases, 23 task packages)
- [x] Research document complete (proof: research/RESEARCH_TEMPLATE_SYSTEM.md - confidence 0.95)
- [ ] README.md created (proof: plugin_manager/plugins/public/phptpl/README.md)
- [ ] Migration guide created (proof: docs/MIGRATION_GUIDE.md)
<!-- ID: phase_0 -->
- [ ] Directory structure created (proof: `ls plugin_manager/plugins/public/phptpl/`)
- [ ] meta.json created and valid (proof: `cat meta.json | jq .`)
- [ ] phptpl.php entry point exists (proof: file exists with IN_MYBB check)
- [ ] composer.json created (proof: file exists)
- [ ] phpunit.xml created (proof: file exists)
- [ ] Plugin appears in MyBB Admin CP (proof: screenshot or manual verification)
- [ ] Plugin activates without errors (proof: no PHP errors in log)

---

## Phase 1 - Core Parsing
<!-- ID: phase_1 -->

- [ ] TokenType.php created with all 10 token types (proof: file review)
- [ ] Token.php readonly class created (proof: file review)
- [ ] ParseException.php created (proof: file review)
- [ ] Parser.php created with parse() method (proof: file review)
- [ ] Parser handles `<if condition then>` (proof: unit test)
- [ ] Parser handles `<else if condition then>` (proof: unit test)
- [ ] Parser handles `<else />` (proof: unit test)
- [ ] Parser handles `</if>` (proof: unit test)
- [ ] Parser handles `<func name>` (proof: unit test)
- [ ] Parser handles `<template name>` (proof: unit test)
- [ ] Parser handles `{= expression }` (proof: unit test)
- [ ] Parser handles `<setvar name>` (proof: unit test)
- [ ] Parser handles plain text without syntax (proof: unit test)

---

## Phase 2 - Security Policy (CRITICAL)
<!-- ID: phase_2 -->

- [ ] SecurityException.php created (proof: file review)
- [ ] SecurityPolicy.php created (proof: file review)
- [ ] ALLOWED_FUNCTIONS contains 39+ whitelisted functions (proof: code review)
- [ ] FORBIDDEN_PATTERNS contains all dangerous patterns (proof: code review)
- [ ] validateFunction() allows whitelisted functions (proof: unit test)
- [ ] validateFunction() rejects non-whitelisted functions (proof: unit test)
- [ ] validateExpression() blocks `eval()` calls (proof: unit test)
- [ ] validateExpression() blocks `exec()` calls (proof: unit test)
- [ ] validateExpression() blocks `system()` calls (proof: unit test)
- [ ] validateExpression() blocks variable variables `${$x}` (proof: unit test)
- [ ] validateExpression() blocks backtick execution (proof: unit test)
- [ ] validateExpression() blocks `include/require` (proof: unit test)
- [ ] Security test coverage >= 100% (proof: coverage report)

---

## Phase 3 - Compilation
<!-- ID: phase_3 -->

- [ ] CompileException.php created (proof: file review)
- [ ] Compiler.php created (proof: file review)
- [ ] compile() accepts Token array and returns string (proof: unit test)
- [ ] IF_OPEN compiles to `".(($condition)?"` (proof: unit test)
- [ ] ELSEIF compiles to `":(($condition)?"` (proof: unit test)
- [ ] ELSE compiles to `":"` (proof: unit test)
- [ ] IF_CLOSE compiles with proper closing (proof: unit test)
- [ ] Nested if statements compile correctly (proof: unit test with 3 levels)
- [ ] FUNC_OPEN/CLOSE wrap content (proof: unit test)
- [ ] TEMPLATE compiles to $GLOBALS["templates"]->get() (proof: unit test)
- [ ] EXPRESSION wraps with strval() (proof: unit test)
- [ ] SETVAR compiles to tplvars assignment (proof: unit test)
- [ ] Security exceptions propagate (proof: unit test)

---

## Phase 4 - Runtime Integration
<!-- ID: phase_4 -->

- [ ] Cache.php created (proof: file review)
- [ ] Cache get() returns null on miss (proof: unit test)
- [ ] Cache set() writes file (proof: unit test)
- [ ] Cache hit returns content (proof: unit test)
- [ ] Runtime.php created extending templates (proof: file review)
- [ ] Runtime constructor copies original properties (proof: unit test)
- [ ] Runtime get() processes templates with syntax (proof: integration test)
- [ ] Runtime get() returns original on error (proof: integration test)
- [ ] Memory cache works (proof: integration test)
- [ ] Disk cache works (proof: integration test)
- [ ] phptpl_run() wraps $templates correctly (proof: integration test)
- [ ] Plugin works end-to-end in TestForum (proof: manual test)

---

## Phase 5 - Testing & QA
<!-- ID: phase_5 -->

- [ ] PHPUnit configured and running (proof: `vendor/bin/phpunit` succeeds)
- [ ] All Parser tests pass (proof: test output)
- [ ] All Compiler tests pass (proof: test output)
- [ ] All SecurityPolicy tests pass (proof: test output)
- [ ] All Cache tests pass (proof: test output)
- [ ] All Runtime tests pass (proof: test output)
- [ ] Integration tests pass (proof: test output)
- [ ] PHPStan level 6 passes (proof: `vendor/bin/phpstan` output)
- [ ] Test coverage >= 90% (proof: coverage report)
- [ ] Manual QA: Plugin installs (proof: screenshot)
- [ ] Manual QA: Plugin activates (proof: screenshot)
- [ ] Manual QA: Cache directory created (proof: `ls cache/phptpl/`)
- [ ] Manual QA: Conditional template works (proof: screenshot)
- [ ] Manual QA: Function whitelist enforced (proof: screenshot/log)
- [ ] Manual QA: No PHP errors in error log (proof: log excerpt)

---

## Phase 6 - Documentation
<!-- ID: phase_6 -->

- [ ] README.md complete with installation instructions (proof: file review)
- [ ] README.md includes syntax examples (proof: file review)
- [ ] README.md lists breaking changes (proof: file review)
- [ ] Migration guide complete (proof: file review)
- [ ] Examples in docs work as documented (proof: manual test)
<!-- ID: final_verification -->
### Pre-Release Checklist

- [ ] All Phase 0-6 checklist items checked with proofs attached
- [ ] No eval() calls in codebase (proof: `grep -r "eval(" src/`)
- [ ] No deprecated PHP syntax (proof: PHPStan output)
- [ ] All security tests pass with 100% coverage
- [ ] Plugin tested on PHP 8.1, 8.2, 8.3 (proof: CI matrix)
- [ ] Performance benchmark completed (proof: benchmark results)

### Release Checklist

- [ ] Version number updated to 3.0.0 in meta.json
- [ ] Version number updated in phptpl_info()
- [ ] CHANGELOG.md created with v3.0.0 notes
- [ ] Git tag created for v3.0.0
- [ ] GitHub release created with assets

### Stakeholder Sign-off

| Reviewer | Date | Verdict | Notes |
|----------|------|---------|-------|
| Review Agent | TBD | Pending | Pre-implementation review |
| Review Agent | TBD | Pending | Post-implementation review |
| User | TBD | Pending | Final acceptance |

---

**Document Status:** COMPLETE
**Author:** ArchitectAgent
**Date:** 2026-01-18
**Confidence:** 0.95
