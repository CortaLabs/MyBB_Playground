"""Tests for plugin_manager.schema module."""

import json
import tempfile
from pathlib import Path
import pytest

from plugin_manager.schema import (
    META_SCHEMA,
    validate_meta,
    create_default_meta,
    create_default_plugin_meta,
    create_default_theme_meta,
    load_meta,
    save_meta,
)


class TestMetaSchema:
    """Test META_SCHEMA structure."""

    def test_schema_has_project_type(self):
        """META_SCHEMA should include project_type field."""
        assert "project_type" in META_SCHEMA["properties"]
        assert META_SCHEMA["properties"]["project_type"]["enum"] == ["plugin", "theme"]

    def test_schema_has_plugin_fields(self):
        """META_SCHEMA should include plugin-specific fields."""
        props = META_SCHEMA["properties"]
        assert "hooks" in props
        assert "settings" in props
        assert "templates" in props

    def test_schema_has_theme_fields(self):
        """META_SCHEMA should include theme-specific fields."""
        props = META_SCHEMA["properties"]
        assert "stylesheets" in props
        assert "template_overrides" in props
        assert "parent_theme" in props
        assert "color_scheme" in props


class TestValidateMeta:
    """Test validate_meta function."""

    def test_validate_valid_plugin_meta(self):
        """Valid plugin meta should pass validation."""
        meta = {
            "codename": "test_plugin",
            "display_name": "Test Plugin",
            "version": "1.0.0",
            "author": "TestAuthor",
            "project_type": "plugin"
        }
        is_valid, errors = validate_meta(meta)
        assert is_valid
        assert errors == []

    def test_validate_valid_theme_meta(self):
        """Valid theme meta should pass validation."""
        meta = {
            "codename": "test_theme",
            "display_name": "Test Theme",
            "version": "2.0.0",
            "author": "ThemeAuthor",
            "project_type": "theme",
            "stylesheets": [{"name": "custom.css"}],
            "template_overrides": ["header", "footer"]
        }
        is_valid, errors = validate_meta(meta)
        assert is_valid
        assert errors == []

    def test_validate_invalid_project_type(self):
        """Invalid project_type should fail validation."""
        meta = {
            "codename": "test",
            "display_name": "Test",
            "version": "1.0.0",
            "author": "Author",
            "project_type": "invalid"
        }
        is_valid, errors = validate_meta(meta)
        assert not is_valid
        assert "project_type must be 'plugin' or 'theme'" in errors

    def test_validate_stylesheets_structure(self):
        """Stylesheets array should be validated."""
        meta = {
            "codename": "test_theme",
            "display_name": "Test",
            "version": "1.0.0",
            "author": "Author",
            "stylesheets": [{"name": "valid.css"}, {"missing": "name"}]
        }
        is_valid, errors = validate_meta(meta)
        assert not is_valid
        assert any("stylesheets[1] missing required field: name" in e for e in errors)

    def test_validate_template_overrides_strings(self):
        """Template overrides must be strings."""
        meta = {
            "codename": "test_theme",
            "display_name": "Test",
            "version": "1.0.0",
            "author": "Author",
            "template_overrides": ["valid", 123]
        }
        is_valid, errors = validate_meta(meta)
        assert not is_valid
        assert any("template_overrides[1] must be a string" in e for e in errors)


class TestCreateDefaultMeta:
    """Test create_default_meta function."""

    def test_create_plugin_meta_default(self):
        """create_default_meta should create plugin meta by default."""
        meta = create_default_meta("test", "Test", "Author")
        assert meta["project_type"] == "plugin"
        assert "hooks" in meta
        assert "settings" in meta
        assert "stylesheets" not in meta

    def test_create_theme_meta(self):
        """create_default_meta with project_type='theme' should create theme meta."""
        meta = create_default_meta("test", "Test", "Author", project_type="theme")
        assert meta["project_type"] == "theme"
        assert "stylesheets" in meta
        assert "template_overrides" in meta
        assert "hooks" not in meta

    def test_plugin_meta_files_structure(self):
        """Plugin meta should have plugin-specific file paths (MyBB-compatible)."""
        meta = create_default_meta("my_plugin", "My Plugin", "Author")
        assert "plugin" in meta["files"]
        assert meta["files"]["plugin"] == "inc/plugins/my_plugin.php"
        assert "languages" in meta["files"]
        assert meta["files"]["languages"] == "inc/languages/"

    def test_theme_meta_files_structure(self):
        """Theme meta should have theme-specific file paths."""
        meta = create_default_meta("my_theme", "My Theme", "Author", project_type="theme")
        assert "stylesheets" in meta["files"]
        assert meta["files"]["stylesheets"] == "stylesheets/"
        assert "plugin" not in meta["files"]


class TestCreateDefaultPluginMeta:
    """Test create_default_plugin_meta convenience function."""

    def test_creates_plugin_type(self):
        """create_default_plugin_meta should create plugin type meta."""
        meta = create_default_plugin_meta("test", "Test", "Author")
        assert meta["project_type"] == "plugin"

    def test_has_plugin_fields(self):
        """Plugin meta should have hooks and settings."""
        meta = create_default_plugin_meta("test", "Test", "Author")
        assert "hooks" in meta
        assert "settings" in meta
        assert meta["hooks"] == []


class TestCreateDefaultThemeMeta:
    """Test create_default_theme_meta convenience function."""

    def test_creates_theme_type(self):
        """create_default_theme_meta should create theme type meta."""
        meta = create_default_theme_meta("test", "Test", "Author")
        assert meta["project_type"] == "theme"

    def test_has_theme_fields(self):
        """Theme meta should have stylesheets and template_overrides."""
        meta = create_default_theme_meta("test", "Test", "Author")
        assert "stylesheets" in meta
        assert "template_overrides" in meta
        assert meta["stylesheets"] == []

    def test_parent_theme_parameter(self):
        """parent_theme parameter should be set correctly."""
        meta = create_default_theme_meta("child", "Child Theme", "Author", parent_theme="default")
        assert meta["parent_theme"] == "default"

    def test_parent_theme_none_by_default(self):
        """parent_theme should be None by default."""
        meta = create_default_theme_meta("test", "Test", "Author")
        assert meta["parent_theme"] is None


class TestSaveAndLoadMeta:
    """Test save_meta and load_meta functions."""

    def test_save_and_load_plugin_meta(self, tmp_path):
        """Should save and load plugin meta correctly."""
        meta = create_default_plugin_meta("test", "Test Plugin", "Author")
        meta_path = tmp_path / "meta.json"

        success, errors = save_meta(meta, meta_path)
        assert success
        assert errors == []

        loaded, errors = load_meta(meta_path)
        assert loaded is not None
        assert errors == []
        assert loaded["codename"] == "test"
        assert loaded["project_type"] == "plugin"

    def test_save_and_load_theme_meta(self, tmp_path):
        """Should save and load theme meta correctly."""
        meta = create_default_theme_meta("test", "Test Theme", "Author", parent_theme="default")
        meta_path = tmp_path / "meta.json"

        success, errors = save_meta(meta, meta_path)
        assert success

        loaded, errors = load_meta(meta_path)
        assert loaded is not None
        assert loaded["project_type"] == "theme"
        assert loaded["parent_theme"] == "default"
