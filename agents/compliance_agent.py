"""
V3 Compliance Agent: gates destructive or high-impact remediation actions.
"""
from __future__ import annotations

from agents.base import AgentInput, AgentOutput, BaseAgent
from mcp_servers.governance_mcp.server import policy_check


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

        policy_results = []
        for action in actions:
            try:
                policy_results.append(policy_check(action, input.event_id))
            except Exception:
                policy_results.append(
                    {
                        "action": action,
                        "requires_human_approval": any(
                            keyword in action.lower() for keyword in DESTRUCTIVE_KEYWORDS
                        ),
                    }
                )
        requires_approval = any(result.get("requires_human_approval") for result in policy_results)
        decision = "requires_human_approval" if requires_approval else "approved"

        return AgentOutput(
            event_id=input.event_id,
            agent_name=self.name,
            status="blocked" if requires_approval else "success",
            result={
                "decision": decision,
                "gated_actions": actions if requires_approval else [],
                "policy_results": policy_results,
                "policy": "destructive_actions_require_hitl",
            },
            next_agent="reporting",
            requires_human_approval=requires_approval,
        )
