from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
from unittest.mock import AsyncMock
import base64
import httpx
import pytest
from sqlalchemy import select
from app.engines.models import Notification,Transaction,Offer,Subscription
from app.engines.schemas import Narrative
from app.engines.calculations import add_months
from app.core.config import settings
from app.engines import jobs
from app.integrations import providers
from app.integrations.gemini.client import gemini_client
from test_financial_api import register,account,transaction,post
from test_reference_review import seed_reference
from contextlib import asynccontextmanager


@pytest.mark.asyncio
async def test_exact_mediation_contract_and_no_unaffordable_proposals(client,test_db_session,monkeypatch):
    h=await register(client);await account(client,h,'10')
    monkeypatch.setattr(settings,'BANKING_API_URL',None)
    monkeypatch.setattr(settings,'INSTALLMENT_ANNUAL_RATE',8.5)
    monkeypatch.setattr(settings,'INSTALLMENT_FEE',30)
    monkeypatch.setattr(providers,'underwriting',AsyncMock(return_value={'eligible':False,'product':'none','reference':'fixture','approved_amount':0}))
    r=await client.post('/api/v1/shocks/mediate',headers={**h,'Idempotency-Key':'repair-1'},json={'shock_amount':'100','shock_type':'EMERGENCY_EXPENSE'})
    assert r.status_code==200,r.text
    assert r.json()['status']=='SHORTFALL_DETECTED' and r.json()['shortfall_amount']=='90.00'
    assert r.json()['installment_proposal']=={'eligible':False,'plans':[]}
    assert (await test_db_session.scalars(select(Offer))).all()==[]
    again=await client.post('/api/v1/shocks/mediate',headers={**h,'Idempotency-Key':'repair-1'},json={'shock_amount':'100'})
    assert again.json()['shock_id']==r.json()['shock_id']
    other=await register(client,'other-contract@example.com')
    response=await client.get('/api/v1/auth/me',headers=other)
    assert (await client.post('/api/v1/shocks/mediate',headers=h,json={'user_id':response.json()['id'],'shock_amount':1})).status_code==403


@pytest.mark.asyncio
async def test_fraud_uses_rolling_90_days_and_keeps_lifetime_recurring_history(client):
    h=await register(client);a=await account(client,h)
    await post(client,'transactions',h,transaction(a,'ancient',amount='-100000',merchant='Ancient',occurred_at=(datetime.now(timezone.utc)-timedelta(days=100)).isoformat()))
    current=await post(client,'transactions',h,transaction(a,'recent'))
    assert current['fraud']['baseline_window_days']==90
    assert current['fraud']['baseline_transaction_count']==0
    assert current['fraud']['score']=='0.500000'


@pytest.mark.asyncio
async def test_browsing_adapter_uses_fuzzy_category_match(monkeypatch):
    at=datetime.now(timezone.utc)
    mock=AsyncMock(return_value=httpx.Response(200,json={'matches':[{'category':'grocerie','viewed_at':at.isoformat()}]}))
    monkeypatch.setattr(providers,'adapter',mock)
    assert await providers.browsing('fixture','groceries',at) is True


@pytest.mark.asyncio
async def test_billing_reminder_is_durable_future_dated_and_cancelled(client,test_db_session):
    h=await register(client);a=await account(client,h)
    due=date.today()+timedelta(days=10)
    for i,day in enumerate((add_months(due,-2),add_months(due,-1))):
        await post(client,'transactions',h,transaction(a,str(i),merchant='Stream',category='STREAMING_VIDEO',
            occurred_at=datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc).isoformat()))
    notices=(await test_db_session.scalars(select(Notification).where(Notification.dedupe_key.like('billing:%')))).all()
    assert len(notices)==1
    notice=notices[0]
    assert notice.scheduled_for.date()==due-timedelta(days=3)
    dashboard=(await client.get('/api/v1/finance/dashboard',headers=h)).json()
    assert not any(n['dedupe_key'].startswith('billing:') for n in dashboard['notifications'])
    contract=(await client.get('/api/v1/subscriptions',headers=h)).json()[0]
    assert contract['cadence']=='MONTHLY' and contract['notification_scheduled_for']==(due-timedelta(days=3)).isoformat()
    await client.patch('/api/v1/finance/subscriptions/'+contract['id'],headers=h,json={'status':'cancelled'})
    await test_db_session.refresh(notice)
    assert notice.cancelled is True


@pytest.mark.asyncio
async def test_personal_gemini_summary_automatically_hands_final_text_to_voice(client,monkeypatch):
    h=await register(client);await account(client,h,'1000')
    await client.put('/api/v1/finance/privacy',headers=h,json={'ai_consent':True})
    narrative=Narrative(introduction="Let's review your verified financial picture together.",metric_keys=['liquidity'],recommendation_ids=[],
        closing='Review the assumptions and upcoming commitments before making changes.',generated_summary='Your available buffer is 1000 CAD.')
    monkeypatch.setattr(gemini_client,'generate_structured_response',AsyncMock(return_value=narrative))
    voice=AsyncMock(return_value=b'ID3-fixture');monkeypatch.setattr(providers,'speech',voice)
    response=await client.post('/api/v1/finance/summaries',headers=h,json={'generate_audio':True,'voice_profile':'empathetic'})
    assert response.status_code==201,response.text
    summary=response.json()
    assert summary['audio_available'] is True and summary['audio_status']['status']=='generated'
    voice.assert_awaited_once_with(summary['text'],'empathetic')
    audio=await client.get('/api/v1/finance/summaries/'+summary['id']+'/audio',headers=h)
    assert audio.content==b'ID3-fixture'
    narrative.generated_summary='Your guaranteed buffer is 99999 CAD.'
    assert (await client.post('/api/v1/finance/summaries',headers=h,json={})).status_code==502


