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

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import structlog

from backend.routers import assets, predictions, alerts, explanations, health
from backend.routers import copilot
from backend.ws.risk_stream import router as ws_router

log = structlog.get_logger()

app = FastAPI(
    title="Agentic Cyber-Battery Intelligence Platform",
    version="2.0.0",
    description="ML-powered risk intelligence + RAG AI Copilot for cyber-physical battery assets",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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
app.include_router(copilot.router)     # ← V2: AI Copilot
app.include_router(ws_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.on_event("startup")
async def startup():
    log.info("platform_startup", version="2.0.0", env="development")
    print("Cyber-Battery Platform API v2.0 started")
    print("   API docs  -> http://localhost:8000/docs")
    print("   Copilot   -> POST /copilot/chat")
    print("   Status    -> GET  /copilot/status")


@app.on_event("shutdown")
async def shutdown():
    log.info("platform_shutdown")
