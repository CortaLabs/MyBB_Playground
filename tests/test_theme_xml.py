"""Tests for theme XML export/import and roundtrip."""

import pytest
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from plugin_manager.manager import PluginManager
from plugin_manager.config import Config


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
    schema_path = Path(__file__).parent.parent / ".plugin_manager" / "schema" / "projects.sql"
    mgr.db.create_tables(schema_path=schema_path)
    return mgr


class TestThemeXMLExport:
    """Tests for theme XML export."""

    def test_export_produces_valid_xml(self, manager, tmp_path):
        """Test export produces valid XML structure."""
        # Create a test theme
        manager.create_theme(
            codename="test_theme",
            display_name="Test Theme",
            author="Test Author"
        )

        # Export to XML
        result = manager.export_theme_xml("test_theme")

        assert result["success"] is True
        assert "xml" in result
        assert result["errors"] == []

        # Parse XML to verify structure
        root = ET.fromstring(result["xml"])
        assert root.tag == "theme"
        assert root.get("name") == "Test Theme"
        assert root.get("version")  # Should have MyBB version

        # Verify required sections
        properties = root.find("properties")
        assert properties is not None

        stylesheets = root.find("stylesheets")
        assert stylesheets is not None

    def test_export_includes_stylesheets(self, manager, tmp_path):
        """Test exported XML includes all stylesheets."""
        # Create theme with custom stylesheets
        manager.create_theme(
            codename="styled_theme",
            display_name="Styled Theme",
            stylesheets=["global.css", "custom.css"]
        )

        # Export
        result = manager.export_theme_xml("styled_theme")
        assert result["success"] is True

        # Parse and check stylesheets
        root = ET.fromstring(result["xml"])
        stylesheets = root.find("stylesheets")
        assert stylesheets is not None

        # Count stylesheet elements
        stylesheet_elements = stylesheets.findall("stylesheet")
        assert len(stylesheet_elements) >= 2

        # Verify stylesheet names
        names = [s.get("name") for s in stylesheet_elements]
        assert "global.css" in names
        assert "custom.css" in names

    def test_export_cdata_escaping(self, manager, tmp_path):
        """Test CDATA escaping handles ]]> correctly."""
        # Create theme
        manager.create_theme(
            codename="cdata_theme",
            display_name="CDATA Theme",
            stylesheets=["test.css"]
        )

        # Write stylesheet with ]]> sequence
        workspace_path = manager.theme_workspace.get_workspace_path("cdata_theme")
        css_file = workspace_path / "stylesheets" / "test.css"
        css_file.write_text("/* Comment with ]]> sequence */\nbody { color: red; }")

        # Export
        result = manager.export_theme_xml("cdata_theme")
        assert result["success"] is True

        # Verify CDATA escaping (should be ]]]]><![CDATA[>)
        assert "]]]]><![CDATA[>" in result["xml"]

        # Verify XML is still parseable
        root = ET.fromstring(result["xml"])
        assert root is not None

    def test_export_with_templates(self, manager, tmp_path):
        """Test export includes templates if present."""
        # Create theme
        manager.create_theme(
            codename="template_theme",
            display_name="Template Theme"
        )

        # Add a template
        workspace_path = manager.theme_workspace.get_workspace_path("template_theme")
        template_dir = workspace_path / "templates"
        template_dir.mkdir(exist_ok=True)
        template_file = template_dir / "header.html"
        template_file.write_text("<div>Test Header</div>")

        # Export
        result = manager.export_theme_xml("template_theme")
        assert result["success"] is True

        # Check templates section
        root = ET.fromstring(result["xml"])
        templates = root.find("templates")
        if templates is not None:
            template_elements = templates.findall("template")
            assert len(template_elements) > 0

    def test_export_to_file(self, manager, tmp_path):
        """Test export writes to file when output_path provided."""
        manager.create_theme(
            codename="file_theme",
            display_name="File Theme"
        )

        output_file = tmp_path / "theme_export.xml"
        result = manager.export_theme_xml("file_theme", output_path=str(output_file))

        assert result["success"] is True
        assert "path" in result
        assert output_file.exists()

        # Verify file is valid XML
        tree = ET.parse(output_file)
        root = tree.getroot()
        assert root.tag == "theme"

    def test_export_nonexistent_theme(self, manager):
        """Test export fails gracefully for nonexistent theme."""
        result = manager.export_theme_xml("nonexistent")

        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0].lower()


