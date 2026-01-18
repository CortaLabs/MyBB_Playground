"""Tests for database connection pooling and retry logic."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from mysql.connector import Error as MySQLError
from mysql.connector.pooling import MySQLConnectionPool

from mybb_mcp.db.connection import MyBBDatabase
from mybb_mcp.config import DatabaseConfig


@pytest.fixture
def db_config():
    """Create test database configuration."""
    return DatabaseConfig(
        host="localhost",
        port=3306,
        database="test_db",
        user="test_user",
        password="test_pass",
        prefix="mybb_",
        pool_size=3,
        pool_name="test_pool"
    )


@pytest.fixture
def db_config_no_pool():
    """Create test database configuration without pooling."""
    return DatabaseConfig(
        host="localhost",
        port=3306,
        database="test_db",
        user="test_user",
        password="test_pass",
        prefix="mybb_",
        pool_size=1,
        pool_name="test_pool"
    )


class TestConnectionPooling:
    """Test connection pooling functionality."""

    def test_pool_initialization(self, db_config):
        """Test that connection pool is initialized with correct parameters."""
        db = MyBBDatabase(db_config, pool_size=3, pool_name="test_pool")

        assert db._pool_size == 3
        assert db._pool_name == "test_pool"
        assert db._use_pooling is True
        assert db._pool is None  # Pool initialized lazily

    def test_no_pooling_for_single_connection(self, db_config_no_pool):
        """Test that pooling is disabled when pool_size=1."""
        db = MyBBDatabase(db_config_no_pool, pool_size=1)

        assert db._pool_size == 1
        assert db._use_pooling is False

    def test_pool_config_from_database_config(self, db_config):
        """Test that pool configuration is read from DatabaseConfig."""
        db = MyBBDatabase(db_config)

        # Should use config values when not explicitly provided
        assert db._pool_size == 3
        assert db._pool_name == "test_pool"

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    def test_lazy_pool_initialization(self, mock_pool_class, db_config):
        """Test that pool is created lazily on first connection."""
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        db = MyBBDatabase(db_config, pool_size=3)
        assert db._pool is None

        # Initialize pool
        pool = db._init_pool()

        assert db._pool is not None
        assert pool == mock_pool
        mock_pool_class.assert_called_once()

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    def test_pool_initialization_only_once(self, mock_pool_class, db_config):
        """Test that pool is only initialized once."""
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        db = MyBBDatabase(db_config, pool_size=3)

        # Call init_pool multiple times
        pool1 = db._init_pool()
        pool2 = db._init_pool()

        assert pool1 == pool2
        mock_pool_class.assert_called_once()  # Only called once


class TestRetryLogic:
    """Test connection retry logic and exponential backoff."""

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    @patch('mybb_mcp.db.connection.mysql.connector.connect')
    def test_successful_connection_first_attempt(self, mock_connect, mock_pool_class, db_config_no_pool):
        """Test successful connection on first attempt."""
        mock_conn = Mock()
        mock_conn.is_connected.return_value = True
        mock_connect.return_value = mock_conn

        db = MyBBDatabase(db_config_no_pool, pool_size=1)
        conn = db._connect_with_retry()

        assert conn == mock_conn
        assert mock_connect.call_count == 1

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    @patch('mybb_mcp.db.connection.time.sleep')
    @patch('mybb_mcp.db.connection.mysql.connector.connect')
    def test_retry_on_failure(self, mock_connect, mock_sleep, mock_pool_class, db_config_no_pool):
        """Test that connection retries on failure."""
        # First two attempts fail, third succeeds
        mock_conn_fail = Mock()
        mock_conn_fail.is_connected.return_value = False

        mock_conn_success = Mock()
        mock_conn_success.is_connected.return_value = True

        mock_connect.side_effect = [
            MySQLError("Connection refused"),
            MySQLError("Connection refused"),
            mock_conn_success
        ]

        db = MyBBDatabase(db_config_no_pool, pool_size=1)
        conn = db._connect_with_retry()

        assert conn == mock_conn_success
        assert mock_connect.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    @patch('mybb_mcp.db.connection.time.sleep')
    @patch('mybb_mcp.db.connection.mysql.connector.connect')
    def test_exponential_backoff(self, mock_connect, mock_sleep, mock_pool_class, db_config_no_pool):
        """Test exponential backoff delays."""
        mock_connect.side_effect = [
            MySQLError("Connection refused"),
            MySQLError("Connection refused"),
            MySQLError("Connection refused"),
        ]

        db = MyBBDatabase(db_config_no_pool, pool_size=1)

        with pytest.raises(MySQLError):
            db._connect_with_retry()

        # Check sleep delays: 0.5s, 1s (exponential backoff)
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]

        # First retry: 0.5 * (2^0) = 0.5s
        assert sleep_calls[0] == 0.5
        # Second retry: 0.5 * (2^1) = 1s
        assert sleep_calls[1] == 1.0

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    @patch('mybb_mcp.db.connection.mysql.connector.connect')
    def test_max_retries_exceeded(self, mock_connect, mock_pool_class, db_config_no_pool):
        """Test that exception is raised after max retries."""
        mock_connect.side_effect = MySQLError("Connection refused")

        db = MyBBDatabase(db_config_no_pool, pool_size=1)

        with pytest.raises(MySQLError) as exc_info:
            db._connect_with_retry()

        assert "Failed to connect after 3 attempts" in str(exc_info.value)
        assert mock_connect.call_count == 3


class TestConnectionHealth:
    """Test connection health checks."""

    def test_health_check_none_connection(self, db_config_no_pool):
        """Test health check returns False for None connection."""
        db = MyBBDatabase(db_config_no_pool)
        assert db._is_connection_healthy(None) is False

    def test_health_check_disconnected(self, db_config_no_pool):
        """Test health check returns False for disconnected connection."""
        db = MyBBDatabase(db_config_no_pool)

        mock_conn = Mock()
        mock_conn.is_connected.return_value = False

        assert db._is_connection_healthy(mock_conn) is False

    def test_health_check_ping_success(self, db_config_no_pool):
        """Test health check returns True when ping succeeds."""
        db = MyBBDatabase(db_config_no_pool)

        mock_conn = Mock()
        mock_conn.is_connected.return_value = True
        mock_conn.ping.return_value = None  # Ping succeeds

        assert db._is_connection_healthy(mock_conn) is True
        mock_conn.ping.assert_called_once_with(reconnect=False, attempts=1, delay=0)

    def test_health_check_ping_failure(self, db_config_no_pool):
        """Test health check returns False when ping fails."""
        db = MyBBDatabase(db_config_no_pool)

        mock_conn = Mock()
        mock_conn.is_connected.return_value = True
        mock_conn.ping.side_effect = MySQLError("Ping failed")

        assert db._is_connection_healthy(mock_conn) is False


class TestCursorContextManager:
    """Test cursor context manager with pooling."""

    @patch('mybb_mcp.db.connection.mysql.connector.connect')
    def test_cursor_returns_connection_to_pool(self, mock_connect, db_config):
        """Test that pooled connections are returned after cursor use."""
        mock_conn = Mock()
        mock_conn.is_connected.return_value = True
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        # Create pooled connection
        with patch.object(MyBBDatabase, '_init_pool') as mock_init_pool:
            mock_pool = Mock()
            mock_pool.get_connection.return_value = mock_conn
            mock_init_pool.return_value = mock_pool

            db = MyBBDatabase(db_config, pool_size=3)

            # Use cursor context manager
            with db.cursor() as cur:
                assert cur == mock_cursor

            # Verify connection was returned to pool
            mock_conn.close.assert_called_once()

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    @patch('mybb_mcp.db.connection.mysql.connector.connect')
    def test_cursor_commits_on_success(self, mock_connect, mock_pool_class, db_config_no_pool):
        """Test that cursor commits transaction on success."""
        mock_conn = Mock()
        mock_conn.is_connected.return_value = True
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        db = MyBBDatabase(db_config_no_pool, pool_size=1)

        with db.cursor() as cur:
            cur.execute("SELECT 1")

        mock_conn.commit.assert_called_once()

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    @patch('mybb_mcp.db.connection.mysql.connector.connect')
    def test_cursor_rolls_back_on_error(self, mock_connect, mock_pool_class, db_config_no_pool):
        """Test that cursor rolls back transaction on error."""
        mock_conn = Mock()
        mock_conn.is_connected.return_value = True
        mock_cursor = Mock()
        # Make execute raise error when called
        mock_cursor.execute = Mock(side_effect=MySQLError("Query failed"))
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        db = MyBBDatabase(db_config_no_pool, pool_size=1)

        with pytest.raises(MySQLError):
            with db.cursor() as cur:
                cur.execute("BAD QUERY")

        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    @patch('mybb_mcp.db.connection.mysql.connector.connect')
    def test_existing_api_unchanged(self, mock_connect, mock_pool_class, db_config):
        """Test that existing MyBBDatabase API remains unchanged."""
        mock_conn = Mock()
        mock_conn.is_connected.return_value = True
        mock_connect.return_value = mock_conn

        # Old instantiation pattern (no pool params)
        db = MyBBDatabase(db_config)

        # Old methods still work
        assert db.prefix == "mybb_"
        assert db.table("users") == "mybb_users"

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    @patch('mybb_mcp.db.connection.mysql.connector.connect')
    def test_single_connection_mode_works(self, mock_connect, mock_pool_class, db_config_no_pool):
        """Test that single connection mode (no pooling) still works."""
        mock_conn = Mock()
        mock_conn.is_connected.return_value = True
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        db = MyBBDatabase(db_config_no_pool, pool_size=1)

        # Multiple cursor calls should reuse same connection
        with db.cursor():
            pass
        with db.cursor():
            pass

        # Should only connect once (reuse persistent connection)
        assert mock_connect.call_count == 1


class TestConcurrentAccess:
    """Test concurrent database access with pooling."""

    @patch('mybb_mcp.db.connection.MySQLConnectionPool')
    def test_pool_handles_concurrent_requests(self, mock_pool_class, db_config):
        """Test that pool can handle concurrent connection requests."""
        # Create mock pool that returns different connections
        mock_pool = Mock()
        mock_conn1 = Mock()
        mock_conn1.is_connected.return_value = True
        mock_conn2 = Mock()
        mock_conn2.is_connected.return_value = True

        mock_pool.get_connection.side_effect = [mock_conn1, mock_conn2]
        mock_pool_class.return_value = mock_pool

        db = MyBBDatabase(db_config, pool_size=3)

        # Simulate two concurrent connections
        conn1 = db._connect_with_retry()
        conn2 = db._connect_with_retry()

        # Should get two different connections from pool
        assert conn1 != conn2
        assert mock_pool.get_connection.call_count == 2


class TestConfigurationOptions:
    """Test configuration options for pooling."""

    def test_pool_size_configuration(self, db_config):
        """Test that pool size can be configured."""
        db = MyBBDatabase(db_config, pool_size=10)
        assert db._pool_size == 10

    def test_pool_name_configuration(self, db_config):
        """Test that pool name can be configured."""
        db = MyBBDatabase(db_config, pool_name="custom_pool")
        assert db._pool_name == "custom_pool"

    def test_retry_configuration(self, db_config):
        """Test that retry parameters are configurable."""
        db = MyBBDatabase(db_config)

        assert db._max_retries == 3
        assert db._base_retry_delay == 0.5
        assert db._max_retry_delay == 5.0
