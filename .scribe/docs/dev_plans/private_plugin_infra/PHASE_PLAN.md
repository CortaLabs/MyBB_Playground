---
id: private_plugin_infra-phase-plan
title: "Phase Plan - install.sh Hardening"
doc_name: PHASE_PLAN
category: engineering
status: active
version: '1.0'
last_updated: '2026-01-19'
maintained_by: Corta Labs
created_by: MyBB-ArchitectAgent
owners: []
related_docs:
  - ARCHITECTURE_GUIDE.md
  - RESEARCH_install_sh_gaps_analysis.md
tags:
  - bash
  - install
  - hardening
summary: 'Implementation phases for install.sh hardening'
---

# Phase Plan - install.sh Hardening

**Author:** MyBB-ArchitectAgent
**Version:** 1.0
**Status:** Active
**Last Updated:** 2026-01-19 UTC

> Execution roadmap for hardening install.sh based on architecture in ARCHITECTURE_GUIDE.md.

---

## Phase Overview
<!-- ID: phase_overview -->

| Phase | Goal | Priority | Est. Lines Changed | Confidence |
|-------|------|----------|-------------------|------------|
| Phase 1 | Critical: Error Handling & Database Fixes | CRITICAL | ~120 lines | 0.95 |
| Phase 2 | High: Input Validation & SSH Security | HIGH | ~100 lines | 0.90 |
| Phase 3 | Medium: Unattended Mode & Logging | MEDIUM | ~80 lines | 0.85 |

**Total Estimated Change:** ~300 lines added/modified (script grows from 634 to ~720 lines)

---

## Phase 1 - Critical Fixes
<!-- ID: phase_1 -->

**Objective:** Implement error handling infrastructure and fix database edge cases.

**Priority:** CRITICAL
**Estimated Lines:** ~120 lines changed
**Research Findings Addressed:** F1 (Error Handling), F3 (Database Edge Cases)

### Task Package 1.1: Shell Options & Trap Infrastructure

**Scope:** Add error handling foundation at script start

**Files:** `install.sh`
**Lines to Modify:** 12 (replace), 36-50 (insert new section)
**Estimated Changes:** ~40 lines added

**Specifications:**

1. Replace line 12:
   - Current: `set -e`
   - New: `set -Eeuo pipefail`

2. Insert after line 35 (after Colors section), new "Error Handling" section:
   ```bash
   # ============================================
   # Error Handling
   # ============================================
   TEMP_DIRS=()
   CLEANUP_DONE=false

   cleanup() { ... }      # ~15 lines
   error_handler() { ... } # ~5 lines
   ```

3. Add trap registration in main() function (line ~610):
   ```bash
   trap cleanup EXIT
   trap 'error_handler $LINENO $?' ERR
   ```

**Verification:**
- [ ] `bash -n install.sh` passes (syntax check)
- [ ] Script exits cleanly on Ctrl+C
- [ ] Temp directory from failed install is cleaned up
- [ ] Error message shows line number on failure

**Out of Scope:**
- Do NOT modify prompt functions yet (Phase 2)
- Do NOT add logging yet (Phase 3)

---

### Task Package 1.2: Temp Directory Tracking

**Scope:** Track temp directories for cleanup

**Files:** `install.sh`
**Lines to Modify:** 497-514 (install_mybb function)
**Estimated Changes:** ~10 lines modified

**Specifications:**

1. Modify line 497 (`TMP_DIR=$(mktemp -d)`):
   ```bash
   TMP_DIR=$(mktemp -d)
   TEMP_DIRS+=("$TMP_DIR")  # Track for cleanup
   ```

2. Remove explicit cleanup at line 514 (`rm -rf "$TMP_DIR"`) - trap handles it now

3. Add similar tracking anywhere else temp dirs are created

**Verification:**
- [ ] Fresh install creates temp dir, extracts MyBB, cleans up
- [ ] Interrupted install (Ctrl+C during download) cleans up temp dir
- [ ] `ls /tmp/tmp.*` shows no orphaned dirs after any exit

**Out of Scope:**
- Do NOT modify download logic
- Do NOT modify extraction logic

---

### Task Package 1.3: MariaDB Version Detection

**Scope:** Detect MariaDB version for auth method selection

**Files:** `install.sh`
**Lines to Modify:** 422-425 (insert before setup_database function body)
**Estimated Changes:** ~15 lines added

**Specifications:**

1. Add helper function before setup_database():
   ```bash
   detect_mariadb_version() {
       local version
       version=$(mariadb --version 2>/dev/null | grep -oP '\d+\.\d+' | head -1 || echo "0.0")
       echo "$version"
   }

   compare_versions() {
       # Returns 0 if $1 >= $2
       local v1="$1" v2="$2"
       [[ "$(printf '%s\n%s' "$v1" "$v2" | sort -V | head -1)" == "$v2" ]]
   }
   ```

