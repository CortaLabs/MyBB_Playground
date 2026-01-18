"""MCP tool invocation helpers for MyBB operations.

This module provides wrapper functions for calling MyBB MCP tools,
handling responses and errors gracefully.
"""

from typing import Dict, List, Any, Optional
import json


class MCPClientError(Exception):
    """Exception raised when MCP tool invocation fails."""
    pass


def call_create_plugin(
    codename: str,
    name: str,
    description: str = "",
    author: str = "Developer",
    version: str = "1.0.0",
    hooks: Optional[List[str]] = None,
    has_settings: bool = False,
    has_templates: bool = False,
    has_database: bool = False
) -> Dict[str, Any]:
    """Call mybb_create_plugin MCP tool.

    NOTE: This function returns a mock response structure.
    In actual implementation, this would invoke the MCP tool via the MCP protocol.
    For now, it returns the expected structure for testing and integration.

    Args:
        codename: Plugin codename (lowercase, underscores)
        name: Plugin display name
        description: Plugin description
        author: Author name
        version: Version string
        hooks: List of hook names to register
        has_settings: Whether plugin has settings
        has_templates: Whether plugin has templates
        has_database: Whether plugin has database tables

    Returns:
        Dictionary with:
        - success: bool
        - message: str
        - files_created: List[str] (paths to generated files)
        - plugin_path: str (path to main PHP file)

    Raises:
        MCPClientError: If MCP call fails or returns error
    """
    if not codename or not name:
        raise MCPClientError("codename and name are required")

    hooks = hooks or []

    # TODO: Replace with actual MCP tool invocation
    # For now, return mock response structure
    return {
        "success": True,
        "message": f"Plugin '{name}' scaffolded successfully",
        "files_created": [
            f"inc/plugins/{codename}.php",
            f"inc/languages/english/{codename}.lang.php"
        ],
        "plugin_path": f"inc/plugins/{codename}.php",
        "codename": codename,
        "hooks_registered": hooks,
        "has_settings": has_settings,
        "has_templates": has_templates,
        "has_database": has_database
    }


def call_list_themes() -> List[Dict[str, Any]]:
    """Call mybb_list_themes MCP tool.

    Returns:
        List of theme dictionaries with tid, name, pid (parent ID)

    Raises:
        MCPClientError: If MCP call fails
    """
    # TODO: Replace with actual MCP tool invocation
    # For now, return mock response
    return [
        {"tid": 1, "name": "Default Theme", "pid": 0},
        {"tid": 2, "name": "Custom Theme", "pid": 1}
    ]


def call_list_stylesheets(tid: int) -> List[Dict[str, Any]]:
    """Call mybb_list_stylesheets MCP tool for a specific theme.

    Args:
        tid: Theme ID

    Returns:
        List of stylesheet dictionaries with sid, name, tid

    Raises:
        MCPClientError: If MCP call fails
    """
    if tid < 1:
        raise MCPClientError("tid must be >= 1")

    # TODO: Replace with actual MCP tool invocation
    # For now, return mock response
    return [
        {"sid": 1, "name": "global.css", "tid": tid},
        {"sid": 2, "name": "colors.css", "tid": tid}
    ]


def call_read_stylesheet(sid: int) -> Dict[str, Any]:
    """Call mybb_read_stylesheet MCP tool.

    Args:
        sid: Stylesheet ID

    Returns:
        Dictionary with sid, name, stylesheet (CSS content), tid

    Raises:
        MCPClientError: If MCP call fails
    """
    if sid < 1:
        raise MCPClientError("sid must be >= 1")

    # TODO: Replace with actual MCP tool invocation
    # For now, return mock response
    return {
        "sid": sid,
        "name": "global.css",
        "stylesheet": "/* CSS content */",
        "tid": 1
    }


def validate_parent_theme(parent_theme: str) -> bool:
    """Validate that a parent theme exists in MyBB.

    Args:
        parent_theme: Parent theme name

    Returns:
        True if theme exists, False otherwise
    """
    try:
        themes = call_list_themes()
        return any(theme["name"] == parent_theme for theme in themes)
    except MCPClientError:
        return False


def get_theme_stylesheets(theme_name: str) -> List[str]:
    """Get list of stylesheet names for a theme.

    Args:
        theme_name: Theme name

    Returns:
        List of stylesheet names

    Raises:
        MCPClientError: If theme not found or MCP call fails
    """
    themes = call_list_themes()
    theme = next((t for t in themes if t["name"] == theme_name), None)

    if not theme:
        raise MCPClientError(f"Theme not found: {theme_name}")

    stylesheets = call_list_stylesheets(theme["tid"])
    return [s["name"] for s in stylesheets]


def parse_mcp_response(response: Any) -> Dict[str, Any]:
    """Parse and validate MCP tool response.

    Args:
        response: Raw MCP response (could be string, dict, etc.)

    Returns:
        Parsed response dictionary

    Raises:
        MCPClientError: If response is invalid or indicates error
    """
    if isinstance(response, dict):
        if "error" in response:
            raise MCPClientError(f"MCP error: {response['error']}")
        return response

    if isinstance(response, str):
        try:
            parsed = json.loads(response)
            if "error" in parsed:
                raise MCPClientError(f"MCP error: {parsed['error']}")
            return parsed
        except json.JSONDecodeError:
            # Assume it's a plain text success message
            return {"success": True, "message": response}

    raise MCPClientError(f"Unexpected MCP response type: {type(response)}")


def handle_mcp_error(error: Exception) -> None:
    """Handle MCP tool errors with appropriate logging.

    Args:
        error: Exception from MCP call

    Raises:
        MCPClientError: Always raises with formatted error message
    """
    if isinstance(error, MCPClientError):
        raise error

    # Wrap other exceptions
    raise MCPClientError(f"MCP invocation failed: {str(error)}") from error
