"""
explainability/explanation_store.py
In-memory + file-backed store for LIME explanations keyed by alert_id.
"""
from __future__ import annotations
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

STORE_PATH = Path("audit_logs/explanations")


class ExplanationStore:
    _store: dict[str, dict] = {}

    @classmethod
    def save(cls, alert_id: str, explanation: dict, risk_score: float,
             asset_id: str) -> str:
        entry = {
            "alert_id":    alert_id,
            "asset_id":    asset_id,
            "risk_score":  risk_score,
            "explanation": explanation,
            "created_at":  datetime.now(timezone.utc).isoformat(),
        }
        cls._store[alert_id] = entry

        # Persist to disk
        STORE_PATH.mkdir(parents=True, exist_ok=True)
        path = STORE_PATH / f"{alert_id}.json"
        path.write_text(json.dumps(entry, indent=2))
        return alert_id

    @classmethod
    def get(cls, alert_id: str) -> dict | None:
        if alert_id in cls._store:
            return cls._store[alert_id]
        path = STORE_PATH / f"{alert_id}.json"
        if path.exists():
            data = json.loads(path.read_text())
            cls._store[alert_id] = data
            return data
        return None

    @classmethod
    def list_all(cls) -> list[dict]:
        STORE_PATH.mkdir(parents=True, exist_ok=True)
        return [json.loads(p.read_text()) for p in STORE_PATH.glob("*.json")]
