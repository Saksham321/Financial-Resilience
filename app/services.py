"""Separately deployable engine APIs backed by the existing shared data model.

Run SERVICE_NAME=<name> uvicorn app.services:create_service --factory.
The main app remains the integrated dashboard. Migrations run centrally first.
"""
import os
from fastapi import FastAPI,APIRouter,Depends,HTTPException
from typing import Annotated
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.api.middleware.error_handler import register_exception_handlers
from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.finance import router as finance_router
from app.api.endpoints.specification import router as specification_router
from app.shared.database.session import get_db

SERVICES={
 'shock':('/shocks/mediate','/finance/shocks','/finance/offers','/finance/scenarios'),
 'predictive':('/predictive-plan','/finance/flows'),
 'fraud':('/finance/transactions','/finance/privacy','/finance/budgets','/finance/vacations','/finance/chargebacks'),
 'subscriptions':('/subscriptions','/finance/subscriptions','/finance/jobs/run'),
 'inflation':('/inflation','/finance/inflation'),
 'pyramid':('/expense-pyramid',),
 'gemini':('/finance/summaries',),
 'voice':('/finance/summaries',),
}


def create_service(name=None):
    name=name or os.environ.get('SERVICE_NAME','shock')
    if name not in SERVICES:
        raise ValueError('Unknown SERVICE_NAME: '+name)
    from app.main import lifespan
    app=FastAPI(title=settings.APP_NAME+' — '+name,version='0.1.0',lifespan=lifespan)
    app.state.enable_background_jobs=name=='subscriptions'
    register_exception_handlers(app);app.add_middleware(CorrelationIdMiddleware)
    app.include_router(auth_router,prefix=settings.API_V1_PREFIX)
    chosen=[]
    for source in (finance_router,specification_router):
        for route in source.routes:
            path=getattr(route,'path','')
            if not any(path==prefix or path.startswith(prefix+'/') for prefix in SERVICES[name]):
                continue
            if name=='gemini' and path.endswith('/audio'):continue
            if name=='voice' and not path.endswith('/audio'):continue
            chosen.append(route)
    app.include_router(APIRouter(routes=chosen),prefix=settings.API_V1_PREFIX)

    @app.get('/health')
    async def health():
        return {'status':'ok','service':name}

    @app.get('/health/ready')
    async def ready(db:Annotated[AsyncSession,Depends(get_db)]):
        try:await db.execute(text('SELECT 1'))
        except Exception as exc:raise HTTPException(503,'Database unavailable') from exc
        return {'status':'HEALTHY','service':name,'architecture':'separate_process_shared_database'}
    return app
