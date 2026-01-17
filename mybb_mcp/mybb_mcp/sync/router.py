"""Path parsing and routing for disk sync."""

from pathlib import Path
from dataclasses import dataclass
from typing import Literal


@dataclass
class ParsedPath:
    """Parsed file path information.

    Attributes:
        type: File type (template, stylesheet, or unknown)
        set_name: Template set name (for templates)
        group_name: Template group name (for templates, used on export only)
        template_name: Template title without .html extension (for templates)
        theme_name: Theme name (for stylesheets)
        stylesheet_name: Stylesheet filename including .css (for stylesheets)
        raw_path: Original path string
    """
    type: Literal["template", "stylesheet", "unknown"]
    set_name: str | None = None
    group_name: str | None = None
    template_name: str | None = None
    theme_name: str | None = None
    stylesheet_name: str | None = None
    raw_path: str = ""


class PathRouter:
    """Parse and build file paths for disk sync."""

    def __init__(self, sync_root: Path):
        """Initialize PathRouter.

        Args:
            sync_root: Root directory for synced files
        """
        self.sync_root = sync_root

    def parse(self, relative_path: str) -> ParsedPath:
        """Parse a relative file path to extract type and metadata.

        Expected patterns:
            Templates: template_sets/{set_name}/{group_name}/{template_name}.html
            Stylesheets: styles/{theme_name}/{stylesheet_name}.css

        Args:
            relative_path: Path relative to sync_root

        Returns:
            ParsedPath with extracted metadata, type='unknown' if invalid
        """
        path = Path(relative_path)
        parts = path.parts

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
