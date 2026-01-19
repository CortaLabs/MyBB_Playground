"""
MyBB Forge Configuration Loader

Loads configuration from .mybb-forge.yaml and .mybb-forge.env with precedence:
ENV vars > YAML > defaults

Provides developer metadata for plugin auto-filling and subtree remote configuration.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from dotenv import dotenv_values


class ForgeConfig:
    """MyBB Forge configuration loader with precedence handling."""

    def __init__(self, repo_root: Path):
        """
        Initialize ForgeConfig loader.

        Args:
            repo_root: Repository root directory path
        """
        self.repo_root = Path(repo_root)
        self.yaml_path = self.repo_root / ".mybb-forge.yaml"
        self.env_path = self.repo_root / ".mybb-forge.env"
        self._config: Dict[str, Any] = {}
        self._env: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load config with precedence: env vars > yaml > defaults."""
        # 1. Load defaults
        self._config = self._get_defaults()

        # 2. Merge YAML if exists
        if self.yaml_path.exists():
            try:
                with open(self.yaml_path, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f) or {}
                self._deep_merge(self._config, yaml_config)
            except (yaml.YAMLError, IOError) as e:
                # Graceful degradation - use defaults if YAML invalid
                pass

        # 3. Load .env file
        if self.env_path.exists():
            try:
                self._env = dotenv_values(self.env_path)
            except Exception:
                # Graceful degradation - use empty env if loading fails
                self._env = {}

    def _get_defaults(self) -> Dict[str, Any]:
        """
        Return default configuration values.

        Returns:
            Dictionary with default developer info, defaults, subtrees, and sync settings
        """
        return {
            "developer": {
                "name": "Developer",
                "website": "",
                "email": ""
            },
            "defaults": {
                "compatibility": "18*",
                "license": "GPL-3.0",
                "visibility": "public"
            },
            "subtrees": {},
            "sync": {
                "debounce_ms": 100,
                "batch_window_ms": 100,
                "enable_cache_refresh": True
            }
        }

    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> None:
        """
        Recursively merge overlay dict into base dict.

        Args:
            base: Base dictionary to merge into (modified in place)
            overlay: Dictionary with values to overlay onto base
        """
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                # Recursive merge for nested dicts
                self._deep_merge(base[key], value)
            else:
                # Direct override for non-dict values or new keys
                base[key] = value

    # Developer Properties
    @property
    def developer_name(self) -> str:
        """Get developer name from config."""
        return self._config.get("developer", {}).get("name", "Developer")

    @property
    def developer_website(self) -> str:
        """Get developer website from config."""
        return self._config.get("developer", {}).get("website", "")

    @property
    def developer_email(self) -> str:
        """Get developer email from config."""
        return self._config.get("developer", {}).get("email", "")

    # Default Values
    @property
    def defaults(self) -> Dict[str, str]:
        """Get default values for new plugins."""
        return self._config.get("defaults", {})

    # Subtree Configuration Methods
    def get_subtree_remote(self, subtree_key: str) -> Optional[str]:
        """
        Get subtree remote URL, resolving env var reference.

        Args:
            subtree_key: Key in subtrees config (e.g., "plugins/private")

        Returns:
            Remote URL from .env file, or None if not configured
        """
        subtree = self._config.get("subtrees", {}).get(subtree_key, {})
        env_key = subtree.get("remote_env")
        if env_key:
            return self._env.get(env_key)
        return None

    def get_subtree_config(self, prefix: str) -> Optional[Dict[str, Any]]:
        """
        Get subtree configuration by prefix.

        Args:
            prefix: Subtree prefix path (e.g., "plugin_manager/plugins/private")

        Returns:
            Subtree config dict, or None if not found
        """
        return self._config.get("subtrees", {}).get(prefix)

    # Sync Settings
    def get_sync_settings(self) -> Dict[str, Any]:
        """
        Get sync optimization settings.

        Returns:
            Dictionary with debounce_ms, batch_window_ms, enable_cache_refresh
        """
        return self._config.get("sync", {
            "debounce_ms": 100,
            "batch_window_ms": 100,
            "enable_cache_refresh": True
        })
