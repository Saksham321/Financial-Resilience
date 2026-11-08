from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select, func
from app.shared.database.datasets import DatasetSourceRecord as Record
from app.engines.models import Transaction
from app.api.endpoints.datasets import DATASET_ID
from app.integrations import providers
from app.integrations.gemini.client import gemini_client


async def seed_reference(db):
    def add(source,key,payload,account_id=None,period=None):
        db.add(Record(dataset_id=DATASET_ID,source=source,record_key=str(key),payload=payload,account_id=account_id,period=period))
    add('accounts',20160,{'account_id':'20160','district_id':'1','frequency':'monthly','account_opened':'2020-01-01'},20160)
    add('districts',1,{'district_id':'1','district_name':'Test district','region':'Test region','average_salary':'5000','unemployment_rate_2023':'3'})
    add('clients',1,{'client_id':'1','district_id':'1','gender':'F','birth_date':'1982-01-01'})
    add('dispositions',1,{'disposition_id':'1','client_id':'1','account_id':'20160','type':'owner'},20160)
    add('standing_orders',1,{'order_id':'1','account_id':'20160','to_bank':'AB','to_account':'12345678','amount':'100','purpose':'household bills'},20160)
    for month in ('2025-10','2025-11','2025-12'):
        add('monthly_summary','20160:'+month,{'account_id':'20160','month':month,'money_in':'1000','money_out':'900',
            'household_bills':'100','insurance':'50','loan_payments':'100','bank_fees':'10',
            'cash_withdrawals_genuine':'400','card_withdrawals':'200','transfers_out_other':'40',
            'month_end_balance':'1300','avg_daily_balance':'1200','days_below_zero':'0'},20160,month)
    for n in range(6):
        add('transactions',n,{'transaction_id':str(n),'account_id':'20160','date':'2025-12-01',
            'amount':'100','signed_amount':'-100','operation':'card withdrawal','partner_bank':'AB','purpose':''},20160,'2025-12-01')
    await db.commit()


@pytest.mark.asyncio
async def test_reference_values_scenarios_and_read_only_state(client,test_db_session,admin_headers):
    await seed_reference(test_db_session)
    response=await client.get('/api/v1/source-review/20160',headers=admin_headers)
    assert response.status_code==200,response.text
    r=response.json();m=r['metrics']
    assert m['typical_income_I']==1000 and m['typical_spending_S']==900
    assert m['typical_fixed_costs_F']==250 and m['savings_buffer_B']==1200
    assert m['baseline_runway_months']=='no shortfall (120+)'
    assert r['shock']['post_shock']['runway_months']==3.4
    assert r['profile']['home_district_name']=='Test district'
    assert r['pyramid']['user_pyramid_amounts']=={'base_cad':250,'middle_cad':0,'peak_cad':240}
    assert len(r['predictive']['forecast']['projections_30_60_90'])==3
    assert r['inflation']['benchmark_cpi_period']=='2025-12'
    assert {s['data_origin'] for s in r['subscriptions']['subscriptions']}=={'recorded_standing_order'}
    assert len(r['subscriptions']['overlap_alerts'])==0
    for scenario in ('FURNACE_REPAIR','LAID_OFF_AND_BILLS_UP','INFLATION_STAGNATION','CUSTOM'):
        response=await client.post('/api/v1/source-review/20160/simulate',headers=admin_headers,json={'scenario_id':scenario,'one_off_costs':200})
        assert response.status_code==200,response.text
    assert (await client.post('/api/v1/source-review/20160/simulate',headers=admin_headers,json={'income_reduction_pct':2})).status_code==422
    assert (await client.get('/api/v1/source-review/999',headers=admin_headers)).status_code==404
    assert await test_db_session.scalar(select(func.count()).select_from(Transaction))==0


@pytest.mark.asyncio
async def test_reference_fraud_manual_context_vacation_and_external_gates(client,test_db_session,monkeypatch,admin_headers):
    await seed_reference(test_db_session)
    body={'amount':5000,'merchant_name':'New merchant','is_new_store':True,'is_outside_normal_location':True,'chargebacks_count':0}
    high=(await client.post('/api/v1/source-review/20160/fraud',headers=admin_headers,json=body)).json()
    assert high['is_flagged'] is True
    travel=(await client.post('/api/v1/source-review/20160/fraud',headers=admin_headers,json={**body,'vacation_mode':True})).json()
    assert travel['anomaly_score']<high['anomaly_score']
    assert any(f['factor']=='CART_MAGNITUDE_Z_SCORE' for f in travel['scoring_breakdown'])
    ai=AsyncMock();voice=AsyncMock()
    monkeypatch.setattr(gemini_client,'generate_structured_response',ai)
    monkeypatch.setattr(providers,'speech',voice)
    summary=await client.post('/api/v1/source-review/20160/briefing',headers=admin_headers,json={})
    assert summary.status_code==200 and summary.json()['source']=='DETERMINISTIC_LOCAL_MODEL'
    assert (await client.post('/api/v1/source-review/20160/audio',headers=admin_headers,json={})).status_code==403
    ai.assert_not_called();voice.assert_not_called()
