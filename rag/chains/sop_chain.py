"""
rag/chains/sop_chain.py
SOP lookup chain for V2 copilot procedure questions.
Uses LLMRouter (Gemma 4 → Gemini fallback) — consistent with ConversationalChain.
"""
from __future__ import annotations

import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


class SOPChain:
    def __init__(self):
        from rag.chains.prompts import build_sop_prompt
        from rag.retrieval.retriever import KnowledgeRetriever, retriever_available
        from backend.llm.router import LLMRouter

        self.llm = LLMRouter()
        self.last_generation_error: str | None = None
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
            "answer": self._call_llm(prompt, query, context_docs),
            "sources": [d["source"] for d in context_docs],
            "suggested_actions": [
                "View SOP documentation",
                "Open incident playbook",
                "Escalate to tier-2",
            ],
            "context_count": len(context_docs),
        }

    def _call_llm(self, prompt: str, query: str, context_docs: list[dict]) -> str:
        for attempt in range(3):
            try:
                self.last_generation_error = None
                return self.llm.generate(prompt, task_type="sop_lookup")
            except Exception as e:
                self.last_generation_error = str(e)
                if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                    time.sleep(2 ** attempt)
                else:
                    break
        return self._fallback(query, context_docs)

    def _fallback(self, query: str, context_docs: list[dict]) -> str:
        source_names = sorted({d.get("source", "unknown") for d in context_docs})
        sources = ", ".join(f"[{s}]" for s in source_names) if source_names else "no retrieved SOP source"
        snippets = " ".join(d.get("content", "")[:220] for d in context_docs[:2]).strip()

        if snippets:
            return (
                f"LLM generation is temporarily unavailable. "
                f"Local SOP fallback for '{query}': use {sources}.\n\n"
                f"Relevant local context: {snippets}\n\n"
                "Review the playbook, confirm the asset state, and escalate before "
                "executing containment steps that affect live systems."
            )

        return (
            f"The SOP for '{query}' was not found in the retrieved documents. "
            "The FAISS knowledge index may need to be rebuilt. "
            "Please run: python rag/ingestion/build_index.py\n\n"
            "In the meantime, escalate to a senior analyst or incident response lead."
        )
