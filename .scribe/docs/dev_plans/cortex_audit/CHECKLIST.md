---
id: cortex_audit-checklist
title: "\u2705 Acceptance Checklist \u2014 cortex-audit"
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

# ✅ Acceptance Checklist — cortex-audit
**Author:** Scribe
**Version:** v0.1
**Status:** Draft
**Last Updated:** 2026-01-18 13:02:39 UTC

> Acceptance checklist for cortex-audit.

---
## Documentation Hygiene
<!-- ID: documentation_hygiene -->
## Documentation Hygiene

- [x] Architecture guide updated (proof: ARCHITECTURE_GUIDE.md - 22KB, 10 sections)
- [x] Phase plan current (proof: PHASE_PLAN.md - 6 phases, 14 task packages)
- [x] Research document referenced (proof: RESEARCH_CORTEX_AUDIT_20260118_1304.md)
- [ ] Wiki updated with Cortex settings documentation
<!-- ID: phase_0 -->
## Phase 1: MyBB Settings Integration

- [ ] cortex_install() creates setting group (proof: SELECT * FROM mybb_settinggroups WHERE name='cortex')
- [ ] cortex_install() creates 7 settings (proof: SELECT COUNT(*) FROM mybb_settings WHERE name LIKE 'cortex_%')
- [ ] cortex_uninstall() removes all settings (proof: verify empty after uninstall)
- [ ] cortex_is_installed() returns correct state (proof: test both states)
- [ ] Language strings added to cortex.lang.php (proof: file inspection)
- [ ] rebuild_settings() called after insert/delete (proof: settings appear in ACP)

## Phase 2: SecurityPolicy Enhancement

- [ ] SecurityPolicy constructor accepts 3 parameters (proof: code review)
- [ ] deniedFunctions property populated from config (proof: debug output)
- [ ] isAllowedFunction() checks denied list first (proof: test with 'strlen' denied)
- [ ] validateExpression() checks length (proof: test with max_expression_length=50)
- [ ] SecurityException::expressionTooLong() creates correct message (proof: exception test)

## Phase 3: Parser Nesting Depth

- [ ] Parser constructor accepts maxNestingDepth (proof: code review)
- [ ] validateStructure() tracks depth (proof: debug output)
- [ ] Exception thrown when depth exceeded (proof: test with max=3, 4 nested ifs)
- [ ] ParseException::nestingTooDeep() creates correct message (proof: exception test)
- [ ] Depth limit of 0 means unlimited (proof: test deep nesting with 0)

## Phase 4: Cache TTL

- [ ] Cache constructor accepts ttl parameter (proof: code review)
- [ ] get() checks file mtime against TTL (proof: test with TTL=5, wait 6s)
- [ ] Expired files are deleted on access (proof: verify file removed)
- [ ] TTL of 0 means no expiration (proof: old files still returned)
- [ ] Memory cache bypasses TTL check (proof: same-request caching works)

## Phase 5: Config Building

- [ ] cortex_init() reads $mybb->settings (proof: debug config array)
- [ ] ACP settings override file config (proof: change ACP value, verify used)
- [ ] File config used as fallback (proof: remove setting, verify default)
- [ ] denied_functions parsed from comma-separated string (proof: test "strlen,substr")
- [ ] Runtime passes config to all components (proof: trace component construction)

## Phase 6: Integration & Testing

- [ ] Plugin deploys without errors (proof: mybb_plugin_install output)
- [ ] All 7 settings visible in ACP (proof: screenshot/verification)
- [ ] cortex_enabled toggle works (proof: Cortex syntax ignored when off)
- [ ] cortex_debug_mode logs errors (proof: PHP error log entry)
- [ ] cortex_cache_enabled toggle works (proof: no cache files when off)
- [ ] cortex_cache_ttl expires cache (proof: cache regenerated after TTL)
- [ ] cortex_max_nesting_depth enforced (proof: graceful failure on deep nesting)
- [ ] cortex_max_expression_length enforced (proof: graceful failure on long expr)
- [ ] cortex_denied_functions blocks functions (proof: function call fails)
<!-- ID: final_verification -->
## Final Verification

- [ ] All Phase 1-6 checklist items completed with proofs
- [ ] No PHP errors in error log during testing
- [ ] Existing Cortex templates still work after upgrade
- [ ] Settings persist across plugin deactivate/reactivate cycle
- [ ] Config.php fallback tested (remove settings, verify defaults)
- [ ] Review Agent grade >= 93%
- [ ] Stakeholder sign-off recorded (name + date)
- [ ] Retro completed and lessons learned documented in PHASE_PLAN.md
