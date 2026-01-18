"""
Tests for Phase 6c: Theme MCP Tools Integration

Unit tests for theme tool logic:
- Theme name to codename conversion
- Workspace path construction
- Theme detection logic
- Stylesheet file operations
"""

import pytest
from pathlib import Path


class TestThemeCodenameNormalization:
    """Tests for theme name to codename conversion (used in handlers)"""

    def test_codename_conversion(self):
        """Test theme name conversion to codename format"""
        test_cases = [
            ('Default Theme', 'default_theme'),
            ('My Custom Theme', 'my_custom_theme'),
            ('Theme-With-Dashes', 'theme-with-dashes'),
            ('  Spaces  ', 'spaces'),
            ('UPPERCASE', 'uppercase'),
            ('Mixed_Case-Theme', 'mixed_case-theme'),
        ]

        for theme_name, expected_codename in test_cases:
            # Simulate codename conversion logic from handlers
            codename = theme_name.lower().replace(' ', '_').strip('_')
            assert codename == expected_codename, f"Failed for {theme_name}"


class TestWorkspaceThemeDetection:
    """Tests for workspace theme detection logic"""

    def test_workspace_theme_match_positive(self):
        """Test detecting if a theme is workspace-managed (positive case)"""
        workspace_themes = [
            {'codename': 'custom_theme', 'status': 'development'},
            {'codename': 'pro_theme', 'status': 'installed'}
        ]

        # Test positive match
        is_managed = any(t['codename'] == 'custom_theme' for t in workspace_themes)
        assert is_managed is True

    def test_workspace_theme_match_negative(self):
        """Test detecting if a theme is workspace-managed (negative case)"""
        workspace_themes = [
            {'codename': 'custom_theme', 'status': 'development'},
        ]

        # Test negative match
        is_managed = any(t['codename'] == 'nonexistent' for t in workspace_themes)
        assert is_managed is False

    def test_empty_workspace_themes(self):
        """Test detection with empty workspace themes list"""
        workspace_themes = []

        is_managed = any(t['codename'] == 'any_theme' for t in workspace_themes)
        assert is_managed is False


class TestWorkspacePathConstruction:
    """Tests for workspace path construction and file operations"""

    def test_workspace_path_creation(self, tmp_path):
        """Test constructing workspace paths correctly"""
        base_workspace = tmp_path / "themes/public"
        codename = "test_theme"

        workspace_path = base_workspace / codename
        stylesheets_path = workspace_path / "stylesheets"

        # Simulate directory creation (as done in handlers)
        stylesheets_path.mkdir(parents=True, exist_ok=True)

        assert workspace_path.exists()
        assert stylesheets_path.exists()
        assert (workspace_path / "stylesheets").is_dir()

    def test_stylesheet_file_read(self, tmp_path):
        """Test reading stylesheet from workspace file"""
        workspace_path = tmp_path / "themes/public/test_theme"
        stylesheets_dir = workspace_path / "stylesheets"
        stylesheets_dir.mkdir(parents=True)

        # Create test stylesheet
        stylesheet_file = stylesheets_dir / "global.css"
        test_css = "/* Test CSS */\nbody { margin: 0; }"
        stylesheet_file.write_text(test_css, encoding='utf-8')

        # Read back
        content = stylesheet_file.read_text(encoding='utf-8')
        assert content == test_css
        assert '/* Test CSS */' in content

    def test_stylesheet_file_write(self, tmp_path):
        """Test writing stylesheet to workspace file"""
        workspace_path = tmp_path / "themes/public/test_theme"
        stylesheets_dir = workspace_path / "stylesheets"
        stylesheets_dir.mkdir(parents=True)

        # Write stylesheet
        stylesheet_file = stylesheets_dir / "custom.css"
        new_css = "/* Updated CSS */\nbody { background: blue; }"
        stylesheet_file.write_text(new_css, encoding='utf-8')

        # Verify
        assert stylesheet_file.exists()
        content = stylesheet_file.read_text(encoding='utf-8')
        assert '/* Updated CSS */' in content
        assert 'body { background: blue; }' in content


class TestHybridModeLogic:
    """Tests for hybrid mode decision logic"""

    def test_managed_theme_detection_from_name(self):
        """Test converting MyBB theme name to workspace codename for matching"""
        # Simulate the hybrid mode logic
        mybb_theme_name = "Default Theme"
        workspace_themes = [
            {'codename': 'default_theme', 'workspace_path': '/path/to/workspace'}
        ]

        # Convert theme name to codename
        theme_codename = mybb_theme_name.lower().replace(' ', '_')

        # Check if managed
        managed_theme = next((t for t in workspace_themes if t['codename'] == theme_codename), None)

        assert managed_theme is not None
        assert managed_theme['codename'] == 'default_theme'

    def test_unmanaged_theme_fallback(self):
        """Test fallback when theme is not workspace-managed"""
        mybb_theme_name = "Legacy Theme"
        workspace_themes = [
            {'codename': 'modern_theme', 'workspace_path': '/path/to/workspace'}
        ]

        # Convert theme name to codename
        theme_codename = mybb_theme_name.lower().replace(' ', '_')

        # Check if managed
        managed_theme = next((t for t in workspace_themes if t['codename'] == theme_codename), None)

        assert managed_theme is None  # Should fall back to DB


class TestStylesheetPathMapping:
    """Tests for stylesheet to workspace file path mapping"""

    def test_stylesheet_path_construction(self, tmp_path):
        """Test constructing stylesheet file path from workspace and stylesheet name"""
        workspace_path = Path("/workspace/themes/public/my_theme")
        stylesheet_name = "global.css"

        # Simulate path construction from handler
        stylesheet_file = workspace_path / "stylesheets" / stylesheet_name

        expected_path = Path("/workspace/themes/public/my_theme/stylesheets/global.css")
        assert stylesheet_file == expected_path

    def test_multiple_stylesheets(self, tmp_path):
        """Test handling multiple stylesheet files in workspace"""
        workspace_path = tmp_path / "themes/public/test_theme"
        stylesheets_dir = workspace_path / "stylesheets"
        stylesheets_dir.mkdir(parents=True)

        # Create multiple stylesheets
        stylesheet_names = ["global.css", "usercp.css", "modcp.css"]
        for name in stylesheet_names:
            file_path = stylesheets_dir / name
            file_path.write_text(f"/* {name} */", encoding='utf-8')

        # Verify all exist
        for name in stylesheet_names:
            file_path = stylesheets_dir / name
            assert file_path.exists()
            content = file_path.read_text(encoding='utf-8')
            assert f"/* {name} */" in content


class TestThemeListMerging:
    """Tests for merging workspace and DB theme lists"""

    def test_merge_workspace_and_db_themes(self):
        """Test merging logic for workspace and DB themes"""
        workspace_themes = [
            {'codename': 'custom_theme', 'status': 'development'},
            {'codename': 'default', 'status': 'installed'}
        ]

        db_themes = [
            {'tid': 1, 'name': 'Default'},
            {'tid': 2, 'name': 'Another Theme'}
        ]

        # Simulate marking managed themes
        marked_themes = []
        for db_theme in db_themes:
            theme_codename = db_theme['name'].lower().replace(' ', '_')
            is_managed = any(wt['codename'] == theme_codename for wt in workspace_themes)
            marked_themes.append({
                **db_theme,
                'managed': is_managed
            })

        # Verify
        assert marked_themes[0]['managed'] is True  # Default -> default
        assert marked_themes[1]['managed'] is False  # Another Theme not in workspace


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
