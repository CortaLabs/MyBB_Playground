# Phase Plan - MyBB Ecosystem Enhancement
**Author:** ArchitectAgent
**Version:** v1.0
**Status:** Approved
**Last Updated:** 2026-01-17 14:30 UTC

> Implementation roadmap for MyBB MCP enhancement based on 8 research audits. Total estimated effort: 10-14 weeks across 4 phases.

---

## Executive Summary

This phase plan prioritizes work based on:
1. **Security first** - Critical vulnerabilities block all other work
2. **Value/complexity ratio** - Content management scores highest (11/20)
3. **Dependencies** - Security fixes enable expansion, plugin creator enables ecosystem
4. **Risk mitigation** - Gradual expansion with verification gates

**Total Scope:**
- 2 CRITICAL + 3 HIGH security fixes
- 52+ new MCP tools
- 6 major enhancement areas
- 10-14 weeks implementation

---

## Phase Overview
<!-- ID: phase_overview -->

| Phase | Duration | Focus | Deliverables | Confidence |
|-------|----------|-------|--------------|------------|
| Phase 0 | 1 week | Security Remediation (BLOCKING) | 5 security fixes, all tests pass | 0.95 |
| Phase 1 | 2-3 weeks | Foundation Enhancement | Plugin creator, template tools, hooks | 0.90 |
| Phase 2 | 2-3 weeks | Content Management | Posts, threads, forums, search | 0.85 |
| Phase 3 | 3-4 weeks | Admin Operations | Settings, cache, backup, tasks, moderation | 0.80 |
| Phase 4 | 2-4 weeks | Advanced Features (Optional) | Testing, migration, performance tools | 0.70 |

---

## Phase 0 - Security Remediation (BLOCKING)
<!-- ID: phase_0 -->

**Duration:** 1 week
**Priority:** CRITICAL - Blocks all other phases
**Dependencies:** None

### Objective
Fix all critical and high-priority security vulnerabilities identified in RESEARCH_MyBB_MCP_Security_Audit_20260117_1405.md before any expansion work begins.

### Task Packages

#### TP-0.1: Asyncio Threading Fix
- **Scope:** Fix asyncio.run() anti-pattern in file watcher
- **Files:** `sync/watcher.py` (lines 150, 180, 189)
- **Effort:** 1-2 days
- **Verification:** Unit test with 10+ rapid file modifications passes

#### TP-0.2: Database Password Security
- **Scope:** Remove empty password default, require explicit password
- **Files:** `config.py` (line 45)
- **Effort:** 0.5 days
- **Verification:** MCP server fails to start without MYBB_DB_PASS set

#### TP-0.3: Connection Pooling
- **Scope:** Replace single connection with connection pool
- **Files:** `db/connection.py`
- **Effort:** 1-2 days
- **Verification:** Concurrent operations work without connection conflicts

#### TP-0.4: Error Handling Enhancement
- **Scope:** Add structured error types for better debugging
- **Files:** `server.py`, `db/connection.py`
- **Effort:** 1 day
- **Verification:** Database errors return DatabaseError with code

#### TP-0.5: Security Test Suite
- **Scope:** Create comprehensive security test coverage
- **Files:** NEW `tests/test_security.py`
- **Effort:** 1-2 days
- **Verification:** All security tests pass, coverage > 80%

### Acceptance Criteria
- [ ] No RuntimeError on concurrent file changes
- [ ] MCP fails to start without password
- [ ] Connection pool with 5 connections
- [ ] Structured error types implemented
- [ ] All security tests pass

### Dependencies
None - this is the first phase

**Source:** RESEARCH_MyBB_MCP_Security_Audit_20260117_1405.md (Confidence: 0.92)

---

## Phase 1 - Foundation Enhancement
<!-- ID: phase_1 -->

**Duration:** 2-3 weeks
**Priority:** HIGH - Enables ecosystem improvements
**Dependencies:** Phase 0 complete

### Objective
Enhance plugin creator with all required MyBB patterns, expand template tools with critical functionality, and implement dynamic hook discovery.

### Task Packages

#### TP-1.1: Plugin Creator - Settings Enhancement
- **Scope:** Add rebuild_settings() to generated plugin code
- **Files:** `tools/plugins.py`
- **Effort:** 0.5 days
- **Verification:** Generated plugin includes rebuild_settings() calls

#### TP-1.2: Plugin Creator - Multi-DB Support
- **Scope:** Generate database-agnostic table creation code
- **Files:** `tools/plugins.py`
- **Effort:** 1 day
- **Verification:** Generated plugin includes multi-DB switch statement

#### TP-1.3: Plugin Creator - Security Boilerplate
- **Scope:** Add security patterns to generated plugins
- **Files:** `tools/plugins.py`
- **Effort:** 0.5 days
- **Verification:** Generated plugin includes IN_MYBB check, CSRF protection

