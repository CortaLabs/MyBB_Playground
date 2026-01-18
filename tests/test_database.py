"""Tests for ProjectDatabase class."""

import pytest
import tempfile
from pathlib import Path
from plugin_manager.database import ProjectDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        schema_path = Path(__file__).parent.parent / ".plugin_manager" / "schema" / "projects.sql"

        db = ProjectDatabase(db_path)
        db.create_tables(schema_path)

        yield db

        db.close()


def test_create_tables(temp_db):
    """Test database table creation."""
    # Should not raise any errors
    cursor = temp_db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    assert "projects" in tables
    assert "history" in tables


def test_add_project(temp_db):
    """Test adding a new project."""
    project_id = temp_db.add_project(
        codename="test_plugin",
        display_name="Test Plugin",
        workspace_path="plugins/public/test_plugin",
        author="Test Author",
        description="A test plugin"
    )

    assert project_id > 0

    # Verify project was added
    project = temp_db.get_project("test_plugin")
    assert project is not None
    assert project["codename"] == "test_plugin"
    assert project["display_name"] == "Test Plugin"
    assert project["author"] == "Test Author"


def test_get_project(temp_db):
    """Test retrieving a project."""
    temp_db.add_project(
        codename="my_plugin",
        display_name="My Plugin",
        workspace_path="plugins/public/my_plugin"
    )

    project = temp_db.get_project("my_plugin")
    assert project is not None
    assert project["codename"] == "my_plugin"

    # Test non-existent project
    not_found = temp_db.get_project("nonexistent")
    assert not_found is None


def test_update_project(temp_db):
    """Test updating project fields."""
    temp_db.add_project(
        codename="update_test",
        display_name="Update Test",
        workspace_path="plugins/public/update_test",
        version="1.0.0"
    )

    # Update version and status
    success = temp_db.update_project(
        "update_test",
        version="1.1.0",
        status="testing"
    )
    assert success is True

    # Verify update
    project = temp_db.get_project("update_test")
    assert project["version"] == "1.1.0"
    assert project["status"] == "testing"

    # Test updating non-existent project
    success = temp_db.update_project("nonexistent", version="2.0.0")
    assert success is False


def test_delete_project(temp_db):
    """Test deleting a project."""
    temp_db.add_project(
        codename="delete_test",
        display_name="Delete Test",
        workspace_path="plugins/public/delete_test"
    )

    # Verify it exists
    project = temp_db.get_project("delete_test")
    assert project is not None

    # Delete it
    success = temp_db.delete_project("delete_test")
    assert success is True

    # Verify it's gone
    project = temp_db.get_project("delete_test")
    assert project is None

    # Test deleting non-existent project
    success = temp_db.delete_project("nonexistent")
    assert success is False


def test_list_projects(temp_db):
    """Test listing projects with filters."""
    # Add multiple projects
    temp_db.add_project(
        codename="plugin1",
        display_name="Plugin 1",
        workspace_path="plugins/public/plugin1",
        type="plugin",
        visibility="public",
        status="development"
    )
    temp_db.add_project(
        codename="plugin2",
        display_name="Plugin 2",
        workspace_path="plugins/private/plugin2",
        type="plugin",
        visibility="private",
        status="installed"
    )
    temp_db.add_project(
        codename="theme1",
        display_name="Theme 1",
        workspace_path="themes/public/theme1",
        type="theme",
        visibility="public",
        status="development"
    )

    # List all
    all_projects = temp_db.list_projects()
    assert len(all_projects) == 3

    # Filter by type
    plugins = temp_db.list_projects(type="plugin")
    assert len(plugins) == 2

    themes = temp_db.list_projects(type="theme")
    assert len(themes) == 1

    # Filter by visibility
    public_projects = temp_db.list_projects(visibility="public")
    assert len(public_projects) == 2

    # Filter by status
    dev_projects = temp_db.list_projects(status="development")
    assert len(dev_projects) == 2

    # Multiple filters
    public_plugins = temp_db.list_projects(type="plugin", visibility="public")
    assert len(public_plugins) == 1
    assert public_plugins[0]["codename"] == "plugin1"


def test_add_history(temp_db):
    """Test adding history entries."""
    project_id = temp_db.add_project(
        codename="history_test",
        display_name="History Test",
        workspace_path="plugins/public/history_test"
    )

    # History should already have 'created' entry from add_project
    history = temp_db.get_history("history_test", limit=10)
    assert len(history) >= 1
    assert history[0]["action"] == "created"

    # Add another history entry
    history_id = temp_db.add_history(project_id, "installed", '{"target": "TestForum"}')
    assert history_id > 0

    # Verify new entry
    history = temp_db.get_history("history_test", limit=10)
    assert len(history) >= 2


def test_get_history(temp_db):
    """Test retrieving history entries."""
    # Add project with some history
    project_id = temp_db.add_project(
        codename="hist_proj",
        display_name="History Project",
        workspace_path="plugins/public/hist_proj"
    )
    temp_db.add_history(project_id, "synced")
    temp_db.add_history(project_id, "exported")

    # Get history for specific project
    history = temp_db.get_history("hist_proj")
    assert len(history) == 3  # created + synced + exported

    # Get all history
    all_history = temp_db.get_history()
    assert len(all_history) >= 3


def test_context_manager(temp_db):
    """Test using ProjectDatabase as context manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "context_test.db"
        schema_path = Path(__file__).parent.parent / ".plugin_manager" / "schema" / "projects.sql"

        with ProjectDatabase(db_path) as db:
            db.create_tables(schema_path)
            project_id = db.add_project(
                codename="ctx_test",
                display_name="Context Test",
                workspace_path="plugins/public/ctx_test"
            )
            assert project_id > 0

        # Connection should be closed after exiting context
