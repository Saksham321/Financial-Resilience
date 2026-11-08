"""
Financial Resilience Engine - Main FastAPI Application
"""

import sys
from pathlib import Path
import asyncio
from contextlib import suppress

# Ensure project root directory is in sys.path when executed directly as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api.router import api_v1_router
from app.api.endpoints.health import router as root_health_router
from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.middleware.error_handler import register_exception_handlers
from app.shared.database.session import async_engine
from app.shared.database.base import Base
# Import models to ensure metadata registration
import app.shared.database.models # noqa

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events: startup and shutdown.
    """
    setup_logging()
    logger.info(
        "Starting Financial Resilience Engine",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        app_name=settings.APP_NAME
    )

    # Automatically create tables for local development / testing
    try:
        async with async_engine.begin() as conn:
            # If PostgreSQL, ensure schemas exist
            if settings.ENVIRONMENT != "production" and "postgresql" in str(async_engine.url):
                from sqlalchemy import text
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS core;"))
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS audit;"))
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS transactions;"))
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS shock_mediation;"))
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS predictive_planning;"))
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS behavioral_fraud;"))
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS subscriptions;"))
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS inflation;"))
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS expense_pyramid;"))
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS ai;"))
            
            if settings.ENVIRONMENT != "production":
                await conn.run_sync(Base.metadata.create_all)
            else:
                from sqlalchemy import inspect
                schema = "transactions" if conn.dialect.name == "postgresql" else None
                ready = await conn.run_sync(lambda connection: inspect(connection).has_table("ledger_transactions", schema=schema))
                if not ready:
                    raise RuntimeError("Database migrations must be applied before starting production")
                core_schema='core' if conn.dialect.name=='postgresql' else None
                reminder_columns=await conn.run_sync(lambda connection:{c['name'] for c in inspect(connection).get_columns('notifications',schema=core_schema)})
                if not {'scheduled_for','cancelled'}<=reminder_columns:
                    raise RuntimeError('Apply the scheduled-notification migration before starting production')
            logger.info("Database schemas and relational models synchronized successfully.")
    except Exception as e:
        logger.error("Database initialization failed", error_type=type(e).__name__)
        raise

    worker = None
    if settings.ENABLE_BACKGROUND_JOBS and getattr(app.state,'enable_background_jobs',True):
        from app.engines.jobs import run
        worker = asyncio.create_task(run())
    yield
    if worker:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker

    logger.info("Shutting down Financial Resilience Engine...")
    await async_engine.dispose()

def create_application() -> FastAPI:
    """Factory creating and configuring the FastAPI instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-grade financial resilience, risk detection, shock mediation, and intelligent planning platform.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # 1. Register Global Exception Handlers
    register_exception_handlers(app)

    # 2. Register Middleware (Order matters: outermost first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    # 3. Mount API Routers
    app.include_router(root_health_router) # Mounts /health and /health/ready at root
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(PROJECT_ROOT / "app" / "web"), html=True), name="dashboard")

    return app

app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG, app_dir=str(PROJECT_ROOT))
