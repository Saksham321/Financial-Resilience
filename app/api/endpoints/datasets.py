"""Read-only access to the imported reference dataset, separate from user money."""
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.shared.database.datasets import (
    DatasetAccount,
    DatasetInsights,
    DatasetMonth,
    DatasetSourceFile,
    DatasetSourceRecord,
)
from app.shared.database.session import get_db

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
    profiles=Counter()
    regions=defaultdict(list)
    for account in (await db.scalars(select(DatasetAccount).where(DatasetAccount.dataset_id==DATASET_ID))).all():
        profiles[account.payload.get('archetype','Unassigned')]+=1
        regions[account.payload.get('region','Unknown')].append(account.payload.get('B'))
    from app.engines.calculations import money
    breakdown=[]
    for name,values in sorted(regions.items()):
        available=[Decimal(str(value)) for value in values if value is not None]
        breakdown.append({'region':name,'accounts':len(values),'avg_buffer':money(sum(available)/len(available)) if available else None})
    return {"available": True, "accounts": accounts, "monthly_records": months,
            "period": {'first':await db.scalar(select(func.min(DatasetMonth.month)).where(DatasetMonth.dataset_id==DATASET_ID)),
                       'last':await db.scalar(select(func.max(DatasetMonth.month)).where(DatasetMonth.dataset_id==DATASET_ID))},
            "insights": {**row.payload,'archetypes':dict(profiles),'regional_breakdown':breakdown},
            "currency": "CAD", "imported_at": row.imported_at,
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
    # Recompute the directory cash flow using the same cent-rounded medians as
    # the toolkit. The preserved processed snapshot used different tie rounding.
    history=defaultdict(list)
    if records:
        source_rows=(await db.scalars(select(DatasetSourceRecord).where(
            DatasetSourceRecord.dataset_id==DATASET_ID,DatasetSourceRecord.source=='monthly_summary',
            DatasetSourceRecord.account_id.in_([r.account_id for r in records])))).all()
        for row in source_rows:history[row.account_id].append(row.payload)
    items=[]
    from statistics import median

    from app.engines.calculations import money
    for record in records:
        value=dict(record.payload)
        months=history[record.account_id]
        if months and all(row.get('money_in') is not None and row.get('money_out') is not None for row in months):
            incoming=money(median(float(row['money_in']) for row in months))
            outgoing=money(median(float(row['money_out']) for row in months))
            value['net_cash_flow']=money(incoming-outgoing)
        items.append(value)
    return {"total": total, "offset": offset, "limit": limit, "items": items}


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
            "currency": "CAD", "analysis": encode(analysis)}


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


_cpi_cache = None
_cpi_cache_time = 0.0

@router.get('/canadian-cpi')
async def canadian_cpi():
    """Public economic statistics; no customer data is sent to the provider."""
    import time
    from app.integrations.providers import fetch_cpi
    from app.core.config import settings
    global _cpi_cache, _cpi_cache_time
    if _cpi_cache is not None and time.monotonic() - _cpi_cache_time < 3600:
        return _cpi_cache
    rows = sorted(dict(await fetch_cpi()).items())
    result = {'source':'Statistics Canada','vector':str(settings.STATSCAN_CPI_VECTOR),
        'observations':[{'month':month,'index':str(value)} for month,value in rows]}
    _cpi_cache, _cpi_cache_time = result, time.monotonic()
    return result
