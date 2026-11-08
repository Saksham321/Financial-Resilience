"""
Integration Tests for Health and Readiness APIs
"""

import pytest

@pytest.mark.asyncio
async def test_shallow_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Financial Resilience Engine" in data["app_name"]

@pytest.mark.asyncio
async def test_deep_readiness_endpoint(client):
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["HEALTHY", "DEGRADED"]
    assert "database" in data
    assert "active_engines" in data
    assert len(data["active_engines"]) == 8
    assert "gemini_scaffold" in data
