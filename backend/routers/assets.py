"""
backend/routers/assets.py
Asset management endpoints — fleet listing and individual asset detail.
"""
from __future__ import annotations
import random
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.demo_data import ASSET_STORE

router = APIRouter(prefix="/assets", tags=["assets"])


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
    return ASSET_STORE


@router.get("/{asset_id}", response_model=Asset)
async def get_asset(asset_id: str):
    for a in ASSET_STORE:
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