class TestThemeXMLImport:
    """Tests for theme XML import."""

    def test_import_creates_workspace(self, manager, tmp_path):
        """Test import creates correct workspace structure."""
        # Create a simple theme XML
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<theme name="Imported Theme" version="1839">
    <properties>
        <templateset><![CDATA[-1]]></templateset>
        <editortheme><![CDATA[default.css]]></editortheme>
        <imgdir><![CDATA[images]]></imgdir>
        <logo><![CDATA[]]></logo>
        <tablespace><![CDATA[5]]></tablespace>
        <borderwidth><![CDATA[0]]></borderwidth>
        <color><![CDATA[]]></color>
        <disporder><![CDATA[a:0:{}]]></disporder>
    </properties>
    <stylesheets>
        <stylesheet name="global.css" attachedto="" version="1839"><![CDATA[
body { color: black; }
]]></stylesheet>
    </stylesheets>
</theme>'''

        xml_file = tmp_path / "import_test.xml"
        xml_file.write_text(xml_content)

        # Import
        result = manager.import_theme_xml(str(xml_file))

        assert result["success"] is True
        assert "codename" in result

        # Verify workspace structure
        codename = result["codename"]
        workspace_path = manager.theme_workspace.get_workspace_path(codename)
        assert workspace_path.exists()
        assert (workspace_path / "stylesheets").exists()
        assert (workspace_path / "meta.json").exists()

    def test_import_extracts_stylesheets(self, manager, tmp_path):
        """Test import extracts stylesheets to files."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<theme name="Multi Style Theme" version="1839">
    <properties>
        <templateset><![CDATA[-1]]></templateset>
        <editortheme><![CDATA[default.css]]></editortheme>
        <imgdir><![CDATA[images]]></imgdir>
        <logo><![CDATA[]]></logo>
        <tablespace><![CDATA[5]]></tablespace>
        <borderwidth><![CDATA[0]]></borderwidth>
        <color><![CDATA[]]></color>
        <disporder><![CDATA[a:2:{s:10:"global.css";i:1;s:9:"color.css";i:2;}]]></disporder>
    </properties>
    <stylesheets>
        <stylesheet name="global.css" attachedto="" version="1839"><![CDATA[
body { margin: 0; }
]]></stylesheet>
        <stylesheet name="color.css" attachedto="global.css" version="1839"><![CDATA[
.red { color: red; }
]]></stylesheet>
    </stylesheets>
</theme>'''

        xml_file = tmp_path / "multi_style.xml"
        xml_file.write_text(xml_content)

        result = manager.import_theme_xml(str(xml_file))
        assert result["success"] is True

        # Check stylesheets were extracted
        workspace_path = manager.theme_workspace.get_workspace_path(result["codename"])
        assert (workspace_path / "stylesheets" / "global.css").exists()
        assert (workspace_path / "stylesheets" / "color.css").exists()

        # Verify content
        global_css = (workspace_path / "stylesheets" / "global.css").read_text()
        assert "margin: 0" in global_css

        color_css = (workspace_path / "stylesheets" / "color.css").read_text()
        assert "color: red" in color_css

    def test_import_generates_meta(self, manager, tmp_path):
        """Test import generates valid meta.json."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<theme name="Meta Test Theme" version="1839">
    <properties>
        <templateset><![CDATA[-1]]></templateset>
        <editortheme><![CDATA[default.css]]></editortheme>
        <imgdir><![CDATA[images]]></imgdir>
        <logo><![CDATA[]]></logo>
        <tablespace><![CDATA[5]]></tablespace>
        <borderwidth><![CDATA[0]]></borderwidth>
        <color><![CDATA[]]></color>
        <disporder><![CDATA[a:0:{}]]></disporder>
    </properties>
    <stylesheets>
        <stylesheet name="global.css" attachedto="" version="1839"><![CDATA[
body { color: black; }
]]></stylesheet>
    </stylesheets>
</theme>'''

        xml_file = tmp_path / "meta_test.xml"
        xml_file.write_text(xml_content)

        result = manager.import_theme_xml(str(xml_file))
        assert result["success"] is True

        # Read and validate meta.json
        workspace_path = manager.theme_workspace.get_workspace_path(result["codename"])
        meta = manager.theme_workspace.read_meta(result["codename"])

        assert meta["display_name"] == "Meta Test Theme"
        assert meta["project_type"] == "theme"
        assert "version" in meta
        assert "_xml_properties" in meta

    def test_import_with_templates(self, manager, tmp_path):
        """Test import extracts templates."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<theme name="Template Theme" version="1839">
    <properties>
        <templateset><![CDATA[-1]]></templateset>
        <editortheme><![CDATA[default.css]]></editortheme>
        <imgdir><![CDATA[images]]></imgdir>
        <logo><![CDATA[]]></logo>
        <tablespace><![CDATA[5]]></tablespace>
        <borderwidth><![CDATA[0]]></borderwidth>
        <color><![CDATA[]]></color>
        <disporder><![CDATA[a:0:{}]]></disporder>
    </properties>
    <stylesheets>
        <stylesheet name="global.css" attachedto="" version="1839"><![CDATA[
body { color: black; }
]]></stylesheet>
    </stylesheets>
    <templates>
        <template name="header" version="1839"><![CDATA[
<div class="header">Site Header</div>
]]></template>
    </templates>
