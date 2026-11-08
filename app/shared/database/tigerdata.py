"""
TigerData & TimescaleDB Extension Utilities
Manages Hypertables, PostGIS, and Continuous Aggregates
"""

import re
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger

async def inspect_database_capabilities(session: AsyncSession) -> Dict[str, Any]:
    """
    Queries active database extensions to confirm TigerData / TimescaleDB features.
    """
    bind = session.bind
    if bind and "sqlite" in str(bind.url):
        return {
            "dialect": "sqlite",
            "timescaledb_active": False,
            "postgis_active": False,
            "pgcrypto_active": False,
            "installed_extensions": [],
            "status": "DEVELOPMENT_SQLITE_FALLBACK"
        }

    try:
        result = await session.execute(text("SELECT extname, extversion FROM pg_extension;"))
        extensions = {row[0]: row[1] for row in result.fetchall()}
        return {
            "dialect": "postgresql",
            "timescaledb_active": "timescaledb" in extensions,
            "timescaledb_version": extensions.get("timescaledb"),
            "postgis_active": "postgis" in extensions,
            "postgis_version": extensions.get("postgis"),
            "pgcrypto_active": "pgcrypto" in extensions,
            "installed_extensions": list(extensions.keys()),
            "status": "TIGERDATA_CONNECTED" if "timescaledb" in extensions else "POSTGRES_CONNECTED"
        }
    except Exception as e:
        logger.warning("Failed to query pg_extension", error=str(e))
        return {
            "dialect": "unknown",
            "timescaledb_active": False,
            "postgis_active": False,
            "error": str(e),
            "status": "DISCONNECTED"
        }

async def enable_hypertable_if_supported(
    session: AsyncSession,
    table_name: str,
    time_column: str = "timestamp",
    chunk_time_interval: str = "7 days"
) -> bool:
    """
    Converts a time-series table into a TimescaleDB hypertable if supported.
    """
    caps = await inspect_database_capabilities(session)
    if not caps.get("timescaledb_active"):
        logger.info(
            "TimescaleDB is not active. Table will remain standard relational table.",
            table_name=table_name
        )
        return False

    # These values become SQL identifiers/literals in the DDL statement below.
    # Accept simple (optionally schema-qualified) PostgreSQL identifiers and a
    # plain interval such as "7 days"; reject arbitrary SQL fragments.
    identifier = r"[A-Za-z_][A-Za-z0-9_$]*"
    if not re.fullmatch(rf"{identifier}(?:\.{identifier})?", table_name):
        raise ValueError("table_name must be a simple or schema-qualified SQL identifier")
    if not re.fullmatch(identifier, time_column):
        raise ValueError("time_column must be a simple SQL identifier")
    if not re.fullmatch(r"[1-9][0-9]*\s+(?:second|minute|hour|day|week)s?", chunk_time_interval, re.IGNORECASE):
        raise ValueError("chunk_time_interval must be a positive PostgreSQL interval, for example '7 days'")

    try:
        query = text(f"""
            SELECT create_hypertable(
                '{table_name}',
                '{time_column}',
                chunk_time_interval => INTERVAL '{chunk_time_interval}',
                if_not_exists => TRUE
            );
        """)
        await session.execute(query)
        logger.info("Successfully configured hypertable", table_name=table_name)
        return True
    except Exception as e:
        logger.warning("Failed to configure hypertable", table_name=table_name, error=str(e))
        await session.rollback()
        return False
