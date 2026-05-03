"""
services/telegram/dispatch.py

Converts a raw Telegram update dict into a typed command and routes it
to the correct handler function with full tenant context injected.

This is the bridge between the stateless webhook receiver (which knows
only webhook_secret → bot_token) and the stateful handler layer
(which needs business_id, store config, session state, etc.).

Update type routing
───────────────────
  message                → on_message()
    ├── /start [payload] → on_start()
    ├── /help            → on_help()
    └── text / photo     → on_message()
  callback_query         → on_callback_query()
  pre_checkout_query     → on_pre_checkout_query()
  successful_payment     → on_successful_payment()
"""

from __future__ import annotations

import logging
from typing import Any

from app.database import async_session_factory
from models.bot_config import BotConfig
from models.store import Store
from services.telegram.context import TenantBotContext
from services.telegram.handlers import (
    on_callback_query,
    on_message,
    on_pre_checkout_query,
    on_start,
    on_successful_payment,
)

logger = logging.getLogger(__name__)


async def dispatch_update(
    update: dict[str, Any],
    bot_token: str,
    business_id: str,
    bot_username: str,
) -> None:
    """
    Main dispatch entry point called by the webhook receiver.

    Builds a TenantBotContext from the DB (store config, plan, etc.)
    then routes to the appropriate handler.
    """
    ctx = await _build_context(bot_token, business_id, bot_username)
    if ctx is None:
        logger.warning("Could not build context for business %s — skipping update", business_id)
        return

    update_id = update.get("update_id")
    logger.debug("Dispatching update_id=%s for @%s", update_id, bot_username)

    # ── Route by update type ──────────────────────────────────────────────

    if "message" in update:
        message = update["message"]

        # Check for successful_payment inside message
        if "successful_payment" in message:
            await on_successful_payment(ctx, message)
            return

        # Command routing
        text: str = message.get("text", "")
        if text.startswith("/start"):
            payload = text[len("/start"):].strip()
            await on_start(ctx, message, payload=payload)
            return

        await on_message(ctx, message)

    elif "callback_query" in update:
        await on_callback_query(ctx, update["callback_query"])

    elif "pre_checkout_query" in update:
        await on_pre_checkout_query(ctx, update["pre_checkout_query"])

    else:
        logger.debug("Unhandled update type in update_id=%s", update_id)


# ── Context builder ───────────────────────────────────────────────────────────

async def _build_context(
    bot_token: str,
    business_id: str,
    bot_username: str,
) -> TenantBotContext | None:
    """
    Loads the active Store for this business and assembles a TenantBotContext.
    Returns None if no active store is found.
    """
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(
            select(Store).where(
                Store.business_id == business_id,
                Store.is_active == True,
            )
        )
        store = result.scalar_one_or_none()

    if store is None:
        logger.warning("No active store for business %s", business_id)
        return None

    return TenantBotContext(
        bot_token=bot_token,
        business_id=business_id,
        store_id=str(store.id),
        store_name=store.name,
        bot_username=bot_username,
        currency=store.currency or "USD",
        plan=store.plan or "starter",
    )
