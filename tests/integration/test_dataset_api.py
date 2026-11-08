import pytest
from app.shared.database.datasets import DatasetAccount, DatasetMonth, DatasetInsights, DatasetSourceRecord, DatasetSourceFile
from app.api.endpoints.datasets import DATASET_ID
from test_financial_api import register


@pytest.mark.asyncio
async def test_dataset_auth_empty_state_and_read_only_browsing(client, test_db_session):
    assert (await client.get('/api/v1/datasets/overview')).status_code == 200
    h = await register(client)
    assert (await client.get('/api/v1/datasets/overview', headers=h)).json()['available'] is False
    for identifier in (1, 2):
        test_db_session.add(DatasetAccount(dataset_id=DATASET_ID, account_id=identifier,
            payload={'account_id': identifier, 'B': 150.25, 'region': 'Source region', 'archetype': 'Saver'}))
    test_db_session.add(DatasetMonth(dataset_id=DATASET_ID, account_id=1, month='2025-12',
        payload={'account_id': 1, 'month': '2025-12', 'money_in': 100.5, 'money_out': 50.25}))
    test_db_session.add(DatasetInsights(dataset_id=DATASET_ID, payload={'total_accounts': 2},
        source_manifest={'period': {'first': '2025-12', 'last': '2025-12'}}))
    test_db_session.add(DatasetSourceRecord(dataset_id=DATASET_ID, source='transactions', record_key='123',
        account_id=1, period='2025-12-01', payload={'transaction_id':'123','signed_amount':'12.34'}))
    test_db_session.add(DatasetSourceFile(dataset_id=DATASET_ID, source='transactions', sha256='0'*64,
        row_count=1, columns=['transaction_id','signed_amount']))
    await test_db_session.commit()
    result = (await client.get('/api/v1/datasets/overview', headers=h)).json()
    assert result['accounts'] == 2 and result['monthly_records'] == 1
    assert result['currency'] == 'Unspecified in source'
    assert result['source_files'] == [{'source':'transactions','rows':1}]
    txs = (await client.get('/api/v1/datasets/accounts/1/transactions',headers=h)).json()
    assert txs['total'] == 1 and txs['items'][0]['signed_amount'] == '12.34'
    assert (await client.get('/api/v1/datasets/accounts/2/transactions',headers=h)).json()['total'] == 0
    page = (await client.get('/api/v1/datasets/accounts?limit=1&offset=1', headers=h)).json()
    assert page['total'] == 2 and page['items'][0]['account_id'] == 2
    page = (await client.get('/api/v1/datasets/accounts?account_id=1', headers=h)).json()
    assert page['total'] == 1 and page['items'][0]['account_id'] == 1
    detail = (await client.get('/api/v1/datasets/accounts/1', headers=h)).json()
    assert detail['account']['B'] == 150.25 and detail['months'][0]['month'] == '2025-12'
    assert detail['analysis']['forecast']['balance'] == '150.25'
    assert detail['analysis']['as_of'] == '2025-12-31'
    assert detail['analysis']['pyramid']['unclassified_total'] == '50.25'
    assert (await client.get('/api/v1/datasets/accounts/3', headers=h)).status_code == 404
    assert (await client.get('/api/v1/datasets/accounts?limit=10000', headers=h)).status_code == 422
    assert (await client.get('/api/v1/finance/accounts', headers=h)).json() == []
    assert (await client.get('/api/v1/finance/transactions', headers=h)).json() == []
