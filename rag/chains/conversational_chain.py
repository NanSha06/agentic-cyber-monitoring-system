"""
rag/chains/conversational_chain.py
Multi-turn conversational chain for the AI Copilot.
Handles intent classification and routes to the correct chain.
"""
from __future__ import annotations
import time
import hashlib
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

# Intent types
INTENT_ALERT_QUERY  = "alert_query"
INTENT_SOP_LOOKUP   = "sop_lookup"
INTENT_GENERAL      = "general"

# Keywords that signal each intent
ALERT_KEYWORDS = ["risky","risk","alert","score","anomaly","threat","why","danger","critical","urgent"]
SOP_KEYWORDS   = ["sop","procedure","protocol","steps","how to","what should","playbook","response","mitigation"]

# Max history turns to include in prompt
MAX_HISTORY_TURNS = 5
_RESPONSE_CACHE: dict[str, dict] = {}


def _cache_key(message: str, history: list[dict], asset_context: dict | None) -> str:
    payload = {
        "message": message,
        "history": history[-(MAX_HISTORY_TURNS * 2):],
        "asset_context": asset_context or {},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def classify_intent(message: str) -> str:
    low = message.lower()
    if any(k in low for k in SOP_KEYWORDS):
        return INTENT_SOP_LOOKUP
    if any(k in low for k in ALERT_KEYWORDS):
        return INTENT_ALERT_QUERY
    return INTENT_GENERAL


class ConversationalChain:
    def __init__(self):
        from rag.retrieval.retriever import KnowledgeRetriever, retriever_available
        from rag.chains.prompts import GENERAL_QUERY_PROMPT
        from backend.llm.router import LLMRouter

        self.llm = LLMRouter()
        self.last_generation_error: str | None = None
        self._general_prompt   = GENERAL_QUERY_PROMPT

        self.retriever = None
        if retriever_available():
            try:
                self.retriever = KnowledgeRetriever.get_instance()
            except Exception:
                pass

    def run(
        self,
        message: str,
        history: list[dict],
        asset_context: dict | None = None,
    ) -> dict:
        key = _cache_key(message, history, asset_context)
        if key in _RESPONSE_CACHE:
            return {**_RESPONSE_CACHE[key], "cached": True}

        intent = classify_intent(message)
        context_docs = []

        # Build history string (last N turns)
        recent = history[-(MAX_HISTORY_TURNS * 2):]
        history_text = "\n".join(
            f"{'Operator' if m['role']=='user' else 'Assistant'}: {m['content']}"
            for m in recent
        )

        if intent == INTENT_ALERT_QUERY and asset_context:
            # Use AlertRAGChain for asset-specific questions
            from rag.chains.alert_chain import AlertRAGChain
            chain = AlertRAGChain()
            alert, lime = self._hydrate_alert_context(asset_context)
            result = chain.run(alert, lime)
            answer = result["answer"]
            sources = result["sources"]
            suggested = self._suggest_actions(asset_context)
            context_count = result.get("context_count", 0)

        elif intent == INTENT_SOP_LOOKUP:
            from rag.chains.sop_chain import SOPChain
            result = SOPChain().run(message, history_text=history_text)
            answer = result["answer"]
            sources = result["sources"]
            suggested = result["suggested_actions"]
            context_count = result.get("context_count", 0)

        else:
            # General query — direct Gemini with history
            if self.retriever:
                context_docs = self.retriever.retrieve(message, k=3)
            context_text = "\n\n".join(d["content"] for d in context_docs) if context_docs else ""
            prompt = (
                f"{self._general_prompt}\n\n"
                + (f"Relevant context:\n{context_text}\n\n" if context_text else "")
                + (f"Conversation history:\n{history_text}\n\n" if history_text else "")
                + f"Operator: {message}\nAssistant:"
            )
            answer = self._call_llm(prompt)
            sources = [d["source"] for d in context_docs]
            suggested = ["Ask about an asset", "Look up a procedure", "View active alerts"]
            context_count = len(context_docs)

        response = {
            "response":          answer,
            "sources":           list(set(sources)),
            "intent":            intent,
            "suggested_actions": suggested,
            "context_count":     context_count,
            "cached":            False,
        }
        if not self._is_fallback_response(answer):
            _RESPONSE_CACHE[key] = response
        return response

    def _hydrate_alert_context(self, asset_context: dict) -> tuple[dict, dict]:
        alert_id = asset_context.get("alert_id")
        alert = None
        lime = asset_context.get("lime_explanation")

        if alert_id:
            try:
                from backend.services.demo_data import get_alert, get_explanation
                alert = get_alert(str(alert_id))
                lime = lime or get_explanation(str(alert_id))
            except Exception:
                alert = None

        if alert is None:
            asset_id = str(asset_context.get("asset_id", "unknown"))
            try:
                from backend.services.demo_data import get_latest_alert_for_asset, get_explanation
                alert = get_latest_alert_for_asset(asset_id)
                if alert and not lime:
                    lime = get_explanation(alert["alert_id"])
            except Exception:
                alert = None

        if alert is None:
            alert = {
                "alert_id": asset_context.get("alert_id", "ad-hoc"),
                "asset_id": asset_context.get("asset_id", "unknown"),
                "risk_score": asset_context.get("risk_score", 0),
                "risk_tier": asset_context.get("risk_tier", "UNKNOWN"),
                "threat_type": asset_context.get("threat_type", "unknown"),
                "description": asset_context.get("description", ""),
            }

        return alert, lime or {"contributions": []}

    def _call_llm(self, prompt: str) -> str:
        """Call LLMRouter (Gemma 4 → Gemini) with retry."""
        for attempt in range(3):
            try:
                self.last_generation_error = None
                return self.llm.generate(prompt, task_type="critical_reasoning")
            except Exception as e:
                self.last_generation_error = str(e)
                if "429" in str(e) or "rate" in str(e).lower():
                    time.sleep(2 ** attempt)
                else:
                    break
        return self._fallback_response(prompt)

    # Backwards-compat alias
    def _call_gemini(self, prompt: str) -> str:
        return self._call_llm(prompt)

    def _fallback_response(self, prompt: str) -> str:
        reason = "LLM generation (Gemma 4 + Gemini) is temporarily unavailable"
        if self.last_generation_error and self._is_invalid_api_key_error(self.last_generation_error):
            reason = "LLM generation is unavailable due to an invalid or missing API key"
        return (
            f"{reason}. I am using local RAG fallback mode with the available knowledge index. "
            "Use the retrieved sources for SOP review, compare top contributors against recent "
            "telemetry, and escalate CRITICAL assets before automated containment."
        )

    def _is_invalid_api_key_error(self, error: str) -> bool:
        low = error.lower()
        return (
            "api_key_invalid" in low
            or "api key not found" in low
            or "invalid api key" in low
            or "unauthorized" in low
        )

    def _is_fallback_response(self, answer: str) -> bool:
        return answer.startswith("LLM generation")

    def _suggest_actions(self, asset_context: dict) -> list[str]:
        tier = asset_context.get("risk_tier", "")
        asset = asset_context.get("asset_id", "this asset")
        if tier == "CRITICAL":
            return [
                f"Isolate {asset} from network immediately",
                "Dispatch maintenance team for physical inspection",
                "Review full 24-hour telemetry history",
            ]
        elif tier == "URGENT":
            return [
                f"Increase monitoring frequency for {asset}",
                "Check for concurrent cyber events",
                "Review LIME explanation for root cause",
            ]
        return [
            f"Monitor {asset} for next 30 minutes",
            "View asset detail page",
            "Check LIME explanation",
        ]
