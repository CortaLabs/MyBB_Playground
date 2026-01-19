---
id: private_plugin_infra-architecture-guide
title: "Architecture Guide - install.sh Hardening"
doc_name: ARCHITECTURE_GUIDE
category: engineering
status: active
version: '1.0'
last_updated: '2026-01-19'
maintained_by: Corta Labs
created_by: MyBB-ArchitectAgent
owners: []
related_docs:
  - RESEARCH_install_sh_gaps_analysis.md
  - custom.md
tags:
  - bash
  - install
  - hardening
  - production
summary: 'Architecture for hardening install.sh based on research findings'
---

# Architecture Guide - install.sh Hardening

**Author:** MyBB-ArchitectAgent
**Version:** 1.0
**Status:** Active
**Last Updated:** 2026-01-19 UTC

> This document defines the architecture for hardening the install.sh script based on research findings in RESEARCH_install_sh_gaps_analysis.md.

---

## 1. Problem Statement
<!-- ID: problem_statement -->

### Context

The `install.sh` script (634 lines) is the primary entry point for setting up MyBB Playground development environments. Research analysis identified **10 gap categories** affecting production readiness:

| Finding | Priority | Issue |
|---------|----------|-------|
| F1: Error Handling | CRITICAL | No trap handlers, temp files orphaned, no cleanup |
| F2: Cross-Platform | HIGH | Only 4 OS families, Alpine unsupported, fragile service detection |
| F3: Database Edge Cases | HIGH | MariaDB 10.4+ unix socket auth not handled, no verification |
| F4: SSH Security | MEDIUM | No passphrase, weak key derivation, unverified ssh-add |
| F5: Input Validation | MEDIUM | No validation for DB names, ports, passwords |
| F6: GitHub Auth | MEDIUM | Fragile grep parsing, gh auth can hang indefinitely |
| F7: Unattended Mode | MEDIUM | No CI/CD support, interactive-only |
| F8: Logging | LOW-MEDIUM | No log file, no debug mode |
| F9: ShellCheck | MEDIUM | No static analysis integration |
| F10: Platform Blind Spots | MEDIUM | macOS Xcode, SELinux, WSL networking |

### Goals

1. **Hardened Error Handling** - `set -Eeuo pipefail`, trap handlers, cleanup on exit
2. **Input Validation** - Prevent injection, validate ranges, escape SQL
3. **Database Robustness** - Handle unix socket auth, verify connections
4. **SSH Security** - Strong key derivation, optional passphrase
5. **Unattended Mode** - Environment variable support for CI/CD
6. **Logging** - Debug mode, log file output
7. **Broader Platform Support** - Alpine Linux, improved service detection

### Non-Goals (This Phase)

- GitHub API integration for auto-creating repos
- Full CI/CD pipeline with Docker test matrix
- ShellCheck GitHub Actions workflow
- SELinux context configuration

---

## 2. Requirements & Constraints
<!-- ID: requirements_constraints -->

### Functional Requirements

| Requirement | Description | Priority |
|-------------|-------------|----------|
| FR1 | Script must clean up temp files on any exit | CRITICAL |
| FR2 | Database connection must be verified after setup | HIGH |
| FR3 | All user input must be validated | MEDIUM |
| FR4 | Script must support unattended execution | MEDIUM |
| FR5 | Installation must be logged to file | LOW |

### Non-Functional Requirements

| Requirement | Description | Metric |
|-------------|-------------|--------|
| NFR1 | Backwards compatible | Existing .env files work |
| NFR2 | No new dependencies | Uses only bash builtins + existing tools |
| NFR3 | Portable across supported platforms | Works on Ubuntu, Debian, Fedora, Arch, macOS, Alpine |

### Constraints

- **Script size:** Must remain maintainable (~700-800 lines max)
- **No Python/Node:** Pure bash for zero-dependency bootstrap
- **Interactive default:** Unattended mode is opt-in, not default

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing installations | HIGH | Test update mode preserves data |
| MariaDB version differences | MEDIUM | Version detection before auth method |
| SSH passphrase breaks automation | LOW | Skip passphrase in unattended mode |

---

## 3. Architecture Overview
<!-- ID: architecture_overview -->

### Solution Summary

Harden install.sh through **defense-in-depth** layers:

```
Layer 1: Shell Options     (set -Eeuo pipefail)
Layer 2: Trap Handlers     (ERR/EXIT cleanup)
Layer 3: Input Validation  (validate_* functions)
Layer 4: Command Verification (check return codes)
Layer 5: Logging           (dual console/file output)
```

