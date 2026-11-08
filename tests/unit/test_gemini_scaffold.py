"""
Unit Tests for Gemini SDK Scaffolding
"""

from app.integrations.gemini.client import gemini_client

def test_gemini_client_status():
    status = gemini_client.get_status()
    assert status["sdk"] == "google-genai"
    assert "model_configured" in status
    assert "mode" in status
    assert status["mode"] in ["LIVE_API", "UNCONFIGURED"]
