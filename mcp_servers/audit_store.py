"""Append-only JSONL audit store shared by V3 MCP servers."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


ROOT_DIR = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT_DIR / "audit_logs"
AUDIT_FILE = AUDIT_DIR / "governance.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_audit_record(record: dict[str, Any]) -> dict[str, Any]:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "audit_id": str(uuid4()),
        "timestamp": utc_now(),
        **record,
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
    return entry


def read_audit_records(limit: int = 100) -> list[dict[str, Any]]:
    if not AUDIT_FILE.exists():
        return []

    records: list[dict[str, Any]] = []
    with AUDIT_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records[-limit:]


def log_tool_call(
    *,
    server: str,
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
    event_id: str | None = None,
) -> dict[str, Any]:
    return append_audit_record(
        {
            "record_type": "mcp_tool_call",
            "server": server,
            "tool_name": tool_name,
            "event_id": event_id,
            "arguments": arguments,
            "result": result,
        }
    )
