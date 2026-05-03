"""
services/telegram/handlers.py

Handler functions called by dispatch.py with a fully-built TenantBotContext.
Each function receives ctx (TenantBotContext) + the relevant Telegram object.

Handlers also upsert the Customer row on every message so the CRM stays
up to date without any extra work in dispatch.
"""
from __future__ import annotations

import logging
from typing import Any

from app.database import async_session_factory
from models.session import TelegramSession
from flow_engine import FlowEngine
from sqlalchemy import select

logger = logging.getLogger(__name__)


# ── Customer upsert helper (imported from routes to avoid circular imports) ──

async def _upsert_customer(ctx, tg_user: dict) -> None:
    """Silently upsert the customer — never blocks the handler."""
    try:
        from routes.customers import upsert_customer_from_telegram
        async with async_session_factory() as db:
            await upsert_customer_from_telegram(db, ctx.business_id, tg_user)
            await db.commit()
    except Exception as exc:
        logger.warning("upsert_customer failed: %s", exc)


# ── Handlers (called by dispatch.py) ─────────────────────────────────────────

async def on_start(ctx, message: dict[str, Any], payload: str = "") -> None:
    """Handle /start [deep-link-payload]."""
    tg_user = message.get("from", {})
    await _upsert_customer(ctx, tg_user)

    await ctx.send(
        chat_id=message["chat"]["id"],
        text=(
            f"👋 Welcome to <b>{ctx.store_name}</b>!\n\n"
            "Browse our catalogue, place orders, and track deliveries — all right here."
        ),
    )


async def on_message(ctx, message: dict[str, Any]) -> None:
    """Handle regular text / photo messages."""
    tg_user = message.get("from", {})
    await _upsert_customer(ctx, tg_user)

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    async with async_session_factory() as db:
        result = await db.execute(
            select(TelegramSession).where(
                TelegramSession.telegram_user_id == str(tg_user.get("id", "")),
                TelegramSession.is_active == True,
            )
        )
        session = result.scalar_one_or_none()

        if session:
            engine = FlowEngine(db)
            await engine.process_message(session, text, message)
        else:
            from services.telegram.ui_components import send_welcome_message
            await send_welcome_message(chat_id)


async def on_callback_query(ctx, callback_query: dict[str, Any]) -> None:
    """Handle inline button taps."""
    tg_user = callback_query.get("from", {})
    await _upsert_customer(ctx, tg_user)

    chat_id = callback_query["message"]["chat"]["id"]
    data = callback_query.get("data", "")
    callback_id = callback_query["id"]

    await ctx.answer_callback(callback_id)

    async with async_session_factory() as db:
        result = await db.execute(
            select(TelegramSession).where(
                TelegramSession.telegram_user_id == str(tg_user.get("id", "")),
                TelegramSession.is_active == True,
            )
        )
        session = result.scalar_one_or_none()
        if session:
            engine = FlowEngine(db)
            await engine.process_callback(session, data, callback_query)


async def on_pre_checkout_query(ctx, query: dict[str, Any]) -> None:
    """Approve all pre-checkout queries (payment step)."""
    await ctx.answer_pre_checkout(query["id"], ok=True)


async def on_successful_payment(ctx, message: dict[str, Any]) -> None:
    """Handle confirmed Telegram payment."""
    tg_user = message.get("from", {})
    payment = message["successful_payment"]
    chat_id = message["chat"]["id"]

    logger.info(
        "Successful payment: %s %s from tg_user=%s",
        payment.get("total_amount"),
        payment.get("currency"),
        tg_user.get("id"),
    )

    await ctx.send(
        chat_id=chat_id,
        text="✅ <b>Payment confirmed!</b> Your order is being processed.",
    )


# ── Legacy function names kept for backwards compatibility ────────────────────

async def handle_message(message: dict) -> None:
    """Legacy entry point — used before dispatch.py was integrated."""
    chat_id = str(message["chat"]["id"])
    user_id = str(message["from"]["id"])
    text = message.get("text", "")

    async with async_session_factory() as db:
        result = await db.execute(
            select(TelegramSession).where(
                TelegramSession.telegram_user_id == user_id,
                TelegramSession.is_active == True,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            from services.telegram.ui_components import send_welcome_message
            await send_welcome_message(chat_id)
            return
        engine = FlowEngine(db)
        await engine.process_message(session, text, message)


async def handle_callback_query(callback_query: dict) -> None:
    """Legacy entry point."""
    user_id = str(callback_query["from"]["id"])
    data = callback_query.get("data", "")
    callback_id = callback_query["id"]

    from services.telegram.bot_service import answer_callback_query
    await answer_callback_query(callback_id)

    async with async_session_factory() as db:
        result = await db.execute(
            select(TelegramSession).where(
                TelegramSession.telegram_user_id == user_id,
                TelegramSession.is_active == True,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            return
        engine = FlowEngine(db)
        await engine.process_callback(session, data, callback_query)
