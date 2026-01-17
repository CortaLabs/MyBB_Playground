#!/bin/bash
# ============================================
# Start MyBB Development Server
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MYBB_DIR="${SCRIPT_DIR}/TestForum"
PORT="${MYBB_PORT:-8022}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================="
echo "MyBB Development Server"
echo -e "==========================================${NC}"

# Check if MariaDB is running
if ! pgrep -x "mariadbd" > /dev/null && ! pgrep -x "mysqld" > /dev/null; then
    echo -e "${YELLOW}Starting MariaDB...${NC}"
    sudo service mariadb start
    sleep 2
fi

# Check if MariaDB started successfully
if pgrep -x "mariadbd" > /dev/null || pgrep -x "mysqld" > /dev/null; then
    echo -e "${GREEN}✓ MariaDB is running${NC}"
else
    echo -e "${RED}✗ Failed to start MariaDB${NC}"
    exit 1
fi

# Check if PHP is installed
if ! command -v php &> /dev/null; then
    echo -e "${RED}✗ PHP is not installed. Run ./setup_dev_env.sh first${NC}"
    exit 1
fi

echo -e "${GREEN}✓ PHP $(php -v | head -1 | cut -d' ' -f2)${NC}"

# Check if MyBB directory exists
if [ ! -d "$MYBB_DIR" ]; then
    echo -e "${RED}✗ TestForum directory not found${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Starting PHP development server on port ${PORT}...${NC}"
echo -e "${YELLOW}Forum URL: http://localhost:${PORT}${NC}"
echo -e "${YELLOW}Install:   http://localhost:${PORT}/install/${NC}"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start PHP built-in server
cd "$MYBB_DIR"
php -S localhost:${PORT} -t .
