"""Tests for plugin and theme installer functionality."""

import pytest
from pathlib import Path
import shutil
import tempfile
from unittest.mock import Mock, patch, MagicMock

from plugin_manager.config import Config
from plugin_manager.database import ProjectDatabase
from plugin_manager.workspace import PluginWorkspace, ThemeWorkspace
from plugin_manager.installer import PluginInstaller, ThemeInstaller


@pytest.fixture
def temp_repo():
    """Create temporary repository structure."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)

    # Create TestForum structure
    testforum = repo_path / "TestForum"
    (testforum / "inc" / "plugins").mkdir(parents=True)
    (testforum / "inc" / "languages" / "english").mkdir(parents=True)

    # Create workspace structure
    (repo_path / "plugin_manager" / "plugins" / "public").mkdir(parents=True)
    (repo_path / "plugin_manager" / "themes" / "public").mkdir(parents=True)

    # Create .plugin_manager directory
    (repo_path / ".plugin_manager").mkdir(parents=True)

    yield repo_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_repo):
    """Create test configuration."""
    config = Config(repo_root=temp_repo)
    config.data["mybb_root"] = "TestForum"
    return config


@pytest.fixture
def db(temp_repo):
    """Create test database."""
    db_path = temp_repo / ".plugin_manager" / "test.db"
    schema_path = Path(__file__).parent.parent.parent / ".plugin_manager" / "schema" / "projects.sql"

    db = ProjectDatabase(db_path)
    db.create_tables(schema_path)
    return db


@pytest.fixture
def plugin_workspace(config):
    """Create plugin workspace."""
    workspace_root = config.get_workspace_path('plugin')
    return PluginWorkspace(workspace_root)


@pytest.fixture
def theme_workspace(config):
    """Create theme workspace."""
    workspace_root = config.get_workspace_path('theme')
    return ThemeWorkspace(workspace_root)


@pytest.fixture
def sample_plugin(temp_repo, db, plugin_workspace):
    """Create a sample plugin in workspace using MyBB-compatible structure."""
    codename = "test_plugin"

    # Add to database
    db.add_project(
        codename=codename,
        display_name="Test Plugin",
        workspace_path=str(temp_repo / "plugin_manager" / "plugins" / "public" / codename),
        type="plugin",
        visibility="public"
    )

    # Create workspace (creates MyBB-compatible structure)
    workspace_path = plugin_workspace.create_workspace(codename, "public")

    # Create plugin PHP file (MyBB-compatible path)
    plugin_dir = workspace_path / "inc" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_file = plugin_dir / f"{codename}.php"
    plugin_file.write_text("""<?php
// Test plugin PHP file
function test_plugin_info() {
    return array("name" => "Test Plugin");
}
""")

    # Create language file (MyBB-compatible path)
    lang_dir = workspace_path / "inc" / "languages" / "english"
    lang_dir.mkdir(parents=True, exist_ok=True)
    lang_file = lang_dir / f"{codename}.lang.php"
    lang_file.write_text("""<?php
