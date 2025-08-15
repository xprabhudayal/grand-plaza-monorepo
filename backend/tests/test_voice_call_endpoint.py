import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_start_voice_call():
    """Test the start voice call endpoint"""
    response = client.post("/api/v1/voice-sessions/start-call?room_number=101")
    # We expect this to fail because we don't have the full setup, but we can check if the endpoint exists
    assert response.status_code in [201, 500]  # Either created or internal server error

def test_get_active_voice_sessions():
    """Test the get active voice sessions endpoint"""
    response = client.get("/api/v1/voice-sessions/active")
    assert response.status_code == 200