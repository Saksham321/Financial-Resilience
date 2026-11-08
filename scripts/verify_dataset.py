"""Verify every imported payload and optionally compare pre-import user tables."""
import argparse
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import select
from app.shared.database.datasets import DatasetAccount, DatasetMonth, DatasetInsights
from scripts.import_dataset import DATASET_ID, load_dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('data/processed'))
    parser.add_argument('--backup', type=Path)
    parser.add_argument('--report', type=Path, default=Path('docs/DATA_IMPORT_REPORT.json'))
    args = parser.parse_args()
    accounts, months, insights, manifest = load_dataset(args.data_dir)
    from app.shared.database.session import sync_engine
    with sync_engine.connect() as connection:
        actual_accounts = list(connection.scalars(select(DatasetAccount.payload).where(
            DatasetAccount.dataset_id == DATASET_ID).order_by(DatasetAccount.account_id)))
        actual_months = list(connection.scalars(select(DatasetMonth.payload).where(
            DatasetMonth.dataset_id == DATASET_ID).order_by(DatasetMonth.account_id, DatasetMonth.month)))
        actual_insights = connection.scalar(select(DatasetInsights.payload).where(DatasetInsights.dataset_id == DATASET_ID))
        actual_manifest = connection.scalar(select(DatasetInsights.source_manifest).where(DatasetInsights.dataset_id == DATASET_ID))
    if actual_accounts != sorted(accounts, key=lambda r: r['account_id']):
        raise ValueError('Account payload verification failed')
    if actual_months != sorted(months, key=lambda r: (r['account_id'], r['month'])):
        raise ValueError('Monthly payload verification failed')
    if actual_insights != insights or actual_manifest != manifest:
        raise ValueError('Insights or provenance verification failed')
    unchanged = None
    if args.backup:
        if sync_engine.dialect.name != 'sqlite':
            raise ValueError('Backup comparison requires SQLite')
        unchanged = []
        with sqlite3.connect(args.backup) as before, sqlite3.connect(sync_engine.url.database) as after:
            for (table,) in before.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                if table == 'alembic_version' or table.startswith(('source_dataset_', 'sqlite_')):
                    continue
                quoted = '"' + table.replace('"', '""') + '"'
                original = sorted(before.execute(f'SELECT * FROM {quoted}').fetchall(), key=repr)
                current = sorted(after.execute(f'SELECT * FROM {quoted}').fetchall(), key=repr)
                if original != current:
                    raise ValueError(f'Pre-existing records changed in {table}')
                unchanged.append(table)
    report = {
        'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'dataset_id': DATASET_ID,
        'database_kind': sync_engine.dialect.name,
        'tables': {'source_dataset_accounts': len(actual_accounts),
                   'source_dataset_monthly': len(actual_months), 'source_dataset_insights': 1},
        'all_source_payloads_match': True,
        'source_manifest': manifest,
        'unchanged_preexisting_tables': unchanged,
        'backup': args.backup.as_posix() if args.backup else None,
        'currency_converted': False,
        'user_dashboard_data_populated': False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
