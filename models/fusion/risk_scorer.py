"""
models/fusion/risk_scorer.py
Computes the unified cross-domain risk score and tier.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class RiskComponents:
    battery_risk:   float   # 0–100
    threat_score:   float   # 0–100
    fusion_context: float   # 0–100
    temporal_trend: float   # -100 to +100 (negative = improving)


WEIGHTS = {
    "battery_risk":   0.35,
    "threat_score":   0.35,
    "fusion_context": 0.20,
    "temporal_trend": 0.10,
}

RISK_TIERS = [
    (30,  "NOMINAL",     "green",  "monitor",   "log"),
    (60,  "INVESTIGATE", "yellow", "30min",     "flag"),
    (80,  "URGENT",      "orange", "5min",      "diagnose"),
    (101, "CRITICAL",    "red",    "immediate", "full_pipeline"),
]


def compute_risk_score(components: RiskComponents) -> float:
    raw = (
        WEIGHTS["battery_risk"]   * components.battery_risk   +
        WEIGHTS["threat_score"]   * components.threat_score   +
        WEIGHTS["fusion_context"] * components.fusion_context +
        WEIGHTS["temporal_trend"] * max(0.0, components.temporal_trend)
    )
    return round(min(max(raw, 0.0), 100.0), 2)


def get_risk_tier(score: float) -> dict:
    for threshold, tier, color, sla, action in RISK_TIERS:
        if score <= threshold:
            return {"tier": tier, "color": color, "sla": sla, "action": action, "score": score}
    return {"tier": "CRITICAL", "color": "red", "sla": "immediate", "action": "full_pipeline", "score": score}
