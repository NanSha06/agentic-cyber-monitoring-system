"""
backend/routers/explanations.py
LIME explanation retrieval endpoints.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/explain", tags=["explanations"])

# Mock explanations keyed by alert_id
_MOCK_EXPLANATIONS: dict[str, dict] = {}


def _mock_explanation(alert_id: str, asset_id: str, risk_score: float) -> dict:
    return {
        "alert_id":  alert_id,
        "asset_id":  asset_id,
        "risk_score": risk_score,
        "prediction": risk_score,
        "intercept":  15.2,
        "contributions": [
            {"feature": "auth_failure_burst_rate", "weight":  18.5},
            {"feature": "temp_rate_of_change",     "weight":  12.3},
            {"feature": "voltage_variance_10m",    "weight":  -8.7},
            {"feature": "packet_entropy",          "weight":   7.1},
            {"feature": "soc_drop_under_load",     "weight":   5.4},
            {"feature": "lateral_move_indicator",  "weight":   3.2},
        ],
        "human_readable": (
            f"ALERT — {asset_id} — Risk Score: {risk_score}/100\n"
            "Contributing factors:\n"
            "  · auth_failure_burst_rate: +18.5\n"
            "  · temp_rate_of_change: +12.3\n"
            "  · voltage_variance_10m: -8.7\n"
            "  · packet_entropy: +7.1\n"
            "  · soc_drop_under_load: +5.4\n"
            "  · lateral_move_indicator: +3.2"
        ),
    }


@router.get("/{alert_id}")
async def get_explanation(alert_id: str):
    """Return LIME explanation for a given alert."""
    if alert_id not in _MOCK_EXPLANATIONS:
        # Generate on the fly for demo
        _MOCK_EXPLANATIONS[alert_id] = _mock_explanation(
            alert_id=alert_id,
            asset_id="BATTERY-001",
            risk_score=72.5,
        )
    return _MOCK_EXPLANATIONS[alert_id]


@router.get("/")
async def list_explanations():
    return {"explanations": list(_MOCK_EXPLANATIONS.values()), "total": len(_MOCK_EXPLANATIONS)}
