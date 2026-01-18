"""Tests for plugin and theme packaging/export functionality."""

import pytest
import zipfile
from pathlib import Path
from plugin_manager.packager import PluginPackager, ThemePackager
from plugin_manager.workspace import PluginWorkspace, ThemeWorkspace
from plugin_manager.database import ProjectDatabase


class TestPluginPackager:
    """Test PluginPackager class."""

    @pytest.fixture
    def workspace_path(self, tmp_path):
        """Return tmp_path for shared use."""
        return tmp_path

    @pytest.fixture
    def plugin_packager(self, workspace_path):
        """Create PluginPackager instance."""
        workspace = PluginWorkspace(workspace_path / "plugins")
        db = ProjectDatabase(workspace_path / "test.db")
        return PluginPackager(workspace, db)

    @pytest.fixture
    def sample_plugin(self, workspace_path):
        """Create a sample plugin workspace for testing."""
        workspace_root = workspace_path / "plugins" / "public"
        workspace_root.mkdir(parents=True)

        plugin_dir = workspace_root / "test_plugin"
        plugin_dir.mkdir()

        # Create meta.json
        import json
        meta = {
            "codename": "test_plugin",
            "display_name": "Test Plugin",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "Test plugin for export",
            "mybb_compatibility": "18*",
            "project_type": "plugin",
            "visibility": "public",
            "hooks": [
                {"name": "index_start", "handler": "test_plugin_index"},
                {"name": "global_start", "handler": "test_plugin_global"}
            ],
            "settings": [
                {"name": "enable_feature", "title": "Enable Feature", "type": "yesno", "description": "Enable test feature"}
            ],
            "features": {
                "templates": True,
                "database": False
            },
            "files": {
                "plugin": "inc/plugins/test_plugin.php",
                "languages": "inc/languages/"
            }
        }

        (plugin_dir / "meta.json").write_text(json.dumps(meta, indent=2))

        # Create plugin PHP file
        php_content = """<?php
/**
 * Test Plugin
 */

function test_plugin_info() {
    return array(
        "name" => "Test Plugin",
        "description" => "Test plugin",
        "version" => "1.0.0",
        "author" => "Test Author"
    );
}

function test_plugin_activate() {
    global $plugins;
    $plugins->add_hook("index_start", "test_plugin_hook");
}
"""
        # Create plugin PHP file (MyBB-compatible path)
        plugin_php_dir = plugin_dir / "inc" / "plugins"
        plugin_php_dir.mkdir(parents=True)
        (plugin_php_dir / "test_plugin.php").write_text(php_content)

        # Create language file (MyBB-compatible path)
        lang_content = """<?php
$l['test_plugin_setting'] = 'Test Setting';
"""
        lang_dir = plugin_dir / "inc" / "languages" / "english"
        lang_dir.mkdir(parents=True)
        (lang_dir / "test_plugin.lang.php").write_text(lang_content)

        # Create jscripts directory (optional)
        jscripts_dir = plugin_dir / "jscripts"
        jscripts_dir.mkdir()

        # Create images directory (optional)
        images_dir = plugin_dir / "images"
        images_dir.mkdir()

        return plugin_dir

    def test_validate_for_export_valid_plugin(self, plugin_packager, sample_plugin):
        """Test validation passes for valid plugin."""
        result = plugin_packager.validate_for_export("test_plugin", "public")

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["meta"] is not None
        assert result["meta"]["codename"] == "test_plugin"

    def test_validate_for_export_missing_workspace(self, plugin_packager):
        """Test validation fails for missing workspace."""
        result = plugin_packager.validate_for_export("nonexistent", "public")

        assert result["valid"] is False
        assert "workspace not found" in result["errors"][0].lower()

    def test_validate_for_export_missing_meta(self, tmp_path):
        """Test validation fails when meta.json is missing."""
        workspace_root = tmp_path / "plugins" / "public"
        workspace_root.mkdir(parents=True)

        plugin_dir = workspace_root / "bad_plugin"
        plugin_dir.mkdir()

        # Create PHP file but no meta.json (MyBB-compatible path)
        plugin_php_dir = plugin_dir / "inc" / "plugins"
        plugin_php_dir.mkdir(parents=True)
        (plugin_php_dir / "bad_plugin.php").write_text("<?php\nfunction bad_plugin_info() {}")

        workspace = PluginWorkspace(tmp_path / "plugins")
        db = ProjectDatabase(tmp_path / "test.db")
        packager = PluginPackager(workspace, db)

        result = packager.validate_for_export("bad_plugin", "public")

        assert result["valid"] is False
        assert "meta.json not found" in result["errors"]

    def test_validate_for_export_missing_php_file(self, tmp_path):
        """Test validation fails when main PHP file is missing."""
        workspace_root = tmp_path / "plugins" / "public"
        workspace_root.mkdir(parents=True)

        plugin_dir = workspace_root / "no_php"
        plugin_dir.mkdir()

        # Create meta.json but no PHP file
        import json
        meta = {
            "codename": "no_php",
            "display_name": "No PHP",
            "version": "1.0.0",
            "author": "Test",
            "project_type": "plugin"
        }
        (plugin_dir / "meta.json").write_text(json.dumps(meta))

        workspace = PluginWorkspace(tmp_path / "plugins")
        db = ProjectDatabase(tmp_path / "test.db")
        packager = PluginPackager(workspace, db)

        result = packager.validate_for_export("no_php", "public")

        assert result["valid"] is False
        assert any("php file not found" in err.lower() for err in result["errors"])

    def test_generate_readme(self, plugin_packager, sample_plugin):
        """Test README generation."""
        import json
        meta = json.loads((sample_plugin / "meta.json").read_text())

        readme = plugin_packager.generate_readme("test_plugin", meta)

        assert "# Test Plugin" in readme
        assert "Test plugin for export" in readme
        assert "**Version:** 1.0.0" in readme
        assert "**Author:** Test Author" in readme
        assert "## Hooks Used" in readme
        assert "index_start" in readme
        assert "## Settings" in readme
        assert "Installation" in readme

    def test_create_plugin_zip(self, plugin_packager, sample_plugin, workspace_path):
        """Test ZIP creation."""
        output_path = workspace_path / "test_plugin-1.0.0.zip"

        result = plugin_packager.create_plugin_zip(
            "test_plugin",
            output_path,
            "public",
            include_tests=False
        )

        assert result["success"] is True
        assert output_path.exists()
        # MyBB-compatible paths in ZIP
        assert "inc/plugins/test_plugin.php" in result["files_included"]
        assert "inc/languages/english/test_plugin.lang.php" in result["files_included"]

        # Verify ZIP structure (MyBB-compatible layout for overlay install)
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "inc/plugins/test_plugin.php" in names
            assert "inc/languages/english/test_plugin.lang.php" in names

    def test_create_plugin_zip_nonexistent(self, plugin_packager, tmp_path):
        """Test ZIP creation fails for nonexistent plugin."""
        output_path = tmp_path / "bad.zip"

        result = plugin_packager.create_plugin_zip(
            "nonexistent",
            output_path,
            "public"
        )

        assert result["success"] is False
        assert "workspace not found" in result.get("error", "").lower()


