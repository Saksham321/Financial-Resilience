"""
Unified API v1 Router
Aggregates all domain engine routes into the versioned API tree
"""

from fastapi import APIRouter
from typing import Annotated
from fastapi import Depends
from app.core.dependencies import require_role
from app.core.metrics import system_metrics
from app.shared.database.models import User
from app.api.endpoints.health import router as health_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.finance import router as finance_router
from app.api.endpoints.datasets import router as dataset_router
from app.api.endpoints.reference_review import router as reference_router

api_v1_router = APIRouter()

# Core & Infrastructure
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(finance_router)
api_v1_router.include_router(dataset_router)
api_v1_router.include_router(reference_router)

@api_v1_router.get("/system/metrics", tags=["Health & Diagnostics"])
async def generate_system_metrics(user: Annotated[User, Depends(require_role("admin"))]):
    return system_metrics.snapshot()
