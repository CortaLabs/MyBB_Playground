"""Tests for MyBB settings, cache, and statistics tools."""

import pytest
from unittest.mock import MagicMock, patch
from mybb_mcp.db.connection import MyBBDatabase
from mybb_mcp.config import DatabaseConfig


class TestSettings:
    """Test settings database methods."""

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

    def test_get_setting_exists(self, mock_db_config):
        """Test getting an existing setting."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                "sid": 1,
                "name": "bbname",
                "title": "Board Name",
                "description": "Name of your board",
                "optionscode": "text",
                "value": "My Forum",
                "disporder": 1,
                "gid": 1,
                "isdefault": 0
            }
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_setting("bbname")
            assert result is not None
            assert result["name"] == "bbname"
            assert result["value"] == "My Forum"

    def test_get_setting_not_found(self, mock_db_config):
        """Test getting a non-existent setting."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_setting("nonexistent")
            assert result is None

    def test_set_setting_success(self, mock_db_config):
        """Test successfully updating a setting."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.set_setting("bbname", "New Forum Name")
            assert result is True

            # Verify parameterized query
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "UPDATE" in call_args[0][0]
            assert call_args[0][1] == ("New Forum Name", "bbname")

    def test_set_setting_not_found(self, mock_db_config):
        """Test updating a non-existent setting."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 0
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.set_setting("nonexistent", "value")
            assert result is False

    def test_list_settings_all(self, mock_db_config):
        """Test listing all settings."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {"sid": 1, "name": "bbname", "value": "My Forum", "gid": 1},
                {"sid": 2, "name": "bburl", "value": "http://example.com", "gid": 1}
            ]
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.list_settings()
            assert len(result) == 2
            assert result[0]["name"] == "bbname"

    def test_list_settings_by_group(self, mock_db_config):
        """Test listing settings filtered by group."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {"sid": 1, "name": "bbname", "value": "My Forum", "gid": 2}
            ]
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.list_settings(gid=2)
            assert len(result) == 1

            # Verify parameterized query with gid
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "WHERE gid = %s" in call_args[0][0]
            assert call_args[0][1] == (2,)

    def test_list_setting_groups(self, mock_db_config):
        """Test listing setting groups."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {"gid": 1, "name": "general", "title": "General Configuration", "description": "General settings"},
                {"gid": 2, "name": "user", "title": "User Registration", "description": "User settings"}
            ]
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.list_setting_groups()
            assert len(result) == 2
            assert result[0]["name"] == "general"


class TestCache:
    """Test cache database methods."""

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

    def test_read_cache_exists(self, mock_db_config):
        """Test reading an existing cache entry."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {"cache": "a:1:{s:4:\"test\";s:5:\"value\";}"}
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.read_cache("settings")
            assert result == "a:1:{s:4:\"test\";s:5:\"value\";}"

            # Verify parameterized query
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "WHERE title = %s" in call_args[0][0]
            assert call_args[0][1] == ("settings",)

    def test_read_cache_not_found(self, mock_db_config):
        """Test reading a non-existent cache entry."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.read_cache("nonexistent")
            assert result is None

    def test_rebuild_cache_specific(self, mock_db_config):
        """Test rebuilding a specific cache."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.rebuild_cache("settings")
            assert result["status"] == "success"
            assert "settings" in result["message"]
            assert result["rows_affected"] == 1

            # Verify DELETE was called with parameterized query
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "DELETE FROM" in call_args[0][0]
            assert "WHERE title = %s" in call_args[0][0]
            assert call_args[0][1] == ("settings",)

    def test_rebuild_cache_all(self, mock_db_config):
        """Test rebuilding all caches."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 5
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.rebuild_cache("all")
            assert result["status"] == "success"
            assert "All caches" in result["message"]
            assert result["rows_affected"] == 5

    def test_list_caches(self, mock_db_config):
        """Test listing all cache entries."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {"title": "settings", "size": 1024},
                {"title": "plugins", "size": 512},
                {"title": "usergroups", "size": 256}
            ]
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.list_caches()
            assert len(result) == 3
            assert result[0]["title"] == "settings"
            assert result[0]["size"] == 1024

    def test_clear_cache_specific(self, mock_db_config):
        """Test clearing a specific cache."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.clear_cache("settings")
            assert result is True

            # Verify parameterized DELETE
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "WHERE title = %s" in call_args[0][0]
            assert call_args[0][1] == ("settings",)

    def test_clear_cache_all(self, mock_db_config):
        """Test clearing all caches."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 5
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.clear_cache(None)
            assert result is True


