"""Tests for plugin and theme workspace management."""

import pytest
import json
import shutil
from pathlib import Path
from plugin_manager.workspace import PluginWorkspace, ThemeWorkspace
from plugin_manager.schema import create_default_plugin_meta, create_default_theme_meta


@pytest.fixture
def temp_plugin_workspace(tmp_path):
    """Create temporary plugin workspace for testing."""
    workspace_root = tmp_path / "test_plugins"
    workspace_root.mkdir()
    yield workspace_root
    # Cleanup
    if workspace_root.exists():
        shutil.rmtree(workspace_root)


@pytest.fixture
def temp_theme_workspace(tmp_path):
    """Create temporary theme workspace for testing."""
    workspace_root = tmp_path / "test_themes"
    workspace_root.mkdir()
    yield workspace_root
    # Cleanup
    if workspace_root.exists():
        shutil.rmtree(workspace_root)


class TestPluginWorkspace:
    """Test PluginWorkspace class."""

    def test_init(self, temp_plugin_workspace):
        """Test workspace initialization."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        assert workspace.workspace_root == temp_plugin_workspace
        assert temp_plugin_workspace.exists()

    def test_create_workspace_public(self, temp_plugin_workspace):
        """Test creating public plugin workspace with MyBB-compatible structure."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        path = workspace.create_workspace("test_plugin", "public")

        assert path.exists()
        assert path == temp_plugin_workspace / "public" / "test_plugin"
        # MyBB-compatible directory structure
        assert (path / "inc" / "plugins").exists()
        assert (path / "inc" / "languages" / "english").exists()
        # Optional directories for jscripts and images
        assert (path / "jscripts").exists()
        assert (path / "images").exists()

    def test_create_workspace_private(self, temp_plugin_workspace):
        """Test creating private plugin workspace."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        path = workspace.create_workspace("secret_plugin", "private")

        assert path.exists()
        assert path == temp_plugin_workspace / "private" / "secret_plugin"

    def test_create_workspace_duplicate_fails(self, temp_plugin_workspace):
        """Test that creating duplicate workspace raises error."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        workspace.create_workspace("test_plugin", "public")

        with pytest.raises(ValueError, match="already exists"):
            workspace.create_workspace("test_plugin", "public")

    def test_get_workspace_path(self, temp_plugin_workspace):
        """Test finding workspace path."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        created_path = workspace.create_workspace("test_plugin", "public")

        # Find with visibility
        found_path = workspace.get_workspace_path("test_plugin", "public")
        assert found_path == created_path

        # Find without visibility
        found_path = workspace.get_workspace_path("test_plugin")
        assert found_path == created_path

        # Not found
        not_found = workspace.get_workspace_path("nonexistent")
        assert not_found is None

    def test_write_and_read_meta(self, temp_plugin_workspace):
        """Test writing and reading meta.json."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        workspace.create_workspace("test_plugin", "public")

        meta = create_default_plugin_meta(
            codename="test_plugin",
            display_name="Test Plugin",
            author="Test Author",
            description="Test description"
        )

        # Write meta
        workspace.write_meta("test_plugin", meta, "public")

        # Read meta
        read_meta = workspace.read_meta("test_plugin", "public")
        assert read_meta["codename"] == "test_plugin"
        assert read_meta["display_name"] == "Test Plugin"
        assert read_meta["author"] == "Test Author"
        assert read_meta["project_type"] == "plugin"

    def test_write_invalid_meta_fails(self, temp_plugin_workspace):
        """Test that writing invalid meta raises error."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        workspace.create_workspace("test_plugin", "public")

        invalid_meta = {"invalid": "data"}

        with pytest.raises(ValueError, match="Invalid metadata"):
            workspace.write_meta("test_plugin", invalid_meta, "public")

    def test_validate_workspace_valid(self, temp_plugin_workspace):
        """Test validating a valid workspace."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        path = workspace.create_workspace("test_plugin", "public")

        # Add meta.json and PHP file (MyBB-compatible path)
        meta = create_default_plugin_meta("test_plugin", "Test Plugin", "Author")
        workspace.write_meta("test_plugin", meta, "public")

        php_file = path / "inc" / "plugins" / "test_plugin.php"
        php_file.write_text("<?php // Test plugin", encoding='utf-8')

        errors = workspace.validate_workspace("test_plugin", "public")
        assert len(errors) == 0

    def test_validate_workspace_missing_dirs(self, temp_plugin_workspace):
        """Test validating workspace with missing directories."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        path = workspace.create_workspace("test_plugin", "public")

        # Remove a required directory (inc/plugins)
        shutil.rmtree(path / "inc" / "plugins")

        errors = workspace.validate_workspace("test_plugin", "public")
        assert any("inc/plugins" in err for err in errors)

    def test_validate_workspace_missing_meta(self, temp_plugin_workspace):
        """Test validating workspace without meta.json."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        workspace.create_workspace("test_plugin", "public")

        errors = workspace.validate_workspace("test_plugin", "public")
        assert any("meta.json" in err for err in errors)

    def test_validate_workspace_missing_php(self, temp_plugin_workspace):
        """Test validating workspace without PHP file in inc/plugins/."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        workspace.create_workspace("test_plugin", "public")

        meta = create_default_plugin_meta("test_plugin", "Test Plugin", "Author")
        workspace.write_meta("test_plugin", meta, "public")

        errors = workspace.validate_workspace("test_plugin", "public")
        assert any("PHP file" in err for err in errors) or any("inc/plugins" in err for err in errors)

    def test_list_plugins_empty(self, temp_plugin_workspace):
        """Test listing plugins when none exist."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        plugins = workspace.list_plugins()
        assert len(plugins) == 0

    def test_list_plugins_multiple(self, temp_plugin_workspace):
        """Test listing multiple plugins."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        workspace.create_workspace("plugin1", "public")
        workspace.create_workspace("plugin2", "private")

        # Add meta to one
        meta = create_default_plugin_meta("plugin1", "Plugin One", "Author")
        workspace.write_meta("plugin1", meta, "public")

        plugins = workspace.list_plugins()
        assert len(plugins) == 2

        codenames = [p["codename"] for p in plugins]
        assert "plugin1" in codenames
        assert "plugin2" in codenames

    def test_list_plugins_filter_visibility(self, temp_plugin_workspace):
        """Test listing plugins filtered by visibility."""
        workspace = PluginWorkspace(temp_plugin_workspace)
        workspace.create_workspace("plugin1", "public")
        workspace.create_workspace("plugin2", "private")

        public_plugins = workspace.list_plugins(visibility="public")
        assert len(public_plugins) == 1
        assert public_plugins[0]["codename"] == "plugin1"

        private_plugins = workspace.list_plugins(visibility="private")
        assert len(private_plugins) == 1
        assert private_plugins[0]["codename"] == "plugin2"


class TestThemeWorkspace:
    """Test ThemeWorkspace class."""

    def test_init(self, temp_theme_workspace):
        """Test workspace initialization."""
        workspace = ThemeWorkspace(temp_theme_workspace)
        assert workspace.workspace_root == temp_theme_workspace
        assert temp_theme_workspace.exists()

    def test_create_workspace_structure(self, temp_theme_workspace):
        """Test creating theme workspace structure."""
        workspace = ThemeWorkspace(temp_theme_workspace)
        path = workspace.create_workspace("test_theme", "public")

        assert path.exists()
        assert (path / "stylesheets").exists()
        assert (path / "templates").exists()
        assert (path / "images").exists()

    def test_scaffold_stylesheet_global(self, temp_theme_workspace):
        """Test scaffolding global.css."""
        workspace = ThemeWorkspace(temp_theme_workspace)
        css = workspace.scaffold_stylesheet("global.css")

        assert "Global Styles" in css
        assert "body {" in css
        assert "#header" in css

    def test_scaffold_stylesheet_colors(self, temp_theme_workspace):
        """Test scaffolding colors.css."""
        workspace = ThemeWorkspace(temp_theme_workspace)
        css = workspace.scaffold_stylesheet("colors.css")

        assert "Color Scheme" in css
        assert ":root {" in css
        assert "--primary-color" in css

    def test_scaffold_stylesheet_with_parent(self, temp_theme_workspace):
        """Test scaffolding with parent theme."""
        workspace = ThemeWorkspace(temp_theme_workspace)
        css = workspace.scaffold_stylesheet("global.css", parent_theme="Default")

        assert "Inherits from: Default" in css

    def test_write_and_read_theme_meta(self, temp_theme_workspace):
        """Test writing and reading theme meta.json."""
        workspace = ThemeWorkspace(temp_theme_workspace)
        workspace.create_workspace("test_theme", "public")

        meta = create_default_theme_meta(
            codename="test_theme",
            display_name="Test Theme",
            author="Test Author",
            parent_theme="Default"
        )
        meta["stylesheets"] = [
            {"name": "global.css"},
            {"name": "colors.css"}
        ]

        workspace.write_meta("test_theme", meta, "public")

        read_meta = workspace.read_meta("test_theme", "public")
        assert read_meta["codename"] == "test_theme"
        assert read_meta["project_type"] == "theme"
        assert read_meta["parent_theme"] == "Default"
        assert any(s["name"] == "global.css" for s in read_meta["stylesheets"])

    def test_validate_workspace_valid(self, temp_theme_workspace):
        """Test validating valid theme workspace."""
        workspace = ThemeWorkspace(temp_theme_workspace)
        path = workspace.create_workspace("test_theme", "public")

        # Add meta and CSS
        meta = create_default_theme_meta("test_theme", "Test Theme", "Author")
        meta["stylesheets"] = [{"name": "global.css"}]
        workspace.write_meta("test_theme", meta, "public")

        css_file = path / "stylesheets" / "global.css"
        css_file.write_text("/* CSS */", encoding='utf-8')

        errors = workspace.validate_workspace("test_theme", "public")
        assert len(errors) == 0

    def test_validate_workspace_missing_css(self, temp_theme_workspace):
        """Test validating workspace without CSS files."""
        workspace = ThemeWorkspace(temp_theme_workspace)
        workspace.create_workspace("test_theme", "public")

        meta = create_default_theme_meta("test_theme", "Test Theme", "Author")
        meta["stylesheets"] = [{"name": "global.css"}]
        workspace.write_meta("test_theme", meta, "public")

        errors = workspace.validate_workspace("test_theme", "public")
        assert any("CSS file" in err for err in errors)

    def test_validate_workspace_wrong_type(self, temp_theme_workspace):
        """Test validating workspace with wrong meta type."""
        workspace = ThemeWorkspace(temp_theme_workspace)
        path = workspace.create_workspace("test_theme", "public")

        # Create plugin meta instead of theme meta
        meta = create_default_plugin_meta("test_theme", "Test", "Author")
        (path / "meta.json").write_text(json.dumps(meta, indent=2), encoding='utf-8')

        css_file = path / "stylesheets" / "global.css"
        css_file.write_text("/* CSS */", encoding='utf-8')

        errors = workspace.validate_workspace("test_theme", "public")
        assert any("project_type must be 'theme'" in err for err in errors)

    def test_list_themes(self, temp_theme_workspace):
        """Test listing themes."""
        workspace = ThemeWorkspace(temp_theme_workspace)
        workspace.create_workspace("theme1", "public")
        workspace.create_workspace("theme2", "private")

        meta1 = create_default_theme_meta("theme1", "Theme One", "Author")
        meta1["stylesheets"] = [{"name": "global.css"}]
        workspace.write_meta("theme1", meta1, "public")

        themes = workspace.list_themes()
        assert len(themes) == 2

        # Find theme with meta
        theme_with_meta = next(t for t in themes if t["codename"] == "theme1")
        assert theme_with_meta["display_name"] == "Theme One"
        assert any(s["name"] == "global.css" for s in theme_with_meta["stylesheets"])