### Script Structure (Post-Hardening)

```
install.sh (estimated ~720 lines after hardening)
├── Configuration (lines 14-30)
│   ├── Version, URLs, defaults
│   ├── LOG_FILE path
│   └── NON_INTERACTIVE flag
├── Colors & Formatting (lines 32-50)
├── Error Handling (lines 52-85) [NEW]
│   ├── cleanup() function
│   ├── error_handler() function
│   └── trap setup
├── Logging Functions (lines 87-120) [ENHANCED]
│   ├── log_to_file()
│   ├── info(), success(), warn(), error()
│   └── Debug mode support
├── Input Validation (lines 122-170) [NEW]
│   ├── validate_db_name()
│   ├── validate_port()
│   └── validate_password()
├── Prompt Functions (lines 172-230) [ENHANCED]
│   ├── prompt() with validation
│   ├── prompt_yn() with unattended support
│   └── prompt_choice() with unattended support
├── OS Detection (lines 232-285) [ENHANCED]
│   └── Alpine Linux support
├── Dependency Installation (lines 287-360) [ENHANCED]
│   └── Alpine case added
├── Previous Installation (lines 362-445)
├── Git Authentication (lines 447-560) [ENHANCED]
│   ├── SSH: -a 100, passphrase option
│   ├── GitHub CLI: timeout protection
│   └── Verification improvements
├── Database Setup (lines 562-640) [ENHANCED]
│   ├── MariaDB version detection
│   ├── Unix socket auth handling
│   └── Connection verification
├── MyBB Installation (lines 642-700)
├── Environment Configuration (lines 702-760)
├── Summary (lines 762-810)
└── Main (lines 812-850) [ENHANCED]
    ├── Argument parsing (-y, --debug)
    └── trap registration
```

### Data Flow

```
User Input → validate_*() → prompt() → Function Logic → verify_*() → Log
     ↓                                        ↓
  Reject if invalid                    Cleanup on failure
```

---

## 4. Detailed Design
<!-- ID: detailed_design -->

### 4.1 Error Handling Subsystem

**Purpose:** Ensure cleanup runs on any exit, capture failures with context.

**Location:** Lines 52-85 (new section after Colors)

**Components:**

```bash
# Global state for cleanup
TEMP_DIRS=()
CLEANUP_DONE=false

cleanup() {
    [[ "$CLEANUP_DONE" == "true" ]] && return
    CLEANUP_DONE=true

    # Remove tracked temp directories
    for dir in "${TEMP_DIRS[@]}"; do
        [[ -d "$dir" ]] && rm -rf "$dir"
    done

    # Kill any background processes we started
    jobs -p | xargs -r kill 2>/dev/null || true
}

error_handler() {
    local line_no="$1"
    local exit_code="$2"
    error "Script failed at line $line_no with exit code $exit_code"
    error "Check log file: $LOG_FILE"
}

# Trap registration (in main, before any work)
trap cleanup EXIT
trap 'error_handler $LINENO $?' ERR
```

**Shell Options (line 12):**
```bash
set -Eeuo pipefail
```

- `-E`: ERR trap inherited by functions
- `-e`: Exit on error
- `-u`: Error on undefined variables
- `-o pipefail`: Pipeline fails if any command fails

### 4.2 Input Validation Subsystem

**Purpose:** Prevent injection, ensure valid ranges, provide helpful errors.

**Location:** Lines 122-170 (new section)

**Components:**

```bash
validate_db_name() {
    local name="$1"
    # Must start with letter, contain only alphanumeric and underscore
    # Max 64 chars (MySQL limit)
    if [[ ! "$name" =~ ^[a-zA-Z][a-zA-Z0-9_]{0,63}$ ]]; then
        error "Invalid database name: must start with letter, contain only a-z, 0-9, underscore, max 64 chars"
        return 1
    fi
    return 0
}

validate_port() {
    local port="$1"
    # Numeric, range 1024-65535 (avoid privileged ports)
    if [[ ! "$port" =~ ^[0-9]+$ ]] || (( port < 1024 || port > 65535 )); then
        error "Invalid port: must be numeric, 1024-65535"
        return 1
    fi
    return 0
}

validate_password() {
    local pass="$1"
    # Non-empty, warn on characters that need SQL escaping
    if [[ -z "$pass" ]]; then
        error "Password cannot be empty"
        return 1
    fi
    if [[ "$pass" =~ [\'\"\\] ]]; then
        warn "Password contains special characters - will be escaped for SQL"
    fi
    return 0
}

escape_sql() {
    local str="$1"
    # Escape single quotes for SQL
    echo "${str//\'/\'\'}"
}
```

