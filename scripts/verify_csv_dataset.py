"""Compare every retained CSV payload with the current source files."""
import argparse
import csv
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import select, func
from app.shared.database.datasets import DatasetSourceRecord as Record, DatasetSourceFile as File
from scripts.import_csv_dataset import SOURCES, file_hash
from scripts.import_dataset import DATASET_ID


def verify(connection, directory):
    results = []
    for source, keys in SOURCES.items():
        path = Path(directory)/(source+'.csv')
        manifest = connection.execute(select(File.sha256,File.row_count).where(File.dataset_id==DATASET_ID,File.source==source)).one()
        if manifest.sha256 != file_hash(path):
            raise ValueError(f'{source}: source checksum mismatch')
        count = 0
        def compare(batch):
            stored = dict(connection.execute(select(Record.record_key,Record.payload).where(
                Record.dataset_id==DATASET_ID,Record.source==source,Record.record_key.in_([key for key,_ in batch]))).all())
            for key,row in batch:
                if stored.get(key) != row:
                    raise ValueError(f'{source}: payload mismatch for source record {key}')
        with path.open(encoding='utf-8-sig',newline='') as stream:
            batch = []
            for row in csv.DictReader(stream):
                batch.append((':'.join(row[key] for key in keys),row)); count += 1
                if len(batch)==1000:
                    compare(batch);batch.clear()
            if batch:
                compare(batch)
        actual = connection.scalar(select(func.count()).select_from(Record).where(Record.dataset_id==DATASET_ID,Record.source==source))
        if count != manifest.row_count or count != actual:
            raise ValueError(f'{source}: row count mismatch')
        result = {'source':source,'rows':count,'sha256':manifest.sha256,'all_payloads_match':True}
        results.append(result)
        print(json.dumps(result),flush=True)
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('data'))
    args=parser.parse_args()
    from app.shared.database.session import sync_engine
    with tempfile.TemporaryDirectory(prefix='fre-csv-verify-') as temporary:
        snapshot=Path(temporary)
        for source in SOURCES:
            shutil.copyfile(args.data_dir/(source+'.csv'),snapshot/(source+'.csv'))
        with sync_engine.connect() as connection:
            sources=verify(connection,snapshot)
    report={'dataset_id':DATASET_ID,'verified_at_utc':datetime.now(timezone.utc).isoformat(),
            'sources':sources,'total_csv_rows':sum(r['rows'] for r in sources),'all_source_payloads_match':True}
    Path('docs/CSV_IMPORT_REPORT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'verified_csv_rows':report['total_csv_rows']}),flush=True)


if __name__=='__main__':
    main()
