"""
Integration Tests for Authentication API (Register, Login, Me)
"""

import pytest

@pytest.mark.asyncio
async def test_register_login_and_me_flow(client):
    # 1. Register new user
    register_payload = {
        "email": "resilience.tester@example.com",
        "password": "SecurePassword2026!",
        "first_name": "Jordan",
        "last_name": "Lee",
        "province": "Ontario"
    }
    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["email"] == "resilience.tester@example.com"
    token = reg_data["access_token"]

    # 2. Prevent duplicate registration
    dup_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert dup_res.status_code == 409
    dup_data = dup_res.json()
    assert dup_data["error"]["code"] == "RESOURCE_CONFLICT"

    # 3. Login with credentials
    login_payload = {
        "email": "resilience.tester@example.com",
        "password": "SecurePassword2026!"
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data

    # 4. Access protected /me endpoint with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "resilience.tester@example.com"
    assert me_data["first_name"] == "Jordan"
    assert me_data["last_name"] == "Lee"

    # 5. Access protected /me without token fails with 401
    unauth_res = await client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401
    assert unauth_res.json()["error"]["code"] == "AUTHENTICATION_FAILED"
