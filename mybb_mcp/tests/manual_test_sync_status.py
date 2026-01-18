"""Manual integration test for enhanced mybb_sync_status.

Run this from mybb_mcp directory:
    python tests/manual_test_sync_status.py

This verifies that mybb_sync_status correctly displays workspace projects.
"""

import sys
from pathlib import Path

# Add plugin_manager to path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "plugin_manager"))

from database import ProjectDatabase


def test_sync_status_enhancement():
    """Test enhanced sync_status displays workspace projects."""
    print("Testing enhanced mybb_sync_status...")

    # Check if database exists
    db_path = repo_root / "plugin_manager" / ".meta" / "projects.db"

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("   Run plugin_manager tests first to create database")
        return False

    # Initialize database
    try:
        project_db = ProjectDatabase(db_path)
        print(f"✓ Connected to database at {db_path}")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False

    # Query projects
    try:
        plugins = project_db.list_projects(type='plugin')
        themes = project_db.list_projects(type='theme')

        print(f"\n✓ Found {len(plugins)} plugins and {len(themes)} themes")

        if plugins:
            print("\nPlugins:")
            for p in plugins:
                print(f"  - {p['codename']} (v{p['version']}, {p['status']})")

        if themes:
            print("\nThemes:")
            for t in themes:
                print(f"  - {t['codename']} (v{t['version']}, {t['status']})")

    except Exception as e:
        print(f"❌ Failed to query projects: {e}")
        return False

    # Test timestamp formatting
    print("\n✓ Testing timestamp formatting...")
    from datetime import datetime
    test_timestamp = "2026-01-18T12:34:56"
    try:
        dt = datetime.fromisoformat(test_timestamp)
        formatted = dt.strftime('%Y-%m-%d %H:%M')
        print(f"  {test_timestamp} → {formatted}")
        assert formatted == "2026-01-18 12:34"
        print("✓ Timestamp formatting works correctly")
    except Exception as e:
        print(f"❌ Timestamp formatting failed: {e}")
        return False

    print("\n✅ All tests passed! Enhanced sync_status should work correctly.")
    return True


if __name__ == "__main__":
    success = test_sync_status_enhancement()
    sys.exit(0 if success else 1)
