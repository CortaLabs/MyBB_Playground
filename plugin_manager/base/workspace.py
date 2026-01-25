"""Base workspace management for plugin and theme development.

This module provides the abstract BaseWorkspace class that defines common
workspace operations shared between PluginWorkspace and ThemeWorkspace.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..schema import (
    validate_meta,
    load_meta,
    save_meta
)


class BaseWorkspace(ABC):
    """Abstract base class for workspace management.

    This class provides common functionality for managing plugin and theme
    workspaces, including directory creation, metadata handling, and validation.

    Subclasses must implement:
    - _create_subdirectories(): Create type-specific directory structure
    - _validate_type_specific(): Perform type-specific validation
    - item_type property: Return 'plugin' or 'theme'
    """

    def __init__(self, workspace_root: Path):
        """Initialize workspace manager.

        Args:
            workspace_root: Root directory for workspaces (e.g., plugin_manager/plugins)
        """
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def create_workspace(
        self,
        codename: str,
        visibility: str = "public"
    ) -> Path:
        """Create a new workspace directory structure.

        Args:
            codename: Item codename (lowercase, underscores)
            visibility: "public" or "private"

        Returns:
            Path to created workspace directory

        Raises:
            ValueError: If workspace already exists
        """
        workspace_path = self.workspace_root / visibility / codename

        if workspace_path.exists():
            raise ValueError(f"{self.item_type.capitalize()} workspace already exists: {workspace_path}")

        # Create main directory
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Create type-specific subdirectories (implemented by subclass)
        self._create_subdirectories(workspace_path)

        return workspace_path

    def get_workspace_path(self, codename: str, visibility: Optional[str] = None) -> Optional[Path]:
        """Find workspace path by codename.

        Args:
            codename: Item codename
            visibility: Optional visibility filter (searches all if None)

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
        """Read and parse meta.json from workspace.

        Args:
            codename: Item codename
            visibility: Optional visibility filter

        Returns:
            Parsed meta.json dictionary

        Raises:
            FileNotFoundError: If workspace or meta.json not found
            ValueError: If meta.json is invalid
        """
        workspace_path = self.get_workspace_path(codename, visibility)
        if not workspace_path:
            raise FileNotFoundError(f"{self.item_type.capitalize()} workspace not found: {codename}")

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
        """Write meta.json to workspace.

        Args:
            codename: Item codename
            meta: Metadata dictionary to write
            visibility: Optional visibility filter

        Raises:
            FileNotFoundError: If workspace not found
            ValueError: If meta validation fails
        """
        workspace_path = self.get_workspace_path(codename, visibility)
        if not workspace_path:
            raise FileNotFoundError(f"{self.item_type.capitalize()} workspace not found: {codename}")

        # Validate before writing
        is_valid, errors = validate_meta(meta)
        if not is_valid:
            raise ValueError(f"Invalid metadata: {', '.join(errors)}")

        meta_path = workspace_path / "meta.json"
        success, save_errors = save_meta(meta, meta_path)
        if not success:
            raise ValueError(f"Failed to save meta.json: {', '.join(save_errors)}")

    def validate_workspace(self, codename: str, visibility: Optional[str] = None) -> List[str]:
        """Validate workspace structure and contents.

        Args:
            codename: Item codename
            visibility: Optional visibility filter

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        workspace_path = self.get_workspace_path(codename, visibility)
        if not workspace_path:
            errors.append(f"Workspace not found: {codename}")
            return errors

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

        # Perform type-specific validation (implemented by subclass)
        type_specific_errors = self._validate_type_specific(workspace_path, codename)
        errors.extend(type_specific_errors)

        return errors

    def list_items(self, visibility: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all items in workspace.

        Args:
            visibility: Optional filter ("public" or "private")

        Returns:
            List of item info dictionaries with codename, visibility, workspace_path
        """
        items = []

        visibilities = [visibility] if visibility else ["public", "private"]

        for vis in visibilities:
            vis_dir = self.workspace_root / vis
            if not vis_dir.exists():
                continue

            for item_dir in vis_dir.iterdir():
                if item_dir.is_dir():
                    item_info = {
                        "codename": item_dir.name,
                        "visibility": vis,
                        "workspace_path": str(item_dir),
                        "has_meta": (item_dir / "meta.json").exists()
                    }

                    # Try to load meta for additional info
                    if item_info["has_meta"]:
                        try:
                            meta = self.read_meta(item_dir.name, vis)
                            item_info.update({
                                "display_name": meta.get("display_name"),
                                "version": meta.get("version"),
                                "type": meta.get("type")
                            })
                        except Exception:
                            pass

                    items.append(item_info)

        return items

    @abstractmethod
    def _create_subdirectories(self, workspace_path: Path) -> None:
        """Create type-specific subdirectories in workspace.

        Args:
            workspace_path: Path to workspace directory

        Note:
            This method is called by create_workspace() after creating the main
            workspace directory. Implement this to create the subdirectory structure
            specific to plugins or themes.
        """
        pass

    @abstractmethod
    def _validate_type_specific(self, workspace_path: Path, codename: str) -> List[str]:
        """Perform type-specific workspace validation.

        Args:
            workspace_path: Path to workspace directory
            codename: Item codename

        Returns:
            List of validation errors (empty if valid)

        Note:
            This method is called by validate_workspace() after common validation.
            Implement this to check type-specific requirements (e.g., required
            directories, file patterns, meta.json fields).
        """
        pass

    @property
    @abstractmethod
    def item_type(self) -> str:
        """Return the type of item managed by this workspace.

        Returns:
            'plugin' or 'theme'

        Note:
            This property is used for error messages and type identification.
        """
        pass
