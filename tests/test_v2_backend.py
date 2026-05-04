import os

from fastapi.testclient import TestClient

from backend.main import app
from models.fusion.risk_scorer import RiskComponents, compute_risk_score, get_risk_tier
from rag.chains.conversational_chain import classify_intent


os.environ["GEMINI_API_KEY"] = ""
client = TestClient(app)


def test_copilot_status_schema():
    response = client.get("/copilot/status")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"faiss_index_ready", "gemini_key_set", "ready"}
    assert isinstance(body["ready"], bool)


def test_copilot_suggested_prompts_can_be_asset_scoped():
    response = client.get("/copilot/suggested-prompts?asset_id=BATTERY-007")

    assert response.status_code == 200
    prompts = response.json()["prompts"]
    assert prompts
    assert any("BATTERY-007" in prompt for prompt in prompts)


def test_intent_classifier_routes_v2_queries():
    assert classify_intent("What is the SOP for DDoS?") == "sop_lookup"
    assert classify_intent("Why is Tower-12 risky?") == "alert_query"
    assert classify_intent("What does SOH mean?") == "general"


def test_risk_scorer_tiers_critical_alerts():
    score = compute_risk_score(
        RiskComponents(
            battery_risk=90,
            threat_score=90,
            fusion_context=90,
            temporal_trend=40,
        )
    )

    assert score == 85.0
    assert get_risk_tier(score)["tier"] == "CRITICAL"


def test_alert_explanation_matches_alert_record():
    alert = client.get("/alerts/").json()[0]
    response = client.get(f"/explain/{alert['alert_id']}")

    assert response.status_code == 200
    explanation = response.json()
    assert explanation["alert_id"] == alert["alert_id"]
    assert explanation["asset_id"] == alert["asset_id"]
    assert explanation["risk_score"] == alert["risk_score"]
    assert explanation["contributions"]


def test_copilot_chat_uses_alert_context_and_returns_sources():
    alert = client.get("/alerts/").json()[0]
    response = client.post(
        "/copilot/chat",
        headers={"X-Session-ID": "v2-alert-test"},
        json={
            "message": f"Why is {alert['asset_id']} risky?",
            "history": [],
            "asset_context": {
                "alert_id": alert["alert_id"],
                "asset_id": alert["asset_id"],
                "risk_score": alert["risk_score"],
                "risk_tier": alert["risk_tier"],
                "threat_type": alert["threat_type"],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "alert_query"
    assert body["response"]
    assert body["sources"]
    assert body["context_count"] > 0


def test_copilot_repeated_alert_query_is_cached():
    alert = client.get("/alerts/").json()[0]
    payload = {
        "message": f"Why is {alert['asset_id']} risky?",
        "history": [],
        "asset_context": {
            "alert_id": alert["alert_id"],
            "asset_id": alert["asset_id"],
            "risk_score": alert["risk_score"],
            "risk_tier": alert["risk_tier"],
            "threat_type": alert["threat_type"],
        },
    }

    first = client.post("/copilot/chat", headers={"X-Session-ID": "v2-cache-test"}, json=payload)
    second = client.post("/copilot/chat", headers={"X-Session-ID": "v2-cache-test"}, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["cached"] is True


def test_copilot_rate_limit_uses_session_header():
    payload = {"message": "What is SOH?", "history": [], "session_id": "ignored"}
    statuses = [
        client.post("/copilot/chat", headers={"X-Session-ID": "v2-rate-test"}, json=payload).status_code
        for _ in range(11)
    ]

    assert statuses[-1] == 429
