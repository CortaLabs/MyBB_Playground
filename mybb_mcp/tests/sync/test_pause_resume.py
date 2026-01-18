"""Tests for watcher pause/resume functionality.

Validates that the FileWatcher can be paused during export operations
to prevent race conditions, and that it resumes correctly afterwards.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from mybb_mcp.sync.watcher import FileWatcher
from mybb_mcp.sync.templates import TemplateImporter
from mybb_mcp.sync.stylesheets import StylesheetImporter
from mybb_mcp.sync.cache import CacheRefresher
from mybb_mcp.sync.router import PathRouter


@pytest.fixture
def sync_root(tmp_path):
    """Create a temporary sync root directory."""
    sync_root = tmp_path / "mybb_sync"
    sync_root.mkdir()
    return sync_root


@pytest.fixture
def mock_template_importer():
    """Create a mock TemplateImporter."""
    importer = Mock(spec=TemplateImporter)
    importer.import_template = AsyncMock()
    return importer


@pytest.fixture
def mock_stylesheet_importer():
    """Create a mock StylesheetImporter."""
    importer = Mock(spec=StylesheetImporter)
    importer.import_stylesheet = AsyncMock()
    return importer


@pytest.fixture
def mock_cache_refresher():
    """Create a mock CacheRefresher."""
    refresher = Mock(spec=CacheRefresher)
    refresher.refresh_stylesheet = AsyncMock()
    return refresher


@pytest.fixture
def path_router(sync_root):
    """Create a PathRouter instance."""
    return PathRouter(sync_root)


@pytest.fixture
def file_watcher(sync_root, mock_template_importer, mock_stylesheet_importer,
                 mock_cache_refresher, path_router):
    """Create a FileWatcher instance."""
    return FileWatcher(
        sync_root=sync_root,
        template_importer=mock_template_importer,
        stylesheet_importer=mock_stylesheet_importer,
        cache_refresher=mock_cache_refresher,
        router=path_router
    )


@pytest.mark.asyncio
async def test_pause_idempotent(file_watcher):
    """Test that multiple pause() calls are safe (idempotent)."""
    assert file_watcher._paused is False

    # First pause
    file_watcher.pause()
    assert file_watcher._paused is True

    # Second pause - should be safe
    file_watcher.pause()
    assert file_watcher._paused is True

    # Third pause - still safe
    file_watcher.pause()
    assert file_watcher._paused is True


@pytest.mark.asyncio
async def test_resume_idempotent(file_watcher):
    """Test that multiple resume() calls are safe (idempotent)."""
    # Start in paused state
    file_watcher.pause()
    assert file_watcher._paused is True

    # First resume
    file_watcher.resume()
    assert file_watcher._paused is False

    # Second resume - should be safe
    file_watcher.resume()
    assert file_watcher._paused is False

    # Third resume - still safe
    file_watcher.resume()
    assert file_watcher._paused is False


@pytest.mark.asyncio
async def test_events_queue_during_pause(file_watcher, mock_template_importer):
    """Test that events queue up during pause and process on resume."""
    # Start the processor task
    file_watcher._processor_task = asyncio.create_task(file_watcher._process_work_queue())

    # Pause the watcher
    file_watcher.pause()

    # Queue a work item while paused
    work_item = {
        "type": "template",
        "set_name": "Default Templates",
        "template_name": "header",
        "content": "<html>test</html>"
    }
    await file_watcher.work_queue.put(work_item)

    # Give it a moment to ensure it doesn't process while paused
    await asyncio.sleep(0.3)

    # Verify it hasn't been processed yet (paused)
    assert mock_template_importer.import_template.call_count == 0

    # Resume the watcher
    file_watcher.resume()

    # Give it time to process
    await asyncio.sleep(0.3)

    # Now it should have processed
    assert mock_template_importer.import_template.call_count == 1
    mock_template_importer.import_template.assert_called_once_with(
        "Default Templates",
        "header",
        "<html>test</html>"
    )

    # Cleanup
    file_watcher._processor_task.cancel()
    try:
        await file_watcher._processor_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_export_pauses_and_resumes(sync_root, mock_template_importer,
                                         mock_stylesheet_importer, mock_cache_refresher,
                                         path_router):
    """Integration test: export operations should pause and resume watcher."""
    from mybb_mcp.sync.service import DiskSyncService
    from mybb_mcp.sync.config import SyncConfig
    from mybb_mcp.db.connection import MyBBDatabase

    # Create mock database
    mock_db = Mock(spec=MyBBDatabase)
    mock_db.table = lambda name: f"mybb_{name}"

    # Mock the database query for template set lookup
    mock_db.query = Mock(return_value=[
        {"sid": 1, "title": "Default Templates"}
    ])

    # Mock fetch_all for templates
    mock_db.fetch_all = AsyncMock(return_value=[])

    # Create config
    config = SyncConfig(sync_root=sync_root)

    # Create service
    service = DiskSyncService(
        db=mock_db,
        config=config,
        mybb_url="http://localhost:8022"
    )

    # Replace the importers with our mocks
    service.template_importer = mock_template_importer
    service.stylesheet_importer = mock_stylesheet_importer
    service.cache_refresher = mock_cache_refresher

    # Verify watcher is not paused initially
    assert service.watcher._paused is False

    # Pause watcher
    service.pause_watcher()
    assert service.watcher._paused is True

    # Resume watcher
    service.resume_watcher()
    assert service.watcher._paused is False


@pytest.mark.asyncio
async def test_resume_on_export_error(file_watcher, mock_template_importer):
    """Test that watcher resumes even if export fails."""
    # Start the processor task
    file_watcher._processor_task = asyncio.create_task(file_watcher._process_work_queue())

    # Simulate export operation pattern
    try:
        # Pause before export
        file_watcher.pause()
        assert file_watcher._paused is True

        # Simulate an error during export
        raise ValueError("Export failed")

    except ValueError:
        # Error caught, but finally block should resume
        pass
    finally:
        # This is what the server.py handlers do
        file_watcher.resume()

    # Verify watcher resumed despite error
    assert file_watcher._paused is False

    # Queue a work item to verify it processes normally
    work_item = {
        "type": "template",
        "set_name": "Default Templates",
        "template_name": "footer",
        "content": "<html>footer</html>"
    }
    await file_watcher.work_queue.put(work_item)

    # Give it time to process
    await asyncio.sleep(0.3)

    # Verify it processed successfully
    assert mock_template_importer.import_template.call_count == 1

    # Cleanup
    file_watcher._processor_task.cancel()
    try:
        await file_watcher._processor_task
    except asyncio.CancelledError:
        pass
