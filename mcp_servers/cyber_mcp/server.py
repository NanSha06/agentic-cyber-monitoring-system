"""Cyber MCP server exposing cyber-response tools on port 8002."""
from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.services.demo_data import ALERT_STORE, get_asset
from mcp_servers.audit_store import log_tool_call


SERVER_NAME = "cyber_mcp"
PORT = 8002

app = FastAPI(title="Cyber MCP", version="3.0.0")


class ActiveAlertsRequest(BaseModel):
    asset_id: str | None = None
    event_id: str | None = None


class QuarantineRequest(BaseModel):
    asset_id: str
    event_id: str | None = None
    approved_by: str = "human_operator"
    reason: str = "HITL-approved containment"


def get_active_alerts(asset_id: str | None = None, event_id: str | None = None) -> dict[str, Any]:
    alerts = [
        alert for alert in ALERT_STORE
        if not alert["resolved"] and (asset_id is None or alert["asset_id"] == asset_id)
    ]
    result = {"count": len(alerts), "alerts": alerts[:20]}
    log_tool_call(
        server=SERVER_NAME,
        tool_name="get_active_alerts",
        event_id=event_id,
        arguments={"asset_id": asset_id},
        result={"count": len(alerts)},
    )
    return result


def quarantine_asset(
    asset_id: str,
    *,
    event_id: str | None = None,
    approved_by: str = "human_operator",
    reason: str = "HITL-approved containment",
) -> dict[str, Any]:
    asset = get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    asset["status"] = "quarantined"
    result = {
        "asset_id": asset_id,
        "status": asset["status"],
        "approved_by": approved_by,
        "reason": reason,
    }
    log_tool_call(
        server=SERVER_NAME,
        tool_name="quarantine_asset",
        event_id=event_id,
        arguments={"asset_id": asset_id, "approved_by": approved_by, "reason": reason},
        result=result,
    )
    return result


@app.get("/health")
async def health():
    return {"status": "ready", "server": SERVER_NAME, "port": PORT}


@app.get("/tools")
async def tools():
    return {"tools": ["get_active_alerts", "quarantine_asset"]}


@app.post("/tools/get_active_alerts")
async def get_active_alerts_endpoint(request: ActiveAlertsRequest):
    return get_active_alerts(request.asset_id, request.event_id)


@app.post("/tools/quarantine_asset")
async def quarantine_asset_endpoint(request: QuarantineRequest):
    return quarantine_asset(
        request.asset_id,
        event_id=request.event_id,
        approved_by=request.approved_by,
        reason=request.reason,
    )


if __name__ == "__main__":
    uvicorn.run("mcp_servers.cyber_mcp.server:app", host="0.0.0.0", port=PORT)
