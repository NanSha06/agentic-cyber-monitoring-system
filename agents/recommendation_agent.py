"""
agents/recommendation_agent.py
LLM-powered recommendation agent — replaces static RESPONSE_TEMPLATES with
live Gemma 4 / Gemini-grounded mitigation guidance.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


# ── Lightweight agent I/O types (no external dep needed here) ─────────────────
@dataclass
class AgentInput:
    event_id: str
    payload: Any  # alert dict or free-form dict


@dataclass
class AgentOutput:
    event_id: str
    agent_name: str
    status: str
    result: dict
    next_agent: str | None = None
    errors: list[str] = field(default_factory=list)


# ── RecommendationAgent ───────────────────────────────────────────────────────
class RecommendationAgent:
    """
    Generates LLM-grounded mitigation recommendations for a given alert.

    Primary LLM: Gemma 4 (via NVIDIA NIM)
    Fallback LLM: Gemini 1.5 Flash
    """

    name = "recommendation"

    def __init__(self):
        from backend.llm.router import LLMRouter
        self.llm = LLMRouter()

    async def run(self, input: AgentInput) -> AgentOutput:  # noqa: A002
        payload = input.payload or {}
        asset_id   = payload.get("asset_id", "unknown")
        risk_score = payload.get("risk_score", "N/A")
        threat     = payload.get("threat_type", "unknown")
        tier       = payload.get("risk_tier", "UNKNOWN")

        prompt = f"""
You are a cyber-physical security expert for industrial battery management systems.

Alert Details:
- Asset ID:    {asset_id}
- Risk Score:  {risk_score}/100
- Risk Tier:   {tier}
- Threat Type: {threat}
- Payload:     {payload}

Suggest the top 3 concrete mitigation steps for this alert.
Prioritize operator safety and regulatory compliance.
Format as a numbered list with a single sentence per step.
"""

        try:
            actions = self.llm.generate(prompt, task_type="critical_reasoning")
            status = "success"
        except Exception as e:
            actions = (
                f"LLM unavailable ({e}). Manual fallback: "
                "1. Isolate the asset from the network. "
                "2. Notify the on-call security engineer. "
                "3. Follow the standard battery SOP in the runbook."
            )
            status = "fallback"

        return AgentOutput(
            event_id=input.event_id,
            agent_name=self.name,
            status=status,
            result={"proposed_actions": actions},
            next_agent="compliance",
        )
