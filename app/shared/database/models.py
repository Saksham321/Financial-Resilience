"""
Relational Entities for Core & Audit Schemas
SQLAlchemy 2.0 Models with UUIDs and Exact Decimal Arithmetic
"""

import uuid
from decimal import Decimal
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String, Boolean, Numeric, Date, DateTime, ForeignKey, Text, JSON, Enum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, GUID

# -----------------------------------------------------------------------------
# CORE SCHEMA MODELS
# -----------------------------------------------------------------------------

class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = {"schema": "core"}

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    bank_accounts: Mapped[List["BankAccount"]] = relationship(
        "BankAccount", back_populates="user", cascade="all, delete-orphan"
    )
    goals: Mapped[List["FinancialGoal"]] = relationship(
        "FinancialGoal", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped[Optional["UserPreference"]] = relationship(
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

class UserProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_profiles"
    __table_args__ = {"schema": "core"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("core.users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    risk_tier: Mapped[str] = mapped_column(String(30), default="MODERATE", nullable=False) # CONSERVATIVE, MODERATE, AGGRESSIVE
    annual_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    credit_score_estimate: Mapped[Optional[int]] = mapped_column(nullable=True)
    province: Mapped[str] = mapped_column(String(50), default="Ontario", nullable=False)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="profile")

class BankAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bank_accounts"
    __table_args__ = {"schema": "core"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("core.users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    institution_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False) # CHECKING, SAVINGS, CREDIT, LOAN
    currency: Mapped[str] = mapped_column(String(3), default="CAD", nullable=False)
    masked_account_number: Mapped[str] = mapped_column(String(20), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    available_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="bank_accounts")

class FinancialGoal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "financial_goals"
    __table_args__ = {"schema": "core"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("core.users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="IN_PROGRESS", nullable=False) # IN_PROGRESS, ACHIEVED, PAUSED

    user: Mapped["User"] = relationship("User", back_populates="goals")

class UserPreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_preferences"
    __table_args__ = {"schema": "core"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("core.users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    consent_ai_processing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_browsing_context: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_channel: Mapped[str] = mapped_column(String(30), default="EMAIL", nullable=False)
    vacation_mode_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="preferences")

# -----------------------------------------------------------------------------
# AUDIT SCHEMA MODELS
# -----------------------------------------------------------------------------

class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "system_events"
    __table_args__ = {"schema": "audit"}

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

class FinancialDecision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "financial_decisions"
    __table_args__ = {"schema": "audit"}

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True, nullable=False)
    decision_type: Mapped[str] = mapped_column(String(100), nullable=False) # SHOCK_MEDIATION, LOAN_OFFER, FRAUD_ALERT
    status: Mapped[str] = mapped_column(String(50), nullable=False) # PROPOSED, ACCEPTED, DECLINED, EXPIRED
    inputs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    outputs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class UserConsent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_consents"
    __table_args__ = {"schema": "audit"}

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True, nullable=False)
    consent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    terms_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)

# Register domain metadata for application startup and Alembic.
import app.engines.models  # noqa: E402,F401
import app.shared.database.datasets  # noqa: E402,F401
