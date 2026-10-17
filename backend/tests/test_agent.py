import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.models.auth import UserRole
from app.services.agent_service import AgentService
from tests.test_phase8_auth import get_token_for_role

client = TestClient(app)

@pytest.fixture
def reviewer_token():
    return get_token_for_role(UserRole.REVIEWER_MD, username="dr_agent_tester")

def test_agent_status_endpoint(reviewer_token):
    res = client.get("/api/agent/status", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "groq_configured" in data
    assert "active_model" in data
    assert "supported_models" in data

def test_agent_set_groq_key_validation(reviewer_token):
    # Short / invalid key rejected
    res_bad = client.post(
        "/api/agent/set-groq-key",
        json={"groq_api_key": "short"},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res_bad.status_code == 400

    # Valid key accepted
    valid_key = "gsk_test_1234567890abcdefghijklmnopqrstuvwxyz"
    res_ok = client.post(
        "/api/agent/set-groq-key",
        json={"groq_api_key": valid_key},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "SUCCESS"
    assert settings.GROQ_API_KEY == valid_key

def test_agent_chat_deterministic_fallback(reviewer_token):
    # When no Groq key is provided, deterministic clinical reasoning is synthesized
    res = client.post(
        "/api/agent/chat",
        json={
            "message": "Based on this note, can the head CT scan be approved?",
            "case_id": "CASE-2026-001"
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert data["model_used"] == "MedRule Deterministic Rules Engine"
    assert "MedRule Clinical Assessment" in data["response"]
    assert "CASE-2026-001" in data["case_id"]

@pytest.mark.anyio
async def test_agent_chat_groq_mocked(reviewer_token):
    mock_groq_response = (
        "### Prior Authorization Determination\n\n"
        "**Verdict: APPROVED**\n\n"
        "Based on review of the neurological encounter for John Doe, the requested CT Scan of Head with Contrast "
        "meets all medical necessity criteria under United Healthcare Guideline P-UHC-CT-2026.\n\n"
        "- **Indication:** Severe atypical headache with documented left pronator drift.\n"
        "- **Duration:** Symptoms persisting for 9 weeks (exceeds >= 6 weeks threshold).\n"
        "- **Conservative Trial:** Failed NSAID and physical therapy regimen."
    )

    with patch("app.services.agent_service.AgentService.call_groq_api", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = (mock_groq_response, "llama-3.3-70b-versatile", None)

        res = client.post(
            "/api/agent/chat",
            json={
                "message": "Can this CT scan be approved?",
                "case_id": "CASE-2026-001",
                "groq_api_key": "gsk_mock_valid_key_123456789012345"
            },
            headers={"Authorization": f"Bearer {reviewer_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_groq_powered"] is True
        assert "APPROVED" in data["response"]
        assert "llama-3.3-70b-versatile (Groq)" in data["model_used"]
