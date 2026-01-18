"""Tests for file size validation in disk-sync watcher.

Validates that the watcher correctly rejects empty files and handles
edge cases like file deletion during processing.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import sys

from mybb_mcp.sync.watcher import SyncEventHandler
from mybb_mcp.sync.templates import TemplateImporter
from mybb_mcp.sync.stylesheets import StylesheetImporter
from mybb_mcp.sync.cache import CacheRefresher
from mybb_mcp.sync.router import PathRouter


@pytest.fixture
def mock_sync_components(tmp_path):
    """Create mock sync components for testing."""
    # Create sync root with proper structure
    sync_root = tmp_path / "mybb_sync"
    # Templates need: template_sets/{set_name}/{group_name}/{template}.html
    template_dir = sync_root / "template_sets" / "Default Templates" / "Test Group"
    stylesheet_dir = sync_root / "styles" / "Default"
    template_dir.mkdir(parents=True)
    stylesheet_dir.mkdir(parents=True)

    # Create mock components
    template_importer = Mock(spec=TemplateImporter)
    stylesheet_importer = Mock(spec=StylesheetImporter)
    cache_refresher = Mock(spec=CacheRefresher)
    router = PathRouter(sync_root)
    work_queue = asyncio.Queue()

    # Create event handler
    handler = SyncEventHandler(
        template_importer,
        stylesheet_importer,
        cache_refresher,
        router,
        work_queue
    )

    return {
        "handler": handler,
        "sync_root": sync_root,
        "template_dir": template_dir,
        "stylesheet_dir": stylesheet_dir,
        "work_queue": work_queue,
        "template_importer": template_importer,
        "stylesheet_importer": stylesheet_importer
    }


def test_empty_template_file_rejected(mock_sync_components):
    """Test that empty template files (0 bytes) are rejected before database write."""
    # Create empty template file
    template_path = mock_sync_components["template_dir"] / "header.html"
    template_path.write_text("", encoding='utf-8')

    # Capture print output
    captured_output = StringIO()
    with patch('sys.stdout', captured_output):
        # Process the empty file
        mock_sync_components["handler"]._handle_template_change(template_path)

    # Verify warning was logged
    output = captured_output.getvalue()
    assert "[disk-sync] WARNING: Skipping empty file:" in output
    assert str(template_path) in output

    # Verify work was NOT queued (queue should be empty)
    assert mock_sync_components["work_queue"].empty()


def test_empty_stylesheet_file_rejected(mock_sync_components):
    """Test that empty stylesheet files (0 bytes) are rejected before database write."""
    # Create empty stylesheet file
    stylesheet_path = mock_sync_components["stylesheet_dir"] / "global.css"
    stylesheet_path.write_text("", encoding='utf-8')

    # Capture print output
    captured_output = StringIO()
    with patch('sys.stdout', captured_output):
        # Process the empty file
        mock_sync_components["handler"]._handle_stylesheet_change(stylesheet_path)

    # Verify warning was logged
    output = captured_output.getvalue()
    assert "[disk-sync] WARNING: Skipping empty file:" in output
    assert str(stylesheet_path) in output

    # Verify work was NOT queued (queue should be empty)
    assert mock_sync_components["work_queue"].empty()


def test_tiny_template_file_accepted(mock_sync_components):
    """Test that tiny but non-empty files (1 byte) are processed normally."""
    # Create 1-byte template file
    template_path = mock_sync_components["template_dir"] / "header.html"
    template_path.write_text("x", encoding='utf-8')

    # Process the file
    mock_sync_components["handler"]._handle_template_change(template_path)

    # Verify work WAS queued (1 item in queue)
    assert not mock_sync_components["work_queue"].empty()
    work_item = mock_sync_components["work_queue"].get_nowait()
    assert work_item["type"] == "template"
    assert work_item["content"] == "x"


def test_tiny_stylesheet_file_accepted(mock_sync_components):
    """Test that tiny but non-empty stylesheet files (1 byte) are processed normally."""
    # Create 1-byte stylesheet file
    stylesheet_path = mock_sync_components["stylesheet_dir"] / "global.css"
    stylesheet_path.write_text("x", encoding='utf-8')

    # Process the file
    mock_sync_components["handler"]._handle_stylesheet_change(stylesheet_path)

    # Verify work WAS queued (1 item in queue)
    assert not mock_sync_components["work_queue"].empty()
    work_item = mock_sync_components["work_queue"].get_nowait()
    assert work_item["type"] == "stylesheet"
    assert work_item["content"] == "x"


def test_file_deleted_during_processing_template(mock_sync_components):
    """Test graceful handling when template file is deleted between event and validation."""
    # Create a file path that doesn't exist (simulates deletion during processing)
    template_path = mock_sync_components["template_dir"] / "deleted.html"

    # Process the non-existent file - should not raise exception
    try:
        mock_sync_components["handler"]._handle_template_change(template_path)
        # If we get here, the handler gracefully handled the missing file
        success = True
    except FileNotFoundError:
        # Handler should catch this, not propagate it
        success = False

    assert success, "Handler should gracefully handle deleted files without raising FileNotFoundError"

    # Verify work was NOT queued (file didn't exist)
    assert mock_sync_components["work_queue"].empty()


def test_file_deleted_during_processing_stylesheet(mock_sync_components):
    """Test graceful handling when stylesheet file is deleted between event and validation."""
    # Create a file path that doesn't exist (simulates deletion during processing)
    stylesheet_path = mock_sync_components["stylesheet_dir"] / "deleted.css"

    # Process the non-existent file - should not raise exception
    try:
        mock_sync_components["handler"]._handle_stylesheet_change(stylesheet_path)
        # If we get here, the handler gracefully handled the missing file
        success = True
    except FileNotFoundError:
        # Handler should catch this, not propagate it
        success = False

    assert success, "Handler should gracefully handle deleted files without raising FileNotFoundError"

    # Verify work was NOT queued (file didn't exist)
    assert mock_sync_components["work_queue"].empty()


def test_validation_logs_warning_with_path(mock_sync_components):
    """Test that validation warning includes the file path for debugging."""
    # Create empty template file
    template_path = mock_sync_components["template_dir"] / "test_template.html"
    template_path.write_text("", encoding='utf-8')

    # Capture print output
    captured_output = StringIO()
    with patch('sys.stdout', captured_output):
        mock_sync_components["handler"]._handle_template_change(template_path)

    # Verify warning format
    output = captured_output.getvalue()
    assert "[disk-sync] WARNING: Skipping empty file:" in output
    assert "test_template.html" in output
    assert str(template_path) in output


def test_normal_template_file_processed(mock_sync_components):
    """Test that normal template files with content are processed correctly."""
    # Create template with actual content
    template_path = mock_sync_components["template_dir"] / "header.html"
    content = "<html><body>Test Content</body></html>"
    template_path.write_text(content, encoding='utf-8')

    # Process the file
    mock_sync_components["handler"]._handle_template_change(template_path)

    # Verify work was queued
    assert not mock_sync_components["work_queue"].empty()
    work_item = mock_sync_components["work_queue"].get_nowait()
    assert work_item["type"] == "template"
    assert work_item["content"] == content
    assert work_item["template_name"] == "header"
    assert work_item["set_name"] == "Default Templates"


def test_normal_stylesheet_file_processed(mock_sync_components):
    """Test that normal stylesheet files with content are processed correctly."""
    # Create stylesheet with actual content
    stylesheet_path = mock_sync_components["stylesheet_dir"] / "global.css"
    content = "body { color: red; }"
    stylesheet_path.write_text(content, encoding='utf-8')

    # Process the file
    mock_sync_components["handler"]._handle_stylesheet_change(stylesheet_path)

    # Verify work was queued
    assert not mock_sync_components["work_queue"].empty()
    work_item = mock_sync_components["work_queue"].get_nowait()
    assert work_item["type"] == "stylesheet"
    assert work_item["content"] == content
    assert work_item["stylesheet_name"] == "global.css"
    assert work_item["theme_name"] == "Default"


# ============================================================================
# Defense-in-Depth: Importer Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_template_importer_rejects_empty_content():
    """Test that TemplateImporter raises ValueError for empty content."""
    from mybb_mcp.sync.templates import TemplateImporter

    # Create a mock database
    mock_db = Mock()
    importer = TemplateImporter(mock_db)

    # Test empty string
    with pytest.raises(ValueError, match="Cannot import empty template"):
        await importer.import_template("Default", "test_template", "")

    # Test whitespace-only string
    with pytest.raises(ValueError, match="Cannot import empty template"):
        await importer.import_template("Default", "test_template", "   \n\t  ")


@pytest.mark.asyncio
async def test_stylesheet_importer_rejects_empty_content():
    """Test that StylesheetImporter raises ValueError for empty content."""
    from mybb_mcp.sync.stylesheets import StylesheetImporter

    # Create a mock database
    mock_db = Mock()
    importer = StylesheetImporter(mock_db)

    # Test empty string
    with pytest.raises(ValueError, match="Cannot import empty stylesheet"):
        await importer.import_stylesheet("Default", "global.css", "")

    # Test whitespace-only string
    with pytest.raises(ValueError, match="Cannot import empty stylesheet"):
        await importer.import_stylesheet("Default", "global.css", "   \n\t  ")
