"""Base installer class for plugins and themes.

This module provides the abstract BaseInstaller class that eliminates code
duplication between PluginInstaller and ThemeInstaller by extracting common
initialization patterns and database operation helpers.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional

from ..config import Config
from ..database import ProjectDatabase
from .workspace import BaseWorkspace


class BaseInstaller(ABC):
    """Abstract base class for plugin and theme installers.

    This class provides shared initialization and helper methods that are
    common to both PluginInstaller and ThemeInstaller, eliminating code
    duplication.

    Shared functionality:
    - Common initialization (__init__)
    - Project status updates (_update_project_status)
    - History entry creation (_add_history_entry)

    Type-specific functionality (must be implemented by subclasses):
    - install() - Deploy to TestForum
    - uninstall() - Remove from TestForum

    Note:
        This is an abstract class and cannot be instantiated directly.
        Use PluginInstaller or ThemeInstaller instead.
    """

    def __init__(
        self,
        config: Config,
        db: ProjectDatabase,
        workspace: BaseWorkspace
    ):
        """Initialize installer with common dependencies.

        Args:
            config: Plugin manager configuration
            db: Project database for tracking deployments
            workspace: Workspace manager (PluginWorkspace or ThemeWorkspace)

        Note:
            The workspace parameter accepts BaseWorkspace type to support
            both plugin and theme workspaces through polymorphism.
        """
        self.config = config
        self.db = db
        self.workspace = workspace
        self.mybb_root = config.mybb_root

    def _update_project_status(
        self,
        codename: str,
        status: str,
        warnings: Optional[list] = None
    ) -> None:
        """Update project installation status in database.

        This helper method provides consistent error handling for status
        updates across both plugin and theme installers.

        Args:
            codename: Project codename
            status: New status ('installed', 'uninstalled', etc.)
            warnings: Optional list to append warnings to

        Note:
            Errors are caught and added to warnings list if provided,
            otherwise silently ignored. This matches the pattern used
            in both PluginInstaller and ThemeInstaller.
        """
        try:
            update_data = {
                "codename": codename,
                "status": status
            }

            # Add timestamp for install/uninstall actions
            if status == "installed":
                update_data["installed_at"] = datetime.utcnow().isoformat()
            elif status == "uninstalled":
                update_data["installed_at"] = None

            self.db.update_project(**update_data)

        except Exception as e:
            if warnings is not None:
                warnings.append(f"Database update failed: {str(e)}")

    def _add_history_entry(
        self,
        codename: str,
        action: str,
        details: str,
        warnings: Optional[list] = None
    ) -> None:
        """Add installation history entry to database.

        This helper method provides consistent error handling for history
        entries across both plugin and theme installers.

        Args:
            codename: Project codename
            action: Action performed ('installed', 'uninstalled', etc.)
            details: Description of what was done
            warnings: Optional list to append warnings to

        Note:
            Errors are caught and added to warnings list if provided,
            otherwise silently ignored. This matches the pattern used
            in both PluginInstaller and ThemeInstaller.
        """
        try:
            project = self.db.get_project(codename)
            if project:
                self.db.add_history(
                    project_id=project['id'],
                    action=action,
                    details=details
                )
        except Exception as e:
            if warnings is not None:
                warnings.append(f"History entry failed: {str(e)}")

    @abstractmethod
    def install(
        self,
        codename: str,
        visibility: Optional[str] = None
    ) -> Dict[str, Any]:
        """Deploy project to TestForum.

        Args:
            codename: Project codename
            visibility: 'public' or 'private' (uses default if None)

        Returns:
            Dict with deployment status and details

        Note:
            Must be implemented by subclass (PluginInstaller or ThemeInstaller).
        """
        pass

    @abstractmethod
    def uninstall(
        self,
        codename: str,
        visibility: Optional[str] = None
    ) -> Dict[str, Any]:
        """Remove project from TestForum.

        Args:
            codename: Project codename
            visibility: 'public' or 'private' (uses default if None)

        Returns:
            Dict with removal status and details

        Note:
            Must be implemented by subclass (PluginInstaller or ThemeInstaller).
        """
        pass