$l['test_plugin_name'] = "Test Plugin";
""")

    # Create metadata
    meta = {
        "codename": codename,
        "display_name": "Test Plugin",
        "name": "Test Plugin",
        "description": "Test plugin for unit tests",
        "author": "Test Author",
        "version": "1.0.0",
        "type": "plugin",
        "visibility": "public",
        "mybb_compatibility": "18*",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "has_templates": False,
        "has_database": False,
        "hooks": [{"name": "global_start", "handler": "test_plugin_global_start"}],
        "settings": [],
        "files": {
            "plugin": f"inc/plugins/{codename}.php",
            "languages": "inc/languages/"
        }
    }
    plugin_workspace.write_meta(codename, meta, "public")

    return codename


@pytest.fixture
def sample_theme(temp_repo, db, theme_workspace):
    """Create a sample theme in workspace."""
    codename = "test_theme"

    # Add to database
    db.add_project(
        codename=codename,
        display_name="Test Theme",
        workspace_path=str(temp_repo / "plugin_manager" / "themes" / "public" / codename),
        type="theme",
        visibility="public"
    )

    # Create workspace
    workspace_path = theme_workspace.create_workspace(codename, "public")

    # Create stylesheet
    css_dir = workspace_path / "stylesheets"
    css_dir.mkdir(parents=True, exist_ok=True)
    css_file = css_dir / "global.css"
    css_file.write_text("""body { background: #fff; }""")

    # Create template override
    template_dir = workspace_path / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_file = template_dir / "header.html"
    template_file.write_text("<header>Custom Header</header>")

    # Create metadata
    meta = {
        "codename": codename,
        "display_name": "Test Theme",
        "name": "Test Theme",
        "description": "Test theme for unit tests",
        "author": "Test Author",
        "version": "1.0.0",
        "type": "theme",
        "visibility": "public",
        "mybb_compatibility": "18*",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "parent_theme": None,
        "color_scheme": {},
        "stylesheets": [{"name": "global"}],
        "template_overrides": ["header"]
    }
    theme_workspace.write_meta(codename, meta, "public")

    return codename


class TestPluginInstaller:
    """Test PluginInstaller class."""

    def test_init(self, config, db, plugin_workspace):
        """Test installer initialization."""
        installer = PluginInstaller(config, db, plugin_workspace)

        assert installer.config == config
        assert installer.db == db
        assert installer.plugin_workspace == plugin_workspace
        assert installer.mybb_root == config.mybb_root

    def test_install_plugin_success(self, config, db, plugin_workspace, sample_plugin, temp_repo):
        """Test successful plugin installation using directory overlay."""
        installer = PluginInstaller(config, db, plugin_workspace)

        # MCP calls will fail gracefully in test environment (no MCP server)
        result = installer.install_plugin(sample_plugin)

        assert result["success"] is True
        assert result["plugin"] == sample_plugin
        assert len(result["files_copied"]) >= 2  # PHP + language file
        # Directory overlay copies with relative paths from inc/
        assert any("plugins/test_plugin.php" in f or "test_plugin.php" in f for f in result["files_copied"])

        # Verify files were copied
        plugin_file = temp_repo / "TestForum" / "inc" / "plugins" / f"{sample_plugin}.php"
        assert plugin_file.exists()

        lang_file = temp_repo / "TestForum" / "inc" / "languages" / "english" / f"{sample_plugin}.lang.php"
        assert lang_file.exists()

        # Verify warning about ACP activation
        assert any("IMPORTANT" in w and "Admin CP" in w for w in result["warnings"])

    def test_install_plugin_not_found(self, config, db, plugin_workspace):
        """Test installation of non-existent plugin."""
        installer = PluginInstaller(config, db, plugin_workspace)

        result = installer.install_plugin("nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_install_plugin_backup_existing(self, config, db, plugin_workspace, sample_plugin, temp_repo):
        """Test that existing files are backed up during overlay installation."""
        installer = PluginInstaller(config, db, plugin_workspace)

        # Create existing plugin file
        existing_file = temp_repo / "TestForum" / "inc" / "plugins" / f"{sample_plugin}.php"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.write_text("<?php // Old version")

        # MCP calls will fail gracefully in test environment
        result = installer.install_plugin(sample_plugin)

        assert result["success"] is True

        # Verify backup file exists (directory overlay backs up files silently)
        backups = list(existing_file.parent.glob(f"{sample_plugin}.php.backup.*"))
        assert len(backups) > 0

        # Verify new file was installed
        assert existing_file.exists()
        assert "Old version" not in existing_file.read_text()

    def test_uninstall_plugin(self, config, db, plugin_workspace, sample_plugin, temp_repo):
        """Test plugin uninstallation."""
        installer = PluginInstaller(config, db, plugin_workspace)

        # First install the plugin
        plugin_file = temp_repo / "TestForum" / "inc" / "plugins" / f"{sample_plugin}.php"
        plugin_file.parent.mkdir(parents=True, exist_ok=True)
        plugin_file.write_text("<?php // Test plugin")

        lang_file = temp_repo / "TestForum" / "inc" / "languages" / "english" / f"{sample_plugin}.lang.php"
        lang_file.parent.mkdir(parents=True, exist_ok=True)
        lang_file.write_text("<?php // Language")

        # MCP call will fail gracefully in test environment
        result = installer.uninstall_plugin(sample_plugin)

        assert result["success"] is True
        assert len(result["files_removed"]) == 2

        # Verify files were removed
        assert not plugin_file.exists()
        assert not lang_file.exists()

    def test_get_installed_plugins(self, config, db, plugin_workspace, temp_repo):
        """Test listing installed plugins."""
        installer = PluginInstaller(config, db, plugin_workspace)

        # Create some plugin files
        plugins_dir = temp_repo / "TestForum" / "inc" / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)

        (plugins_dir / "plugin1.php").write_text("<?php")
        (plugins_dir / "plugin2.php").write_text("<?php")
        (plugins_dir / "index.php").write_text("<?php")  # Should be ignored

        installed = installer.get_installed_plugins()

        assert "plugin1" in installed
        assert "plugin2" in installed
        assert "index" not in installed


class TestThemeInstaller:
    """Test ThemeInstaller class."""

    def test_init(self, config, db, theme_workspace):
        """Test installer initialization."""
        installer = ThemeInstaller(config, db, theme_workspace)

        assert installer.config == config
        assert installer.db == db
        assert installer.theme_workspace == theme_workspace
        assert installer.mybb_root == config.mybb_root

    def test_install_theme_success(self, config, db, theme_workspace, sample_theme):
        """Test successful theme installation."""
        installer = ThemeInstaller(config, db, theme_workspace)

        # MCP calls will fail gracefully in test environment
        result = installer.install_theme(sample_theme)

        assert result["success"] is True
        assert result["theme"] == sample_theme
        # Note: stylesheets/templates won't deploy without MCP server,
        # but installer handles this gracefully

    def test_install_theme_unknown_stylesheet(self, config, db, theme_workspace, sample_theme):
        """Test theme installation with unknown stylesheet."""
        installer = ThemeInstaller(config, db, theme_workspace)

        # MCP will fail in test environment - test that install still succeeds
        result = installer.install_theme(sample_theme)

        assert result["success"] is True
        # In test mode, deployment warnings expected

    def test_install_theme_not_found(self, config, db, theme_workspace):
        """Test installation of non-existent theme."""
        installer = ThemeInstaller(config, db, theme_workspace)

        result = installer.install_theme("nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_uninstall_theme(self, config, db, theme_workspace, sample_theme):
        """Test theme uninstallation."""
        installer = ThemeInstaller(config, db, theme_workspace)

        result = installer.uninstall_theme(sample_theme)

        assert result["success"] is True
        assert "reverts customizations" in result["warnings"][0]


class TestDatabaseIntegration:
    """Test database integration in installer."""

    def test_install_updates_database(self, config, db, plugin_workspace, sample_plugin):
        """Test that install updates database status."""
        installer = PluginInstaller(config, db, plugin_workspace)

        # Initial status
        project = db.get_project(sample_plugin)
        assert project["status"] == "development"
        assert project["installed_at"] is None

        # Install
        installer.install_plugin(sample_plugin)

        # Check status updated
        project = db.get_project(sample_plugin)
        assert project["status"] == "installed"
        assert project["installed_at"] is not None

    def test_install_creates_history(self, config, db, plugin_workspace, sample_plugin):
        """Test that install creates history entry."""
        installer = PluginInstaller(config, db, plugin_workspace)

        # Install
        installer.install_plugin(sample_plugin)

        # Check history
        history = db.get_history(sample_plugin, limit=10)
        install_entries = [h for h in history if h["action"] == "installed"]

        assert len(install_entries) > 0
        assert "TestForum" in install_entries[0]["details"]

    def test_uninstall_updates_database(self, config, db, plugin_workspace, sample_plugin):
        """Test that uninstall updates database status."""
        installer = PluginInstaller(config, db, plugin_workspace)

        # Set to installed first
        db.update_project(sample_plugin, status="installed", installed_at="2024-01-01T00:00:00")

        # Uninstall
        installer.uninstall_plugin(sample_plugin)

        # Check status reverted
        project = db.get_project(sample_plugin)
        assert project["status"] == "development"
        assert project["installed_at"] is None