**Integration with prompt():**

```bash
prompt_validated() {
    local message="$1"
    local default="$2"
    local var_name="$3"
    local validator="$4"  # Function name

    local value
    while true; do
        prompt "$message" "$default" "value"
        if $validator "$value"; then
            eval "$var_name=\"$value\""
            return 0
        fi
        warn "Please try again"
    done
}
```

### 4.3 Database Setup Subsystem

**Purpose:** Handle MariaDB version differences, verify connections.

**Location:** Lines 562-640 (enhanced setup_database function)

**Key Changes:**

```bash
# Detect MariaDB version for auth method
detect_mariadb_version() {
    local version
    version=$(mariadb --version 2>/dev/null | grep -oP '\d+\.\d+' | head -1)
    echo "$version"
}

setup_database() {
    # ... existing preamble ...

    # Validate inputs
    prompt_validated "Database name" "$DEFAULT_DB_NAME" "MYBB_DB_NAME" "validate_db_name"
    prompt_validated "Database user" "$DEFAULT_DB_USER" "MYBB_DB_USER" "validate_db_name"

    # Generate and validate password
    DEFAULT_PASS="mybb_$(openssl rand -hex 6)"
    prompt_validated "Database password" "$DEFAULT_PASS" "MYBB_DB_PASS" "validate_password"

    # Escape password for SQL
    local escaped_pass
    escaped_pass=$(escape_sql "$MYBB_DB_PASS")

    # Detect MariaDB version
    local mariadb_version
    mariadb_version=$(detect_mariadb_version)
    info "Detected MariaDB version: $mariadb_version"

    # Create database and user
    info "Creating database and user..."
    sudo mariadb -e "CREATE DATABASE IF NOT EXISTS \`$MYBB_DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" || {
        error "Failed to create database"
        return 1
    }

    # For MariaDB 10.4+, use mysql_native_password for compatibility
    if [[ "$(echo "$mariadb_version >= 10.4" | bc -l)" == "1" ]]; then
        sudo mariadb -e "CREATE USER IF NOT EXISTS '$MYBB_DB_USER'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('$escaped_pass');" || {
            # User might exist, try ALTER
            sudo mariadb -e "ALTER USER '$MYBB_DB_USER'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('$escaped_pass');"
        }
    else
        sudo mariadb -e "CREATE USER IF NOT EXISTS '$MYBB_DB_USER'@'localhost' IDENTIFIED BY '$escaped_pass';"
        sudo mariadb -e "ALTER USER '$MYBB_DB_USER'@'localhost' IDENTIFIED BY '$escaped_pass';"
    fi

    sudo mariadb -e "GRANT ALL PRIVILEGES ON \`$MYBB_DB_NAME\`.* TO '$MYBB_DB_USER'@'localhost';"
    sudo mariadb -e "FLUSH PRIVILEGES;"

    # VERIFY CONNECTION
    info "Verifying database connection..."
    if mysql -u "$MYBB_DB_USER" -p"$MYBB_DB_PASS" -e "SELECT 1;" "$MYBB_DB_NAME" &>/dev/null; then
        success "Database connection verified!"
    else
        error "Database connection failed - check credentials"
        return 1
    fi

    success "Database configured"
}
```

### 4.4 Unattended Mode Subsystem

**Purpose:** Enable CI/CD and automated deployments.

**Location:** Main function and prompt functions

**Environment Variables:**

| Variable | Purpose | Default |
|----------|---------|---------|
| `MYBB_NON_INTERACTIVE` | Enable unattended mode | (not set) |
| `MYBB_DB_NAME` | Database name | mybb_dev |
| `MYBB_DB_USER` | Database user | mybb_user |
| `MYBB_DB_PASS` | Database password | (auto-generated) |
| `MYBB_PORT` | Server port | 8022 |
| `MYBB_INSTALL_MODE` | fresh/update/skip | fresh |
| `MYBB_SKIP_DEPS` | Skip dependency install | (not set) |
| `MYBB_SKIP_AUTH` | Skip git auth setup | (not set) |

**Argument Parsing:**

