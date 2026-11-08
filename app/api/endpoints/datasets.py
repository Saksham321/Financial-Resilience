"""Read-only access to the imported reference dataset, separate from user money."""
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundError
from app.shared.database.session import get_db
from app.shared.database.datasets import DatasetAccount, DatasetMonth, DatasetInsights, DatasetSourceRecord, DatasetSourceFile

router = APIRouter(prefix="/datasets", tags=["Imported dataset"])
DB = Annotated[AsyncSession, Depends(get_db)]
DATASET_ID = "financial_resilience_processed_v1"


@router.get("/overview")
async def overview(db: DB):
    row = await db.get(DatasetInsights, DATASET_ID)
    if row is None:
        return {"available": False, "accounts": 0, "monthly_records": 0}
    accounts = await db.scalar(select(func.count()).select_from(DatasetAccount).where(DatasetAccount.dataset_id == DATASET_ID))
    months = await db.scalar(select(func.count()).select_from(DatasetMonth).where(DatasetMonth.dataset_id == DATASET_ID))
    files = (await db.scalars(select(DatasetSourceFile).where(DatasetSourceFile.dataset_id == DATASET_ID))).all()
    return {"available": True, "accounts": accounts, "monthly_records": months,
            "period": row.source_manifest.get("period", {}), "insights": row.payload,
            "currency": "Unspecified in source", "imported_at": row.imported_at,
            "source_files": [{"source": f.source, "rows": f.row_count} for f in files]}


@router.get("/accounts")
async def accounts(db: DB,
                   offset: Annotated[int, Query(ge=0)] = 0,
                   limit: Annotated[int, Query(ge=1, le=100)] = 25,
                   account_id: Annotated[int | None, Query(gt=0)] = None):
    query = select(DatasetAccount).where(DatasetAccount.dataset_id == DATASET_ID)
    if account_id is not None:
        query = query.where(DatasetAccount.account_id == account_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    records = (await db.scalars(query.order_by(DatasetAccount.account_id).offset(offset).limit(limit))).all()
    return {"total": total, "offset": offset, "limit": limit, "items": [r.payload for r in records]}


@router.get("/accounts/{account_id}")
async def account_details(account_id: int, db: DB):
    account = await db.get(DatasetAccount, (DATASET_ID, account_id))
    if account is None:
        raise EntityNotFoundError("Imported dataset account not found")
    months = (await db.scalars(select(DatasetMonth).where(
        DatasetMonth.dataset_id == DATASET_ID, DatasetMonth.account_id == account_id,
    ).order_by(DatasetMonth.month))).all()
    source_months = (await db.scalars(select(DatasetSourceRecord).where(
        DatasetSourceRecord.dataset_id == DATASET_ID, DatasetSourceRecord.account_id == account_id,
        DatasetSourceRecord.source == "monthly_summary"))).all()
    from app.engines.dataset_analysis import analyze_source_account
    from app.engines.service import encode
    analysis = analyze_source_account(account.payload, [m.payload for m in months], [r.payload for r in source_months])
    return {"account": account.payload, "months": [m.payload for m in months],
            "currency": "Unspecified in source", "analysis": encode(analysis)}


@router.get("/accounts/{account_id}/transactions")
async def account_transactions(account_id: int, db: DB,
                               offset: Annotated[int, Query(ge=0)] = 0,
                               limit: Annotated[int, Query(ge=1, le=100)] = 50):
    account = await db.get(DatasetAccount, (DATASET_ID, account_id))
    if account is None:
        raise EntityNotFoundError("Imported dataset account not found")
    query = select(DatasetSourceRecord).where(DatasetSourceRecord.dataset_id == DATASET_ID,
        DatasetSourceRecord.source == "transactions", DatasetSourceRecord.account_id == account_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    records = (await db.scalars(query.order_by(DatasetSourceRecord.period.desc(), DatasetSourceRecord.record_key).offset(offset).limit(limit))).all()
    return {"total": total, "offset": offset, "limit": limit, "items": [r.payload for r in records]}
