"""
RQ worker job: send a broadcast message to all matching customers via Telegram.

Uses the per-business bot token from BotConfig (active bot for that business)
when available, falling back to the global TELEGRAM_BOT_TOKEN env var.
"""
import asyncio
import httpx
from datetime import datetime, timezone
from sqlalchemy import select, and_

from app.database import AsyncSessionLocal
from models.broadcast import Broadcast, BroadcastStatus, BroadcastSegment
from models.customer import Customer
from app.config import settings

# Map BroadcastSegment → customer ARRAY segment string
_SEGMENT_MAP: dict[str, str | None] = {
    BroadcastSegment.all:     None,
    BroadcastSegment.new:     "new",
    BroadcastSegment.regular: "repeat_buyer",
    BroadcastSegment.vip:     "vip",
    BroadcastSegment.at_risk: "at_risk",
    BroadcastSegment.churned: "at_risk",  # churned ≈ at_risk
}


async def _get_bot_token(db, business_id: str) -> str:
    """Return the active bot token for this business, or the global fallback."""
    try:
        from models.bot_config import BotConfig, BotStatus
        from core.security import decrypt_value
        result = await db.execute(
            select(BotConfig).where(
                BotConfig.business_id == str(business_id),
                BotConfig.status == BotStatus.ACTIVE,
                BotConfig.is_primary == True,
            )
        )
        cfg = result.scalar_one_or_none()
        if cfg:
            return decrypt_value(cfg.bot_token_encrypted)
    except Exception:
        pass
    return settings.TELEGRAM_BOT_TOKEN


async def _send(broadcast_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Broadcast).where(Broadcast.id == broadcast_id))
        broadcast = result.scalar_one_or_none()
        if not broadcast:
            return

        # Fetch target customers
        filters = [
            Customer.business_id == str(broadcast.business_id),
            Customer.is_blocked == False,
        ]

        seg_string = _SEGMENT_MAP.get(broadcast.segment)
        if seg_string is not None:
            filters.append(Customer.segments.contains([seg_string]))

        customers_result = await db.execute(select(Customer).where(and_(*filters)))
        customers = customers_result.scalars().all()

        broadcast.total_recipients = len(customers)
        sent = 0
        failed = 0

        bot_token = await _get_bot_token(db, broadcast.business_id)

        async with httpx.AsyncClient(timeout=10) as client:
            for customer in customers:
                try:
                    payload: dict = {
                        "chat_id": customer.telegram_user_id,
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
                        f"https://api.telegram.org/bot{bot_token}/{method}",
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
