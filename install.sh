#!/bin/bash
# ============================================
# MyBB Playground - Production Install Script
# ============================================
# Interactive installer with:
# - OS detection (Ubuntu/Debian, macOS, WSL)
# - Previous installation handling
# - Git authentication setup
# - Private plugin support
# ============================================

set -Eeuo pipefail

# ============================================
# Configuration
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MYBB_VERSION_FALLBACK="1839"
MYBB_VERSION=""
MYBB_DOWNLOAD_URL=""
DEFAULT_PORT=8022
DEFAULT_DB_NAME="mybb_dev"
DEFAULT_DB_USER="mybb_user"
DEFAULT_PASS=""
DEFAULT_DB_PREFIX="mybb_"
DEFAULT_MYBB_ROOT=""
DEFAULT_MYBB_URL=""

# Runtime flags (can be set via env vars or args)
NON_INTERACTIVE="${MYBB_NON_INTERACTIVE:-}"
DEBUG="${DEBUG:-}"
LOG_FILE=""

# ============================================
# Colors & Formatting
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ============================================
# Logging Infrastructure
# ============================================

strip_ansi() {
    sed 's/\x1b\[[0-9;]*m//g'
}

log_to_file() {
    [[ -n "${LOG_FILE:-}" ]] && echo "$1" | strip_ansi >> "$LOG_FILE"
}

init_logging() {
    mkdir -p "${SCRIPT_DIR}/logs"
    LOG_FILE="${SCRIPT_DIR}/logs/install_$(date +%Y%m%d_%H%M%S).log"
    touch "$LOG_FILE"
    {
        echo "=== MyBB Playground Install Log ==="
        echo "Started: $(date)"
        echo "OS: ${OS:-unknown} (${OS_FAMILY:-unknown})"
        echo "Args: $*"
        echo "Non-interactive: ${NON_INTERACTIVE:-no}"
        echo "==================================="
        echo ""
    } >> "$LOG_FILE"
}

# ============================================
# Error Handling
# ============================================
TEMP_DIRS=()
CLEANUP_DONE=false

cleanup() {
    if [[ "$CLEANUP_DONE" == "true" ]]; then
        return
    fi
    CLEANUP_DONE=true

    # Clean up any registered temp directories
    for dir in "${TEMP_DIRS[@]}"; do
        if [[ -d "$dir" ]]; then
            rm -rf "$dir" 2>/dev/null || true
        fi
    done
}

error_handler() {
    local line="$1"
    local exit_code="$2"
    error "Script failed at line $line with exit code $exit_code"
}

# ============================================
# Helper Functions
# ============================================

banner() {
    clear
    echo -e "${CYAN}"
    cat << 'EOF'

    ███╗   ███╗██╗   ██╗██████╗ ██████╗
    ████╗ ████║╚██╗ ██╔╝██╔══██╗██╔══██╗
    ██╔████╔██║ ╚████╔╝ ██████╔╝██████╔╝
    ██║╚██╔╝██║  ╚██╔╝  ██╔══██╗██╔══██╗
    ██║ ╚═╝ ██║   ██║   ██████╔╝██████╔╝
    ╚═╝     ╚═╝   ╚═╝   ╚═════╝ ╚═════╝
EOF
    echo -e "${BOLD}${MAGENTA}           P L A Y G R O U N D${NC}"
    echo -e "${DIM}      AI-Assisted Development Toolkit${NC}"
    echo ""
    echo -e "${DIM}             ─── ${NC}${BOLD}Corta Labs${NC}${DIM} ───${NC}"
    echo ""
}

info() {
    echo -e "${BLUE}ℹ${NC}  $1"
    log_to_file "[INFO] $1"
}

success() {
    echo -e "${GREEN}✓${NC}  $1"
    log_to_file "[OK] $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC}  $1"
    log_to_file "[WARN] $1"
}

error() {
    echo -e "${RED}✗${NC}  $1" >&2
    log_to_file "[ERROR] $1"
}

step() {
    echo ""
    echo -e "${MAGENTA}${BOLD}▶ $1${NC}"
    echo -e "${DIM}─────────────────────────────────────────${NC}"
}

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

    if [ -n "$default" ]; then
        echo -en "${CYAN}?${NC}  ${message} [${default}]: "
    else
        echo -en "${CYAN}?${NC}  ${message}: "
    fi

    read -r input
    if [ -z "$input" ] && [ -n "$default" ]; then
        eval "$var_name=\"$default\""
    else
        eval "$var_name=\"$input\""
    fi
}