#### TP-1.4: Plugin Creator - Template Caching
- **Scope:** Add $templatelist pattern for template caching
- **Files:** `tools/plugins.py`
- **Effort:** 0.5 days
- **Verification:** Generated plugin includes $templatelist assignment

#### TP-1.5: Plugin Creator - Hook Priority
- **Scope:** Add hook priority support to plugin generator
- **Files:** `tools/plugins.py`
- **Effort:** 0.5 days
- **Verification:** Object array generates correct priority

#### TP-1.6: Template Tools - find_replace
- **Scope:** Implement find_replace_templatesets() wrapper
- **Files:** NEW `tools/templates.py`
- **Effort:** 2 days
- **Verification:** Find and replace works with simple strings and regex

#### TP-1.7: Template Tools - Batch Operations
- **Scope:** Add batch template read/write operations
- **Files:** `tools/templates.py`
- **Effort:** 1 day
- **Verification:** Batch of 10 templates writes in single transaction

#### TP-1.8: Template Tools - Diff/Outdated
- **Scope:** Add template comparison and outdated detection
- **Files:** `tools/templates.py`
- **Effort:** 1 day
- **Verification:** Diff shows additions/removals clearly

#### TP-1.9: Hook System - Dynamic Discovery
- **Scope:** Implement dynamic hook discovery from MyBB codebase
- **Files:** NEW `tools/hooks.py`
- **Effort:** 2 days
- **Verification:** Discovers 200+ hooks from MyBB codebase

#### TP-1.10: Hook System - Enhanced Categories
- **Scope:** Add missing hook categories to reference
- **Files:** `tools/plugins.py`
- **Effort:** 1 day
- **Verification:** All 15 categories available

### Acceptance Criteria
- [ ] Plugin creator generates complete, working plugins
- [ ] Generated plugins include all 10 MyBB patterns
- [ ] Template tools work for find/replace and batch operations
- [ ] Hook discovery returns 200+ hooks
- [ ] All tests pass (unit + integration)

### Dependencies
Phase 0 complete

**Source:** RESEARCH_MYBB_PLUGIN_PATTERNS_20260117_1405.md, RESEARCH_MyBB_Template_System_20260117_1407.md, RESEARCH_MyBB_Hooks_System_20260117_1406.md

---

## Phase 2 - Content Management
<!-- ID: phase_2 -->

**Duration:** 2-3 weeks
**Priority:** HIGH - Highest value per research scoring
**Dependencies:** Phase 1 complete

### Objective
Implement content management tools for forums, threads, posts, and search functionality using MyBB datahandler patterns.

### Task Packages

#### TP-2.1: Forums CRUD
- **Scope:** Implement forum/category management tools
- **Files:** NEW `tools/content.py`
- **Effort:** 2-3 days
- **Verification:** Create works for both forums and categories

#### TP-2.2: Threads CRUD
- **Scope:** Implement thread management tools
- **Files:** `tools/content.py`
- **Effort:** 3-4 days
- **Verification:** Thread and first post created atomically

#### TP-2.3: Posts CRUD
- **Scope:** Implement post management tools
- **Files:** `tools/content.py`
- **Effort:** 2-3 days
- **Verification:** Post appears in thread correctly

#### TP-2.4: Search Functionality
- **Scope:** Implement search tools wrapping MyBB search
- **Files:** `tools/content.py`
- **Effort:** 3-4 days
- **Verification:** Permissions respected (no private content leaked)

#### TP-2.5: Content Integration Tests
- **Scope:** Create comprehensive content workflow tests
- **Files:** NEW `tests/test_content.py`
- **Effort:** 2 days
- **Verification:** Workflow tests complete in < 10s

### Acceptance Criteria
- [ ] Forum/thread/post CRUD works correctly
- [ ] Search returns relevant results
- [ ] Permission system respected
- [ ] All tests pass (unit + integration + security)

### Dependencies
Phase 1 complete

**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md (Priority Score: 11 for posts/threads)

---

## Phase 3 - Admin Operations
<!-- ID: phase_3 -->

**Duration:** 3-4 weeks
**Priority:** MEDIUM - Essential for admin workflows
**Dependencies:** Phase 2 complete

### Objective
Implement admin operation tools for settings, cache, backup, tasks, moderation, and basic user management.

### Task Packages

#### TP-3.1: Settings Management
- **Scope:** Implement settings read/write tools
- **Files:** NEW `tools/admin.py`
- **Effort:** 2 days
- **Verification:** Get/update setting works, cache properly rebuilt

#### TP-3.2: Cache Management
- **Scope:** Implement cache control tools
- **Files:** `tools/admin.py`
- **Effort:** 1 day
- **Verification:** Rebuild all caches works

