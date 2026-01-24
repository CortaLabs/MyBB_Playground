"""
Bug reproduction test: Plugin uninstaller deletes core MyBB directories.

Bug ID: 2025-01-23_uninstaller_core_deletion
Severity: CRITICAL
Component: plugin_manager/installer.py

This test verifies that:
1. Core MyBB directories are NOT tracked during plugin install
2. Protected directories are NOT deleted during uninstall
3. Plugin-specific directories ARE still cleaned up properly
"""

import pytest
from pathlib import Path
import shutil
import tempfile
import json

from plugin_manager.config import Config
from plugin_manager.database import ProjectDatabase
from plugin_manager.workspace import PluginWorkspace
from plugin_manager.installer import PluginInstaller


@pytest.fixture
def temp_repo_with_core_dirs():
    """Create temporary repository with realistic MyBB core directory structure."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)

    # Create TestForum structure with CORE MyBB directories
    testforum = repo_path / "TestForum"

    # Core plugin directory
    (testforum / "inc" / "plugins").mkdir(parents=True)

    # Core language directories
    (testforum / "inc" / "languages" / "english").mkdir(parents=True)
    (testforum / "inc" / "languages" / "english" / "admin").mkdir(parents=True)

    # Core admin directories - THESE MUST NEVER BE DELETED
    admin_dirs = [
        "admin/modules/config",
        "admin/modules/forum",
        "admin/modules/home",
        "admin/modules/style",
        "admin/modules/tools",
        "admin/modules/user",  # This was deleted in the bug!
    ]
    for admin_dir in admin_dirs:
        dir_path = testforum / admin_dir
        dir_path.mkdir(parents=True)
        # Create a core file in each to simulate real MyBB
        (dir_path / "module_meta.php").write_text("<?php // Core MyBB file ?>")

    # Core uploads directories
    (testforum / "uploads" / "avatars").mkdir(parents=True)

    # Create workspace structure
    (repo_path / "plugin_manager" / "plugins" / "public").mkdir(parents=True)
    (repo_path / "plugin_manager" / "plugins" / "private").mkdir(parents=True)

    # Create .plugin_manager directory
    (repo_path / ".plugin_manager").mkdir(parents=True)

    yield repo_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def config_with_core(temp_repo_with_core_dirs):
    """Create test configuration."""
    config = Config(repo_root=temp_repo_with_core_dirs)
    config.data["mybb_root"] = "TestForum"
    return config


@pytest.fixture
def db_with_core(temp_repo_with_core_dirs):
    """Create test database."""
    db_path = temp_repo_with_core_dirs / ".plugin_manager" / "test.db"
    schema_path = Path(__file__).parent.parent.parent / ".plugin_manager" / "schema" / "projects.sql"

    db = ProjectDatabase(db_path)
    db.create_tables(schema_path)
    return db


@pytest.fixture
def plugin_workspace_with_core(config_with_core):
    """Create plugin workspace."""
    workspace_root = config_with_core.get_workspace_path('plugin')
    return PluginWorkspace(workspace_root)


@pytest.fixture
def plugin_deploying_to_admin(temp_repo_with_core_dirs, db_with_core, plugin_workspace_with_core):
    """
    Create a plugin that deploys files to admin/modules/user/ subdirectory.

    This is the exact scenario that caused the bug - a plugin that adds
    files under a core MyBB admin directory.
    """
    codename = "admin_extension"
    # Create the workspace path directly since it doesn't exist yet
    workspace_path = plugin_workspace_with_core.workspace_root / "public" / codename
    workspace_path.mkdir(parents=True)

    # Create meta.json (must have display_name, version, author per schema.py)
    meta = {
        "codename": codename,
        "display_name": "Admin Extension Plugin",
        "description": "Plugin that extends admin functionality",
        "version": "1.0.0",
        "author": "Test",
        "compatibility": "18*"
    }
    (workspace_path / "meta.json").write_text(json.dumps(meta, indent=2))

    # Create main plugin file (required)
    (workspace_path / "inc" / "plugins").mkdir(parents=True)
    (workspace_path / "inc" / "plugins" / f"{codename}.php").write_text(
        f"""<?php
if(!defined("IN_MYBB")) die("No direct access.");

