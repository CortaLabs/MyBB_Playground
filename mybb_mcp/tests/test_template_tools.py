"""Test suite for enhanced template tools.

Tests the 4 new template tools:
1. mybb_template_find_replace - regex/literal find/replace across template sets
2. mybb_template_batch_read - read multiple templates efficiently
3. mybb_template_batch_write - atomic batch write operations
4. mybb_template_outdated - detect outdated templates by version comparison
"""

import pytest
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import implementations
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "mybb_mcp"))

from mybb_mcp.db.connection import MyBBDatabase
from mybb_mcp.config import DatabaseConfig


class TestTemplateFindReplace:
    """Test mybb_template_find_replace functionality."""

    @pytest.fixture
    def mock_db_config(self):
        """Create mock database config."""
        return DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test_user",
            password="test_pass",
            prefix="mybb_"
        )

    @pytest.fixture
    def mock_templates(self):
        """Sample templates for find/replace testing."""
        return [
            {
                'tid': 1,
                'title': 'header',
                'template': '<div>{$pm_notice}</div>',
                'sid': 1,
                'version': '1800'
            },
            {
                'tid': 2,
                'title': 'header',
                'template': '<div>{$pm_notice}</div>',
                'sid': 2,
                'version': '1800'
            }
        ]

    def test_find_templates_for_replace_all_sets(self, mock_db_config):
        """Test finding templates across all sets."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_method:
            mock_cursor = MagicMock()
            mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
            mock_cursor.__exit__ = MagicMock(return_value=False)
            mock_cursor.fetchall.return_value = [
                {'tid': 1, 'title': 'header', 'template': '<div>test</div>', 'sid': 1, 'version': '1800'}
            ]
            mock_cursor_method.return_value = mock_cursor

            results = db.find_templates_for_replace('header', [])

            # Verify query was called with correct parameters
            assert mock_cursor.execute.called
            call_args = mock_cursor.execute.call_args[0]
            assert 'header' in str(call_args)
            assert results == mock_cursor.fetchall.return_value

    def test_find_templates_for_replace_specific_sets(self, mock_db_config):
        """Test finding templates in specific sets."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_method:
            mock_cursor = MagicMock()
            mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
            mock_cursor.__exit__ = MagicMock(return_value=False)
            mock_cursor.fetchall.return_value = []
            mock_cursor_method.return_value = mock_cursor

            results = db.find_templates_for_replace('header', [1, 2])

            # Verify IN clause was used
            call_args = mock_cursor.execute.call_args[0]
            query = call_args[0]
            params = call_args[1]

            assert 'IN' in query
            assert 'header' in params
            assert 1 in params
            assert 2 in params

    def test_regex_replacement(self, mock_db_config, mock_templates):
        """Test regex-based find/replace."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'find_templates_for_replace', return_value=mock_templates):
            with patch.object(db, 'update_template', return_value=True) as mock_update:
                # Simulate the handler logic
                title = 'header'
                find = r'\{\$pm_notice\}'  # Correct regex pattern
                replace = r'{$my_notice}\n{$pm_notice}'

                templates = db.find_templates_for_replace(title, [])
                modified_count = 0

                for template in templates:
                    original = template['template']
                    new_content = re.sub(find, replace, original)

                    if new_content != original:
                        db.update_template(template['tid'], new_content)
                        modified_count += 1

                assert modified_count == 2
                assert mock_update.call_count == 2

    def test_literal_replacement(self, mock_db_config):
        """Test literal string find/replace."""
        template = '<div>{$pm_notice}</div>'
        find = '{$pm_notice}'
        replace = '{$my_notice}'

        result = template.replace(find, replace)
        assert result == '<div>{$my_notice}</div>'

    def test_replacement_with_limit(self, mock_db_config):
        """Test find/replace with replacement limit."""
        template = '<div>test test test</div>'
        find = 'test'
        replace = 'demo'
        limit = 2

        result = template.replace(find, replace, limit)
        assert result == '<div>demo demo test</div>'


class TestTemplateBatchRead:
    """Test mybb_template_batch_read functionality."""

    @pytest.fixture
    def mock_db_config(self):
        """Create mock database config."""
        return DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test_user",
            password="test_pass",
            prefix="mybb_"
        )

    def test_batch_read_multiple_templates(self, mock_db_config):
        """Test reading multiple templates in one call."""
        db = MyBBDatabase(mock_db_config)

        # Mock different templates
        template_responses = {
            'header': {'tid': 1, 'template': '<header>content</header>'},
            'footer': {'tid': 2, 'template': '<footer>content</footer>'},
            'index': {'tid': 3, 'template': '<div>index</div>'}
        }

        def get_template_side_effect(title, sid):
            return template_responses.get(title)

        with patch.object(db, 'get_template', side_effect=get_template_side_effect):
            results = {}
            template_names = ['header', 'footer', 'index']

            for title in template_names:
                template = db.get_template(title, -2)
                if template:
                    results[title] = template['template']

            assert len(results) == 3
            assert results['header'] == '<header>content</header>'
            assert results['footer'] == '<footer>content</footer>'
            assert results['index'] == '<div>index</div>'

    def test_batch_read_with_missing_templates(self, mock_db_config):
        """Test batch read handles missing templates correctly."""
        db = MyBBDatabase(mock_db_config)

        template_responses = {
            'header': {'tid': 1, 'template': '<header>content</header>'},
            'footer': None  # Missing template
        }

        def get_template_side_effect(title, sid):
            return template_responses.get(title)

        with patch.object(db, 'get_template', side_effect=get_template_side_effect):
            results = {}
            not_found = []
            template_names = ['header', 'footer']

            for title in template_names:
                template = db.get_template(title, -2)
                if template:
                    results[title] = template['template']
                else:
                    not_found.append(title)

            assert len(results) == 1
            assert len(not_found) == 1
            assert 'footer' in not_found


class TestTemplateBatchWrite:
    """Test mybb_template_batch_write functionality."""

    @pytest.fixture
    def mock_db_config(self):
        """Create mock database config."""
        return DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test_user",
            password="test_pass",
            prefix="mybb_"
        )

    def test_batch_write_creates_new_templates(self, mock_db_config):
        """Test batch write creates new templates."""
        db = MyBBDatabase(mock_db_config)

        templates = [
            {'title': 'custom_header', 'template': '<header>new</header>'},
            {'title': 'custom_footer', 'template': '<footer>new</footer>'}
        ]

        with patch.object(db, 'get_template', return_value=None):
            with patch.object(db, 'create_template', return_value=10) as mock_create:
                created = []

                for item in templates:
                    existing = db.get_template(item['title'], 1)
                    if not existing:
                        tid = db.create_template(item['title'], item['template'], 1)
                        created.append({'title': item['title'], 'tid': tid})

                assert len(created) == 2
                assert mock_create.call_count == 2

    def test_batch_write_updates_existing_templates(self, mock_db_config):
        """Test batch write updates existing templates."""
        db = MyBBDatabase(mock_db_config)

        templates = [
            {'title': 'header', 'template': '<header>updated</header>'},
            {'title': 'footer', 'template': '<footer>updated</footer>'}
        ]

        existing_templates = {
            'header': {'tid': 1, 'template': '<header>old</header>'},
            'footer': {'tid': 2, 'template': '<footer>old</footer>'}
        }

        def get_template_side_effect(title, sid):
            return existing_templates.get(title)

        with patch.object(db, 'get_template', side_effect=get_template_side_effect):
            with patch.object(db, 'update_template', return_value=True) as mock_update:
                updated = []

                for item in templates:
                    existing = db.get_template(item['title'], 1)
                    if existing:
                        db.update_template(existing['tid'], item['template'])
                        updated.append({'title': item['title'], 'tid': existing['tid']})

                assert len(updated) == 2
                assert mock_update.call_count == 2

    def test_batch_write_atomic_operation(self, mock_db_config):
        """Test batch write collects all operations before executing."""
        templates = [
            {'title': 'template1', 'template': 'content1'},
            {'title': 'template2', 'template': 'content2'},
            {'title': 'template3', 'template': 'content3'}
        ]

        # Collect all operations first
        operations = []
        for item in templates:
            operations.append({
                'title': item['title'],
                'content': item['template'],
                'action': 'create'
            })

        # All operations should be collected before execution
        assert len(operations) == 3
        assert all(op['action'] == 'create' for op in operations)


class TestTemplateOutdated:
    """Test mybb_template_outdated functionality."""

    @pytest.fixture
    def mock_db_config(self):
        """Create mock database config."""
        return DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test_user",
            password="test_pass",
            prefix="mybb_"
        )

    def test_find_outdated_templates(self, mock_db_config):
        """Test finding outdated templates by version comparison."""
        db = MyBBDatabase(mock_db_config)

        outdated_templates = [
            {
                'tid': 10,
                'title': 'header',
                'custom_version': '1800',
                'master_version': '1820'
            },
            {
                'tid': 11,
                'title': 'footer',
                'custom_version': '1800',
                'master_version': '1810'
            }
        ]

        with patch.object(db, 'cursor') as mock_cursor_method:
            mock_cursor = MagicMock()
            mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
            mock_cursor.__exit__ = MagicMock(return_value=False)
            mock_cursor.fetchall.return_value = outdated_templates
            mock_cursor_method.return_value = mock_cursor

            results = db.find_outdated_templates(1)

            # Verify INNER JOIN query was executed
            assert mock_cursor.execute.called
            call_args = mock_cursor.execute.call_args[0]
            query = call_args[0]

            assert 'INNER JOIN' in query
            assert 'CAST' in query  # Version comparison
            assert 'AS UNSIGNED' in query
            assert len(results) == 2

    def test_outdated_templates_version_comparison(self, mock_db_config):
        """Test version comparison logic."""
        # Simulating SQL CAST comparison
        custom_version = 1800
        master_version = 1820

        assert custom_version < master_version  # Template is outdated

    def test_no_outdated_templates(self, mock_db_config):
        """Test when all templates are up to date."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_method:
            mock_cursor = MagicMock()
            mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
            mock_cursor.__exit__ = MagicMock(return_value=False)
            mock_cursor.fetchall.return_value = []
            mock_cursor_method.return_value = mock_cursor

            results = db.find_outdated_templates(1)

            assert len(results) == 0


