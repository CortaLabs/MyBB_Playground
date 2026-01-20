"""Log parsing utilities for PHP development server output."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class LogEntry:
    """Parsed log entry from PHP development server."""
    timestamp: Optional[datetime]
    raw_line: str
    entry_type: str  # 'request', 'error', 'connection', 'other'
    status_code: Optional[int] = None
    method: Optional[str] = None
    path: Optional[str] = None
    ip: Optional[str] = None
    is_error: bool = False
    is_static: bool = False
    error_category: Optional[str] = None  # fatal, parse, warning, notice, http_5xx, etc.


# Static asset patterns to filter out
STATIC_PATTERNS = [
    r'/images/',
    r'/jscripts/',
    r'/cache/themes/',
    r'\.(png|jpg|jpeg|gif|css|js|ico|woff|woff2|ttf|svg)(\?|$)',
]

# Error patterns to detect with categories
ERROR_PATTERNS = {
    'fatal': [r'PHP Fatal error:', r'Fatal error:'],
    'parse': [r'PHP Parse error:', r'Parse error:', r'syntax error'],
    'warning': [r'PHP Warning:', r'Warning:'],
    'notice': [r'PHP Notice:', r'Notice:'],
    'deprecated': [r'PHP Deprecated:', r'Deprecated:'],
    'strict': [r'PHP Strict Standards:', r'Strict Standards:'],
    'recoverable': [r'PHP Recoverable fatal error:'],
    'exception': [r'Uncaught Exception:', r'Uncaught Error:', r'Exception:'],
    'http_5xx': [r'\[50[0-9]\]:'],  # 500-509 status codes
    'http_4xx': [r'\[4[0-9]{2}\]:'],  # 400-499 status codes
    'stack_trace': [r'^#\d+\s'],  # Stack trace lines
}

# Flattened patterns for quick matching
ALL_ERROR_PATTERNS = [p for patterns in ERROR_PATTERNS.values() for p in patterns]


def parse_log_line(line: str) -> Optional[LogEntry]:
    """Parse a single log line from PHP development server.

    Handles formats:
    - Request: [Mon Jan 19 22:21:26 2026] 127.0.0.1:47778 [200]: GET /usercp.php
    - Error: [Mon Jan 19 22:21:26 2026] PHP Fatal error: ...
    - Connection: [Mon Jan 19 22:21:26 2026] 127.0.0.1:47778 Accepted
    - Stack trace: #0 /path/to/file.php(123): function()

    Args:
        line: Raw log line

    Returns:
        LogEntry if parseable, None otherwise
    """
    line = line.strip()
    if not line:
        return None

    # Parse timestamp from [...]
    timestamp_match = re.match(r'\[([^\]]+)\]', line)
    timestamp = None
    if timestamp_match:
        timestamp_str = timestamp_match.group(1)
        try:
            # PHP dev server format: "Mon Jan 19 22:21:26 2026"
            timestamp = datetime.strptime(timestamp_str, "%a %b %d %H:%M:%S %Y")
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # Initialize entry with defaults
    entry = LogEntry(
        timestamp=timestamp,
        raw_line=line,
        entry_type='other'
    )

    # Check for stack trace lines (start with #0, #1, etc.)
    if re.match(r'^#\d+', line):
        entry.entry_type = 'error'
        entry.is_error = True
        return entry

    # Extract IP:port pattern
    ip_port_match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)', line)
    if ip_port_match:
        entry.ip = ip_port_match.group(1)

    # Check for connection events
    if 'Accepted' in line or 'Closing' in line:
        entry.entry_type = 'connection'
        return entry

    # Check for HTTP request format: [200]: GET /path
    request_match = re.search(r'\[(\d{3})\]:\s+([A-Z]+)\s+(.+)$', line)
    if request_match:
        entry.status_code = int(request_match.group(1))
        entry.method = request_match.group(2)
        entry.path = request_match.group(3)
        entry.entry_type = 'request'

        # Check if it's an error status and categorize
        if entry.status_code >= 400:
            entry.is_error = True
            entry.error_category = get_error_category(entry)

        # Check if it's a static asset
        if is_static_request(entry):
            entry.is_static = True

        return entry

    # Check for PHP error patterns
    error_cat = get_error_category(entry)
    if error_cat:
        entry.entry_type = 'error'
        entry.is_error = True
        entry.error_category = error_cat
        return entry

    return entry


def is_static_request(entry: LogEntry) -> bool:
    """Check if log entry is for a static asset request.

    Args:
        entry: Parsed log entry

    Returns:
        True if entry path matches static asset patterns
    """
    if not entry.path:
        return False

    for pattern in STATIC_PATTERNS:
        if re.search(pattern, entry.path):
            return True

    return False


def get_error_category(entry: LogEntry) -> Optional[str]:
    """Determine the error category for a log entry.

    Args:
        entry: Parsed log entry

    Returns:
        Error category string or None if not an error
    """
    # Check status code first
    if entry.status_code:
        if 500 <= entry.status_code < 600:
            return 'http_5xx'
        elif 400 <= entry.status_code < 500:
            return 'http_4xx'

    # Check raw line for error patterns
    for category, patterns in ERROR_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, entry.raw_line):
                return category

    return None


def is_error_entry(entry: LogEntry) -> bool:
    """Check if log entry is an error.

    Args:
        entry: Parsed log entry

    Returns:
        True if entry contains error indicators
    """
    return get_error_category(entry) is not None
