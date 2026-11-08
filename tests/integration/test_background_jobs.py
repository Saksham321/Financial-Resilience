from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from sqlalchemy import select
import httpx
import pytest
from app.engines import jobs
from app.engines.models import Notification
from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from test_financial_api import register


@pytest.mark.asyncio
async def test_worker_durable_delivery_retry_and_dedup(client,test_db_session,monkeypatch):
    h=await register(client)
    await client.get('/api/v1/finance/dashboard',headers=h)  # zero-liquidity notification
    @asynccontextmanager
    async def factory():
        yield test_db_session
    monkeypatch.setattr(jobs,'AsyncSessionLocal',factory)
    monkeypatch.setattr(settings,'NOTIFICATION_API_URL','https://test.invalid')
    monkeypatch.setattr(settings,'NOTIFICATION_API_KEY','test-key')
    sender=AsyncMock(side_effect=ExternalServiceError('test provider unavailable'))
    monkeypatch.setattr(jobs,'adapter',sender)
    await jobs.tick()
    n=await test_db_session.scalar(select(Notification))
    assert n.delivery_status=='failed_retry_pending'
    sender.side_effect=None
    sender.return_value=httpx.Response(200,json={'delivered':True})
    await jobs.tick()
    assert n.delivery_status=='delivered'
    calls=sender.call_count
    await jobs.tick()
    assert sender.call_count==calls
    assert len((await test_db_session.scalars(select(Notification))).all())==1
