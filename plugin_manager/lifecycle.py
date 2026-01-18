"""PHP Lifecycle Bridge - Execute MyBB plugin lifecycle functions via CLI.

This module provides a Python wrapper around the MCP Bridge PHP script,
enabling execution of MyBB plugin lifecycle functions (_install, _activate,
_deactivate, _uninstall) through subprocess calls.

The bridge bootstraps MyBB properly and uses MyBB's own systems for all
operations - no reimplementations or workarounds.
"""

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BridgeResult:
    """Result from a bridge operation."""
    success: bool
    action: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: Optional[str] = None

    @classmethod
    def from_json(cls, action: str, json_data: Dict[str, Any]) -> 'BridgeResult':
        """Create BridgeResult from JSON response."""
        return cls(
            success=json_data.get('success', False),
            action=action,
            data=json_data.get('data', {}),
            error=json_data.get('error'),
            timestamp=json_data.get('timestamp')
        )

    @classmethod
    def from_error(cls, action: str, error: str) -> 'BridgeResult':
        """Create error BridgeResult."""
        return cls(
            success=False,
            action=action,
            error=error
        )


class PluginLifecycle:
    """Execute MyBB plugin lifecycle functions via PHP bridge.

    This class provides methods to activate, deactivate, and query plugin
    status through the MCP Bridge PHP script. All operations bootstrap
    MyBB properly and use MyBB's native plugin system.

    Example:
        lifecycle = PluginLifecycle(Path("/path/to/TestForum"))
        result = lifecycle.activate("my_plugin")
        if result.success:
            print(f"Plugin activated: {result.data}")
    """

    def __init__(
        self,
        mybb_root: Path,
        php_binary: str = "php",
        timeout: int = 30
    ):
        """Initialize the lifecycle manager.

        Args:
            mybb_root: Path to MyBB installation (e.g., TestForum/)
            php_binary: Path to PHP binary (default: "php")
            timeout: Subprocess timeout in seconds (default: 30)
        """
        self.mybb_root = Path(mybb_root).resolve()
        self.php_binary = php_binary
        self.timeout = timeout
        self.bridge_path = self.mybb_root / "mcp_bridge.php"

        if not self.bridge_path.exists():
            raise FileNotFoundError(
                f"MCP Bridge not found at {self.bridge_path}. "
                "Ensure mcp_bridge.php is installed in MyBB root."
            )

    def _call_bridge(self, action: str, **kwargs) -> BridgeResult:
        """Execute a bridge action via subprocess.

        Args:
            action: The bridge action (e.g., "plugin:activate")
            **kwargs: Additional arguments to pass to the bridge

        Returns:
            BridgeResult with success status and data
        """
        cmd = [
            self.php_binary,
            str(self.bridge_path),
            f"--action={action}",
            "--json"
        ]

        # Add optional arguments
        for key, value in kwargs.items():
            if value is True:
                cmd.append(f"--{key}")
            elif value is not None and value is not False:
                cmd.append(f"--{key}={value}")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.mybb_root),
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            # Parse JSON output
            try:
                json_output = json.loads(result.stdout)
                return BridgeResult.from_json(action, json_output)
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw output as error
                error_msg = result.stderr or result.stdout or "Unknown error"
                return BridgeResult.from_error(action, f"Invalid JSON response: {error_msg}")

        except subprocess.TimeoutExpired:
            return BridgeResult.from_error(action, f"Operation timed out after {self.timeout}s")
        except FileNotFoundError:
            return BridgeResult.from_error(action, f"PHP binary not found: {self.php_binary}")
        except Exception as e:
            return BridgeResult.from_error(action, str(e))

    # =========================================================================
    # Plugin Operations
    # =========================================================================

    def get_status(self, codename: str) -> BridgeResult:
        """Get plugin status and info.

        Args:
            codename: Plugin codename (without .php)

        Returns:
            BridgeResult with plugin info including:
            - is_installed: Whether _is_installed() returns true
            - is_active: Whether plugin is in active cache
            - is_compatible: Whether plugin is compatible with MyBB version
            - info: Plugin info from _info() function
        """
        return self._call_bridge("plugin:status", plugin=codename)

    def activate(self, codename: str, force: bool = False) -> BridgeResult:
        """Activate a plugin (runs _install and _activate if needed).

        This mirrors MyBB Admin CP behavior:
        1. Check compatibility (unless force=True)
        2. Run _install() if not installed and function exists
        3. Run _activate() if function exists
        4. Update plugins cache

        Args:
            codename: Plugin codename (without .php)
            force: Skip compatibility check

        Returns:
            BridgeResult with actions_taken list
        """
        return self._call_bridge(
            "plugin:activate",
            plugin=codename,
            force=force if force else None
        )

    def deactivate(self, codename: str, uninstall: bool = False) -> BridgeResult:
        """Deactivate a plugin (optionally uninstall).

        This mirrors MyBB Admin CP behavior:
        1. Run _deactivate() if function exists
        2. Run _uninstall() if uninstall=True and function exists
        3. Update plugins cache

        Args:
            codename: Plugin codename (without .php)
            uninstall: Also run _uninstall() function

        Returns:
            BridgeResult with actions_taken list
        """
        return self._call_bridge(
            "plugin:deactivate",
            plugin=codename,
            uninstall=uninstall if uninstall else None
        )

    def list_plugins(self) -> BridgeResult:
        """List all plugins with their status.

        Returns:
            BridgeResult with plugins list containing:
            - codename, name, version, author
            - is_active, is_installed, is_compatible
        """
        return self._call_bridge("plugin:list")

    # =========================================================================
    # MyBB Info
    # =========================================================================

    def get_mybb_info(self) -> BridgeResult:
        """Get MyBB installation info.

        Returns:
            BridgeResult with MyBB version, PHP version, database info, etc.
        """
        return self._call_bridge("info")

    # =========================================================================
    # Cache Operations
    # =========================================================================

    def read_cache(self, cache_name: str) -> BridgeResult:
        """Read a MyBB cache entry.

        Args:
            cache_name: Name of cache to read (e.g., "plugins", "settings")

        Returns:
            BridgeResult with cache data
        """
        return self._call_bridge("cache:read", cache=cache_name)

    def rebuild_cache(self) -> BridgeResult:
        """Rebuild MyBB settings cache.

        Returns:
            BridgeResult indicating success
        """
        return self._call_bridge("cache:rebuild")


# Convenience function for quick operations
def activate_plugin(
    mybb_root: Path,
    codename: str,
    force: bool = False,
    php_binary: str = "php"
) -> BridgeResult:
    """Convenience function to activate a plugin.

    Args:
        mybb_root: Path to MyBB installation
        codename: Plugin codename
        force: Skip compatibility check
        php_binary: Path to PHP binary

    Returns:
        BridgeResult
    """
    lifecycle = PluginLifecycle(mybb_root, php_binary)
    return lifecycle.activate(codename, force)


def deactivate_plugin(
    mybb_root: Path,
    codename: str,
    uninstall: bool = False,
    php_binary: str = "php"
) -> BridgeResult:
    """Convenience function to deactivate a plugin.

    Args:
        mybb_root: Path to MyBB installation
        codename: Plugin codename
        uninstall: Also run uninstall function
        php_binary: Path to PHP binary

    Returns:
        BridgeResult
    """
    lifecycle = PluginLifecycle(mybb_root, php_binary)
    return lifecycle.deactivate(codename, uninstall)
