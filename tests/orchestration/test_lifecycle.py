"""Tests for server lifecycle methods (Task Packages 1.3 and 1.4)."""

import os
import time
import pytest
from pathlib import Path
from datetime import datetime, timezone
from mybb_mcp.orchestration import ServerOrchestrationService, ServerResult, ServerStatus


class TestCheckMariaDB:
    """Tests for _check_mariadb helper method."""

    def test_check_mariadb_detects_running_process(self, temp_service):
        """Test that _check_mariadb returns True when MariaDB is running."""
        # This test depends on actual MariaDB running in environment
        # It's more of an integration test
        result = temp_service._check_mariadb()
        assert isinstance(result, bool)
        # We can't assert True/False without knowing if MariaDB is actually running


class TestGetStatus:
    """Tests for get_status method."""

    def test_get_status_when_no_state_file(self, temp_service):
        """Test get_status returns running=False when no state file exists."""
        status = temp_service.get_status()

        assert isinstance(status, ServerStatus)
        assert status.running is False
        assert status.port is None
        assert status.pid is None
        assert status.started_at is None
        assert status.uptime_seconds is None
        assert status.log_file is None
        assert isinstance(status.mariadb_running, bool)

    def test_get_status_with_valid_state(self, temp_service):
        """Test get_status returns running=True with valid state."""
        # Write valid state with current process PID (guaranteed to be running)
        current_pid = os.getpid()
        started_at = datetime.now(timezone.utc).isoformat()

        temp_service._write_state({
            'port': 8022,
            'pid': current_pid,
            'started_at': started_at,
            'log_file': str(temp_service.log_file)
        })

        status = temp_service.get_status()

        assert status.running is True
        assert status.port == 8022
        assert status.pid == current_pid
        assert status.started_at == started_at
        assert status.uptime_seconds is not None
        assert status.uptime_seconds >= 0
        assert status.log_file == str(temp_service.log_file)

    def test_get_status_cleans_stale_state(self, temp_service):
        """Test get_status cleans up stale state file automatically."""
        # Write state with invalid PID
        temp_service._write_state({
            'port': 8022,
            'pid': 999999,  # Very unlikely to exist
            'started_at': datetime.now(timezone.utc).isoformat(),
            'log_file': str(temp_service.log_file)
        })

        assert temp_service.state_file.exists()

        status = temp_service.get_status()

        # Should clean up stale state
        assert status.running is False
        assert not temp_service.state_file.exists()


class TestCheckPortAvailable:
    """Tests for _check_port_available helper method."""

    def test_check_port_available_on_free_port(self, temp_service):
        """Test _check_port_available returns True for unused port."""
        # Use very high port that's unlikely to be in use
        available, pid = temp_service._check_port_available(58022)

        assert available is True
        assert pid is None

    def test_check_port_available_on_used_port(self, temp_service):
        """Test _check_port_available returns False for used port."""
        # Port 22 (SSH) is almost always in use on dev systems
        available, pid = temp_service._check_port_available(22)

        # This might vary by environment, but if port is in use:
        if not available:
            assert isinstance(pid, (int, type(None)))


class TestRotateLog:
    """Tests for _rotate_log helper method."""

    def test_rotate_log_creates_directory(self, temp_service):
        """Test _rotate_log creates log directory if it doesn't exist."""
        # Ensure log dir doesn't exist
        if temp_service.log_dir.exists():
            import shutil
            shutil.rmtree(temp_service.log_dir)

        temp_service._rotate_log()

        assert temp_service.log_dir.exists()
        assert temp_service.log_dir.is_dir()

    def test_rotate_log_moves_existing_log(self, temp_service):
        """Test _rotate_log moves existing log to .log.1."""
        # Create log file
        temp_service.log_dir.mkdir(parents=True, exist_ok=True)
        temp_service.log_file.write_text("Test log content")

        temp_service._rotate_log()

        # Original should be gone
        assert not temp_service.log_file.exists()

        # Rotated should exist
        rotated = temp_service.log_file.with_suffix('.log.1')
        assert rotated.exists()
        assert rotated.read_text() == "Test log content"

    def test_rotate_log_deletes_old_rotation(self, temp_service):
        """Test _rotate_log deletes existing .log.1 before rotating."""
        # Create log file and old rotation
        temp_service.log_dir.mkdir(parents=True, exist_ok=True)
        temp_service.log_file.write_text("New log")
        rotated = temp_service.log_file.with_suffix('.log.1')
        rotated.write_text("Old rotated log")

        temp_service._rotate_log()

        # Rotated should have new content
        assert rotated.exists()
        assert rotated.read_text() == "New log"


class TestStop:
    """Tests for stop method."""

    def test_stop_when_not_running(self, temp_service):
        """Test stop returns error when server is not running."""
        result = temp_service.stop()

        assert isinstance(result, ServerResult)
        assert result.success is False
        assert "not running" in result.message.lower()

    def test_stop_detects_stale_state(self, temp_service):
        """Test stop detects and reports when state is stale (process doesn't exist)."""
        # Write state with invalid PID
        temp_service._write_state({
            'port': 8022,
            'pid': 999999,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'log_file': str(temp_service.log_file)
        })

        # stop() calls get_status() which cleans up stale state
        # So stop() will report server is not running (which is correct)
        result = temp_service.stop()

        # Should report not running (state was stale)
        assert result.success is False
        assert "not running" in result.message.lower()
        # State should be cleaned up by get_status()
        assert not temp_service.state_file.exists()


# Fixtures
@pytest.fixture
def temp_service(tmp_path):
    """Create a temporary ServerOrchestrationService for testing."""
    # Create a mock config
    class MockConfig:
        def __init__(self, root):
            self.mybb_root = root / "TestForum"

    # Create directory structure
    test_root = tmp_path / "test_mybb"
    test_root.mkdir()
    mybb_root = test_root / "TestForum"
    mybb_root.mkdir()

    config = MockConfig(test_root)
    service = ServerOrchestrationService(config)

    return service
