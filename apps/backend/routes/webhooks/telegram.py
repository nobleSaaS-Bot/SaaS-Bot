"""
routes/webhooks/telegram.py

Handles incoming Telegram webhook POSTs for both:

1. Multi-tenant (new):  POST /{webhook_secret}
   Each merchant bot has a unique URL segment (webhook_secret).
   The bot_registry resolves secret → { business_id, bot_token, bot_username }
   and dispatch_update() routes to the correct tenant handlers.

2. Legacy (fallback):   POST /
   Uses global TELEGRAM_WEBHOOK_SECRET header validation.
   Delegates to the old single-bot handle_telegram_update().
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Multi-tenant webhook (per-bot secret in URL) ──────────────────────────────

@router.post("/{webhook_secret}")
async def telegram_webhook_multitenant(
    webhook_secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    """
    Receives updates for a specific merchant bot identified by webhook_secret.
    The bot_registry resolves the secret to tenant credentials and dispatches.
    """
    from services.telegram.bot_registry import bot_registry
    from core.security import decrypt_value

    # Fast cache lookup — no DB hit on the hot path
    entry = await bot_registry.get_entry(webhook_secret)
    if entry is None:
        # Unknown secret — return 200 so Telegram doesn't retry
        logger.warning("Unknown webhook_secret received: %s…", webhook_secret[:8])
        return {"ok": True}

    # Validate the Telegram-signed secret header
    if x_telegram_bot_api_secret_token != webhook_secret:
        logger.warning("Secret header mismatch for bot @%s", entry.bot_username)
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    if not entry.is_active:
        logger.info("Update received for paused bot @%s — dropping", entry.bot_username)
        return {"ok": True}

    update = await request.json()

    try:
        raw_token = decrypt_value(entry._token_encrypted)
        from services.telegram.dispatch import dispatch_update
        await dispatch_update(
            update=update,
            bot_token=raw_token,
            business_id=entry.business_id,
            bot_username=entry.bot_username,
        )
    except Exception as exc:
        logger.exception("Error dispatching update for @%s: %s", entry.bot_username, exc)

    return {"ok": True}


# ── Legacy single-bot webhook (root path) ─────────────────────────────────────

@router.post("/")
async def telegram_webhook_legacy(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    """
    Legacy webhook handler for a single global bot.
    Validates against TELEGRAM_WEBHOOK_SECRET env var.
    """
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    update = await request.json()

    try:
        from services.telegram.bot_service import handle_telegram_update
        await handle_telegram_update(update)
    except Exception as exc:
        logger.exception("Error in legacy webhook handler: %s", exc)

    return {"ok": True}
