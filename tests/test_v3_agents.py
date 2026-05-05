from __future__ import annotations

import asyncio
from fastapi.testclient import TestClient

from agents.base import AgentInput
from agents.bus import InMemoryEventBus
from agents.orchestrator import AgentOrchestrator
from backend.main import app
from backend.services.demo_data import ALERT_STORE


def test_v3_orchestrator_runs_full_agent_sequence_without_redis():
    alert = next(alert for alert in ALERT_STORE if alert["risk_tier"] == "CRITICAL")
    bus = InMemoryEventBus()
    orchestrator = AgentOrchestrator(bus=bus)

    response = asyncio.run(
        orchestrator.run_sequence(
            AgentInput(alert_id=alert["alert_id"], payload={"alert": alert})
        )
    )

    assert response.status == "success"
    assert response.bus_backend == "InMemoryEventBus"
    assert [output.agent_name for output in response.outputs] == [
        "monitoring",
        "diagnosis",
        "recommendation",
        "compliance",
        "reporting",
    ]
    assert response.requires_human_approval is True
    assert "agents.output" in bus.messages


def test_v3_agents_status_endpoint_is_mounted():
    client = TestClient(app)

    response = client.get("/agents/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["agents"] == ["monitoring", "diagnosis", "recommendation", "compliance", "reporting"]


def test_v3_run_alert_endpoint_rejects_unknown_alert():
    client = TestClient(app)

    response = client.post("/agents/run-alert/missing-alert")

    assert response.status_code == 404
