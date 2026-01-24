"""Workspace management for plugin and theme development.

This module provides classes for creating and managing plugin and theme workspaces
in the plugin_manager directory structure.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .schema import (
    validate_meta,
    create_default_plugin_meta,
    create_default_theme_meta,
    load_meta,
    save_meta
)


class PluginWorkspace:
    """Manages plugin development workspace."""

    def __init__(self, workspace_root: Path):
        """Initialize plugin workspace manager.

        Args:
            workspace_root: Root directory for plugin workspaces (e.g., plugin_manager/plugins)
        """
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def create_workspace(
        self,
        codename: str,
        visibility: str = "public"
    ) -> Path:
        """Create a new plugin workspace directory structure.

        Creates the following structure that MIRRORS MyBB's actual directory layout:
        plugins/{visibility}/{codename}/
        ├── inc/
        │   ├── plugins/           # Plugin PHP files go here
        │   └── languages/
        │       └── english/       # Language files go here
        ├── jscripts/              # Optional JavaScript
        ├── images/                # Optional images
        └── meta.json              # Our metadata (not part of MyBB)

        This allows installation to be a simple directory overlay:
        cp -r {workspace}/inc/* TestForum/inc/

        Args:
            codename: Plugin codename (lowercase, underscores)
            visibility: "public" or "private"

        Returns:
            Path to created workspace directory

        Raises:
            ValueError: If workspace already exists
        """
        workspace_path = self.workspace_root / visibility / codename

        if workspace_path.exists():
            raise ValueError(f"Plugin workspace already exists: {workspace_path}")

        # Create main directory
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories matching MyBB structure
        (workspace_path / "inc" / "plugins").mkdir(parents=True, exist_ok=True)
        (workspace_path / "inc" / "languages" / "english").mkdir(parents=True, exist_ok=True)
        # Optional directories for jscripts and images
        (workspace_path / "jscripts").mkdir(exist_ok=True)
        (workspace_path / "images").mkdir(exist_ok=True)

        return workspace_path

    def get_workspace_path(self, codename: str, visibility: Optional[str] = None) -> Optional[Path]:
        """Find plugin workspace path by codename.

        Args:
            codename: Plugin codename
            visibility: Optional visibility filter (searches both if None)

        Returns:
            Path to workspace or None if not found
        """
        if visibility:
            path = self.workspace_root / visibility / codename
            return path if path.exists() else None

        # Search all visibility directories
        for vis in ["public", "private", "forked", "imported"]:
            path = self.workspace_root / vis / codename
            if path.exists():
                return path

        return None

    def read_meta(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
        """Read and parse meta.json from plugin workspace.

        Args:
            codename: Plugin codename
            visibility: Optional visibility filter

        Returns:
            Parsed meta.json dictionary

        Raises:
            FileNotFoundError: If workspace or meta.json not found
            ValueError: If meta.json is invalid
        """
        workspace_path = self.get_workspace_path(codename, visibility)
        if not workspace_path:
            raise FileNotFoundError(f"Plugin workspace not found: {codename}")

        meta_path = workspace_path / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"meta.json not found in workspace: {workspace_path}")

        meta, errors = load_meta(meta_path)
        if errors:
            raise ValueError(f"Invalid meta.json: {', '.join(errors)}")

        return meta

    def write_meta(
        self,
        codename: str,
        meta: Dict[str, Any],
        visibility: Optional[str] = None
    ) -> None:
        """Write meta.json to plugin workspace.

        Args:
            codename: Plugin codename
            meta: Metadata dictionary to write
            visibility: Optional visibility filter

        Raises:
            FileNotFoundError: If workspace not found
            ValueError: If meta validation fails
        """
        workspace_path = self.get_workspace_path(codename, visibility)
        if not workspace_path:
            raise FileNotFoundError(f"Plugin workspace not found: {codename}")

        # Validate before writing
        is_valid, errors = validate_meta(meta)
        if not is_valid:
            raise ValueError(f"Invalid metadata: {', '.join(errors)}")

        meta_path = workspace_path / "meta.json"
        success, save_errors = save_meta(meta, meta_path)
        if not success:
            raise ValueError(f"Failed to save meta.json: {', '.join(save_errors)}")

    def validate_workspace(self, codename: str, visibility: Optional[str] = None) -> List[str]:
        """Validate plugin workspace structure and contents.

        Args:
            codename: Plugin codename
            visibility: Optional visibility filter

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        workspace_path = self.get_workspace_path(codename, visibility)
        if not workspace_path:
            errors.append(f"Workspace not found: {codename}")
            return errors

        # Check required directories (MyBB-compatible structure)
        required_dirs = ["inc/plugins", "inc/languages/english"]
        for dir_path in required_dirs:
            if not (workspace_path / dir_path).exists():
                errors.append(f"Missing required directory: {dir_path}")

        # Check meta.json
        meta_path = workspace_path / "meta.json"
        if not meta_path.exists():
            errors.append("Missing meta.json")
        else:
            meta, load_errors = load_meta(meta_path)
            if load_errors:
                errors.extend([f"meta.json: {err}" for err in load_errors])
            elif meta:
                is_valid, validation_errors = validate_meta(meta)
                if not is_valid:
                    errors.extend([f"meta.json validation: {err}" for err in validation_errors])

        # Check for PHP file in inc/plugins/
        plugins_dir = workspace_path / "inc" / "plugins"
        if plugins_dir.exists():
            php_files = list(plugins_dir.glob("*.php"))
            if not php_files:
                errors.append("No PHP file found in inc/plugins/ directory")

        return errors

    def list_plugins(self, visibility: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all plugins in workspace.

        Args:
            visibility: Optional filter ("public" or "private")

        Returns:
            List of plugin info dictionaries with codename, visibility, workspace_path
        """
        plugins = []

        visibilities = [visibility] if visibility else ["public", "private"]

        for vis in visibilities:
            vis_dir = self.workspace_root / vis
            if not vis_dir.exists():
                continue

            for plugin_dir in vis_dir.iterdir():
                if plugin_dir.is_dir():
                    plugin_info = {
                        "codename": plugin_dir.name,
                        "visibility": vis,
                        "workspace_path": str(plugin_dir),
                        "has_meta": (plugin_dir / "meta.json").exists()
                    }

                    # Try to load meta for additional info
                    if plugin_info["has_meta"]:
                        try:
                            meta = self.read_meta(plugin_dir.name, vis)
                            plugin_info.update({
                                "display_name": meta.get("display_name"),
                                "version": meta.get("version"),
                                "type": meta.get("type")
                            })
                        except Exception:
                            pass

                    plugins.append(plugin_info)

        return plugins


class ThemeWorkspace:
    """Manages theme development workspace."""

    def __init__(self, workspace_root: Path):
        """Initialize theme workspace manager.

        Args:
            workspace_root: Root directory for theme workspaces (e.g., plugin_manager/themes)
        """
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def create_workspace(
        self,
        codename: str,
        visibility: str = "public"
    ) -> Path:
        """Create a new theme workspace directory structure.

        Creates the following structure:
        themes/{visibility}/{codename}/
        ├── stylesheets/
        ├── templates/
        └── images/

        Args:
            codename: Theme codename (lowercase, underscores)
            visibility: "public" or "private"

        Returns:
            Path to created workspace directory

        Raises:
            ValueError: If workspace already exists
        """
        workspace_path = self.workspace_root / visibility / codename

        if workspace_path.exists():
            raise ValueError(f"Theme workspace already exists: {workspace_path}")

        # Create main directory
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (workspace_path / "stylesheets").mkdir(exist_ok=True)
        (workspace_path / "templates").mkdir(exist_ok=True)
        (workspace_path / "images").mkdir(exist_ok=True)

        return workspace_path

    def get_workspace_path(self, codename: str, visibility: Optional[str] = None) -> Optional[Path]:
        """Find theme workspace path by codename.

        Args:
            codename: Theme codename
            visibility: Optional visibility filter (searches both if None)

        Returns:
            Path to workspace or None if not found
        """
        if visibility:
            path = self.workspace_root / visibility / codename
            return path if path.exists() else None

        # Search all visibility directories
        for vis in ["public", "private", "forked", "imported"]:
            path = self.workspace_root / vis / codename
            if path.exists():
                return path

        return None

    def read_meta(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
        """Read and parse meta.json from theme workspace.

        Args:
            codename: Theme codename
            visibility: Optional visibility filter

        Returns:
            Parsed meta.json dictionary

        Raises:
            FileNotFoundError: If workspace or meta.json not found
            ValueError: If meta.json is invalid
        """
        workspace_path = self.get_workspace_path(codename, visibility)
        if not workspace_path:
            raise FileNotFoundError(f"Theme workspace not found: {codename}")

        meta_path = workspace_path / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"meta.json not found in workspace: {workspace_path}")

        meta, errors = load_meta(meta_path)
        if errors:
            raise ValueError(f"Invalid meta.json: {', '.join(errors)}")

        return meta

    def write_meta(
        self,
        codename: str,
        meta: Dict[str, Any],
        visibility: Optional[str] = None
    ) -> None:
        """Write meta.json to theme workspace.

        Args:
            codename: Theme codename
            meta: Metadata dictionary to write
            visibility: Optional visibility filter

        Raises:
            FileNotFoundError: If workspace not found
            ValueError: If meta validation fails
        """
        workspace_path = self.get_workspace_path(codename, visibility)
        if not workspace_path:
            raise FileNotFoundError(f"Theme workspace not found: {codename}")

        # Validate before writing
        is_valid, errors = validate_meta(meta)
        if not is_valid:
            raise ValueError(f"Invalid metadata: {', '.join(errors)}")

        meta_path = workspace_path / "meta.json"
        success, save_errors = save_meta(meta, meta_path)
        if not success:
            raise ValueError(f"Failed to save meta.json: {', '.join(save_errors)}")

    def validate_workspace(self, codename: str, visibility: Optional[str] = None) -> List[str]:
        """Validate theme workspace structure and contents.

        Args:
            codename: Theme codename
            visibility: Optional visibility filter

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        workspace_path = self.get_workspace_path(codename, visibility)
        if not workspace_path:
            errors.append(f"Workspace not found: {codename}")
            return errors

        # Check required directories
        required_dirs = ["stylesheets", "templates", "images"]
        for dir_path in required_dirs:
            if not (workspace_path / dir_path).exists():
                errors.append(f"Missing required directory: {dir_path}")

        # Check meta.json
        meta_path = workspace_path / "meta.json"
        if not meta_path.exists():
            errors.append("Missing meta.json")
        else:
            meta, load_errors = load_meta(meta_path)
            if load_errors:
                errors.extend([f"meta.json: {err}" for err in load_errors])
            elif meta:
                is_valid, validation_errors = validate_meta(meta)
                if not is_valid:
                    errors.extend([f"meta.json validation: {err}" for err in validation_errors])

                # Check theme-specific fields
                if meta.get("project_type") != "theme":
                    errors.append("meta.json project_type must be 'theme'")
                if "stylesheets" not in meta:
                    errors.append("meta.json missing 'stylesheets' array")

        # Check for at least one CSS file
        stylesheets_dir = workspace_path / "stylesheets"
        css_files = list(stylesheets_dir.glob("*.css"))
        if not css_files:
            errors.append("No CSS file found in stylesheets/ directory")

        return errors

    def list_themes(self, visibility: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all themes in workspace.

        Args:
            visibility: Optional filter ("public" or "private")

        Returns:
            List of theme info dictionaries with codename, visibility, workspace_path
        """
        themes = []

        visibilities = [visibility] if visibility else ["public", "private"]

        for vis in visibilities:
            vis_dir = self.workspace_root / vis
            if not vis_dir.exists():
                continue

            for theme_dir in vis_dir.iterdir():
                if theme_dir.is_dir():
                    theme_info = {
                        "codename": theme_dir.name,
                        "visibility": vis,
                        "workspace_path": str(theme_dir),
                        "has_meta": (theme_dir / "meta.json").exists()
                    }

                    # Try to load meta for additional info
                    if theme_info["has_meta"]:
                        try:
                            meta = self.read_meta(theme_dir.name, vis)
                            theme_info.update({
                                "display_name": meta.get("display_name"),
                                "version": meta.get("version"),
                                "type": meta.get("type"),
                                "parent_theme": meta.get("parent_theme"),
                                "stylesheets": meta.get("stylesheets", [])
                            })
                        except Exception:
                            pass

                    themes.append(theme_info)

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
