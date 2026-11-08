"""
Authentication Endpoints
User Registration, Login, JWT Token Issuance, and Profile Retrieval
"""

import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.shared.database.session import get_db
from app.shared.database.models import User, UserProfile, UserPreference
from app.shared.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import AuthenticationError, DuplicateResourceError, AuthorizationError
from app.core.dependencies import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Registers a new user account, creates default profile and preferences, and returns JWT.
    """
    if not settings.ENABLE_REGISTRATION:
        raise AuthorizationError("Public sign-up is disabled. Search by customer account ID or use the administrator login.")
    # Check if user already exists
    existing_query = select(User).where(User.email == req.email)
    existing = (await db.execute(existing_query)).scalar_one_or_none()
    if existing:
        raise DuplicateResourceError(f"User with email '{req.email}' already exists")

    # Create User
    new_user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        is_active=True,
        is_verified=True,
        role="user"
    )
    db.add(new_user)
    await db.flush()

    # Create UserProfile
    profile = UserProfile(
        user_id=new_user.id,
        first_name=req.first_name,
        last_name=req.last_name,
        province=req.province
    )
    db.add(profile)

    # Create UserPreference
    pref = UserPreference(
        user_id=new_user.id,
        consent_ai_processing=False,
        notification_channel="EMAIL"
    )
    db.add(pref)

    await db.commit()
    await db.refresh(new_user)

    # Generate Token
    token = create_access_token(subject=new_user.id, roles=[new_user.role])

    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user_id=new_user.id,
        email=new_user.email,
        role=new_user.role
    )

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Authenticates a user via email and password, returning a JWT token.
    """
    query = select(User).where(User.email == req.email)
    user = (await db.execute(query)).scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    token = create_access_token(subject=user.id, roles=[user.role])

    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user_id=user.id,
        email=user.email,
        role=user.role
    )

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Retrieves currently authenticated user profile and details.
    """
    profile_query = select(UserProfile).where(UserProfile.user_id == current_user.id)
    profile = (await db.execute(profile_query)).scalar_one_or_none()

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        role=current_user.role,
        first_name=profile.first_name if profile else None,
        last_name=profile.last_name if profile else None,
        province=profile.province if profile else None
    )
