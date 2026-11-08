from datetime import datetime, date, timezone, timedelta
from decimal import Decimal as D
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from app.engines.models import Transaction, ScheduledFlow, CPI, Offer
from app.engines import service
from app.core.config import settings
from app.integrations import providers
from app.engines.calculations import add_months


async def register(client,email='engine@example.com'):
    r=await client.post('/api/v1/auth/register',json={'email':email,'password':'StrongPassword123!','first_name':'Alex','last_name':'Lee'})
    assert r.status_code==201,r.text
    return {'Authorization':'Bearer '+r.json()['access_token']}


async def account(client,h,balance='1000'):
    r=await client.post('/api/v1/finance/accounts',headers=h,json={'institution_name':'Manual bank snapshot','account_type':'CHECKING','masked_account_number':'****1234','current_balance':balance,'available_balance':balance})
    assert r.status_code==201,r.text
    return r.json()['id']


def transaction(a,ref='tx1',**kwargs):
    return {'account_id':a,'external_id':ref,'occurred_at':(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),'amount':'-20.00','merchant':'New shop','category':'entertainment',**kwargs}


async def post(client,path,h,body,status=201):
    r=await client.post('/api/v1/finance/'+path,headers=h,json=body)
    assert r.status_code==status,r.text
    return r.json()


@pytest.mark.asyncio
async def test_empty_dashboard_and_auth(client):
    assert (await client.get('/api/v1/finance/dashboard')).status_code==401
    h=await register(client)
    r=await client.get('/api/v1/finance/dashboard',headers=h)
    assert r.status_code==200,r.text
    assert r.json()['forecast']['balance']=='0.00'
    assert r.json()['pyramid']['deformity_score'] is None
    p=(await client.get('/api/v1/finance/privacy',headers=h)).json()
    assert not p['ai_consent'] and not p['browsing_consent'] and not p['geolocation_consent']


@pytest.mark.asyncio
async def test_ingest_duplicate_and_snapshot_not_double_applied(client,test_db_session,monkeypatch):
    h=await register(client);a=await account(client,h)
    spy=AsyncMock();monkeypatch.setattr(providers,'browsing',spy)
    payload=transaction(a)
    first=await post(client,'transactions',h,payload)
    second=await post(client,'transactions',h,payload)
    assert first['id']==second['id']
    assert first['fraud']['score']=='0.500000'
    spy.assert_not_called()
    assert len((await client.get('/api/v1/finance/transactions',headers=h)).json())==1
    d=(await client.get('/api/v1/finance/dashboard',headers=h)).json()
    assert d['forecast']['balance']=='1000.00'
    r=await client.post('/api/v1/finance/transactions',headers=h,json={**payload,'amount':'-21'})
    assert r.status_code==422


@pytest.mark.asyncio
async def test_cross_user_access(client):
    h1=await register(client);a=await account(client,h1)
    h2=await register(client,'other@example.com')
    assert (await client.post('/api/v1/finance/transactions',headers=h2,json=transaction(a))).status_code==404
    assert (await client.get('/api/v1/finance/accounts',headers=h2)).json()==[]
    assert (await client.put('/api/v1/finance/accounts/'+a,headers=h2,json={'institution_name':'Bank','account_type':'CHECKING','masked_account_number':'1234','current_balance':0,'available_balance':0})).status_code==404


@pytest.mark.asyncio
async def test_geo_consent_vacation_and_fraud_continues(client):
    h=await register(client);a=await account(client,h)
    payload=transaction(a,latitude='48.85',longitude='2.35')
    assert (await client.post('/api/v1/finance/transactions',headers=h,json=payload)).status_code==422
    geo={'geolocation_consent':True,'latitude':'43.65','longitude':'-79.38','radius_km':50}
    assert (await client.put('/api/v1/finance/privacy',headers=h,json=geo)).status_code==200
    v=await post(client,'vacations',h,{'destination':'Paris','start_date':date.today().isoformat(),'end_date':(date.today()+timedelta(days=7)).isoformat(),'budget':'100','latitude':'48.85','longitude':'2.35'})
    t=await post(client,'transactions',h,payload)
    assert t['vacation_id']==v['id']
    assert t['fraud']['score']=='0.500000'
    assert all(r['rule']!='outside_area' for r in t['fraud']['reasons'])
    trip=(await client.get('/api/v1/finance/vacations',headers=h)).json()[0]
    assert trip['total_spent']=='20.00' and trip['remaining_budget']=='80.00'
    assert len(trip['transactions'])==1
    await client.put('/api/v1/finance/privacy',headers=h,json={'geolocation_consent':False})
    txs=(await client.get('/api/v1/finance/transactions',headers=h)).json()
    assert txs[0]['latitude'] is None
    trip=(await client.get('/api/v1/finance/vacations',headers=h)).json()[0]
    assert not trip['enabled'] and 'latitude' not in trip


