"""
backend/llm/gemma_client.py
Gemma 4 client via NVIDIA NIM API — primary LLM for the platform.
"""
import requests
import os


class GemmaClient:
    def __init__(self):
        self.api_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.api_key = os.getenv("NVIDIA_API_KEY")

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("NVIDIA_API_KEY is not set — cannot use Gemma 4")

        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemma-4-31b-it",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a cyber-physical systems expert specialising in "
                            "lithium-ion battery security and industrial IoT threat analysis. "
                            "Provide concise, accurate, and actionable responses."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 1024,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
