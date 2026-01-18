"""Plugin and theme export/packaging for distribution.

This module provides ZIP packaging functionality for MyBB plugins and themes,
including validation, README generation, and proper file structure.
"""

import zipfile
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from plugin_manager.workspace import PluginWorkspace, ThemeWorkspace
from plugin_manager.schema import validate_meta, load_meta
from plugin_manager.database import ProjectDatabase


class PluginPackager:
    """Handles plugin export and ZIP packaging."""

    def __init__(self, workspace: PluginWorkspace, db: ProjectDatabase):
        """Initialize plugin packager.

        Args:
            workspace: PluginWorkspace instance for file operations
            db: ProjectDatabase instance for history tracking
        """
        self.workspace = workspace
        self.db = db

    def validate_for_export(
        self,
        codename: str,
        visibility: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate plugin is ready for export.

        Args:
            codename: Plugin codename
            visibility: Workspace visibility (public/private/None for auto-detect)

        Returns:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "meta": Dict[str, Any] (if valid)
            }
        """
        errors = []
        warnings = []

        # Get workspace path
        workspace_path = self.workspace.get_workspace_path(codename, visibility)
        if not workspace_path:
            return {
                "valid": False,
                "errors": [f"Plugin '{codename}' workspace not found"],
                "warnings": [],
                "meta": None
            }

        # Load and validate meta.json
        meta_path = workspace_path / "meta.json"
        meta = None
        if not meta_path.exists():
            errors.append("meta.json not found")
        else:
            meta, load_errors = load_meta(meta_path)
            if load_errors:
                errors.extend(load_errors)
            elif meta:
                # Validate meta schema
                valid_schema, validation_errors = validate_meta(meta)
                if not valid_schema:
                    errors.extend(validation_errors)

                # Check required fields for export
                if not meta.get("version") or meta.get("version") == "0.0.0":
                    warnings.append("Version should be set before export")

                if not meta.get("author"):
                    warnings.append("Author should be set before export")

        # Check plugin PHP file exists (MyBB-compatible path)
        src_path = workspace_path / "inc" / "plugins" / f"{codename}.php"
        if not src_path.exists():
            errors.append(f"Plugin PHP file not found: inc/plugins/{codename}.php")
        else:
            # Basic PHP syntax check (just verify it's not empty)
            content = src_path.read_text()
            if len(content.strip()) < 100:
                warnings.append("Plugin PHP file seems incomplete")

            # Check for required functions
            if f"function {codename}_info" not in content:
                errors.append(f"Missing required function: {codename}_info()")

        # Check language file if referenced in meta (MyBB-compatible path)
        if meta and meta.get("files", {}).get("languages"):
            lang_path = workspace_path / "inc" / "languages" / "english" / f"{codename}.lang.php"
            if not lang_path.exists():
                warnings.append(f"Language file referenced but not found: {lang_path.name}")

        # Determine validity
        valid = len(errors) == 0

        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "meta": meta if valid else None
        }

    def generate_readme(
        self,
        codename: str,
        meta: Dict[str, Any],
        plugin_analysis: Optional[str] = None
    ) -> str:
        """Generate README.md content for plugin.

        Args:
            codename: Plugin codename
            meta: Plugin metadata from meta.json
            plugin_analysis: Optional output from mybb_analyze_plugin MCP tool

        Returns:
            README markdown content
        """
        lines = []

        # Header
        display_name = meta.get("display_name", codename)
        lines.append(f"# {display_name}\n")

        # Description
        if meta.get("description"):
            lines.append(f"{meta['description']}\n")

        # Metadata
        lines.append(f"**Version:** {meta.get('version', '1.0.0')}  ")
        lines.append(f"**Author:** {meta.get('author', 'Unknown')}  ")
        lines.append(f"**Compatibility:** MyBB {meta.get('mybb_compatibility', '18*')}\n")

        # Installation
        lines.append("## Installation\n")
        lines.append(f"1. Upload `{codename}.php` to `inc/plugins/`")

        if meta.get("files", {}).get("language"):
            lines.append("2. Upload `languages/` folder to `inc/languages/`")

        lines.append("3. Activate in Admin CP → Configuration → Plugins\n")

        # Hooks (from meta.json or analysis)
        hooks = meta.get("hooks", [])
        if hooks:
            lines.append(f"## Hooks Used ({len(hooks)})\n")
            for hook in hooks[:20]:  # Limit to 20
                hook_name = hook if isinstance(hook, str) else hook.get("name", "unknown")
                lines.append(f"- `{hook_name}`")
            lines.append("")

        # Settings
        settings = meta.get("settings", [])
        if settings:
            lines.append(f"## Settings ({len(settings)})\n")
            lines.append("Configure in Admin CP → Configuration → Settings:\n")
            for setting in settings[:20]:  # Limit to 20
                setting_name = setting.get("name", "unknown")
                setting_desc = setting.get("description", "")
                lines.append(f"- **{setting_name}**: {setting_desc}")
            lines.append("")

        # Features (from meta.json)
        features = []
        if meta.get("features", {}).get("templates"):
            features.append("Custom templates")
        if meta.get("features", {}).get("database"):
            features.append("Database tables")
        if settings:
            features.append("ACP settings")

        if features:
            lines.append("## Features\n")
            for feature in features:
                lines.append(f"- {feature}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Packaged with Plugin & Theme Manager*")

        return "\n".join(lines)

    def create_plugin_zip(
        self,
        codename: str,
        output_path: Path,
        visibility: Optional[str] = None,
        include_tests: bool = False
    ) -> Dict[str, Any]:
        """Create distributable ZIP package for plugin.

        Args:
            codename: Plugin codename
            output_path: Path where ZIP will be created
            visibility: Workspace visibility
            include_tests: Whether to include test files (default: False)

        Returns:
            {
                "success": bool,
                "zip_path": str,
                "files_included": List[str],
                "warnings": List[str]
            }
        """
        files_included = []
        warnings = []

        # Get workspace path
        workspace_path = self.workspace.get_workspace_path(codename, visibility)
        if not workspace_path:
            return {
                "success": False,
                "error": f"Plugin '{codename}' workspace not found",
                "zip_path": None,
                "files_included": [],
                "warnings": []
            }

        # Create ZIP with MyBB-compatible structure
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add main plugin PHP file (MyBB-compatible path)
                src_php = workspace_path / "inc" / "plugins" / f"{codename}.php"
                if src_php.exists():
                    # In ZIP: inc/plugins/{codename}.php (for direct overlay)
                    zf.write(src_php, f"inc/plugins/{codename}.php")
                    files_included.append(f"inc/plugins/{codename}.php")
                else:
                    warnings.append(f"Main plugin file not found: {src_php}")

                # Add language file if exists (MyBB-compatible path)
                lang_file = workspace_path / "inc" / "languages" / "english" / f"{codename}.lang.php"
                if lang_file.exists():
                    zf.write(lang_file, f"inc/languages/english/{codename}.lang.php")
                    files_included.append(f"inc/languages/english/{codename}.lang.php")

                # Add jscripts if directory exists
                jscripts_dir = workspace_path / "jscripts"
                if jscripts_dir.exists() and jscripts_dir.is_dir():
                    for js_file in jscripts_dir.rglob("*"):
                        if js_file.is_file():
                            rel_path = js_file.relative_to(workspace_path)
                            zf.write(js_file, str(rel_path))
                            files_included.append(str(rel_path))

                # Add images if directory exists
                images_dir = workspace_path / "images"
                if images_dir.exists() and images_dir.is_dir():
                    for img_file in images_dir.rglob("*"):
                        if img_file.is_file():
                            rel_path = img_file.relative_to(workspace_path)
                            zf.write(img_file, str(rel_path))
                            files_included.append(str(rel_path))

                # Add README.md if exists
                readme = workspace_path / "README.md"
                if readme.exists():
                    zf.write(readme, "README.md")
                    files_included.append("README.md")

                # Optionally include tests
                if include_tests:
                    tests_dir = workspace_path / "tests"
                    if tests_dir.exists() and tests_dir.is_dir():
                        for test_file in tests_dir.rglob("*.py"):
                            rel_path = test_file.relative_to(workspace_path)
                            zf.write(test_file, str(rel_path))
                            files_included.append(str(rel_path))

            return {
                "success": True,
                "zip_path": str(output_path),
                "files_included": files_included,
                "warnings": warnings
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create ZIP: {str(e)}",
                "zip_path": None,
                "files_included": files_included,
                "warnings": warnings
            }


class ThemePackager:
    """Handles theme export and ZIP packaging."""

    def __init__(self, workspace: ThemeWorkspace, db: ProjectDatabase):
        """Initialize theme packager.

        Args:
            workspace: ThemeWorkspace instance for file operations
            db: ProjectDatabase instance for history tracking
        """
        self.workspace = workspace
        self.db = db

    def validate_for_export(
        self,
        codename: str,
        visibility: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate theme is ready for export.

        Args:
            codename: Theme codename
            visibility: Workspace visibility

        Returns:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "meta": Dict[str, Any] (if valid)
            }
        """
        errors = []
        warnings = []

        # Get workspace path
        workspace_path = self.workspace.get_workspace_path(codename, visibility)
        if not workspace_path:
            return {
                "valid": False,
                "errors": [f"Theme '{codename}' workspace not found"],
                "warnings": [],
                "meta": None
            }

        # Load and validate meta.json
        meta_path = workspace_path / "meta.json"
        if not meta_path.exists():
            errors.append("meta.json not found")
        else:
            meta, load_errors = load_meta(meta_path)
            if load_errors:
                errors.extend(load_errors)
            else:
                # Validate meta schema
                valid, validation_errors = validate_meta(meta)
                if not valid:
                    errors.extend(validation_errors)

                # Check theme-specific requirements
                stylesheets = meta.get("stylesheets")
                if not stylesheets or len(stylesheets) == 0:
                    errors.append("Theme must have at least one stylesheet (stylesheets array is empty)")

                # Check version and author
                if not meta.get("version") or meta.get("version") == "0.0.0":
                    warnings.append("Version should be set before export")

                if not meta.get("author"):
                    warnings.append("Author should be set before export")

        # Verify stylesheet files exist
        if meta and meta.get("stylesheets"):
            stylesheets_dir = workspace_path / "stylesheets"
            for stylesheet in meta["stylesheets"]:
                # Handle both string and object format
                stylesheet_name = stylesheet if isinstance(stylesheet, str) else stylesheet.get("name", "")
                stylesheet_path = stylesheets_dir / f"{stylesheet_name}.css"
                if not stylesheet_path.exists():
                    errors.append(f"Stylesheet not found: {stylesheet_name}.css")

        # Check template overrides if referenced
        if meta and meta.get("template_overrides"):
            templates_dir = workspace_path / "templates"
            for template_name in meta["template_overrides"]:
                template_path = templates_dir / f"{template_name}.html"
                if not template_path.exists():
                    warnings.append(f"Template override not found: {template_name}.html")

        # Determine validity
        valid = len(errors) == 0

        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "meta": meta if valid else None
        }

    def generate_readme(
        self,
        codename: str,
        meta: Dict[str, Any]
    ) -> str:
        """Generate README.md content for theme.

        Args:
            codename: Theme codename
            meta: Theme metadata from meta.json

        Returns:
            README markdown content
        """
        lines = []

        # Header
        display_name = meta.get("display_name", codename)
        lines.append(f"# {display_name}\n")

        # Description
        if meta.get("description"):
            lines.append(f"{meta['description']}\n")

        # Metadata
        lines.append(f"**Version:** {meta.get('version', '1.0.0')}  ")
        lines.append(f"**Author:** {meta.get('author', 'Unknown')}  ")
        lines.append(f"**Compatibility:** MyBB {meta.get('mybb_compatibility', '18*')}\n")

        # Parent theme
        if meta.get("parent_theme"):
            lines.append(f"**Parent Theme:** {meta['parent_theme']}\n")

        # Installation
        lines.append("## Installation\n")
        lines.append("### Option 1: Manual Import")
        lines.append("1. Extract ZIP contents")
        lines.append("2. Upload `stylesheets/` to your theme directory")
        if meta.get("template_overrides"):
            lines.append("3. Import template overrides via Admin CP → Templates & Style")
        lines.append("\n### Option 2: Admin CP Import")
        lines.append("1. Go to Admin CP → Templates & Style → Themes")
        lines.append("2. Import theme from ZIP (if MyBB XML format included)\n")

        # Stylesheets
        stylesheets = meta.get("stylesheets", [])
        if stylesheets:
            lines.append(f"## Included Stylesheets ({len(stylesheets)})\n")
            for sheet in stylesheets:
                # Handle both string and object format
                sheet_name = sheet if isinstance(sheet, str) else sheet.get("name", "")
                lines.append(f"- `{sheet_name}.css`")
            lines.append("")

        # Template overrides
        template_overrides = meta.get("template_overrides", [])
        if template_overrides:
            lines.append(f"## Template Overrides ({len(template_overrides)})\n")
            for template in template_overrides:
                lines.append(f"- `{template}.html`")
            lines.append("")

        # Color scheme
        color_scheme = meta.get("color_scheme", {})
        if color_scheme:
            lines.append("## Color Scheme\n")
            for var_name, var_value in color_scheme.items():
                lines.append(f"- `{var_name}`: {var_value}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Packaged with Plugin & Theme Manager*")

        return "\n".join(lines)

    def create_theme_zip(
        self,
        codename: str,
        output_path: Path,
        visibility: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create distributable ZIP package for theme.

        Args:
            codename: Theme codename
            output_path: Path where ZIP will be created
            visibility: Workspace visibility

        Returns:
            {
                "success": bool,
                "zip_path": str,
                "files_included": List[str],
                "warnings": List[str]
            }
        """
        files_included = []
        warnings = []

        # Get workspace path
        workspace_path = self.workspace.get_workspace_path(codename, visibility)
        if not workspace_path:
            return {
                "success": False,
                "error": f"Theme '{codename}' workspace not found",
                "zip_path": None,
                "files_included": [],
                "warnings": []
            }

        # Create ZIP
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add all stylesheets
                stylesheets_dir = workspace_path / "stylesheets"
                if stylesheets_dir.exists() and stylesheets_dir.is_dir():
                    for css_file in stylesheets_dir.glob("*.css"):
                        zf.write(css_file, f"stylesheets/{css_file.name}")
                        files_included.append(f"stylesheets/{css_file.name}")
                else:
                    warnings.append("No stylesheets directory found")

                # Add template overrides if exist
                templates_dir = workspace_path / "templates"
                if templates_dir.exists() and templates_dir.is_dir():
                    for tpl_file in templates_dir.glob("*.html"):
                        zf.write(tpl_file, f"templates/{tpl_file.name}")
                        files_included.append(f"templates/{tpl_file.name}")

                # Add images if directory exists
                images_dir = workspace_path / "images"
                if images_dir.exists() and images_dir.is_dir():
                    for img_file in images_dir.rglob("*"):
                        if img_file.is_file():
                            rel_path = img_file.relative_to(images_dir)
                            zf.write(img_file, f"images/{rel_path}")
                            files_included.append(f"images/{rel_path}")

                # Add README.md if exists
                readme = workspace_path / "README.md"
                if readme.exists():
                    zf.write(readme, "README.md")
                    files_included.append("README.md")

            return {
                "success": True,
                "zip_path": str(output_path),
                "files_included": files_included,
                "warnings": warnings
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create ZIP: {str(e)}",
                "zip_path": None,
                "files_included": files_included,
                "warnings": warnings
            }
