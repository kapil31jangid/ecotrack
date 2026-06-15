import pytest
import sys
import os
from unittest.mock import AsyncMock, patch

# Add parent path to support modular imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backend.firestore_service
# Force fallback to local store for reliability and speed during API tests
backend.firestore_service._db_initialized = True
backend.firestore_service._db_client = None

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["ai_provider"] == "Google Gemini AI (REST API)"

def test_calculate_endpoint():
    payload = {
        "session_id": "test-session-123",
        "transport_mode": "car",
        "transport_km_per_week": 150.0,
        "diet_type": "vegan",
        "energy_kwh_per_month": 120.0,
        "shopping_level": "low"
    }
    mock_tips = [
        {"action": "Use a bicycle", "saving_kg": 25.0, "difficulty": "Easy", "category": "transport"},
        {"action": "Eat home cooked meals", "saving_kg": 15.0, "difficulty": "Easy", "category": "diet"},
        {"action": "Use solar chargers", "saving_kg": 10.0, "difficulty": "Medium", "category": "energy"},
        {"action": "Buy items in bulk", "saving_kg": 5.0, "difficulty": "Easy", "category": "shopping"},
        {"action": "Turn off AC when leaving", "saving_kg": 20.0, "difficulty": "Easy", "category": "energy"},
    ]
    with patch("backend.main.get_ai_tips", new_callable=AsyncMock) as mocked_tips_service, \
         patch("backend.main.get_ai_insights", new_callable=AsyncMock) as mocked_insights_service:
        mocked_tips_service.return_value = mock_tips
        mocked_insights_service.return_value = "Mock carbon footprint insights from Gemini."
        response = client.post("/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "co2e_monthly" in data
        assert "co2e_annual" in data
        assert data["session_id"] == "test-session-123"
        assert len(data["tips"]) == 5
        assert data["tips"][0]["action"] == "Use a bicycle"
        assert data["insights"] == "Mock carbon footprint insights from Gemini."

def test_calculate_endpoint_fallback():
    payload = {
        "session_id": "test-session-123",
        "transport_mode": "car",
        "transport_km_per_week": 150.0,
        "diet_type": "vegan",
        "energy_kwh_per_month": 120.0,
        "shopping_level": "low"
    }
    with patch("backend.main.get_ai_tips", side_effect=Exception("Vertex AI Error")), \
         patch("backend.main.get_ai_insights", side_effect=Exception("Vertex AI Error")):
        response = client.post("/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "co2e_monthly" in data
        assert len(data["tips"]) == 5
        # Verification that fallback is rule-based tips
        assert any(t["action"] == "Switch to public transport" for t in data["tips"])
        assert "insights" in data
        assert "Based on your breakdown" in data["insights"]

def test_history_endpoint():
    response = client.get("/api/history/test-session-123")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_admin_stats_unauthorized():
    response = client.post("/api/admin/aggregate-stats")
    assert response.status_code == 403

def test_admin_stats_authorized_empty():
    headers = {"X-CloudScheduler-JobName": "test-cron-job"}
    response = client.post("/api/admin/aggregate-stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "stats" in data
    assert data["stats"]["total_calculations"] >= 0

def test_chat_endpoint_mocked():
    payload = {
        "session_id": "test-session-123",
        "message": "How can I reduce transport emissions?",
        "footprint_context": {
            "co2e_monthly": 150.0,
            "category_breakdown": {"transport": 50.0, "diet": 50.0, "energy": 25.0, "shopping": 25.0}
        }
    }
    with patch("backend.main.get_ai_response", new_callable=AsyncMock) as mocked_service:
        mocked_service.return_value = ("Mock reply from Gemini AI", "gemini-1.5-flash")
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Mock reply from Gemini AI"
        assert data["model_used"] == "gemini-1.5-flash"
        assert data["session_id"] == "test-session-123"
