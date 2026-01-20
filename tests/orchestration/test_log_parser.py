"""Unit tests for log_parser module."""

import pytest
from mybb_mcp.orchestration.log_parser import (
    LogEntry, parse_log_line, is_static_request, is_error_entry,
    STATIC_PATTERNS, ERROR_PATTERNS
)


class TestParseLogLine:
    """Test parse_log_line function."""

    def test_parse_request_line(self):
        """Test parsing HTTP request format."""
        line = "[Mon Jan 20 01:32:55 2026] 127.0.0.1:47778 [200]: GET /usercp.php"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.status_code == 200
        assert entry.method == "GET"
        assert entry.path == "/usercp.php"
        assert entry.entry_type == "request"

    def test_parse_error_request(self):
        """Test parsing 500 error request."""
        line = "[Mon Jan 20 01:32:55 2026] 127.0.0.1:47778 [500]: GET /broken.php"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.status_code == 500
        assert entry.is_error == True

    def test_parse_php_error(self):
        """Test parsing PHP error line."""
        line = "[Mon Jan 20 01:32:55 2026] PHP Fatal error: Something broke"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.entry_type == "error"
        assert entry.is_error == True

    def test_parse_php_parse_error(self):
        """Test parsing PHP Parse error."""
        line = "[Mon Jan 20 01:32:55 2026] PHP Parse error: syntax error"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.is_error == True

    def test_parse_connection_event(self):
        """Test parsing connection events."""
        line = "[Mon Jan 20 01:32:55 2026] 127.0.0.1:47778 Accepted"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.entry_type == "connection"

    def test_parse_empty_line(self):
        """Empty lines return None."""
        assert parse_log_line("") is None
        assert parse_log_line("   ") is None

    def test_parse_404_error(self):
        """Test parsing 404 error."""
        line = "[Mon Jan 20 01:32:55 2026] 127.0.0.1:47778 [404]: GET /notfound.php"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.status_code == 404
        assert entry.is_error == True

    def test_parse_php_warning(self):
        """Test parsing PHP Warning."""
        line = "[Mon Jan 20 01:32:55 2026] PHP Warning: Division by zero"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.entry_type == "error"
        assert entry.is_error == True


class TestIsStaticRequest:
    """Test is_static_request function."""

    def test_image_is_static(self):
        """Images are static."""
        entry = LogEntry(
            timestamp=None,
            raw_line="",
            entry_type="request",
            path="/images/logo.png"
        )
        assert is_static_request(entry) == True

    def test_css_is_static(self):
        """CSS files are static."""
        entry = LogEntry(
            timestamp=None,
            raw_line="",
            entry_type="request",
            path="/cache/themes/style.css"
        )
        assert is_static_request(entry) == True

    def test_js_is_static(self):
        """JavaScript files are static."""
        entry = LogEntry(
            timestamp=None,
            raw_line="",
            entry_type="request",
            path="/jscripts/jquery.js"
        )
        assert is_static_request(entry) == True

    def test_php_not_static(self):
        """PHP files are not static."""
        entry = LogEntry(
            timestamp=None,
            raw_line="",
            entry_type="request",
            path="/usercp.php"
        )
        assert is_static_request(entry) == False

    def test_font_is_static(self):
        """Font files are static."""
        entry = LogEntry(
            timestamp=None,
            raw_line="",
            entry_type="request",
            path="/fonts/roboto.woff2"
        )
        assert is_static_request(entry) == True

    def test_icon_is_static(self):
        """Icon files are static."""
        entry = LogEntry(
            timestamp=None,
            raw_line="",
            entry_type="request",
            path="/favicon.ico"
        )
        assert is_static_request(entry) == True


class TestIsErrorEntry:
    """Test is_error_entry function."""

    def test_500_is_error(self):
        """500 status code is an error."""
        entry = LogEntry(
            timestamp=None,
            raw_line="[500]: GET /",
            entry_type="request",
            status_code=500
        )
        assert is_error_entry(entry) == True

    def test_404_is_error(self):
        """404 status code is an error."""
        entry = LogEntry(
            timestamp=None,
            raw_line="[404]: GET /",
            entry_type="request",
            status_code=404
        )
        assert is_error_entry(entry) == True

    def test_200_not_error(self):
        """200 status code is not an error."""
        entry = LogEntry(
            timestamp=None,
            raw_line="[200]: GET /",
            entry_type="request",
            status_code=200
        )
        assert is_error_entry(entry) == False

    def test_php_fatal_is_error(self):
        """PHP Fatal error is an error."""
        entry = LogEntry(
            timestamp=None,
            raw_line="PHP Fatal error: boom",
            entry_type="other"
        )
        assert is_error_entry(entry) == True

    def test_php_warning_is_error(self):
        """PHP Warning is an error."""
        entry = LogEntry(
            timestamp=None,
            raw_line="PHP Warning: something",
            entry_type="error"
        )
        assert is_error_entry(entry) == True

    def test_503_is_error(self):
        """503 status code is an error."""
        entry = LogEntry(
            timestamp=None,
            raw_line="[503]: GET /",
            entry_type="request",
            status_code=503
        )
        assert is_error_entry(entry) == True

    def test_normal_connection_not_error(self):
        """Connection event without error indicators is not an error."""
        entry = LogEntry(
            timestamp=None,
            raw_line="127.0.0.1:47778 Accepted",
            entry_type="connection"
        )
        assert is_error_entry(entry) == False
