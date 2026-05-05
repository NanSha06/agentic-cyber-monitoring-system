"""
V3 Recommendation Agent.
"""
from __future__ import annotations

import os

from agents.base import AgentInput, AgentOutput, BaseAgent


class RecommendationAgent(BaseAgent):
    """
    Generates LLM-grounded mitigation recommendations for a given alert.

    Primary LLM: Gemma 4 (via NVIDIA NIM)
    Fallback LLM: Gemini 1.5 Flash
    """

    name = "recommendation"

    def __init__(self, *, use_llm: bool | None = None):
        self.use_llm = (
            os.getenv("V3_ENABLE_LLM_RECOMMENDATIONS", "0") == "1"
            if use_llm is None
            else use_llm
        )
        self.llm = None
        if self.use_llm:
            from backend.llm.router import LLMRouter
            self.llm = LLMRouter()

    async def run(self, input: AgentInput) -> AgentOutput:  # noqa: A002
        alert = input.payload.get("alert", input.payload)
        diagnosis = input.payload.get("diagnosis", {})
        asset_id = alert.get("asset_id", "unknown")
        risk_score = alert.get("risk_score", "N/A")
        threat = alert.get("threat_type", "unknown")
        tier = alert.get("risk_tier", "UNKNOWN")

        prompt = f"""
You are a cyber-physical security expert for industrial battery management systems.

Alert Details:
- Asset ID:    {asset_id}
- Risk Score:  {risk_score}/100
- Risk Tier:   {tier}
- Threat Type: {threat}
- Diagnosis:   {diagnosis}
- Payload:     {alert}

Suggest the top 3 concrete mitigation steps for this alert.
Prioritize operator safety and regulatory compliance.
Format as a numbered list with a single sentence per step.
"""

        if self.llm is not None:
            try:
                actions = self.llm.generate(prompt, task_type="critical_reasoning")
                status = "success"
            except Exception as e:
                actions = self._fallback_actions(asset_id, threat, f"LLM unavailable: {e}")
                status = "fallback"
        else:
            actions = self._fallback_actions(asset_id, threat, "LLM recommendations disabled")
            status = "fallback"

        return AgentOutput(
            event_id=input.event_id,
            agent_name=self.name,
            status=status,
            result={"proposed_actions": actions, "prompt_context": prompt.strip()},
            next_agent="compliance",
        )

    def _fallback_actions(self, asset_id: str, threat: str, reason: str) -> list[str]:
        if threat in {"dos", "ddos", "bruteforce"}:
            return [
                f"Rate-limit and inspect suspicious traffic targeting {asset_id}.",
                f"Isolate {asset_id} from nonessential network paths pending operator approval.",
                "Notify the security engineer and preserve telemetry for incident review.",
            ]
        return [
            f"Increase monitoring frequency for {asset_id}.",
            "Compare recent battery telemetry against the normal operating envelope.",
            f"Document the event context for follow-up review ({reason}).",
        ]
