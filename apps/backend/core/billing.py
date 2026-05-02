from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.subscription import Subscription
from core.plans import PLANS
from core.limits import check_limit


class BillingError(Exception):
    pass


async def get_active_subscription(db: AsyncSession, business_id: str) -> Subscription | None:
    result = await db.execute(
        select(Subscription).where(
            Subscription.business_id == business_id,
            Subscription.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def enforce_plan(db: AsyncSession, business_id: str, feature: str) -> bool:
    subscription = await get_active_subscription(db, business_id)
    if not subscription:
        plan = PLANS["free"]
    else:
        plan = PLANS.get(subscription.plan_name, PLANS["free"])

    allowed = check_limit(plan, feature)
    if not allowed:
        raise BillingError(f"Feature '{feature}' is not available on your current plan.")
    return True


async def create_subscription(
    db: AsyncSession,
    business_id: str,
    plan_name: str,
    stripe_subscription_id: str | None = None,
) -> Subscription:
    subscription = Subscription(
        business_id=business_id,
        plan_name=plan_name,
        status="active",
        stripe_subscription_id=stripe_subscription_id,
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription


async def cancel_subscription(db: AsyncSession, subscription_id: str) -> Subscription:
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise BillingError("Subscription not found.")
    subscription.status = "cancelled"
    await db.commit()
    await db.refresh(subscription)
    return subscription
