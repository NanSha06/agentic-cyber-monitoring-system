"""
rag/chains/conversational_chain.py
Multi-turn conversational chain for the AI Copilot.
Handles intent classification and routes to the correct chain.
"""
from __future__ import annotations
import os
import time

# Intent types
INTENT_ALERT_QUERY  = "alert_query"
INTENT_SOP_LOOKUP   = "sop_lookup"
INTENT_GENERAL      = "general"

# Keywords that signal each intent
ALERT_KEYWORDS = ["risky","risk","alert","score","anomaly","threat","why","danger","critical","urgent"]
SOP_KEYWORDS   = ["sop","procedure","protocol","steps","how to","what should","playbook","response","mitigation"]

# Max history turns to include in prompt
MAX_HISTORY_TURNS = 5


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
        from rag.chains.prompts import build_sop_prompt, GENERAL_QUERY_PROMPT

        api_key = os.environ.get("GEMINI_API_KEY", "")
        self.model = None
        self.gemini_configured = bool(api_key)
        self.last_generation_error: str | None = None
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        self._build_sop_prompt = build_sop_prompt
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
            alert = {
                "asset_id":   asset_context.get("asset_id", "unknown"),
                "risk_score": asset_context.get("risk_score", 0),
                "risk_tier":  asset_context.get("risk_tier", "UNKNOWN"),
                "threat_type": asset_context.get("threat_type", "unknown"),
            }
            lime = asset_context.get("lime_explanation", {"contributions": []})
            result = chain.run(alert, lime)
            answer = result["answer"]
            sources = result["sources"]
            suggested = self._suggest_actions(asset_context)

        elif intent == INTENT_SOP_LOOKUP:
            # Retrieve SOP documents and answer
            if self.retriever:
                context_docs = self.retriever.retrieve(message, k=4)
            prompt = self._build_sop_prompt(message, context_docs)
            if history_text:
                prompt = f"Conversation so far:\n{history_text}\n\n{prompt}"
            answer = self._call_gemini(prompt)
            sources = [d["source"] for d in context_docs]
            suggested = ["View SOP documentation", "Open incident playbook", "Escalate to tier-2"]

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
            answer = self._call_gemini(prompt)
            sources = [d["source"] for d in context_docs]
            suggested = ["Ask about an asset", "Look up a procedure", "View active alerts"]

        return {
            "response":          answer,
            "sources":           list(set(sources)),
            "intent":            intent,
            "suggested_actions": suggested,
            "context_count":     len(context_docs),
        }

    def _call_gemini(self, prompt: str) -> str:
        if self.model is None:
            return self._fallback_response(prompt)

        for attempt in range(3):
            try:
                self.last_generation_error = None
                return self.model.generate_content(prompt).text
            except Exception as e:
                self.last_generation_error = str(e)
                if "429" in str(e):
                    time.sleep(2 ** attempt)
                else:
                    break
        return self._fallback_response(prompt)

    def _fallback_response(self, prompt: str) -> str:
        if self.gemini_configured:
            reason = "Gemini generation is temporarily unavailable"
            if self.last_generation_error and self._is_invalid_api_key_error(self.last_generation_error):
                reason = "Gemini generation is unavailable because the configured API key was rejected"
            return (
                f"{reason}. I am using local RAG fallback mode with the available knowledge index. "
                "Use the retrieved sources for SOP review, compare top contributors against recent "
                "telemetry, and escalate CRITICAL assets before automated containment."
            )

        return (
            "Gemini generation is not configured, so I am using local RAG fallback mode with the "
            "available knowledge index. Use the retrieved sources for SOP review, compare top "
            "contributors against recent telemetry, and escalate CRITICAL assets before automated containment."
        )

    def _is_invalid_api_key_error(self, error: str) -> bool:
        low = error.lower()
        return "api_key_invalid" in low or "api key not found" in low or "invalid api key" in low

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
