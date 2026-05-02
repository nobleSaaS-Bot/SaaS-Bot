from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta, timezone

from models.order import Order, OrderStatus


async def get_revenue_summary(db: AsyncSession, store_id: str) -> dict:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_result = await db.execute(
        select(func.sum(Order.total)).where(
            Order.store_id == store_id,
            Order.status == OrderStatus.paid,
        )
    )
    total_revenue = float(total_result.scalar() or 0)

    month_result = await db.execute(
        select(func.sum(Order.total)).where(
            Order.store_id == store_id,
            Order.status == OrderStatus.paid,
            Order.created_at >= month_start,
        )
    )
    monthly_revenue = float(month_result.scalar() or 0)

    orders_result = await db.execute(
        select(func.count()).where(Order.store_id == store_id)
    )
    total_orders = int(orders_result.scalar() or 0)

    pending_result = await db.execute(
        select(func.count()).where(
            Order.store_id == store_id,
            Order.status == OrderStatus.pending,
        )
    )
    pending_orders = int(pending_result.scalar() or 0)

    return {
        "total_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
    }


async def get_orders_over_time(db: AsyncSession, store_id: str, days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date(Order.created_at).label("date"),
            func.count().label("orders"),
            func.sum(Order.total).label("revenue"),
        ).where(
            Order.store_id == store_id,
            Order.created_at >= since,
        ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at))
    )
    return [{"date": str(row.date), "orders": row.orders, "revenue": float(row.revenue or 0)} for row in result]


async def get_top_products(db: AsyncSession, store_id: str, limit: int = 10) -> list[dict]:
    return []
