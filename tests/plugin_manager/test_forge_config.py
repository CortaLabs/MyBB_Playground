"""
Unit tests for ForgeConfig configuration loader.

Tests YAML+ENV loading with precedence, default values, graceful degradation,
and all public methods/properties.
"""

import pytest
from pathlib import Path
import yaml
from plugin_manager.forge_config import ForgeConfig


class TestForgeConfigDefaults:
    """Test default behavior when no config files exist."""

    def test_defaults_when_no_files(self, tmp_path):
        """ForgeConfig should load with defaults when no config files exist."""
        # Create ForgeConfig pointing to empty directory
        config = ForgeConfig(tmp_path)

        # Verify developer defaults
        assert config.developer_name == "Developer"
        assert config.developer_website == ""
        assert config.developer_email == ""

        # Verify plugin defaults
        assert config.defaults["compatibility"] == "18*"
        assert config.defaults["license"] == "GPL-3.0"
        assert config.defaults["visibility"] == "public"

        # Verify sync defaults
        sync = config.get_sync_settings()
        assert sync["debounce_ms"] == 100
        assert sync["batch_window_ms"] == 100
        assert sync["enable_cache_refresh"] is True

        # Verify no subtrees configured
        assert config.get_subtree_config("plugins/private") is None
        assert config.get_subtree_remote("plugins/private") is None


class TestForgeConfigYAML:
    """Test YAML configuration loading and merging."""

    def test_yaml_merge(self, tmp_path):
        """YAML config should override defaults."""
        # Create YAML config
        yaml_path = tmp_path / ".mybb-forge.yaml"
        yaml_content = {
            "developer": {
                "name": "Test Developer",
                "website": "https://test.example.com",
                "email": "test@example.com"
            },
            "defaults": {
                "compatibility": "19*",
                "license": "MIT"
            },
            "sync": {
                "debounce_ms": 200
            }
        }
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_content, f)

        # Load config
        config = ForgeConfig(tmp_path)

        # Verify YAML overrides
        assert config.developer_name == "Test Developer"
        assert config.developer_website == "https://test.example.com"
        assert config.developer_email == "test@example.com"

        # Verify partial override (compatibility and license changed, visibility default kept)
        assert config.defaults["compatibility"] == "19*"
        assert config.defaults["license"] == "MIT"
        assert config.defaults["visibility"] == "public"  # Default preserved

        # Verify deep merge (debounce_ms changed, other sync settings kept)
        sync = config.get_sync_settings()
        assert sync["debounce_ms"] == 200
        assert sync["batch_window_ms"] == 100  # Default preserved
        assert sync["enable_cache_refresh"] is True  # Default preserved

    def test_yaml_invalid_graceful_degradation(self, tmp_path):
        """Invalid YAML should fall back to defaults."""
        # Create invalid YAML
        yaml_path = tmp_path / ".mybb-forge.yaml"
        with open(yaml_path, 'w') as f:
            f.write("invalid: yaml: syntax: [unclosed")

        # Should not raise exception, should use defaults
        config = ForgeConfig(tmp_path)
        assert config.developer_name == "Developer"


class TestForgeConfigEnv:
    """Test .env file loading."""

    def test_env_loading(self, tmp_path):
        """ENV variables should be accessible."""
        # Create .env file
        env_path = tmp_path / ".mybb-forge.env"
        with open(env_path, 'w') as f:
            f.write("PRIVATE_PLUGINS_REMOTE=git@github.com:test/plugins.git\n")
            f.write("PRIVATE_THEMES_REMOTE=git@github.com:test/themes.git\n")
            f.write("SOME_OTHER_VAR=value123\n")

        # Load config
        config = ForgeConfig(tmp_path)

        # ENV should be loaded
        assert config._env["PRIVATE_PLUGINS_REMOTE"] == "git@github.com:test/plugins.git"
        assert config._env["PRIVATE_THEMES_REMOTE"] == "git@github.com:test/themes.git"
        assert config._env["SOME_OTHER_VAR"] == "value123"

    def test_env_missing_graceful_degradation(self, tmp_path):
        """Missing .env file should not cause errors."""
        # No .env file created
        config = ForgeConfig(tmp_path)

        # Should have empty env dict
        assert config._env == {}


