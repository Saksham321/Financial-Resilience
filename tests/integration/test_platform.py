from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from app.core.config import settings
from app.core.metrics import SystemMetrics
from app.engines.models import Summary
from app.engines.platform import publish_financial_event, consume_financial_events, manage_data_retention
from app.engines.service import lock_user
from app.shared.database.models import User, AuditLog
from test_financial_api import register


@pytest.mark.asyncio
async def test_events_durable_owner_scoped_and_idempotent(client, test_db_session):
    await register(client)
    await register(client, 'other@example.com')
    users = (await test_db_session.scalars(select(User))).all()
    uid, other = users[0].id, users[1].id
    await lock_user(test_db_session, uid)
    first = await publish_financial_event(test_db_session, uid, 'one', 'balance_changed')
    assert (await publish_financial_event(test_db_session, uid, 'one', 'balance_changed')).id == first.id
    await publish_financial_event(test_db_session, other, 'one', 'balance_changed')
    assert await consume_financial_events(test_db_session, uid) == 1
    assert await consume_financial_events(test_db_session, uid) == 0
    assert await consume_financial_events(test_db_session, other) == 1
    await test_db_session.commit()
    assert len((await test_db_session.scalars(select(AuditLog).where(
        AuditLog.event_type == 'FINANCIAL_EVENT_PROCESSED'))).all()) == 2
    await publish_financial_event(test_db_session, uid, 'rolled-back', 'balance_changed')
    await test_db_session.rollback()
    assert await consume_financial_events(test_db_session, uid) == 0


@pytest.mark.asyncio
async def test_retention_disabled_by_default_and_owner_scoped(client, test_db_session, monkeypatch):
    h = await register(client)
    await register(client, 'other@example.com')
    users = (await test_db_session.scalars(select(User))).all()
    now = datetime.now(timezone.utc)
    old = Summary(user_id=users[0].id, metrics={}, text='expired', audio=b'private', created_at=now-timedelta(days=31))
    recent = Summary(user_id=users[0].id, metrics={}, text='recent', created_at=now)
    foreign = Summary(user_id=users[1].id, metrics={}, text='foreign', created_at=now-timedelta(days=31))
    test_db_session.add_all([old, recent, foreign])
    await test_db_session.commit()
    recent_id, foreign_id = recent.id, foreign.id
    monkeypatch.setattr(settings, 'SUMMARY_RETENTION_DAYS', 0)
    assert await manage_data_retention(test_db_session, users[0].id, now) == 0
    monkeypatch.setattr(settings, 'SUMMARY_RETENTION_DAYS', 30)
    assert await manage_data_retention(test_db_session, users[0].id, now) == 1
    await test_db_session.commit()
    remaining = (await client.get('/api/v1/finance/summaries', headers=h)).json()
    assert [s['text'] for s in remaining] == ['recent']
    assert (await client.delete(f'/api/v1/finance/summaries/{foreign_id}', headers=h)).status_code == 404
    assert (await client.delete(f'/api/v1/finance/summaries/{recent_id}', headers=h)).status_code == 204
    assert (await client.get(f'/api/v1/finance/summaries/{recent_id}/audio', headers=h)).status_code == 404


@pytest.mark.asyncio
async def test_metrics_admin_only_and_route_templates(client, test_db_session):
    assert (await client.get('/api/v1/system/metrics')).status_code == 401
    h = await register(client)
    assert (await client.get('/api/v1/system/metrics', headers=h)).status_code == 403
    user = await test_db_session.scalar(select(User))
    user.role = 'admin'
    await test_db_session.commit()
    response = await client.get('/api/v1/system/metrics', headers=h)
    assert response.status_code == 200
    assert response.json()['requests_total'] > 0
    assert response.json()['scope'] == 'current_process_since_start'
    assert 'example.com' not in response.text
    metrics = SystemMetrics()
    metrics.observe('GET', '/items/{id}', 200, 0.25)
    metrics.observe('GET', '/items/{id}', 500, 0.5)
    assert metrics.snapshot()['request_duration_seconds_total'] == 0.75
