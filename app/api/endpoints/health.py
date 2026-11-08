"""
Health & Readiness Check Endpoints
"""

from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.shared.database.session import get_db
from app.shared.database.tigerdata import inspect_database_capabilities
from app.shared.schemas.health import HealthResponse, ReadinessResponse
from app.integrations.gemini.client import gemini_client

router = APIRouter(tags=["Health & Diagnostics"])

@router.get("/health", response_model=HealthResponse, summary="Shallow Health Check")
async def shallow_health():
    """
    Returns 200 OK if FastAPI process is responsive. Used for container orchestration liveness probes.
    """
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT
    )

@router.get("/health/ready", response_model=ReadinessResponse, summary="Deep Readiness & Dependency Probe")
async def deep_readiness(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Verifies database connectivity, TigerData/TimescaleDB extension status, and AI SDK readiness.
    """
    # 1. Check Database
    db_caps = await inspect_database_capabilities(db)
    
    # Check simple query
    try:
        await db.execute(text("SELECT 1;"))
        db_alive = True
    except Exception as e:
        db_alive = False
        db_caps["connection_error"] = str(e)

    overall_status = "HEALTHY" if db_alive else "DEGRADED"

    # Registered engines in the modular architecture
    active_engines = [
        "shock_mediation",
        "predictive_planning",
        "behavioral_fraud",
        "subscription_manager",
        "inflation_tracker",
        "expense_pyramid",
        "ai_orchestration",
        "voice"
    ]

    return ReadinessResponse(
        status=overall_status,
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        database=db_caps,
        active_engines=active_engines,
        gemini_scaffold=gemini_client.get_status()
    )