@pytest.mark.asyncio
async def test_combined_fraud_adjustments_and_browsing_permission(client,monkeypatch):
    h=await register(client);a=await account(client,h)
    await client.put('/api/v1/finance/privacy',headers=h,json={'geolocation_consent':True,'browsing_consent':True,'latitude':43,'longitude':-79})
    monkeypatch.setattr(providers,'browsing',AsyncMock(return_value=True))
    for i in range(2):
        await post(client,'chargebacks',h,{'external_id':str(i),'reported_on':date.today().isoformat(),'merchant':'another'})
    await client.put('/api/v1/finance/budgets',headers=h,json={'category':'entertainment','monthly_amount':10})
    t=await post(client,'transactions',h,transaction(a,latitude='0',longitude='0'))
    assert t['fraud']['score']=='0.900000' # .50 - .15 + .20 + .25 + .10
    assert t['fraud']['elevated_review'] and not t['fraud']['confirmed_fraud']


@pytest.mark.asyncio
async def test_subscription_detection_notification_dedup(client):
    h=await register(client);a=await account(client,h)
    # Last payment one month ago; upcoming payment in two days.
    due=date.today()+timedelta(days=2)
    last=add_months(due,-1);previous=add_months(last,-1)
    for i,day in enumerate([previous,last]):
        await post(client,'transactions',h,transaction(a,str(i),occurred_at=datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc).isoformat(),merchant='Stream',category='streaming'))
    d=(await client.get('/api/v1/finance/dashboard',headers=h)).json()
    assert len(d['subscriptions'])==1
    billing=[n for n in d['notifications'] if n['dedupe_key'].startswith('billing:')]
    assert len(billing)==1
    for _ in range(2):
        await client.post('/api/v1/finance/jobs/run',headers=h)
    again=(await client.get('/api/v1/finance/dashboard',headers=h)).json()
    assert len([n for n in again['notifications'] if n['dedupe_key'].startswith('billing:')])==1
    sub=d['subscriptions'][0]
    assert (await client.patch('/api/v1/finance/subscriptions/'+sub['id'],headers=h,json={'status':'cancelled'})).status_code==200
    again=(await client.get('/api/v1/finance/dashboard',headers=h)).json()
    assert again['subscriptions'][0]['status']=='cancelled'


@pytest.mark.asyncio
async def test_shock_unknown_credit_never_invents_denial(client,monkeypatch):
    monkeypatch.setattr(settings,'UNDERWRITING_API_URL',None)
    h=await register(client);await account(client,h,'10')
    s=await post(client,'shocks',h,{'external_id':'shock','name':'Repair','amount':'100','due_date':date.today().isoformat()})
    assert s['shortfall']=='90.00' and s['routing']['status']=='eligibility_unknown'
    d=(await client.get('/api/v1/finance/dashboard',headers=h)).json()
    assert d['offers']==[]


@pytest.mark.asyncio
async def test_offer_explicit_acceptance_exact_schedule_and_idempotency(client,test_db_session,monkeypatch):
    monkeypatch.setattr(settings,'INSTALLMENT_ANNUAL_RATE',12)
    monkeypatch.setattr(settings,'INSTALLMENT_FEE',5)
    monkeypatch.setattr(providers,'underwriting',AsyncMock(return_value={'eligible':False,'product':'none','reference':'tested','approved_amount':0}))
    h=await register(client);await account(client,h,'100')
    await client.put('/api/v1/finance/flows',headers=h,json={'external_id':'salary','name':'Income','category':'income','amount':'2000','due_date':(date.today()+timedelta(days=1)).isoformat(),'recurrence':'monthly'})
    s=await post(client,'shocks',h,{'external_id':'shock','name':'Repair','amount':'400','due_date':date.today().isoformat()})
    d=(await client.get('/api/v1/finance/dashboard',headers=h)).json()
    assert len(d['offers'])==3
    offer=d['offers'][0]
    assert offer['terms']['principal']=='300.00'
    assert (await client.post('/api/v1/finance/offers/'+offer['id']+'/decision',headers=h,json={'decision':'accepted'})).status_code==422
    accepted=await post(client,'offers/'+offer['id']+'/decision',h,{'decision':'accepted','confirm_obligation':True},200)
    assert accepted['status']=='accepted'
    await post(client,'offers/'+offer['id']+'/decision',h,{'decision':'accepted','confirm_obligation':True},200)
    flows=(await client.get('/api/v1/finance/flows',headers=h)).json()
    repayments=[f for f in flows if f['external_id'].startswith('offer:') and not f['external_id'].endswith('funding')]
    assert len(repayments)==offer['months']
    assert sum(-D(f['amount']) for f in repayments)==D(offer['terms']['total_repayment'])
    assert sum(o.status=='accepted' for o in (await test_db_session.scalars(select(Offer))).all())==1


