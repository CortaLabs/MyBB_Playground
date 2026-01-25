"""Tests for template from-DB sync with manifest-based change detection.

Tests Task Package 5.1: dateline-based filtering in _sync_theme_templates_from_db.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from mybb_mcp.sync.service import DiskSyncService
from mybb_mcp.sync.config import SyncConfig
from mybb_mcp.sync.manifest import SyncManifest


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir) / "test_theme"
    workspace.mkdir(parents=True)
    yield workspace
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_db():
    """Create a mock MyBBDatabase."""
    db = Mock()
    return db


@pytest.fixture
def mock_bridge():
    """Create a mock MyBBBridgeClient."""
    with patch('mybb_mcp.sync.service.MyBBBridgeClient') as mock_bridge_class:
        mock_bridge = MagicMock()
        mock_bridge_class.return_value = mock_bridge
        yield mock_bridge


@pytest.fixture
def sync_service(mock_db, temp_workspace):
    """Create a DiskSyncService instance."""
    config = SyncConfig(sync_root=temp_workspace.parent)
    service = DiskSyncService(
        db=mock_db,
        config=config,
        mybb_url="http://localhost:8022",
        workspace_root=temp_workspace.parent,
        mybb_root=Path("/fake/mybb/root")
    )
    return service


def test_first_export_writes_all_templates(sync_service, temp_workspace, mock_bridge, mock_db):
    """First export should write ALL templates since no manifest exists."""
    # Setup mock template group manager
    with patch('mybb_mcp.sync.service.TemplateGroupManager') as mock_group_mgr:
        mock_group_instance = Mock()
        mock_group_instance.get_group_name.return_value = "Header Templates"
        mock_group_mgr.return_value = mock_group_instance

        # Mock bridge response with templates
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {
            'templates': [
                {'title': 'header', 'template': '<div>Header v1</div>', 'dateline': 1000},
                {'title': 'footer', 'template': '<div>Footer v1</div>', 'dateline': 1000}
            ]
        }
        mock_bridge.call.return_value = mock_result

        # Execute sync
        result = sync_service._sync_theme_templates_from_db(temp_workspace, template_set_sid=1)

        # Verify all templates were written
        assert len(result['templates']) == 2
        assert 'header' in result['templates']
        assert 'footer' in result['templates']
        assert len(result.get('skipped', [])) == 0

        # Verify files exist
        header_file = temp_workspace / "templates" / "Header Templates" / "header.html"
        footer_file = temp_workspace / "templates" / "Header Templates" / "footer.html"
        assert header_file.exists()
        assert footer_file.exists()
        assert header_file.read_text() == '<div>Header v1</div>'

        # Verify manifest was created
        manifest_file = temp_workspace / ".sync_manifest.json"
        assert manifest_file.exists()


def test_second_export_skips_unchanged_templates(sync_service, temp_workspace, mock_bridge, mock_db):
    """Second export with no DB changes should skip ALL templates."""
    # Setup mock template group manager
    with patch('mybb_mcp.sync.service.TemplateGroupManager') as mock_group_mgr:
        mock_group_instance = Mock()
        mock_group_instance.get_group_name.return_value = "Header Templates"
        mock_group_mgr.return_value = mock_group_instance

        # First export - create initial files
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {
            'templates': [
                {'title': 'header', 'template': '<div>Header v1</div>', 'dateline': 1000},
                {'title': 'footer', 'template': '<div>Footer v1</div>', 'dateline': 1000}
            ]
        }
        mock_bridge.call.return_value = mock_result

        result1 = sync_service._sync_theme_templates_from_db(temp_workspace, template_set_sid=1)
        assert len(result1['templates']) == 2

        # Second export - same datelines, should skip
        result2 = sync_service._sync_theme_templates_from_db(temp_workspace, template_set_sid=1)

        # Verify all templates were skipped
        assert len(result2.get('skipped', [])) == 2
        assert 'header' in result2['skipped']
        assert 'footer' in result2['skipped']
        assert len(result2['templates']) == 0


def test_db_change_triggers_reexport(sync_service, temp_workspace, mock_bridge, mock_db):
    """Template edited in Admin CP (new dateline) should trigger re-export."""
    # Setup mock template group manager
    with patch('mybb_mcp.sync.service.TemplateGroupManager') as mock_group_mgr:
        mock_group_instance = Mock()
        mock_group_instance.get_group_name.return_value = "Header Templates"
        mock_group_mgr.return_value = mock_group_instance

        # First export
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {
            'templates': [
                {'title': 'header', 'template': '<div>Header v1</div>', 'dateline': 1000}
            ]
        }
        mock_bridge.call.return_value = mock_result

        result1 = sync_service._sync_theme_templates_from_db(temp_workspace, template_set_sid=1)
        assert len(result1['templates']) == 1

        # Second export - dateline changed (template edited in Admin CP)
        mock_result.data = {
            'templates': [
                {'title': 'header', 'template': '<div>Header v2</div>', 'dateline': 2000}
            ]
        }

        result2 = sync_service._sync_theme_templates_from_db(temp_workspace, template_set_sid=1)

        # Verify template was re-exported
        assert len(result2['templates']) == 1
        assert 'header' in result2['templates']
        assert len(result2.get('skipped', [])) == 0

        # Verify file content was updated
        header_file = temp_workspace / "templates" / "Header Templates" / "header.html"
        assert header_file.read_text() == '<div>Header v2</div>'


def test_manifest_tracks_db_dateline(sync_service, temp_workspace, mock_bridge, mock_db):
    """Verify manifest stores db_dateline after from_db sync."""
    # Setup mock template group manager
    with patch('mybb_mcp.sync.service.TemplateGroupManager') as mock_group_mgr:
        mock_group_instance = Mock()
        mock_group_instance.get_group_name.return_value = "Header Templates"
        mock_group_mgr.return_value = mock_group_instance

        # Export template
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {
            'templates': [
                {'title': 'header', 'template': '<div>Header</div>', 'dateline': 12345}
            ]
        }
        mock_bridge.call.return_value = mock_result

        sync_service._sync_theme_templates_from_db(temp_workspace, template_set_sid=1)

        # Load manifest and verify dateline was stored
        manifest = SyncManifest(temp_workspace / ".sync_manifest.json")
        header_file = temp_workspace / "templates" / "Header Templates" / "header.html"

        # Get relative path
        rel_path = header_file.relative_to(temp_workspace)
        file_key = str(rel_path).replace('\\', '/')

        assert file_key in manifest.files
        file_entry = manifest.files[file_key]
        assert file_entry.db_dateline == 12345
        assert file_entry.sync_direction == 'from_db'
        assert file_entry.db_entity_type == 'template'
        assert file_entry.db_sid == 1


def test_mixed_skip_and_export(sync_service, temp_workspace, mock_bridge, mock_db):
    """Test with some templates changed and some unchanged."""
    # Setup mock template group manager
    with patch('mybb_mcp.sync.service.TemplateGroupManager') as mock_group_mgr:
        mock_group_instance = Mock()
        mock_group_instance.get_group_name.return_value = "Header Templates"
        mock_group_mgr.return_value = mock_group_instance

        # First export - two templates
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {
            'templates': [
                {'title': 'header', 'template': '<div>Header v1</div>', 'dateline': 1000},
                {'title': 'footer', 'template': '<div>Footer v1</div>', 'dateline': 1000}
            ]
        }
        mock_bridge.call.return_value = mock_result

        result1 = sync_service._sync_theme_templates_from_db(temp_workspace, template_set_sid=1)
        assert len(result1['templates']) == 2

        # Second export - only header changed
        mock_result.data = {
            'templates': [
                {'title': 'header', 'template': '<div>Header v2</div>', 'dateline': 2000},
                {'title': 'footer', 'template': '<div>Footer v1</div>', 'dateline': 1000}
            ]
        }

        result2 = sync_service._sync_theme_templates_from_db(temp_workspace, template_set_sid=1)

        # Verify one exported, one skipped
        assert len(result2['templates']) == 1
        assert 'header' in result2['templates']
        assert len(result2['skipped']) == 1
        assert 'footer' in result2['skipped']
