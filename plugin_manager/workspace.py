"""Workspace management for plugin and theme development.

This module provides classes for creating and managing plugin and theme workspaces
in the plugin_manager directory structure.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base.workspace import BaseWorkspace
from .schema import (
    validate_meta,
    create_default_plugin_meta,
    create_default_theme_meta,
    load_meta,
    save_meta
)


class PluginWorkspace(BaseWorkspace):
    """Manages plugin development workspace."""

    def _create_subdirectories(self, workspace_path: Path) -> None:
        """Create plugin-specific subdirectories in workspace.

        Creates MyBB-compatible structure:
        - inc/plugins/           # Plugin PHP files go here
        - inc/languages/english/ # Language files go here
        - jscripts/              # Optional JavaScript
        - images/                # Optional images

        Args:
            workspace_path: Path to workspace directory
        """
        # Create subdirectories matching MyBB structure
        (workspace_path / "inc" / "plugins").mkdir(parents=True, exist_ok=True)
        (workspace_path / "inc" / "languages" / "english").mkdir(parents=True, exist_ok=True)
        # Optional directories for jscripts and images
        (workspace_path / "jscripts").mkdir(exist_ok=True)
        (workspace_path / "images").mkdir(exist_ok=True)

    def _validate_type_specific(self, workspace_path: Path, codename: str) -> List[str]:
        """Perform plugin-specific workspace validation.

        Args:
            workspace_path: Path to workspace directory
            codename: Plugin codename

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required directories (MyBB-compatible structure)
        required_dirs = ["inc/plugins", "inc/languages/english"]
        for dir_path in required_dirs:
            if not (workspace_path / dir_path).exists():
                errors.append(f"Missing required directory: {dir_path}")

        # Check for PHP file in inc/plugins/
        plugins_dir = workspace_path / "inc" / "plugins"
        if plugins_dir.exists():
            php_files = list(plugins_dir.glob("*.php"))
            if not php_files:
                errors.append("No PHP file found in inc/plugins/ directory")

        return errors

    @property
    def item_type(self) -> str:
        """Return the type of item managed by this workspace.

        Returns:
            'plugin'
        """
        return "plugin"

    def list_plugins(self, visibility: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all plugins in workspace.

        Args:
            visibility: Optional filter ("public" or "private")

        Returns:
            List of plugin info dictionaries with codename, visibility, workspace_path

        Note:
            This is a wrapper around list_items() for backwards compatibility.
        """
        return self.list_items(visibility)


class ThemeWorkspace(BaseWorkspace):
    """Manages theme development workspace."""

    def _create_subdirectories(self, workspace_path: Path) -> None:
        """Create theme-specific subdirectories in workspace.

        Creates theme structure:
        - stylesheets/  # CSS files
        - templates/    # Template overrides
        - images/       # Theme images

        Args:
            workspace_path: Path to workspace directory
        """
        # Create subdirectories for theme components
        (workspace_path / "stylesheets").mkdir(exist_ok=True)
        (workspace_path / "templates").mkdir(exist_ok=True)
        (workspace_path / "images").mkdir(exist_ok=True)

    def _validate_type_specific(self, workspace_path: Path, codename: str) -> List[str]:
        """Perform theme-specific workspace validation.

        Args:
            workspace_path: Path to workspace directory
            codename: Theme codename

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required directories
        required_dirs = ["stylesheets", "templates", "images"]
        for dir_path in required_dirs:
            if not (workspace_path / dir_path).exists():
                errors.append(f"Missing required directory: {dir_path}")

        # Check for at least one CSS file
        stylesheets_dir = workspace_path / "stylesheets"
        if stylesheets_dir.exists():
            css_files = list(stylesheets_dir.glob("*.css"))
            if not css_files:
                errors.append("No CSS file found in stylesheets/ directory")

        # Check theme-specific meta.json fields (if meta exists)
        meta_path = workspace_path / "meta.json"
        if meta_path.exists():
            meta, load_errors = load_meta(meta_path)
            if not load_errors and meta:
                # Check theme-specific fields
                if meta.get("project_type") != "theme":
                    errors.append("meta.json project_type must be 'theme'")
                if "stylesheets" not in meta:
                    errors.append("meta.json missing 'stylesheets' array")

        return errors

    @property
    def item_type(self) -> str:
        """Return the type of item managed by this workspace.

        Returns:
            'theme'
        """
        return "theme"

    def list_themes(self, visibility: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all themes in workspace.

        Args:
            visibility: Optional filter ("public" or "private")

        Returns:
            List of theme info dictionaries with codename, visibility, workspace_path

        Note:
            Extends list_items() with theme-specific meta fields (parent_theme, stylesheets).
        """
        # Get base item info from inherited method
        themes = self.list_items(visibility)

        # Enhance with theme-specific meta fields
        for theme_info in themes:
            if theme_info["has_meta"]:
                try:
                    meta = self.read_meta(theme_info["codename"], theme_info["visibility"])
                    # Add theme-specific fields
                    theme_info["parent_theme"] = meta.get("parent_theme")
                    theme_info["stylesheets"] = meta.get("stylesheets", [])
                except Exception:
                    pass

        return themes

    def scaffold_stylesheet(
        self,
        name: str = "global.css",
        parent_theme: Optional[str] = None
    ) -> str:
        """Generate base CSS content for a new stylesheet.

        Args:
            name: Stylesheet name (e.g., "global.css", "colors.css")
            parent_theme: Optional parent theme name for inheritance comment

        Returns:
            CSS content string
        """
        header = f"""/**
 * MyBB Theme Stylesheet - {name}
 * Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 */
"""

        if parent_theme:
            header += f"""
/* Inherits from: {parent_theme} */
/* Override styles below */

"""

        if name == "global.css":
            return header + """
/* Global Styles */
body {
    font-family: Arial, sans-serif;
    font-size: 14px;
    line-height: 1.5;
}

/* Header */
#header {
    padding: 20px 0;
}

/* Navigation */
.menu {
    list-style: none;
    padding: 0;
    margin: 0;
}

/* Content */
#content {
    padding: 20px;
}

/* Footer */
#footer {
    padding: 20px 0;
    text-align: center;
}
"""
        elif name == "colors.css":
            return header + """
/* Color Scheme */
:root {
    --primary-color: #0066cc;
    --secondary-color: #f0f0f0;
    --text-color: #333333;
    --link-color: #0066cc;
    --border-color: #cccccc;
    --background-color: #ffffff;
}

/* Apply colors */
body {
    color: var(--text-color);
    background-color: var(--background-color);
}

a {
    color: var(--link-color);
}
"""
        else:
            return header + """
/* Custom Styles */

"""
