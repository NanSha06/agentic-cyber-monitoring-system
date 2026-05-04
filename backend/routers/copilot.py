"""
backend/routers/copilot.py
AI Copilot endpoint — multi-turn conversational RAG interface.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/copilot", tags=["copilot"])

# ── Rate limiting (10 req/min per session) ────────────────────────────────────
_RATE_STORE: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT  = 10
RATE_WINDOW = 60.0


def _check_rate_limit(session_id: str) -> None:
    now = time.time()
    window_start = now - RATE_WINDOW
    _RATE_STORE[session_id] = [t for t in _RATE_STORE[session_id] if t > window_start]
    if len(_RATE_STORE[session_id]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: {RATE_LIMIT} requests per minute. Try again shortly.",
            headers={"Retry-After": "60"},
        )
    _RATE_STORE[session_id].append(now)


# ── Schemas ───────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role:    str   # "user" | "assistant"
    content: str


class CopilotRequest(BaseModel):
    message:       str
    history:       list[ChatMessage] = Field(default_factory=list)
    asset_context: dict | None = None
    session_id:    str = "default"


class CopilotResponse(BaseModel):
    response:          str
    sources:           list[str]
    suggested_actions: list[str]
    intent:            str
    context_count:     int
    cached:            bool = False
    timestamp:         str


# ── Lazy chain loader ─────────────────────────────────────────────────────────
_chain = None

def _get_chain():
    global _chain
    if _chain is None:
        try:
            from rag.chains.conversational_chain import ConversationalChain
            _chain = ConversationalChain()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Copilot not available: {e}. Ensure dependencies are installed and the FAISS index is built."
            )
    return _chain


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/chat", response_model=CopilotResponse)
async def chat(req: CopilotRequest, request: Request):
    session_id = (
        request.headers.get("X-Session-ID")
        or request.cookies.get("session_id")
        or req.session_id
        or "default"
    )
    _check_rate_limit(session_id)
    chain = _get_chain()

    history_dicts = [m.model_dump() for m in req.history]
    result = chain.run(
        message=req.message,
        history=history_dicts,
        asset_context=req.asset_context,
    )

    return CopilotResponse(
        response=          result["response"],
        sources=           result.get("sources", []),
        suggested_actions= result.get("suggested_actions", []),
        intent=            result.get("intent", "general"),
        context_count=     result.get("context_count", 0),
        cached=            bool(result.get("cached", False)),
        timestamp=         datetime.now(timezone.utc).isoformat(),
    )


@router.get("/status")
async def copilot_status():
    """Check if the copilot is ready (FAISS index + at least one LLM key present)."""
    from rag.retrieval.retriever import retriever_available
    import os

    nvidia_key_set  = bool(os.environ.get("NVIDIA_API_KEY"))
    gemini_key_set  = bool(os.environ.get("GEMINI_API_KEY"))
    llm_ready       = nvidia_key_set or gemini_key_set

    return {
        "faiss_index_ready": retriever_available(),
        "nvidia_key_set":    nvidia_key_set,
        "gemini_key_set":    gemini_key_set,
        "llm_ready":         llm_ready,
        "primary_llm":       "gemma-4-31b-it" if nvidia_key_set else "gemini-fallback",
        "ready":             retriever_available() and llm_ready,
    }


@router.get("/suggested-prompts")
async def suggested_prompts(asset_id: str | None = None):
    """Return context-aware suggested prompts for the UI."""
    if asset_id:
        return {"prompts": [
            f"Why is {asset_id} showing a high risk score?",
            f"What is the SOP for the current alert on {asset_id}?",
            f"What threat type is affecting {asset_id}?",
            "What are the top 3 mitigation actions I should take?",
        ]}
    return {"prompts": [
        "Which asset has the highest risk right now?",
        "What is the SOP for a thermal runaway event?",
        "Explain the difference between a DoS and DDoS attack on BMS",
        "What does a high auth_failure_burst_rate indicate?",
        "What should I do when risk score exceeds 80?",
    ]}
