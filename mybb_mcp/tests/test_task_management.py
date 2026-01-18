"""Tests for MyBB task management tools."""

import pytest
from unittest.mock import MagicMock, patch
from mybb_mcp.db.connection import MyBBDatabase
from mybb_mcp.config import DatabaseConfig


class TestTaskManagement:
    """Test task management database methods."""

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
    def sample_task(self):
        """Sample task data."""
        return {
            "tid": 1,
            "title": "Test Task",
            "description": "Test task description",
            "file": "testtask",
            "minute": "*",
            "hour": "0",
            "day": "*",
            "month": "*",
            "weekday": "*",
            "nextrun": 1768658400,
            "lastrun": 1768654800,
            "enabled": 1,
            "logging": 1,
            "locked": 0
        }

    def test_list_tasks_all(self, mock_db_config, sample_task):
        """Test listing all tasks."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [sample_task]
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.list_tasks()
            assert len(result) == 1
            assert result[0]["title"] == "Test Task"

            # Verify SQL was called correctly
            sql = mock_cursor.execute.call_args[0][0]
            assert "mybb_tasks" in sql
            assert "ORDER BY title" in sql

    def test_list_tasks_enabled_only(self, mock_db_config, sample_task):
        """Test listing only enabled tasks."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [sample_task]
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.list_tasks(enabled_only=True)
            assert len(result) == 1

            # Verify WHERE enabled = 1 clause was used
            sql = mock_cursor.execute.call_args[0][0]
            assert "WHERE enabled = 1" in sql

    def test_get_task_exists(self, mock_db_config, sample_task):
        """Test getting a specific task that exists."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = sample_task
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_task(1)
            assert result is not None
            assert result["tid"] == 1
            assert result["title"] == "Test Task"

    def test_get_task_not_exists(self, mock_db_config):
        """Test getting a task that doesn't exist."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_task(999)
            assert result is None

    def test_enable_task_success(self, mock_db_config):
        """Test enabling a task successfully."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.enable_task(1)
            assert result is True

            # Verify UPDATE query
            sql = mock_cursor.execute.call_args[0][0]
            assert "UPDATE" in sql
            assert "enabled = 1" in sql

    def test_enable_task_not_found(self, mock_db_config):
        """Test enabling a task that doesn't exist."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 0
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.enable_task(999)
            assert result is False

    def test_disable_task_success(self, mock_db_config):
        """Test disabling a task successfully."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.disable_task(1)
            assert result is True

            # Verify UPDATE query
            sql = mock_cursor.execute.call_args[0][0]
            assert "UPDATE" in sql
            assert "enabled = 0" in sql

    def test_update_task_nextrun_success(self, mock_db_config):
        """Test updating task next run time."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            new_nextrun = 1768662000
            result = db.update_task_nextrun(1, new_nextrun)
            assert result is True

            # Verify UPDATE query with correct timestamp
            call_args = mock_cursor.execute.call_args
            assert "UPDATE" in call_args[0][0]
            assert "nextrun = %s" in call_args[0][0]
            assert call_args[0][1] == (new_nextrun, 1)

    def test_get_task_logs_all(self, mock_db_config):
        """Test getting all task logs."""
        sample_logs = [
            {"lid": 1, "tid": 1, "dateline": 1768654800, "data": "Task completed"},
            {"lid": 2, "tid": 2, "dateline": 1768654900, "data": "Task failed"}
        ]

        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = sample_logs
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_task_logs()
            assert len(result) == 2
            assert result[0]["lid"] == 1

    def test_get_task_logs_filtered(self, mock_db_config):
        """Test getting task logs filtered by task ID."""
        sample_logs = [
            {"lid": 1, "tid": 1, "dateline": 1768654800, "data": "Task completed"}
        ]

        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = sample_logs
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            result = db.get_task_logs(tid=1, limit=50)
            assert len(result) == 1

            # Verify WHERE clause for tid
            sql = mock_cursor.execute.call_args[0][0]
            assert "WHERE tid = %s" in sql

    def test_get_task_logs_limit_enforcement(self, mock_db_config):
        """Test that task logs limit is enforced (max 500)."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            # Try to request 1000 logs
            db.get_task_logs(limit=1000)

            # Should be capped at 500
            call_args = mock_cursor.execute.call_args
            assert call_args[0][1] == (500,) or call_args[0][1][-1] == 500


class TestTaskSecurity:
    """Test task management security."""

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

    def test_task_sql_injection_prevention(self, mock_db_config):
        """Test that task methods use parameterized queries."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {"tid": 1, "title": "Test"}
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            # Try to get task with potentially malicious ID
            db.get_task(1)

            # Verify parameterized query was used
            call_args = mock_cursor.execute.call_args
            assert "%s" in call_args[0][0]  # SQL has placeholder
            assert isinstance(call_args[0][1], tuple)  # params tuple

    def test_task_update_parameterized(self, mock_db_config):
        """Test that task updates use parameterized queries."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor_ctx:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

            # Update task nextrun
            db.update_task_nextrun(1, 1768658400)

            # Verify parameterized query
            call_args = mock_cursor.execute.call_args
            assert "%s" in call_args[0][0]
            assert call_args[0][1] == (1768658400, 1)
