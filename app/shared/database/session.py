"""
SQLAlchemy 2.0 Database Session Management
Supports TigerData (PostgreSQL/TimescaleDB) with graceful local fallback
"""

import os
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.logging import logger

def _resolve_database_urls():
    """Normalize PostgreSQL connection URLs for app and migration engines.

    Tiger Cloud supplies a normal PostgreSQL URL (often ``postgresql://``).
    Psycopg 3 supports both SQLAlchemy sync and async engines, so use it for
    both by default. If a deployment explicitly selects asyncpg, retain that
    for the async app engine and use psycopg for the sync migration engine.
    """
    raw_url = settings.DATABASE_URL.strip()
    if raw_url.startswith("postgres://"):
        raw_url = "postgresql://" + raw_url[len("postgres://"):]

    parsed_url = make_url(raw_url)
    if parsed_url.drivername.startswith("postgresql"):
        if parsed_url.drivername == "postgresql+asyncpg":
            async_url = parsed_url
            sync_url = parsed_url.set(drivername="postgresql+psycopg")
        else:
            normalized_url = parsed_url.set(drivername="postgresql+psycopg")
            async_url = normalized_url
            sync_url = normalized_url
    else:
        async_url = parsed_url
        sync_url = parsed_url

    # Check if we should fallback to SQLite during local tests if Postgres is not reachable
    if (
        settings.USE_LOCAL_FALLBACK_DB
        and parsed_url.drivername.startswith("postgresql")
        and parsed_url.host in {"localhost", "127.0.0.1", "::1"}
    ):
        # The fallback is intentionally limited to local development hosts.
        import socket
        try:
            with socket.create_connection((parsed_url.host, parsed_url.port or 5432), timeout=0.5):
                is_pg_up = True
        except OSError:
            is_pg_up = False

        if not is_pg_up:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            fallback_db = os.path.join(project_root, "financial_resilience.db")
            logger.warning(
                "TigerData/PostgreSQL localhost:5432 is unreachable. Falling back to local SQLite database.",
                fallback_db=fallback_db
            )
            async_url = make_url(f"sqlite+aiosqlite:///{fallback_db}")
            sync_url = make_url(f"sqlite:///{fallback_db}")

    if parsed_url.drivername.startswith("sqlite") and async_url == sync_url:
        async_url = parsed_url.set(drivername="sqlite+aiosqlite")
        sync_url = parsed_url.set(drivername="sqlite")
    return async_url.render_as_string(hide_password=False), sync_url.render_as_string(hide_password=False)

ASYNC_DATABASE_URL, SYNC_DATABASE_URL = _resolve_database_urls()

# Engine configurations
engine_kwargs = {
    "echo": False,
    "hide_parameters": True,
    "pool_pre_ping": True,
}

if "sqlite" not in ASYNC_DATABASE_URL:
    engine_kwargs.update({
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
        "pool_recycle": settings.DATABASE_POOL_RECYCLE,
    })

# Async Engine & Sessionmaker
async_engine = create_async_engine(ASYNC_DATABASE_URL, **engine_kwargs)

# SQLite has no PostgreSQL schemas. Map the app's logical schemas into the
# single SQLite database used by the local fallback so the same models work.
if "sqlite" in ASYNC_DATABASE_URL:
    sqlite_schema_map = {
        schema: None
        for schema in (
            "core",
            "audit",
            "transactions",
            "shock_mediation",
            "predictive_planning",
            "behavioral_fraud",
            "subscriptions",
            "inflation",
            "expense_pyramid",
            "ai",
        )
    }
    async_engine = async_engine.execution_options(schema_translate_map=sqlite_schema_map)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Sync Engine & Sessionmaker (for migrations and sync workers)
sync_kwargs = {k: v for k, v in engine_kwargs.items()}
sync_engine = create_engine(SYNC_DATABASE_URL, **sync_kwargs)
if "sqlite" in SYNC_DATABASE_URL:
    sync_engine = sync_engine.execution_options(schema_translate_map=sqlite_schema_map)
SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session, autoflush=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
