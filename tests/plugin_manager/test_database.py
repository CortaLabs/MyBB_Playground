"""Tests for plugin_manager.database module."""

import json
import shutil
import tempfile
from pathlib import Path
import pytest

from plugin_manager.database import ProjectDatabase


@pytest.fixture
def db_with_schema(tmp_path):
    """Create a database with schema initialized."""
    # Copy schema file to temp location
    schema_source = Path(__file__).parent.parent.parent / ".plugin_manager" / "schema" / "projects.sql"
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    shutil.copy(schema_source, schema_dir / "projects.sql")

    db_path = tmp_path / "test.db"
    db = ProjectDatabase(db_path)
    db.create_tables(schema_dir / "projects.sql")
    yield db
    db.close()


class TestProjectDatabase:
    """Test ProjectDatabase class."""

    def test_add_plugin_project(self, db_with_schema):
        """Should add a plugin project."""
        project_id = db_with_schema.add_project(
            codename="test_plugin",
            display_name="Test Plugin",
            workspace_path="plugins/public/test_plugin",
            type="plugin",
            visibility="public"
        )
        assert project_id > 0

    def test_add_theme_project(self, db_with_schema):
        """Should add a theme project."""
        project_id = db_with_schema.add_project(
            codename="test_theme",
            display_name="Test Theme",
            workspace_path="themes/private/test_theme",
            type="theme",
            visibility="private"
        )
        assert project_id > 0

    def test_get_project(self, db_with_schema):
        """Should retrieve project by codename."""
        db_with_schema.add_project(
            codename="my_theme",
            display_name="My Theme",
            workspace_path="themes/public/my_theme",
            type="theme"
        )

        project = db_with_schema.get_project("my_theme")
        assert project is not None
        assert project["codename"] == "my_theme"
        assert project["type"] == "theme"

    def test_list_projects_filter_by_type(self, db_with_schema):
        """Should filter projects by type."""
        db_with_schema.add_project(
            codename="plugin1",
            display_name="Plugin 1",
            workspace_path="plugins/public/plugin1",
            type="plugin"
        )
        db_with_schema.add_project(
            codename="theme1",
            display_name="Theme 1",
            workspace_path="themes/public/theme1",
            type="theme"
        )
        db_with_schema.add_project(
            codename="plugin2",
            display_name="Plugin 2",
            workspace_path="plugins/public/plugin2",
            type="plugin"
        )

        plugins = db_with_schema.list_projects(type="plugin")
        themes = db_with_schema.list_projects(type="theme")
        all_projects = db_with_schema.list_projects()

        assert len(plugins) == 2
        assert len(themes) == 1
        assert len(all_projects) == 3

    def test_list_projects_filter_by_visibility(self, db_with_schema):
        """Should filter projects by visibility."""
        db_with_schema.add_project(
            codename="public_theme",
            display_name="Public Theme",
            workspace_path="themes/public/public_theme",
            type="theme",
            visibility="public"
        )
        db_with_schema.add_project(
            codename="private_theme",
            display_name="Private Theme",
            workspace_path="themes/private/private_theme",
            type="theme",
            visibility="private"
        )

        public = db_with_schema.list_projects(visibility="public")
        private = db_with_schema.list_projects(visibility="private")

        assert len(public) == 1
        assert public[0]["codename"] == "public_theme"
        assert len(private) == 1
        assert private[0]["codename"] == "private_theme"

    def test_list_projects_combined_filters(self, db_with_schema):
        """Should support combined type and visibility filters."""
        db_with_schema.add_project(
            codename="public_plugin",
            display_name="Public Plugin",
            workspace_path="plugins/public/public_plugin",
            type="plugin",
            visibility="public"
        )
        db_with_schema.add_project(
            codename="private_theme",
            display_name="Private Theme",
            workspace_path="themes/private/private_theme",
            type="theme",
            visibility="private"
        )

        results = db_with_schema.list_projects(type="theme", visibility="private")
        assert len(results) == 1
        assert results[0]["codename"] == "private_theme"

    def test_update_project(self, db_with_schema):
        """Should update project fields."""
        db_with_schema.add_project(
            codename="test",
            display_name="Test",
            workspace_path="plugins/public/test",
            type="plugin",
            version="1.0.0"
        )

        success = db_with_schema.update_project("test", version="2.0.0", status="testing")
        assert success

        project = db_with_schema.get_project("test")
        assert project["version"] == "2.0.0"
        assert project["status"] == "testing"

    def test_delete_project(self, db_with_schema):
        """Should delete project."""
        db_with_schema.add_project(
            codename="to_delete",
            display_name="To Delete",
            workspace_path="plugins/public/to_delete",
            type="plugin"
        )

        success = db_with_schema.delete_project("to_delete")
        assert success

        project = db_with_schema.get_project("to_delete")
        assert project is None

    def test_history_logged_on_create(self, db_with_schema):
        """Should log history entry when project is created."""
        db_with_schema.add_project(
            codename="with_history",
            display_name="With History",
            workspace_path="themes/public/with_history",
            type="theme"
        )

        history = db_with_schema.get_history("with_history")
        assert len(history) >= 1
        assert history[0]["action"] == "created"
