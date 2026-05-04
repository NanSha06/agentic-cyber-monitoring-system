"""
backend/routers/explanations.py
LIME explanation retrieval endpoints.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from backend.services.demo_data import ALERT_STORE, get_explanation as build_alert_explanation

router = APIRouter(prefix="/explain", tags=["explanations"])


@router.get("/{alert_id}")
async def get_explanation(alert_id: str):
    """Return LIME explanation for a given alert."""
    explanation = build_alert_explanation(alert_id)
    if explanation is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return explanation


@router.get("/")
async def list_explanations():
    explanations = [
        build_alert_explanation(a["alert_id"])
        for a in ALERT_STORE
        if a["explanation_available"]
    ]
    return {"explanations": explanations, "total": len(explanations)}
