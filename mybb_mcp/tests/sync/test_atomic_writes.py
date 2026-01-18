"""Tests for atomic write operations in disk-sync.

Validates that template and stylesheet exports use atomic write patterns
(write to .tmp, then rename) and that the watcher correctly ignores .tmp files.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from mybb_mcp.sync.templates import TemplateExporter
from mybb_mcp.sync.stylesheets import StylesheetExporter
from mybb_mcp.sync.watcher import SyncEventHandler
from mybb_mcp.sync.router import PathRouter
from mybb_mcp.sync.groups import TemplateGroupManager
from mybb_mcp.db.connection import MyBBDatabase


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = Mock(spec=MyBBDatabase)
    db.table = lambda name: f"mybb_{name}"
    return db


@pytest.fixture
def sync_root(tmp_path):
    """Create a temporary sync root directory."""
    sync_root = tmp_path / "mybb_sync"
    sync_root.mkdir()
    return sync_root


@pytest.fixture
def path_router(sync_root):
    """Create a PathRouter instance."""
    return PathRouter(sync_root)


@pytest.fixture
def group_manager(mock_db):
    """Create a TemplateGroupManager instance."""
    return TemplateGroupManager(mock_db)


@pytest.fixture
def template_exporter(mock_db, path_router, group_manager):
    """Create a TemplateExporter instance."""
    return TemplateExporter(mock_db, path_router, group_manager)


@pytest.fixture
def stylesheet_exporter(mock_db, path_router):
    """Create a StylesheetExporter instance."""
    return StylesheetExporter(mock_db, path_router)


@pytest.fixture
def sync_event_handler(sync_root):
    """Create a SyncEventHandler instance."""
    template_importer = Mock()
    stylesheet_importer = Mock()
    cache_refresher = Mock()
    router = PathRouter(sync_root)
    work_queue = asyncio.Queue()

    return SyncEventHandler(
        template_importer,
        stylesheet_importer,
        cache_refresher,
        router,
        work_queue
    )


@pytest.mark.asyncio
async def test_atomic_write_creates_temp_file(template_exporter, mock_db, group_manager):
    """Test that atomic write creates .tmp file first."""
    # Setup mock database responses
    mock_db.get_template_set_by_name.return_value = {"sid": 1, "title": "Default Templates"}

    # Mock _fetch_templates to return a single template
    template_exporter._fetch_templates = Mock(return_value=[
        {"tid": 1, "sid": 1, "title": "test_template", "template": "Test content"}
    ])

    # Mock group manager to return a group name
    group_manager.get_group_name = Mock(return_value="Test Group")

    # Track file creation order
    created_files = []
    original_write_text = Path.write_text
    original_rename = Path.rename

    def track_write_text(self, content, **kwargs):
        created_files.append(("write", str(self)))
        return original_write_text(self, content, **kwargs)

    def track_rename(self, target):
        created_files.append(("rename", str(self), str(target)))
        return original_rename(self, target)

    with patch.object(Path, 'write_text', track_write_text), \
         patch.object(Path, 'rename', track_rename):
        # Export the template
        await template_exporter.export_template_set("Default Templates")

    # Verify .tmp file was written first
    assert len(created_files) >= 2
    assert created_files[0][0] == "write"
    assert created_files[0][1].endswith(".tmp")

    # Verify rename happened after write
    assert created_files[1][0] == "rename"
    assert created_files[1][1].endswith(".tmp")
    assert created_files[1][2].endswith(".html")


@pytest.mark.asyncio
async def test_atomic_rename_completes(template_exporter, mock_db, group_manager, sync_root):
    """Test that final file exists after rename completes."""
    # Setup mock database responses
    mock_db.get_template_set_by_name.return_value = {"sid": 1, "title": "Default Templates"}

    # Mock _fetch_templates to return a single template
    template_exporter._fetch_templates = Mock(return_value=[
        {"tid": 1, "sid": 1, "title": "test_template", "template": "Test content"}
    ])

    # Mock group manager to return a group name
    group_manager.get_group_name = Mock(return_value="Test Group")

    # Export the template
    await template_exporter.export_template_set("Default Templates")

    # Verify final file exists
    expected_path = sync_root / "template_sets" / "Default Templates" / "Test Group" / "test_template.html"
    assert expected_path.exists()
    assert expected_path.read_text(encoding='utf-8') == "Test content"

    # Verify .tmp file does not exist
    temp_path = expected_path.with_suffix('.tmp')
    assert not temp_path.exists()


@pytest.mark.asyncio
async def test_temp_file_cleaned_on_error(template_exporter, mock_db, group_manager, sync_root):
    """Test that .tmp file is removed on failure."""
    # Setup mock database responses
    mock_db.get_template_set_by_name.return_value = {"sid": 1, "title": "Default Templates"}

    # Mock _fetch_templates to return a single template
    template_exporter._fetch_templates = Mock(return_value=[
        {"tid": 1, "sid": 1, "title": "test_template", "template": "Test content"}
    ])

    # Mock group manager to return a group name
    group_manager.get_group_name = Mock(return_value="Test Group")

    # Track temp file path
    temp_file_path = None
    original_rename = Path.rename

    def failing_rename(self, target):
        nonlocal temp_file_path
        temp_file_path = self
        raise OSError("Simulated rename failure")

    with patch.object(Path, 'rename', failing_rename):
        # Export should fail
        with pytest.raises(OSError, match="Simulated rename failure"):
            await template_exporter.export_template_set("Default Templates")

    # Verify temp file was cleaned up
    assert temp_file_path is not None
    assert not temp_file_path.exists()


def test_watcher_ignores_tmp_files(sync_event_handler, sync_root):
    """Test that watcher skips .tmp files."""
    # Create a .tmp file in the templates directory
    template_dir = sync_root / "template_sets" / "Default Templates" / "Test Group"
    template_dir.mkdir(parents=True, exist_ok=True)

    tmp_file = template_dir / "test_template.tmp"
    tmp_file.write_text("Temp content", encoding='utf-8')

    # Trigger file change event
    sync_event_handler._handle_file_change(tmp_file)

    # Verify no work was queued (queue should be empty)
    assert sync_event_handler.work_queue.empty()


@pytest.mark.asyncio
async def test_export_uses_atomic_pattern(stylesheet_exporter, mock_db, sync_root):
    """Integration test: verify stylesheet export uses atomic pattern."""
    # Setup mock database responses
    mock_db.get_theme_by_name.return_value = {"tid": 1, "name": "Default"}

    # Mock _fetch_stylesheets to return a single stylesheet
    stylesheet_exporter._fetch_stylesheets = Mock(return_value=[
        {"name": "global.css", "stylesheet": "body { margin: 0; }"}
    ])

    # Track file operations
    operations = []
    original_write_text = Path.write_text
    original_rename = Path.rename

    def track_write(self, content, **kwargs):
        operations.append(("write", str(self), len(content)))
        return original_write_text(self, content, **kwargs)

    def track_rename(self, target):
        operations.append(("rename", str(self), str(target)))
        return original_rename(self, target)

    with patch.object(Path, 'write_text', track_write), \
         patch.object(Path, 'rename', track_rename):
        # Export stylesheets
        result = await stylesheet_exporter.export_theme_stylesheets("Default")

    # Verify atomic pattern was used
    assert len(operations) == 2
    assert operations[0][0] == "write"
    assert operations[0][1].endswith(".tmp")
    assert operations[0][2] > 0  # Content was written

    assert operations[1][0] == "rename"
    assert operations[1][1].endswith(".tmp")
    assert operations[1][2].endswith(".css")

    # Verify export succeeded
    assert result["files_exported"] == 1

    # Verify final file exists
    final_path = sync_root / "styles" / "Default" / "global.css"
    assert final_path.exists()
    assert final_path.read_text(encoding='utf-8') == "body { margin: 0; }"
