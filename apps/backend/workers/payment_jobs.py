import asyncio
import logging
from workers.tasks import log_task_start, log_task_complete, log_task_error

logger = logging.getLogger(__name__)


def process_payment(order_id: str, provider: str, payment_data: dict) -> None:
    log_task_start("process_payment", order_id=order_id, provider=provider)
    try:
        asyncio.run(_process_payment_async(order_id, provider, payment_data))
        log_task_complete("process_payment", order_id=order_id)
    except Exception as e:
        log_task_error("process_payment", e, order_id=order_id)
        raise


async def _process_payment_async(order_id: str, provider: str, payment_data: dict) -> None:
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from models.payment import Payment, PaymentStatus
    from models.order import Order, OrderStatus

    status = payment_data.get("status", "pending")

    async with AsyncSessionLocal() as db:
        payment_result = await db.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = payment_result.scalar_one_or_none()

        order_result = await db.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalar_one_or_none()

        if not order:
            logger.error(f"Order {order_id} not found")
            return

        if status == "completed":
            if payment:
                payment.status = PaymentStatus.completed
            order.status = OrderStatus.paid

            await db.commit()

            from services.telegram.checkout import send_order_confirmation
            await send_order_confirmation(order.customer_telegram_id, order)

        elif status == "failed":
            if payment:
                payment.status = PaymentStatus.failed
            order.status = OrderStatus.cancelled
            await db.commit()

            from services.telegram.bot_service import send_message
            await send_message(order.customer_telegram_id, "Payment failed. Please try again or contact support.")
