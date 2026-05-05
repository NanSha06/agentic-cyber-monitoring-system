"""
V3 Reporting Agent: finalizes the agent run summary.
"""
from __future__ import annotations

from agents.base import AgentInput, AgentOutput, BaseAgent, utc_now
from mcp_servers.governance_mcp.server import write_audit_log


class ReportingAgent(BaseAgent):
    name = "reporting"

    async def run(self, input: AgentInput) -> AgentOutput:  # noqa: A002
        audit_entry = write_audit_log(
            record_type="agent_run_summary",
            event_id=input.event_id,
            agent_name=self.name,
            payload={
                "alert_id": input.alert_id,
                "agent_hops": [entry.agent_name for entry in input.trace],
                "requires_human_approval": any(
                    entry.agent_name == "compliance" and entry.status == "blocked"
                    for entry in input.trace
                ),
            },
        )
        return AgentOutput(
            event_id=input.event_id,
            agent_name=self.name,
            status="success",
            result={
                "completed_at": utc_now(),
                "agent_hops": [entry.agent_name for entry in input.trace],
                "audit_status": "persisted",
                "audit_id": audit_entry["audit_id"],
            },
            next_agent=None,
        )
