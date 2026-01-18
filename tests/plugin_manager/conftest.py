"""Pytest configuration for plugin_manager tests.

Sets up path to allow imports from both plugin_manager and mybb_mcp packages.
"""

import sys
from pathlib import Path

# Get the repo root
REPO_ROOT = Path(__file__).parent.parent.parent

# Add repo root for plugin_manager imports
sys.path.insert(0, str(REPO_ROOT))

# Add mybb_mcp directory for mybb_mcp package imports
# This allows "from mybb_mcp.sync.router import PathRouter" to work
sys.path.insert(0, str(REPO_ROOT / "mybb_mcp"))
