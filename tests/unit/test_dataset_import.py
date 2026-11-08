import json
import pytest
from sqlalchemy import create_engine, select, func
from app.shared.database.datasets import DatasetAccount, DatasetMonth, DatasetInsights
from scripts.import_dataset import import_dataset, load_dataset


def test_dataset_import_preserves_fields_and_deduplicates():
    engine = create_engine('sqlite://').execution_options(schema_translate_map={'core': None})
    for model in (DatasetAccount, DatasetMonth, DatasetInsights):
        model.__table__.create(engine)
    accounts = [{'account_id': 1, 'B': 123.45, 'region': 'Source region', 'unknown_field': 'preserved'}]
    months = [{'account_id': 1, 'month': '2025-12', 'money_in': 50.25, 'money_out': 20.5}]
    insights = {'total_accounts': 1, 'baseline': {'median_buffer': 123.45}}
    manifest = {'counts': {'accounts': 1, 'monthly_records': 1}, 'currency': 'unspecified'}
    with engine.begin() as conn:
        assert import_dataset(conn, accounts, months, insights, manifest)['status'] == 'imported'
        assert import_dataset(conn, accounts, months, insights, manifest)['status'] == 'already_imported'
        assert conn.scalar(select(DatasetAccount.payload)) == accounts[0]
        assert conn.scalar(select(DatasetMonth.payload)) == months[0]
        assert conn.scalar(select(DatasetInsights.payload)) == insights
        assert conn.scalar(select(func.count()).select_from(DatasetMonth)) == 1
    # A failed surrounding transaction does not leave half an import behind.
    with pytest.raises(RuntimeError):
        with engine.begin() as conn:
            import_dataset(conn, accounts, months, insights, manifest, dataset_id='rolled_back')
            raise RuntimeError('test rollback')
    with engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(DatasetAccount)) == 1
    engine.dispose()


def test_dataset_validation_rejects_orphans_duplicates_and_count_mismatch(tmp_path):
    arrow = pytest.importorskip('pyarrow')
    parquet = pytest.importorskip('pyarrow.parquet')
    parquet.write_table(arrow.Table.from_pylist([{'account_id': 1, 'B': 100.0}]), tmp_path/'accounts_master.parquet')
    def write_months(rows):
        parquet.write_table(arrow.Table.from_pylist(rows), tmp_path/'monthly_summary_compact.parquet')
    (tmp_path/'macro_insights.json').write_text(json.dumps({'total_accounts': 1}), encoding='utf-8')
    write_months([{'account_id': 2, 'month': '2025-01'}])
    with pytest.raises(ValueError, match='unknown account'):
        load_dataset(tmp_path)
    write_months([{'account_id': 1, 'month': '2025-01'}]*2)
    with pytest.raises(ValueError, match='Duplicate account/month'):
        load_dataset(tmp_path)
    write_months([{'account_id': 1, 'month': '2025-01'}])
    assert load_dataset(tmp_path)[3]['counts'] == {'accounts': 1, 'monthly_records': 1}
    (tmp_path/'macro_insights.json').write_text(json.dumps({'total_accounts': 2}), encoding='utf-8')
    with pytest.raises(ValueError, match='count does not match'):
        load_dataset(tmp_path)
