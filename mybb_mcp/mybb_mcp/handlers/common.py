"""Common formatting utilities for handler modules."""

from typing import List


def format_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    """Format data as a markdown table.

    Args:
        headers: List of column headers
        rows: List of row data (each row is a list of column values)

    Returns:
        Formatted markdown table string
    """
    if not headers or not rows:
        return ""

    lines = []

    # Header row
    lines.append("| " + " | ".join(headers) + " |")

    # Separator row
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")

    # Data rows
    for row in rows:
        # Ensure row has same number of columns as headers
        padded_row = list(row) + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(str(cell) for cell in padded_row[:len(headers)]) + " |")

    return "\n".join(lines)


def format_code_block(content: str, lang: str = "") -> str:
    """Format content as a markdown code block.

    Args:
        content: Code content to format
        lang: Optional language identifier (e.g., "python", "sql")

    Returns:
        Formatted code block string
    """
    return f"```{lang}\n{content}\n```"


def format_error(message: str) -> str:
    """Format an error message.

    Args:
        message: Error message text

    Returns:
        Formatted error string
    """
    if not message.startswith("Error:"):
        return f"Error: {message}"
    return message


def format_success(message: str) -> str:
    """Format a success message.

    Args:
        message: Success message text

    Returns:
        Formatted success string with markdown emphasis
    """
    return f"**{message}**"
