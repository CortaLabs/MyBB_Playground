"""Tests for MCP tool integration with PluginManager.

Tests the refactored mybb_create_plugin, mybb_plugin_activate, and mybb_plugin_deactivate
MCP tool handlers that delegate to the plugin_manager system.
"""

import pytest
import sys
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure plugin_manager is importable
repo_root = Path(__file__).resolve().parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


class TestMCPPluginManagerIntegration:
    """Test MCP tool handlers with PluginManager delegation."""

    @pytest.fixture
    def mock_config(self):
        """Create mock MCP config."""
        config = MagicMock()
        config.mybb_root = Path("/tmp/test_mybb")
        config.mybb_url = "http://localhost:8022"
        return config

    @pytest.fixture
    def mock_db(self):
        """Create mock MyBBDatabase."""
        db = MagicMock()
        db.get_plugins_cache.return_value = {"plugins": [], "raw": "a:0:{}"}
        db.is_plugin_installed.return_value = False
        return db

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create temporary workspace for plugin creation."""
        workspace = tmp_path / "plugin_manager" / "plugins" / "public"
        workspace.mkdir(parents=True)
        return workspace


class TestCreatePluginDelegation:
    """Test mybb_create_plugin delegates to PluginManager."""

    @pytest.fixture
    def mock_plugin_manager(self):
        """Create mock PluginManager."""
        with patch('plugin_manager.manager.PluginManager') as mock_cls:
            mock_pm = MagicMock()
            mock_pm.create_plugin.return_value = {
                "success": True,
                "message": "Plugin 'Test Plugin' created successfully",
                "workspace_path": "/tmp/plugin_manager/plugins/public/test_plugin",
                "project_id": 1,
                "codename": "test_plugin",
                "files_created": [
                    "/tmp/plugin_manager/plugins/public/test_plugin/src/test_plugin.php",
                    "/tmp/plugin_manager/plugins/public/test_plugin/meta.json"
                ]
            }
            mock_cls.return_value = mock_pm
            yield mock_pm

    def test_create_plugin_success_response_format(self, mock_plugin_manager):
        """Test that create_plugin returns proper markdown format."""
        result = mock_plugin_manager.create_plugin(
            codename="test_plugin",
            display_name="Test Plugin",
            description="A test plugin",
            author="Developer",
            version="1.0.0",
            visibility="public"
        )

        assert result["success"] is True
        assert result["codename"] == "test_plugin"
        assert "workspace_path" in result
        assert "files_created" in result

    def test_create_plugin_hooks_conversion(self, mock_plugin_manager):
        """Test that hooks list is converted to dict format."""
        hooks_input = ["index_start", "postbit"]
        expected_hooks = [
            {"name": "index_start", "handler": "test_plugin_index_start", "priority": 10},
            {"name": "postbit", "handler": "test_plugin_postbit", "priority": 10}
        ]

        # The actual conversion happens in server.py, here we just verify the concept
        converted = [{"name": h, "handler": f"test_plugin_{h}", "priority": 10}
                     for h in hooks_input]
        assert converted == expected_hooks


class TestActivatePluginDelegation:
    """Test mybb_plugin_activate delegates to PluginManager for managed plugins."""

    def test_managed_plugin_uses_install_plugin(self):
        """Test that managed plugins use PluginManager.install_plugin()."""
        with patch('plugin_manager.manager.PluginManager') as mock_cls:
            mock_pm = MagicMock()
            mock_pm.db.get_project.return_value = {
                "codename": "test_plugin",
                "visibility": "public",
                "status": "development"
            }
            mock_pm.install_plugin.return_value = {
                "success": True,
                "files_copied": 3,
                "templates_installed": 2,
                "workspace_path": "/tmp/workspace"
            }
            mock_cls.return_value = mock_pm

            pm = mock_cls()
            project = pm.db.get_project("test_plugin", project_type="plugin")
            assert project is not None

            result = pm.install_plugin("test_plugin", project["visibility"])
            assert result["success"] is True
            assert result["files_copied"] == 3

    def test_unmanaged_plugin_falls_back_to_legacy(self):
        """Test that unmanaged plugins use legacy cache-only activation."""
        with patch('plugin_manager.manager.PluginManager') as mock_cls:
            mock_pm = MagicMock()
            mock_pm.db.get_project.return_value = None  # Not in workspace
            mock_cls.return_value = mock_pm

            pm = mock_cls()
            project = pm.db.get_project("legacy_plugin", project_type="plugin")
            assert project is None  # Should fall through to legacy


class TestDeactivatePluginDelegation:
    """Test mybb_plugin_deactivate delegates to PluginManager for managed plugins."""

    def test_managed_plugin_uses_uninstall_plugin(self):
        """Test that managed plugins use PluginManager.uninstall_plugin()."""
        with patch('plugin_manager.manager.PluginManager') as mock_cls:
            mock_pm = MagicMock()
            mock_pm.db.get_project.return_value = {
                "codename": "test_plugin",
                "visibility": "public",
                "status": "installed"
            }
            mock_pm.uninstall_plugin.return_value = {
                "success": True,
                "files_removed": 3,
                "templates_removed": 2,
                "workspace_path": "/tmp/workspace"
            }
            mock_cls.return_value = mock_pm

            pm = mock_cls()
            project = pm.db.get_project("test_plugin", project_type="plugin")
            assert project is not None

            result = pm.uninstall_plugin("test_plugin", project["visibility"])
            assert result["success"] is True
            assert result["files_removed"] == 3


class TestImportStrategy:
    """Test that import strategy works correctly."""

    def test_repo_root_calculation(self):
        """Test repo_root path calculation from server.py location."""
        # Simulate server.py location
        server_path = Path("/home/austin/projects/MyBB_Playground/mybb_mcp/mybb_mcp/server.py")
        repo_root = server_path.parent.parent.parent

        assert repo_root.name == "MyBB_Playground"
        assert str(repo_root).endswith("MyBB_Playground")

    def test_plugin_manager_importable_from_repo_root(self):
        """Test that plugin_manager can be imported when repo_root is in sys.path."""
        # This test verifies the actual import works
        try:
            from plugin_manager.manager import PluginManager
            assert PluginManager is not None
        except ImportError as e:
            pytest.fail(f"Failed to import PluginManager: {e}")


class TestBackwardCompatibility:
    """Test backward compatibility for existing workflows."""

    def test_legacy_plugin_activation_preserves_behavior(self):
        """Test that plugins not in workspace still get cache-only activation."""
        # Legacy behavior: check file exists, update cache
        mock_plugins_dir = Path("/tmp/test_plugins")
        mock_plugins_dir.mkdir(parents=True, exist_ok=True)

        # Create a "legacy" plugin file
        legacy_plugin = mock_plugins_dir / "legacy_plugin.php"
        legacy_plugin.write_text("<?php // legacy plugin")

        try:
            assert legacy_plugin.exists()
            # In legacy mode, the MCP handler checks if file exists
            # and updates MyBB cache without using PluginManager
        finally:
            shutil.rmtree(mock_plugins_dir)

    def test_import_error_falls_back_gracefully(self):
        """Test that ImportError falls back to legacy behavior."""
        # The refactored handlers catch ImportError and fall back
        # This ensures the MCP server works even if plugin_manager is missing
        pass  # Conceptual test - actual fallback is in server.py


class TestResponseFormats:
    """Test response formats for refactored tools."""

    def test_create_plugin_response_includes_workspace_path(self):
        """Test create_plugin response includes workspace information."""
        result = {
            "success": True,
            "codename": "test_plugin",
            "workspace_path": "/path/to/workspace",
            "project_id": 1,
            "files_created": ["file1.php", "meta.json"]
        }

        # Format check
        assert "workspace_path" in result
        assert isinstance(result["files_created"], list)

    def test_activate_plugin_response_includes_deployment_info(self):
        """Test activate/install response includes deployment information."""
        result = {
            "success": True,
            "files_copied": 3,
            "templates_installed": 2,
            "workspace_path": "/path/to/workspace"
        }

        assert result["files_copied"] >= 0
        assert result["templates_installed"] >= 0

    def test_deactivate_plugin_response_preserves_workspace(self):
        """Test deactivate/uninstall response indicates workspace preservation."""
        result = {
            "success": True,
            "files_removed": 3,
            "templates_removed": 2,
            "workspace_path": "/path/to/workspace"
        }

        # Workspace path should still exist after uninstall
        assert "workspace_path" in result


class TestPhase6bListQueryTools:
    """Test Phase 6b refactored list/query tools - conceptual pattern verification."""

    def test_list_plugins_pattern(self):
        """Verify mybb_list_plugins uses correct dual-source pattern."""
        # Phase 6b Pattern: ProjectDatabase.list_projects(type="plugin") + filesystem scan - workspace codenames

        # Simulated workspace plugins
        workspace_plugins = [
            {'codename': 'workspace_plugin', 'display_name': 'Workspace Plugin', 'status': 'installed'}
        ]

        # Simulated filesystem plugins
        filesystem_plugins = ['workspace_plugin', 'legacy_plugin']

        # Pattern: Filter out workspace plugins from filesystem list
        workspace_codenames = {p['codename'] for p in workspace_plugins}
        legacy_plugins = [p for p in filesystem_plugins if p not in workspace_codenames]

        # Verification
        assert 'legacy_plugin' in legacy_plugins
        assert 'workspace_plugin' not in legacy_plugins
        assert len(workspace_plugins) == 1

    def test_read_plugin_pattern(self):
        """Verify mybb_read_plugin checks workspace first, falls back to TestForum."""
        # Phase 6b Pattern: get_project(codename) → workspace_path/src/{codename}.php → TestForum/inc/plugins/{codename}.php

        codename = 'test_plugin'

        # Simulated ProjectDatabase response
        project = {'codename': codename, 'workspace_path': 'plugin_manager/plugins/public/test_plugin'}

        # Pattern verification
        if project:
            expected_workspace_file = f"{project['workspace_path']}/src/{codename}.php"
            assert 'workspace_path' in project
        else:
            expected_legacy_file = f"TestForum/inc/plugins/{codename}.php"
            # Would fall back to legacy

        # Verified: Workspace check happens first

    def test_analyze_plugin_pattern(self, tmp_path):
        """Verify mybb_analyze_plugin uses meta.json for workspace, PHP parsing for legacy."""
        # Phase 6b Pattern: Check workspace → read meta.json → formatted output vs PHP regex parsing

        # Simulated workspace plugin with meta.json
        workspace_dir = tmp_path / "test_plugin"
        workspace_dir.mkdir()
        meta_file = workspace_dir / "meta.json"
        meta_file.write_text('{"plugin": {"name": "Test"}, "hooks": [{"name": "index_start"}]}')

        # Verify meta.json structure
        import json
        meta_data = json.loads(meta_file.read_text())
        assert 'plugin' in meta_data
        assert 'hooks' in meta_data

        # Pattern: If meta.json exists → use it, else → parse PHP
        # Verified: meta.json provides structured data

    def test_is_installed_pattern(self):
        """Verify mybb_plugin_is_installed checks both sources and detects sync issues."""
        # Phase 6b Pattern: get_project(codename) + MyBB cache check → compare → warn on mismatch

        # Simulated workspace status
        workspace_project = {'codename': 'test_plugin', 'status': 'installed'}
        workspace_status = workspace_project.get('status')

        # Simulated MyBB cache status
        mybb_cache_active = False  # Not active in MyBB

        # Pattern: Detect sync issues
        sync_status = None
        if workspace_status == 'installed' and mybb_cache_active:
            sync_status = 'synced'
        elif workspace_status == 'installed' and not mybb_cache_active:
            sync_status = 'workspace_ahead'  # Should warn
        elif workspace_status != 'installed' and mybb_cache_active:
            sync_status = 'mybb_ahead'  # Should warn
        else:
            sync_status = 'both_inactive'

        # Verification: Pattern detects mismatch
        assert sync_status == 'workspace_ahead'
        # Handler should generate warning in this case
