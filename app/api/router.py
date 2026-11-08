"""
Unified API v1 Router
Aggregates all domain engine routes into the versioned API tree
"""

from fastapi import APIRouter
from app.api.endpoints.health import router as health_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.finance import router as finance_router

api_v1_router = APIRouter()

# Core & Infrastructure
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(finance_router)

# Engine Routers will be mounted here in subsequent phases:
# - shock_mediation
# - predictive_planning
# - behavioral_fraud
# - subscription_manager
# - inflation_tracker
# - expense_pyramid
# - ai_orchestration
# - resilience_score
# - voice
