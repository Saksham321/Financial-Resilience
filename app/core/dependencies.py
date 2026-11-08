"""
FastAPI Request Dependencies
Authentication, Database sessions, and Authorization guards
"""

import uuid
from typing import Annotated, Optional
from fastapi import Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.shared.database.session import get_db
from app.shared.database.models import User
from app.core.security import decode_access_token
from app.core.exceptions import AuthenticationError, AuthorizationError

security_scheme = HTTPBearer(auto_error=False)

async def get_correlation_id(
    request: Request,
    x_correlation_id: Annotated[Optional[str], Header()] = None
) -> str:
    """Extracts or generates correlation ID for request tracing."""
    return getattr(request.state, "correlation_id", x_correlation_id or str(uuid.uuid4()))

async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Validates JWT token and retrieves active user entity.
    """
    if not credentials:
        raise AuthenticationError("Authorization header missing or invalid")

    payload = decode_access_token(credentials.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Malformed token payload")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Invalid user ID in token")

    query = select(User).where(User.id == user_uuid, User.is_active.is_(True))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User not found or inactive")

    return user

def require_role(required_role: str):
    """Factory dependency for role-based authorization."""
    async def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role != required_role and current_user.role != "admin":
            raise AuthorizationError(f"Operation requires '{required_role}' privileges")
        return current_user
    return role_checker
