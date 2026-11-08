"""Stream CSV source files into separate reference-data tables, atomically."""
import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select, func
from app.shared.database.datasets import DatasetSourceRecord as Record, DatasetSourceFile as File
from scripts.import_dataset import DATASET_ID

SOURCES = {
    'districts': ('district_id',), 'accounts': ('account_id',),
    'clients': ('client_id',), 'dispositions': ('disposition_id',),
    'cards': ('card_id',), 'loans': ('loan_id',),
    'standing_orders': ('order_id',), 'monthly_summary': ('account_id', 'month'),
    'transactions': ('transaction_id',),
}


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def import_csv_files(connection, directory, progress=lambda result: None):
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    insert = pg_insert if connection.dialect.name == 'postgresql' else sqlite_insert
    results = []
    # All files share the caller's transaction: invalid input rolls back the lot.
    account_ids = set()
    with (Path(directory)/'accounts.csv').open(encoding='utf-8-sig', newline='') as stream:
        account_ids = {int(row['account_id']) for row in csv.DictReader(stream)}
    for source, key_columns in SOURCES.items():
        path = Path(directory)/(source+'.csv')
        checksum = file_hash(path)
        previous = connection.execute(select(File.sha256, File.row_count).where(File.dataset_id == DATASET_ID, File.source == source)).first()
        if previous and previous.sha256 == checksum:
            actual = connection.scalar(select(func.count()).select_from(Record).where(Record.dataset_id == DATASET_ID, Record.source == source))
            if actual == previous.row_count:
                result = {'source': source, 'rows': actual, 'status': 'already_imported'}
                results.append(result); progress(result); continue
        count = 0
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            columns = reader.fieldnames
            if not columns or not set(key_columns).issubset(columns) or len(set(columns)) != len(columns):
                raise ValueError(f'{source}: missing or duplicate columns')
            batch = []
            statement = insert(Record.__table__)
            upsert = statement.on_conflict_do_update(index_elements=['dataset_id', 'source', 'record_key'], set_={
                'account_id': statement.excluded.account_id, 'period': statement.excluded.period, 'payload': statement.excluded.payload})
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f'{source}: malformed row {reader.line_num}')
                key = ':'.join(row[name] for name in key_columns)
                if any(not row[name] for name in key_columns) or len(key)>100:
                    raise ValueError(f'{source}: invalid record key at row {reader.line_num}')
                account = int(row['account_id']) if 'account_id' in row else None
                if account is not None and account not in account_ids:
                    raise ValueError(f'{source}: unknown account at row {reader.line_num}')
                batch.append({'dataset_id': DATASET_ID, 'source': source, 'record_key': key,
                              'account_id': account, 'period': row.get('date') or row.get('month'), 'payload': row})
                count += 1
                if len(batch) == 2000:
                    connection.execute(upsert, batch); batch.clear()
            if batch:
                connection.execute(upsert, batch)
        actual = connection.scalar(select(func.count()).select_from(Record).where(Record.dataset_id == DATASET_ID, Record.source == source))
        if actual != count:
            raise ValueError(f'{source}: duplicate source keys or removed records; import rolled back')
        if file_hash(path) != checksum:
            raise ValueError(f'{source}: file changed during import')
        statement = insert(File.__table__).values(dataset_id=DATASET_ID, source=source, sha256=checksum,
            row_count=count, columns=columns, imported_at=datetime.now(timezone.utc))
        connection.execute(statement.on_conflict_do_update(index_elements=['dataset_id','source'], set_={
            name: getattr(statement.excluded,name) for name in ('sha256','row_count','columns','imported_at')}))
        result = {'source': source, 'rows': count, 'status': 'imported'}
        results.append(result); progress(result)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    args = parser.parse_args()
    from app.shared.database.session import sync_engine
    # A stable local snapshot avoids OneDrive recalling/dehydrating files mid-read.
    with tempfile.TemporaryDirectory(prefix='fre-csv-import-') as temporary:
        snapshot = Path(temporary)
        for source in SOURCES:
            shutil.copyfile(args.data_dir/(source+'.csv'), snapshot/(source+'.csv'))
        with sync_engine.begin() as connection:
            results = import_csv_files(connection, snapshot, lambda r: print(json.dumps(r), flush=True))
    print(json.dumps({'status': 'committed', 'total_source_rows': sum(r['rows'] for r in results)}), flush=True)


if __name__ == '__main__':
    main()