class TestForgeConfigSubtrees:
    """Test subtree configuration and remote resolution."""

    def test_subtree_remote_resolution(self, tmp_path):
        """Subtree remotes should resolve ENV var references."""
        # Create YAML with subtree config
        yaml_path = tmp_path / ".mybb-forge.yaml"
        yaml_content = {
            "subtrees": {
                "plugins/private": {
                    "remote_env": "PRIVATE_PLUGINS_REMOTE",
                    "branch": "main",
                    "squash": True
                },
                "themes/private": {
                    "remote_env": "PRIVATE_THEMES_REMOTE",
                    "branch": "develop",
                    "squash": False
                }
            }
        }
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_content, f)

        # Create .env with remote URLs
        env_path = tmp_path / ".mybb-forge.env"
        with open(env_path, 'w') as f:
            f.write("PRIVATE_PLUGINS_REMOTE=git@github.com:org/plugins.git\n")
            f.write("PRIVATE_THEMES_REMOTE=git@github.com:org/themes.git\n")

        # Load config
        config = ForgeConfig(tmp_path)

        # Verify subtree config accessible
        plugins_config = config.get_subtree_config("plugins/private")
        assert plugins_config is not None
        assert plugins_config["branch"] == "main"
        assert plugins_config["squash"] is True

        themes_config = config.get_subtree_config("themes/private")
        assert themes_config is not None
        assert themes_config["branch"] == "develop"
        assert themes_config["squash"] is False

        # Verify remote resolution via ENV
        plugins_remote = config.get_subtree_remote("plugins/private")
        assert plugins_remote == "git@github.com:org/plugins.git"

        themes_remote = config.get_subtree_remote("themes/private")
        assert themes_remote == "git@github.com:org/themes.git"

    def test_subtree_remote_missing_env_var(self, tmp_path):
        """Subtree remote should return None if ENV var not set."""
        # Create YAML with subtree config
        yaml_path = tmp_path / ".mybb-forge.yaml"
        yaml_content = {
            "subtrees": {
                "plugins/private": {
                    "remote_env": "MISSING_VAR",
                    "branch": "main"
                }
            }
        }
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_content, f)

        # No .env file with MISSING_VAR
        config = ForgeConfig(tmp_path)

        # Should return None for missing env var
        remote = config.get_subtree_remote("plugins/private")
        assert remote is None


class TestForgeConfigProperties:
    """Test all public properties."""

    def test_developer_properties(self, tmp_path):
        """All developer properties should return correct values."""
        # Create YAML with complete developer info
        yaml_path = tmp_path / ".mybb-forge.yaml"
        yaml_content = {
            "developer": {
                "name": "Alice Developer",
                "website": "https://alice.dev",
                "email": "alice@example.com"
            }
        }
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_content, f)

        config = ForgeConfig(tmp_path)

        # Verify all properties
        assert config.developer_name == "Alice Developer"
        assert config.developer_website == "https://alice.dev"
        assert config.developer_email == "alice@example.com"

    def test_defaults_property(self, tmp_path):
        """Defaults property should return plugin defaults dict."""
        # Create YAML with custom defaults
        yaml_path = tmp_path / ".mybb-forge.yaml"
        yaml_content = {
            "defaults": {
                "compatibility": "20*",
                "license": "Apache-2.0",
                "visibility": "private"
            }
        }
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_content, f)

        config = ForgeConfig(tmp_path)

        defaults = config.defaults
        assert defaults["compatibility"] == "20*"
        assert defaults["license"] == "Apache-2.0"
        assert defaults["visibility"] == "private"


class TestForgeConfigSyncSettings:
    """Test sync settings retrieval."""

    def test_sync_settings(self, tmp_path):
        """Sync settings should be accessible via method."""
        # Create YAML with custom sync settings
        yaml_path = tmp_path / ".mybb-forge.yaml"
        yaml_content = {
            "sync": {
                "debounce_ms": 50,
                "batch_window_ms": 75,
                "enable_cache_refresh": False
            }
        }
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_content, f)

        config = ForgeConfig(tmp_path)

        sync = config.get_sync_settings()
        assert sync["debounce_ms"] == 50
        assert sync["batch_window_ms"] == 75
        assert sync["enable_cache_refresh"] is False

    def test_sync_settings_defaults(self, tmp_path):
        """Sync settings should have sensible defaults."""
        # No YAML file
        config = ForgeConfig(tmp_path)

        sync = config.get_sync_settings()
        assert sync["debounce_ms"] == 100
        assert sync["batch_window_ms"] == 100
        assert sync["enable_cache_refresh"] is True
