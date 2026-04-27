"""
backend/routers/health.py
Health check endpoints.
"""
from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health():
    return {
        "status":    "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version":   "1.0.0",
    }


@router.get("/metrics")
async def metrics():
    return {
        "uptime_seconds":   0,
        "predictions_total": 0,
        "alerts_active":     0,
        "models_loaded":     ["soh_predictor", "anomaly_detector", "attack_classifier"],
    }
