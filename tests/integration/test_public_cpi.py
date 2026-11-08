from decimal import Decimal
import pytest
from app.integrations import providers
from app.api.endpoints import datasets

@pytest.mark.asyncio
async def test_public_cpi_returns_official_observations_without_identity(client,monkeypatch):
    monkeypatch.setattr(datasets,'_cpi_cache',None)
    async def fetch():return [('2024-01',Decimal('100')),('2025-01',Decimal('105'))]
    monkeypatch.setattr(providers,'fetch_cpi',fetch)
    response=await client.get('/api/v1/datasets/canadian-cpi')
    assert response.status_code==200
    assert response.json()['source']=='Statistics Canada'
    assert response.json()['observations'][1]=={'month':'2025-01','index':'105'}