@pytest.mark.asyncio
@pytest.mark.parametrize('body',[
    {'latitude':1}, {'amount':'0'}, {'amount':'NaN'}, {'occurred_at':'2026-01-01T00:00:00'},
    {'occurred_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}, {'latitude':91,'longitude':0}])
async def test_invalid_transactions(client,body):
    h=await register(client);a=await account(client,h)
    r=await client.post('/api/v1/finance/transactions',headers=h,json=transaction(a,**body))
    assert r.status_code==422,r.text


@pytest.mark.asyncio
async def test_ai_consent_and_missing_credentials(client,monkeypatch):
    h=await register(client)
    assert (await client.post('/api/v1/finance/summaries',headers=h,json={})).status_code==403
    await client.put('/api/v1/finance/privacy',headers=h,json={'ai_consent':True})
    monkeypatch.setattr(settings,'GEMINI_API_KEY',None)
    assert (await client.post('/api/v1/finance/summaries',headers=h,json={})).status_code==502


@pytest.mark.asyncio
async def test_static_frontend_served(client):
    r=await client.get('/')
    assert r.status_code==200 and 'Financial Resilience' in r.text
    assert (await client.get('/app.js')).status_code==200


@pytest.mark.asyncio
async def test_scenario_is_deterministic_and_does_not_create_obligations(client):
    h=await register(client);await account(client,h,'1000')
    result=await post(client,'scenarios',h,{'amount':'250','due_date':(date.today()+timedelta(days=2)).isoformat()},200)
    assert result['baseline']['projections']['30']=='1000.00'
    assert result['scenario']['projections']['30']=='750.00'
    assert not result['persisted']
    assert (await client.get('/api/v1/finance/flows',headers=h)).json()==[]


@pytest.mark.asyncio
async def test_recurring_merchant_updates_cumulative_familiarity(client):
    h=await register(client);a=await account(client,h)
    for i,months in enumerate([-3,-2,-1]):
        day=add_months(date.today().replace(day=1),months)
        result=await post(client,'transactions',h,transaction(a,str(i),occurred_at=datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc).isoformat()))
        assert D(result['fraud']['score'])==D('.50')*D('.90')**i
        assert result['fraud']['merchant_history_count']==i


@pytest.mark.asyncio
async def test_cpi_refresh_persists_and_upserts(client,test_db_session,monkeypatch):
    h=await register(client)
    monkeypatch.setattr(providers,'fetch_cpi',AsyncMock(return_value=[('2026-01',D('160.2'))]))
    for _ in range(2):
        assert (await client.post('/api/v1/finance/inflation/refresh',headers=h)).status_code==200
    observations=(await test_db_session.scalars(select(CPI))).all()
    assert len(observations)==1 and observations[0].value==D('160.2')


@pytest.mark.asyncio
async def test_banking_sync_validates_ownership_and_deduplicates_events(client,monkeypatch):
    import httpx
    h=await register(client);a=await account(client,h,'1000')
    snapshot={'institution_name':'Verified test adapter','account_type':'CHECKING','masked_account_number':'****1234','current_balance':'500','available_balance':'500','currency':'CAD'}
    payload={'accounts':[{'local_account_id':a,'snapshot':snapshot}],'transactions':[transaction(a)]}
    provider=AsyncMock(return_value=httpx.Response(200,json=payload))
    monkeypatch.setattr(providers,'adapter',provider)
    for _ in range(2):
        assert (await client.post('/api/v1/finance/banking/sync',headers=h)).status_code==200
    assert len((await client.get('/api/v1/finance/transactions',headers=h)).json())==1
    assert (await client.get('/api/v1/finance/accounts',headers=h)).json()[0]['available_balance']=='500.00'
    other=await register(client,'bank-other@example.com');other_account=await account(client,other)
    provider.return_value=httpx.Response(200,json={**payload,'accounts':[{'local_account_id':other_account,'snapshot':snapshot}]})
    assert (await client.post('/api/v1/finance/banking/sync',headers=h)).status_code==404


@pytest.mark.asyncio
async def test_vacation_associates_existing_consented_transactions(client):
    h=await register(client);a=await account(client,h)
    await client.put('/api/v1/finance/privacy',headers=h,json={'geolocation_consent':True})
    await post(client,'transactions',h,transaction(a,latitude='48.85',longitude='2.35'))
    v=await post(client,'vacations',h,{'destination':'Paris','start_date':(date.today()-timedelta(days=1)).isoformat(),'end_date':(date.today()+timedelta(days=1)).isoformat(),'budget':'100','latitude':'48.85','longitude':'2.35'})
    assert v['total_spent']=='20.00' and len(v['transactions'])==1