```bash
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -y|--non-interactive)
                NON_INTERACTIVE=1
                ;;
            --debug)
                DEBUG=1
                set -x
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                warn "Unknown option: $1"
                ;;
        esac
        shift
    done
}

is_interactive() {
    [[ -z "${NON_INTERACTIVE:-}" ]]
}
```

**Modified prompt function:**

```bash
prompt() {
    local message="$1"
    local default="$2"
    local var_name="$3"
    local env_var="${4:-}"  # Optional: env var to check

    # In non-interactive mode, use env var or default
    if ! is_interactive; then
        if [[ -n "$env_var" ]] && [[ -n "${!env_var:-}" ]]; then
            eval "$var_name=\"${!env_var}\""
        else
            eval "$var_name=\"$default\""
        fi
        info "$message: ${!var_name} (non-interactive)"
        return 0
    fi

    # Interactive mode - existing behavior
    # ...
}
```

### 4.5 SSH Security Subsystem

**Purpose:** Stronger key generation, verification.

**Location:** Lines 447-500 (setup_ssh_auth function)

**Key Changes:**

```bash
setup_ssh_auth() {
    # ...existing checks...

    SSH_KEY="$HOME/.ssh/id_ed25519"

    if [ -f "$SSH_KEY" ]; then
        info "SSH key already exists at $SSH_KEY"
    else
        prompt "Enter your email for the SSH key" "" "ssh_email"

        # Passphrase handling
        local passphrase_opt=""
        if is_interactive; then
            if prompt_yn "Protect SSH key with passphrase? (recommended)" "y"; then
                # ssh-keygen will prompt for passphrase
                passphrase_opt=""
            else
                passphrase_opt="-N \"\""
                warn "Creating unencrypted SSH key (less secure)"
            fi
        else
            # Non-interactive: no passphrase
            passphrase_opt="-N \"\""
            warn "Non-interactive mode: creating unencrypted SSH key"
        fi

        # Generate with strong key derivation
        eval ssh-keygen -t ed25519 -a 100 -C "$ssh_email" -f "$SSH_KEY" $passphrase_opt
        success "SSH key generated with strong key derivation (-a 100)"
    fi

    # Start ssh-agent if needed
    if [[ -z "${SSH_AUTH_SOCK:-}" ]]; then
        eval "$(ssh-agent -s)"
    fi

    # Add key and verify
    ssh-add "$SSH_KEY" 2>/dev/null || {
        warn "Could not add key to ssh-agent (may need passphrase)"
    }

    # Verify key is loaded
    if ssh-add -l 2>/dev/null | grep -q "ed25519"; then
        success "SSH key loaded into agent"
    else
        warn "SSH key may not be loaded - check ssh-agent"
    fi

    # ...rest of function (display key, test connection)...
}
```

### 4.6 Logging Subsystem

**Purpose:** Capture all output for troubleshooting.

**Location:** Configuration section and logging functions

**Components:**

```bash
# Configuration section
LOG_FILE="${SCRIPT_DIR}/install_$(date +%Y%m%d_%H%M%S).log"
DEBUG="${DEBUG:-}"

# Initialize log file
init_logging() {
    touch "$LOG_FILE"
    echo "=== MyBB Playground Install Log ===" >> "$LOG_FILE"
    echo "Started: $(date)" >> "$LOG_FILE"
    echo "===================================" >> "$LOG_FILE"
}

# Strip ANSI colors for log file
strip_ansi() {
    sed 's/\x1b\[[0-9;]*m//g'
}

# Log to file (called by info/success/warn/error)
log_to_file() {
    echo "$1" | strip_ansi >> "$LOG_FILE"
}

# Enhanced output functions
info() {
    local msg="${BLUE}i${NC}  $1"
    echo -e "$msg"
    log_to_file "[INFO] $1"
}

success() {
    local msg="${GREEN}v${NC}  $1"
    echo -e "$msg"
    log_to_file "[SUCCESS] $1"
}

warn() {
    local msg="${YELLOW}!${NC}  $1"
    echo -e "$msg"
    log_to_file "[WARN] $1"
}

error() {
    local msg="${RED}x${NC}  $1"
    echo -e "$msg" >&2
    log_to_file "[ERROR] $1"
}
```

### 4.7 Alpine Linux Support

**Purpose:** Support containerized environments.

**Location:** OS detection and dependency installation

**Components:**

