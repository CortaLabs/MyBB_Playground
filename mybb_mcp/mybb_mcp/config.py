"""Configuration management for MyBB MCP Server."""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    prefix: str = "mybb_"
    pool_size: int = 10  # Increased to handle concurrent operations
    pool_name: str = "mybb_pool"


@dataclass
class MyBBConfig:
    db: DatabaseConfig
    mybb_root: Path
    mybb_url: str
    port: int = 8022


def load_config(env_path: Path | None = None) -> MyBBConfig:
    """Load configuration from environment variables."""
    if env_path:
        load_dotenv(env_path)
    else:
        # Try to find .env in parent directories
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            env_file = parent / ".env"
            if env_file.exists():
                load_dotenv(env_file)
                break

    # Validate required password is set
    db_password = os.getenv("MYBB_DB_PASS")
    if not db_password:
        raise ConfigurationError(
            "Database password is required but not configured.\n"
            "Please set MYBB_DB_PASS in your .env file or environment variables.\n"
            "Example: MYBB_DB_PASS=your_secure_password"
        )

    db_config = DatabaseConfig(
        host=os.getenv("MYBB_DB_HOST", "localhost"),
        port=int(os.getenv("MYBB_DB_PORT", "3306")),
        database=os.getenv("MYBB_DB_NAME", "mybb_dev"),
        user=os.getenv("MYBB_DB_USER", "mybb_user"),
        password=db_password,
        prefix=os.getenv("MYBB_DB_PREFIX", "mybb_"),
        pool_size=int(os.getenv("MYBB_DB_POOL_SIZE", "10")),
        pool_name=os.getenv("MYBB_DB_POOL_NAME", "mybb_pool"),
    )

    # Find MyBB root
    mybb_root_env = os.getenv("MYBB_ROOT")
    if mybb_root_env:
        mybb_root = Path(mybb_root_env)
    else:
        # Default to TestForum in parent dir
        mybb_root = Path(__file__).parent.parent / "TestForum"

    return MyBBConfig(
        db=db_config,
        mybb_root=mybb_root,
        mybb_url=os.getenv("MYBB_URL", f"http://localhost:{os.getenv('MYBB_PORT', '8022')}"),
        port=int(os.getenv("MYBB_PORT", "8022")),
    )
