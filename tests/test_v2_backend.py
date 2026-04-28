from fastapi.testclient import TestClient

from backend.main import app
from models.fusion.risk_scorer import RiskComponents, compute_risk_score, get_risk_tier
from rag.chains.conversational_chain import classify_intent


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
