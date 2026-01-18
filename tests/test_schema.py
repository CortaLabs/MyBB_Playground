"""Tests for meta.json schema validation."""

import pytest
from plugin_manager.schema import (
    validate_meta,
    create_default_meta,
    load_meta,
    save_meta,
    META_SCHEMA
)
import tempfile
from pathlib import Path


def test_meta_schema_structure():
    """Test META_SCHEMA has required structure."""
    assert "$schema" in META_SCHEMA
    assert "required" in META_SCHEMA
    assert "properties" in META_SCHEMA

    # Check required fields
    required = META_SCHEMA["required"]
    assert "codename" in required
    assert "display_name" in required
    assert "version" in required
    assert "author" in required


def test_validate_meta_valid():
    """Test validation passes for valid meta.json."""
    valid_meta = {
        "codename": "my_plugin",
        "display_name": "My Plugin",
        "version": "1.0.0",
        "author": "Developer"
    }

    is_valid, errors = validate_meta(valid_meta)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_meta_missing_required():
    """Test validation fails for missing required fields."""
    incomplete_meta = {
        "codename": "test",
        "version": "1.0.0"
        # Missing display_name and author
    }

    is_valid, errors = validate_meta(incomplete_meta)
    assert is_valid is False
    assert len(errors) >= 2
    assert any("display_name" in err for err in errors)
    assert any("author" in err for err in errors)


def test_validate_meta_invalid_codename():
    """Test validation fails for invalid codename format."""
    invalid_metas = [
        {
            "codename": "MyPlugin",  # Uppercase
            "display_name": "Test",
            "version": "1.0.0",
            "author": "Dev"
        },
        {
            "codename": "my-plugin",  # Hyphens not allowed
            "display_name": "Test",
            "version": "1.0.0",
            "author": "Dev"
        },
        {
            "codename": "123plugin",  # Can't start with number
            "display_name": "Test",
            "version": "1.0.0",
            "author": "Dev"
        }
    ]

    for meta in invalid_metas:
        is_valid, errors = validate_meta(meta)
        assert is_valid is False
        assert any("codename" in err for err in errors)


def test_validate_meta_invalid_version():
    """Test validation fails for invalid version format."""
    invalid_meta = {
        "codename": "test",
        "display_name": "Test",
        "version": "1.0",  # Not semantic versioning
        "author": "Dev"
    }

    is_valid, errors = validate_meta(invalid_meta)
    assert is_valid is False
    assert any("version" in err for err in errors)


def test_validate_meta_invalid_visibility():
    """Test validation fails for invalid visibility value."""
    invalid_meta = {
        "codename": "test",
        "display_name": "Test",
        "version": "1.0.0",
        "author": "Dev",
        "visibility": "secret"  # Not 'public' or 'private'
    }

    is_valid, errors = validate_meta(invalid_meta)
    assert is_valid is False
    assert any("visibility" in err for err in errors)


def test_validate_meta_hooks_structure():
    """Test validation of hooks array."""
    # Valid hooks
    valid_meta = {
        "codename": "test",
        "display_name": "Test",
        "version": "1.0.0",
        "author": "Dev",
        "hooks": [
            {"name": "index_start", "handler": "test_handler", "priority": 10}
        ]
    }
    is_valid, errors = validate_meta(valid_meta)
    assert is_valid is True

    # Invalid hooks - missing required fields
    invalid_meta = {
        "codename": "test",
        "display_name": "Test",
        "version": "1.0.0",
        "author": "Dev",
        "hooks": [
            {"name": "index_start"}  # Missing handler
        ]
    }
    is_valid, errors = validate_meta(invalid_meta)
    assert is_valid is False
    assert any("handler" in err for err in errors)


