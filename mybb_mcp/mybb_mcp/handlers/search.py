"""Search handlers for MyBB MCP tools."""

from datetime import datetime
from typing import Any


# ==================== Search Handlers ====================

async def handle_search_posts(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Search post content with optional filters.

    Args:
        args: Tool arguments containing:
            - query: Search term (required)
            - forums: Optional list of forum IDs
            - author: Optional username filter
            - date_from: Optional start timestamp
            - date_to: Optional end timestamp
            - limit: Max results (default 25)
            - offset: Pagination offset (default 0)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Search results as markdown table
    """
    query = args.get("query")
    if not query:
        return "Error: 'query' parameter is required."

    results = db.search_posts(
        query=query,
        forums=args.get("forums"),
        author=args.get("author"),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        limit=args.get("limit", 25),
        offset=args.get("offset", 0)
    )

    if not results:
        return f"# Post Search Results\n\nNo posts found matching '{query}'."

    lines = [f"# Post Search Results ({len(results)} found)\n"]
    lines.append("| PID | Thread | Author | Date | Preview |")
    lines.append("|-----|--------|--------|------|---------|")

    for post in results:
        date_str = datetime.fromtimestamp(post['dateline']).strftime('%Y-%m-%d')
        # Truncate message for preview
        preview = post['message'][:100].replace('\n', ' ').replace('|', '\\|')
        if len(post['message']) > 100:
            preview += "..."
        lines.append(
            f"| {post['pid']} | {post['thread_subject']} | {post['username']} | {date_str} | {preview} |"
        )

    return "\n".join(lines)


async def handle_search_threads(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Search thread subjects with optional filters.

    Args:
        args: Tool arguments containing:
            - query: Search term (required)
            - forums: Optional list of forum IDs
            - author: Optional username filter
            - prefix: Optional thread prefix ID
            - limit: Max results (default 25)
            - offset: Pagination offset (default 0)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Search results as markdown table
    """
    query = args.get("query")
    if not query:
        return "Error: 'query' parameter is required."

    results = db.search_threads(
        query=query,
        forums=args.get("forums"),
        author=args.get("author"),
        prefix=args.get("prefix"),
        limit=args.get("limit", 25),
        offset=args.get("offset", 0)
    )

    if not results:
        return f"# Thread Search Results\n\nNo threads found matching '{query}'."

    lines = [f"# Thread Search Results ({len(results)} found)\n"]
    lines.append("| TID | Subject | Author | Replies | Views | Last Post |")
    lines.append("|-----|---------|--------|---------|-------|-----------|")

    for thread in results:
        last_post = datetime.fromtimestamp(thread['lastpost']).strftime('%Y-%m-%d %H:%M')
        lines.append(
            f"| {thread['tid']} | {thread['subject']} | {thread['username']} | "
            f"{thread['replies']} | {thread['views']} | {last_post} |"
        )

    return "\n".join(lines)


async def handle_search_users(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Search users by username or email.

    Args:
        args: Tool arguments containing:
            - query: Search term (required)
            - field: Field to search ('username' or 'email', default 'username')
            - limit: Max results (default 25)
            - offset: Pagination offset (default 0)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Search results as markdown table
    """
    query = args.get("query")
    if not query:
        return "Error: 'query' parameter is required."

    field = args.get("field", "username")

    try:
        results = db.search_users(
            query=query,
            field=field,
            limit=args.get("limit", 25),
            offset=args.get("offset", 0)
        )
    except ValueError as e:
        return f"Error: {e}"

    if not results:
        return f"# User Search Results\n\nNo users found matching '{query}' in {field}."

    lines = [f"# User Search Results ({len(results)} found)\n"]
    lines.append("| UID | Username | Group | Posts | Threads | Registered |")
    lines.append("|-----|----------|-------|-------|---------|------------|")

    for user in results:
        reg_date = datetime.fromtimestamp(user['regdate']).strftime('%Y-%m-%d')
        lines.append(
            f"| {user['uid']} | {user['username']} | {user['usergroup']} | "
            f"{user['postnum']} | {user['threadnum']} | {reg_date} |"
        )

    return "\n".join(lines)


async def handle_search_advanced(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Combined search across posts and/or threads with multiple filters.

    Args:
        args: Tool arguments containing:
            - query: Search term (required)
            - content_type: 'posts', 'threads', or 'both' (default 'both')
            - forums: Optional list of forum IDs
            - date_from: Optional start timestamp
            - date_to: Optional end timestamp
            - sort_by: 'date' or 'relevance' (default 'date')
            - limit: Max results per type (default 25)
            - offset: Pagination offset (default 0)
        db: MyBBDatabase instance
        config: Server configuration (unused)
        sync_service: Disk sync service (unused)

    Returns:
        Combined search results as markdown
    """
    query = args.get("query")
    if not query:
        return "Error: 'query' parameter is required."

    results = db.search_advanced(
        query=query,
        content_type=args.get("content_type", "both"),
        forums=args.get("forums"),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        sort_by=args.get("sort_by", "date"),
        limit=args.get("limit", 25),
        offset=args.get("offset", 0)
    )

    lines = [f"# Advanced Search Results for '{query}'\n"]

    if "posts" in results:
        posts = results["posts"]
        lines.append(f"\n## Posts ({len(posts)} found)\n")
        if posts:
            lines.append("| PID | Thread | Author | Date | Preview |")
            lines.append("|-----|--------|--------|------|---------|")
            for post in posts:
                date_str = datetime.fromtimestamp(post['dateline']).strftime('%Y-%m-%d')
                preview = post['message'][:80].replace('\n', ' ').replace('|', '\\|')
                if len(post['message']) > 80:
                    preview += "..."
                lines.append(
                    f"| {post['pid']} | {post['thread_subject']} | {post['username']} | {date_str} | {preview} |"
                )

    if "threads" in results:
        threads = results["threads"]
        lines.append(f"\n## Threads ({len(threads)} found)\n")
        if threads:
            lines.append("| TID | Subject | Author | Replies | Views |")
            lines.append("|-----|---------|--------|---------|-------|")
            for thread in threads:
                lines.append(
                    f"| {thread['tid']} | {thread['subject']} | {thread['username']} | "
                    f"{thread['replies']} | {thread['views']} |"
                )

    if not results.get("posts") and not results.get("threads"):
        lines.append("\nNo results found.")

    return "\n".join(lines)


# Handler registry for search tools
SEARCH_HANDLERS = {
    "mybb_search_posts": handle_search_posts,
    "mybb_search_threads": handle_search_threads,
    "mybb_search_users": handle_search_users,
    "mybb_search_advanced": handle_search_advanced,
}
