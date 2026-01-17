"""Configuration management for MyBB MCP Server."""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    prefix: str = "mybb_"


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

    db_config = DatabaseConfig(
        host=os.getenv("MYBB_DB_HOST", "localhost"),
        port=int(os.getenv("MYBB_DB_PORT", "3306")),
        database=os.getenv("MYBB_DB_NAME", "mybb_dev"),
        user=os.getenv("MYBB_DB_USER", "mybb_user"),
        password=os.getenv("MYBB_DB_PASS", ""),
        prefix=os.getenv("MYBB_DB_PREFIX", "mybb_"),
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
