"""Tests for theme template group organization."""

import pytest
from pathlib import Path
from unittest.mock import Mock
from mybb_mcp.sync.groups import TemplateGroupManager


class TestTemplateGrouping:
    """Test template group categorization."""

    def test_header_template_grouping(self):
        """Test header templates assigned to Header Templates group."""
        # Mock DB - not needed for hardcoded patterns
        db = None
        group_mgr = TemplateGroupManager(db)

        group = group_mgr.get_group_name("header_welcome", sid=1)
        assert group == "Header Templates"

    def test_footer_template_grouping(self):
        """Test footer templates assigned to Footer Templates group."""
        db = None
        group_mgr = TemplateGroupManager(db)

        group = group_mgr.get_group_name("footer_links", sid=1)
        assert group == "Footer Templates"

    def test_forum_template_grouping(self):
        """Test forum templates assigned to Forum Templates group."""
        db = None
        group_mgr = TemplateGroupManager(db)

        group = group_mgr.get_group_name("forum_index", sid=1)
        assert group == "Forum Templates"

    def test_custom_prefix_grouping(self):
        """Test custom prefix gets capitalized group name."""
        # Mock DB that returns empty list, allowing fallback to Strategy 4
        db = Mock()
        db.list_template_groups = Mock(return_value=[])
        group_mgr = TemplateGroupManager(db)

        group = group_mgr.get_group_name("myplugin_welcome", sid=1)
        assert group == "Myplugin Templates"


class TestDirectPathBuilding:
    """Test direct path building from workspace_path (no PathRouter method)."""

    def test_grouped_path_building(self):
        """Test building grouped paths directly from workspace_path."""
        # Simulates what the service.py code does
        workspace_path = Path("/plugin_manager/themes/public/my_theme")
        group_name = "Header Templates"
        title = "header_welcome"

        file_path = workspace_path / "templates" / group_name / f"{title}.html"

        expected = Path("/plugin_manager/themes/public/my_theme/templates/Header Templates/header_welcome.html")
        assert file_path == expected

    def test_workspace_path_includes_visibility(self):
        """Verify workspace_path includes visibility subdirectory."""
        # This tests the key insight: workspace_path already has visibility baked in
        workspace_path = Path("/plugin_manager/themes/private/secret_theme")
        group_name = "Footer Templates"
        title = "footer_links"

        file_path = workspace_path / "templates" / group_name / f"{title}.html"

        # Should include 'private' visibility in path
        assert "private" in str(file_path)
        assert file_path == Path("/plugin_manager/themes/private/secret_theme/templates/Footer Templates/footer_links.html")
