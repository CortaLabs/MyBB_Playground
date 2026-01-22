from __future__ import annotations

import asyncio
import json
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class BridgeResult:
    success: bool
    action: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    request_id: str | None = None
    bridge_version: str | None = None
    protocol_version: str | None = None
    raw: dict[str, Any] | None = None


class MyBBBridgeClient:
    """Invoke the CLI PHP bridge and parse its JSON response.

    This is intended for MCP handlers to call MyBB-native operations without
    reimplementing MyBB behavior via direct SQL.
    """

    def __init__(self, mybb_root: Path, php_binary: str = "php", timeout: int = 30):
        self.mybb_root = Path(mybb_root).resolve()
        self.php_binary = php_binary
        self.timeout = timeout
        self.bridge_path = self.mybb_root / "mcp_bridge.php"

    def _build_cmd(self, action: str, request_id: str, **kwargs: Any) -> list[str]:
        cmd: list[str] = [
            self.php_binary,
            str(self.bridge_path),
            f"--action={action}",
            "--json",
            f"--request_id={request_id}",
        ]

        for key, value in kwargs.items():
            if value is True:
                cmd.append(f"--{key}")
            elif value is None or value is False:
                continue
            else:
                cmd.append(f"--{key}={value}")

        return cmd

    def call(self, action: str, request_id: str | None = None, **kwargs: Any) -> BridgeResult:
        if not self.bridge_path.exists():
            return BridgeResult(
                success=False,
                action=action,
                error=f"MCP Bridge not found at {self.bridge_path}",
            )

        rid = request_id or str(uuid.uuid4())
        cmd = self._build_cmd(action, rid, **kwargs)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.mybb_root),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return BridgeResult(
                success=False,
                action=action,
                request_id=rid,
                error=f"Bridge operation timed out after {self.timeout}s",
            )
        except FileNotFoundError:
            return BridgeResult(
                success=False,
                action=action,
                request_id=rid,
                error=f"PHP binary not found: {self.php_binary}",
            )
        except Exception as e:
            return BridgeResult(
                success=False,
                action=action,
                request_id=rid,
                error=str(e),
            )

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        try:
            payload = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            msg = stderr or stdout or "Invalid JSON response"
            return BridgeResult(
                success=False,
                action=action,
                request_id=rid,
                error=f"Invalid JSON response: {msg}",
            )

        success = bool(payload.get("success", False))
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        warnings = payload.get("warnings")
        error = payload.get("error")

        return BridgeResult(
            success=success,
            action=str(payload.get("action") or action),
            data=data,
            warnings=list(warnings) if isinstance(warnings, list) else [],
            error=str(error) if error is not None else None,
            request_id=str(payload.get("request_id")) if payload.get("request_id") else rid,
            bridge_version=str(payload.get("bridge_version")) if payload.get("bridge_version") else None,
            protocol_version=str(payload.get("protocol_version")) if payload.get("protocol_version") else None,
            raw=payload,
        )

    async def call_async(self, action: str, request_id: str | None = None, **kwargs: Any) -> BridgeResult:
        return await asyncio.to_thread(self.call, action, request_id, **kwargs)