@pytest.mark.asyncio
async def test_source_gemini_context_and_automatic_voice_are_consent_gated(client,test_db_session,monkeypatch,admin_headers):
    await seed_reference(test_db_session)
    narrative=Narrative(introduction="Let's review your verified financial picture together.",metric_keys=['scenario'],recommendation_ids=[],
        closing='Review the assumptions and upcoming commitments before making changes.',generated_summary='Let us review your selected scenario together.')
    ai=AsyncMock(return_value=narrative);voice=AsyncMock(return_value=b'ID3-fixture')
    monkeypatch.setattr(gemini_client,'generate_structured_response',ai);monkeypatch.setattr(providers,'speech',voice)
    response=await client.post('/api/v1/source-review/20160/briefing',headers=admin_headers,json={'allow_external_processing':True,'generate_audio':True})
    assert response.status_code==200,response.text
    body=response.json()
    assert base64.b64decode(body['audio_base64'])==b'ID3-fixture'
    assert body['source']=='GEMINI_GENERATED_GROUNDED'
    assert all(key in ai.call_args.args[0] for key in ('predictive','pyramid','mediation'))
    voice.assert_awaited_once_with(body['summary_text'],'professional')


@pytest.mark.asyncio
async def test_mediation_syncs_banking_and_serializes_affordable_plan_contract(client,monkeypatch):
    h=await register(client);a=await account(client,h,'100')
    await client.put('/api/v1/finance/flows',headers=h,json={'external_id':'income','name':'Income','category':'income',
        'amount':'2000','due_date':(date.today()+timedelta(days=1)).isoformat(),'recurrence':'monthly'})
    monkeypatch.setattr(settings,'BANKING_API_URL','https://bank.fixture')
    monkeypatch.setattr(settings,'BANKING_API_KEY','fixture')
    monkeypatch.setattr(settings,'INSTALLMENT_ANNUAL_RATE',12)
    monkeypatch.setattr(settings,'INSTALLMENT_FEE',5)
    snapshot={'local_account_id':a,'snapshot':{'institution_name':'Bank fixture','account_type':'CHECKING',
        'masked_account_number':'****1234','current_balance':'100','available_balance':'100'}}
    banking=AsyncMock(return_value=httpx.Response(200,json={'accounts':[snapshot],'transactions':[]}))
    monkeypatch.setattr(providers,'adapter',banking)
    monkeypatch.setattr(providers,'underwriting',AsyncMock(return_value={'eligible':False,'product':'none','reference':'fixture','approved_amount':0}))
    response=await client.post('/api/v1/shocks/mediate',headers=h,json={'shock_amount':400})
    assert response.status_code==200,response.text
    result=response.json()
    assert result['banking_source']=='banking_provider_snapshot'
    assert result['installment_proposal']['eligible'] is True
    plans=result['installment_proposal']['plans']
    assert {p['term_months'] for p in plans}=={3,6,12}
    assert all(Decimal(p['monthly_installment'])>0 and Decimal(p['apr'])>12 and p['annual_interest_rate_percent']=='12' for p in plans)
    assert banking.call_args.args[0]=='BANKING'


@pytest.mark.asyncio
async def test_predictive_contract_requires_six_completed_months_and_groups_spending(client):
    h=await register(client);a=await account(client,h)
    assert (await client.post('/api/v1/predictive-plan',headers=h,json={})).status_code==422
    for n in range(1,7):
        day=add_months(date.today().replace(day=1),-n)
        for kind,amount,category in (('income','1000','income'),('expense','-500','groceries')):
            await post(client,'transactions',h,transaction(a,f'{kind}-{n}',amount=amount,merchant=kind,category=category,
                occurred_at=datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc).isoformat()))
    response=await client.post('/api/v1/predictive-plan',headers=h,json={'window_months':6})
    assert response.status_code==200,response.text
    result=response.json()
    assert result['spending_breakdown']['essential_monthly']=='500.00'
    assert set(result['forecast']['projections_30_60_90'])=={'30','60','90'}


@pytest.mark.asyncio
async def test_delivery_worker_waits_until_persisted_three_day_due_time(client,test_db_session,monkeypatch):
    h=await register(client);a=await account(client,h,'1000')
    due=date.today()+timedelta(days=10)
    for n,day in enumerate((add_months(due,-2),add_months(due,-1))):
        await post(client,'transactions',h,transaction(a,f'recurring-{n}',merchant='Streaming fixture',category='streaming',
            occurred_at=datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc).isoformat()))
    @asynccontextmanager
    async def factory():yield test_db_session
    monkeypatch.setattr(jobs,'AsyncSessionLocal',factory)
    monkeypatch.setattr(settings,'NOTIFICATION_API_URL','https://push.fixture')
    monkeypatch.setattr(settings,'NOTIFICATION_API_KEY','fixture')
    sender=AsyncMock(return_value=httpx.Response(200,json={'delivered':True}))
    monkeypatch.setattr(jobs,'adapter',sender)
    await jobs.tick();sender.assert_not_awaited()
    class DueClock(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.combine(due-timedelta(days=3),datetime.min.time(),tzinfo=timezone.utc)
    monkeypatch.setattr(jobs,'datetime',DueClock)
    await jobs.tick();sender.assert_awaited_once()
    await jobs.tick();sender.assert_awaited_once()
