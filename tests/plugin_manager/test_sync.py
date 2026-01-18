"""Tests for plugin_manager sync workflow (Phase 4 - Fixed).

Tests the extended sync components in mybb_mcp/mybb_mcp/sync/:
- PathRouter: Extended with workspace path parsing
- DiskSyncService: Extended with sync_plugin/sync_theme methods
- PluginManager sync methods: Integration
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from mybb_mcp.sync.router import PathRouter, ParsedPath
from plugin_manager.manager import PluginManager
from plugin_manager.config import Config
from plugin_manager.database import ProjectDatabase


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory structure."""
    temp_dir = tempfile.mkdtemp()
    workspace_root = Path(temp_dir)

    # Create plugin_manager structure
    plugin_manager = workspace_root / "plugin_manager"
    (plugin_manager / "plugins" / "public").mkdir(parents=True)
    (plugin_manager / "plugins" / "private").mkdir(parents=True)
    (plugin_manager / "themes" / "public").mkdir(parents=True)
    (plugin_manager / "themes" / "private").mkdir(parents=True)

    # Create mybb_sync structure (for original sync tests)
    mybb_sync = workspace_root / "mybb_sync"
    (mybb_sync / "template_sets" / "Default Templates" / "Header Templates").mkdir(parents=True)
    (mybb_sync / "styles" / "Default").mkdir(parents=True)

    # Create a test plugin workspace
    test_plugin = plugin_manager / "plugins" / "public" / "test_plugin"
    (test_plugin / "src").mkdir(parents=True)
    (test_plugin / "templates").mkdir(parents=True)
    (test_plugin / "languages" / "english").mkdir(parents=True)

    # Create a test theme workspace
    test_theme = plugin_manager / "themes" / "public" / "test_theme"
    (test_theme / "stylesheets").mkdir(parents=True)
    (test_theme / "templates").mkdir(parents=True)

    yield workspace_root

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_mybb_root():
    """Create a temporary MyBB root directory."""
    temp_dir = tempfile.mkdtemp()
    mybb_root = Path(temp_dir)

    # Create MyBB plugin/language directories
    (mybb_root / "inc" / "plugins").mkdir(parents=True)
    (mybb_root / "inc" / "languages" / "english").mkdir(parents=True)

    yield mybb_root

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = Mock(spec=ProjectDatabase)
    db.get_project.return_value = {'id': 1, 'codename': 'test_plugin'}
    db.add_history.return_value = 1
    return db


@pytest.fixture
def config(temp_workspace, temp_mybb_root):
    """Create a Config object for testing."""
    config = Config(repo_root=temp_workspace)
    config.data['workspaces'] = {
        'plugins': 'plugin_manager/plugins',
        'themes': 'plugin_manager/themes'
    }
    config.data['mybb_root'] = str(temp_mybb_root)
    return config


# =============================================================================
# Extended PathRouter Tests
# =============================================================================

class TestPathRouterOriginal:
    """Tests for original PathRouter functionality (mybb_sync paths)."""

    def test_parse_template_path(self, temp_workspace):
        """Test parsing original template path."""
        sync_root = temp_workspace / "mybb_sync"
        router = PathRouter(sync_root)

        parsed = router.parse("template_sets/Default Templates/Header Templates/header.html")

        assert parsed.type == "template"
        assert parsed.set_name == "Default Templates"
        assert parsed.group_name == "Header Templates"
        assert parsed.template_name == "header"

    def test_parse_stylesheet_path(self, temp_workspace):
        """Test parsing original stylesheet path."""
        sync_root = temp_workspace / "mybb_sync"
        router = PathRouter(sync_root)

        parsed = router.parse("styles/Default/global.css")

        assert parsed.type == "stylesheet"
        assert parsed.theme_name == "Default"
        assert parsed.stylesheet_name == "global.css"

    def test_parse_unknown_path(self, temp_workspace):
        """Test parsing unknown path returns unknown type."""
        sync_root = temp_workspace / "mybb_sync"
        router = PathRouter(sync_root)

        parsed = router.parse("random/path/file.txt")

        assert parsed.type == "unknown"

    def test_build_template_path(self, temp_workspace):
        """Test building template path."""
        sync_root = temp_workspace / "mybb_sync"
        router = PathRouter(sync_root)

        path = router.build_template_path("Default Templates", "Header Templates", "header")

        expected = sync_root / "template_sets" / "Default Templates" / "Header Templates" / "header.html"
        assert path == expected

    def test_build_stylesheet_path(self, temp_workspace):
        """Test building stylesheet path."""
        sync_root = temp_workspace / "mybb_sync"
        router = PathRouter(sync_root)

        path = router.build_stylesheet_path("Default", "global.css")

        expected = sync_root / "styles" / "Default" / "global.css"
        assert path == expected


