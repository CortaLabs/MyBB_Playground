"""Server orchestration service for PHP development server lifecycle management.

Follows DiskSyncService pattern for consistency.
Uses subprocess for server management.
Persists state to .mybb-server.json.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import subprocess
import json
import os
import signal
import time
from datetime import datetime, timezone, timedelta
from collections import deque
from .log_parser import parse_log_line, is_static_request, is_error_entry


@dataclass
class ServerResult:
    """Result of a server operation."""
    success: bool
    message: str
    port: Optional[int] = None
    pid: Optional[int] = None
    uptime_seconds: Optional[float] = None


@dataclass
class ServerStatus:
    """Current server status."""
    running: bool
    port: Optional[int] = None
    pid: Optional[int] = None
    started_at: Optional[str] = None
    uptime_seconds: Optional[float] = None
    log_file: Optional[str] = None
    mariadb_running: bool = False


@dataclass
class LogQueryOptions:
    """Options for querying server logs."""
    errors_only: bool = False
    exclude_static: bool = False
    since_minutes: Optional[int] = None
    filter_keyword: Optional[str] = None
    limit: int = 50
    offset: int = 0  # Pagination offset
    tail: bool = True


class ServerOrchestrationService:
    """Manages PHP development server lifecycle.

    Follows DiskSyncService pattern for consistency.
    Uses subprocess for server management.
    Persists state to .mybb-server.json.
    """

    def __init__(self, config):
        """Initialize server orchestration service.

        Args:
            config: Configuration object with mybb_root attribute
        """
        self.config = config
        self.repo_root = Path(config.mybb_root).parent
        self.mybb_root = Path(config.mybb_root)
        self.state_file = self.repo_root / ".mybb-server.json"
        self.log_dir = self.repo_root / "logs"
        self.log_file = self.log_dir / "server.log"

    def _read_state(self) -> Optional[dict]:
        """Read server state from JSON file.

        Returns:
            State dict if file exists and is valid JSON, None otherwise
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _write_state(self, state: dict) -> None:
        """Write server state to JSON file atomically.

        Args:
            state: State dictionary to persist
        """
        # Add version if not present
        if 'version' not in state:
            state['version'] = 1

        # Ensure parent directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        temp_file = self.state_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(state, f, indent=2)

        # Atomic rename
        temp_file.rename(self.state_file)

    def _validate_state(self, state: dict) -> bool:
        """Validate that the process in state is actually running.

        Args:
            state: State dictionary with 'pid' field

        Returns:
            True if PID exists and process is running, False otherwise
        """
        pid = state.get('pid')
        if not pid:
            return False

        try:
            # os.kill with signal 0 checks if process exists without sending a signal
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, OSError):
            # Process doesn't exist
            return False

    def _clear_state(self) -> None:
        """Remove state file if it exists."""
        if self.state_file.exists():
            self.state_file.unlink()

    def _check_mariadb(self) -> bool:
        """Check if MariaDB/MySQL is running.

        Returns:
            True if MariaDB or MySQL process is running, False otherwise
        """
        # Try mariadbd first (newer MariaDB)
        result = subprocess.run(['pgrep', '-x', 'mariadbd'], capture_output=True)
        if result.returncode == 0:
            return True

        # Fallback to mysqld (older or MySQL)
        result = subprocess.run(['pgrep', '-x', 'mysqld'], capture_output=True)
        return result.returncode == 0

    def get_status(self) -> ServerStatus:
        """Get current server status.

        Returns:
            ServerStatus with current state
        """
        # Check MariaDB status
        mariadb_running = self._check_mariadb()

        # Read state file
        state = self._read_state()

        # No state file - check if port is in use anyway (server started externally)
        if not state:
            default_port = int(os.environ.get('MYBB_PORT', 8022))
            port_available, pid = self._check_port_available(default_port)
            if not port_available:
                # Server running but not managed by us
                return ServerStatus(
                    running=True,
                    port=default_port,
                    pid=pid,
                    started_at=None,  # Unknown - started externally
                    uptime_seconds=None,
                    log_file=None,
                    mariadb_running=mariadb_running
                )
            return ServerStatus(running=False, mariadb_running=mariadb_running)

        # Validate PID is still running
        if not self._validate_state(state):
            # Stale state file - clean it up
            self._clear_state()
            return ServerStatus(running=False, mariadb_running=mariadb_running)

        # Calculate uptime
        started_at = datetime.fromisoformat(state['started_at'])
        uptime_seconds = (datetime.now(timezone.utc) - started_at).total_seconds()

        # Return full status
        return ServerStatus(
            running=True,
            port=state.get('port'),
            pid=state.get('pid'),
            started_at=state.get('started_at'),
            uptime_seconds=uptime_seconds,
            log_file=state.get('log_file'),
            mariadb_running=mariadb_running
        )

    def _check_port_available(self, port: int) -> tuple[bool, Optional[int]]:
        """Check if a port is available for use.

        Args:
            port: Port number to check

        Returns:
            Tuple of (is_available, pid_using_port)
        """
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True
        )

        # returncode != 0 means nothing is using the port
        if result.returncode != 0:
            return (True, None)

        # Parse PID from output
        try:
            pid = int(result.stdout.strip())
            return (False, pid)
        except (ValueError, AttributeError):
            # Couldn't parse PID, but port is in use
            return (False, None)

    def _rotate_log(self) -> None:
        """Rotate the server log file.

        Moves current log to .log.1, deleting any existing .log.1
        """
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # If current log exists, rotate it
        if self.log_file.exists():
            rotated = self.log_file.with_suffix('.log.1')

            # Delete old rotated log if it exists
            if rotated.exists():
                rotated.unlink()

            # Rename current log to rotated
            self.log_file.rename(rotated)

    def start(self, port: Optional[int] = None, force: bool = False) -> ServerResult:
        """Start the PHP development server.

        Args:
            port: Port to run on (default: MYBB_PORT env or 8022)
            force: If True, stop existing server first

        Returns:
            ServerResult with operation status
        """
        # Default port
        port = port or int(os.environ.get('MYBB_PORT', 8022))

        # Check current status
        status = self.get_status()

        # If already running and not force, return error
        if status.running and not force:
            return ServerResult(
                success=False,
                message="Server already running",
                port=status.port,
                pid=status.pid
            )

        # If already running and force, stop it first
        if status.running and force:
            stop_result = self.stop()
            if not stop_result.success:
                return ServerResult(
                    success=False,
                    message=f"Failed to stop existing server: {stop_result.message}"
                )

        # Check if port is available
        port_available, pid_using_port = self._check_port_available(port)
        if not port_available:
            return ServerResult(
                success=False,
                message=f"Port {port} already in use by PID {pid_using_port}"
            )

        # Check MariaDB is running
        if not self._check_mariadb():
            return ServerResult(
                success=False,
                message="MariaDB is not running. Start MariaDB first."
            )

        # Rotate log file
        self._rotate_log()

        # Start PHP server
        log_path = str(self.log_file)
        cmd = f'cd "{self.mybb_root}" && php -S localhost:{port} -t . >> "{log_path}" 2>&1 & echo $!'

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.mybb_root)
            )

            # Parse PID from output
            pid = int(result.stdout.strip())

            # Wait a moment for server to start
            time.sleep(0.5)

            # Verify process exists
            try:
                os.kill(pid, 0)
            except (ProcessLookupError, OSError):
                return ServerResult(
                    success=False,
                    message=f"Server process {pid} failed to start"
                )

            # Write state
            self._write_state({
                'port': port,
                'pid': pid,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'log_file': log_path
            })

            return ServerResult(
                success=True,
                message=f"Server started on port {port}",
                port=port,
                pid=pid
            )

        except (subprocess.SubprocessError, ValueError) as e:
            return ServerResult(
                success=False,
                message=f"Failed to start server: {str(e)}"
            )

    def stop(self, force: bool = False) -> ServerResult:
        """Stop the PHP development server.

        Args:
            force: If True, use SIGKILL if graceful shutdown fails

        Returns:
            ServerResult with operation status
        """
        # Get current status
        status = self.get_status()

        # If not running, return error
        if not status.running:
            return ServerResult(
                success=False,
                message="Server is not running"
            )

        # Get PID from status
        pid = status.pid

        try:
            # Try graceful shutdown first
            os.kill(pid, signal.SIGTERM)

            # Wait up to 5 seconds for process to exit
            for _ in range(50):  # 50 * 0.1s = 5s
                try:
                    os.kill(pid, 0)  # Check if process still exists
                    time.sleep(0.1)
                except (ProcessLookupError, OSError):
                    # Process is gone
                    break
            else:
                # Process still running after 5 seconds
                if force:
                    # Force kill
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.1)
                else:
                    return ServerResult(
                        success=False,
                        message="Server did not stop gracefully. Use force=True to kill."
                    )

            # Clear state file
            self._clear_state()

            return ServerResult(
                success=True,
                message="Server stopped",
                uptime_seconds=status.uptime_seconds
            )

        except (ProcessLookupError, OSError) as e:
            # Process doesn't exist - clean up state anyway
            self._clear_state()
            return ServerResult(
                success=True,
                message=f"Server process not found, cleaned up state: {str(e)}"
            )

    def query_logs(self, options: LogQueryOptions) -> str:
        """Query server logs with filtering options.

        Args:
            options: LogQueryOptions with filter settings

        Returns:
            Markdown-formatted log output
        """
        log_file = self.log_dir / "server.log"

        # Check if log file exists
        if not log_file.exists():
            return "# Server Logs\n\nNo log file found. Server may not have been started yet."

        # Get file size for info
        file_size = log_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # Max bytes to read (10MB) - prevents memory issues on huge logs
        MAX_READ_BYTES = 10 * 1024 * 1024

        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                if options.tail and file_size > MAX_READ_BYTES:
                    # For large files with tail mode, seek to end and read last chunk
                    f.seek(max(0, file_size - MAX_READ_BYTES))
                    f.readline()  # Discard partial line
                    lines = f.readlines()
                    truncated = True
                else:
                    lines = f.readlines()
                    truncated = False
        except Exception as e:
            return f"# Server Logs\n\n**Error reading log file:** {str(e)}"

        total_lines = len(lines)

        # Parse and filter entries, collecting matches
        entries = []
        for line in lines:
            entry = parse_log_line(line)
            if entry is None:
                continue

            # Apply filters
            if options.errors_only and not entry.is_error:
                continue
            if options.exclude_static and entry.is_static:
                continue
            if options.filter_keyword:
                if options.filter_keyword.lower() not in entry.raw_line.lower():
                    continue
            if options.since_minutes is not None and entry.timestamp:
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=options.since_minutes)
                if entry.timestamp < cutoff_time:
                    continue

            entries.append(entry)

        # Track total matching before pagination
        total_matching = len(entries)

        # Apply pagination: offset first, then limit
        if options.tail:
            # For tail, offset from the end
            if options.offset > 0:
                entries = entries[:-options.offset] if options.offset < len(entries) else []
            entries = entries[-options.limit:] if entries else []
        else:
            # For head, offset from the start
            entries = entries[options.offset:options.offset + options.limit]

        # Build error category breakdown
        error_categories = {}
        for e in entries:
            if e.is_error and e.error_category:
                error_categories[e.error_category] = error_categories.get(e.error_category, 0) + 1

        # Format as markdown
        filter_desc = []
        if options.errors_only:
            filter_desc.append("errors_only=true")
        if options.exclude_static:
            filter_desc.append("exclude_static=true")
        if options.filter_keyword:
            filter_desc.append(f"keyword='{options.filter_keyword}'")
        if options.since_minutes:
            filter_desc.append(f"since={options.since_minutes}m")
        if options.offset > 0:
            filter_desc.append(f"offset={options.offset}")

        filters_str = ", ".join(filter_desc) if filter_desc else "none"
        truncated_warning = "\n**⚠️ Large log file - showing last 10MB only**" if truncated else ""

        # Pagination info
        has_more = total_matching > (options.offset + options.limit)
        page_info = f" (page {options.offset // options.limit + 1})" if options.offset > 0 else ""
        next_page_hint = f"\n*More entries available. Use offset={options.offset + options.limit} to see next page.*" if has_more else ""

        output = f"""# Server Logs{page_info}

**Showing:** {len(entries)} of {total_matching} matching (from {total_lines} lines read)
**Log file:** {log_file} ({file_size_mb:.2f} MB)
**Filters:** {filters_str}{truncated_warning}

```
"""

        # Token guard: max ~8000 chars of log content to avoid context bloat
        MAX_OUTPUT_CHARS = 8000
        chars_used = 0
        entries_shown = 0

        for entry in entries:
            # Format timestamp
            ts_str = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else "??:??:??"

            # Format line based on entry type
            if entry.entry_type == 'request':
                cat_tag = f"[{entry.error_category}] " if entry.error_category else ""
                status_marker = "**" if entry.is_error else ""
                line = f"{status_marker}[{ts_str}] {cat_tag}[{entry.status_code}] {entry.method} {entry.path}{status_marker}\n"
            elif entry.entry_type == 'error':
                cat_tag = f"[{entry.error_category}] " if entry.error_category else ""
                line = f"**[{ts_str}] {cat_tag}{entry.raw_line[:200]}{'...' if len(entry.raw_line) > 200 else ''}**\n"
            elif entry.entry_type == 'connection':
                continue
            else:
                line = f"[{ts_str}] {entry.raw_line[:150]}{'...' if len(entry.raw_line) > 150 else ''}\n"

            # Check token guard
            if chars_used + len(line) > MAX_OUTPUT_CHARS:
                output += f"... ({len(entries) - entries_shown} more entries truncated for context limit)\n"
                break

            output += line
            chars_used += len(line)
            entries_shown += 1

        output += "```\n"

        # Add summary with error breakdown
        error_count = sum(1 for e in entries if e.is_error)
        if error_count > 0:
            breakdown = ", ".join(f"{cat}: {count}" for cat, count in sorted(error_categories.items()))
            output += f"\n**Summary:** {entries_shown} entries shown, {error_count} errors"
            if breakdown:
                output += f"\n**Error breakdown:** {breakdown}"
            output += "\n"

        output += next_page_hint

        return output

    def restart(self, port: Optional[int] = None) -> ServerResult:
        """Restart the server (stop + start).

        Args:
            port: Port for restarted server (default: same as before)

        Returns:
            ServerResult with operation status
        """
        # Stop the server
        stop_result = self.stop()

        # Wait a moment for cleanup
        time.sleep(1)

        # Start the server (use same port if not specified)
        if port is None:
            # Try to get port from previous state
            state = self._read_state()
            if state:
                port = state.get('port')

        start_result = self.start(port=port)

        # Combine results
        if start_result.success:
            return ServerResult(
                success=True,
                message=f"Server restarted successfully\n\nStop: {stop_result.message}\nStart: {start_result.message}",
                port=start_result.port,
                pid=start_result.pid
            )
        else:
            return ServerResult(
                success=False,
                message=f"Restart failed\n\nStop: {stop_result.message}\nStart: {start_result.message}"
            )