2. Call at start of setup_database():
   ```bash
   local mariadb_version
   mariadb_version=$(detect_mariadb_version)
   info "Detected MariaDB version: $mariadb_version"
   ```

**Verification:**
- [ ] Version detected correctly on Ubuntu (should show 10.x)
- [ ] Version detected correctly on macOS
- [ ] Fallback to "0.0" if mariadb not installed yet

**Out of Scope:**
- Do NOT modify user creation yet (Task 1.4)
- Do NOT add connection verification yet (Task 1.5)

---

### Task Package 1.4: Unix Socket Auth Handling

**Scope:** Handle MariaDB 10.4+ authentication differences

**Files:** `install.sh`
**Lines to Modify:** 463-470 (database user creation)
**Estimated Changes:** ~25 lines modified

**Specifications:**

1. Replace current user creation block (lines 464-468):
   ```bash
   # Current (lines 464-468):
   sudo mariadb -e "CREATE USER IF NOT EXISTS '$MYBB_DB_USER'@'localhost' IDENTIFIED BY '$MYBB_DB_PASS';"
   sudo mariadb -e "ALTER USER '$MYBB_DB_USER'@'localhost' IDENTIFIED BY '$MYBB_DB_PASS';"
   ```

2. New version-aware block:
   ```bash
   # Escape password for SQL
   local escaped_pass="${MYBB_DB_PASS//\'/\'\'}"

   if compare_versions "$mariadb_version" "10.4"; then
       info "Using mysql_native_password for MariaDB 10.4+"
       sudo mariadb -e "CREATE USER IF NOT EXISTS '$MYBB_DB_USER'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('$escaped_pass');" 2>/dev/null || \
       sudo mariadb -e "ALTER USER '$MYBB_DB_USER'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('$escaped_pass');"
   else
       sudo mariadb -e "CREATE USER IF NOT EXISTS '$MYBB_DB_USER'@'localhost' IDENTIFIED BY '$escaped_pass';" 2>/dev/null || \
       sudo mariadb -e "ALTER USER '$MYBB_DB_USER'@'localhost' IDENTIFIED BY '$escaped_pass';"
   fi
   ```

3. Also escape database name with backticks in CREATE DATABASE (line 464)

**Verification:**
- [ ] User creation works on fresh MariaDB 10.4+ install
- [ ] User creation works when user already exists
- [ ] Password with special characters (single quote) works

**Out of Scope:**
- Do NOT add connection verification yet (Task 1.5)

---

### Task Package 1.5: Database Connection Verification

**Scope:** Verify database connection works after setup

**Files:** `install.sh`
**Lines to Modify:** 470-471 (after FLUSH PRIVILEGES, before success message)
**Estimated Changes:** ~15 lines added

**Specifications:**

1. Insert after `FLUSH PRIVILEGES;` (line 469):
   ```bash
   # Verify connection works
   info "Verifying database connection..."
   if mysql -u "$MYBB_DB_USER" -p"$MYBB_DB_PASS" -e "SELECT 1;" "$MYBB_DB_NAME" &>/dev/null; then
       success "Database connection verified!"
   else
       error "Database connection failed!"
       error "User: $MYBB_DB_USER, Database: $MYBB_DB_NAME"
       error "Please check MariaDB logs: sudo journalctl -u mariadb"
       return 1
   fi
   ```

2. The `return 1` will trigger ERR trap and cleanup

**Verification:**
- [ ] Successful setup shows "Database connection verified!"
- [ ] Wrong password shows error message with diagnostics
- [ ] Script exits with cleanup on verification failure

**Out of Scope:**
- Do NOT modify error messages elsewhere
- Do NOT add retry logic

---

## Phase 2 - High Priority Fixes
<!-- ID: phase_2 -->

**Objective:** Add input validation and SSH security improvements.

**Priority:** HIGH
**Estimated Lines:** ~100 lines changed
**Research Findings Addressed:** F4 (SSH Security), F5 (Input Validation), F6 (GitHub Auth)

**Dependencies:** Phase 1 complete (error handling infrastructure needed)

### Task Package 2.1: Input Validation Functions

**Scope:** Add validation helper functions

**Files:** `install.sh`
**Lines to Modify:** Insert after line 125 (after command_exists function)
**Estimated Changes:** ~50 lines added

**Specifications:**