prompt_yn() {
    local message="$1"
    local default="$2"

    # In non-interactive mode, use default
    if ! is_interactive; then
        info "$message: $default (non-interactive)"
        [[ "$default" =~ ^[Yy] ]]
        return
    fi

    if [ "$default" = "y" ]; then
        echo -en "${CYAN}?${NC}  ${message} [Y/n]: "
    else
        echo -en "${CYAN}?${NC}  ${message} [y/N]: "
    fi

    read -r input
    input="${input:-$default}"
    [[ "$input" =~ ^[Yy] ]]
}

prompt_choice() {
    local message="$1"
    shift
    local options=("$@")

    # In non-interactive mode, use first option (or MYBB_INSTALL_MODE if set)
    if ! is_interactive; then
        local default_choice="${MYBB_INSTALL_MODE:-1}"
        # Map mode names to numbers if needed
        case "$default_choice" in
            update) default_choice=1 ;;
            fresh)  default_choice=2 ;;
            skip)   default_choice=3 ;;
        esac
        info "$message: $default_choice (non-interactive)"
        echo "$default_choice"
        return
    fi

    # Output menu to stderr so it's visible when capturing result with $()
    echo -e "${CYAN}?${NC}  ${message}" >&2
    for i in "${!options[@]}"; do
        echo -e "   ${BOLD}$((i+1))${NC}) ${options[$i]}" >&2
    done
    echo -en "   Choice [1-${#options[@]}]: " >&2
    read -r choice

    # Handle empty input - re-prompt up to 3 times
    local attempts=0
    while [[ -z "$choice" && $attempts -lt 3 ]]; do
        echo -en "   Please enter a choice [1-${#options[@]}]: " >&2
        read -r choice
        ((attempts++))
    done

    # Default to last option (usually exit/cancel) if still empty
    if [[ -z "$choice" ]]; then
        choice="${#options[@]}"
    fi

    # Return choice to stdout for capture
    echo "$choice"
}

command_exists() {
    command -v "$1" &> /dev/null
}

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

# ============================================
# Existing Environment Loading
# ============================================

load_existing_env() {
    local env_file="${1:-.env}"

    if [[ -f "$env_file" ]]; then
        info "Found existing $env_file - loading as defaults"

        # Source safely (only export known vars)
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ -z "$key" || "$key" =~ ^# ]] && continue
            # Remove quotes from value
            value="${value%\"}"
            value="${value#\"}"
            value="${value%\'}"
            value="${value#\'}"

            case "$key" in
                MYBB_DB_HOST)   DEFAULT_DB_HOST="$value" ;;
                MYBB_DB_NAME)   DEFAULT_DB_NAME="$value" ;;
                MYBB_DB_USER)   DEFAULT_DB_USER="$value" ;;
                MYBB_DB_PASS)   DEFAULT_PASS="$value" ;;
                MYBB_DB_PREFIX) DEFAULT_DB_PREFIX="$value" ;;
                MYBB_PORT)      DEFAULT_PORT="$value" ;;
                MYBB_ROOT)      DEFAULT_MYBB_ROOT="$value" ;;
                MYBB_URL)       DEFAULT_MYBB_URL="$value" ;;
            esac
        done < "$env_file"

        success "Loaded existing configuration from $env_file"
        return 0
    fi
    return 1
}

# ============================================
# Argument Parsing
# ============================================

show_help() {
    cat << 'EOF'
Usage: ./install.sh [OPTIONS]

Options:
  -y, --non-interactive  Run without prompts (use env vars/defaults)
  --debug                Enable debug output (set -x)
  --env FILE             Load environment from FILE (default: .env)
  -h, --help             Show this help

Environment variables for non-interactive mode:
  MYBB_DB_NAME, MYBB_DB_USER, MYBB_DB_PASS, MYBB_PORT
  MYBB_INSTALL_MODE (fresh|update|skip)
  MYBB_SKIP_DEPS=1, MYBB_SKIP_AUTH=1

Multi-forum support (future):
  MYBB_INSTANCE_NAME     Instance identifier (default: main)

EOF
}

parse_args() {
    ENV_FILE=".env"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -y|--non-interactive) NON_INTERACTIVE=1 ;;
            --debug) DEBUG=1; set -x ;;
            --env) ENV_FILE="$2"; shift ;;
            -h|--help) show_help; exit 0 ;;
            *) warn "Unknown option: $1" ;;
        esac
        shift
    done
}

is_interactive() {
    [[ -z "${NON_INTERACTIVE:-}" ]]
}

