"""Tests for MyBB plugin lifecycle management tools."""

import pytest
from unittest.mock import MagicMock, patch
from mybb_mcp.db.connection import MyBBDatabase
from mybb_mcp.config import DatabaseConfig


class TestPluginLifecycle:
    """Test plugin lifecycle database methods."""

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

    def test_get_plugins_cache_empty(self, mock_db_config):
        """Test getting empty plugins cache."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {"cache": "a:0:{}"}
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_plugins_cache()
            assert result["raw"] == "a:0:{}"
            assert result["plugins"] == []

    def test_get_plugins_cache_with_plugins(self, mock_db_config):
        """Test getting plugins cache with active plugins."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                "cache": 'a:2:{i:0;s:10:"myplugin1";i:1;s:10:"myplugin2";}'
            }
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_plugins_cache()
            assert len(result["plugins"]) == 2
            assert "myplugin1" in result["plugins"]
            assert "myplugin2" in result["plugins"]

    def test_get_plugins_cache_no_row(self, mock_db_config):
        """Test getting plugins cache when row doesn't exist."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_plugins_cache()
            assert result["raw"] == ""
            assert result["plugins"] == []

    def test_update_plugins_cache_empty(self, mock_db_config):
        """Test updating plugins cache with empty list."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            db.update_plugins_cache([])

            # Verify execute was called with correct serialized format
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "a:0:{}" in call_args[0][1]

    def test_update_plugins_cache_with_plugins(self, mock_db_config):
        """Test updating plugins cache with plugin list."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            db.update_plugins_cache(["plugin1", "plugin2"])

            # Verify execute was called
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            # Get the serialized value (first element of params tuple)
            serialized = call_args[0][1][0]
            # Should contain serialized array with 2 elements
            assert "a:2:" in serialized
            assert "plugin1" in serialized
            assert "plugin2" in serialized

    def test_is_plugin_installed_true(self, mock_db_config):
        """Test checking if plugin is installed (active)."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                "cache": 'a:1:{i:0;s:10:"testplugin";}'
            }
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.is_plugin_installed("testplugin")
            assert result is True

    def test_is_plugin_installed_false(self, mock_db_config):
        """Test checking if plugin is not installed."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {"cache": "a:0:{}"}
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.is_plugin_installed("nonexistent")
            assert result is False


class TestPluginSecurity:
    """Test plugin lifecycle security."""

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

    def test_plugin_cache_sql_injection_prevention(self, mock_db_config):
        """Test that plugin cache methods use parameterized queries."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {"cache": "a:0:{}"}
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            # Execute get_plugins_cache
            db.get_plugins_cache()

            # Verify parameterized query was used
            call_args = mock_cursor.execute.call_args
            assert "%s" in call_args[0][0]  # SQL has placeholder
            assert call_args[0][1] == ("plugins",)  # params tuple

    def test_update_plugins_cache_sql_injection_prevention(self, mock_db_config):
        """Test that update_plugins_cache uses parameterized queries."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            # Try to inject SQL through plugin name
            db.update_plugins_cache(["normal_plugin"])

            # Verify parameterized query was used
            call_args = mock_cursor.execute.call_args
            assert "%s" in call_args[0][0]  # SQL has placeholders
            assert isinstance(call_args[0][1], tuple)  # params is tuple