1. Insert new "Input Validation" section:
   ```bash
   # ============================================
   # Input Validation
   # ============================================

   validate_db_name() {
       local name="$1"
       if [[ ! "$name" =~ ^[a-zA-Z][a-zA-Z0-9_]{0,63}$ ]]; then
           error "Invalid database name: must start with letter, contain only a-z, 0-9, underscore, max 64 chars"
           return 1
       fi
       return 0
   }

   validate_port() {
       local port="$1"
       if [[ ! "$port" =~ ^[0-9]+$ ]] || (( port < 1024 || port > 65535 )); then
           error "Invalid port: must be numeric, 1024-65535"
           return 1
       fi
       return 0
   }

   validate_password() {
       local pass="$1"
       if [[ -z "$pass" ]]; then
           error "Password cannot be empty"
           return 1
       fi
       if [[ "$pass" =~ [\'\"\\] ]]; then
           warn "Password contains special characters - will be escaped"
       fi
       return 0
   }

   prompt_validated() {
       local message="$1"
       local default="$2"
       local var_name="$3"
       local validator="$4"

       local value
       local attempts=0
       while (( attempts < 3 )); do
           prompt "$message" "$default" "value"
           if $validator "$value"; then
               eval "$var_name=\"$value\""
               return 0
           fi
           warn "Please try again (attempt $((attempts+1))/3)"
           ((attempts++))
       done
       error "Too many invalid attempts"
       return 1
   }
   ```

**Verification:**
- [ ] `validate_db_name "mybb_dev"` returns 0
- [ ] `validate_db_name "123bad"` returns 1 with error
- [ ] `validate_port "8022"` returns 0
- [ ] `validate_port "99999"` returns 1 with error

**Out of Scope:**
- Do NOT integrate with prompts yet (Task 2.2)

---

### Task Package 2.2: Integrate Validation with Database Prompts

**Scope:** Use validation in database setup

**Files:** `install.sh`
**Lines to Modify:** 451-458 (database prompts in setup_database), 529 (port prompt)
**Estimated Changes:** ~10 lines modified

**Specifications:**

1. Replace current prompts (lines 451-457):
   ```bash
   # Current:
   prompt "Database name" "$DEFAULT_DB_NAME" "MYBB_DB_NAME"
   prompt "Database user" "$DEFAULT_DB_USER" "MYBB_DB_USER"
   # ...
   prompt "Database password" "$DEFAULT_PASS" "MYBB_DB_PASS"
   ```

2. New validated prompts:
   ```bash
   prompt_validated "Database name" "$DEFAULT_DB_NAME" "MYBB_DB_NAME" "validate_db_name"
   prompt_validated "Database user" "$DEFAULT_DB_USER" "MYBB_DB_USER" "validate_db_name"
   # ...
   prompt_validated "Database password" "$DEFAULT_PASS" "MYBB_DB_PASS" "validate_password"
   ```

3. Also add port validation in save_env() (line 529):
   ```bash
   prompt_validated "MyBB development server port" "$DEFAULT_PORT" "MYBB_PORT" "validate_port"
   ```

**Verification:**
- [ ] Invalid database name rejected, re-prompted
- [ ] Invalid port rejected, re-prompted
- [ ] Empty password rejected
- [ ] Valid inputs accepted first try

**Out of Scope:**
- Do NOT modify SSH prompts (separate task)

---

### Task Package 2.3: SSH Key Security Enhancement

**Scope:** Add -a 100 flag and passphrase option

**Files:** `install.sh`
**Lines to Modify:** 353-366 (setup_ssh_auth function, key generation)
**Estimated Changes:** ~25 lines modified

**Specifications:**

1. Modify key generation (around line 359):
   ```bash
   # Current:
   ssh-keygen -t ed25519 -C "$ssh_email" -f "$SSH_KEY" -N ""

   # New:
   if prompt_yn "Protect SSH key with passphrase? (recommended)" "n"; then
       # ssh-keygen will prompt for passphrase interactively
       ssh-keygen -t ed25519 -a 100 -C "$ssh_email" -f "$SSH_KEY"
   else
       warn "Creating unencrypted SSH key (less secure for production)"
       ssh-keygen -t ed25519 -a 100 -C "$ssh_email" -f "$SSH_KEY" -N ""
   fi
   success "SSH key generated with strong key derivation (-a 100)"
   ```

2. Add key verification after ssh-add (around line 366):
   ```bash
   # Current:
   ssh-add "$SSH_KEY" 2>/dev/null

   # New:
   ssh-add "$SSH_KEY" 2>/dev/null || {
       warn "Could not add key to ssh-agent (may need passphrase)"
   }

   if ssh-add -l 2>/dev/null | grep -q "ed25519"; then
       success "SSH key loaded into agent"
   else
       warn "SSH key may not be loaded - check ssh-agent"
   fi
   ```