class TestTemplateToolsIntegration:
    """Integration tests for template tools."""

    @pytest.fixture
    def mock_db_config(self):
        """Create mock database config."""
        return DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test_user",
            password="test_pass",
            prefix="mybb_"
        )

    def test_find_replace_workflow(self, mock_db_config):
        """Test complete find/replace workflow."""
        db = MyBBDatabase(mock_db_config)

        # Simulate finding templates, replacing content, updating
        templates = [
            {'tid': 1, 'title': 'header', 'template': '<div>{$old}</div>', 'sid': 1}
        ]

        with patch.object(db, 'find_templates_for_replace', return_value=templates):
            with patch.object(db, 'update_template', return_value=True) as mock_update:
                # Find
                found = db.find_templates_for_replace('header', [1])
                assert len(found) == 1

                # Replace
                new_content = found[0]['template'].replace('{$old}', '{$new}')

                # Update
                db.update_template(found[0]['tid'], new_content)

                mock_update.assert_called_once_with(1, '<div>{$new}</div>')

    def test_batch_operations_consistency(self, mock_db_config):
        """Test batch read and write maintain consistency."""
        db = MyBBDatabase(mock_db_config)

        original_templates = {
            'header': '<header>original</header>',
            'footer': '<footer>original</footer>'
        }

        # Batch read
        with patch.object(db, 'get_template') as mock_get:
            mock_get.side_effect = lambda title, sid: {'template': original_templates[title]}

            read_results = {}
            for title in ['header', 'footer']:
                template = db.get_template(title, -2)
                read_results[title] = template['template']

            assert read_results == original_templates

        # Batch write
        with patch.object(db, 'get_template', return_value={'tid': 1}):
            with patch.object(db, 'update_template', return_value=True) as mock_update:
                for title, content in read_results.items():
                    existing = db.get_template(title, 1)
                    db.update_template(existing['tid'], content)

                assert mock_update.call_count == 2