</theme>'''

        xml_file = tmp_path / "template_import.xml"
        xml_file.write_text(xml_content)

        result = manager.import_theme_xml(str(xml_file))
        assert result["success"] is True

        # Check template was extracted
        workspace_path = manager.theme_workspace.get_workspace_path(result["codename"])
        template_file = workspace_path / "templates" / "header.html"
        assert template_file.exists()

        content = template_file.read_text()
        assert "Site Header" in content


class TestThemeXMLRoundtrip:
    """Tests for export->import roundtrip."""

    def test_roundtrip_preserves_content(self, manager, tmp_path):
        """Test export->import preserves stylesheet content."""
        # Create original theme
        manager.create_theme(
            codename="original_theme",
            display_name="Original Theme",
            stylesheets=["global.css", "colors.css"]
        )

        # Write custom CSS content
        workspace_path = manager.theme_workspace.get_workspace_path("original_theme")
        (workspace_path / "stylesheets" / "global.css").write_text("body { margin: 0; padding: 0; }")
        (workspace_path / "stylesheets" / "colors.css").write_text(".blue { color: blue; }")

        # Export
        export_result = manager.export_theme_xml("original_theme")
        assert export_result["success"] is True

        # Save to file
        xml_file = tmp_path / "roundtrip.xml"
        xml_file.write_text(export_result["xml"])

        # Import to new theme (use different codename to avoid collision)
        import_result = manager.import_theme_xml(str(xml_file), codename="imported_theme")
        assert import_result["success"] is True

        # Verify content preserved
        imported_workspace = manager.theme_workspace.get_workspace_path(import_result["codename"])

        global_css = (imported_workspace / "stylesheets" / "global.css").read_text()
        assert "margin: 0" in global_css
        assert "padding: 0" in global_css

        colors_css = (imported_workspace / "stylesheets" / "colors.css").read_text()
        assert "color: blue" in colors_css

    def test_roundtrip_preserves_meta(self, manager, tmp_path):
        """Test export->import preserves metadata."""
        # Create theme with specific metadata
        manager.create_theme(
            codename="meta_roundtrip",
            display_name="Metadata Roundtrip Test",
            author="Test Author",
            version="2.0.0",
            description="Testing metadata preservation"
        )

        # Export
        export_result = manager.export_theme_xml("meta_roundtrip")
        assert export_result["success"] is True

        # Import (use different codename to avoid collision)
        xml_file = tmp_path / "meta_roundtrip.xml"
        xml_file.write_text(export_result["xml"])
        import_result = manager.import_theme_xml(str(xml_file), codename="imported_meta")
        assert import_result["success"] is True

        # Check metadata preserved
        imported_meta = manager.theme_workspace.read_meta(import_result["codename"])
        assert imported_meta["display_name"] == "Metadata Roundtrip Test"
        # Note: author/description are not in MyBB XML format,
        # so they won't survive roundtrip through XML
        # Version might be in _xml_properties

    def test_roundtrip_handles_cdata_escaping(self, manager, tmp_path):
        """Test roundtrip preserves content with ]]> sequences."""
        # Create theme
        manager.create_theme(
            codename="cdata_roundtrip",
            display_name="CDATA Roundtrip",
            stylesheets=["special.css"]
        )

        # Write CSS with ]]> sequence
        workspace_path = manager.theme_workspace.get_workspace_path("cdata_roundtrip")
        special_css = workspace_path / "stylesheets" / "special.css"
        original_content = "/* Comment with ]]> and more ]]> sequences */\nbody { color: black; }"
        special_css.write_text(original_content)

        # Export
        export_result = manager.export_theme_xml("cdata_roundtrip")
        assert export_result["success"] is True

        # Import (use different codename to avoid collision)
        xml_file = tmp_path / "cdata_roundtrip.xml"
        xml_file.write_text(export_result["xml"])
        import_result = manager.import_theme_xml(str(xml_file), codename="imported_cdata")
        assert import_result["success"] is True

        # Verify content preserved including ]]> sequences
        imported_workspace = manager.theme_workspace.get_workspace_path(import_result["codename"])
        imported_css = (imported_workspace / "stylesheets" / "special.css").read_text()
        assert "]]>" in imported_css
        assert "color: black" in imported_css

    def test_roundtrip_with_templates(self, manager, tmp_path):
        """Test roundtrip preserves templates."""
        # Create theme
        manager.create_theme(
            codename="template_roundtrip",
            display_name="Template Roundtrip"
        )

        # Add template
        workspace_path = manager.theme_workspace.get_workspace_path("template_roundtrip")
        template_dir = workspace_path / "templates"
        template_dir.mkdir(exist_ok=True)

        template_content = "<div class='header'>\n    <h1>Site Title</h1>\n</div>"
        (template_dir / "header.html").write_text(template_content)

        # Export
        export_result = manager.export_theme_xml("template_roundtrip")
        assert export_result["success"] is True

        # Import (use different codename to avoid collision)
        xml_file = tmp_path / "template_roundtrip.xml"
        xml_file.write_text(export_result["xml"])
        import_result = manager.import_theme_xml(str(xml_file), codename="imported_templates")
        assert import_result["success"] is True

        # Verify template preserved
        imported_workspace = manager.theme_workspace.get_workspace_path(import_result["codename"])
        imported_template = (imported_workspace / "templates" / "header.html").read_text()
        assert "Site Title" in imported_template

    def test_roundtrip_stylesheet_count_matches(self, manager, tmp_path):
        """Test roundtrip preserves stylesheet count."""
        # Create theme with multiple stylesheets
        manager.create_theme(
            codename="count_test",
            display_name="Count Test",
            stylesheets=["global.css", "colors.css", "layout.css"]
        )

        # Export
        export_result = manager.export_theme_xml("count_test")
        assert export_result["success"] is True
        original_count = export_result["stylesheets_count"]

        # Import (use different codename to avoid collision)
        xml_file = tmp_path / "count_test.xml"
        xml_file.write_text(export_result["xml"])
        import_result = manager.import_theme_xml(str(xml_file), codename="imported_count")
        assert import_result["success"] is True

        # Count stylesheets in imported workspace
        imported_workspace = manager.theme_workspace.get_workspace_path(import_result["codename"])
        stylesheet_dir = imported_workspace / "stylesheets"
        imported_stylesheets = list(stylesheet_dir.glob("*.css"))

        assert len(imported_stylesheets) == original_count
