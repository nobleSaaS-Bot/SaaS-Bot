"""
routes/bots.py

Bot management API — lets merchants register, inspect, pause, and rotate
their Telegram bot tokens from the BotSettings.jsx dashboard page.

All endpoints require JWT auth and enforce that the requesting merchant
can only manage their own business's bots (no cross-tenant access).

Endpoints
─────────
POST   /bots/register               Register a new bot token
GET    /bots                        List all bots for current business
GET    /bots/{bot_id}               Get a single bot's details
GET    /bots/{bot_id}/webhook-status  Live Telegram webhook health check
PATCH  /bots/{bot_id}/pause         Pause the bot (stop processing updates)
PATCH  /bots/{bot_id}/activate      Re-activate a paused bot
POST   /bots/{bot_id}/rotate-secret Rotate the webhook URL secret
DELETE /bots/{bot_id}               Revoke + soft-delete the bot
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from core.security import get_current_business  # JWT dep → returns Business
from core.telegram_client import TelegramAPIError
from models.bot_config import BotConfig, BotStatus
from services.telegram.bot_registry import bot_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bots", tags=["bots"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class RegisterBotRequest(BaseModel):
    bot_token: str = Field(
        ...,
        min_length=30,
        description="Bot token from @BotFather — format: 123456:ABC-DEF...",
    )


class BotResponse(BaseModel):
    id: str
    business_id: str
    bot_username: str
    bot_display_name: Optional[str]
    telegram_bot_id: str
    status: str
    is_primary: bool
    registered_webhook_url: Optional[str]
    webhook_registered_at: Optional[str]
    created_at: str

    # Never include bot_token_encrypted in any response
    class Config:
        from_attributes = True

    @classmethod
    def from_orm_safe(cls, row: BotConfig) -> "BotResponse":
        return cls(
            id=str(row.id),
            business_id=str(row.business_id),
            bot_username=row.bot_username,
            bot_display_name=row.bot_display_name,
            telegram_bot_id=row.telegram_bot_id,
            status=row.status,
            is_primary=row.is_primary,
            registered_webhook_url=row.registered_webhook_url,
            webhook_registered_at=row.webhook_registered_at.isoformat() if row.webhook_registered_at else None,
            created_at=row.created_at.isoformat(),
        )


class WebhookStatusResponse(BaseModel):
    url: str
    is_registered: bool
    pending_update_count: int
    last_error_message: Optional[str]
    last_error_date: Optional[int]
    max_connections: int
    allowed_updates: list[str]
    db_status: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=BotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a Telegram bot for the current merchant",
)
async def register_bot(
    body: RegisterBotRequest,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    """
    Validates the bot token with Telegram, stores it encrypted, and
    registers the webhook URL.  Returns the BotConfig (no token in response).
    """
    try:
        bot_cfg = await bot_registry.register_bot(
            db=db,
            business_id=business.id,
            raw_bot_token=body.bot_token,
        )
    except TelegramAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Telegram rejected the bot token: {exc.description}",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return BotResponse.from_orm_safe(bot_cfg)


@router.get(
    "",
    response_model=list[BotResponse],
    summary="List all bots for the current merchant",
)
async def list_bots(
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    result = await db.execute(
        select(BotConfig)
        .where(
            BotConfig.business_id == str(business.id),
            BotConfig.status != BotStatus.REVOKED,
        )
        .order_by(BotConfig.created_at.desc())
    )
    rows = result.scalars().all()
    return [BotResponse.from_orm_safe(r) for r in rows]


@router.get(
    "/{bot_id}",
    response_model=BotResponse,
    summary="Get a single bot config",
)
async def get_bot(
    bot_id: UUID,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    bot_cfg = await _get_owned_bot(db, bot_id, business.id)
    return BotResponse.from_orm_safe(bot_cfg)


@router.get(
    "/{bot_id}/webhook-status",
    response_model=WebhookStatusResponse,
    summary="Live webhook health from Telegram's getWebhookInfo",
)
async def get_webhook_status(
    bot_id: UUID,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    """
    Calls Telegram's getWebhookInfo and returns live status.
    Used by BotSettings.jsx to show real-time webhook health.
    """
    await _get_owned_bot(db, bot_id, business.id)  # ownership check

    try:
        status_data = await bot_registry.get_webhook_status(bot_id, db)
    except TelegramAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach Telegram API: {exc.description}",
        )

    return WebhookStatusResponse(**status_data)


@router.patch(
    "/{bot_id}/pause",
    response_model=BotResponse,
    summary="Pause bot — stops processing incoming Telegram updates",
)
async def pause_bot(
    bot_id: UUID,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    await _get_owned_bot(db, bot_id, business.id)

    try:
        bot_cfg = await bot_registry.pause_bot(db, bot_id)
    except TelegramAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return BotResponse.from_orm_safe(bot_cfg)


@router.patch(
    "/{bot_id}/activate",
    response_model=BotResponse,
    summary="Re-activate a paused bot by re-registering its webhook",
)
async def activate_bot(
    bot_id: UUID,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    bot_cfg = await _get_owned_bot(db, bot_id, business.id)

    # Re-register the webhook with the existing token + existing secret
    from core.security import decrypt_value
    from services.telegram.bot_registry import _build_webhook_url
    from core.telegram_client import set_webhook
    from datetime import datetime

    raw_token = decrypt_value(bot_cfg.bot_token_encrypted)
    try:
        await set_webhook(
            raw_token,
            url=_build_webhook_url(bot_cfg.webhook_secret),
            secret_token=bot_cfg.webhook_secret,
        )
    except TelegramAPIError as exc:
        bot_cfg.status = BotStatus.WEBHOOK_FAILED
        bot_cfg.last_webhook_error = str(exc)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"setWebhook failed: {exc.description}")

    bot_cfg.status = BotStatus.ACTIVE
    bot_cfg.last_webhook_error = None
    bot_cfg.webhook_registered_at = datetime.utcnow()
    await db.commit()
    await db.refresh(bot_cfg)

    # Warm caches
    from services.telegram.bot_registry import BotCacheEntry, _local_set
    entry = BotCacheEntry.from_db_row(bot_cfg)
    _local_set(bot_cfg.webhook_secret, entry)
    await bot_registry._redis_set(entry)

    return BotResponse.from_orm_safe(bot_cfg)


@router.post(
    "/{bot_id}/rotate-secret",
    response_model=BotResponse,
    summary="Rotate the webhook URL secret (invalidates old webhook URL)",
)
async def rotate_secret(
    bot_id: UUID,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    """
    Generates a new webhook_secret, calls setWebhook with the new URL,
    and invalidates the old URL.  Use if the webhook URL is compromised.
    """
    await _get_owned_bot(db, bot_id, business.id)

    try:
        bot_cfg = await bot_registry.rotate_webhook_secret(db, bot_id)
    except TelegramAPIError as exc:
        raise HTTPException(status_code=502, detail=f"Rotation failed: {exc.description}")

    return BotResponse.from_orm_safe(bot_cfg)


@router.delete(
    "/{bot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke and soft-delete a bot registration",
)
async def revoke_bot(
    bot_id: UUID,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    await _get_owned_bot(db, bot_id, business.id)
    await bot_registry.revoke_bot(db, bot_id)


# ── Ownership guard ───────────────────────────────────────────────────────────

async def _get_owned_bot(
    db: AsyncSession, bot_id: UUID, business_id
) -> BotConfig:
    """
    Fetch a BotConfig, asserting it belongs to the requesting business.
    Raises 404 if not found, 403 if owned by a different business.
    """
    bot_cfg = await db.get(BotConfig, str(bot_id))

    if bot_cfg is None or bot_cfg.status == BotStatus.REVOKED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    if str(bot_cfg.business_id) != str(business_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return bot_cfg
