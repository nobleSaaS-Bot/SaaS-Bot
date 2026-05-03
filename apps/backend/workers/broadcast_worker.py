"""
RQ worker job: send a broadcast message to all matching customers via Telegram.
"""
import asyncio
import httpx
from datetime import datetime, timezone
from sqlalchemy import select, and_

from app.database import SessionLocal
from models.broadcast import Broadcast, BroadcastStatus, BroadcastSegment
from models.customer import Customer, CustomerSegment
from app.config import settings


async def _send(broadcast_id: str):
    async with SessionLocal() as db:
        result = await db.execute(select(Broadcast).where(Broadcast.id == broadcast_id))
        broadcast = result.scalar_one_or_none()
        if not broadcast:
            return

        # Fetch target customers
        filters = [
            Customer.business_id == broadcast.business_id,
            Customer.is_blocked == False,
        ]
        if broadcast.store_id:
            filters.append(Customer.store_id == broadcast.store_id)
        if broadcast.segment != BroadcastSegment.all:
            filters.append(Customer.segment == CustomerSegment(broadcast.segment.value))

        customers_result = await db.execute(select(Customer).where(and_(*filters)))
        customers = customers_result.scalars().all()

        broadcast.total_recipients = len(customers)
        sent = 0
        failed = 0

        async with httpx.AsyncClient(timeout=10) as client:
            for customer in customers:
                try:
                    payload: dict = {
                        "chat_id": customer.telegram_id,
                        "parse_mode": "HTML",
                    }

                    if broadcast.image_url:
                        payload["photo"] = broadcast.image_url
                        payload["caption"] = f"<b>{broadcast.message}</b>"
                        method = "sendPhoto"
                    else:
                        payload["text"] = broadcast.message
                        method = "sendMessage"

                    if broadcast.buttons:
                        inline_keyboard = [
                            [{"text": btn.get("text", ""), "url": btn.get("url", "")}]
                            for btn in broadcast.buttons
                        ]
                        payload["reply_markup"] = {"inline_keyboard": inline_keyboard}

                    resp = await client.post(
                        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}",
                        json=payload,
                    )
                    if resp.status_code == 200:
                        sent += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1

        broadcast.sent_count = sent
        broadcast.delivered_count = sent
        broadcast.failed_count = failed
        broadcast.status = BroadcastStatus.sent
        broadcast.sent_at = datetime.now(timezone.utc)
        await db.commit()


def send_broadcast(broadcast_id: str):
    """Entry point called by RQ worker."""
    asyncio.run(_send(broadcast_id))
