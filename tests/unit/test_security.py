"""
Unit Tests for Security, Password Hashing, and JWT Tokens
"""

import uuid
import pytest
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.core.exceptions import AuthenticationError

def test_password_hashing_and_verification():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

def test_jwt_token_creation_and_decoding():
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id, roles=["user", "analyst"])
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert "user" in payload["roles"]
    assert "analyst" in payload["roles"]

def test_expired_jwt_token_raises_error():
    user_id = uuid.uuid4()
    # Expired token (negative delta)
    token = create_access_token(subject=user_id, expires_delta=timedelta(seconds=-10))

    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(token)
    assert "expired" in str(exc_info.value.message).lower()

def test_invalid_jwt_token_raises_error():
    with pytest.raises(AuthenticationError):
        decode_access_token("this.is.a.completely.invalid.token")
