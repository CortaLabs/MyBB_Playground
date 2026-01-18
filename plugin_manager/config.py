"""Configuration management for Plugin Manager."""

import json
from pathlib import Path
from typing import Dict, Any, Optional


DEFAULT_CONFIG = {
    "workspaces": {
        "plugins": "plugin_manager/plugins",
        "themes": "plugin_manager/themes"
    },
    "database_path": "plugin_manager/projects.db",
    "schema_path": "plugin_manager/schema/projects.sql",
    "mybb_root": "TestForum",
    "default_visibility": "public",
    "default_author": "Developer",
    "default_mybb_compatibility": "18*"
}


class Config:
    """Plugin Manager configuration."""

    def __init__(self, config_path: Optional[str | Path] = None, repo_root: Optional[str | Path] = None):
        """Initialize configuration.

        Args:
            config_path: Path to config.json file. If None, uses default location.
            repo_root: Repository root directory. If None, uses current working directory.
        """
        if repo_root is None:
            self.repo_root = Path.cwd()
        else:
            self.repo_root = Path(repo_root)

        if config_path is None:
            self.config_path = self.repo_root / ".plugin_manager" / "config.json"
        else:
            self.config_path = Path(config_path)

        self.data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults.

        Returns:
            Configuration dictionary
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                # Merge with defaults
                config = DEFAULT_CONFIG.copy()
                config.update(user_config)
                return config
            except Exception:
                # Fall back to defaults if config is invalid
                return DEFAULT_CONFIG.copy()
        else:
            return DEFAULT_CONFIG.copy()

    def save(self) -> None:
        """Save current configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    @property
    def workspaces(self) -> Dict[str, str]:
        """Get workspaces configuration dict.

        Returns:
            Dict mapping workspace type ('plugins', 'themes') to relative path
        """
        # Check if user explicitly set workspace_root (legacy format)
        # Legacy format takes precedence if workspace_root is NOT the default
        if "workspace_root" in self.data:
            # Legacy config detected - use workspace_root for plugins
            return {"plugins": self.data["workspace_root"]}
        # New format with workspaces dict
        if "workspaces" in self.data:
            return self.data["workspaces"]
        # Fallback to defaults
        return DEFAULT_CONFIG["workspaces"]

    def get_workspace_path(self, project_type: str = "plugin") -> Path:
        """Get absolute path to workspace for a project type.

        Args:
            project_type: 'plugin' or 'theme'

        Returns:
            Absolute path to the workspace directory
        """
        # Map project_type to workspace key (handle singular/plural)
        workspace_key = "plugins" if project_type in ("plugin", "plugins") else "themes"
        workspace_relative = self.workspaces.get(workspace_key, workspace_key)
        return self.repo_root / workspace_relative

    @property
    def workspace_root(self) -> Path:
        """Get absolute path to plugins workspace root.

        Note: This property is kept for backward compatibility.
        For new code, use get_workspace_path(project_type) instead.
        """
        return self.get_workspace_path("plugin")

    @property
    def database_path(self) -> Path:
        """Get absolute path to database file."""
        return self.repo_root / self.data["database_path"]

    @property
    def schema_path(self) -> Path:
        """Get absolute path to schema file."""
        return self.repo_root / self.data["schema_path"]

    @property
    def default_visibility(self) -> str:
        """Get default visibility for new projects."""
        return self.data["default_visibility"]

    @property
    def default_author(self) -> str:
        """Get default author name."""
        return self.data["default_author"]

    @property
    def default_mybb_compatibility(self) -> str:
        """Get default MyBB compatibility string."""
        return self.data["default_mybb_compatibility"]

    @property
    def mybb_root(self) -> Path:
        """Get absolute path to MyBB installation root (TestForum)."""
        mybb_root_relative = self.data.get("mybb_root", "TestForum")
        return self.repo_root / mybb_root_relative

    def get_project_path(
        self,
        codename: str,
        visibility: Optional[str] = None,
        project_type: str = "plugin"
    ) -> Path:
        """Get absolute path to a project workspace.

        Args:
            codename: Project codename
            visibility: 'public' or 'private' (uses default if None)
            project_type: 'plugin' or 'theme' (default: 'plugin')

        Returns:
            Absolute path to project directory
        """
        if visibility is None:
            visibility = self.default_visibility

        workspace = self.get_workspace_path(project_type)
        return workspace / visibility / codename

    def __getitem__(self, key: str) -> Any:
        """Dict-like access to config values."""
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-like assignment to config values."""
        self.data[key] = value

    def __contains__(self, key: str) -> bool:
        """Dict-like membership test."""
        return key in self.data
