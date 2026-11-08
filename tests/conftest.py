"""
Pytest Test Fixtures & In-Memory Async Database Setup
"""

import sys
import os
# Ensure app module is in python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app as fastapi_app
from app.shared.database.base import Base
from app.shared.database.session import get_db
# Import models to ensure all tables are registered
import app.shared.database.models # noqa

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated in-memory SQLite database session for tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Attach schemas in SQLite for test compatibility with PostgreSQL schemas
    @event.listens_for(engine.sync_engine, "connect")
    def attach_sqlite_schemas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        for schema in ["core", "audit", "transactions", "shock_mediation", "predictive_planning", "behavioral_fraud", "subscriptions", "inflation", "expense_pyramid", "ai"]:
            cursor.execute(f"ATTACH DATABASE ':memory:' AS {schema};")
        cursor.close()

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provides an authenticated/unauthenticated HTTPX AsyncClient with overridden DB dependency."""
    async def override_get_db():
        try:
            yield test_db_session
            await test_db_session.commit()
        except Exception:
            await test_db_session.rollback()
            raise

    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()
