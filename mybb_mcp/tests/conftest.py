"""Pytest configuration and shared fixtures for MyBB MCP tests."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_mybb_root(tmp_path):
    """Create a temporary MyBB root directory structure."""
    mybb_root = tmp_path / "mybb"
    mybb_root.mkdir()

    # Create standard MyBB directories
    (mybb_root / "inc" / "plugins").mkdir(parents=True)
    (mybb_root / "cache").mkdir()
    (mybb_root / "uploads").mkdir()

    return mybb_root


@pytest.fixture
def sample_env_config(tmp_path):
    """Create sample .env configuration for testing."""
    env_file = tmp_path / ".env"
    env_content = """
MYBB_DB_HOST=localhost
MYBB_DB_PORT=3306
MYBB_DB_NAME=test_mybb
MYBB_DB_USER=test_user
MYBB_DB_PASS=test_password
MYBB_DB_PREFIX=mybb_
MYBB_ROOT=/tmp/mybb
MYBB_URL=http://localhost:8022
MYBB_PORT=8022
"""
    env_file.write_text(env_content.strip())
    return env_file
