"""Governance MCP server exposing audit and policy tools on port 8004."""
from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from mcp_servers.audit_store import append_audit_record, read_audit_records


SERVER_NAME = "governance_mcp"
PORT = 8004
DESTRUCTIVE_KEYWORDS = {"quarantine", "shutdown", "disconnect", "isolate", "disable", "revoke", "rotate"}

app = FastAPI(title="Governance MCP", version="3.0.0")


class AuditLogRequest(BaseModel):
    record_type: str
    event_id: str | None = None
    agent_name: str | None = None
    tool_name: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class PolicyCheckRequest(BaseModel):
    action: str
    event_id: str | None = None


def write_audit_log(
    *,
    record_type: str,
    payload: dict[str, Any],
    event_id: str | None = None,
    agent_name: str | None = None,
    tool_name: str | None = None,
) -> dict[str, Any]:
    return append_audit_record(
        {
            "record_type": record_type,
            "server": SERVER_NAME,
            "event_id": event_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "payload": payload,
        }
    )


def policy_check(action: str, event_id: str | None = None) -> dict[str, Any]:
    normalized = action.lower()
    requires_approval = any(keyword in normalized for keyword in DESTRUCTIVE_KEYWORDS)
    result = {
        "action": action,
        "decision": "requires_human_approval" if requires_approval else "approved",
        "requires_human_approval": requires_approval,
        "policy": "destructive_actions_require_hitl",
    }
    write_audit_log(
        record_type="mcp_tool_call",
        event_id=event_id,
        tool_name="policy_check",
        payload={"arguments": {"action": action}, "result": result},
    )
    return result


@app.get("/health")
async def health():
    return {"status": "ready", "server": SERVER_NAME, "port": PORT}


@app.get("/tools")
async def tools():
    return {"tools": ["write_audit_log", "policy_check", "read_audit_logs"]}


@app.post("/tools/write_audit_log")
async def write_audit_log_endpoint(request: AuditLogRequest):
    return write_audit_log(
        record_type=request.record_type,
        event_id=request.event_id,
        agent_name=request.agent_name,
        tool_name=request.tool_name,
        payload=request.payload,
    )


@app.post("/tools/policy_check")
async def policy_check_endpoint(request: PolicyCheckRequest):
    return policy_check(request.action, request.event_id)


@app.get("/tools/read_audit_logs")
async def read_audit_logs(limit: int = 100):
    return {"records": read_audit_records(limit)}


if __name__ == "__main__":
    uvicorn.run("mcp_servers.governance_mcp.server:app", host="0.0.0.0", port=PORT)
