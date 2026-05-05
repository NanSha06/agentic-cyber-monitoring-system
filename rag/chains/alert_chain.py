"""
rag/chains/alert_chain.py
AlertRAGChain — retrieves context from FAISS and generates LLM-grounded explanations.
Uses Gemma 4 (primary) via LLMRouter; falls back to Gemini, then LIME-only if both are unavailable.
"""
from __future__ import annotations
import time
import hashlib
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Response cache to avoid duplicate API calls
_CACHE: dict[str, dict] = {}
CACHE_PATH = Path("audit_logs/rag_cache.jsonl")
CACHE_SCHEMA_VERSION = "llmrouter-gemma4-v1"
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


def _load_persisted_cache() -> None:
    if _CACHE or not CACHE_PATH.exists():
        return
    try:
        for line in CACHE_PATH.read_text().splitlines():
            entry = json.loads(line)
            key = entry.get("key")
            if key:
                _CACHE[key] = {
                    "answer": entry.get("answer", ""),
                    "sources": entry.get("sources", []),
                    "query": entry.get("query", ""),
                    "context_count": entry.get("context_count", 0),
                    "cached": True,
                }
    except Exception:
        _CACHE.clear()


def _cache_key(alert: dict, lime: dict) -> str:
    nvidia_configured = bool(os.environ.get("NVIDIA_API_KEY"))
    gemini_configured = bool(os.environ.get("GEMINI_API_KEY"))
    payload = (
        f"{CACHE_SCHEMA_VERSION}:nvidia={nvidia_configured}:gemini={gemini_configured}:"
        f"{alert.get('asset_id')}:{alert.get('risk_score')}:{json.dumps(lime, sort_keys=True)}"
    )
    return hashlib.md5(payload.encode()).hexdigest()[:12]


class AlertRAGChain:
    def __init__(self):
        from rag.retrieval.retriever import KnowledgeRetriever, retriever_available
        from rag.chains.prompts import build_alert_prompt
        from backend.llm.router import LLMRouter

        _load_persisted_cache()
        self.llm = LLMRouter()
        self.last_generation_error: str | None = None
        self._build_alert_prompt = build_alert_prompt

        # Load retriever if index exists, else operate in LLM-only mode
        self.retriever = None
        if retriever_available():
            try:
                self.retriever = KnowledgeRetriever.get_instance()
            except Exception as e:
                print(f"[WARN] Retriever load failed: {e} -- operating without RAG context")
        else:
            print("[WARN] FAISS index not found. Run: python rag/ingestion/build_index.py")

    def run(self, alert: dict, lime_explanation: dict) -> dict:
        """Run the full RAG chain: retrieve → prompt → generate."""
        # Check cache first
        key = _cache_key(alert, lime_explanation)
        if key in _CACHE:
            return {**_CACHE[key], "cached": True}

        # Retrieve context docs
        query = self._build_query(alert, lime_explanation)
        context_docs = []
        if self.retriever:
            try:
                context_docs = self.retriever.retrieve(query, k=5)
            except Exception as e:
                print(f"[WARN] Retrieval failed: {e}")

        # Build prompt and call Gemini with retry
        prompt = self._build_alert_prompt(alert, lime_explanation, context_docs)
        answer = self._call_gemini_with_retry(prompt, alert, lime_explanation, context_docs)

        result = {
            "answer":        answer,
            "sources":       list({d["source"] for d in context_docs}),
            "query":         query,
            "context_count": len(context_docs),
            "cached":        False,
        }

        # Cache only successful LLM answers. Fallbacks should recover once the
        # model/key/network configuration is fixed.
        if not self._is_fallback_answer(answer):
            _CACHE[key] = result
            self._persist_cache(key, alert, result)
        return result

    def _build_query(self, alert: dict, lime: dict) -> str:
        contribs = ", ".join(
            f"{c['feature']} ({c['weight']:+.2f})"
            for c in lime.get("contributions", [])[:4]
        )
        return (
            f"Asset {alert.get('asset_id', 'unknown')} — Risk Score {alert.get('risk_score', 0)}/100. "
            f"Key contributing factors: {contribs}. "
            f"Threat type: {alert.get('threat_type', 'unknown')}. "
            f"What is the likely root cause and recommended mitigation?"
        )

    def _call_gemini_with_retry(
        self,
        prompt: str,
        alert: dict,
        lime_explanation: dict,
        context_docs: list[dict],
        max_retries: int = 3,
    ) -> str:
        """Call LLMRouter (Gemma 4 → Gemini) with retry. Returns LIME fallback if all fail."""
        for attempt in range(max_retries):
            try:
                self.last_generation_error = None
                return self.llm.generate(prompt, task_type="critical_reasoning")
            except Exception as e:
                self.last_generation_error = str(e)
                err = str(e)
                if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                    wait = 2 ** attempt
                    print(f"  [WARN] LLM rate limit -- retrying in {wait}s (attempt {attempt+1})")
                    time.sleep(wait)
                else:
                    print(f"  [WARN] LLM error: {e}")
                    break
        return self._fallback_answer(alert, lime_explanation, context_docs)

    def _fallback_answer(self, alert: dict, lime_explanation: dict, context_docs: list[dict]) -> str:
        contributors = lime_explanation.get("contributions", [])[:3]
        factors = ", ".join(
            f"{c.get('feature', 'unknown')} ({float(c.get('weight', 0)):+.1f})"
            for c in contributors
        ) or "no LIME contributors were available"
        sources = sorted({d.get("source", "unknown") for d in context_docs})
        source_text = ", ".join(f"[{s}]" for s in sources) if sources else "no retrieved sources"
        asset_id = alert.get("asset_id", "this asset")
        risk = alert.get("risk_score", 0)
        threat = alert.get("threat_type", "unknown")

        reason = "LLM generation (Gemma 4 + Gemini) is temporarily unavailable"
        if self.last_generation_error and self._is_invalid_api_key_error(self.last_generation_error):
            reason = "LLM generation is unavailable due to an invalid or missing API key"
        return (
            f"{reason}. Local fallback: {asset_id} is at risk {risk}/100 with threat type "
            f"{threat}. The strongest available contributors are {factors}. Retrieved context: "
            f"{source_text}. Recommended actions: 1. verify battery telemetry and temperature "
            "trend, 2. inspect matching network/authentication alerts, 3. follow the cited SOP "
            "before containment or maintenance action."
        )

    def _is_invalid_api_key_error(self, error: str) -> bool:
        low = error.lower()
        return (
            "api_key_invalid" in low
            or "api key not found" in low
            or "invalid api key" in low
            or "unauthorized" in low
        )

    def _is_fallback_answer(self, answer: str) -> bool:
        return answer.startswith("LLM generation")

    def _persist_cache(self, key: str, alert: dict, result: dict):
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            entry = {"key": key, "asset_id": alert.get("asset_id"), **result}
            with CACHE_PATH.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
