from unittest.mock import AsyncMock
import pytest
from app.engines.schemas import Narrative
from app.integrations.gemini.client import gemini_client
from app.integrations import providers
from test_financial_api import register,account
from datetime import date


@pytest.mark.asyncio
async def test_verified_summary_voice_and_owner_protection(client,monkeypatch):
    h=await register(client);await account(client,h,'1234.56')
    await client.put('/api/v1/finance/privacy',headers=h,json={'ai_consent':True})
    result=Narrative(introduction="Let's review your verified financial picture together.",metric_keys=['liquidity','balance_30'],recommendation_ids=[0],closing='Review the assumptions and upcoming commitments before making changes.')
    monkeypatch.setattr(gemini_client,'generate_structured_response',AsyncMock(return_value=result))
    r=await client.post('/api/v1/finance/summaries',headers=h,json={})
    assert r.status_code==201,r.text
    summary=r.json()
    assert '1234.56' in summary['text']
    monkeypatch.setattr(providers,'speech',AsyncMock(return_value=b'ID3-test-fixture'))
    r=await client.post('/api/v1/finance/summaries/'+summary['id']+'/audio',headers=h,json={'profile':'professional'})
    assert r.status_code==200
    r=await client.get(r.json()['audio_url'],headers=h)
    assert r.status_code==200 and r.content==b'ID3-test-fixture'
    assert r.headers['cache-control']=='no-store'
    other=await register(client,'second@example.com')
    assert (await client.get('/api/v1/finance/summaries/'+summary['id']+'/audio',headers=other)).status_code==404
    result.metric_keys=['invented_balance']
    r=await client.post('/api/v1/finance/summaries',headers=h,json={})
    assert r.status_code==502


@pytest.mark.asyncio
async def test_hypothetical_summary_includes_contingency_without_creating_obligations(client, monkeypatch):
    h = await register(client)
    await account(client, h, '1000')
    await client.put('/api/v1/finance/privacy', headers=h, json={'ai_consent': True})
    result = Narrative(introduction="Let's review your verified financial picture together.",
                       metric_keys=['scenario_balance_30'], recommendation_ids=[],
                       closing='Review the assumptions and upcoming commitments before making changes.')
    model = AsyncMock(return_value=result)
    monkeypatch.setattr(gemini_client, 'generate_structured_response', model)
    response = await client.post('/api/v1/finance/summaries', headers=h, json={
        'scenario': {'amount': '300', 'due_date': date.today().isoformat()}})
    assert response.status_code == 201, response.text
    summary = response.json()
    assert '700.00' in summary['text']
    assert 'Hypothetical emergency' in summary['text']
    assert 'For this contingency' in summary['text']
    assert summary['metrics']['hypothetical_scenario']['persisted'] is False
    dashboard = (await client.get('/api/v1/finance/dashboard', headers=h)).json()
    assert dashboard['shocks'] == [] and dashboard['offers'] == []
    assert dashboard['forecast']['balance'] == '1000.00'
    assert (await client.get('/api/v1/finance/flows', headers=h)).json() == []