class TestPathRouterExtended:
    """Tests for extended PathRouter functionality (plugin_manager workspace paths)."""

    def test_parse_plugin_template(self, temp_workspace):
        """Test parsing plugin template path."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        parsed = router.parse("plugins/public/my_plugin/templates/widget.html")

        assert parsed.type == "plugin_template"
        assert parsed.project_name == "my_plugin"
        assert parsed.visibility == "public"
        assert parsed.file_type == "template"
        assert parsed.template_name == "widget"

    def test_parse_plugin_php(self, temp_workspace):
        """Test parsing plugin PHP file path."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        parsed = router.parse("plugins/private/my_plugin/src/my_plugin.php")

        assert parsed.type == "plugin_php"
        assert parsed.project_name == "my_plugin"
        assert parsed.visibility == "private"
        assert parsed.file_type == "php"

    def test_parse_plugin_language(self, temp_workspace):
        """Test parsing plugin language file path."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        parsed = router.parse("plugins/public/my_plugin/languages/english/my_plugin.lang.php")

        assert parsed.type == "plugin_lang"
        assert parsed.project_name == "my_plugin"
        assert parsed.file_type == "lang"

    def test_parse_theme_stylesheet(self, temp_workspace):
        """Test parsing theme stylesheet path."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        parsed = router.parse("themes/public/my_theme/stylesheets/global.css")

        assert parsed.type == "theme_stylesheet"
        assert parsed.project_name == "my_theme"
        assert parsed.visibility == "public"
        assert parsed.stylesheet_name == "global.css"

    def test_parse_theme_template(self, temp_workspace):
        """Test parsing theme template override path."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        parsed = router.parse("themes/private/my_theme/templates/header.html")

        assert parsed.type == "theme_template"
        assert parsed.project_name == "my_theme"
        assert parsed.visibility == "private"
        assert parsed.template_name == "header"

    def test_parse_invalid_visibility(self, temp_workspace):
        """Test parsing path with invalid visibility returns unknown."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        parsed = router.parse("plugins/invalid/my_plugin/src/file.php")

        assert parsed.type == "unknown"

    def test_build_plugin_template_path(self, temp_workspace):
        """Test building plugin template path."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        path = router.build_plugin_template_path("my_plugin", "public", "widget")

        expected = workspace_root / "plugins" / "public" / "my_plugin" / "templates" / "widget.html"
        assert path == expected

    def test_build_plugin_php_path(self, temp_workspace):
        """Test building plugin PHP path."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        path = router.build_plugin_php_path("my_plugin", "public")

        expected = workspace_root / "plugins" / "public" / "my_plugin" / "src" / "my_plugin.php"
        assert path == expected

    def test_build_plugin_lang_path(self, temp_workspace):
        """Test building plugin language path."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        path = router.build_plugin_lang_path("my_plugin", "private", "english")

        expected = workspace_root / "plugins" / "private" / "my_plugin" / "languages" / "english" / "my_plugin.lang.php"
        assert path == expected

    def test_build_theme_stylesheet_path(self, temp_workspace):
        """Test building theme stylesheet path."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        path = router.build_theme_stylesheet_path("my_theme", "public", "global")

        expected = workspace_root / "themes" / "public" / "my_theme" / "stylesheets" / "global.css"
        assert path == expected

    def test_build_theme_template_path(self, temp_workspace):
        """Test building theme template path."""
        sync_root = temp_workspace / "mybb_sync"
        workspace_root = temp_workspace / "plugin_manager"
        router = PathRouter(sync_root, workspace_root)

        path = router.build_theme_template_path("my_theme", "private", "header")

        expected = workspace_root / "themes" / "private" / "my_theme" / "templates" / "header.html"
        assert path == expected

    def test_build_workspace_path_requires_workspace_root(self, temp_workspace):
        """Test that workspace path builders require workspace_root."""
        sync_root = temp_workspace / "mybb_sync"
        router = PathRouter(sync_root)  # No workspace_root

        with pytest.raises(ValueError, match="workspace_root not configured"):
            router.build_plugin_template_path("my_plugin", "public", "widget")


