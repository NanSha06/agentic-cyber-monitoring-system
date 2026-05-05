from __future__ import annotations

import asyncio
from fastapi.testclient import TestClient

from mcp_servers import audit_store
from agents.base import AgentInput
from agents.bus import InMemoryEventBus
from agents.orchestrator import AgentOrchestrator
from backend.main import app
from backend.services.demo_data import ALERT_STORE
from mcp_servers.analytics_mcp.server import app as analytics_app
from mcp_servers.battery_mcp.server import app as battery_app
from mcp_servers.cyber_mcp.server import app as cyber_app
from mcp_servers.governance_mcp.server import app as governance_app


def test_v3_orchestrator_runs_full_agent_sequence_without_redis(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_store, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(audit_store, "AUDIT_FILE", tmp_path / "governance.jsonl")
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
    records = audit_store.read_audit_records()
    assert any(record["record_type"] == "agent_decision" for record in records)
    assert any(record["record_type"] == "mcp_tool_call" for record in records)


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


def test_v3_mcp_servers_expose_health_and_tools():
    servers = [
        (battery_app, 8001),
        (cyber_app, 8002),
        (analytics_app, 8003),
        (governance_app, 8004),
    ]

    for server_app, port in servers:
        client = TestClient(server_app)
        health = client.get("/health")
        tools = client.get("/tools")

        assert health.status_code == 200
        assert health.json()["port"] == port
        assert tools.status_code == 200
        assert tools.json()["tools"]


def test_v3_approval_endpoint_persists_decision_and_executes_approved_containment(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_store, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(audit_store, "AUDIT_FILE", tmp_path / "governance.jsonl")
    alert = next(alert for alert in ALERT_STORE if alert["risk_tier"] == "CRITICAL")
    client = TestClient(app)

    response = client.post(
        "/agents/approval",
        json={
            "event_id": "approval-test-event",
            "alert_id": alert["alert_id"],
            "decision": "approved",
            "gated_actions": [f"Isolate {alert['asset_id']} pending operator approval."],
            "operator": "pytest",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "recorded"
    assert body["executed_actions"][0]["status"] == "quarantined"
    records = client.get("/agents/audit-log").json()["records"]
    assert any(record["record_type"] == "human_approval" for record in records)
