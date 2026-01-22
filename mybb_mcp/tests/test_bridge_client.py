"""Unit tests for the MyBB PHP bridge client."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mybb_mcp.bridge.client import MyBBBridgeClient


class DummyProc:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_build_cmd_includes_action_json_and_request_id(tmp_path: Path):
    (tmp_path / "mcp_bridge.php").write_text("<?php", encoding="utf-8")
    client = MyBBBridgeClient(tmp_path, php_binary="php", timeout=1)
    cmd = client._build_cmd("info", "rid-123", plugin="hello_world", force=True, uninstall=False, nothing=None)
    assert cmd[:3] == ["php", str(tmp_path / "mcp_bridge.php"), "--action=info"]
    assert "--json" in cmd
    assert "--request_id=rid-123" in cmd
    assert "--plugin=hello_world" in cmd
    assert "--force" in cmd
    assert "--uninstall" not in cmd


def test_call_parses_success_payload(tmp_path: Path):
    (tmp_path / "mcp_bridge.php").write_text("<?php", encoding="utf-8")
    client = MyBBBridgeClient(tmp_path, timeout=1)
    payload = {
        "success": True,
        "timestamp": "2026-01-21T00:00:00Z",
        "data": {"ok": 1},
        "action": "info",
        "bridge_version": "1.1.0",
        "protocol_version": "1",
        "request_id": "rid-xyz",
    }
    with patch("subprocess.run", return_value=DummyProc(stdout=json.dumps(payload))):
        result = client.call("info", request_id="rid-xyz")
    assert result.success is True
    assert result.action == "info"
    assert result.data["ok"] == 1
    assert result.request_id == "rid-xyz"
    assert result.bridge_version == "1.1.0"
    assert result.protocol_version == "1"


def test_call_invalid_json_returns_error(tmp_path: Path):
    (tmp_path / "mcp_bridge.php").write_text("<?php", encoding="utf-8")
    client = MyBBBridgeClient(tmp_path, timeout=1)
    with patch("subprocess.run", return_value=DummyProc(stdout="{not json}", stderr="")):
        result = client.call("info", request_id="rid-1")
    assert result.success is False
    assert result.error and "Invalid JSON response" in result.error


def test_call_missing_bridge_file(tmp_path: Path):
    client = MyBBBridgeClient(tmp_path, timeout=1)
    result = client.call("info", request_id="rid-2")
    assert result.success is False
    assert "MCP Bridge not found" in (result.error or "")

