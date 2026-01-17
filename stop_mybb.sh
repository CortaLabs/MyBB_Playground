#!/bin/bash
# ============================================
# Stop MyBB Development Services
# ============================================

echo "Stopping services..."

# Kill PHP development server if running
pkill -f "php -S localhost" 2>/dev/null && echo "✓ PHP server stopped" || echo "PHP server was not running"

# Optionally stop MariaDB (comment out if you want it always running)
# sudo service mariadb stop && echo "✓ MariaDB stopped"

echo "Done."
