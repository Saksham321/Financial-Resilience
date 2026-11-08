"""
Security & Cryptography Module
JWT token generation, validation, and password hashing
"""

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID
from app.core.config import settings
from app.core.exceptions import AuthenticationError

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(
    subject: str | UUID,
    roles: Optional[list[str]] = None,
    expires_delta: Optional[timedelta] = None,
    custom_claims: Optional[Dict[str, Any]] = None
) -> str:
    """Generates a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "roles": roles or ["user"],
        "iss": settings.APP_NAME,
    }

    if custom_claims:
        to_encode.update(custom_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    """Validates and decodes a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.APP_NAME,
            options={"require": ["exp", "sub", "iat"]}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Authentication token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid authentication token: {str(e)}")