```bash
# In detect_os()
elif [[ -f /etc/alpine-release ]]; then
    OS="alpine"
    OS_FAMILY="alpine"
    PKG_MANAGER="apk"

# In install_dependencies()
alpine)
    info "Detected Alpine Linux - using apk"
    sudo apk update
    sudo apk add \
        php81 php81-cli php81-mysqli php81-gd php81-mbstring php81-xml php81-curl php81-zip \
        mariadb mariadb-client \
        git curl unzip
    sudo rc-service mariadb start
    sudo rc-update add mariadb
    ;;
```

---

## 5. Directory Structure
<!-- ID: directory_structure -->

```
/home/austin/projects/MyBB_Playground/
├── install.sh                    # Target of this architecture
├── .env                          # Generated config (gitignored)
├── .mybb-forge.env               # Private repo config template
├── install_*.log                 # Installation logs (gitignored)
├── TestForum/                    # MyBB installation
└── .scribe/docs/dev_plans/private_plugin_infra/
    ├── ARCHITECTURE_GUIDE.md     # This document
    ├── PHASE_PLAN.md             # Implementation phases
    ├── CHECKLIST.md              # Verification criteria
    └── research/
        └── RESEARCH_install_sh_gaps_analysis.md
```

---

## 6. Testing & Validation Strategy
<!-- ID: testing_strategy -->

### Manual Testing Matrix

| Scenario | Platform | Mode | Expected Result |
|----------|----------|------|-----------------|
| Fresh install | Ubuntu 22.04 | Interactive | Full setup, DB works |
| Fresh install | macOS | Interactive | Full setup, DB works |
| Fresh install | Alpine | Interactive | Full setup, DB works |
| Update existing | Ubuntu | Interactive | Data preserved |
| Unattended | Ubuntu | -y flag | No prompts, DB works |
| Error recovery | Any | Ctrl+C mid-install | Temp files cleaned |
| Invalid input | Any | Interactive | Rejects, re-prompts |

### Verification Commands

```bash
# Test error handling
bash -n install.sh              # Syntax check
shellcheck install.sh           # Static analysis (if available)

# Test unattended mode
MYBB_DB_PASS=test123 MYBB_INSTALL_MODE=fresh ./install.sh -y

# Test database connection after install
mysql -u mybb_user -p$MYBB_DB_PASS -e "SELECT 1;" mybb_dev

# Test cleanup on error
bash -c 'source install.sh; TEMP_DIRS+=(/tmp/test$$); mkdir -p /tmp/test$$; exit 1'
ls /tmp/test$$  # Should not exist
```

---

## 7. Open Questions & Follow-Ups
<!-- ID: open_questions -->

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| ShellCheck CI integration | Future | DEFERRED | Add after core hardening |
| Docker test matrix | Future | DEFERRED | Useful but not blocking |
| SELinux context for Fedora | Future | DEFERRED | Edge case, document workaround |

---

## 8. References & Appendix
<!-- ID: references_appendix -->

### Source Documents

- **Research:** `RESEARCH_install_sh_gaps_analysis.md` - Comprehensive gap analysis
- **Spec:** `custom.md` - Original project specification

### Research References

- [Production Bash Standards 2025 - Medium](https://medium.com/@prasanna.a1.usage/best-practices-we-need-to-follow-in-bash-scripting-in-2025-cebcdf254768)
- [Bash Error Handling - RedHat](https://www.redhat.com/en/blog/bash-error-handling)
- [SSH Key Best Practices 2025](https://www.brandonchecketts.com/archives/ssh-ed25519-key-best-practices-for-2025)
- [MariaDB Unix Socket Auth](https://mariadb.com/kb/en/authentication-plugin-unix-socket/)

### Line Number Reference (Current Script)

| Section | Lines | Status |
|---------|-------|--------|
| Configuration | 14-22 | Enhance with LOG_FILE |
| Colors | 24-35 | Keep as-is |
| Helpers | 39-125 | Add validation functions |
| OS Detection | 127-168 | Add Alpine |
| Dependencies | 170-222 | Add Alpine case |
| Previous Install | 224-298 | Minor cleanup |
| Git Auth | 300-420 | SSH security, gh timeout |
| Database | 422-473 | Major: version detect, verify |
| MyBB Install | 475-520 | Minor cleanup |
| Env Config | 522-565 | Keep as-is |
| Summary | 567-603 | Keep as-is |
| Main | 605-634 | Add arg parsing, traps |

---

*Architecture by MyBB-ArchitectAgent based on RESEARCH_install_sh_gaps_analysis.md*
