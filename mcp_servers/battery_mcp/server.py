"""Battery MCP server exposing battery asset tools on port 8001."""
from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.services.demo_data import get_asset
from mcp_servers.audit_store import log_tool_call


SERVER_NAME = "battery_mcp"
PORT = 8001

app = FastAPI(title="Battery MCP", version="3.0.0")


class AssetRequest(BaseModel):
    asset_id: str
    event_id: str | None = None


class MaintenanceRequest(AssetRequest):
    reason: str = "Agent requested maintenance review"


def get_asset_health(asset_id: str, event_id: str | None = None) -> dict[str, Any]:
    asset = get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    result = {
        "asset_id": asset_id,
        "soh": asset["soh"],
        "soc": asset["soc"],
        "temp": asset["temp"],
        "voltage": asset["voltage"],
        "rul_cycles": asset["rul_cycles"],
        "risk_tier": asset["risk_tier"],
        "maintenance_recommended": asset["soh"] < 75 or asset["temp"] > 40,
    }
    log_tool_call(
        server=SERVER_NAME,
        tool_name="get_asset_health",
        event_id=event_id,
        arguments={"asset_id": asset_id},
        result=result,
    )
    return result


def flag_for_maintenance(asset_id: str, reason: str, event_id: str | None = None) -> dict[str, Any]:
    asset = get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    asset["status"] = "maintenance_review"
    result = {"asset_id": asset_id, "status": asset["status"], "reason": reason}
    log_tool_call(
        server=SERVER_NAME,
        tool_name="flag_for_maintenance",
        event_id=event_id,
        arguments={"asset_id": asset_id, "reason": reason},
        result=result,
    )
    return result


@app.get("/health")
async def health():
    return {"status": "ready", "server": SERVER_NAME, "port": PORT}


@app.get("/tools")
async def tools():
    return {"tools": ["get_asset_health", "flag_for_maintenance"]}


@app.post("/tools/get_asset_health")
async def get_asset_health_endpoint(request: AssetRequest):
    return get_asset_health(request.asset_id, request.event_id)


@app.post("/tools/flag_for_maintenance")
async def flag_for_maintenance_endpoint(request: MaintenanceRequest):
    return flag_for_maintenance(request.asset_id, request.reason, request.event_id)


if __name__ == "__main__":
    uvicorn.run("mcp_servers.battery_mcp.server:app", host="0.0.0.0", port=PORT)
