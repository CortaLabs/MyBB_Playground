"""Database query handler for MyBB MCP tools."""

from typing import Any


async def handle_db_query(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Execute a read-only SQL query against the MyBB database.

    Args:
        args: Tool arguments containing 'query' parameter
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Query results formatted as markdown table, or error message
    """
    query = args.get("query", "").strip()
    if not query.upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed."

    with db.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        return "No results."

    # Format as table
    keys = list(rows[0].keys())
    lines = [" | ".join(keys), " | ".join(["---"] * len(keys))]
    for row in rows[:50]:
        lines.append(" | ".join(str(row[k])[:50] for k in keys))
    if len(rows) > 50:
        lines.append(f"\n*...{len(rows) - 50} more rows*")

    return "\n".join(lines)


# Handler registry for database tools
DATABASE_HANDLERS = {
    "mybb_db_query": handle_db_query,
}