class TestThemePackager:
    """Test ThemePackager class."""

    @pytest.fixture
    def workspace_path(self, tmp_path):
        """Return tmp_path for shared use."""
        return tmp_path

    @pytest.fixture
    def theme_packager(self, workspace_path):
        """Create ThemePackager instance."""
        workspace = ThemeWorkspace(workspace_path / "themes")
        db = ProjectDatabase(workspace_path / "test.db")
        return ThemePackager(workspace, db)

    @pytest.fixture
    def sample_theme(self, workspace_path):
        """Create a sample theme workspace for testing."""
        workspace_root = workspace_path / "themes" / "public"
        workspace_root.mkdir(parents=True)

        theme_dir = workspace_root / "test_theme"
        theme_dir.mkdir()

        # Create meta.json
        import json
        meta = {
            "codename": "test_theme",
            "display_name": "Test Theme",
            "version": "1.0.0",
            "author": "Theme Author",
            "description": "Test theme for export",
            "mybb_compatibility": "18*",
            "project_type": "theme",
            "visibility": "public",
            "stylesheets": [
                {"name": "global", "attached_to": []},
                {"name": "colors", "attached_to": []}
            ],
            "template_overrides": ["header"],
            "parent_theme": None,
            "color_scheme": {
                "primary": "#007bff",
                "secondary": "#6c757d"
            }
        }

        (theme_dir / "meta.json").write_text(json.dumps(meta, indent=2))

        # Create stylesheets
        stylesheets_dir = theme_dir / "stylesheets"
        stylesheets_dir.mkdir()
        (stylesheets_dir / "global.css").write_text("body { font-family: Arial; }")
        (stylesheets_dir / "colors.css").write_text(":root { --primary: #007bff; }")

        # Create template override
        templates_dir = theme_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "header.html").write_text("<header>Custom Header</header>")

        # Create images
        images_dir = theme_dir / "images"
        images_dir.mkdir()
        (images_dir / "logo.png").write_bytes(b"fake_png_data")

        return theme_dir

    def test_validate_for_export_valid_theme(self, theme_packager, sample_theme):
        """Test validation passes for valid theme."""
        result = theme_packager.validate_for_export("test_theme", "public")

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["meta"] is not None
        assert result["meta"]["codename"] == "test_theme"

    def test_validate_for_export_missing_stylesheets(self, tmp_path):
        """Test validation fails when stylesheets are missing."""
        workspace_root = tmp_path / "themes" / "public"
        workspace_root.mkdir(parents=True)

        theme_dir = workspace_root / "bad_theme"
        theme_dir.mkdir()

        # Create meta.json with stylesheet references but no files
        import json
        meta = {
            "codename": "bad_theme",
            "display_name": "Bad Theme",
            "version": "1.0.0",
            "author": "Test",
            "project_type": "theme",
            "visibility": "public",
            "stylesheets": [{"name": "missing_sheet", "attached_to": []}]
        }
        (theme_dir / "meta.json").write_text(json.dumps(meta))

        workspace = ThemeWorkspace(tmp_path / "themes")
        db = ProjectDatabase(tmp_path / "test.db")
        packager = ThemePackager(workspace, db)

        result = packager.validate_for_export("bad_theme", "public")

        assert result["valid"] is False
        assert any("stylesheet not found" in err.lower() for err in result["errors"])

    def test_validate_for_export_empty_stylesheets(self, tmp_path):
        """Test validation fails when stylesheets array is empty."""
        workspace_root = tmp_path / "themes" / "public"
        workspace_root.mkdir(parents=True)

        theme_dir = workspace_root / "empty_theme"
        theme_dir.mkdir()

        # Create meta.json with empty stylesheets
        import json
        meta = {
            "codename": "empty_theme",
            "display_name": "Empty Theme",
            "version": "1.0.0",
            "author": "Test",
            "project_type": "theme",
            "stylesheets": []
        }
        (theme_dir / "meta.json").write_text(json.dumps(meta))

        workspace = ThemeWorkspace(tmp_path / "themes")
        db = ProjectDatabase(tmp_path / "test.db")
        packager = ThemePackager(workspace, db)

        result = packager.validate_for_export("empty_theme", "public")

        assert result["valid"] is False
        assert any("empty" in err.lower() for err in result["errors"])

    def test_generate_readme(self, theme_packager, sample_theme):
        """Test theme README generation."""
        import json
        meta = json.loads((sample_theme / "meta.json").read_text())

        readme = theme_packager.generate_readme("test_theme", meta)

        assert "# Test Theme" in readme
        assert "Test theme for export" in readme
        assert "**Version:** 1.0.0" in readme
        assert "**Author:** Theme Author" in readme
        assert "## Included Stylesheets" in readme
        assert "global.css" in readme
        assert "colors.css" in readme
        assert "## Template Overrides" in readme
        assert "header.html" in readme
        assert "## Color Scheme" in readme
        assert "Installation" in readme

    def test_create_theme_zip(self, theme_packager, sample_theme, workspace_path):
        """Test theme ZIP creation."""
        output_path = workspace_path / "test_theme-1.0.0.zip"

        result = theme_packager.create_theme_zip(
            "test_theme",
            output_path,
            "public"
        )

        assert result["success"] is True
        assert output_path.exists()
        assert "stylesheets/global.css" in result["files_included"]
        assert "stylesheets/colors.css" in result["files_included"]
        assert "templates/header.html" in result["files_included"]
        assert "images/logo.png" in result["files_included"]

        # Verify ZIP structure
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "stylesheets/global.css" in names
            assert "stylesheets/colors.css" in names
            assert "templates/header.html" in names
            assert "images/logo.png" in names
