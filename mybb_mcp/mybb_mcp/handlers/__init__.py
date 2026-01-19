"""Handler modules for MyBB MCP tools.

This package contains modularized handlers extracted from server.py.
Each handler module groups related tools and exports a HANDLERS dict.
"""

from .dispatcher import dispatch_tool, HANDLER_REGISTRY

__all__ = ["dispatch_tool", "HANDLER_REGISTRY"]