function {codename}_info() {{
    return array(
        'name' => 'Admin Extension',
        'version' => '1.0.0',
    );
}}
?>"""
    )

    # Create admin module files - THIS IS THE BUG TRIGGER
    # Plugin deploys to admin/modules/user/admin_extension/ (plugin-specific subdir)
    admin_module_path = workspace_path / "admin" / "modules" / "user" / codename
    admin_module_path.mkdir(parents=True)
    (admin_module_path / "settings.php").write_text("<?php // Plugin admin settings ?>")
    (admin_module_path / "reports.php").write_text("<?php // Plugin admin reports ?>")

    # Register in database
    db_with_core.add_project(
        codename=codename,
        display_name="Admin Extension Plugin",
        type="plugin",
        description="Plugin that extends admin functionality",
        visibility="public",
        workspace_path=str(workspace_path)
    )

    return codename


class TestUninstallerSafety:
    """Tests for uninstaller safety - preventing deletion of core MyBB directories."""

    def test_core_admin_directories_exist_before_install(
        self, temp_repo_with_core_dirs
    ):
        """Verify our test setup has core directories."""
        testforum = temp_repo_with_core_dirs / "TestForum"

        # These core directories must exist
        assert (testforum / "admin" / "modules" / "user").exists()
        assert (testforum / "admin" / "modules" / "config").exists()
        assert (testforum / "inc" / "plugins").exists()

        # Core files must exist
        assert (testforum / "admin" / "modules" / "user" / "module_meta.php").exists()

    def test_install_does_not_track_core_directories(
        self,
        config_with_core,
        db_with_core,
        plugin_workspace_with_core,
        plugin_deploying_to_admin,
        temp_repo_with_core_dirs
    ):
        """
        CRITICAL TEST: Installing a plugin must NOT track core MyBB directories.

        When a plugin deploys to admin/modules/user/myplugin/, ONLY the
        'myplugin' directory should be tracked - NOT admin/, modules/, or user/.
        """
        installer = PluginInstaller(
            config_with_core,
            db_with_core,
            plugin_workspace_with_core
        )

        codename = plugin_deploying_to_admin
        result = installer.install_plugin(codename)

        assert result["success"], f"Install failed: {result.get('error')}"

        # Get the manifest
        manifest = db_with_core.get_deployed_manifest(codename)
        tracked_dirs = manifest.get("directories", [])

        testforum = temp_repo_with_core_dirs / "TestForum"

        # These core directories must NOT be in the manifest
        core_dirs_that_must_not_be_tracked = [
            str(testforum / "admin"),
            str(testforum / "admin" / "modules"),
            str(testforum / "admin" / "modules" / "user"),
            str(testforum / "admin" / "modules" / "config"),
            str(testforum / "inc"),
            str(testforum / "inc" / "plugins"),
            str(testforum / "inc" / "languages"),
        ]

        for core_dir in core_dirs_that_must_not_be_tracked:
            assert core_dir not in tracked_dirs, \
                f"CRITICAL: Core directory '{core_dir}' was tracked in manifest!"

        # The plugin-specific directory SHOULD be tracked
        plugin_dir = str(testforum / "admin" / "modules" / "user" / codename)
        assert plugin_dir in tracked_dirs, \
            f"Plugin-specific directory '{plugin_dir}' should be tracked"

    def test_uninstall_preserves_core_directories(
        self,
        config_with_core,
        db_with_core,
        plugin_workspace_with_core,
        plugin_deploying_to_admin,
        temp_repo_with_core_dirs
    ):
        """
        CRITICAL TEST: Uninstalling a plugin must NOT delete core MyBB directories.

        This is the exact bug that was reported - uninstall deleted admin/modules/user/.
        """
        installer = PluginInstaller(
            config_with_core,
            db_with_core,
            plugin_workspace_with_core
        )

        codename = plugin_deploying_to_admin
        testforum = temp_repo_with_core_dirs / "TestForum"

        # Install
        result = installer.install_plugin(codename)
        assert result["success"], f"Install failed: {result.get('error')}"

        # Verify plugin files are deployed
        plugin_admin_dir = testforum / "admin" / "modules" / "user" / codename
        assert plugin_admin_dir.exists(), "Plugin admin dir should exist after install"
        assert (plugin_admin_dir / "settings.php").exists()

        # Uninstall
        uninstall_result = installer.uninstall_plugin(codename)
        assert uninstall_result["success"], f"Uninstall failed: {uninstall_result}"

        # CRITICAL: Core directories must still exist!
        core_dirs_that_must_survive = [
            testforum / "admin",
            testforum / "admin" / "modules",
            testforum / "admin" / "modules" / "user",
            testforum / "admin" / "modules" / "config",
            testforum / "inc",
            testforum / "inc" / "plugins",
        ]

        for core_dir in core_dirs_that_must_survive:
            assert core_dir.exists(), \
                f"CRITICAL BUG: Core directory '{core_dir}' was deleted during uninstall!"

        # Core files must still exist
        assert (testforum / "admin" / "modules" / "user" / "module_meta.php").exists(), \
            "CRITICAL BUG: Core MyBB file was deleted!"

        # Plugin-specific directory SHOULD be deleted
        assert not plugin_admin_dir.exists(), \
            "Plugin-specific directory should be deleted"

    def test_uninstall_cleans_plugin_specific_dirs(
        self,
        config_with_core,
        db_with_core,
        plugin_workspace_with_core,
        plugin_deploying_to_admin,
        temp_repo_with_core_dirs
    ):
        """Verify that plugin-specific directories ARE properly cleaned up."""
        installer = PluginInstaller(
            config_with_core,
            db_with_core,
            plugin_workspace_with_core
        )

        codename = plugin_deploying_to_admin
        testforum = temp_repo_with_core_dirs / "TestForum"

        # Install and uninstall
        installer.install_plugin(codename)
        installer.uninstall_plugin(codename)

        # Plugin main file should be gone
        assert not (testforum / "inc" / "plugins" / f"{codename}.php").exists()

        # Plugin admin directory should be gone
        assert not (testforum / "admin" / "modules" / "user" / codename).exists()


class TestProtectedDirectories:
    """Tests for the protected directories safeguard."""

    def test_protected_directories_constant_exists(self):
        """Verify PROTECTED_DIRECTORIES constant exists in PluginInstaller."""
        assert hasattr(PluginInstaller, 'PROTECTED_DIRECTORIES'), \
            "PluginInstaller must have PROTECTED_DIRECTORIES constant"

    def test_protected_directories_includes_core_paths(self):
        """Verify protected directories includes essential MyBB paths."""
        protected = PluginInstaller.PROTECTED_DIRECTORIES

        # These path patterns must be protected
        essential_protected = [
            "admin",
            "admin/modules",
            "inc",
            "inc/plugins",
            "inc/languages",
            "uploads",
        ]

        for path in essential_protected:
            assert path in protected, \
                f"'{path}' must be in PROTECTED_DIRECTORIES"

    def test_is_safe_to_track_rejects_core_dirs(
        self,
        config_with_core,
        db_with_core,
        plugin_workspace_with_core
    ):
        """Test that _is_safe_to_track() rejects core directories."""
        installer = PluginInstaller(
            config_with_core,
            db_with_core,
            plugin_workspace_with_core
        )

        testforum = config_with_core.mybb_root

        # Core directories must NOT be safe to track
        unsafe_dirs = [
            testforum / "admin",
            testforum / "admin" / "modules",
            testforum / "admin" / "modules" / "user",
            testforum / "inc",
            testforum / "inc" / "plugins",
        ]

        for dir_path in unsafe_dirs:
            assert not installer._is_safe_to_track(dir_path, "test_plugin"), \
                f"Core directory '{dir_path}' should NOT be safe to track"

    def test_is_safe_to_track_accepts_plugin_specific_dirs(
        self,
        config_with_core,
        db_with_core,
        plugin_workspace_with_core
    ):
        """Test that _is_safe_to_track() accepts plugin-specific directories."""
        installer = PluginInstaller(
            config_with_core,
            db_with_core,
            plugin_workspace_with_core
        )

        testforum = config_with_core.mybb_root
        codename = "my_plugin"

        # Plugin-specific directories SHOULD be safe to track
        safe_dirs = [
            testforum / "inc" / "plugins" / codename,
            testforum / "inc" / "plugins" / codename / "lib",
            testforum / "admin" / "modules" / "user" / codename,
        ]

        for dir_path in safe_dirs:
            assert installer._is_safe_to_track(dir_path, codename), \
                f"Plugin-specific directory '{dir_path}' SHOULD be safe to track"
