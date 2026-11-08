"""
Unit Tests for TigerData / TimescaleDB Inspection Utilities
"""

import pytest
from app.shared.database.tigerdata import inspect_database_capabilities, enable_hypertable_if_supported

@pytest.mark.asyncio
async def test_inspect_database_capabilities_sqlite(test_db_session):
    caps = await inspect_database_capabilities(test_db_session)
    assert caps["dialect"] == "sqlite"
    assert caps["timescaledb_active"] is False
    assert caps["status"] == "DEVELOPMENT_SQLITE_FALLBACK"

@pytest.mark.asyncio
async def test_enable_hypertable_on_non_timescaledb_graceful(test_db_session):
    # Should safely return False on non-TimescaleDB instances without crashing
    res = await enable_hypertable_if_supported(test_db_session, "sample_events", "created_at")
    assert res is False
