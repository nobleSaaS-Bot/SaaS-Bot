import asyncio
import logging
from datetime import datetime, timezone
from workers.tasks import log_task_start, log_task_complete, log_task_error

logger = logging.getLogger(__name__)


def renew_subscription(subscription_id: str) -> None:
    log_task_start("renew_subscription", subscription_id=subscription_id)
    try:
        asyncio.run(_renew_subscription_async(subscription_id))
        log_task_complete("renew_subscription", subscription_id=subscription_id)
    except Exception as e:
        log_task_error("renew_subscription", e, subscription_id=subscription_id)
        raise


async def _renew_subscription_async(subscription_id: str) -> None:
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from models.subscription import Subscription, SubscriptionStatus

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            logger.warning(f"Subscription {subscription_id} not found")
            return

        now = datetime.now(timezone.utc)
        if subscription.current_period_end and now > subscription.current_period_end:
            if subscription.cancel_at_period_end:
                subscription.status = SubscriptionStatus.expired
            else:
                subscription.status = SubscriptionStatus.past_due

            await db.commit()
            logger.info(f"Subscription {subscription_id} status updated to {subscription.status}")


def check_all_expiring_subscriptions() -> None:
    asyncio.run(_check_expiring_async())


async def _check_expiring_async() -> None:
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from models.subscription import Subscription, SubscriptionStatus
    from core.queue import enqueue_subscription_renewal
    from datetime import timedelta

    async with AsyncSessionLocal() as db:
        soon = datetime.now(timezone.utc) + timedelta(days=3)
        result = await db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.active,
                Subscription.current_period_end <= soon,
            )
        )
        subscriptions = result.scalars().all()
        for sub in subscriptions:
            enqueue_subscription_renewal(sub.id)
            logger.info(f"Enqueued renewal for subscription {sub.id}")
