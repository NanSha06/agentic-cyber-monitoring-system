"""
backend/routers/assets.py
Asset management endpoints — fleet listing and individual asset detail.
"""
from __future__ import annotations
import uuid
import random
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/assets", tags=["assets"])

# ── Mock asset store (replace with DB in production) ─────────────────────────
def _mock_assets() -> list[dict]:
    assets = []
    for i in range(1, 13):
        risk = random.uniform(5, 95)
        assets.append({
            "asset_id":   f"BATTERY-{i:03d}",
            "location":   f"Tower-{i}",
            "soh":        round(random.uniform(60, 100), 1),
            "soc":        round(random.uniform(20, 100), 1),
            "temp":       round(random.uniform(18, 45), 1),
            "voltage":    round(random.uniform(3.2, 4.2), 2),
            "risk_score": round(risk, 1),
            "risk_tier":  _tier(risk),
            "rul_cycles": random.randint(50, 800),
            "threat_type": random.choice(["normal", "normal", "normal", "portscan", "dos"]),
            "last_seen":  datetime.now(timezone.utc).isoformat(),
            "status":     "online",
        })
    return assets


def _tier(score: float) -> str:
    if score <= 30:  return "NOMINAL"
    if score <= 60:  return "INVESTIGATE"
    if score <= 80:  return "URGENT"
    return "CRITICAL"


# Seed once at import time
_ASSET_STORE: list[dict] = _mock_assets()


class Asset(BaseModel):
    asset_id:   str
    location:   str
    soh:        float
    soc:        float
    temp:       float
    voltage:    float
    risk_score: float
    risk_tier:  str
    rul_cycles: int
    threat_type: str
    last_seen:  str
    status:     str


@router.get("/", response_model=list[Asset])
async def list_assets():
    """Return all monitored assets."""
    return _ASSET_STORE


@router.get("/{asset_id}", response_model=Asset)
async def get_asset(asset_id: str):
    for a in _ASSET_STORE:
        if a["asset_id"] == asset_id:
            return a
    raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")


@router.get("/{asset_id}/history")
async def get_asset_history(asset_id: str, hours: int = 24):
    """Return synthetic time-series history for an asset."""
    import pandas as pd
    import numpy as np

    times = pd.date_range(end=datetime.now(timezone.utc), periods=hours * 6, freq="10min")
    base_voltage = 3.8
    base_temp    = 25.0
    history = []
    for i, t in enumerate(times):
        history.append({
            "timestamp": t.isoformat(),
            "voltage":   round(base_voltage + np.sin(i / 20) * 0.3 + random.gauss(0, 0.02), 3),
            "temp":      round(base_temp + np.sin(i / 30) * 5 + random.gauss(0, 0.5), 1),
            "soc":       round(max(10, 95 - i * 0.1 + random.gauss(0, 1)), 1),
            "current":   round(random.gauss(-0.5, 0.3), 3),
        })
    return {"asset_id": asset_id, "history": history}
