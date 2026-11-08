import json
from unittest.mock import AsyncMock
from datetime import datetime, timezone, timedelta
import httpx
import pytest
from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.integrations import providers
from app.integrations.gemini.client import gemini_client
from app.engines.schemas import Narrative


def response(data=None, status=200, content=None, headers=None):
    return httpx.Response(status, json=data if content is None else None, content=content, headers=headers, request=httpx.Request('POST','https://test.invalid'))


@pytest.mark.asyncio
async def test_underwriting_validated_and_no_config(monkeypatch):
    monkeypatch.setattr(settings,'UNDERWRITING_API_URL',None)
    with pytest.raises(ExternalServiceError):
        await providers.underwriting('user',100,'key')
    monkeypatch.setattr(providers,'adapter',AsyncMock(return_value=response({'eligible':True,'product':'credit','reference':'id','approved_amount':100})))
    assert (await providers.underwriting('user',100,'key'))['eligible']
    monkeypatch.setattr(providers,'adapter',AsyncMock(return_value=response({'eligible':True,'product':'none','reference':'id','approved_amount':0})))
    with pytest.raises(ExternalServiceError):
        await providers.underwriting('user',100,'key')


@pytest.mark.asyncio
async def test_browsing_recent_category_and_expiration(monkeypatch):
    now=datetime.now(timezone.utc)
    for category,hours,expected in [('groceries',2,True),('groceries',73,False),('other',1,False)]:
        monkeypatch.setattr(providers,'adapter',AsyncMock(return_value=response({'matches':[{'category':category,'viewed_at':(now-timedelta(hours=hours)).isoformat()}]})))
        assert await providers.browsing('user','groceries',now)==expected


@pytest.mark.asyncio
async def test_gemini_structured_request_and_validation(monkeypatch):
    monkeypatch.setattr(settings,'GEMINI_API_KEY','test-only-key')
    result={'introduction':"Let's review your verified financial picture together.",'metric_keys':['liquidity'],'recommendation_ids':[0],'closing':'Review the assumptions and upcoming commitments before making changes.'}
    spy=AsyncMock(return_value=response({'candidates':[{'content':{'parts':[{'text':json.dumps(result)}]}}]}))
    monkeypatch.setattr('app.integrations.gemini.client.request',spy)
    out=await gemini_client.generate_structured_response('verified prompt',Narrative)
    assert out.metric_keys==['liquidity']
    assert spy.call_args.kwargs['headers']['x-goog-api-key']=='test-only-key'
    assert 'responseJsonSchema' in spy.call_args.kwargs['json']['generationConfig']
    spy.return_value=response({'candidates':[{'content':{'parts':[{'text':json.dumps({**result,'introduction':'You have $50000'})}]}}]})
    with pytest.raises(ExternalServiceError):
        await gemini_client.generate_structured_response('prompt',Narrative)


@pytest.mark.asyncio
async def test_gemini_missing_key_never_mock_success(monkeypatch):
    monkeypatch.setattr(settings,'GEMINI_API_KEY',None)
    with pytest.raises(ExternalServiceError):
        await gemini_client.generate_structured_response('prompt',Narrative)


@pytest.mark.asyncio
async def test_elevenlabs_audio_profiles_missing_key_and_invalid_response(monkeypatch):
    monkeypatch.setattr(settings,'ELEVENLABS_API_KEY',None)
    with pytest.raises(ExternalServiceError):
        await providers.speech('hello','professional')
    monkeypatch.setattr(settings,'ELEVENLABS_API_KEY','test-only-key')
    monkeypatch.setattr(settings,'ELEVENLABS_EMPATHETIC_VOICE_ID','test-voice')
    spy=AsyncMock(return_value=response(content=b'ID3-test-fixture',headers={'content-type':'audio/mpeg'}))
    monkeypatch.setattr(providers,'request',spy)
    assert await providers.speech('verified summary','empathetic')==b'ID3-test-fixture'
    assert spy.call_args.args[1].endswith('/test-voice')
    assert spy.call_args.kwargs['retries']==0
    spy.return_value=response({'error':'bad response'})
    with pytest.raises(ExternalServiceError):
        await providers.speech('hello','professional')


@pytest.mark.asyncio
async def test_statistics_canada_contract(monkeypatch):
    spy=AsyncMock(return_value=response([{'status':'SUCCESS','object':{'vectorDataPoint':[{'refPer':'2026-01-01','value':160.2}]}}]))
    monkeypatch.setattr(providers,'request',spy)
    result=await providers.fetch_cpi()
    assert result[0][0]=='2026-01' and str(result[0][1])=='160.2'
    assert isinstance(spy.call_args.kwargs['json'],dict)
    spy.return_value=response([{'status':'FAILED'}])
    with pytest.raises(ExternalServiceError):
        await providers.fetch_cpi()


@pytest.mark.asyncio
@pytest.mark.parametrize('status',[400,401,429,500])
async def test_http_failure_retry_policy(monkeypatch,status):
    calls=[]
    def handler(req):
        calls.append(req)
        return httpx.Response(status,request=req)
    original=httpx.AsyncClient
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    monkeypatch.setattr(providers.asyncio,'sleep',AsyncMock())
    with pytest.raises(ExternalServiceError):
        await providers.request('GET','https://test.invalid',retries=2)
    assert len(calls)==(3 if status in (429,500) else 1)


@pytest.mark.asyncio
async def test_http_timeout_and_success_retry(monkeypatch):
    calls=[]
    def handler(req):
        calls.append(req)
        if len(calls)==1:
            raise httpx.ReadTimeout('test timeout',request=req)
        return httpx.Response(200,json={'ok':True},request=req)
    original=httpx.AsyncClient
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    monkeypatch.setattr(providers.asyncio,'sleep',AsyncMock())
    assert (await providers.request('GET','https://test.invalid')).json()['ok']
    assert len(calls)==2