# ============================================
# OS Detection
# ============================================

detect_os() {
    OS="unknown"
    OS_FAMILY="unknown"
    PKG_MANAGER=""

    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        OS_FAMILY="macos"
        PKG_MANAGER="brew"
    elif [[ -f /etc/os-release ]]; then
        source /etc/os-release
        case "$ID" in
            ubuntu|debian|pop|linuxmint)
                OS="$ID"
                OS_FAMILY="debian"
                PKG_MANAGER="apt"
                ;;
            fedora|rhel|centos|rocky|almalinux)
                OS="$ID"
                OS_FAMILY="redhat"
                PKG_MANAGER="dnf"
                ;;
            arch|manjaro)
                OS="$ID"
                OS_FAMILY="arch"
                PKG_MANAGER="pacman"
                ;;
        esac
    fi

    # Detect WSL
    IS_WSL=false
    if grep -qi microsoft /proc/version 2>/dev/null; then
        IS_WSL=true
    fi

    export OS OS_FAMILY PKG_MANAGER IS_WSL
}

# ============================================
# Dependency Installation
# ============================================

install_dependencies() {
    step "Installing Dependencies"

    case "$OS_FAMILY" in
        debian)
            info "Detected Debian/Ubuntu - using apt"
            sudo apt update
            sudo apt install -y \
                php php-cli php-mysql php-gd php-mbstring php-xml php-curl php-zip \
                mariadb-server mariadb-client \
                git curl unzip
            ;;
        macos)
            info "Detected macOS - using Homebrew"
            if ! command_exists brew; then
                warn "Homebrew not found. Installing..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install php mariadb git curl
            brew services start mariadb
            ;;
        redhat)
            info "Detected RHEL/Fedora - using dnf"
            sudo dnf install -y \
                php php-cli php-mysqlnd php-gd php-mbstring php-xml php-curl php-zip \
                mariadb-server mariadb \
                git curl unzip
            sudo systemctl start mariadb
            sudo systemctl enable mariadb
            ;;
        arch)
            info "Detected Arch Linux - using pacman"
            sudo pacman -Sy --noconfirm \
                php php-gd \
                mariadb \
                git curl unzip
            sudo mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql
            sudo systemctl start mariadb
            sudo systemctl enable mariadb
            ;;
        *)
            error "Unsupported OS: $OS"
            echo "Please install manually: PHP 8+, MariaDB/MySQL, git, curl, unzip"
            exit 1
            ;;
    esac

    success "Dependencies installed"
}

# ============================================
# Previous Installation Detection
# ============================================

detect_previous_install() {
    PREV_INSTALL=false
    PREV_ENV=false
    PREV_TESTFORUM=false
    PREV_DATABASE=false

    if [ -f "$SCRIPT_DIR/.env" ]; then
        PREV_ENV=true
        PREV_INSTALL=true
        source "$SCRIPT_DIR/.env"
    fi

    if [ -d "$SCRIPT_DIR/TestForum" ] && [ -f "$SCRIPT_DIR/TestForum/inc/config.php" ]; then
        PREV_TESTFORUM=true
        PREV_INSTALL=true
    fi

    # Check if database exists
    if [ -n "$MYBB_DB_NAME" ]; then
        if mysql -u root -e "USE $MYBB_DB_NAME" 2>/dev/null; then
            PREV_DATABASE=true
            PREV_INSTALL=true
        fi
    fi

    export PREV_INSTALL PREV_ENV PREV_TESTFORUM PREV_DATABASE
}

handle_previous_install() {
    if [ "$PREV_INSTALL" = true ]; then
        step "Previous Installation Detected"

        [ "$PREV_ENV" = true ] && info "Found: .env configuration file"
        [ "$PREV_TESTFORUM" = true ] && info "Found: TestForum installation"
        [ "$PREV_DATABASE" = true ] && info "Found: Database '$MYBB_DB_NAME'"

        echo ""
        choice=$(prompt_choice "What would you like to do?" \
            "Update/repair (keep data)" \
            "Fresh install (wipe everything)" \
            "Skip setup (keep existing)" \
            "Exit")

        case "$choice" in
            1)
                INSTALL_MODE="update"
                info "Will update while preserving data"
                ;;
            2)
                INSTALL_MODE="fresh"
                warn "Will perform fresh install - ALL DATA WILL BE LOST"
                if ! prompt_yn "Are you absolutely sure?" "n"; then
                    info "Aborted"
                    exit 0
                fi
                ;;
            3)
                INSTALL_MODE="skip"
                info "Skipping MyBB setup"
                ;;
            4|*)
                info "Exiting"
                exit 0
                ;;
        esac
    else
        INSTALL_MODE="fresh"
    fi

    export INSTALL_MODE
}