#### TP-3.3: Plugin Lifecycle
- **Scope:** Implement plugin activate/deactivate/install/uninstall
- **Files:** `tools/admin.py`
- **Effort:** 2 days
- **Verification:** Activate enables plugin hooks

#### TP-3.4: Database Backup
- **Scope:** Implement database backup tools
- **Files:** `tools/admin.py`
- **Effort:** 2 days
- **Verification:** Create backup generates valid SQL dump

#### TP-3.5: Scheduled Tasks
- **Scope:** Implement task management tools
- **Files:** `tools/admin.py`
- **Effort:** 2 days
- **Verification:** Run task executes immediately

#### TP-3.6: Moderation Tools
- **Scope:** Implement basic moderation operations
- **Files:** NEW `tools/moderation.py`
- **Effort:** 3 days
- **Verification:** All operations logged to modlog

#### TP-3.7: User Management (Basic)
- **Scope:** Implement basic user management tools
- **Files:** NEW `tools/users.py`
- **Effort:** 3 days
- **Verification:** Password properly hashed

#### TP-3.8: Statistics Tools
- **Scope:** Implement forum statistics tools
- **Files:** `tools/admin.py`
- **Effort:** 1 day
- **Verification:** Forum stats returns accurate counts

### Acceptance Criteria
- [ ] Settings management works correctly
- [ ] Plugin lifecycle works correctly
- [ ] Backup/cache/task tools work correctly
- [ ] Basic moderation and user tools work correctly
- [ ] All tests pass

### Dependencies
Phase 2 complete

**Source:** RESEARCH_AdminCP_MCP_Expansion_20260117_1404.md (52+ tools proposed)

---

## Phase 4 - Advanced Features (Optional)
<!-- ID: phase_4 -->

**Duration:** 2-4 weeks
**Priority:** LOW - Nice-to-have enhancements
**Dependencies:** Phase 3 complete

### Objective
Implement advanced testing, migration, and performance monitoring tools.

### Task Packages

#### TP-4.1: Testing & Validation Tools
- **Scope:** Implement testing and validation helpers
- **Files:** NEW `tools/testing.py`
- **Effort:** 2-3 days

#### TP-4.2: Migration Tools
- **Scope:** Implement bulk import/export tools
- **Files:** NEW `tools/migration.py`
- **Effort:** 5-7 days

#### TP-4.3: Performance Monitoring
- **Scope:** Implement performance monitoring tools
- **Files:** NEW `tools/monitoring.py`
- **Effort:** 3-4 days

#### TP-4.4: VSCode Integration Alignment
- **Scope:** Address VSCode extension compatibility
- **Files:** Various
- **Effort:** 2-3 days

### Acceptance Criteria
- [ ] Testing tools catch common errors
- [ ] Migration tools validate all data
- [ ] Performance tools show useful metrics

### Dependencies
Phase 3 complete

**Source:** RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md, RESEARCH_VSCode_Extension_Audit_20260117_1406.md

---

## Milestone Tracking
<!-- ID: milestone_tracking -->

| Milestone | Target Date | Owner | Status | Evidence/Link |
|-----------|-------------|-------|--------|---------------|
| Phase 0 Complete | Week 1 | Coder | Planned | Security tests pass |
| Phase 1 Complete | Week 4 | Coder | Planned | Plugin creator tests |
| Phase 2 Complete | Week 7 | Coder | Planned | Content integration tests |
| Phase 3 Complete | Week 11 | Coder | Planned | Admin tool tests |
| Phase 4 Complete | Week 14 | Coder | Planned | Full test suite |

---

## Risk Management

### Identified Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Security fix breaks existing functionality | HIGH | MEDIUM | Extensive testing, backward compatibility |
| DataHandler validation complexity | HIGH | LOW | Research showed clear patterns |
| Performance degradation | MEDIUM | MEDIUM | Benchmark at each phase gate |
| Scope creep in Phase 4 | LOW | HIGH | Phase 4 optional, strict gates |

---

## Retro Notes & Adjustments
<!-- ID: retro_notes -->

*To be updated after each phase completion:*
- Phase 0 lessons learned: TBD
- Phase 1 lessons learned: TBD
- Phase 2 lessons learned: TBD
- Phase 3 lessons learned: TBD
- Phase 4 lessons learned: TBD

---

## Timeline Summary

| Phase | Start | End | Duration |
|-------|-------|-----|----------|
| Phase 0 | Week 1 | Week 1 | 1 week |
| Phase 1 | Week 2 | Week 4 | 2-3 weeks |
| Phase 2 | Week 5 | Week 7 | 2-3 weeks |
| Phase 3 | Week 8 | Week 11 | 3-4 weeks |
| Phase 4 | Week 12 | Week 14 | 2-4 weeks (optional) |

**Total: 10-14 weeks**

---

**Document Status:** Approved for Implementation
**Next Step:** Create CHECKLIST.md with detailed task tracking
