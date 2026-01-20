"""Unit tests for server_service module."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from mybb_mcp.orchestration.server_service import (
    ServerOrchestrationService, ServerResult, ServerStatus, LogQueryOptions
)


class TestStateFileManagement:
    """Test state file read/write/clear operations."""

    def test_write_and_read_state(self, tmp_path):
        """State file round-trips correctly."""
        config = MagicMock()
        config.mybb_root = str(tmp_path / "TestForum")
        (tmp_path / "TestForum").mkdir()

        service = ServerOrchestrationService(config)
        service.state_file = tmp_path / ".mybb-server.json"

        state = {"port": 8022, "pid": 12345}
        service._write_state(state)

        read_state = service._read_state()
        assert read_state["port"] == 8022
        assert read_state["pid"] == 12345
        assert read_state["version"] == 1

    def test_read_missing_state(self, tmp_path):
        """Missing state file returns None."""
        config = MagicMock()
        config.mybb_root = str(tmp_path / "TestForum")

        service = ServerOrchestrationService(config)
        service.state_file = tmp_path / "nonexistent.json"

        assert service._read_state() is None

    def test_clear_state(self, tmp_path):
        """Clear removes state file."""
        config = MagicMock()
        config.mybb_root = str(tmp_path / "TestForum")

        service = ServerOrchestrationService(config)
        service.state_file = tmp_path / ".mybb-server.json"
        service.state_file.write_text("{}")

        service._clear_state()
        assert not service.state_file.exists()

    def test_validate_state_invalid_pid(self, tmp_path):
        """Invalid PID returns False."""
        config = MagicMock()
        config.mybb_root = str(tmp_path / "TestForum")

        service = ServerOrchestrationService(config)
        state = {"pid": 999999999}  # Very unlikely to exist

        assert service._validate_state(state) == False

    def test_write_state_creates_parent_dir(self, tmp_path):
        """Writing state creates parent directory if needed."""
        config = MagicMock()
        config.mybb_root = str(tmp_path / "TestForum")

        service = ServerOrchestrationService(config)
        nested_dir = tmp_path / "nested" / "path"
        service.state_file = nested_dir / ".mybb-server.json"

        state = {"port": 8022}
        service._write_state(state)

        assert service.state_file.exists()
        assert service.state_file.parent.exists()

    def test_read_malformed_json(self, tmp_path):
        """Malformed JSON returns None."""
        config = MagicMock()
        config.mybb_root = str(tmp_path / "TestForum")

        service = ServerOrchestrationService(config)
        service.state_file = tmp_path / ".mybb-server.json"
        service.state_file.write_text("{not valid json")

        assert service._read_state() is None


class TestLogQueryOptions:
    """Test LogQueryOptions dataclass."""

    def test_default_options(self):
        """Default options are sensible."""
        opts = LogQueryOptions()
        assert opts.errors_only == False
        assert opts.exclude_static == False
        assert opts.limit == 50
        assert opts.tail == True
        assert opts.since_minutes is None
        assert opts.filter_keyword is None

    def test_custom_options(self):
        """Custom options override defaults."""
        opts = LogQueryOptions(
            errors_only=True,
            exclude_static=True,
            since_minutes=10,
            filter_keyword="error",
            limit=100,
            tail=False
        )
        assert opts.errors_only == True
        assert opts.exclude_static == True
        assert opts.since_minutes == 10
        assert opts.filter_keyword == "error"
        assert opts.limit == 100
        assert opts.tail == False


class TestServerResultDataclass:
    """Test ServerResult dataclass."""

    def test_minimal_result(self):
        """ServerResult with minimal fields."""
        result = ServerResult(success=True, message="Server started")
        assert result.success == True
        assert result.message == "Server started"
        assert result.port is None
        assert result.pid is None
        assert result.uptime_seconds is None

    def test_full_result(self):
        """ServerResult with all fields."""
        result = ServerResult(
            success=True,
            message="Server running",
            port=8022,
            pid=12345,
            uptime_seconds=3600.5
        )
        assert result.success == True
        assert result.message == "Server running"
        assert result.port == 8022
        assert result.pid == 12345
        assert result.uptime_seconds == 3600.5


class TestServerStatusDataclass:
    """Test ServerStatus dataclass."""

    def test_stopped_status(self):
        """ServerStatus for stopped server."""
        status = ServerStatus(running=False)
        assert status.running == False
        assert status.port is None
        assert status.pid is None
        assert status.started_at is None
        assert status.uptime_seconds is None
        assert status.log_file is None
        assert status.mariadb_running == False

    def test_running_status(self):
        """ServerStatus for running server."""
        status = ServerStatus(
            running=True,
            port=8022,
            pid=12345,
            started_at="2026-01-20T01:00:00Z",
            uptime_seconds=600.0,
            log_file="/path/to/server.log",
            mariadb_running=True
        )
        assert status.running == True
        assert status.port == 8022
        assert status.pid == 12345
        assert status.started_at == "2026-01-20T01:00:00Z"
        assert status.uptime_seconds == 600.0
        assert status.log_file == "/path/to/server.log"
        assert status.mariadb_running == True


class TestServiceInitialization:
    """Test ServerOrchestrationService initialization."""

    def test_init_sets_paths(self, tmp_path):
        """Initialization sets correct paths."""
        config = MagicMock()
        testforum = tmp_path / "TestForum"
        testforum.mkdir()
        config.mybb_root = str(testforum)

        service = ServerOrchestrationService(config)

        assert service.repo_root == tmp_path
        assert service.mybb_root == testforum
        assert service.state_file == tmp_path / ".mybb-server.json"
        assert service.log_dir == tmp_path / "logs"
        assert service.log_file == tmp_path / "logs" / "server.log"

    def test_init_with_trailing_slash(self, tmp_path):
        """Initialization handles trailing slashes correctly."""
        config = MagicMock()
        testforum = tmp_path / "TestForum"
        testforum.mkdir()
        config.mybb_root = str(testforum) + "/"

        service = ServerOrchestrationService(config)

        # Path normalization should handle trailing slash
        assert service.mybb_root == testforum
        assert service.repo_root == tmp_path
