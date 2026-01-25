"""MyBB MCP Server - AI-assisted MyBB development tools.

This server provides tools for Claude to interact with MyBB:
- Template management (list, read, write with inheritance)
- Theme/stylesheet management with cache refresh
- Plugin scaffolding and hook reference

Architecture:
- Tool definitions: mybb_mcp/tools_registry.py (85 tools)
- Tool handlers: mybb_mcp/handlers/ (modularized by category)
- Dispatcher: mybb_mcp/handlers/dispatcher.py (central routing)
"""

import asyncio
import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import load_config, MyBBConfig
from .db import MyBBDatabase
from .tools_registry import ALL_TOOLS
from .handlers import dispatch_tool, HANDLER_REGISTRY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mybb-mcp")


def create_server(config: MyBBConfig) -> Server:
    """Create and configure the MCP server with all tools.

    This function initializes:
    - Database connection pool
    - Disk sync service with file watcher
    - Tool registration with MCP server

    Args:
        config: MyBB configuration from .env

    Returns:
        Configured MCP Server instance
    """
    from .sync import DiskSyncService, SyncConfig

    server = Server("mybb-mcp")

    # Initialize database connection
    db = MyBBDatabase(config.db)

    # Initialize DiskSync service
    # Use mybb_root's parent (repo root) for sync directory
    sync_root = config.mybb_root.parent / "mybb_sync"
    sync_root.mkdir(parents=True, exist_ok=True)
    sync_config = SyncConfig(sync_root=sync_root)
    sync_service = DiskSyncService(db, sync_config, config.mybb_url, mybb_root=config.mybb_root)

    # Auto-start file watcher (dev server - always want sync on)
    sync_service.start_watcher()
    logger.info(f"File watcher started: {sync_root}")

    # Log handler registry status
    logger.info(f"Handler registry loaded: {len(HANDLER_REGISTRY)} handlers")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Return all available MCP tools."""
        return ALL_TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Route tool calls to modular handlers via dispatcher.

        Args:
            name: Tool name (e.g., "mybb_list_templates")
            arguments: Tool arguments dict

        Returns:
            List containing TextContent with handler response
        """
        try:
            result = await dispatch_tool(name, arguments, db, config, sync_service)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.exception(f"Error in tool {name}")
            return [TextContent(type="text", text=f"Error: {e}")]

    return server


async def run_server():
    """Run the MCP server with stdio transport."""
    config = load_config()
    logger.info(f"Starting MyBB MCP Server")
    logger.info(f"MyBB root: {config.mybb_root}")
    logger.info(f"Database: {config.db.database}")
    logger.info(f"Tools registered: {len(ALL_TOOLS)}")

    server = create_server(config)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
