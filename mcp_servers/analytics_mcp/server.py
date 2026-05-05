"""Analytics MCP server exposing prediction and explanation tools on port 8003."""
from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.services.demo_data import get_alert, get_explanation, risk_tier
from mcp_servers.audit_store import log_tool_call


SERVER_NAME = "analytics_mcp"
PORT = 8003

app = FastAPI(title="Analytics MCP", version="3.0.0")


class PredictionRequest(BaseModel):
    asset_id: str
    features: dict[str, float] = Field(default_factory=dict)
    event_id: str | None = None


class ImportanceRequest(BaseModel):
    alert_id: str
    event_id: str | None = None


def run_prediction(asset_id: str, features: dict[str, float], event_id: str | None = None) -> dict[str, Any]:
    temp = features.get("temp", 25.0)
    soh = features.get("soh", 90.0)
    auth_burst = features.get("auth_failure_burst_rate", 0.0)
    entropy = features.get("packet_entropy", 0.0)
    score = min(99.0, max(0.0, (100 - soh) * 0.6 + max(temp - 25, 0) * 1.4 + auth_burst * 2.2 + entropy * 3.0))
    result = {"asset_id": asset_id, "risk_score": round(score, 1), "risk_tier": risk_tier(score)}
    log_tool_call(
        server=SERVER_NAME,
        tool_name="run_prediction",
        event_id=event_id,
        arguments={"asset_id": asset_id, "features": features},
        result=result,
    )
    return result


def get_feature_importance(alert_id: str, event_id: str | None = None) -> dict[str, Any]:
    if get_alert(alert_id) is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    explanation = get_explanation(alert_id)
    if explanation is None:
        raise HTTPException(status_code=404, detail=f"Explanation for {alert_id} not found")

    result = {
        "alert_id": alert_id,
        "asset_id": explanation["asset_id"],
        "risk_score": explanation["risk_score"],
        "top_factors": explanation["contributions"][:5],
    }
    log_tool_call(
        server=SERVER_NAME,
        tool_name="get_feature_importance",
        event_id=event_id,
        arguments={"alert_id": alert_id},
        result=result,
    )
    return result


@app.get("/health")
async def health():
    return {"status": "ready", "server": SERVER_NAME, "port": PORT}


@app.get("/tools")
async def tools():
    return {"tools": ["run_prediction", "get_feature_importance"]}


@app.post("/tools/run_prediction")
async def run_prediction_endpoint(request: PredictionRequest):
    return run_prediction(request.asset_id, request.features, request.event_id)


@app.post("/tools/get_feature_importance")
async def get_feature_importance_endpoint(request: ImportanceRequest):
    return get_feature_importance(request.alert_id, request.event_id)


if __name__ == "__main__":
    uvicorn.run("mcp_servers.analytics_mcp.server:app", host="0.0.0.0", port=PORT)
