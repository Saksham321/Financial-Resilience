from httpx import AsyncClient,ASGITransport
import pytest
from app.services import create_service,SERVICES


@pytest.mark.asyncio
async def test_engines_have_separate_route_surfaces_and_worker_ownership():
    for name in SERVICES:
        app=create_service(name)
        paths=app.openapi()['paths']
        assert '/api/v1/auth/login' in paths
        assert app.state.enable_background_jobs==(name=='subscriptions')
        if name=='shock':
            assert '/api/v1/shocks/mediate' in paths and '/api/v1/predictive-plan' not in paths
        if name=='predictive':
            assert '/api/v1/predictive-plan' in paths and '/api/v1/shocks/mediate' not in paths
        if name=='gemini':
            assert '/api/v1/finance/summaries' in paths
            assert '/api/v1/finance/summaries/{identifier}/audio' not in paths
        if name=='voice':
            assert '/api/v1/finance/summaries/{identifier}/audio' in paths
            assert '/api/v1/finance/summaries' not in paths
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            result=await client.get('/health')
            assert result.status_code==200 and result.json()['service']==name


def test_unknown_engine_is_rejected():
    with pytest.raises(ValueError):create_service('unknown')
