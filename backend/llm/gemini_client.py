"""
backend/llm/gemini_client.py
Gemini 1.5 Flash client — fallback LLM when Gemma 4 is unavailable.
"""
import os
import google.generativeai as genai


class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set — cannot use Gemini fallback")
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str) -> str:
        return self.model.generate_content(prompt).text
