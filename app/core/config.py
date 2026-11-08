"""
Application Configuration Core
Pydantic v2 Settings for Financial Resilience Engine
"""

from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT=Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application Basics
    ENVIRONMENT: str = Field(default="development", description="Environment mode (development/testing/production)")
    DEBUG: bool = Field(default=True, description="Debug mode")
    APP_NAME: str = Field(default="Financial Resilience Engine")
    API_V1_PREFIX: str = Field(default="/api/v1")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # Security & Auth
    SECRET_KEY: str = Field(default="temporary-development-secret-key-replace-in-production-1234567890")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    ENABLE_REGISTRATION: bool = False

    # Database Configuration (TigerData / TimescaleDB)
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/financial_resilience",
        description="TigerData or PostgreSQL connection string"
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)
    DATABASE_POOL_RECYCLE: int = Field(default=1800)
    USE_LOCAL_FALLBACK_DB: bool = Field(
        default=True,
        description="Fallback to local SQLite during development/test when TigerData host is unreachable"
    )

    # Redis & Caching
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Message Broker (RabbitMQ / Celery)
    CELERY_BROKER_URL: str = Field(default="amqp://guest:guest@localhost:5672//")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/1")

    # Google Gemini AI Integration
    GEMINI_API_KEY: str | None = Field(default=None)
    GEMINI_MODEL_NAME: str = Field(default="gemini-2.0-flash")
    GEMINI_REQUEST_TIMEOUT_SECONDS: int = Field(default=30)
    GEMINI_MAX_RETRIES: int = Field(default=3)

    # ElevenLabs Voice Integration
    ELEVENLABS_API_KEY: str | None = Field(default=None)
    ELEVENLABS_VOICE_ID: str = Field(default="21m00Tcm4TlvDq8ikWAM")

    # External APIs
    STATSCAN_API_BASE_URL: str = Field(default="https://www150.statcan.gc.ca/t1/wds/rest")
    BANKING_PROVIDER_MOCK_MODE: bool = Field(default=True)
    BANKING_API_URL: str | None = None
    BANKING_API_KEY: str | None = None
    UNDERWRITING_API_URL: str | None = None
    UNDERWRITING_API_KEY: str | None = None
    BROWSING_API_URL: str | None = None
    BROWSING_API_KEY: str | None = None
    NOTIFICATION_API_URL: str | None = None
    NOTIFICATION_API_KEY: str | None = None
    INTEGRATION_TIMEOUT_SECONDS: float = Field(default=20, gt=0, le=120)
    INTEGRATION_RETRIES: int = Field(default=2, ge=0, le=5)
    ELEVENLABS_EMPATHETIC_VOICE_ID: str | None = None
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"
    STATSCAN_CPI_VECTOR: int = 41690973
    INSTALLMENT_ANNUAL_RATE: float | None = Field(default=None, ge=0, le=100)
    INSTALLMENT_FEE: float | None = Field(default=None, ge=0)
    FRAUD_NEW_MERCHANT: float = Field(default=0.50, ge=0, le=1)
    FRAUD_FAMILIAR_MERCHANT: float = Field(default=0.50, ge=0, le=1)
    FRAUD_RECURRING_MULTIPLIER: float = Field(default=0.90, ge=0, le=1)
    FRAUD_BROWSING_REDUCTION: float = Field(default=0.15, ge=0, le=1)
    FRAUD_CHARGEBACK_INCREMENT: float = Field(default=0.10, ge=0, le=1)
    FRAUD_GEOGRAPHY_INCREMENT: float = Field(default=0.25, ge=0, le=1)
    FRAUD_BUDGET_INCREMENT: float = Field(default=0.10, ge=0, le=1)
    FRAUD_REVIEW_THRESHOLD: float = Field(default=0.85, ge=0, le=1)
    FRAUD_Z_THRESHOLD: float = Field(default=3.0, gt=0)
    FRAUD_CATEGORY_INCREMENT: float = Field(default=0.10,ge=0,le=1)
    FRAUD_TIME_INCREMENT: float = Field(default=0.10,ge=0,le=1)
    FRAUD_CART_INCREMENT: float = Field(default=0.10,ge=0,le=1)
    JOB_INTERVAL_SECONDS: int = Field(default=3600, ge=10)
    ENABLE_BACKGROUND_JOBS: bool = True
    SUMMARY_RETENTION_DAYS: int = Field(default=0, ge=0, le=36500)
    SOURCE_DATA_CURRENCY: str | None = Field(default="CAD",pattern=r'^[A-Z]{3}$')

    # Security & Compliance
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000", "http://localhost:8501"])
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")

    @field_validator("DEBUG", mode="before")
    @classmethod
    def assemble_debug(cls, v):
        if isinstance(v, str):
            val = v.strip().lower()
            if val in ("release", "prod", "production", "0", "false", "no", "off"):
                return False
            if val in ("debug", "dev", "development", "1", "true", "yes", "on"):
                return True
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        return ["*"]

    @model_validator(mode="after")
    def production_security(self):
        from urllib.parse import urlsplit
        for name in ("BANKING", "UNDERWRITING", "BROWSING", "NOTIFICATION"):
            url = getattr(self, name + "_API_URL")
            if url:
                parsed = urlsplit(url)
                if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                    raise ValueError(f"{name}_API_URL must be an HTTP(S) base URL without embedded credentials or query")
                if self.ENVIRONMENT == "production" and parsed.scheme != "https":
                    raise ValueError(f"{name}_API_URL requires HTTPS in production")
        if self.ENVIRONMENT == "production":
            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.startswith(("temporary-", "change-this")):
                raise ValueError("Production requires a unique SECRET_KEY of at least 32 characters")
            if self.DEBUG or self.USE_LOCAL_FALLBACK_DB:
                raise ValueError("Production requires DEBUG=false and USE_LOCAL_FALLBACK_DB=false")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("Production requires explicit CORS origins")
        return self

settings = Settings()
