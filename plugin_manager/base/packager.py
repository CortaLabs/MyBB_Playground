"""Abstract base class for plugin and theme packaging.

This module provides shared validation and export logic for both
PluginPackager and ThemePackager, reducing code duplication.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from plugin_manager.base.workspace import BaseWorkspace
from plugin_manager.schema import validate_meta, load_meta
from plugin_manager.database import ProjectDatabase


class BasePackager(ABC):
    """Abstract base class for packaging plugins and themes.

    Provides shared validation and README generation logic.
    Type-specific packaging (ZIP creation) is handled by subclasses.
    """

    def __init__(self, workspace: BaseWorkspace, db: ProjectDatabase):
        """Initialize base packager.

        Args:
            workspace: BaseWorkspace instance for file operations (PluginWorkspace or ThemeWorkspace)
            db: ProjectDatabase instance for history tracking
        """
        self.workspace = workspace
        self.db = db

    def validate_for_export(
        self,
        codename: str,
        visibility: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate item is ready for export.

        Performs shared validation (workspace exists, meta.json valid) and
        delegates type-specific validation to subclass.

        Args:
            codename: Item codename (plugin or theme)
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
            item_type = self.workspace.item_type
            return {
                "valid": False,
                "errors": [f"{item_type.capitalize()} '{codename}' workspace not found"],
                "warnings": [],
                "meta": None
            }

        # Validate meta.json (shared logic)
        meta_valid, meta_errors = self._validate_meta(workspace_path)
        if not meta_valid:
            errors.extend(meta_errors)

        # Load meta for type-specific validation
        meta = None
        meta_path = workspace_path / "meta.json"
        if meta_path.exists():
            meta, load_errors = load_meta(meta_path)
            if not load_errors:
                # Check version and author (shared warnings)
                if not meta.get("version") or meta.get("version") == "0.0.0":
                    warnings.append("Version should be set before export")

                if not meta.get("author"):
                    warnings.append("Author should be set before export")

        # Delegate type-specific validation to subclass
        type_specific_errors = self._validate_type_specific(workspace_path, codename)
        errors.extend(type_specific_errors)

        # Determine validity
        valid = len(errors) == 0

        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "meta": meta if valid else None
        }

    def _validate_meta(self, workspace_path: Path) -> Tuple[bool, List[str]]:
        """Validate meta.json exists and has valid schema.

        Args:
            workspace_path: Path to workspace directory

        Returns:
            Tuple of (is_valid, error_list)

        Note:
            This is shared logic extracted from both PluginPackager and ThemePackager.
            Does NOT check version/author - those are warnings handled in validate_for_export.
        """
        errors = []

        # Check meta.json exists
        meta_path = workspace_path / "meta.json"
        if not meta_path.exists():
            errors.append("meta.json not found")
            return False, errors

        # Load and validate schema
        meta, load_errors = load_meta(meta_path)
        if load_errors:
            errors.extend(load_errors)
            return False, errors

        if meta:
            # Validate against schema
            valid_schema, validation_errors = validate_meta(meta)
            if not valid_schema:
                errors.extend(validation_errors)
                return False, errors

        return True, []

    def _generate_readme_header(self, meta: Dict[str, Any]) -> str:
        """Generate README header section (shared across plugins and themes).

        Args:
            meta: Metadata dictionary from meta.json

        Returns:
            Markdown string for README header

        Note:
            This is the EXACT shared pattern from both PluginPackager and ThemePackager.
            Lines 134-144 (plugins) and 432-442 (themes) are identical.
        """
        lines = []

        # Header
        codename = meta.get("codename", "unknown")
        display_name = meta.get("display_name", codename)
        lines.append(f"# {display_name}\n")

        # Description
        if meta.get("description"):
            lines.append(f"{meta['description']}\n")

        # Metadata
        lines.append(f"**Version:** {meta.get('version', '1.0.0')}  ")
        lines.append(f"**Author:** {meta.get('author', 'Unknown')}  ")
        lines.append(f"**Compatibility:** MyBB {meta.get('mybb_compatibility', '18*')}\n")

        return "\n".join(lines)

    @abstractmethod
    def _validate_type_specific(
        self,
        workspace_path: Path,
        codename: str
    ) -> List[str]:
        """Validate type-specific requirements (plugin vs theme).

        Args:
            workspace_path: Path to workspace directory
            codename: Item codename

        Returns:
            List of validation error messages (empty if valid)

        Note:
            Subclasses implement this to check:
            - Plugins: PHP file exists, required functions present
            - Themes: Stylesheets exist, template overrides valid
        """
        pass

    @abstractmethod
    def create_package(
        self,
        codename: str,
        output_path: Path,
        visibility: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create distributable package (ZIP) for plugin or theme.

        Args:
            codename: Item codename
            output_path: Path where ZIP should be created
            visibility: Workspace visibility (public/private/None for auto-detect)

        Returns:
            {
                "success": bool,
                "path": str (if successful),
                "errors": List[str]
            }

        Note:
            Subclasses implement this to handle ZIP creation:
            - PluginPackager: create_plugin_zip()
            - ThemePackager: create_theme_zip()

            ZIP structure differs significantly between plugins and themes,
            so this CANNOT be shared in the base class.
        """
        pass