# =============================================================================
# PluginManager Integration Tests
# =============================================================================

class TestPluginManagerSyncIntegration:
    """Integration tests for PluginManager sync methods."""

    def test_sync_plugin_method_exists(self, config, mock_db, temp_workspace):
        """Test that sync_plugin method exists on PluginManager."""
        # Create necessary directories
        pm_dir = temp_workspace / ".plugin_manager"
        pm_dir.mkdir(parents=True, exist_ok=True)

        # Mock database path
        config.data['database_path'] = str(pm_dir / 'projects.db')

        manager = PluginManager(config)

        assert hasattr(manager, 'sync_plugin')
        assert callable(manager.sync_plugin)

    def test_sync_theme_method_exists(self, config, mock_db, temp_workspace):
        """Test that sync_theme method exists on PluginManager."""
        pm_dir = temp_workspace / ".plugin_manager"
        pm_dir.mkdir(parents=True, exist_ok=True)
        config.data['database_path'] = str(pm_dir / 'projects.db')

        manager = PluginManager(config)

        assert hasattr(manager, 'sync_theme')
        assert callable(manager.sync_theme)

    def test_watcher_methods_exist(self, config, mock_db, temp_workspace):
        """Test that watcher control methods exist on PluginManager."""
        pm_dir = temp_workspace / ".plugin_manager"
        pm_dir.mkdir(parents=True, exist_ok=True)
        config.data['database_path'] = str(pm_dir / 'projects.db')

        manager = PluginManager(config)

        assert hasattr(manager, 'start_watcher')
        assert hasattr(manager, 'stop_watcher')
        assert hasattr(manager, 'get_watcher_status')

    def test_sync_plugin_workspace_not_found(self, config, temp_workspace):
        """Test syncing non-existent plugin returns error."""
        pm_dir = temp_workspace / ".plugin_manager"
        pm_dir.mkdir(parents=True, exist_ok=True)
        config.data['database_path'] = str(pm_dir / 'projects.db')

        manager = PluginManager(config)
        result = manager.sync_plugin('nonexistent_plugin')

        assert result['success'] is False
        assert 'not found' in result['error'].lower()

    def test_sync_theme_workspace_not_found(self, config, temp_workspace):
        """Test syncing non-existent theme returns error."""
        pm_dir = temp_workspace / ".plugin_manager"
        pm_dir.mkdir(parents=True, exist_ok=True)
        config.data['database_path'] = str(pm_dir / 'projects.db')

        manager = PluginManager(config)
        result = manager.sync_theme('nonexistent_theme')

        assert result['success'] is False
        assert 'not found' in result['error'].lower()


# =============================================================================
# ParsedPath Extended Fields Tests
# =============================================================================

class TestParsedPathExtended:
    """Tests for ParsedPath extended fields."""

    def test_parsed_path_original_fields(self):
        """Test ParsedPath original fields."""
        parsed = ParsedPath(
            type="template",
            set_name="Default Templates",
            group_name="Header Templates",
            template_name="header",
            raw_path="template_sets/Default Templates/Header Templates/header.html"
        )

        assert parsed.type == "template"
        assert parsed.set_name == "Default Templates"
        assert parsed.group_name == "Header Templates"
        assert parsed.template_name == "header"
        assert parsed.project_name is None  # Extended field not set

    def test_parsed_path_extended_fields(self):
        """Test ParsedPath extended fields."""
        parsed = ParsedPath(
            type="plugin_template",
            project_name="my_plugin",
            visibility="public",
            file_type="template",
            template_name="widget",
            relative_path="templates/widget.html",
            raw_path="plugins/public/my_plugin/templates/widget.html"
        )

        assert parsed.type == "plugin_template"
        assert parsed.project_name == "my_plugin"
        assert parsed.visibility == "public"
        assert parsed.file_type == "template"
        assert parsed.template_name == "widget"
        assert parsed.relative_path == "templates/widget.html"

    def test_parsed_path_all_extended_types(self):
        """Test all extended path types."""
        types = [
            "plugin_template",
            "plugin_php",
            "plugin_lang",
            "theme_template",
            "theme_stylesheet"
        ]

        for path_type in types:
            parsed = ParsedPath(type=path_type)
            assert parsed.type == path_type