# ============================================
# Git Authentication
# ============================================

setup_git_auth() {
    step "Git Authentication Setup"

    # Check current auth status
    SSH_OK=false
    GH_OK=false

    if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
        SSH_OK=true
        success "SSH authentication working"
    fi

    if command_exists gh && gh auth status &>/dev/null; then
        GH_OK=true
        success "GitHub CLI authenticated"
    fi

    if [ "$SSH_OK" = true ] || [ "$GH_OK" = true ]; then
        success "Git authentication working - you're all set!"
        return 0
    fi

    echo ""
    choice=$(prompt_choice "How would you like to authenticate with GitHub?" \
        "SSH Key (project-specific, won't touch existing keys)" \
        "GitHub CLI (easiest setup)" \
        "Skip (configure later)")

    case "$choice" in
        1)
            setup_ssh_auth
            ;;
        2)
            setup_gh_cli
            ;;
        3)
            warn "Skipping git auth - private repos won't work until configured"
            ;;
    esac
}

setup_ssh_auth() {
    info "Setting up SSH authentication (project-specific key)"

    # Use project-specific key to avoid overwriting existing SSH keys
    SSH_KEY="$HOME/.ssh/id_ed25519_mybb_playground"
    SSH_CONFIG="$HOME/.ssh/config"

    if [ -f "$SSH_KEY" ]; then
        info "MyBB Playground SSH key already exists"
    else
        prompt "Enter your email for the SSH key" "" "ssh_email"
        if prompt_yn "Protect SSH key with passphrase? (recommended)" "n"; then
            # ssh-keygen will prompt for passphrase interactively
            ssh-keygen -t ed25519 -a 100 -C "$ssh_email (MyBB Playground)" -f "$SSH_KEY"
        else
            warn "Creating unencrypted SSH key (less secure for production)"
            ssh-keygen -t ed25519 -a 100 -C "$ssh_email (MyBB Playground)" -f "$SSH_KEY" -N ""
        fi
        success "SSH key generated: $SSH_KEY"
    fi

    # Add SSH config entry for this key (if not already present)
    if ! grep -q "# MyBB Playground" "$SSH_CONFIG" 2>/dev/null; then
        info "Adding SSH config entry for MyBB Playground..."
        mkdir -p "$HOME/.ssh"
        cat >> "$SSH_CONFIG" << EOF

# MyBB Playground - project-specific key
Host github.com-mybb
    HostName github.com
    User git
    IdentityFile $SSH_KEY
    IdentitiesOnly yes
EOF
        chmod 600 "$SSH_CONFIG"
        success "SSH config updated"
    fi

    # Start ssh-agent if needed
    eval "$(ssh-agent -s)" &>/dev/null
    ssh-add "$SSH_KEY" 2>/dev/null || {
        warn "Could not add key to ssh-agent (may need passphrase)"
    }

    if ssh-add -l 2>/dev/null | grep -q "mybb_playground"; then
        success "SSH key loaded into agent"
    else
        warn "SSH key may not be loaded - check ssh-agent"
    fi

    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Add this SSH key to GitHub:${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    cat "${SSH_KEY}.pub"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "1. Go to: https://github.com/settings/keys"
    echo "2. Click 'New SSH key'"
    echo "3. Title: 'MyBB Playground'"
    echo "4. Paste the key above"
    echo ""
    info "Note: For private repos, use 'github.com-mybb' as the host in git remotes"
    echo ""

    read -p "Press Enter once you've added the key to GitHub..."

    # Test connection using the specific host
    if ssh -T git@github.com-mybb 2>&1 | grep -q "successfully authenticated"; then
        success "SSH authentication verified!"
    else
        warn "SSH test didn't confirm success - may still work"
    fi
}

setup_gh_cli() {
    info "Setting up GitHub CLI"

    if ! command_exists gh; then
        info "Installing GitHub CLI..."
        case "$OS_FAMILY" in
            debian)
                curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
                sudo apt update && sudo apt install gh -y
                ;;
            macos)
                brew install gh
                ;;
            *)
                error "Please install GitHub CLI manually: https://cli.github.com/"
                return 1
                ;;
        esac
    fi

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

    if gh auth status &>/dev/null; then
        success "GitHub CLI authenticated!"
    else
        error "GitHub CLI authentication failed"
    fi
}

