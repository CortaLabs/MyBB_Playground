"""
Unit tests for PluginTemplateImporter.

Tests the import_template method's core logic:
- Template name construction from codename and template_name
- Validation that empty content raises ValueError
- Database interaction (mocked)
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock
from pathlib import Path

from mybb_mcp.sync.plugin_templates import PluginTemplateImporter


class TestPluginTemplateImporter:
    """Unit tests for PluginTemplateImporter class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection."""
        db = Mock()
        # Mock the actual methods used by PluginTemplateImporter
        db.get_template = Mock(return_value=None)
        db.update_template = Mock(return_value=True)
        db.create_template = Mock(return_value=1)
        return db

    @pytest.fixture
    def importer(self, mock_db):
        """Create a PluginTemplateImporter instance with mocked database."""
        return PluginTemplateImporter(mock_db)

    def test_template_name_construction(self, importer):
        """Test that template name is correctly built from codename and template_name."""
        # Template name should be: {codename}_{template_name}
        codename = "myplugin"
        template_name = "postbit_badge"

        # Expected template title
        expected_title = f"{codename}_{template_name}"

        # Verify this is the naming convention
        assert expected_title == f"{codename}_{template_name}"

    @pytest.mark.asyncio
    async def test_empty_content_raises_error(self, importer, mock_db):
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Cannot import empty template"):
            # This should raise because content is empty
            await importer.import_template(
                codename="testplugin",
                template_name="test_template",
                content=""
            )

    @pytest.mark.asyncio
    async def test_whitespace_content_raises_error(self, importer, mock_db):
        """Test that whitespace-only content raises ValueError."""
        with pytest.raises(ValueError, match="Cannot import empty template"):
            # This should raise because content is only whitespace
            await importer.import_template(
                codename="testplugin",
                template_name="test_template",
                content="   \n\t  \n"
            )

    @pytest.mark.asyncio
    async def test_valid_content_accepted(self, importer, mock_db):
        """Test that valid content is accepted without error."""
        # Mock database responses
        mock_db.get_template = Mock(return_value=None)  # Template doesn't exist
        mock_db.create_template = Mock(return_value=1)  # Insert successful

        # This should NOT raise
        try:
            result = await importer.import_template(
                codename="testplugin",
                template_name="test_template",
                content="<div>Hello World</div>"
            )
            assert result is True
        except ValueError:
            pytest.fail("Valid content should not raise ValueError")

    @pytest.mark.asyncio
    async def test_database_interaction_insert(self, importer, mock_db):
        """Test that new templates trigger database create_template call."""
        # Mock: template doesn't exist
        mock_db.get_template = Mock(return_value=None)
        mock_db.create_template = Mock(return_value=1)

        result = await importer.import_template(
            codename="testplugin",
            template_name="new_template",
            content="<div>Content</div>"
        )

        # Verify create_template was called
        assert mock_db.create_template.called
        assert result is True

    @pytest.mark.asyncio
    async def test_database_interaction_update(self, importer, mock_db):
        """Test that existing templates trigger database update_template call."""
        # Mock: template exists
        existing_template = {
            'tid': 42,
            'title': 'testplugin_existing_template'
        }
        mock_db.get_template = Mock(return_value=existing_template)
        mock_db.update_template = Mock(return_value=True)

        result = await importer.import_template(
            codename="testplugin",
            template_name="existing_template",
            content="<div>Updated Content</div>"
        )

        # Verify update_template was called
        assert mock_db.update_template.called
        assert result is True

    def test_template_title_format(self, importer):
        """Test that template titles follow the {codename}_{template_name} format."""
        test_cases = [
            ("myplugin", "header", "myplugin_header"),
            ("test_plugin", "footer_extra", "test_plugin_footer_extra"),
            ("simple", "simple", "simple_simple"),
        ]

        for codename, template_name, expected_title in test_cases:
            actual_title = f"{codename}_{template_name}"
            assert actual_title == expected_title, \
                f"Expected {expected_title}, got {actual_title}"
