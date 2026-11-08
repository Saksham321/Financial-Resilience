"""
Unit Tests for Application Configuration
"""

from app.core.config import Settings

def test_settings_defaults():
    settings = Settings()
    assert settings.APP_NAME == "Financial Resilience Engine"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
    assert "postgresql" in settings.DATABASE_URL or "sqlite" in settings.DATABASE_URL

def test_cors_origins_parsing():
    s = Settings(CORS_ORIGINS="http://localhost:3000,http://example.com")
    assert "http://localhost:3000" in s.CORS_ORIGINS
    assert "http://example.com" in s.CORS_ORIGINS
