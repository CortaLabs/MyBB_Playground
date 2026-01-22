"""PHP bridge client for MyBB-native operations.

This module is intentionally small and transport-focused: it invokes the CLI
bridge (`mcp_bridge.php`) and returns parsed, structured results.
"""

from .client import BridgeResult, MyBBBridgeClient

__all__ = ["BridgeResult", "MyBBBridgeClient"]

