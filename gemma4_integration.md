# 🚀 Gemma 4 Integration — Required Changes Only

## 📌 Goal
Replace Gemini with **Gemma 4 (primary)** while keeping Gemini as fallback using an LLM abstraction layer.

---

# 1️⃣ CREATE NEW MODULE

## 📁 Create Folder
backend/llm/


---

## 📄 File: `backend/llm/gemma_client.py`

```python
import requests
import os

class GemmaClient:
    def __init__(self):
        self.api_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.api_key = os.getenv("NVIDIA_API_KEY")

    def generate(self, prompt: str) -> str:
        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemma-4-31b-it",
                "messages": [
                    {"role": "system", "content": "You are a cyber-physical systems expert."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
        )

        return response.json()["choices"][0]["message"]["content"]

📄 File: backend/llm/gemini_client.py
import google.generativeai as genai
import os

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def generate(self, prompt: str) -> str:
        return self.model.generate_content(prompt).text

📄 File: backend/llm/router.py
from .gemma_client import GemmaClient
from .gemini_client import GeminiClient

class LLMRouter:
    def __init__(self):
        self.gemma = GemmaClient()
        self.gemini = GeminiClient()

    def generate(self, prompt: str, task_type="critical_reasoning"):
        try:
            return self.gemma.generate(prompt)
        except Exception:
            return self.gemini.generate(prompt)


2️⃣ MODIFY RAG CHAIN
📄 File: rag/chains/alert_chain.py
import google.generativeai as genai
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
self.model = genai.GenerativeModel("gemini-1.5-flash")


✅ ADD:
from backend.llm.router import LLMRouter
self.llm = LLMRouter()

REPLACE:
response = self.model.generate_content(prompt)
✅ WITH:
response = self.llm.generate(prompt, task_type="critical_reasoning")
3️⃣ MODIFY RECOMMENDATION AGENT
📄 File: agents/recommendation_agent.py
🔴 REMOVE:
RESPONSE_TEMPLATES = {...}
✅ ADD:
from backend.llm.router import LLMRouter

class RecommendationAgent(BaseAgent):
    name = "recommendation"

    def __init__(self):
        self.llm = LLMRouter()

    async def run(self, input):
        prompt = f"""
        Alert: {input.payload}

        Suggest top 3 mitigation steps.
        Prioritize safety and compliance.
        """

        actions = self.llm.generate(prompt)

        return AgentOutput(
            event_id=input.event_id,
            agent_name=self.name,
            status="success",
            result={"proposed_actions": actions},
            next_agent="compliance",
        )
4️⃣ MODIFY COPILOT ENDPOINT
📄 File: backend/routers/copilot.py
🔴 REMOVE Gemini usage
✅ ADD:
from backend.llm.router import LLMRouter

llm = LLMRouter()

response = llm.generate(prompt)
5️⃣ ENVIRONMENT VARIABLES
📄 File: .env
NVIDIA_API_KEY=your_nvidia_key
GEMINI_API_KEY=your_gemini_key
✅ FINAL RESULT
Gemma = Primary LLM
Gemini = Fallback
RAG, Copilot, Agents all use LLMRouter
No direct dependency on Gemini
⚠️ DO NOT CHANGE
Models (ML/DL)
Preprocessing pipeline
MCP servers
FastAPI structure