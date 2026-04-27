"""
backend/routers/predictions.py
Predict endpoint: runs all models on incoming asset features.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import random
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

from models.fusion.risk_scorer import compute_risk_score, get_risk_tier, RiskComponents

router = APIRouter(prefix="/predict", tags=["predictions"])


class PredictRequest(BaseModel):
    asset_id: str
    features: dict[str, float]


class PredictResponse(BaseModel):
    asset_id:              str
    risk_score:            float
    risk_tier:             str
    risk_color:            str
    soh:                   float
    rul_cycles:            int
    threat_type:           str
    threat_confidence:     float
    is_battery_anomaly:    bool
    is_zero_day:           bool
    explanation_available: bool
    timestamp:             str


def _compute_battery_risk(features: dict) -> float:
    """Derive battery risk 0–100 from feature heuristics."""
    soh     = features.get("soh", 90.0)
    temp    = features.get("temp", 25.0)
    v_var   = features.get("voltage_variance_10m", 0.0)
    score   = (100 - soh) * 0.5 + max(0, temp - 35) * 2 + v_var * 10
    return float(min(max(score, 0), 100))


def _compute_threat_score(features: dict) -> float:
    entropy = features.get("packet_entropy", 0.0)
    burst   = features.get("auth_failure_burst_rate", 0.0)
    lateral = features.get("lateral_move_indicator", 0.0)
    score   = entropy * 20 + burst * 5 + lateral * 30
    return float(min(max(score, 0), 100))


@router.post("/", response_model=PredictResponse)
async def predict(req: PredictRequest):
    f = req.features

    # Battery risk
    battery_risk = _compute_battery_risk(f)

    # Threat score
    threat_score = _compute_threat_score(f)

    # Fusion risk score
    components = RiskComponents(
        battery_risk=battery_risk,
        threat_score=threat_score,
        fusion_context=f.get("cross_domain_risk_delta", 0.0),
        temporal_trend=f.get("raw_risk_proxy", 0.0),
    )
    score = compute_risk_score(components)
    tier  = get_risk_tier(score)

    return PredictResponse(
        asset_id=req.asset_id,
        risk_score=score,
        risk_tier=tier["tier"],
        risk_color=tier["color"],
        soh=f.get("soh", 85.0),
        rul_cycles=int(f.get("rul_cycles", 300)),
        threat_type="normal" if threat_score < 20 else "suspicious",
        threat_confidence=0.85,
        is_battery_anomaly=battery_risk > 70,
        is_zero_day=threat_score > 80,
        explanation_available=(score > 60),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/history")
async def prediction_history(asset_id: str = None, limit: int = 50):
    """Return last N predictions for an asset (mock)."""
    return {"predictions": [], "total": 0}
