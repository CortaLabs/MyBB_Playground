"""Configuration for disk synchronization."""

import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SyncConfig:
    """Configuration for MyBB disk sync operations.

    Attributes:
        sync_root: Root directory for synced files
        auto_upload: Enable automatic file watching and sync
        cache_token: Optional authentication token for cache refresh
    """
    sync_root: Path
    auto_upload: bool = True
    cache_token: str = ""

    @classmethod
    def from_env(cls) -> "SyncConfig":
        """Load configuration from environment variables.

        Environment variables:
            MYBB_SYNC_ROOT: Root directory for synced files (default: ./mybb_sync)
            MYBB_AUTO_UPLOAD: Enable auto-sync (default: true)
            MYBB_CACHE_TOKEN: Optional auth token for cache refresh

        Returns:
            SyncConfig instance with values from environment
        """
        sync_root_env = os.getenv("MYBB_SYNC_ROOT")
        if sync_root_env:
            sync_root = Path(sync_root_env)
        else:
            # Default to mybb_sync in current directory
            sync_root = Path.cwd() / "mybb_sync"

        auto_upload = os.getenv("MYBB_AUTO_UPLOAD", "true").lower() in ("true", "1", "yes")
        cache_token = os.getenv("MYBB_CACHE_TOKEN", "")

        return cls(
            sync_root=sync_root,
            auto_upload=auto_upload,
            cache_token=cache_token,
        )