**Verification:**
- [ ] New key has -a 100 (check with `ssh-keygen -l -f ~/.ssh/id_ed25519`)
- [ ] Passphrase prompt appears when user chooses "y"
- [ ] No passphrase when user chooses "n"
- [ ] Key verification message shows success or warning

**Out of Scope:**
- Do NOT add key rotation
- Do NOT change existing key handling

---

### Task Package 2.4: GitHub CLI Timeout Protection

**Scope:** Add timeout to gh auth login

**Files:** `install.sh`
**Lines to Modify:** 413 (gh auth login call)
**Estimated Changes:** ~10 lines modified

**Specifications:**

1. Replace gh auth login (line 413):
   ```bash
   # Current:
   gh auth login

   # New:
   info "Starting GitHub CLI login (5 minute timeout)..."
   if command_exists timeout; then
       timeout 300 gh auth login || {
           warn "GitHub CLI login timed out or failed"
           warn "You can retry later with: gh auth login"
           return 1
       }
   else
       # timeout not available (e.g., macOS without coreutils)
       gh auth login
   fi
   ```

**Verification:**
- [ ] Normal login flow works
- [ ] If user waits 5+ minutes, timeout triggers
- [ ] Warning message shows retry command

**Out of Scope:**
- Do NOT install timeout command
- Do NOT change SSH verification logic

---

## Phase 3 - Medium Priority Enhancements
<!-- ID: phase_3 -->

**Objective:** Add unattended mode and logging for CI/CD support.

**Priority:** MEDIUM
**Estimated Lines:** ~80 lines changed
**Research Findings Addressed:** F7 (Unattended Mode), F8 (Logging)

**Dependencies:** Phase 2 complete (validation functions used by unattended mode)

### Task Package 3.1: Argument Parsing & Unattended Flag

**Scope:** Add -y/--non-interactive and --debug flags

**Files:** `install.sh`
**Lines to Modify:** 14-22 (configuration), 609-620 (main function start)
**Estimated Changes:** ~35 lines added

**Specifications:**

1. Add to configuration section (after line 22):
   ```bash
   # Runtime flags
   NON_INTERACTIVE="${MYBB_NON_INTERACTIVE:-}"
   DEBUG="${DEBUG:-}"
   ```

2. Add argument parsing function (before main):
   ```bash
   show_help() {
       echo "Usage: $0 [OPTIONS]"
       echo ""
       echo "Options:"
       echo "  -y, --non-interactive  Run without prompts (use env vars)"
       echo "  --debug                Enable debug output"
       echo "  -h, --help             Show this help"
       echo ""
       echo "Environment variables for non-interactive mode:"
       echo "  MYBB_DB_NAME, MYBB_DB_USER, MYBB_DB_PASS, MYBB_PORT"
       echo "  MYBB_INSTALL_MODE (fresh|update|skip)"
       echo "  MYBB_SKIP_DEPS, MYBB_SKIP_AUTH"
   }

   parse_args() {
       while [[ $# -gt 0 ]]; do
           case "$1" in
               -y|--non-interactive) NON_INTERACTIVE=1 ;;
               --debug) DEBUG=1; set -x ;;
               -h|--help) show_help; exit 0 ;;
               *) warn "Unknown option: $1" ;;
           esac
           shift
       done
   }

   is_interactive() {
       [[ -z "${NON_INTERACTIVE:-}" ]]
   }
   ```

3. Call parse_args at start of main():
   ```bash
   main() {
       parse_args "$@"
       # ... rest of main
   }
   ```

**Verification:**
- [ ] `./install.sh -h` shows help
- [ ] `./install.sh --debug` enables set -x
- [ ] `./install.sh -y` sets NON_INTERACTIVE=1

**Out of Scope:**
- Do NOT modify prompts yet (Task 3.2)

---

### Task Package 3.2: Non-Interactive Prompt Handling

**Scope:** Make prompts use env vars in non-interactive mode

**Files:** `install.sh`
**Lines to Modify:** 75-107 (prompt, prompt_yn, prompt_choice functions)
**Estimated Changes:** ~30 lines modified

**Specifications:**

1. Modify prompt() function:
   ```bash
   prompt() {
       local message="$1"
       local default="$2"
       local var_name="$3"

       # In non-interactive mode, use default
       if ! is_interactive; then
           eval "$var_name=\"$default\""
           info "$message: $default (non-interactive)"
           return 0
       fi

       # ... existing interactive code ...
   }
   ```

