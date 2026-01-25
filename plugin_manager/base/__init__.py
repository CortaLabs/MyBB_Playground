"""
Base classes for Plugin Manager workspace components.

This module provides abstract base classes that define common functionality
shared between plugin and theme workspaces. The base classes enforce consistent
interfaces for workspace operations, installation, and packaging.

Components:
    - BaseWorkspace: Abstract base for PluginWorkspace and ThemeWorkspace
    - BaseInstaller: Abstract base for PluginInstaller and ThemeInstaller
    - BasePackager: Abstract base for plugin and theme packaging operations

The base classes eliminate code duplication while allowing plugin and theme
implementations to specialize their behavior where needed.
"""

from .workspace import BaseWorkspace
from .installer import BaseInstaller
from .packager import BasePackager

__all__ = ["BaseWorkspace", "BaseInstaller", "BasePackager"]
