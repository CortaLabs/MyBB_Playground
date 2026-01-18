"""Tests for enhanced mybb_sync_status with workspace project visibility."""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path


@pytest.fixture
def mock_sync_service():
    """Mock DiskSyncService with basic status."""
    service = Mock()
    service.get_status.return_value = {
        'watcher_running': True,
        'sync_root': '/home/user/MyBB_Playground/mybb_sync',
        'mybb_url': 'http://localhost:8022',
        'workspace_root': '/home/user/MyBB_Playground/plugin_manager'
    }
    return service


@pytest.fixture
def mock_project_db():
    """Mock ProjectDatabase with sample projects."""
    db = Mock()

    # Sample plugins
    db.list_projects.side_effect = lambda type: {
        'plugin': [
            {
                'codename': 'hello_banner',
                'status': 'installed',
                'version': '1.0.0',
                'last_synced_at': '2026-01-18T06:00:00'
            },
            {
                'codename': 'test_plugin',
                'status': 'development',
                'version': '0.1.0',
                'last_synced_at': 'never'
            }
        ],
        'theme': [
            {
                'codename': 'dark_mode',
                'status': 'testing',
                'version': '2.0.0',
                'last_synced_at': '2026-01-18T05:30:00'
            }
        ]
    }.get(type, [])

    return db


@pytest.mark.asyncio
async def test_sync_status_base_output(mock_sync_service):
    """Test basic sync status without workspace projects."""
    from mybb_mcp.server import handle_tool

    # Mock database path to not exist
    with patch('pathlib.Path.exists', return_value=False):
        result = await handle_tool(
            "mybb_sync_status",
            {},
            Mock(),
            mock_sync_service
        )

    # Verify base output
    assert "# Sync Status" in result
    assert "**Watcher**: Running ✓" in result
    assert "**Sync Root**: /home/user/MyBB_Playground/mybb_sync" in result
    assert "**MyBB URL**: http://localhost:8022" in result
    assert "**Workspace Root**: /home/user/MyBB_Playground/plugin_manager" in result


@pytest.mark.asyncio
async def test_sync_status_with_workspace_projects(mock_sync_service, mock_project_db):
    """Test sync status displays workspace projects correctly."""
    from mybb_mcp.server import handle_tool

    with patch('pathlib.Path.exists', return_value=True), \
         patch('database.ProjectDatabase', return_value=mock_project_db):

        result = await handle_tool(
            "mybb_sync_status",
            {},
            Mock(),
            mock_sync_service
        )

    # Verify base status
    assert "# Sync Status" in result
    assert "**Watcher**: Running ✓" in result

    # Verify workspace projects section
    assert "## Workspace Projects" in result

    # Verify plugins table
    assert "### Plugins" in result
    assert "| Codename | Status | Version | Last Synced |" in result
    assert "| hello_banner | installed | 1.0.0 | 2026-01-18 06:00 |" in result
    assert "| test_plugin | development | 0.1.0 | never |" in result

    # Verify themes table
    assert "### Themes" in result
    assert "| dark_mode | testing | 2.0.0 | 2026-01-18 05:30 |" in result


@pytest.mark.asyncio
async def test_sync_status_watcher_stopped(mock_sync_service):
    """Test sync status when watcher is stopped."""
    mock_sync_service.get_status.return_value['watcher_running'] = False

    from mybb_mcp.server import handle_tool

    with patch('pathlib.Path.exists', return_value=False):
        result = await handle_tool(
            "mybb_sync_status",
            {},
            Mock(),
            mock_sync_service
        )

    assert "**Watcher**: Stopped" in result
    assert "Running ✓" not in result


@pytest.mark.asyncio
async def test_sync_status_no_workspace_projects(mock_sync_service):
    """Test sync status when database exists but no projects."""
    from mybb_mcp.server import handle_tool

    empty_db = Mock()
    empty_db.list_projects.return_value = []

    with patch('pathlib.Path.exists', return_value=True), \
         patch('database.ProjectDatabase', return_value=empty_db):

        result = await handle_tool(
            "mybb_sync_status",
            {},
            Mock(),
            mock_sync_service
        )

    # Should show base status but no workspace projects section
    assert "# Sync Status" in result
    assert "**Watcher**: Running ✓" in result
    assert "## Workspace Projects" not in result


@pytest.mark.asyncio
async def test_sync_status_database_error_handling(mock_sync_service):
    """Test sync status gracefully handles database errors."""
    from mybb_mcp.server import handle_tool

    with patch('pathlib.Path.exists', return_value=True), \
         patch('database.ProjectDatabase', side_effect=Exception("DB error")):

        result = await handle_tool(
            "mybb_sync_status",
            {},
            Mock(),
            mock_sync_service
        )

    # Should show base status plus error note
    assert "# Sync Status" in result
    assert "**Watcher**: Running ✓" in result
    assert "Could not query workspace projects" in result or "DB error" in result


@pytest.mark.asyncio
async def test_sync_status_timestamp_formatting():
    """Test that timestamps are formatted correctly."""
    from mybb_mcp.server import handle_tool

    mock_service = Mock()
    mock_service.get_status.return_value = {
        'watcher_running': True,
        'sync_root': '/test',
        'mybb_url': 'http://localhost',
        'workspace_root': '/workspace'
    }

    mock_db = Mock()
    mock_db.list_projects.side_effect = lambda type: [
        {
            'codename': 'test',
            'status': 'development',
            'version': '1.0.0',
            'last_synced_at': '2026-01-18T12:34:56'
        }
    ] if type == 'plugin' else []

    with patch('pathlib.Path.exists', return_value=True), \
         patch('database.ProjectDatabase', return_value=mock_db):

        result = await handle_tool(
            "mybb_sync_status",
            {},
            Mock(),
            mock_service
        )

    # Verify timestamp is formatted nicely
    assert "2026-01-18 12:34" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