# ============================================
# Database Setup
# ============================================

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

setup_database() {
    step "Database Setup"

    if [ "$INSTALL_MODE" = "skip" ]; then
        info "Skipping database setup"
        return 0
    fi

    local mariadb_version
    mariadb_version=$(detect_mariadb_version)
    info "Detected MariaDB version: $mariadb_version"

    # Start MariaDB if not running
    if ! pgrep -x "mariadbd" > /dev/null && ! pgrep -x "mysqld" > /dev/null; then
        info "Starting MariaDB..."
        case "$OS_FAMILY" in
            debian)
                sudo service mariadb start
                ;;
            macos)
                brew services start mariadb
                ;;
            *)
                sudo systemctl start mariadb
                ;;
        esac
        sleep 2
    fi

    prompt_validated "Database name" "$DEFAULT_DB_NAME" "MYBB_DB_NAME" "validate_db_name"
    prompt_validated "Database user" "$DEFAULT_DB_USER" "MYBB_DB_USER" "validate_db_name"

    # Generate random password only if not loaded from existing .env
    if [[ -z "$DEFAULT_PASS" ]]; then
        DEFAULT_PASS="mybb_$(openssl rand -hex 6)"
    fi
    prompt_validated "Database password" "$DEFAULT_PASS" "MYBB_DB_PASS" "validate_password"

    # For fresh install, drop existing user and database
    if [ "$INSTALL_MODE" = "fresh" ]; then
        if [ "$PREV_DATABASE" = true ]; then
            warn "Dropping existing database..."
            sudo mariadb -e "DROP DATABASE IF EXISTS $MYBB_DB_NAME;" 2>/dev/null || true
        fi
        # Drop user to recreate with correct password
        sudo mariadb -e "DROP USER IF EXISTS '$MYBB_DB_USER'@'localhost';" 2>/dev/null || true
    fi

    info "Creating database and user..."
    sudo mariadb -e "CREATE DATABASE IF NOT EXISTS $MYBB_DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

    # Escape password for SQL
    local escaped_pass="${MYBB_DB_PASS//\'/\'\'}"

    # Create or update user - use simple IDENTIFIED BY for plaintext password
    if compare_versions "$mariadb_version" "10.4"; then
        info "Using mysql_native_password for MariaDB 10.4+"
        sudo mariadb -e "CREATE USER IF NOT EXISTS '$MYBB_DB_USER'@'localhost' IDENTIFIED BY '$escaped_pass';" 2>/dev/null || \
        sudo mariadb -e "ALTER USER '$MYBB_DB_USER'@'localhost' IDENTIFIED BY '$escaped_pass';"
    else
        sudo mariadb -e "CREATE USER IF NOT EXISTS '$MYBB_DB_USER'@'localhost' IDENTIFIED BY '$escaped_pass';" 2>/dev/null || \
        sudo mariadb -e "ALTER USER '$MYBB_DB_USER'@'localhost' IDENTIFIED BY '$escaped_pass';"
    fi

    sudo mariadb -e "GRANT ALL PRIVILEGES ON $MYBB_DB_NAME.* TO '$MYBB_DB_USER'@'localhost';"
    sudo mariadb -e "FLUSH PRIVILEGES;"

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

    success "Database configured"

    export MYBB_DB_NAME MYBB_DB_USER MYBB_DB_PASS
}

# ============================================
# MyBB Installation
# ============================================

