"""
Shared contracts for the V3 autonomous agent layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


AgentStatus = Literal["success", "fallback", "blocked", "failed", "skipped"]


class AgentTraceEntry(BaseModel):
    agent_name: str
    status: AgentStatus
    started_at: str
    finished_at: str
    summary: str


class AgentInput(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    alert_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    trace: list[AgentTraceEntry] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    event_id: str
    agent_name: str
    status: AgentStatus
    result: dict[str, Any] = Field(default_factory=dict)
    next_agent: str | None = None
    errors: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False


class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def run(self, input: AgentInput) -> AgentOutput:  # noqa: A002
        """Execute the agent against an event payload."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_trace(
    input: AgentInput,  # noqa: A002
    output: AgentOutput,
    *,
    started_at: str,
    finished_at: str,
    summary: str,
) -> AgentInput:
    trace = list(input.trace)
    trace.append(
        AgentTraceEntry(
            agent_name=output.agent_name,
            status=output.status,
            started_at=started_at,
            finished_at=finished_at,
            summary=summary,
        )
    )
    payload = dict(input.payload)
    payload[output.agent_name] = output.result
    return input.model_copy(update={"payload": payload, "trace": trace})
