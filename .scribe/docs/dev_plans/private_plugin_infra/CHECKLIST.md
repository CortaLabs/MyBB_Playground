---
id: private_plugin_infra-checklist
title: "Acceptance Checklist - install.sh Hardening"
doc_name: CHECKLIST
category: engineering
status: active
version: '1.0'
last_updated: '2026-01-19'
maintained_by: Corta Labs
created_by: MyBB-ArchitectAgent
owners: []
related_docs:
  - ARCHITECTURE_GUIDE.md
  - PHASE_PLAN.md
tags:
  - bash
  - install
  - hardening
summary: 'Verification criteria for install.sh hardening'
---

# Acceptance Checklist - install.sh Hardening

**Author:** MyBB-ArchitectAgent
**Version:** 1.0
**Status:** Active
**Last Updated:** 2026-01-19 UTC

> Verification criteria for install.sh hardening. Each phase must pass all checks before proceeding.

---

## Documentation Hygiene
<!-- ID: documentation_hygiene -->

- [x] Architecture guide updated (proof: ARCHITECTURE_GUIDE.md v1.0)
- [x] Phase plan current (proof: PHASE_PLAN.md v1.0)
- [x] Research findings documented (proof: RESEARCH_install_sh_gaps_analysis.md)

---

## Phase 1: Critical Fixes
<!-- ID: phase_1 -->

**Objective:** Error handling infrastructure and database edge case fixes

### Task 1.1: Shell Options & Trap Infrastructure
- [ ] Line 12 changed from `set -e` to `set -Eeuo pipefail`
- [ ] cleanup() function exists and handles TEMP_DIRS array
- [ ] error_handler() function shows line number on failure
- [ ] trap handlers registered in main() for EXIT and ERR
- [ ] **Verification:** `bash -n install.sh` passes
- [ ] **Verification:** Ctrl+C mid-install cleans up temp files

### Task 1.2: Temp Directory Tracking
- [ ] TEMP_DIRS array tracks created temp directories
- [ ] install_mybb() adds TMP_DIR to TEMP_DIRS
- [ ] Explicit `rm -rf "$TMP_DIR"` removed (trap handles cleanup)
- [ ] **Verification:** `ls /tmp/tmp.*` shows no orphaned dirs after any exit

### Task 1.3: MariaDB Version Detection
- [ ] detect_mariadb_version() function exists
- [ ] compare_versions() function for version comparison
- [ ] Version displayed in setup_database output
- [ ] **Verification:** Version detected correctly on test system

### Task 1.4: Unix Socket Auth Handling
- [ ] Password escaped for SQL (single quotes handled)
- [ ] MariaDB 10.4+ uses mysql_native_password syntax
- [ ] Older MariaDB uses standard IDENTIFIED BY syntax
- [ ] Database name escaped with backticks
- [ ] **Verification:** Password with `'` character works

### Task 1.5: Database Connection Verification
- [ ] Connection test runs after user creation
- [ ] Success message: "Database connection verified!"
- [ ] Failure shows diagnostics (user, database, log location)
- [ ] **Verification:** Wrong password shows helpful error

### Phase 1 Integration
- [ ] All 5 task packages complete
- [ ] Fresh install works on Ubuntu
- [ ] Update mode preserves existing data
- [ ] **Evidence:** Screenshot or log of successful install

---

## Phase 2: High Priority Fixes
<!-- ID: phase_2 -->

**Objective:** Input validation and SSH security improvements

### Task 2.1: Input Validation Functions
- [ ] validate_db_name() validates: starts with letter, alphanumeric+underscore, max 64
- [ ] validate_port() validates: numeric, 1024-65535
- [ ] validate_password() validates: non-empty, warns on special chars
- [ ] prompt_validated() retries up to 3 times on invalid input
- [ ] **Verification:** Invalid database name "123bad" rejected

### Task 2.2: Integrate Validation with Prompts
- [ ] Database name prompt uses prompt_validated with validate_db_name
- [ ] Database user prompt uses prompt_validated with validate_db_name
- [ ] Database password prompt uses prompt_validated with validate_password
- [ ] Port prompt (save_env) uses prompt_validated with validate_port
- [ ] **Verification:** Invalid port "99999" rejected, re-prompted

