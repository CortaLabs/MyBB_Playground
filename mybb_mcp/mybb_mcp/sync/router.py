"""Path parsing and routing for disk sync.

Handles both mybb_sync paths (original) and plugin_manager workspace paths (extended).
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class ParsedPath:
    """Parsed file path information.

    Attributes:
        type: File type (template, stylesheet, plugin_template, plugin_php,
              plugin_lang, theme_template, or unknown)
        set_name: Template set name (for templates)
        group_name: Template group name (for templates, used on export only)
        template_name: Template title without .html extension (for templates)
        theme_name: Theme name (for stylesheets)
        stylesheet_name: Stylesheet filename including .css (for stylesheets)
        raw_path: Original path string

        # Extended fields for plugin_manager workspace paths
        project_name: Plugin or theme codename (for workspace paths)
        visibility: 'public' or 'private' (for workspace paths)
        file_type: Specific file type (template, stylesheet, php, lang)
        relative_path: Path relative to project directory
    """
    type: Literal[
        "template", "stylesheet", "unknown",
        # Extended types for plugin_manager workspace
        "plugin_template", "plugin_php", "plugin_lang",
        "theme_template", "theme_stylesheet"
    ]
    set_name: str | None = None
    group_name: str | None = None
    template_name: str | None = None
    theme_name: str | None = None
    stylesheet_name: str | None = None
    raw_path: str = ""

    # Extended fields for plugin_manager workspace paths
    project_name: str | None = None
    visibility: str | None = None
    file_type: str | None = None
    relative_path: str | None = None


class PathRouter:
    """Parse and build file paths for disk sync.

    Handles both mybb_sync paths (original) and plugin_manager workspace paths (extended).
    """

    def __init__(self, sync_root: Path, workspace_root: Optional[Path] = None):
        """Initialize PathRouter.

        Args:
            sync_root: Root directory for synced files (mybb_sync/)
            workspace_root: Optional root for plugin_manager workspace
        """
        self.sync_root = sync_root
        self.workspace_root = workspace_root

    def parse(self, relative_path: str) -> ParsedPath:
        """Parse a relative file path to extract type and metadata.

        Expected patterns (mybb_sync):
            Templates: template_sets/{set_name}/{group_name}/{template_name}.html
            Stylesheets: styles/{theme_name}/{stylesheet_name}.css

        Extended patterns (plugin_manager workspace):
            Plugin templates: plugins/{vis}/{name}/templates/*.html
            Plugin PHP: plugins/{vis}/{name}/src/*.php
            Plugin lang: plugins/{vis}/{name}/languages/*/*.php
            Theme stylesheets: themes/{vis}/{name}/stylesheets/*.css
            Theme templates: themes/{vis}/{name}/templates/*.html

        Args:
            relative_path: Path relative to sync_root or workspace_root

        Returns:
            ParsedPath with extracted metadata, type='unknown' if invalid
        """
        path = Path(relative_path)
        parts = path.parts

        # Check if this is a plugin_manager workspace path
        if len(parts) >= 1 and parts[0] in ("plugins", "themes"):
            return self._parse_workspace_path(path, parts, relative_path)

        # Original mybb_sync path parsing below

        # Template path: template_sets/{set_name}/{group_name}/{template_name}.html
        if len(parts) >= 4 and parts[0] == "template_sets" and path.suffix == ".html":
            return ParsedPath(
                type="template",
                set_name=parts[1],
                group_name=parts[2],
                template_name=path.stem,  # filename without .html
                raw_path=relative_path,
            )

        # Stylesheet path: styles/{theme_name}/{stylesheet_name}.css
        if len(parts) >= 3 and parts[0] == "styles" and path.suffix == ".css":
            return ParsedPath(
                type="stylesheet",
                theme_name=parts[1],
                stylesheet_name=path.name,  # filename with .css
                raw_path=relative_path,
            )

        # Unknown/invalid path
        return ParsedPath(
            type="unknown",
            raw_path=relative_path,
        )

    def _parse_workspace_path(self, path: Path, parts: tuple, relative_path: str) -> ParsedPath:
        """Parse plugin_manager workspace paths.

        Args:
            path: Path object
            parts: Path parts tuple
            relative_path: Original relative path string

        Returns:
            ParsedPath with workspace metadata
        """
        # Need at least: {plugins|themes}/{visibility}/{codename}/{subdir}/{file}
        if len(parts) < 5:
            return ParsedPath(type="unknown", raw_path=relative_path)

        project_type = parts[0]  # 'plugins' or 'themes'
        visibility = parts[1]    # 'public' or 'private'
        codename = parts[2]      # project codename
        subdir = parts[3]        # 'templates', 'stylesheets', 'src', 'languages'

        # Validate visibility
        if visibility not in ('public', 'private'):
            return ParsedPath(type="unknown", raw_path=relative_path)

        # Route plugin files
        if project_type == 'plugins':
            return self._parse_plugin_path(path, visibility, codename, subdir, parts, relative_path)

        # Route theme files
        if project_type == 'themes':
            return self._parse_theme_path(path, visibility, codename, subdir, parts, relative_path)

        return ParsedPath(type="unknown", raw_path=relative_path)

    def _parse_plugin_path(
        self,
        path: Path,
        visibility: str,
        codename: str,
        subdir: str,
        parts: tuple,
        relative_path: str
    ) -> ParsedPath:
        """Parse plugin workspace file paths.

        Args:
            path: Full path to file
            visibility: 'public' or 'private'
            codename: Plugin codename
            subdir: Subdirectory ('templates', 'templates_themes', 'src', 'languages')
            parts: Path parts tuple
            relative_path: Original relative path

        Returns:
            ParsedPath for the plugin file
        """
        # Plugin templates: plugins/{vis}/{name}/templates/*.html
        if subdir == 'templates' and path.suffix == '.html':
            return ParsedPath(
                type='plugin_template',
                project_name=codename,
                visibility=visibility,
                file_type='template',
                template_name=path.stem,
                relative_path=str(Path(*parts[3:])),
                raw_path=relative_path
            )

        # Theme-specific plugin templates: plugins/{vis}/{name}/templates_themes/{theme_name}/*.html
        if subdir == 'templates_themes' and path.suffix == '.html' and len(parts) >= 6:
            theme_name = parts[4]  # Extract theme name from path
            return ParsedPath(
                type='plugin_template',
                project_name=codename,
                visibility=visibility,
                file_type='template',
                template_name=path.stem,
                theme_name=theme_name,  # Theme-specific template
                relative_path=str(Path(*parts[3:])),
                raw_path=relative_path
            )

        # Plugin PHP: plugins/{vis}/{name}/src/*.php
        if subdir == 'src' and path.suffix == '.php':
            return ParsedPath(
                type='plugin_php',
                project_name=codename,
                visibility=visibility,
                file_type='php',
                relative_path=str(Path(*parts[3:])),
                raw_path=relative_path
            )

        # Plugin language: plugins/{vis}/{name}/languages/*/*.php
        if subdir == 'languages' and path.suffix == '.php':
            return ParsedPath(
                type='plugin_lang',
                project_name=codename,
                visibility=visibility,
                file_type='lang',
                relative_path=str(Path(*parts[3:])),
                raw_path=relative_path
            )

        return ParsedPath(type="unknown", raw_path=relative_path)

    def _parse_theme_path(
        self,
        path: Path,
        visibility: str,
        codename: str,
        subdir: str,
        parts: tuple,
        relative_path: str
    ) -> ParsedPath:
        """Parse theme workspace file paths.

        Args:
            path: Full path to file
            visibility: 'public' or 'private'
            codename: Theme codename
            subdir: Subdirectory ('stylesheets', 'templates')
            parts: Path parts tuple
            relative_path: Original relative path

        Returns:
            ParsedPath for the theme file
        """
        # Theme stylesheets: themes/{vis}/{name}/stylesheets/*.css
        if subdir == 'stylesheets' and path.suffix == '.css':
            return ParsedPath(
                type='theme_stylesheet',
                project_name=codename,
                visibility=visibility,
                file_type='stylesheet',
                theme_name=codename,
                stylesheet_name=path.name,
                relative_path=str(Path(*parts[3:])),
                raw_path=relative_path
            )

        # Theme template overrides: themes/{vis}/{name}/templates/*.html
        if subdir == 'templates' and path.suffix == '.html':
            return ParsedPath(
                type='theme_template',
                project_name=codename,
                visibility=visibility,
                file_type='template',
                template_name=path.stem,
                relative_path=str(Path(*parts[3:])),
                raw_path=relative_path
            )

        return ParsedPath(type="unknown", raw_path=relative_path)

    def build_template_path(self, set_name: str, group: str, title: str) -> Path:
        """Build file path for a template.

        Args:
            set_name: Template set name
            group: Template group name
            title: Template title (without .html extension)

        Returns:
            Absolute path: {sync_root}/template_sets/{set_name}/{group}/{title}.html
        """
        return self.sync_root / "template_sets" / set_name / group / f"{title}.html"

    def build_stylesheet_path(self, theme_name: str, name: str) -> Path:
        """Build file path for a stylesheet.

        Args:
            theme_name: Theme name
            name: Stylesheet filename (should include .css extension)

        Returns:
            Absolute path: {sync_root}/styles/{theme_name}/{name}
        """
        # Ensure .css extension
        if not name.endswith(".css"):
            name = f"{name}.css"
        return self.sync_root / "styles" / theme_name / name

    # -------------------------------------------------------------------------
    # Extended path builders for plugin_manager workspace
    # -------------------------------------------------------------------------

    def build_plugin_template_path(
        self, codename: str, visibility: str, template_name: str
    ) -> Path:
        """Build file path for a plugin template.

        Args:
            codename: Plugin codename
            visibility: 'public' or 'private'
            template_name: Template name without .html

        Returns:
            Absolute path: {workspace_root}/plugins/{visibility}/{codename}/templates/{template_name}.html
        """
        if self.workspace_root is None:
            raise ValueError("workspace_root not configured for workspace paths")
        return self.workspace_root / "plugins" / visibility / codename / "templates" / f"{template_name}.html"

    def build_plugin_php_path(self, codename: str, visibility: str) -> Path:
        """Build file path for a plugin's main PHP file.

        Args:
            codename: Plugin codename
            visibility: 'public' or 'private'

        Returns:
            Absolute path: {workspace_root}/plugins/{visibility}/{codename}/src/{codename}.php
        """
        if self.workspace_root is None:
            raise ValueError("workspace_root not configured for workspace paths")
        return self.workspace_root / "plugins" / visibility / codename / "src" / f"{codename}.php"

    def build_plugin_lang_path(
        self, codename: str, visibility: str, lang: str = "english"
    ) -> Path:
        """Build file path for a plugin's language file.

        Args:
            codename: Plugin codename
            visibility: 'public' or 'private'
            lang: Language name (default 'english')

        Returns:
            Absolute path: {workspace_root}/plugins/{visibility}/{codename}/languages/{lang}/{codename}.lang.php
        """
        if self.workspace_root is None:
            raise ValueError("workspace_root not configured for workspace paths")
        return self.workspace_root / "plugins" / visibility / codename / "languages" / lang / f"{codename}.lang.php"

    def build_theme_stylesheet_path(
        self, codename: str, visibility: str, stylesheet_name: str
    ) -> Path:
        """Build file path for a theme stylesheet.

        Args:
            codename: Theme codename
            visibility: 'public' or 'private'
            stylesheet_name: Stylesheet name (should include .css)

        Returns:
            Absolute path: {workspace_root}/themes/{visibility}/{codename}/stylesheets/{stylesheet_name}
        """
        if self.workspace_root is None:
            raise ValueError("workspace_root not configured for workspace paths")
        if not stylesheet_name.endswith('.css'):
            stylesheet_name = f"{stylesheet_name}.css"
        return self.workspace_root / "themes" / visibility / codename / "stylesheets" / stylesheet_name

    def build_theme_template_path(
        self, codename: str, visibility: str, template_name: str
    ) -> Path:
        """Build file path for a theme template override.

        Args:
            codename: Theme codename
            visibility: 'public' or 'private'
            template_name: Template name without .html

        Returns:
            Absolute path: {workspace_root}/themes/{visibility}/{codename}/templates/{template_name}.html
        """
        if self.workspace_root is None:
            raise ValueError("workspace_root not configured for workspace paths")
        return self.workspace_root / "themes" / visibility / codename / "templates" / f"{template_name}.html"
