import pytest
from pydantic import ValidationError
from app.core.config import Settings
from app.shared.schemas.auth import RegisterRequest
from app.shared.database import session


def test_production_rejects_development_credentials():
    with pytest.raises(ValidationError):
        Settings(_env_file=None,ENVIRONMENT='production')


def test_production_requires_https_provider_urls():
    with pytest.raises(ValidationError):
        Settings(_env_file=None,ENVIRONMENT='production',SECRET_KEY='a'*40,DEBUG=False,USE_LOCAL_FALLBACK_DB=False,BANKING_API_URL='http://insecure.example')


def test_db_url_retains_password_and_normalizes_sqlite(monkeypatch):
    monkeypatch.setattr(session.settings,'DATABASE_URL','postgresql://test:secret-password@cloud.example/database?sslmode=require')
    async_url,sync_url=session._resolve_database_urls()
    assert 'secret-password' in async_url and 'secret-password' in sync_url
    assert 'psycopg' in async_url and 'sslmode=require' in async_url
    monkeypatch.setattr(session.settings,'DATABASE_URL','sqlite:///local.db')
    assert session._resolve_database_urls()==('sqlite+aiosqlite:///local.db','sqlite:///local.db')


def test_bcrypt_utf8_byte_limit():
    with pytest.raises(ValidationError):
        RegisterRequest(email='test@example.com',password='é'*40,first_name='A',last_name='B')
