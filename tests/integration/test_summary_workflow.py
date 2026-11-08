from unittest.mock import AsyncMock
import pytest
from app.engines.schemas import Narrative
from app.integrations.gemini.client import gemini_client
from app.integrations import providers
from test_financial_api import register,account


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
