"""
Shared in-memory demo data for V2 flows.

The production version should replace this module with database-backed assets,
alerts, and explanations. Keeping the demo store centralized ensures the alert
feed, explain endpoint, and copilot all refer to the same records.
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone, timedelta


_RNG = random.Random(42)


def risk_tier(score: float) -> str:
    if score <= 30:
        return "NOMINAL"
    if score <= 60:
        return "INVESTIGATE"
    if score <= 80:
        return "URGENT"
    return "CRITICAL"


def _mock_assets() -> list[dict]:
    assets = []
    threats = ["normal", "normal", "normal", "portscan", "dos", "ddos", "bruteforce"]
    for i in range(1, 13):
        risk = _RNG.uniform(5, 95)
        assets.append({
            "asset_id": f"BATTERY-{i:03d}",
            "location": f"Tower-{i}",
            "soh": round(_RNG.uniform(60, 100), 1),
            "soc": round(_RNG.uniform(20, 100), 1),
            "temp": round(_RNG.uniform(18, 45), 1),
            "voltage": round(_RNG.uniform(3.2, 4.2), 2),
            "risk_score": round(risk, 1),
            "risk_tier": risk_tier(risk),
            "rul_cycles": _RNG.randint(50, 800),
            "threat_type": _RNG.choice(threats),
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "status": "online",
        })
    return assets


ASSET_STORE: list[dict] = _mock_assets()


def _mock_alerts() -> list[dict]:
    threats = ["portscan", "dos", "bruteforce", "ddos"]
    alerts = []
    base_time = datetime.now(timezone.utc)
    risky_assets = sorted(ASSET_STORE, key=lambda a: a["risk_score"], reverse=True)
    for i in range(20):
        asset = risky_assets[i % len(risky_assets)]
        baseline = max(asset["risk_score"], 45)
        risk = min(99.0, baseline + _RNG.uniform(0, 12))
        alert_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"cyber-battery-alert-{i}"))
        alerts.append({
            "alert_id": alert_id,
            "asset_id": asset["asset_id"],
            "risk_score": round(risk, 1),
            "risk_tier": "URGENT" if risk <= 80 else "CRITICAL",
            "threat_type": _RNG.choice(threats),
            "description": "Anomalous battery telemetry coincides with suspicious network activity",
            "timestamp": (base_time - timedelta(minutes=i * 7)).isoformat(),
            "resolved": i > 15,
            "explanation_available": risk > 60,
        })
    return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)


ALERT_STORE: list[dict] = _mock_alerts()


def get_asset(asset_id: str) -> dict | None:
    return next((a for a in ASSET_STORE if a["asset_id"] == asset_id), None)


def get_alert(alert_id: str) -> dict | None:
    return next((a for a in ALERT_STORE if a["alert_id"] == alert_id), None)


def get_latest_alert_for_asset(asset_id: str) -> dict | None:
    return next((a for a in ALERT_STORE if a["asset_id"] == asset_id and not a["resolved"]), None)


def build_explanation(alert: dict) -> dict:
    risk_score = float(alert["risk_score"])
    asset = get_asset(alert["asset_id"]) or {}
    temp_weight = round(max(float(asset.get("temp", 25)) - 28, 0) * 1.15, 1)
    cyber_weight = 14.0 if alert["threat_type"] in {"dos", "ddos", "bruteforce"} else 8.5
    soh_weight = round(max(85 - float(asset.get("soh", 85)), 0) * 0.45, 1)
    voltage_weight = round(max(3.7 - float(asset.get("voltage", 3.8)), 0) * 18, 1)

    contributions = [
        {"feature": "auth_failure_burst_rate", "weight": cyber_weight},
        {"feature": "temp_rate_of_change", "weight": temp_weight},
        {"feature": "packet_entropy", "weight": 7.1},
        {"feature": "soh_degradation_gap", "weight": soh_weight},
        {"feature": "voltage_variance_10m", "weight": -voltage_weight},
        {"feature": "lateral_move_indicator", "weight": 3.2},
    ]

    return {
        "alert_id": alert["alert_id"],
        "asset_id": alert["asset_id"],
        "risk_score": risk_score,
        "prediction": risk_score,
        "intercept": 15.2,
        "contributions": contributions,
        "human_readable": (
            f"ALERT - {alert['asset_id']} - Risk Score: {risk_score}/100\n"
            "Contributing factors:\n"
            + "\n".join(f"  - {c['feature']}: {c['weight']:+.1f}" for c in contributions)
        ),
    }


def get_explanation(alert_id: str) -> dict | None:
    alert = get_alert(alert_id)
    if alert is None:
        return None
    return build_explanation(alert)
