"""
backend/llm/router.py
LLMRouter — tries Gemma 4 (primary) first; falls back to Gemini automatically.
All RAG chains, agents, and copilot endpoints should use this class exclusively.
"""
from __future__ import annotations


class LLMRouter:
    """
    Unified LLM interface.
      - Primary:  Gemma 4 via NVIDIA NIM API (google/gemma-4-31b-it)
      - Fallback: Gemini 1.5 Flash via Google Generative AI SDK

    Usage::

        llm = LLMRouter()
        text = llm.generate("Explain thermal runaway in a BMS context.")
    """

    def __init__(self):
        from backend.llm.gemma_client import GemmaClient
        from backend.llm.gemini_client import GeminiClient

        self._gemma: GemmaClient | None = None
        self._gemini: GeminiClient | None = None

        try:
            self._gemma = GemmaClient()
        except Exception as e:
            print(f"⚠️  LLMRouter: Gemma client unavailable — {e}")

        try:
            self._gemini = GeminiClient()
        except Exception as e:
            print(f"⚠️  LLMRouter: Gemini client unavailable — {e}")

    # task_type is accepted for API compatibility but routing is currently
    # based solely on availability (Gemma → Gemini).
    def generate(self, prompt: str, task_type: str = "critical_reasoning") -> str:
        if self._gemma is not None:
            try:
                return self._gemma.generate(prompt)
            except Exception as e:
                print(f"⚠️  LLMRouter: Gemma generation failed ({e}), falling back to Gemini")

        if self._gemini is not None:
            try:
                return self._gemini.generate(prompt)
            except Exception as e:
                print(f"⚠️  LLMRouter: Gemini fallback also failed ({e})")

        raise RuntimeError(
            "LLMRouter: Both Gemma and Gemini are unavailable. "
            "Set NVIDIA_API_KEY (primary) or GEMINI_API_KEY (fallback) in .env"
        )
