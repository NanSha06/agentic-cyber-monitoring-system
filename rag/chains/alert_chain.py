"""
rag/chains/alert_chain.py
AlertRAGChain — retrieves context from FAISS and generates Gemini-grounded explanations.
Falls back to LIME-only explanation if Gemini API is unavailable.
"""
from __future__ import annotations
import os
import time
import hashlib
import json
from pathlib import Path
from functools import lru_cache

# Response cache to avoid duplicate API calls
_CACHE: dict[str, dict] = {}
CACHE_PATH = Path("audit_logs/rag_cache.jsonl")


def _cache_key(alert: dict, lime: dict) -> str:
    payload = f"{alert.get('asset_id')}:{alert.get('risk_score')}:{json.dumps(lime, sort_keys=True)}"
    return hashlib.md5(payload.encode()).hexdigest()[:12]


class AlertRAGChain:
    def __init__(self):
        from rag.retrieval.retriever import KnowledgeRetriever, retriever_available
        from rag.chains.prompts import build_alert_prompt

        api_key = os.environ.get("GEMINI_API_KEY", "")
        self.model = None
        self.gemini_configured = bool(api_key)
        self.last_generation_error: str | None = None
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        self._build_alert_prompt = build_alert_prompt

        # Load retriever if index exists, else operate in Gemini-only mode
        self.retriever = None
        if retriever_available():
            try:
                self.retriever = KnowledgeRetriever.get_instance()
            except Exception as e:
                print(f"⚠️  Retriever load failed: {e} — operating without RAG context")
        else:
            print("⚠️  FAISS index not found. Run: python rag/ingestion/build_index.py")

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
                print(f"⚠️  Retrieval failed: {e}")

        # Build prompt and call Gemini with retry
        prompt = self._build_alert_prompt(alert, lime_explanation, context_docs)
        answer = self._call_gemini_with_retry(prompt)

        result = {
            "answer":        answer,
            "sources":       list({d["source"] for d in context_docs}),
            "query":         query,
            "context_count": len(context_docs),
            "cached":        False,
        }

        # Cache the result
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

    def _call_gemini_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Call Gemini with exponential backoff. Returns fallback text if all retries fail."""
        if self.model is None:
            return self._fallback_answer()

        for attempt in range(max_retries):
            try:
                self.last_generation_error = None
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                self.last_generation_error = str(e)
                err = str(e)
                if "429" in err or "quota" in err.lower():
                    wait = 2 ** attempt
                    print(f"  ⚠️  Gemini rate limit — retrying in {wait}s (attempt {attempt+1})")
                    time.sleep(wait)
                else:
                    print(f"  ⚠️  Gemini error: {e}")
                    break
        return self._fallback_answer()

    def _fallback_answer(self) -> str:
        if self.gemini_configured:
            reason = "Gemini generation is temporarily unavailable"
            if self.last_generation_error and self._is_invalid_api_key_error(self.last_generation_error):
                reason = "Gemini generation is unavailable because the configured API key was rejected"
            return (
                f"{reason}. I am using local alert fallback mode. Review the top LIME contributors "
                "to identify whether the risk is battery-driven, cyber-driven, or cross-domain. "
                "Recommended next steps: verify recent battery telemetry, inspect matching network "
                "alerts, and follow the relevant SOP before taking containment action."
            )

        return (
            "Gemini generation is not configured, so I am using local alert fallback mode. Review "
            "the top LIME contributors to identify whether the risk is battery-driven, cyber-driven, "
            "or cross-domain. Recommended next steps: verify recent battery telemetry, inspect "
            "matching network alerts, and follow the relevant SOP before taking containment action."
        )

    def _is_invalid_api_key_error(self, error: str) -> bool:
        low = error.lower()
        return "api_key_invalid" in low or "api key not found" in low or "invalid api key" in low

    def _persist_cache(self, key: str, alert: dict, result: dict):
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            entry = {"key": key, "asset_id": alert.get("asset_id"), **result}
            with CACHE_PATH.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
