import logging
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from app.core.exceptions import ExternalServiceError
from app.core.logging import FinancialAccessFilter
from app.shared.database.models import User
from app.shared.database.datasets import DatasetSourceRecord as Record
from app.integrations.gemini.client import gemini_client
from app.integrations import providers
from test_financial_api import register
from test_reference_review import seed_reference

@pytest.mark.asyncio
async def test_historical_information_does_not_require_a_password(client,test_db_session):
    from app.shared.database.datasets import DatasetAccount
    from app.api.endpoints.datasets import DATASET_ID
    await seed_reference(test_db_session)
    test_db_session.add(DatasetAccount(dataset_id=DATASET_ID,account_id=20160,payload={'account_id':20160}))
    await test_db_session.commit()
    for path in ('datasets/overview','datasets/accounts?account_id=20160','datasets/accounts/20160','datasets/accounts/20160/transactions','source-review/20160'):
        assert (await client.get('/api/v1/'+path)).status_code==200
    assert (await client.post('/api/v1/source-review/20160/simulate',json={})).status_code==200
    assert (await client.post('/api/v1/source-review/20160/briefing',json={})).status_code==200
    response=await client.get('/api/v1/source-review/20160')
    assert response.headers['cache-control']=='no-store'
    assert response.json()['mediation']['shortfall_amount']>0
    assert any(n['id']=='scenario-shortfall' for n in response.json()['subscriptions']['notifications'])
    assert (await client.get('/api/v1/finance/dashboard')).status_code==401
    assert (await client.get('/api/v1/system/metrics')).status_code==401

@pytest.mark.asyncio
async def test_incomplete_source_history_withholds_financial_values(client,test_db_session,admin_headers):
    await seed_reference(test_db_session)
    records=(await test_db_session.scalars(select(Record).where(Record.source=='monthly_summary'))).all()
    for record in records:
        payload=dict(record.payload);payload.pop('month_end_balance');record.payload=payload
    await test_db_session.commit()
    response=await client.get('/api/v1/source-review/20160',headers=admin_headers)
    assert response.status_code==200
    r=response.json()
    assert r['availability']['financial_history'] is False and r['metrics'] is None and r['pyramid'] is None
    assert 'No financial estimates' in r['briefing']['summary_text']

@pytest.mark.asyncio
async def test_gemini_failure_returns_local_summary_without_voice(client,test_db_session,admin_headers,monkeypatch):
    await seed_reference(test_db_session)
    monkeypatch.setattr(gemini_client,'generate_structured_response',AsyncMock(side_effect=ExternalServiceError('Provider unavailable')))
    voice=AsyncMock();monkeypatch.setattr(providers,'speech',voice)
    response=await client.post('/api/v1/source-review/20160/briefing',headers=admin_headers,json={'allow_external_processing':True,'generate_audio':True})
    assert response.status_code==200
    assert response.json()['source']=='DETERMINISTIC_LOCAL_MODEL' and 'Provider unavailable' in response.json()['external_error']
    voice.assert_not_awaited()


def test_access_log_filter_redacts_ids_and_queries():
    record=logging.LogRecord('uvicorn.access',20,'',1,'%s %s',('/api/v1/source-review/20160/simulate','/api/v1/datasets/accounts?account_id=20160'),None)
    assert FinancialAccessFilter().filter(record)
    assert '20160' not in record.getMessage() and 'account_id' not in record.getMessage()

@pytest.mark.asyncio
async def test_personal_runway_alert_retires_when_balance_recovers(client,test_db_session):
    from test_financial_api import account
    from app.engines.models import Notification
    h=await register(client)
    a=await account(client,h,'0')
    first=(await client.get('/api/v1/finance/dashboard',headers=h)).json()
    assert any(n['dedupe_key'].startswith('runway:') for n in first['notifications'])
    await client.put('/api/v1/finance/accounts/'+a,headers=h,json={'institution_name':'Recovered snapshot','account_type':'CHECKING',
        'masked_account_number':'****1234','current_balance':'1000','available_balance':'1000'})
    recovered=(await client.get('/api/v1/finance/dashboard',headers=h)).json()
    assert not any(n['dedupe_key'].startswith('runway:') for n in recovered['notifications'])
    notices=(await test_db_session.scalars(select(Notification).where(Notification.dedupe_key.like('runway:%')))).all()
    assert notices and all(n.cancelled for n in notices)
