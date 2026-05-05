"""
V3 Reporting Agent: finalizes the agent run summary.
"""
from __future__ import annotations

from agents.base import AgentInput, AgentOutput, BaseAgent, utc_now


class ReportingAgent(BaseAgent):
    name = "reporting"

    async def run(self, input: AgentInput) -> AgentOutput:  # noqa: A002
        return AgentOutput(
            event_id=input.event_id,
            agent_name=self.name,
            status="success",
            result={
                "completed_at": utc_now(),
                "agent_hops": [entry.agent_name for entry in input.trace],
                "audit_status": "ready_for_governance_mcp",
            },
            next_agent=None,
        )