detect_mybb_latest() {
    info "Checking for latest MyBB version..."

    local api_response
    local version
    local download_url

    # Try GitHub API
    if api_response=$(curl -s --max-time 10 https://api.github.com/repos/mybb/mybb/releases/latest 2>/dev/null); then
        # Extract version from tag_name (e.g., "mybb_1839" -> "1839")
        version=$(echo "$api_response" | grep -oP '"tag_name": "mybb_\K[0-9]+' | head -1)
        download_url=$(echo "$api_response" | grep -oP '"browser_download_url": "\K[^"]+mybb_[0-9]+\.zip' | head -1)

        if [[ -n "$version" && -n "$download_url" ]]; then
            MYBB_VERSION="$version"
            MYBB_DOWNLOAD_URL="$download_url"
            success "Latest MyBB version: $MYBB_VERSION"
            return 0
        fi
    fi

    # Fallback to hardcoded version
    warn "Could not fetch latest version - using fallback"
    MYBB_VERSION="$MYBB_VERSION_FALLBACK"
    MYBB_DOWNLOAD_URL="https://github.com/mybb/mybb/releases/download/mybb_${MYBB_VERSION}/mybb_${MYBB_VERSION}.zip"
    info "Using MyBB version: $MYBB_VERSION"
}

install_mybb() {
    step "MyBB Installation"

    if [ "$INSTALL_MODE" = "skip" ]; then
        info "Skipping MyBB installation"
        return 0
    fi

    TESTFORUM_DIR="$SCRIPT_DIR/TestForum"

    if [ "$INSTALL_MODE" = "fresh" ] && [ -d "$TESTFORUM_DIR" ]; then
        warn "Removing existing TestForum..."
        rm -rf "$TESTFORUM_DIR"
    fi

    if [ ! -d "$TESTFORUM_DIR" ] || [ "$INSTALL_MODE" = "fresh" ]; then
        # Detect latest version before download
        detect_mybb_latest

        info "Downloading MyBB ${MYBB_VERSION}..."

        TMP_DIR=$(mktemp -d)
        TEMP_DIRS+=("$TMP_DIR")
        curl -L "$MYBB_DOWNLOAD_URL" -o "$TMP_DIR/mybb.zip"

        info "Extracting..."
        unzip -q "$TMP_DIR/mybb.zip" -d "$TMP_DIR"

        # Move Upload folder to TestForum
        mv "$TMP_DIR/Upload" "$TESTFORUM_DIR"

        # Set permissions
        chmod 666 "$TESTFORUM_DIR/inc/settings.php" 2>/dev/null || true
        chmod 666 "$TESTFORUM_DIR/inc/config.php" 2>/dev/null || true
        chmod 777 "$TESTFORUM_DIR/cache" 2>/dev/null || true
        chmod 777 "$TESTFORUM_DIR/cache/themes" 2>/dev/null || true
        chmod 777 "$TESTFORUM_DIR/uploads" 2>/dev/null || true
        chmod 777 "$TESTFORUM_DIR/uploads/avatars" 2>/dev/null || true

        # Copy custom files from install_files/ (mcp_bridge.php, etc.)
        if [[ -d "$SCRIPT_DIR/install_files" ]]; then
            info "Installing custom files..."
            cp -r "$SCRIPT_DIR/install_files/"* "$TESTFORUM_DIR/" 2>/dev/null || true
            success "Custom files installed (mcp_bridge.php)"
        fi

        success "MyBB extracted to TestForum/"
    else
        info "TestForum already exists, skipping download"
    fi
}

# ============================================
# Default Plugin Deployment
# ============================================

deploy_default_plugins() {
    local forge_config="$SCRIPT_DIR/.mybb-forge.yaml"
    local plugin_base="$SCRIPT_DIR/plugin_manager/plugins/public"

    # Check if forge config exists
    if [[ ! -f "$forge_config" ]]; then
        return 0
    fi

    # Parse default_plugins from YAML (simple grep-based parsing)
    local plugins=()
    local in_plugins=false
    while IFS= read -r line; do
        if [[ "$line" =~ ^default_plugins: ]]; then
            in_plugins=true
            continue
        fi
        if [[ "$in_plugins" == true ]]; then
            # Stop at next section (line starting without whitespace)
            if [[ "$line" =~ ^[a-zA-Z] ]]; then
                break
            fi
            # Extract plugin name from "  - pluginname" format
            if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*([a-zA-Z0-9_-]+) ]]; then
                plugins+=("${BASH_REMATCH[1]}")
            fi
        fi
    done < "$forge_config"

    # No plugins configured
    if [[ ${#plugins[@]} -eq 0 ]]; then
        return 0
    fi

    step "Default Plugins"
    info "Found ${#plugins[@]} default plugin(s) in .mybb-forge.yaml:"
    for plugin in "${plugins[@]}"; do
        echo -e "   ${CYAN}•${NC} $plugin"
    done
    echo ""

    if ! prompt_yn "Deploy these plugins to TestForum?" "y"; then
        info "Skipping plugin deployment"
        return 0
    fi

    local deployed=0
    for plugin in "${plugins[@]}"; do
        local plugin_dir="$plugin_base/$plugin"
        if [[ ! -d "$plugin_dir" ]]; then
            warn "Plugin not found: $plugin (expected at $plugin_dir)"
            continue
        fi

        # Copy inc/plugins/* to TestForum/inc/plugins/
        if [[ -d "$plugin_dir/inc/plugins" ]]; then
            cp -r "$plugin_dir/inc/plugins/"* "$TESTFORUM_DIR/inc/plugins/" 2>/dev/null || true
        fi

        # Copy inc/languages/* if exists
        if [[ -d "$plugin_dir/inc/languages" ]]; then
            cp -r "$plugin_dir/inc/languages/"* "$TESTFORUM_DIR/inc/languages/" 2>/dev/null || true
        fi

        # Copy jscripts/* if exists
        if [[ -d "$plugin_dir/jscripts" ]]; then
            mkdir -p "$TESTFORUM_DIR/jscripts"
            cp -r "$plugin_dir/jscripts/"* "$TESTFORUM_DIR/jscripts/" 2>/dev/null || true
        fi

        # Copy images/* if exists
        if [[ -d "$plugin_dir/images" ]]; then
            cp -r "$plugin_dir/images/"* "$TESTFORUM_DIR/images/" 2>/dev/null || true
        fi

        success "Deployed: $plugin"
        deployed=$((deployed + 1))
    done

    if [[ $deployed -gt 0 ]]; then
        success "Deployed $deployed plugin(s)"
        info "Activate plugins in MyBB Admin CP → Configuration → Plugins"
    fi
}

# ============================================
# Environment Configuration
# ============================================

save_env() {
    step "Saving Configuration"

    prompt_validated "MyBB development server port" "$DEFAULT_PORT" "MYBB_PORT" "validate_port"

    cat > "$SCRIPT_DIR/.env" << EOF
# MyBB Playground Configuration
# Generated by install.sh on $(date)

# Database
MYBB_DB_HOST=localhost
MYBB_DB_NAME=${MYBB_DB_NAME}
MYBB_DB_USER=${MYBB_DB_USER}
MYBB_DB_PASS=${MYBB_DB_PASS}
MYBB_DB_PREFIX=mybb_

# Server
MYBB_PORT=${MYBB_PORT}
MYBB_ROOT=${SCRIPT_DIR}/TestForum
MYBB_URL=http://localhost:${MYBB_PORT}

# MCP Server (for Claude Code)
MCP_LOG_LEVEL=INFO
EOF

    success "Configuration saved to .env"

    # Create .mybb-forge.env template if it doesn't exist
    if [ ! -f "$SCRIPT_DIR/.mybb-forge.env" ]; then
        cat > "$SCRIPT_DIR/.mybb-forge.env" << EOF
# MyBB Forge Private Configuration
# This file is gitignored - safe for secrets

# Private plugin repository URLs (for nested git repos)
# PRIVATE_PLUGINS_REMOTE=git@github.com:YourOrg/your-private-plugins.git
# PRIVATE_THEMES_REMOTE=git@github.com:YourOrg/your-private-themes.git
EOF
        info "Created .mybb-forge.env template"
    fi
}

# ============================================
# Claude Code MCP Setup
# ============================================

setup_mcp() {
    step "Claude Code MCP Integration"

    # Check if Claude Code is installed
    if ! command_exists claude; then
        info "Claude Code not detected - skipping MCP setup"
        info "Install Claude Code later, then run:"
        echo ""
        echo -e "   ${CYAN}cd mybb_mcp && python3 -m venv .venv && source .venv/bin/activate && pip install -e .${NC}"
        echo -e "   ${CYAN}claude mcp add --scope project --transport stdio mybb -- \$(pwd)/.venv/bin/python -m mybb_mcp.server${NC}"
        echo ""
        return 0
    fi

    success "Claude Code detected"

    if ! prompt_yn "Set up MCP server for Claude Code integration?" "y"; then
        info "Skipping MCP setup"
        return 0
    fi

    MCP_DIR="$SCRIPT_DIR/mybb_mcp"

    # Check Python version
    if ! command_exists python3; then
        error "Python 3 not found - required for MCP server"
        return 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [[ $(echo "$PYTHON_VERSION < 3.10" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
        warn "Python 3.10+ recommended (found $PYTHON_VERSION)"
    else
        info "Python $PYTHON_VERSION detected"
    fi

    # Create virtual environment
    info "Creating Python virtual environment..."
    if [[ -d "$MCP_DIR/.venv" ]]; then
        info "Virtual environment already exists"
    else
        python3 -m venv "$MCP_DIR/.venv"
        success "Virtual environment created"
    fi

    # Install package
    info "Installing MCP server package..."
    "$MCP_DIR/.venv/bin/pip" install --quiet --upgrade pip
    "$MCP_DIR/.venv/bin/pip" install --quiet -e "$MCP_DIR"
    success "MCP server package installed"

    # Add to Claude Code (project scope)
    info "Registering MCP server with Claude Code..."

    # Remove existing if present (to update path)
    claude mcp remove mybb 2>/dev/null || true

    # Add with project scope
    if claude mcp add --scope project --transport stdio mybb \
        -- "$MCP_DIR/.venv/bin/python" -m mybb_mcp.server; then
        success "MCP server registered (project scope)"
        info "Configuration saved to .mcp.json"
    else
        error "Failed to register MCP server"
        warn "You can try manually:"
        echo -e "   ${CYAN}claude mcp add --scope project --transport stdio mybb -- $MCP_DIR/.venv/bin/python -m mybb_mcp.server${NC}"
        return 1
    fi

    # Verify
    if claude mcp get mybb &>/dev/null; then
        success "MCP server verified and ready!"
    else
        warn "MCP server added but verification failed - may need Claude Code restart"
    fi
}

# ============================================
# Final Summary
# ============================================

show_summary() {
    echo ""
    echo -e "${GREEN}"
    cat << 'EOF'
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██████╗ ██████╗ ███╗   ██╗███████╗██╗                       ║
    ║   ██╔══██╗██╔═══██╗████╗  ██║██╔════╝██║                      ║
    ║   ██║  ██║██║   ██║██╔██╗ ██║█████╗  ██║                      ║
    ║   ██║  ██║██║   ██║██║╚██╗██║██╔══╝  ╚═╝                      ║
    ║   ██████╔╝╚██████╔╝██║ ╚████║███████╗██╗                      ║
    ║   ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝                      ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    echo -e "${CYAN}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC} ${BOLD}Database Credentials${NC}                                        ${CYAN}│${NC}"
    echo -e "${CYAN}├─────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│${NC}   Host:     ${GREEN}localhost${NC}                                       ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}   Database: ${GREEN}${MYBB_DB_NAME}${NC}$(printf '%*s' $((38 - ${#MYBB_DB_NAME})) '')${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}   User:     ${GREEN}${MYBB_DB_USER}${NC}$(printf '%*s' $((38 - ${#MYBB_DB_USER})) '')${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}   Password: ${GREEN}${MYBB_DB_PASS}${NC}$(printf '%*s' $((38 - ${#MYBB_DB_PASS})) '')${CYAN}│${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    echo -e "${BOLD}📋 Next Steps:${NC}"
    echo ""
    echo -e "   ${MAGENTA}1${NC}  Start the server     ${DIM}→${NC}  ${CYAN}./start_mybb.sh${NC}"
    echo -e "   ${MAGENTA}2${NC}  Open browser         ${DIM}→${NC}  ${CYAN}http://localhost:${MYBB_PORT}/install/${NC}"
    echo -e "   ${MAGENTA}3${NC}  Complete web setup   ${DIM}→${NC}  Use credentials above"
    echo ""

    if [ "$IS_WSL" = true ]; then
        echo -e "   ${YELLOW}💡 WSL Tip:${NC} Access from Windows at http://localhost:${MYBB_PORT}/"
        echo ""
    fi

    echo -e "${BOLD}🤖 Claude Code Integration:${NC}"
    echo ""
    echo -e "   The MCP server auto-connects when you open this project."
    echo -e "   ${DIM}Try:${NC} \"List MyBB template sets\" ${DIM}or${NC} \"Create a test plugin\""
    echo ""

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${DIM}Configuration saved to .env │ Log: ${LOG_FILE##*/}${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# ============================================
# Main
# ============================================

main() {
    # Parse command line arguments first
    parse_args "$@"

    trap cleanup EXIT
    trap 'error_handler $LINENO $?' ERR

    banner

    step "Environment Detection"
    detect_os

    # Initialize logging after detect_os (so we have OS info)
    init_logging "$@"

    info "OS: $OS ($OS_FAMILY)"
    info "Package Manager: $PKG_MANAGER"
    [ "$IS_WSL" = true ] && info "Running in WSL"

    # Load existing env if present (uses defaults from .env)
    load_existing_env "$ENV_FILE"

    detect_previous_install
    handle_previous_install

    if prompt_yn "Install/update system dependencies (PHP, MariaDB, etc.)?" "y"; then
        install_dependencies
    fi

    setup_database
    install_mybb
    deploy_default_plugins
    setup_git_auth
    save_env
    setup_mcp
    show_summary

    # Log completion to file
    [[ -n "${LOG_FILE:-}" ]] && echo "=== Installation completed: $(date) ===" >> "$LOG_FILE"
}

# Run main
main "$@"
