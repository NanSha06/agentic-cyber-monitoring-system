"""
V3 Diagnosis Agent: attaches root-cause context to an alert.
"""
from __future__ import annotations

from agents.base import AgentInput, AgentOutput, BaseAgent
from backend.services.demo_data import get_explanation


class DiagnosisAgent(BaseAgent):
    name = "diagnosis"

    async def run(self, input: AgentInput) -> AgentOutput:  # noqa: A002
        alert = input.payload.get("alert", input.payload)
        alert_id = input.alert_id or alert.get("alert_id")
        explanation = get_explanation(alert_id) if alert_id else None
        contributions = explanation.get("contributions", []) if explanation else []
        top_factors = sorted(
            contributions,
            key=lambda item: abs(float(item.get("weight", 0))),
            reverse=True,
        )[:3]

        return AgentOutput(
            event_id=input.event_id,
            agent_name=self.name,
            status="success" if explanation else "fallback",
            result={
                "root_cause": "Cross-domain cyber and battery telemetry anomaly",
                "top_factors": top_factors,
                "explanation_available": explanation is not None,
            },
            next_agent="recommendation",
        )
