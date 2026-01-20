"""Server orchestration handlers for MyBB MCP tools."""

from typing import Any, Optional

# Module-level singleton for service instance
_orchestration_service: Optional["ServerOrchestrationService"] = None


def get_orchestration_service(config):
    """Get or create the orchestration service singleton."""
    global _orchestration_service
    if _orchestration_service is None:
        from ..orchestration import ServerOrchestrationService
        _orchestration_service = ServerOrchestrationService(config)
    return _orchestration_service


async def handle_server_start(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Start the MyBB development server."""
    service = get_orchestration_service(config)
    port = args.get("port")
    force = args.get("force", False)

    result = service.start(port=port, force=force)

    if result.success:
        return f"""# Server Started ✓

**Port:** {result.port}
**PID:** {result.pid}
**URL:** http://localhost:{result.port}

Log file: `logs/server.log`
"""
    else:
        return f"""# Server Start Failed ✗

**Error:** {result.message}
"""


async def handle_server_stop(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Stop the MyBB development server."""
    service = get_orchestration_service(config)
    force = args.get("force", False)

    result = service.stop(force=force)

    if result.success:
        uptime_msg = ""
        if result.uptime_seconds:
            mins = int(result.uptime_seconds // 60)
            secs = int(result.uptime_seconds % 60)
            uptime_msg = f"\n**Uptime was:** {mins}m {secs}s"
        return f"""# Server Stopped ✓

{result.message}{uptime_msg}
"""
    else:
        return f"""# Server Stop Failed ✗

**Error:** {result.message}
"""


async def handle_server_status(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get server status."""
    service = get_orchestration_service(config)
    status = service.get_status()

    if status.running:
        mins = int(status.uptime_seconds // 60) if status.uptime_seconds else 0
        secs = int(status.uptime_seconds % 60) if status.uptime_seconds else 0
        return f"""# Server Status

**Status:** 🟢 Running
**Port:** {status.port}
**PID:** {status.pid}
**Uptime:** {mins}m {secs}s
**Started:** {status.started_at}
**Log file:** {status.log_file}
**MariaDB:** {"🟢 Running" if status.mariadb_running else "🔴 Not running"}
"""
    else:
        return f"""# Server Status

**Status:** 🔴 Not running
**MariaDB:** {"🟢 Running" if status.mariadb_running else "🔴 Not running"}

Use `mybb_server_start` to start the server.
"""


async def handle_server_logs(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Query server logs."""
    from ..orchestration import LogQueryOptions

    service = get_orchestration_service(config)
    options = LogQueryOptions(
        errors_only=args.get("errors_only", False),
        exclude_static=args.get("exclude_static", False),
        since_minutes=args.get("since_minutes"),
        filter_keyword=args.get("filter_keyword"),
        limit=args.get("limit", 50),
        tail=args.get("tail", True),
        offset=args.get("offset", 0)
    )

    return service.query_logs(options)


async def handle_server_restart(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Restart the server."""
    service = get_orchestration_service(config)
    port = args.get("port")

    result = service.restart(port=port)

    if result.success:
        return f"""# Server Restarted ✓

**Port:** {result.port}
**PID:** {result.pid}
**URL:** http://localhost:{result.port}

{result.message}
"""
    else:
        return f"""# Server Restart Failed ✗

**Error:** {result.message}
"""


# Handler registry
ORCHESTRATION_HANDLERS = {
    "mybb_server_start": handle_server_start,
    "mybb_server_stop": handle_server_stop,
    "mybb_server_status": handle_server_status,
    "mybb_server_logs": handle_server_logs,
    "mybb_server_restart": handle_server_restart,
}
