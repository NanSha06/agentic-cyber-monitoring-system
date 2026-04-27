"""
backend/routers/alerts.py
Alert management endpoints.
"""
from __future__ import annotations
import uuid
import random
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _mock_alerts() -> list[dict]:
    threats = ["portscan", "dos", "bruteforce", "normal", "ddos"]
    tiers   = ["INVESTIGATE", "URGENT", "CRITICAL"]
    alerts  = []
    base_time = datetime.now(timezone.utc)
    for i in range(20):
        risk = random.uniform(45, 99)
        alerts.append({
            "alert_id":   str(uuid.uuid4()),
            "asset_id":   f"BATTERY-{random.randint(1,12):03d}",
            "risk_score": round(risk, 1),
            "risk_tier":  "URGENT" if risk < 80 else "CRITICAL",
            "threat_type": random.choice(threats),
            "description": f"Anomalous battery + network activity detected",
            "timestamp":  (base_time - timedelta(minutes=i * 7)).isoformat(),
            "resolved":   i > 15,
            "explanation_available": risk > 60,
        })
    return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)


_ALERT_STORE = _mock_alerts()


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
    return [a for a in _ALERT_STORE if a["resolved"] == resolved][:limit]


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(alert_id: str):
    for a in _ALERT_STORE:
        if a["alert_id"] == alert_id:
            return a
    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    for a in _ALERT_STORE:
        if a["alert_id"] == alert_id:
            a["resolved"] = True
            return {"status": "resolved", "alert_id": alert_id}
    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
