"""Validated inputs shared by API, imports, and integration adapters."""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2, allow_inf_nan=False)]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2, allow_inf_nan=False)]
Category = Annotated[str, Field(min_length=1, max_length=80)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AccountInput(Input):
    institution_name: str = Field(min_length=1, max_length=100)
    account_type: Literal["CHECKING", "SAVINGS", "CREDIT", "LOAN"]
    masked_account_number: str = Field(pattern=r"^[*xX\d -]{1,20}$")
    current_balance: Money
    available_balance: Money
    currency: Literal["CAD"] = "CAD"


class Coordinates(Input):
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)

    @model_validator(mode="after")
    def paired(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be supplied together")
        return self


class TransactionInput(Coordinates):
    external_id: str = Field(min_length=1, max_length=150)
    account_id: UUID
    occurred_at: datetime
    amount: Money
    merchant: str = Field(min_length=1, max_length=150)
    category: Category = "unclassified"
    cart_size: int | None = Field(default=None, ge=0, le=100000)

    @field_validator("occurred_at")
    @classmethod
    def past(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Transaction time requires a timezone")
        if value > datetime.now(timezone.utc):
            raise ValueError("Future transactions belong in scheduled flows")
        return value.astimezone(timezone.utc)

    @field_validator("amount")
    @classmethod
    def nonzero(cls, value):
        if value == 0:
            raise ValueError("Transaction amount cannot be zero")
        return value

    @field_validator("category", "merchant")
    @classmethod
    def normalized(cls, value):
        return value.casefold()


class PrivacyInput(Coordinates):
    ai_consent: bool = False
    browsing_consent: bool = False
    geolocation_consent: bool = False
    radius_km: Decimal = Field(default=50, gt=0, le=20000, allow_inf_nan=False)

    @model_validator(mode="after")
    def location_permission(self):
        if self.latitude is not None and not self.geolocation_consent:
            raise ValueError("Geolocation requires explicit consent")
        return self


class BudgetInput(Input):
    category: Category
    monthly_amount: PositiveMoney

    @field_validator("category")
    @classmethod
    def normalized(cls, value):
        return value.casefold()


class FlowInput(Input):
    external_id: str = Field(min_length=1, max_length=150)
    name: str = Field(min_length=1, max_length=150)
    category: Category
    amount: Money
    due_date: date
    recurrence: Literal["once", "monthly", "annual"] = "once"
    active: bool = True
    end_date: date | None = None

    @model_validator(mode="after")
    def valid(self):
        if not self.amount or self.end_date and self.end_date < self.due_date:
            raise ValueError("Invalid flow amount or date range")
        self.category = self.category.casefold()
        return self


class VacationInput(Input):
    destination: str = Field(min_length=1, max_length=150)
    start_date: date
    end_date: date
    budget: PositiveMoney
    latitude: Decimal = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: Decimal = Field(ge=-180, le=180, allow_inf_nan=False)
    radius_km: Decimal = Field(default=Decimal("100"), gt=0, le=20000, allow_inf_nan=False)
    enabled: bool = True

    @model_validator(mode="after")
    def dates(self):
        if self.end_date < self.start_date:
            raise ValueError("Vacation end date must follow start date")
        return self


class ChargebackInput(Input):
    external_id: str = Field(min_length=1, max_length=150)
    reported_on: date
    merchant: str = Field(min_length=1, max_length=150)

    @field_validator("reported_on")
    @classmethod
    def past(cls, value):
        if value > date.today():
            raise ValueError("Chargeback date cannot be in the future")
        return value


class ScenarioInput(Input):
    amount: PositiveMoney
    due_date: date

    @field_validator("due_date")
    @classmethod
    def future(cls, value):
        if value < date.today():
            raise ValueError("Shock due date cannot precede today")
        from datetime import timedelta
        if value > date.today() + timedelta(days=365):
            raise ValueError("Shock assessment supports the next 365 days")
        return value


class ShockInput(ScenarioInput):
    external_id: str = Field(min_length=1, max_length=150)
    name: str = Field(min_length=1, max_length=150)


class DecisionInput(Input):
    decision: Literal["accepted", "rejected"]
    confirm_obligation: bool = False


class SubscriptionInput(Input):
    status: Literal["active", "cancellation_requested", "cancelled"]


class SummaryInput(Input):
    question: str = Field(default="Explain my financial health, spending habits, runway, shock scenarios, recommendations and contingency plan.", max_length=2000)


class Narrative(Input):
    introduction: Literal["Let's review your verified financial picture together.", "Small, informed steps can help you plan with confidence."]
    metric_keys: list[str] = Field(max_length=12)
    recommendation_ids: list[int] = Field(max_length=8)
    closing: Literal["Review the assumptions and upcoming commitments before making changes.", "You can update your accounts and schedules to keep this plan current."]


class AudioInput(Input):
    profile: Literal["professional", "empathetic"] = "professional"