2. Modify prompt_yn() function:
   ```bash
   prompt_yn() {
       local message="$1"
       local default="$2"

       if ! is_interactive; then
           info "$message: $default (non-interactive)"
           [[ "$default" =~ ^[Yy] ]]
           return
       fi

       # ... existing interactive code ...
   }
   ```

3. Modify prompt_choice() - in non-interactive, return first option:
   ```bash
   prompt_choice() {
       local message="$1"
       shift
       local options=("$@")

       if ! is_interactive; then
           info "$message: 1 (non-interactive default)"
           echo "1"
           return
       fi

       # ... existing interactive code ...
   }
   ```

**Verification:**
- [ ] `MYBB_NON_INTERACTIVE=1 ./install.sh` runs without prompts
- [ ] All prompts show "(non-interactive)" in output
- [ ] Default values used throughout

**Out of Scope:**
- Do NOT add env var overrides for specific prompts (keep simple)

---

### Task Package 3.3: Logging Infrastructure

**Scope:** Add log file output

**Files:** `install.sh`
**Lines to Modify:** 14-22 (configuration), 53-67 (output functions)
**Estimated Changes:** ~25 lines added/modified

**Specifications:**

1. Add to configuration section:
   ```bash
   LOG_FILE="${SCRIPT_DIR}/install_$(date +%Y%m%d_%H%M%S).log"
   ```

2. Add logging helpers (after color definitions):
   ```bash
   strip_ansi() {
       sed 's/\x1b\[[0-9;]*m//g'
   }

   log_to_file() {
       [[ -n "${LOG_FILE:-}" ]] && echo "$1" | strip_ansi >> "$LOG_FILE"
   }

   init_logging() {
       touch "$LOG_FILE"
       echo "=== MyBB Playground Install Log ===" >> "$LOG_FILE"
       echo "Started: $(date)" >> "$LOG_FILE"
       echo "OS: $OS ($OS_FAMILY)" >> "$LOG_FILE"
       echo "===================================" >> "$LOG_FILE"
   }
   ```

3. Modify info/success/warn/error to call log_to_file():
   ```bash
   info() {
       echo -e "${BLUE}i${NC}  $1"
       log_to_file "[INFO] $1"
   }
   # Similar for success, warn, error
   ```

4. Call init_logging() in main() after detect_os()

5. Add LOG_FILE to .gitignore pattern (install_*.log)

**Verification:**
- [ ] Log file created in script directory
- [ ] Log file contains all messages without ANSI codes
- [ ] Can grep log file for errors after failed install

**Out of Scope:**
- Do NOT add log rotation
- Do NOT add verbose mode (--debug is sufficient)

---

## Milestone Tracking
<!-- ID: milestone_tracking -->

| Milestone | Target | Owner | Status | Evidence |
|-----------|--------|-------|--------|----------|
| Phase 1 Complete | TBD | Coder | Pending | All Task 1.x verified |
| Phase 2 Complete | TBD | Coder | Pending | All Task 2.x verified |
| Phase 3 Complete | TBD | Coder | Pending | All Task 3.x verified |
| Full Integration Test | TBD | Review | Pending | Fresh install on Ubuntu |

---

## Retro Notes & Adjustments
<!-- ID: retro_notes -->

*To be filled after each phase completion:*

- Phase 1 Retro: (pending)
- Phase 2 Retro: (pending)
- Phase 3 Retro: (pending)

---

## Appendix: Task Package Summary
<!-- ID: appendix -->

| Task | Lines | Est. Changes | Dependencies |
|------|-------|--------------|--------------|
| 1.1 Shell Options & Traps | 12, 36-50, 610 | ~40 lines | None |
| 1.2 Temp Dir Tracking | 497-514 | ~10 lines | 1.1 |
| 1.3 MariaDB Version Detect | 422-425 | ~15 lines | None |
| 1.4 Unix Socket Auth | 463-470 | ~25 lines | 1.3 |
| 1.5 Connection Verify | 470-471 | ~15 lines | 1.4 |
| 2.1 Validation Functions | 125+ | ~50 lines | 1.1 (error handling) |
| 2.2 Validate DB Prompts | 451-458, 529 | ~10 lines | 2.1 |
| 2.3 SSH Security | 353-366 | ~25 lines | None |
| 2.4 GH CLI Timeout | 413 | ~10 lines | None |
| 3.1 Arg Parsing | 14-22, 609-620 | ~35 lines | None |
| 3.2 Non-Interactive Prompts | 75-107 | ~30 lines | 3.1 |
| 3.3 Logging | 14-22, 53-67 | ~25 lines | None |

**Total: ~290 lines across 12 task packages**

---

*Phase Plan by MyBB-ArchitectAgent*
