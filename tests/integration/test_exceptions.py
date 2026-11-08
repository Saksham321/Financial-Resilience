"""
Integration Tests for Standardized Exception Handling and Correlation ID
"""

import pytest

@pytest.mark.asyncio
async def test_correlation_id_header_in_response(client):
    response = await client.get("/health", headers={"X-Correlation-ID": "custom-trace-id-12345"})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "custom-trace-id-12345"

@pytest.mark.asyncio
async def test_validation_error_format(client):
    # Invalid registration payload (missing required fields)
    response = await client.post("/api/v1/auth/register", json={"email": "not-an-email"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "correlation_id" in data["error"]
