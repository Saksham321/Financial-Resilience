import csv
import pytest
from sqlalchemy import create_engine, select, func
from app.shared.database.datasets import DatasetSourceRecord as Record, DatasetSourceFile as File
from scripts.import_csv_dataset import import_csv_files, SOURCES


def test_csv_sources_preserve_all_fields_and_retry_without_duplicates(tmp_path):
    for source, keys in SOURCES.items():
        row = {key: '2025-12' if key == 'month' else '1' for key in keys}
        if source in ('accounts','transactions','loans','standing_orders','dispositions','monthly_summary'):
            row['account_id'] = '1'
        row['source_value'] = '001.2300'
        row['empty'] = ''
        with (tmp_path/(source+'.csv')).open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader(); writer.writerow(row)
    engine = create_engine('sqlite://').execution_options(schema_translate_map={'core': None})
    Record.__table__.create(engine); File.__table__.create(engine)
    with engine.begin() as connection:
        result = import_csv_files(connection, tmp_path)
        assert sum(r['rows'] for r in result) == 9
        assert all(r['status'] == 'already_imported' for r in import_csv_files(connection,tmp_path))
        payload = connection.scalar(select(Record.payload).where(Record.source=='transactions'))
        assert payload['source_value']=='001.2300' and payload['empty']==''
    with (tmp_path/'transactions.csv').open('a', encoding='utf-8') as stream:
        stream.write('2,999,unexpected,\n')
    with pytest.raises(ValueError, match='unknown account'):
        with engine.begin() as connection:
            import_csv_files(connection,tmp_path)
    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(Record)) == 9
    engine.dispose()