def test_validate_meta_settings_structure():
    """Test validation of settings array."""
    # Valid settings
    valid_meta = {
        "codename": "test",
        "display_name": "Test",
        "version": "1.0.0",
        "author": "Dev",
        "settings": [
            {
                "name": "test_enabled",
                "title": "Enable Test",
                "type": "yesno",
                "default": "1"
            }
        ]
    }
    is_valid, errors = validate_meta(valid_meta)
    assert is_valid is True

    # Invalid settings - missing required fields
    invalid_meta = {
        "codename": "test",
        "display_name": "Test",
        "version": "1.0.0",
        "author": "Dev",
        "settings": [
            {"name": "test_enabled"}  # Missing title and type
        ]
    }
    is_valid, errors = validate_meta(invalid_meta)
    assert is_valid is False
    assert any("title" in err for err in errors)
    assert any("type" in err for err in errors)

    # Invalid settings - wrong type
    invalid_meta2 = {
        "codename": "test",
        "display_name": "Test",
        "version": "1.0.0",
        "author": "Dev",
        "settings": [
            {
                "name": "test_enabled",
                "title": "Enable",
                "type": "checkbox"  # Invalid type
            }
        ]
    }
    is_valid, errors = validate_meta(invalid_meta2)
    assert is_valid is False
    assert any("type" in err.lower() for err in errors)


def test_create_default_meta():
    """Test creating default meta.json structure."""
    meta = create_default_meta(
        codename="test_plugin",
        display_name="Test Plugin",
        author="Test Author"
    )

    # Verify required fields
    assert meta["codename"] == "test_plugin"
    assert meta["display_name"] == "Test Plugin"
    assert meta["author"] == "Test Author"
    assert meta["version"] == "1.0.0"

    # Verify defaults
    assert meta["mybb_compatibility"] == "18*"
    assert meta["visibility"] == "public"
    assert meta["hooks"] == []
    assert meta["settings"] == []
    assert meta["templates"] == []

    # Verify file paths
    assert "files" in meta
    assert meta["files"]["plugin"] == "src/test_plugin.php"


def test_create_default_meta_custom_values():
    """Test creating meta with custom values."""
    meta = create_default_meta(
        codename="custom",
        display_name="Custom Plugin",
        author="Author",
        version="2.0.0",
        description="Custom description",
        visibility="private"
    )

    assert meta["version"] == "2.0.0"
    assert meta["description"] == "Custom description"
    assert meta["visibility"] == "private"


def test_load_meta_valid():
    """Test loading valid meta.json from file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / "meta.json"

        # Create valid meta.json
        import json
        valid_meta = {
            "codename": "load_test",
            "display_name": "Load Test",
            "version": "1.0.0",
            "author": "Tester"
        }
        with open(meta_path, 'w') as f:
            json.dump(valid_meta, f)

        # Load it
        loaded_meta, errors = load_meta(meta_path)
        assert loaded_meta is not None
        assert len(errors) == 0
        assert loaded_meta["codename"] == "load_test"


def test_load_meta_invalid():
    """Test loading invalid meta.json from file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / "meta.json"

        # Create invalid meta.json (missing required fields)
        import json
        invalid_meta = {
            "codename": "test"
            # Missing required fields
        }
        with open(meta_path, 'w') as f:
            json.dump(invalid_meta, f)

        # Load it
        loaded_meta, errors = load_meta(meta_path)
        assert loaded_meta is None
        assert len(errors) > 0


def test_load_meta_nonexistent():
    """Test loading from non-existent file."""
    loaded_meta, errors = load_meta("/nonexistent/path/meta.json")
    assert loaded_meta is None
    assert len(errors) > 0
    assert any("not found" in err.lower() for err in errors)


def test_save_meta_valid():
    """Test saving valid meta.json to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / "meta.json"

        valid_meta = {
            "codename": "save_test",
            "display_name": "Save Test",
            "version": "1.0.0",
            "author": "Tester"
        }

        success, errors = save_meta(valid_meta, meta_path)
        assert success is True
        assert len(errors) == 0
        assert meta_path.exists()

        # Verify content
        import json
        with open(meta_path, 'r') as f:
            saved_data = json.load(f)
        assert saved_data["codename"] == "save_test"


def test_save_meta_invalid():
    """Test saving invalid meta.json fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / "meta.json"

        invalid_meta = {
            "codename": "test"
            # Missing required fields
        }

        success, errors = save_meta(invalid_meta, meta_path)
        assert success is False
        assert len(errors) > 0
        assert not meta_path.exists()
