"""Persistent domain records. Financial source data is shared across engines."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, DateTime, Boolean, JSON, ForeignKey, UniqueConstraint, Integer, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, GUID


class Owned:
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("core.users.id"), index=True)


class Transaction(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "ledger_transactions"
    __table_args__ = (UniqueConstraint("user_id", "external_id"), {"schema": "transactions"})
    account_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("core.bank_accounts.id"))
    external_id: Mapped[str] = mapped_column(String(150))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))  # positive income; negative expense
    merchant: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80))
    cart_size: Mapped[int | None] = mapped_column(Integer)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    vacation_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("behavioral_fraud.vacations.id"))
    fraud: Mapped[dict] = mapped_column(JSON, default=dict)


class PrivacySetting(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "privacy_settings"
    __table_args__ = (UniqueConstraint("user_id"), {"schema": "core"})
    geolocation_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    home_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    home_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    radius_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=50)


class Budget(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "spending_budgets"
    __table_args__ = (UniqueConstraint("user_id", "category"), {"schema": "core"})
    category: Mapped[str] = mapped_column(String(80))
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class ScheduledFlow(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "scheduled_flows"
    __table_args__ = (UniqueConstraint("user_id", "external_id"), {"schema": "predictive_planning"})
    external_id: Mapped[str] = mapped_column(String(150))
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    recurrence: Mapped[str] = mapped_column(String(20), default="once")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_offer_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    end_date: Mapped[date | None] = mapped_column(Date)


class Vacation(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "vacations"
    __table_args__ = {"schema": "behavioral_fraud"}
    destination: Mapped[str] = mapped_column(String(150))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    budget: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    radius_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Chargeback(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "chargebacks"
    __table_args__ = (UniqueConstraint("user_id", "external_id"), {"schema": "behavioral_fraud"})
    external_id: Mapped[str] = mapped_column(String(150))
    reported_on: Mapped[date] = mapped_column(Date)
    merchant: Mapped[str] = mapped_column(String(150))


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "recurring_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "merchant", "cadence"), {"schema": "subscriptions"})
    merchant: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    cadence: Mapped[str] = mapped_column(String(20))
    next_billing: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")


class Shock(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "shocks"
    __table_args__ = (UniqueConstraint("user_id", "external_id"), {"schema": "shock_mediation"})
    external_id: Mapped[str] = mapped_column(String(150))
    name: Mapped[str] = mapped_column(String(150))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    due_date: Mapped[date] = mapped_column(Date)
    shortfall: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    routing: Mapped[dict] = mapped_column(JSON, default=dict)


class Offer(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "installment_offers"
    __table_args__ = (UniqueConstraint("shock_id", "months"), {"schema": "shock_mediation"})
    shock_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("shock_mediation.shocks.id"))
    months: Mapped[int] = mapped_column(Integer)
    terms: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="proposed")
    expires_on: Mapped[date] = mapped_column(Date)


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key"), {"schema": "core"})
    dedupe_key: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(2000))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_status: Mapped[str] = mapped_column(String(30), default="in_app")


class Forecast(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "forecast_snapshots"
    __table_args__ = (UniqueConstraint("user_id"), {"schema": "predictive_planning"})
    metrics: Mapped[dict] = mapped_column(JSON)


class CPI(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cpi_observations"
    __table_args__ = (UniqueConstraint("month"), {"schema": "inflation"})
    month: Mapped[str] = mapped_column(String(7))
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    source: Mapped[str] = mapped_column(String(255))


class Summary(Base, UUIDPrimaryKeyMixin, TimestampMixin, Owned):
    __tablename__ = "verified_summaries"
    __table_args__ = {"schema": "ai"}
    metrics: Mapped[dict] = mapped_column(JSON)
    text: Mapped[str] = mapped_column(String(20000))
    audio: Mapped[bytes | None] = mapped_column(LargeBinary)
