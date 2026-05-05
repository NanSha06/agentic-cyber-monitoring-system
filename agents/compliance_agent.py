"""
V3 Compliance Agent: gates destructive or high-impact remediation actions.
"""
from __future__ import annotations

from agents.base import AgentInput, AgentOutput, BaseAgent


DESTRUCTIVE_KEYWORDS = {
    "quarantine",
    "shutdown",
    "disconnect",
    "isolate",
    "disable",
    "revoke",
    "rotate",
}


class ComplianceAgent(BaseAgent):
    name = "compliance"

    async def run(self, input: AgentInput) -> AgentOutput:  # noqa: A002
        recommendation = input.payload.get("recommendation", {})
        proposed = recommendation.get("proposed_actions", [])
        if isinstance(proposed, str):
            action_text = proposed.lower()
            actions = [proposed]
        else:
            actions = [str(action) for action in proposed]
            action_text = " ".join(actions).lower()

        requires_approval = any(keyword in action_text for keyword in DESTRUCTIVE_KEYWORDS)
        decision = "requires_human_approval" if requires_approval else "approved"

        return AgentOutput(
            event_id=input.event_id,
            agent_name=self.name,
            status="blocked" if requires_approval else "success",
            result={
                "decision": decision,
                "gated_actions": actions if requires_approval else [],
                "policy": "destructive_actions_require_hitl",
            },
            next_agent="reporting",
            requires_human_approval=requires_approval,
        )
