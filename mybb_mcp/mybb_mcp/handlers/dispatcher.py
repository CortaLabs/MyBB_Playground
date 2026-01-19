"""Central dispatcher for MCP tool handlers."""

from typing import Dict, Callable, Any

# Registry mapping tool names to handler functions
HANDLER_REGISTRY: Dict[str, Callable] = {}


async def dispatch_tool(
    name: str,
    args: dict,
    db: Any,
    config: Any,
    sync_service: Any
) -> str:
    """Dispatch an MCP tool call to its registered handler.

    Args:
        name: Tool name (e.g., "mybb_db_query")
        args: Tool arguments dict
        db: MyBBDatabase instance
        config: Server configuration
        sync_service: Disk sync service instance

    Returns:
        Handler response as markdown string

    Raises:
        No exceptions - returns error messages as strings
    """
    handler = HANDLER_REGISTRY.get(name)

    if handler is None:
        return f"Unknown tool: {name}"

    try:
        # Call the handler with all parameters
        result = await handler(args, db, config, sync_service)
        return result
    except Exception as e:
        return f"Error executing {name}: {str(e)}"


# Import and register handler modules
from .database import DATABASE_HANDLERS
from .tasks import TASK_HANDLERS
from .admin import ADMIN_HANDLERS
from .templates import TEMPLATE_HANDLERS
from .themes import THEME_HANDLERS
from .content import CONTENT_HANDLERS
from .search import SEARCH_HANDLERS
from .moderation import MODERATION_HANDLERS
from .users import USER_HANDLERS
from .sync import SYNC_HANDLERS
from .plugins import PLUGIN_HANDLERS
from .plugin_git import PLUGIN_GIT_HANDLERS

HANDLER_REGISTRY.update(DATABASE_HANDLERS)
HANDLER_REGISTRY.update(TASK_HANDLERS)
HANDLER_REGISTRY.update(ADMIN_HANDLERS)
HANDLER_REGISTRY.update(TEMPLATE_HANDLERS)
HANDLER_REGISTRY.update(THEME_HANDLERS)
HANDLER_REGISTRY.update(CONTENT_HANDLERS)
HANDLER_REGISTRY.update(SEARCH_HANDLERS)
HANDLER_REGISTRY.update(MODERATION_HANDLERS)
HANDLER_REGISTRY.update(USER_HANDLERS)
HANDLER_REGISTRY.update(SYNC_HANDLERS)
HANDLER_REGISTRY.update(PLUGIN_HANDLERS)
HANDLER_REGISTRY.update(PLUGIN_GIT_HANDLERS)
