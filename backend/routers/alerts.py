"""
backend/routers/alerts.py
Alert management endpoints.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.demo_data import ALERT_STORE

router = APIRouter(prefix="/alerts", tags=["alerts"])


class Alert(BaseModel):
    alert_id:              str
    asset_id:              str
    risk_score:            float
    risk_tier:             str
    threat_type:           str
    description:           str
    timestamp:             str
    resolved:              bool
    explanation_available: bool


@router.get("/", response_model=list[Alert])
async def list_alerts(resolved: bool = False, limit: int = 50):
    return [a for a in ALERT_STORE if a["resolved"] == resolved][:limit]


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(alert_id: str):
    for a in ALERT_STORE:
        if a["alert_id"] == alert_id:
            return a
    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    for a in ALERT_STORE:
        if a["alert_id"] == alert_id:
            a["resolved"] = True
            return {"status": "resolved", "alert_id": alert_id}
    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
