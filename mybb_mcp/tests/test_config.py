"""Tests for configuration management."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mybb_mcp.config import ConfigurationError, DatabaseConfig, MyBBConfig, load_config


class TestConfigurationValidation:
    """Test configuration validation and error handling."""

    def test_missing_password_raises_error(self):
        """Test that missing MYBB_DB_PASS raises ConfigurationError."""
        # Mock load_dotenv to prevent .env file loading
        with patch('mybb_mcp.config.load_dotenv'):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ConfigurationError) as exc_info:
                    load_config()

                error_message = str(exc_info.value)
                assert "Database password is required" in error_message
                assert "MYBB_DB_PASS" in error_message
                assert "Example:" in error_message

    def test_empty_password_raises_error(self):
        """Test that empty MYBB_DB_PASS raises ConfigurationError."""
        # Mock load_dotenv to prevent .env file loading
        with patch('mybb_mcp.config.load_dotenv'):
            with patch.dict(os.environ, {"MYBB_DB_PASS": ""}, clear=True):
                with pytest.raises(ConfigurationError) as exc_info:
                    load_config()

                error_message = str(exc_info.value)
                assert "Database password is required" in error_message

    def test_valid_password_succeeds(self):
        """Test that valid MYBB_DB_PASS allows config loading."""
        test_env = {
            "MYBB_DB_PASS": "secure_password_123",
            "MYBB_DB_HOST": "localhost",
            "MYBB_DB_PORT": "3306",
            "MYBB_DB_NAME": "test_db",
            "MYBB_DB_USER": "test_user",
            "MYBB_ROOT": "/tmp/test_mybb",
        }

        # Mock load_dotenv to prevent .env file loading
        with patch('mybb_mcp.config.load_dotenv'):
            with patch.dict(os.environ, test_env, clear=True):
                config = load_config()

                assert config.db.password == "secure_password_123"
                assert config.db.host == "localhost"
                assert config.db.port == 3306
                assert config.db.database == "test_db"
                assert config.db.user == "test_user"

    def test_error_message_is_actionable(self):
        """Test that error message provides clear guidance."""
        # Mock load_dotenv to prevent .env file loading
        with patch('mybb_mcp.config.load_dotenv'):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ConfigurationError) as exc_info:
                    load_config()

                error_message = str(exc_info.value)
                # Check for actionable guidance
                assert "set MYBB_DB_PASS" in error_message
                assert ".env file" in error_message or "environment variables" in error_message


class TestDatabaseConfig:
    """Test DatabaseConfig dataclass."""

    def test_database_config_creation(self):
        """Test DatabaseConfig can be created with all fields."""
        db_config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="mybb",
            user="mybb_user",
            password="secret",
            prefix="mybb_"
        )

        assert db_config.host == "localhost"
        assert db_config.port == 3306
        assert db_config.database == "mybb"
        assert db_config.user == "mybb_user"
        assert db_config.password == "secret"
        assert db_config.prefix == "mybb_"

    def test_database_config_default_prefix(self):
        """Test DatabaseConfig uses default prefix and pool settings."""
        db_config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="mybb",
            user="mybb_user",
            password="secret"
        )

        assert db_config.prefix == "mybb_"
        assert db_config.pool_size == 5
        assert db_config.pool_name == "mybb_pool"


class TestMyBBConfig:
    """Test MyBBConfig dataclass."""

    def test_mybb_config_creation(self):
        """Test MyBBConfig can be created with all fields."""
        db_config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="mybb",
            user="mybb_user",
            password="secret"
        )

        mybb_config = MyBBConfig(
            db=db_config,
            mybb_root=Path("/var/www/mybb"),
            mybb_url="http://localhost:8022",
            port=8022
        )

        assert mybb_config.db == db_config
        assert mybb_config.mybb_root == Path("/var/www/mybb")
        assert mybb_config.mybb_url == "http://localhost:8022"
        assert mybb_config.port == 8022

    def test_mybb_config_default_port(self):
        """Test MyBBConfig uses default port."""
        db_config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="mybb",
            user="mybb_user",
            password="secret"
        )

        mybb_config = MyBBConfig(
            db=db_config,
            mybb_root=Path("/var/www/mybb"),
            mybb_url="http://localhost:8022"
        )

        assert mybb_config.port == 8022
