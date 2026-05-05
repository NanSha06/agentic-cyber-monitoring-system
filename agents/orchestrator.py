"""
V3 event-driven agent orchestrator.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.base import AgentInput, AgentOutput, BaseAgent, append_trace, utc_now
from agents.bus import InMemoryEventBus, RedisEventBus, create_event_bus
from agents.compliance_agent import ComplianceAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.monitoring_agent import MonitoringAgent
from agents.recommendation_agent import RecommendationAgent
from agents.reporting_agent import ReportingAgent
from backend.services.demo_data import get_alert


class AgentRunRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    start_agent: str = "monitoring"


class AgentRunResponse(BaseModel):
    event_id: str
    alert_id: str | None
    status: str
    outputs: list[AgentOutput]
    requires_human_approval: bool
    trace: list[dict[str, Any]]
    bus_backend: str


class AgentOrchestrator:
    def __init__(self, bus: RedisEventBus | InMemoryEventBus | None = None) -> None:
        self.bus = bus
        self.agents: dict[str, BaseAgent] = {
            "monitoring": MonitoringAgent(),
            "diagnosis": DiagnosisAgent(),
            "recommendation": RecommendationAgent(),
            "compliance": ComplianceAgent(),
            "reporting": ReportingAgent(),
        }

    async def _bus(self) -> RedisEventBus | InMemoryEventBus:
        if self.bus is None:
            self.bus = await create_event_bus()
        return self.bus

    async def run_sequence(self, input: AgentInput, start_agent: str = "monitoring") -> AgentRunResponse:  # noqa: A002
        bus = await self._bus()
        current_agent = start_agent
        current_input = input
        outputs: list[AgentOutput] = []
        requires_human_approval = False

        for _ in range(len(self.agents) + 2):
            agent = self.agents.get(current_agent)
            if agent is None:
                raise ValueError(f"Unknown agent: {current_agent}")

            await bus.publish_input(agent.name, current_input)
            started_at = utc_now()
            try:
                output = await agent.run(current_input)
            except Exception as exc:
                output = AgentOutput(
                    event_id=current_input.event_id,
                    agent_name=agent.name,
                    status="failed",
                    errors=[str(exc)],
                    next_agent=None,
                )
                await bus.publish_dead_letter(
                    {
                        "event_id": current_input.event_id,
                        "agent_name": agent.name,
                        "error": str(exc),
                        "payload": current_input.payload,
                    }
                )

            finished_at = utc_now()
            outputs.append(output)
            await bus.publish_output(output)
            requires_human_approval = requires_human_approval or output.requires_human_approval
            current_input = append_trace(
                current_input,
                output,
                started_at=started_at,
                finished_at=finished_at,
                summary=self._summarize_output(output),
            )

            if output.next_agent is None or output.status == "failed":
                break
            current_agent = output.next_agent
        else:
            await bus.publish_dead_letter(
                {
                    "event_id": current_input.event_id,
                    "error": "Agent sequence exceeded max hops",
                    "payload": current_input.payload,
                }
            )
            raise RuntimeError("Agent sequence exceeded max hops")

        terminal = outputs[-1].status if outputs else "skipped"
        return AgentRunResponse(
            event_id=current_input.event_id,
            alert_id=current_input.alert_id,
            status=terminal,
            outputs=outputs,
            requires_human_approval=requires_human_approval,
            trace=[entry.model_dump(mode="json") for entry in current_input.trace],
            bus_backend=type(bus).__name__,
        )

    def _summarize_output(self, output: AgentOutput) -> str:
        if output.errors:
            return "; ".join(output.errors)
        if "decision" in output.result:
            return str(output.result["decision"])
        if "triage" in output.result:
            return str(output.result["triage"])
        if "audit_status" in output.result:
            return str(output.result["audit_status"])
        return output.status


router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/status")
async def agent_status():
    bus = await create_event_bus()
    try:
        return {
            "status": "ready",
            "bus_backend": type(bus).__name__,
            "agents": ["monitoring", "diagnosis", "recommendation", "compliance", "reporting"],
        }
    finally:
        await bus.close()


@router.post("/run-alert/{alert_id}", response_model=AgentRunResponse)
async def run_alert_pipeline(alert_id: str, request: AgentRunRequest | None = None):
    alert = get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    request = request or AgentRunRequest()
    payload = {"alert": alert, **request.payload}
    orchestrator = AgentOrchestrator()
    try:
        return await orchestrator.run_sequence(
            AgentInput(alert_id=alert_id, payload=payload),
            start_agent=request.start_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
