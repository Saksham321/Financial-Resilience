"""Periodic durable work. Run one worker; delivery keys permit provider deduplication."""
import asyncio
from sqlalchemy import select,or_
from datetime import datetime,timezone
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import ExternalServiceError
from app.shared.database.session import AsyncSessionLocal
from app.shared.database.models import User
from app.engines.models import Notification
from app.engines.service import refresh, lock_user
from app.integrations.providers import adapter
from app.engines.platform import consume_financial_events, manage_data_retention


async def tick():
    async with AsyncSessionLocal() as db:
        ids = list((await db.scalars(select(User.id).where(User.is_active.is_(True)))).all())
    for uid in ids:
        try:
            async with AsyncSessionLocal() as db:
                await lock_user(db, uid)
                if not await consume_financial_events(db, uid):
                    await refresh(db, uid)
                await manage_data_retention(db, uid)
                await db.commit()
                if settings.NOTIFICATION_API_URL and settings.NOTIFICATION_API_KEY:
                    pending = list((await db.scalars(select(Notification).where(Notification.user_id == uid,
                        Notification.delivery_status != "delivered",Notification.cancelled.is_(False),
                        or_(Notification.scheduled_for.is_(None),Notification.scheduled_for<=datetime.now(timezone.utc))))).all())
                    for row in pending:
                        try:
                            response = await adapter("NOTIFICATION", "/deliver", {"user_id": str(uid), "title": row.title, "message": row.message}, row.dedupe_key)
                            data = response.json()
                            if data.get("delivered") is not True:
                                raise ExternalServiceError("Notification provider did not confirm delivery")
                            row.delivery_status = "delivered"
                        except (ExternalServiceError, ValueError):
                            row.delivery_status = "failed_retry_pending"
                            logger.warning("notification_delivery_failed", notification_id=str(row.id))
                        await db.commit()
        except Exception:
            logger.exception("financial_background_job_failed", user_id=str(uid))


async def run():
    while True:
        try:
            await tick()
        except Exception:
            logger.exception("background_tick_failed")
        await asyncio.sleep(settings.JOB_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run())
