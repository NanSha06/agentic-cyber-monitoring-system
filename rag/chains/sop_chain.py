"""
SOP lookup chain for V2 copilot procedure questions.
"""
from __future__ import annotations

import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


class SOPChain:
    def __init__(self):
        from rag.chains.prompts import build_sop_prompt
        from rag.chains.gemini_utils import configure_gemini, get_gemini_api_key, GEMINI_TIMEOUT_SECONDS
        from rag.retrieval.retriever import KnowledgeRetriever, retriever_available

        self.model = None
        self.last_generation_error: str | None = None
        self.gemini_configured = bool(get_gemini_api_key())
        self.gemini_timeout_seconds = GEMINI_TIMEOUT_SECONDS
        if self.gemini_configured:
            self.model = configure_gemini()

        self._build_sop_prompt = build_sop_prompt
        self.retriever = None
        if retriever_available():
            try:
                self.retriever = KnowledgeRetriever.get_instance()
            except Exception:
                self.retriever = None

    def run(self, query: str, history_text: str = "") -> dict:
        context_docs = self.retriever.retrieve(query, k=4) if self.retriever else []
        prompt = self._build_sop_prompt(query, context_docs)
        if history_text:
            prompt = f"Conversation so far:\n{history_text}\n\n{prompt}"

        return {
            "answer": self._call_gemini(prompt, query, context_docs),
            "sources": [d["source"] for d in context_docs],
            "suggested_actions": [
                "View SOP documentation",
                "Open incident playbook",
                "Escalate to tier-2",
            ],
            "context_count": len(context_docs),
        }

    def _call_gemini(self, prompt: str, query: str, context_docs: list[dict]) -> str:
        if self.model is None:
            return self._fallback(query, context_docs)

        for attempt in range(3):
            try:
                self.last_generation_error = None
                return self.model.generate_content(
                    prompt,
                    request_options={"timeout": self.gemini_timeout_seconds},
                ).text
            except Exception as e:
                self.last_generation_error = str(e)
                if "429" in str(e) or "quota" in str(e).lower():
                    time.sleep(2 ** attempt)
                else:
                    break
        return self._fallback(query, context_docs)

    def _fallback(self, query: str, context_docs: list[dict]) -> str:
        source_names = sorted({d.get("source", "unknown") for d in context_docs})
        sources = ", ".join(f"[{s}]" for s in source_names) if source_names else "no retrieved SOP source"
        snippets = " ".join(d.get("content", "")[:220] for d in context_docs[:2]).strip()
        if not snippets:
            snippets = "No matching SOP text was available in the local FAISS index."

        reason = "Gemini generation is not configured"
        if self.gemini_configured:
            reason = "Gemini generation is temporarily unavailable"
            if self.last_generation_error and self._is_invalid_api_key_error(self.last_generation_error):
                reason = "Gemini generation is unavailable because the configured API key was rejected"

        return (
            f"{reason}. Local SOP fallback for '{query}': use {sources}. "
            f"Relevant local context: {snippets} Review the playbook, confirm the asset state, "
            "and escalate before executing containment steps that affect live systems."
        )

    def _is_invalid_api_key_error(self, error: str) -> bool:
        low = error.lower()
        return "api_key_invalid" in low or "api key not found" in low or "invalid api key" in low
