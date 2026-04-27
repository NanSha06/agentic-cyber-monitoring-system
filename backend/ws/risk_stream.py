"""
backend/ws/risk_stream.py
WebSocket endpoint streaming live risk scores at ~1 Hz.
"""
from __future__ import annotations
import asyncio
import json
import random
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])

_ASSET_IDS = [f"BATTERY-{i:03d}" for i in range(1, 13)]


@router.websocket("/ws/risk-stream")
async def risk_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Emit a risk update for a random subset of assets
            updates = []
            for asset_id in random.sample(_ASSET_IDS, k=4):
                risk = round(random.uniform(5, 95), 1)
                tier = (
                    "NOMINAL"     if risk <= 30 else
                    "INVESTIGATE" if risk <= 60 else
                    "URGENT"      if risk <= 80 else
                    "CRITICAL"
                )
                updates.append({
                    "asset_id":   asset_id,
                    "risk_score": risk,
                    "risk_tier":  tier,
                    "timestamp":  datetime.now(timezone.utc).isoformat(),
                })

            await websocket.send_text(json.dumps({"type": "risk_update", "data": updates}))
            await asyncio.sleep(1.0)   # 1 Hz

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")