### Task 2.3: SSH Key Security Enhancement
- [ ] ssh-keygen uses -a 100 flag
- [ ] Passphrase option offered (default: no for convenience)
- [ ] Warning shown when creating unencrypted key
- [ ] ssh-add result verified
- [ ] Success/warning message for key loading
- [ ] **Verification:** New key shows 100 rounds in `ssh-keygen -l`

### Task 2.4: GitHub CLI Timeout Protection
- [ ] gh auth login wrapped with timeout (5 minutes)
- [ ] Fallback to no timeout if timeout command unavailable (macOS)
- [ ] Warning message shows retry command on timeout
- [ ] **Verification:** Normal login flow still works

### Phase 2 Integration
- [ ] All 4 task packages complete
- [ ] Invalid inputs rejected and re-prompted
- [ ] SSH key generation uses strong derivation
- [ ] **Evidence:** Log showing validation in action

---

## Phase 3: Medium Priority Enhancements
<!-- ID: phase_3 -->

**Objective:** Unattended mode and logging for CI/CD support

### Task 3.1: Argument Parsing
- [ ] -y/--non-interactive flag sets NON_INTERACTIVE=1
- [ ] --debug flag enables set -x
- [ ] -h/--help shows usage and env var documentation
- [ ] parse_args() called at start of main()
- [ ] is_interactive() helper function works
- [ ] **Verification:** `./install.sh -h` shows help text

### Task 3.2: Non-Interactive Prompt Handling
- [ ] prompt() uses default when NON_INTERACTIVE=1
- [ ] prompt_yn() uses default when NON_INTERACTIVE=1
- [ ] prompt_choice() returns 1 (first option) when NON_INTERACTIVE=1
- [ ] All prompts show "(non-interactive)" in output
- [ ] **Verification:** `MYBB_NON_INTERACTIVE=1 ./install.sh` runs without prompts

### Task 3.3: Logging Infrastructure
- [ ] LOG_FILE created with timestamp in script directory
- [ ] strip_ansi() removes ANSI color codes
- [ ] log_to_file() writes to LOG_FILE
- [ ] info/success/warn/error all write to log file
- [ ] init_logging() creates log header
- [ ] install_*.log pattern added to .gitignore
- [ ] **Verification:** Log file contains all messages without colors

### Phase 3 Integration
- [ ] All 3 task packages complete
- [ ] Unattended mode works for CI/CD
- [ ] Log file useful for debugging
- [ ] **Evidence:** Successful CI-style run: `MYBB_DB_PASS=test123 ./install.sh -y`

---

## Final Verification
<!-- ID: final_verification -->

### Functional Tests
- [ ] Fresh install on Ubuntu 22.04 (interactive)
- [ ] Fresh install on macOS (interactive)
- [ ] Update mode preserves data
- [ ] Error recovery cleans up temp files
- [ ] Database connection verified after setup
- [ ] Unattended install completes without prompts

### Non-Functional Tests
- [ ] Script size reasonable (~700-800 lines)
- [ ] `bash -n install.sh` passes (syntax check)
- [ ] `shellcheck install.sh` has no errors (if available)
- [ ] Existing .env files still work (backwards compatible)
- [ ] Log file created and useful

### Sign-Off
- [ ] All checklist items verified with evidence
- [ ] Code review passed
- [ ] Stakeholder sign-off: _________________ (name + date)
- [ ] Retro completed (see PHASE_PLAN.md Retro Notes)

---

## Research Findings Coverage
<!-- ID: research_coverage -->

| Finding | Priority | Addressed In | Status |
|---------|----------|--------------|--------|
| F1: Error Handling | CRITICAL | Phase 1 (1.1, 1.2) | Pending |
| F2: Cross-Platform | HIGH | Future (Alpine deferred) | Deferred |
| F3: Database Edge Cases | HIGH | Phase 1 (1.3, 1.4, 1.5) | Pending |
| F4: SSH Security | MEDIUM | Phase 2 (2.3) | Pending |
| F5: Input Validation | MEDIUM | Phase 2 (2.1, 2.2) | Pending |
| F6: GitHub Auth | MEDIUM | Phase 2 (2.4) | Pending |
| F7: Unattended Mode | MEDIUM | Phase 3 (3.1, 3.2) | Pending |
| F8: Logging | LOW-MEDIUM | Phase 3 (3.3) | Pending |
| F9: ShellCheck | MEDIUM | Future | Deferred |
| F10: Platform Blind Spots | MEDIUM | Future | Deferred |

---

*Checklist by MyBB-ArchitectAgent*
