"""
V3 Monitoring Agent: performs initial alert triage.
"""
from __future__ import annotations

from agents.base import AgentInput, AgentOutput, BaseAgent


class MonitoringAgent(BaseAgent):
    name = "monitoring"

    async def run(self, input: AgentInput) -> AgentOutput:  # noqa: A002
        alert = input.payload.get("alert", input.payload)
        risk_score = float(alert.get("risk_score", 0))
        risk_tier = str(alert.get("risk_tier", "UNKNOWN")).upper()
        should_escalate = risk_tier in {"URGENT", "CRITICAL"} or risk_score >= 60

        return AgentOutput(
            event_id=input.event_id,
            agent_name=self.name,
            status="success" if should_escalate else "skipped",
            result={
                "risk_score": risk_score,
                "risk_tier": risk_tier,
                "triage": "escalate" if should_escalate else "monitor",
            },
            next_agent="diagnosis" if should_escalate else None,
        )
