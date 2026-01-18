"""Tests for PluginManager create workflows."""

import pytest
import shutil
from pathlib import Path
from plugin_manager.manager import PluginManager
from plugin_manager.config import Config
from plugin_manager.database import ProjectDatabase


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for testing."""
    workspace_root = tmp_path / "plugin_manager"
    workspace_root.mkdir()

    # Create subdirectories
    (workspace_root / "plugins").mkdir()
    (workspace_root / "themes").mkdir()
    (workspace_root / "db").mkdir()

    yield workspace_root

    # Cleanup
    if workspace_root.exists():
        shutil.rmtree(workspace_root)


@pytest.fixture
def test_config(temp_workspace):
    """Create test configuration."""
    config_data = {
        "workspace": {
            "root": str(temp_workspace),
            "plugin_dir": "plugins",
            "theme_dir": "themes"
        },
        "database": {
            "path": str(temp_workspace / "db" / "test_projects.db")
        },
        "defaults": {
            "author": "Test Author",
            "visibility": "public"
        }
    }

    config = Config(repo_root=temp_workspace)
    config._config = config_data
    return config


@pytest.fixture
def manager(test_config, tmp_path):
    """Create PluginManager instance for testing."""
    mgr = PluginManager(config=test_config)
    # Initialize database tables using actual schema file
    schema_path = Path(__file__).parent.parent.parent / ".plugin_manager" / "schema" / "projects.sql"
    mgr.db.create_tables(schema_path=schema_path)
    return mgr


class TestPluginCreation:
    """Test plugin creation workflow."""

    def test_create_simple_plugin(self, manager):
        """Test creating a simple plugin."""
        result = manager.create_plugin(
            codename="test_plugin",
            display_name="Test Plugin",
            description="A test plugin",
            author="Test Author"
        )

        assert result["success"] is True
        assert "Test Plugin" in result["message"]
        assert result["codename"] == "test_plugin"
        assert "workspace_path" in result
        assert "project_id" in result

        # Verify workspace exists with MyBB-compatible structure
        workspace_path = Path(result["workspace_path"])
        assert workspace_path.exists()
        assert (workspace_path / "inc" / "plugins").exists()
        assert (workspace_path / "meta.json").exists()

    def test_create_plugin_with_hooks(self, manager):
        """Test creating plugin with hooks."""
        result = manager.create_plugin(
            codename="hooked_plugin",
            display_name="Hooked Plugin",
            hooks=[{"name": "index_start"}, {"name": "postbit"}]
        )

        assert result["success"] is True

        # Verify PHP file contains hooks (MyBB-compatible path)
        workspace_path = Path(result["workspace_path"])
        php_file = workspace_path / "inc" / "plugins" / "hooked_plugin.php"
        php_content = php_file.read_text()

        assert "add_hook('index_start'" in php_content
        assert "add_hook('postbit'" in php_content
        assert "function hooked_plugin_index_start" in php_content

    def test_create_plugin_with_database(self, manager):
        """Test creating plugin with database support."""
        result = manager.create_plugin(
            codename="db_plugin",
            display_name="Database Plugin",
            has_database=True
        )

        assert result["success"] is True

        # Verify PHP contains database code (MyBB-compatible path)
        workspace_path = Path(result["workspace_path"])
        php_file = workspace_path / "inc" / "plugins" / "db_plugin.php"
        php_content = php_file.read_text()

        assert "CREATE TABLE" in php_content
        assert "db_plugin_data" in php_content
        assert "table_exists" in php_content

    def test_create_plugin_with_templates(self, manager):
        """Test creating plugin with template support."""
        result = manager.create_plugin(
            codename="template_plugin",
            display_name="Template Plugin",
            has_templates=True
        )

        assert result["success"] is True

        # Verify PHP contains template code (MyBB-compatible path)
        workspace_path = Path(result["workspace_path"])
        php_file = workspace_path / "inc" / "plugins" / "template_plugin.php"
        php_content = php_file.read_text()

        assert "$templatelist" in php_content
        assert "template_plugin_main" in php_content

    def test_create_plugin_generates_readme(self, manager):
        """Test that README.md is generated."""
        result = manager.create_plugin(
            codename="readme_test",
            display_name="README Test",
            description="Test README generation"
        )

        workspace_path = Path(result["workspace_path"])
        readme = workspace_path / "README.md"

        assert readme.exists()
        readme_content = readme.read_text()
        assert "README Test" in readme_content
        assert "readme_test" in readme_content
        assert "Test README generation" in readme_content

    def test_create_plugin_generates_lang_file(self, manager):
        """Test that language file is generated."""
        result = manager.create_plugin(
            codename="lang_test",
            display_name="Language Test"
        )

        workspace_path = Path(result["workspace_path"])
        lang_file = workspace_path / "inc" / "languages" / "english" / "lang_test.lang.php"

        assert lang_file.exists()
        lang_content = lang_file.read_text()
        assert "$l['lang_test_name']" in lang_content

    def test_create_plugin_registers_in_database(self, manager):
        """Test that plugin is registered in database."""
        result = manager.create_plugin(
            codename="db_test",
            display_name="Database Test",
            description="Test DB registration",
            version="2.0.0"
        )

        # Query database
        project = manager.db.get_project("db_test")
        assert project is not None
        assert project["display_name"] == "Database Test"
        assert project["type"] == "plugin"
        assert project["version"] == "2.0.0"
        assert project["status"] == "development"

    def test_create_plugin_adds_history(self, manager):
        """Test that history entry is created."""
        result = manager.create_plugin(
            codename="history_test",
            display_name="History Test",
            hooks=["index_start", "postbit"]
        )

        project_id = result["project_id"]
        history = manager.db.get_history(codename="history_test")

        assert len(history) > 0
        assert history[0]["action"] == "created"
        # Details contains JSON with version and visibility
        assert "version" in history[0]["details"]

    def test_create_plugin_private_visibility(self, manager):
        """Test creating private plugin."""
        result = manager.create_plugin(
            codename="private_test",
            display_name="Private Test",
            visibility="private"
        )

        workspace_path = Path(result["workspace_path"])
        assert "private" in str(workspace_path)

    def test_create_plugin_custom_compatibility(self, manager):
        """Test creating plugin with custom MyBB compatibility."""
        result = manager.create_plugin(
            codename="compat_test",
            display_name="Compatibility Test",
            mybb_compatibility="19*"
        )

        workspace_path = Path(result["workspace_path"])
        php_file = workspace_path / "inc" / "plugins" / "compat_test.php"
        php_content = php_file.read_text()

        assert "'compatibility' => '19*'" in php_content

    def test_create_plugin_rollback_on_error(self, manager, test_config):
        """Test that workspace is cleaned up on error."""
        # This should fail during meta validation (if we could force an error)
        # For now, test that duplicate codename prevents creation

        manager.create_plugin(
            codename="duplicate_test",
            display_name="First Plugin"
        )

        # Try to create again with same codename
        with pytest.raises((ValueError, Exception)):
            manager.create_plugin(
                codename="duplicate_test",
                display_name="Second Plugin"
            )

    def test_create_plugin_files_created_list(self, manager):
        """Test that files_created list is accurate."""
        result = manager.create_plugin(
            codename="files_test",
            display_name="Files Test"
        )

        files_created = result["files_created"]
        assert len(files_created) > 0

        # Verify all files exist
        for file_path in files_created:
            assert Path(file_path).exists()


class TestThemeCreation:
    """Test theme creation workflow."""

    def test_create_simple_theme(self, manager):
        """Test creating a simple theme."""
        result = manager.create_theme(
            codename="test_theme",
            display_name="Test Theme",
            description="A test theme"
        )

        assert result["success"] is True
        assert "Test Theme" in result["message"]
        assert result["codename"] == "test_theme"

        # Verify workspace exists
        workspace_path = Path(result["workspace_path"])
        assert workspace_path.exists()
        assert (workspace_path / "stylesheets").exists()
        assert (workspace_path / "templates").exists()
        assert (workspace_path / "images").exists()

    def test_create_theme_generates_css(self, manager):
        """Test that CSS files are generated."""
        result = manager.create_theme(
            codename="css_theme",
            display_name="CSS Theme",
            stylesheets=["global.css", "colors.css"]  # Manager converts to objects
        )

        workspace_path = Path(result["workspace_path"])
        global_css = workspace_path / "stylesheets" / "global.css"
        colors_css = workspace_path / "stylesheets" / "colors.css"

        assert global_css.exists()
        assert colors_css.exists()

        # Verify content
        global_content = global_css.read_text()
        assert "Global Styles" in global_content

        colors_content = colors_css.read_text()
        assert ":root" in colors_content
        assert "--primary-color" in colors_content

    def test_create_theme_with_parent(self, manager):
        """Test creating theme with parent theme."""
        # Note: This will use mock validation from mcp_client
        result = manager.create_theme(
            codename="child_theme",
            display_name="Child Theme",
            parent_theme="Default Theme"
        )

        assert result["success"] is True

        # Verify meta.json has parent
        workspace_path = Path(result["workspace_path"])
        meta = manager.theme_workspace.read_meta("child_theme")
        assert meta["parent_theme"] == "Default Theme"

        # Verify CSS has parent comment
        css_file = workspace_path / "stylesheets" / "global.css"
        css_content = css_file.read_text()
        assert "Inherits from: Default Theme" in css_content

    def test_create_theme_generates_readme(self, manager):
        """Test that theme README is generated."""
        result = manager.create_theme(
            codename="readme_theme",
            display_name="README Theme",
            stylesheets=["global.css", "custom.css"]
        )

        workspace_path = Path(result["workspace_path"])
        readme = workspace_path / "README.md"

        assert readme.exists()
        readme_content = readme.read_text()
        assert "README Theme" in readme_content
        assert "global.css" in readme_content
        assert "custom.css" in readme_content

    def test_create_theme_registers_in_database(self, manager):
        """Test that theme is registered in database."""
        result = manager.create_theme(
            codename="db_theme",
            display_name="Database Theme",
            version="1.5.0"
        )

        project = manager.db.get_project("db_theme")
        assert project is not None
        assert project["display_name"] == "Database Theme"
        assert project["type"] == "theme"
        assert project["version"] == "1.5.0"

    def test_create_theme_adds_history(self, manager):
        """Test that theme creation is logged in history."""
        result = manager.create_theme(
            codename="history_theme",
            display_name="History Theme",
            stylesheets=["global.css", "colors.css", "layout.css"]
        )

        history = manager.db.get_history(codename="history_theme")
        assert len(history) > 0
        assert history[0]["action"] == "created"
        # Details contains JSON with version and visibility
        assert "version" in history[0]["details"]

    def test_create_theme_private_visibility(self, manager):
        """Test creating private theme."""
        result = manager.create_theme(
            codename="private_theme",
            display_name="Private Theme",
            visibility="private"
        )

        workspace_path = Path(result["workspace_path"])
        assert "private" in str(workspace_path)

    def test_create_theme_with_color_scheme(self, manager):
        """Test creating theme with color scheme."""
        result = manager.create_theme(
            codename="color_theme",
            display_name="Color Theme",
            color_scheme={
                "primary": "#0066cc",
                "secondary": "#f0f0f0"
            }
        )

        meta = manager.theme_workspace.read_meta("color_theme")
        assert "color_scheme" in meta
        assert meta["color_scheme"]["primary"] == "#0066cc"

    def test_create_theme_with_template_overrides(self, manager):
        """Test creating theme with template overrides."""
        result = manager.create_theme(
            codename="override_theme",
            display_name="Override Theme",
            template_overrides=["header", "footer", "index"]
        )

        meta = manager.theme_workspace.read_meta("override_theme")
        assert "template_overrides" in meta
        assert "header" in meta["template_overrides"]
        assert len(meta["template_overrides"]) == 3

    def test_create_theme_files_created_list(self, manager):
        """Test that files_created list includes all CSS files."""
        result = manager.create_theme(
            codename="files_theme",
            display_name="Files Theme",
            stylesheets=["global.css", "colors.css"]  # Manager converts to objects
        )

        files_created = result["files_created"]

        # Should include at least 2 CSS files, README, and meta.json
        assert len(files_created) >= 4

        # Verify all files exist
        for file_path in files_created:
            assert Path(file_path).exists()


class TestManagerValidation:
    """Test validation and error handling."""

    def test_create_plugin_empty_codename_fails(self, manager):
        """Test that empty codename raises error."""
        with pytest.raises(Exception):
            manager.create_plugin(
                codename="",
                display_name="Test"
            )

    def test_create_theme_invalid_parent_fails(self, manager):
        """Test that invalid parent theme raises error."""
        # Mock will return False for unknown themes
        with pytest.raises(ValueError, match="Parent theme not found"):
            manager.create_theme(
                codename="bad_theme",
                display_name="Bad Theme",
                parent_theme="NonexistentTheme123"
            )


class TestPluginExport:
    """Test plugin export functionality."""

    def test_export_plugin_success(self, manager):
        """Test successful plugin export."""
        # Create a plugin first
        result = manager.create_plugin(
            codename="export_test",
            display_name="Export Test Plugin",
            description="Plugin for export testing",
            author="Test Author",
            version="1.2.0"
        )
        assert result["success"]

        # Export it
        export_result = manager.export_plugin("export_test")

        assert export_result["success"]
        assert export_result["zip_path"] is not None
        assert "export_test-1.2.0.zip" in export_result["zip_path"]
        assert export_result["readme_generated"]
        assert len(export_result["files_included"]) > 0
        # MyBB-compatible path in ZIP
        assert "inc/plugins/export_test.php" in export_result["files_included"]

    def test_export_plugin_validation_fails(self, manager):
        """Test export fails when validation fails."""
        # Try to export nonexistent plugin
        export_result = manager.export_plugin("nonexistent_plugin")

        assert export_result["success"] is False
        assert "errors" in export_result
        assert len(export_result["errors"]) > 0

    def test_export_plugin_creates_readme(self, manager):
        """Test export generates README in workspace."""
        # Create plugin
        manager.create_plugin(
            codename="readme_test",
            display_name="README Test",
            description="Test README generation"
        )

        # Export
        manager.export_plugin("readme_test")

        # Check README was created
        workspace_path = manager.plugin_workspace.get_workspace_path("readme_test")
        readme_path = workspace_path / "README.md"
        assert readme_path.exists()

        readme_content = readme_path.read_text()
        assert "# README Test" in readme_content
        assert "Installation" in readme_content

    def test_export_plugin_custom_output_dir(self, manager, tmp_path):
        """Test export to custom output directory."""
        # Create plugin
        manager.create_plugin(
            codename="custom_dir",
            display_name="Custom Dir Test"
        )

        # Export to custom location
        custom_output = tmp_path / "custom_exports"
        export_result = manager.export_plugin("custom_dir", output_dir=custom_output)

        assert export_result["success"]
        assert custom_output.exists()
        assert (custom_output / "custom_dir-1.0.0.zip").exists()

    def test_validate_plugin_success(self, manager):
        """Test plugin validation."""
        # Create plugin
        manager.create_plugin(
            codename="validate_test",
            display_name="Validate Test"
        )

        # Validate
        validation = manager.validate_plugin("validate_test")

        assert validation["valid"]
        assert len(validation["errors"]) == 0
        assert validation["meta"] is not None

    def test_validate_plugin_missing(self, manager):
        """Test validation of nonexistent plugin."""
        validation = manager.validate_plugin("missing_plugin")

        assert not validation["valid"]
        assert len(validation["errors"]) > 0


class TestThemeExport:
    """Test theme export functionality."""

    def test_export_theme_success(self, manager):
        """Test successful theme export."""
        # Create a theme first
        result = manager.create_theme(
            codename="export_theme",
            display_name="Export Test Theme",
            description="Theme for export testing",
            author="Theme Author",
            version="2.0.0",
            stylesheets=["global", "colors"]
        )
        assert result["success"]

        # Export it
        export_result = manager.export_theme("export_theme")

        assert export_result["success"]
        assert export_result["zip_path"] is not None
        assert "export_theme-2.0.0.zip" in export_result["zip_path"]
        assert export_result["readme_generated"]
        assert len(export_result["files_included"]) > 0
        # Check for stylesheets
        assert any("stylesheets/" in f for f in export_result["files_included"])

    def test_export_theme_validation_fails(self, manager):
        """Test theme export fails when validation fails."""
        # Try to export nonexistent theme
        export_result = manager.export_theme("nonexistent_theme")

        assert export_result["success"] is False
        assert "errors" in export_result

    def test_export_theme_creates_readme(self, manager):
        """Test theme export generates README."""
        # Create theme
        manager.create_theme(
            codename="theme_readme",
            display_name="Theme README Test",
            description="Test theme README",
            stylesheets=["main"]
        )

        # Export
        manager.export_theme("theme_readme")

        # Check README
        workspace_path = manager.theme_workspace.get_workspace_path("theme_readme")
        readme_path = workspace_path / "README.md"
        assert readme_path.exists()

        readme_content = readme_path.read_text()
        assert "# Theme README Test" in readme_content
        assert "Stylesheets" in readme_content
        assert "main.css" in readme_content

    def test_export_theme_custom_output_dir(self, manager, tmp_path):
        """Test theme export to custom directory."""
        # Create theme
        manager.create_theme(
            codename="custom_theme",
            display_name="Custom Theme",
            stylesheets=["custom"]
        )

        # Export to custom location
        custom_output = tmp_path / "theme_exports"
        export_result = manager.export_theme("custom_theme", output_dir=custom_output)

        assert export_result["success"]
        assert custom_output.exists()
        assert (custom_output / "custom_theme-1.0.0.zip").exists()

    def test_validate_theme_success(self, manager):
        """Test theme validation."""
        # Create theme
        manager.create_theme(
            codename="valid_theme",
            display_name="Valid Theme",
            stylesheets=["test"]
        )

        # Validate
        validation = manager.validate_theme("valid_theme")

        assert validation["valid"]
        assert len(validation["errors"]) == 0
        assert validation["meta"] is not None

    def test_validate_theme_missing(self, manager):
        """Test validation of nonexistent theme."""
        validation = manager.validate_theme("missing_theme")

        assert not validation["valid"]
        assert len(validation["errors"]) > 0