class TestStatistics:
    """Test statistics database methods."""

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

    def test_get_forum_stats(self, mock_db_config):
        """Test getting forum statistics."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            # First call returns counts
            mock_cursor.fetchone.side_effect = [
                {"total_users": 100, "total_threads": 50, "total_posts": 250},
                {"uid": 99, "username": "newest_user", "regdate": 1234567890}
            ]
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_forum_stats()
            assert result["total_users"] == 100
            assert result["total_threads"] == 50
            assert result["total_posts"] == 250
            assert result["newest_member"]["username"] == "newest_user"

    def test_get_forum_stats_no_members(self, mock_db_config):
        """Test getting forum stats when no members exist."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            # First call returns counts, second returns None (no users)
            mock_cursor.fetchone.side_effect = [
                {"total_users": 0, "total_threads": 0, "total_posts": 0},
                None
            ]
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_forum_stats()
            assert result["total_users"] == 0
            assert result["newest_member"] is None

    def test_get_board_stats(self, mock_db_config):
        """Test getting board statistics."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            # Three calls: counts, latest post, active forum
            mock_cursor.fetchone.side_effect = [
                {"total_forums": 10, "total_users": 100, "total_threads": 50, "total_posts": 250, "total_pms": 30},
                {"pid": 250, "tid": 45, "fid": 2, "subject": "Latest Post", "dateline": 1234567890, "username": "user1"},
                {"fid": 2, "name": "General Discussion", "threads": 30, "posts": 150}
            ]
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_board_stats()
            assert result["total_forums"] == 10
            assert result["total_users"] == 100
            assert result["total_private_messages"] == 30
            assert result["latest_post"]["subject"] == "Latest Post"
            assert result["most_active_forum"]["name"] == "General Discussion"

    def test_get_board_stats_empty_board(self, mock_db_config):
        """Test getting board stats for empty board."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            # Three calls: counts, no latest post, no active forum
            mock_cursor.fetchone.side_effect = [
                {"total_forums": 0, "total_users": 0, "total_threads": 0, "total_posts": 0, "total_pms": 0},
                None,
                None
            ]
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_board_stats()
            assert result["total_forums"] == 0
            assert result["latest_post"] is None
            assert result["most_active_forum"] is None


class TestSecurity:
    """Test SQL injection prevention for settings and cache."""

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

    def test_setting_sql_injection_prevention(self, mock_db_config):
        """Test that settings queries use parameterized queries."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            # Try malicious input
            malicious = "bbname'; DROP TABLE settings; --"
            db.get_setting(malicious)

            # Verify parameterized query was used
            call_args = mock_cursor.execute.call_args
            assert call_args[0][1] == (malicious,)  # Should be passed as parameter

    def test_cache_sql_injection_prevention(self, mock_db_config):
        """Test that cache queries use parameterized queries."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            # Try malicious input
            malicious = "settings'; DELETE FROM datacache; --"
            db.read_cache(malicious)

            # Verify parameterized query was used
            call_args = mock_cursor.execute.call_args
            assert call_args[0][1] == (malicious,)

    def test_set_setting_parameterized(self, mock_db_config):
        """Test that set_setting uses parameterized UPDATE."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            malicious_name = "bbname'; UPDATE users SET usergroup=4; --"
            malicious_value = "value'; DELETE FROM settings; --"
            db.set_setting(malicious_name, malicious_value)

            # Verify both values are parameterized
            call_args = mock_cursor.execute.call_args
            assert call_args[0][1] == (malicious_value, malicious_name)
