"""Tests for plugin_manager.config module."""

import json
import tempfile
from pathlib import Path
import pytest

from plugin_manager.config import Config, DEFAULT_CONFIG


class TestConfig:
    """Test Config class functionality."""

    def test_default_config_has_workspaces(self):
        """DEFAULT_CONFIG should have workspaces dict with plugins and themes."""
        assert "workspaces" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["workspaces"]["plugins"] == "plugin_manager/plugins"
        assert DEFAULT_CONFIG["workspaces"]["themes"] == "plugin_manager/themes"

    def test_workspaces_property(self, tmp_path):
        """Config.workspaces should return workspaces dict."""
        config_dir = tmp_path / ".plugin_manager"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({
            "workspaces": {"plugins": "plugins", "themes": "themes"}
        }))

        config = Config(repo_root=tmp_path)
        assert config.workspaces == {"plugins": "plugins", "themes": "themes"}

    def test_workspaces_legacy_fallback(self, tmp_path):
        """Config.workspaces should fall back to workspace_root for legacy configs."""
        config_dir = tmp_path / ".plugin_manager"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({
            "workspace_root": "my_plugins"
        }))

        config = Config(repo_root=tmp_path)
        assert "plugins" in config.workspaces
        assert config.workspaces["plugins"] == "my_plugins"

    def test_get_workspace_path_plugin(self, tmp_path):
        """get_workspace_path('plugin') should return plugins workspace path."""
        config = Config(repo_root=tmp_path)
        path = config.get_workspace_path("plugin")
        assert path == tmp_path / "plugin_manager" / "plugins"

    def test_get_workspace_path_theme(self, tmp_path):
        """get_workspace_path('theme') should return themes workspace path."""
        config = Config(repo_root=tmp_path)
        path = config.get_workspace_path("theme")
        assert path == tmp_path / "plugin_manager" / "themes"

    def test_get_workspace_path_handles_plural(self, tmp_path):
        """get_workspace_path should handle both singular and plural forms."""
        config = Config(repo_root=tmp_path)
        assert config.get_workspace_path("plugin") == config.get_workspace_path("plugins")
        assert config.get_workspace_path("theme") == config.get_workspace_path("themes")

    def test_workspace_root_backward_compatible(self, tmp_path):
        """workspace_root property should still work for backward compatibility."""
        config = Config(repo_root=tmp_path)
        assert config.workspace_root == tmp_path / "plugin_manager" / "plugins"

    def test_get_project_path_plugin(self, tmp_path):
        """get_project_path should return correct path for plugins."""
        config = Config(repo_root=tmp_path)
        path = config.get_project_path("my_plugin", "public", "plugin")
        assert path == tmp_path / "plugin_manager" / "plugins" / "public" / "my_plugin"

    def test_get_project_path_theme(self, tmp_path):
        """get_project_path should return correct path for themes."""
        config = Config(repo_root=tmp_path)
        path = config.get_project_path("my_theme", "private", "theme")
        assert path == tmp_path / "plugin_manager" / "themes" / "private" / "my_theme"

    def test_get_project_path_default_visibility(self, tmp_path):
        """get_project_path should use default visibility when not specified."""
        config = Config(repo_root=tmp_path)
        path = config.get_project_path("test", project_type="plugin")
        assert path == tmp_path / "plugin_manager" / "plugins" / "public" / "test"

    def test_get_project_path_default_type(self, tmp_path):
        """get_project_path should default to plugin type."""
        config = Config(repo_root=tmp_path)
        path = config.get_project_path("test", "public")
        assert path == tmp_path / "plugin_manager" / "plugins" / "public" / "test"
