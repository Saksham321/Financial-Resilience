"""Validate and atomically import processed data, keeping original JSON fields.

Run: python -m scripts.import_dataset [--data-dir data/processed] [--dry-run]
No users, balances, transactions, currency conversions, or consents are created.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select, func
from app.shared.database.datasets import DatasetAccount, DatasetMonth, DatasetInsights

DATASET_ID = "financial_resilience_processed_v1"
FILES = ("accounts_master.parquet", "monthly_summary_compact.parquet", "macro_insights.json")


def load_dataset(directory):
    import pyarrow.parquet as parquet
    directory = Path(directory)
    paths = {name: directory / name for name in FILES}
    manifest = {name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
                for name, path in paths.items()}
    accounts = parquet.read_table(paths[FILES[0]]).to_pylist()
    months = parquet.read_table(paths[FILES[1]]).to_pylist()
    insights = json.loads(paths[FILES[2]].read_text(encoding="utf-8"))
    if not accounts or not months:
        raise ValueError("Account and monthly files must not be empty")
    # Fail on non-JSON values instead of silently dropping/rewriting source data.
    for label, data in (("accounts", accounts), ("months", months), ("insights", insights)):
        try:
            json.dumps(data, allow_nan=False)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{label} contains non-finite or unsupported JSON values") from exc
    ids = set()
    for row in accounts:
        identifier = row.get("account_id")
        if type(identifier) is not int or identifier in ids:
            raise ValueError("Invalid or duplicate source account_id")
        ids.add(identifier)
    keys = set()
    for row in months:
        identifier, month = row.get("account_id"), row.get("month")
        if identifier not in ids:
            raise ValueError("Monthly record references an unknown account")
        if not isinstance(month, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            raise ValueError("Invalid monthly period")
        key = (identifier, month)
        if key in keys:
            raise ValueError("Duplicate account/month record")
        keys.add(key)
    if insights.get("total_accounts") != len(accounts):
        raise ValueError("Macro insights account count does not match source records")
    manifest["counts"] = {"accounts": len(accounts), "monthly_records": len(months)}
    manifest["period"] = {"first": min(r["month"] for r in months), "last": max(r["month"] for r in months)}
    manifest["currency"] = "unspecified_in_source_no_conversion"
    return accounts, months, insights, manifest


def import_dataset(connection, accounts, months, insights, manifest, dataset_id=DATASET_ID):
    """Caller owns the transaction. Conflict keys make repeated runs idempotent."""
    if connection.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif connection.dialect.name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise ValueError("Dataset importer supports PostgreSQL and SQLite")
    previous = connection.execute(select(DatasetInsights.source_manifest).where(DatasetInsights.dataset_id == dataset_id)).scalar_one_or_none()
    if previous == manifest:
        account_count = connection.scalar(select(func.count()).select_from(DatasetAccount).where(DatasetAccount.dataset_id == dataset_id))
        month_count = connection.scalar(select(func.count()).select_from(DatasetMonth).where(DatasetMonth.dataset_id == dataset_id))
        if account_count == len(accounts) and month_count == len(months):
            return {"status": "already_imported", "accounts": account_count, "monthly_records": month_count}
    for model, records, columns in (
        (DatasetAccount, accounts, ["dataset_id", "account_id"]),
        (DatasetMonth, months, ["dataset_id", "account_id", "month"]),
    ):
        for start in range(0, len(records), 1000):
            batch = [{"dataset_id": dataset_id, "account_id": r["account_id"], "payload": r,
                      **({"month": r["month"]} if model is DatasetMonth else {})} for r in records[start:start+1000]]
            statement = insert(model.__table__)
            connection.execute(statement.on_conflict_do_update(index_elements=columns, set_={"payload": statement.excluded.payload}), batch)
    statement = insert(DatasetInsights.__table__).values(dataset_id=dataset_id, payload=insights,
        source_manifest=manifest, imported_at=datetime.now(timezone.utc))
    connection.execute(statement.on_conflict_do_update(index_elements=["dataset_id"], set_={
        "payload": statement.excluded.payload, "source_manifest": statement.excluded.source_manifest,
        "imported_at": statement.excluded.imported_at}))
    return {"status": "imported", **manifest["counts"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    accounts, months, insights, manifest = load_dataset(args.data_dir)
    if args.dry_run:
        print(json.dumps({"status": "validated", "dataset_id": DATASET_ID, "manifest": manifest}, indent=2))
        return
    from app.shared.database.session import sync_engine
    with sync_engine.begin() as connection:
        result = import_dataset(connection, accounts, months, insights, manifest)
    print(json.dumps({"dataset_id": DATASET_ID, **result}, indent=2))


if __name__ == "__main__":
    main()
