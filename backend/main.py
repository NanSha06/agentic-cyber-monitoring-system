"""
backend/main.py
FastAPI application entry point for the Cyber-Battery Intelligence Platform.

Start with:
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from backend.routers import assets, predictions, alerts, explanations, health
from backend.ws.risk_stream import router as ws_router

log = structlog.get_logger()

app = FastAPI(
    title="Agentic Cyber-Battery Intelligence Platform",
    version="1.0.0",
    description="ML-powered risk intelligence for cyber-physical battery assets",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(assets.router)
app.include_router(predictions.router)
app.include_router(alerts.router)
app.include_router(explanations.router)
app.include_router(ws_router)


@app.on_event("startup")
async def startup():
    log.info("platform_startup", version="1.0.0", env="development")
    print("🛡️  Cyber-Battery Platform API started — http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown():
    log.info("platform_shutdown")
