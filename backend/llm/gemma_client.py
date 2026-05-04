"""
backend/llm/gemma_client.py
Gemma 4 client via NVIDIA NIM API — primary LLM for the platform.

Uses Server-Sent Events (SSE) streaming with enable_thinking=True,
exactly matching the official NVIDIA NIM integration pattern.
"""
import json
import os
import requests


SYSTEM_PROMPT = (
    "You are a cyber-physical systems expert specialising in "
    "lithium-ion battery security and industrial IoT threat analysis. "
    "Provide concise, accurate, and actionable responses."
)

INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


class GemmaClient:
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise RuntimeError("NVIDIA_API_KEY is not set — cannot use Gemma 4")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(self, prompt: str, *, stream: bool = True) -> str:
        """
        Send a prompt to Gemma 4 (google/gemma-4-31b-it) via NVIDIA NIM and
        return the full response text.

        Args:
            prompt:  User message / RAG prompt to send.
            stream:  Whether to use SSE streaming (default True, recommended
                     for long responses to avoid gateway timeouts).

        Returns:
            The model's response text (thinking tokens are stripped; only the
            final answer is returned).
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream" if stream else "application/json",
        }

        payload = {
            "model": "google/gemma-4-31b-it",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            "max_tokens": 16384,
            "temperature": 1.00,
            "top_p": 0.95,
            "stream": stream,
            "chat_template_kwargs": {"enable_thinking": True},
        }

        response = requests.post(
            INVOKE_URL,
            headers=headers,
            json=payload,
            stream=stream,
            timeout=120,          # generous timeout for long generations
        )
        response.raise_for_status()

        if stream:
            return self._collect_stream(response)
        else:
            data = response.json()
            return data["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_stream(self, response: requests.Response) -> str:
        """
        Consume an SSE stream from NVIDIA NIM and return the assembled
        response text.

        Each SSE line looks like:
            data: {"choices":[{"delta":{"content":"...","reasoning_content":"..."}}]}
        or:
            data: [DONE]

        Gemma 4's thinking tokens arrive in `reasoning_content`; the actual
        answer arrives in `content`.  We only surface the answer to callers.
        """
        answer_parts: list[str] = []

        for raw_line in response.iter_lines():
            if not raw_line:
                continue

            line: str = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line

            # Strip the "data: " prefix
            if not line.startswith("data:"):
                continue
            payload_str = line[len("data:"):].strip()

            # Terminal sentinel
            if payload_str == "[DONE]":
                break

            try:
                chunk = json.loads(payload_str)
            except json.JSONDecodeError:
                continue

            for choice in chunk.get("choices", []):
                delta = choice.get("delta", {})
                # Accumulate only the visible answer, not the thinking trace
                content = delta.get("content") or ""
                if content:
                    answer_parts.append(content)

        return "".join(answer_parts).strip()
