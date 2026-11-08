"""Durable local event delivery and configurable derived-data retention.

Events share the audit transaction, so a rolled-back import cannot publish work.
Workers lock the user before consuming, and commit refresh plus delivery together.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete
from app.core.config import settings
from app.shared.database.models import AuditLog
from app.engines.models import Summary


async def publish_financial_event(db, uid, key, kind, details=None):
    # Caller holds the user lock; serialize duplicate keys without a new schema.
    events = (await db.scalars(select(AuditLog).where(
        AuditLog.user_id == uid,
        AuditLog.event_type.in_(("FINANCIAL_EVENT_PENDING", "FINANCIAL_EVENT_PROCESSED")),
    ))).all()
    existing = next((e for e in events if e.details.get("key") == key), None)
    if existing:
        return existing
    event = AuditLog(user_id=uid, event_type="FINANCIAL_EVENT_PENDING",
                     details={"key": key, "kind": kind, "payload": details or {}})
    db.add(event)
    await db.flush()
    return event


async def consume_financial_events(db, uid):
    from app.engines.service import refresh
    events = (await db.scalars(select(AuditLog).where(
        AuditLog.user_id == uid, AuditLog.event_type == "FINANCIAL_EVENT_PENDING",
    ).with_for_update())).all()
    if not events:
        return 0
    await refresh(db, uid)
    for event in events:
        event.event_type = "FINANCIAL_EVENT_PROCESSED"
    await db.flush()
    return len(events)


async def manage_data_retention(db, uid, now=None):
    """Remove expired generated summaries, including audio; retain source/audit data.

    Zero disables automatic deletion. Policy uses creation time so reads or audio
    generation cannot indefinitely extend the lifetime of sensitive snapshots.
    """
    days = settings.SUMMARY_RETENTION_DAYS
    if not days:
        return 0
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    result = await db.execute(delete(Summary).where(
        Summary.user_id == uid, Summary.created_at < cutoff,
    ))
    if result.rowcount:
        db.add(AuditLog(user_id=uid, event_type="DATA_RETENTION_APPLIED",
                        details={"summaries_deleted": result.rowcount, "retention_days": days}))
    return result.rowcount
