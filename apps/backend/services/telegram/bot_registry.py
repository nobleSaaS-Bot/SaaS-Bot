"""
services/telegram/bot_registry.py

The central nervous system for multi-tenant bot routing.

Problem being solved
────────────────────
Every merchant has their own Telegram bot (separate bot token).  All those
bots register webhooks that point back to THIS FastAPI server.  When a
Telegram update arrives we must know:

    webhook_secret  →  { business_id, bot_token, store_id, status }

in under 1 ms — before any DB query — so we can dispatch to the right
tenant's handlers.

Architecture
────────────
  1. DB (source of truth)   BotConfig rows, persisted forever
  2. Redis (L1 cache)       webhook_secret → BotCacheEntry, TTL = 5 min
  3. Module-level dict      In-process cache, TTL = 30 s  (avoids Redis RTT
                             on every single update in high-traffic tenants)

Registration flow (when a merchant saves their bot token)
─────────────────────────────────────────────────────────
  register_bot()
    ├── call Telegram getMe  (validates token, gets username/id)
    ├── encrypt token        (core/security.py)
    ├── upsert BotConfig     (DB)
    ├── call Telegram setWebhook  (registers our URL)
    ├── warm Redis cache
    └── return BotConfig

Lookup flow (on every Telegram webhook POST)
────────────────────────────────────────────
  resolve_bot(webhook_secret)
    ├── check in-process cache  (O(1) dict lookup)
    ├── check Redis             (single GET)
    ├── fall back to DB         (SQL query, then warm caches)
    └── return BotCacheEntry | None

"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from core.security import decrypt_value, encrypt_value
from core.telegram_client import (
    TelegramAPIError,
    delete_webhook,
    get_me,
    get_webhook_info,
    set_webhook,
)
from models.bot_config import BotConfig, BotStatus

logger = logging.getLogger(__name__)

# ── Cache configuration ───────────────────────────────────────────────────────
REDIS_CACHE_TTL = 300       # 5 minutes
LOCAL_CACHE_TTL = 30        # 30 seconds
REDIS_KEY_PREFIX = "bot_registry:"


# ── Cache entry (what we keep in Redis and the local dict) ────────────────────

@dataclass
class BotCacheEntry:
    """
    Everything the webhook router needs about a bot, without hitting the DB.
    Intentionally does NOT contain the raw bot token — callers receive the
    decrypted token only when they explicitly call get_bot_token().
    """
    bot_config_id: str         # UUID string
    business_id: str           # UUID string
    bot_username: str
    telegram_bot_id: str
    status: str                # BotStatus value
    webhook_secret: str
    # token kept in Redis as an encrypted blob so it never travels in plaintext
    _token_encrypted: str = ""

    def is_active(self) -> bool:
        return self.status == BotStatus.ACTIVE

    def to_redis_payload(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_redis_payload(cls, raw: str) -> "BotCacheEntry":
        return cls(**json.loads(raw))

    @classmethod
    def from_db_row(cls, row: BotConfig) -> "BotCacheEntry":
        return cls(
            bot_config_id=str(row.id),
            business_id=str(row.business_id),
            bot_username=row.bot_username,
            telegram_bot_id=row.telegram_bot_id,
            status=row.status,
            webhook_secret=row.webhook_secret,
            _token_encrypted=row.bot_token_encrypted,
        )


# ── Local in-process cache ────────────────────────────────────────────────────
# Keyed by webhook_secret → (BotCacheEntry, expiry_timestamp)
_local_cache: dict[str, tuple[BotCacheEntry, float]] = {}


def _local_get(secret: str) -> BotCacheEntry | None:
    entry = _local_cache.get(secret)
    if entry and entry[1] > time.monotonic():
        return entry[0]
    _local_cache.pop(secret, None)
    return None


def _local_set(secret: str, entry: BotCacheEntry) -> None:
    _local_cache[secret] = (entry, time.monotonic() + LOCAL_CACHE_TTL)


def _local_delete(secret: str) -> None:
    _local_cache.pop(secret, None)


# ── BotRegistry ───────────────────────────────────────────────────────────────

class BotRegistry:
    """
    Singleton-style service.  Inject via FastAPI Depends or import directly.
    Requires a Redis client (aioredis / redis.asyncio) injected at startup.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client  # set via set_redis() at app startup

    def set_redis(self, redis_client) -> None:
        self._redis = redis_client

    # ── Redis helpers ─────────────────────────────────────────────────────

    def _rkey(self, webhook_secret: str) -> str:
        return f"{REDIS_KEY_PREFIX}{webhook_secret}"

    async def _redis_get(self, webhook_secret: str) -> BotCacheEntry | None:
        if not self._redis:
            return None
        try:
            raw = await self._redis.get(self._rkey(webhook_secret))
            if raw:
                return BotCacheEntry.from_redis_payload(raw)
        except Exception as exc:
            logger.warning("Redis GET failed for bot_registry: %s", exc)
        return None

    async def _redis_set(self, entry: BotCacheEntry) -> None:
        if not self._redis:
            return
        try:
            await self._redis.setex(
                self._rkey(entry.webhook_secret),
                REDIS_CACHE_TTL,
                entry.to_redis_payload(),
            )
        except Exception as exc:
            logger.warning("Redis SET failed for bot_registry: %s", exc)

    async def _redis_delete(self, webhook_secret: str) -> None:
        if not self._redis:
            return
        try:
            await self._redis.delete(self._rkey(webhook_secret))
        except Exception as exc:
            logger.warning("Redis DEL failed for bot_registry: %s", exc)

    # ── Core lookup (called on EVERY Telegram webhook POST) ───────────────

    async def resolve_bot(self, webhook_secret: str) -> BotCacheEntry | None:
        """
        Resolve a webhook_secret to a BotCacheEntry.

        Layer 1: local in-process dict  (synchronous, ~50 ns)
        Layer 2: Redis                  (~0.5 ms)
        Layer 3: PostgreSQL             (~5 ms, then warms L1+L2)

        Returns None if the secret is unknown or the bot is not ACTIVE.
        """
        # L1: in-process
        entry = _local_get(webhook_secret)
        if entry:
            return entry

        # L2: Redis
        entry = await self._redis_get(webhook_secret)
        if entry:
            _local_set(webhook_secret, entry)
            return entry

        # L3: Database
        async with async_session_factory() as db:
            row = await self._fetch_from_db(db, webhook_secret)
        if row is None:
            return None

        entry = BotCacheEntry.from_db_row(row)
        _local_set(webhook_secret, entry)
        await self._redis_set(entry)
        return entry

    async def _fetch_from_db(
        self, db: AsyncSession, webhook_secret: str
    ) -> BotConfig | None:
        result = await db.execute(
            select(BotConfig).where(BotConfig.webhook_secret == webhook_secret)
        )
        return result.scalar_one_or_none()

    # ── Get decrypted bot token (only when needed for API calls) ──────────

    async def get_bot_token(self, webhook_secret: str) -> str | None:
        """
        Returns the plaintext bot token for making Telegram API calls.
        Decrypts on the fly — never stored in plaintext in cache.
        """
        entry = await self.resolve_bot(webhook_secret)
        if not entry:
            return None
        return decrypt_value(entry._token_encrypted)

    async def get_bot_token_by_business(self, business_id: UUID | str) -> str | None:
        """
        Convenience: get the primary bot token for a business (for proactive
        messages, broadcasts, etc.)
        """
        async with async_session_factory() as db:
            result = await db.execute(
                select(BotConfig).where(
                    BotConfig.business_id == str(business_id),
                    BotConfig.is_primary == True,
                    BotConfig.status == BotStatus.ACTIVE,
                )
            )
            row = result.scalar_one_or_none()
        if not row:
            return None
        return decrypt_value(row.bot_token_encrypted)

    # ── Registration ──────────────────────────────────────────────────────

    async def register_bot(
        self,
        db: AsyncSession,
        business_id: UUID | str,
        raw_bot_token: str,
    ) -> BotConfig:
        """
        Full registration flow:
          1. Validate token with Telegram (getMe)
          2. Encrypt + persist BotConfig
          3. Register webhook with Telegram (setWebhook)
          4. Warm caches
          5. Return BotConfig (token_encrypted, never raw)

        Raises:
            TelegramAPIError: if token is invalid or setWebhook fails
            ValueError: if this bot is already registered to another business
        """
        # Step 1 — validate token, get bot identity
        bot_info = await get_me(raw_bot_token)
        telegram_bot_id = str(bot_info["id"])
        bot_username = bot_info["username"]
        bot_display_name = bot_info.get("first_name", bot_username)

        # Step 2 — check for conflicts (same Telegram bot registered to different business)
        existing = await db.execute(
            select(BotConfig).where(BotConfig.telegram_bot_id == telegram_bot_id)
        )
        existing_row: BotConfig | None = existing.scalar_one_or_none()

        if existing_row and str(existing_row.business_id) != str(business_id):
            raise ValueError(
                f"Bot @{bot_username} is already registered to a different business."
            )

        # Step 3 — upsert BotConfig
        if existing_row and str(existing_row.business_id) == str(business_id):
            # Re-registration: update token (merchant may have rotated it)
            bot_cfg = existing_row
            bot_cfg.bot_token_encrypted = encrypt_value(raw_bot_token)
            bot_cfg.bot_display_name = bot_display_name
            bot_cfg.status = BotStatus.PENDING
            logger.info("Re-registering bot @%s for business %s", bot_username, business_id)
        else:
            bot_cfg = BotConfig(
                business_id=str(business_id),
                bot_token_encrypted=encrypt_value(raw_bot_token),
                bot_username=bot_username,
                bot_display_name=bot_display_name,
                telegram_bot_id=telegram_bot_id,
                status=BotStatus.PENDING,
            )
            db.add(bot_cfg)
            await db.flush()  # get the generated id + webhook_secret

        # Step 4 — register webhook with Telegram
        webhook_url = _build_webhook_url(bot_cfg.webhook_secret)
        try:
            await set_webhook(
                raw_bot_token,
                url=webhook_url,
                secret_token=bot_cfg.webhook_secret,  # X-Telegram-Bot-Api-Secret-Token
                drop_pending_updates=False,
            )
            bot_cfg.status = BotStatus.ACTIVE
            bot_cfg.registered_webhook_url = webhook_url
            from datetime import datetime
            bot_cfg.webhook_registered_at = datetime.utcnow()
            bot_cfg.last_webhook_error = None
        except TelegramAPIError as exc:
            bot_cfg.status = BotStatus.WEBHOOK_FAILED
            bot_cfg.last_webhook_error = str(exc)
            await db.commit()
            raise

        await db.commit()
        await db.refresh(bot_cfg)

        # Step 5 — warm caches
        entry = BotCacheEntry.from_db_row(bot_cfg)
        _local_set(bot_cfg.webhook_secret, entry)
        await self._redis_set(entry)

        logger.info(
            "Bot registered: @%s → webhook %s (business=%s)",
            bot_username,
            webhook_url,
            business_id,
        )
        return bot_cfg

    # ── Deregistration / pause ────────────────────────────────────────────

    async def pause_bot(self, db: AsyncSession, bot_config_id: UUID | str) -> BotConfig:
        """
        Pause a bot: deleteWebhook from Telegram + mark PAUSED in DB.
        Incoming messages will still arrive (Telegram queues them) but
        the webhook handler will drop them until the bot is re-activated.
        """
        bot_cfg = await db.get(BotConfig, str(bot_config_id))
        if not bot_cfg:
            raise ValueError(f"BotConfig {bot_config_id} not found")

        raw_token = decrypt_value(bot_cfg.bot_token_encrypted)
        try:
            await delete_webhook(raw_token, drop_pending_updates=True)
        except TelegramAPIError as exc:
            logger.warning("deleteWebhook failed (marking paused anyway): %s", exc)

        bot_cfg.status = BotStatus.PAUSED
        await db.commit()

        # Invalidate caches
        _local_delete(bot_cfg.webhook_secret)
        await self._redis_delete(bot_cfg.webhook_secret)

        return bot_cfg

    async def revoke_bot(self, db: AsyncSession, bot_config_id: UUID | str) -> None:
        """
        Permanently remove a bot registration.  Deletes the webhook and
        marks the row REVOKED (soft-delete for audit trail).
        """
        bot_cfg = await db.get(BotConfig, str(bot_config_id))
        if not bot_cfg:
            return

        raw_token = decrypt_value(bot_cfg.bot_token_encrypted)
        try:
            await delete_webhook(raw_token)
        except TelegramAPIError:
            pass  # Best-effort — token may already be invalid

        _local_delete(bot_cfg.webhook_secret)
        await self._redis_delete(bot_cfg.webhook_secret)

        bot_cfg.status = BotStatus.REVOKED
        bot_cfg.bot_token_encrypted = ""  # Wipe token on revocation
        await db.commit()

    # ── Secret rotation ───────────────────────────────────────────────────

    async def rotate_webhook_secret(
        self, db: AsyncSession, bot_config_id: UUID | str
    ) -> BotConfig:
        """
        Generate a new webhook_secret and re-register with Telegram.
        Old secret is invalidated immediately (cache purge).

        Use when a webhook URL is suspected to have been leaked.
        """
        import secrets as _secrets

        bot_cfg = await db.get(BotConfig, str(bot_config_id))
        if not bot_cfg:
            raise ValueError(f"BotConfig {bot_config_id} not found")

        old_secret = bot_cfg.webhook_secret
        new_secret = _secrets.token_hex(32)

        raw_token = decrypt_value(bot_cfg.bot_token_encrypted)
        new_url = _build_webhook_url(new_secret)

        await set_webhook(raw_token, url=new_url, secret_token=new_secret)

        # Purge old caches before updating DB
        _local_delete(old_secret)
        await self._redis_delete(old_secret)

        bot_cfg.webhook_secret = new_secret
        bot_cfg.registered_webhook_url = new_url
        from datetime import datetime
        bot_cfg.webhook_registered_at = datetime.utcnow()
        await db.commit()
        await db.refresh(bot_cfg)

        # Warm new caches
        entry = BotCacheEntry.from_db_row(bot_cfg)
        _local_set(new_secret, entry)
        await self._redis_set(entry)

        logger.info("Rotated webhook secret for bot @%s", bot_cfg.bot_username)
        return bot_cfg

    # ── Webhook health status ─────────────────────────────────────────────

    async def get_webhook_status(self, bot_config_id: UUID | str, db: AsyncSession) -> dict:
        """
        Live status from Telegram's getWebhookInfo — for the BotSettings page.
        """
        bot_cfg = await db.get(BotConfig, str(bot_config_id))
        if not bot_cfg:
            raise ValueError(f"BotConfig {bot_config_id} not found")

        raw_token = decrypt_value(bot_cfg.bot_token_encrypted)
        info = await get_webhook_info(raw_token)
        return {
            "url": info.get("url", ""),
            "is_registered": bool(info.get("url")),
            "pending_update_count": info.get("pending_update_count", 0),
            "last_error_message": info.get("last_error_message"),
            "last_error_date": info.get("last_error_date"),
            "max_connections": info.get("max_connections", 40),
            "allowed_updates": info.get("allowed_updates", []),
            "db_status": bot_cfg.status,
        }


# ── Module-level singleton ────────────────────────────────────────────────────

bot_registry = BotRegistry()


# ── Private helpers ───────────────────────────────────────────────────────────

def _build_webhook_url(webhook_secret: str) -> str:
    """
    Constructs the full webhook URL for a given secret.
    e.g. https://api.yourdomain.com/webhooks/telegram/a3f9c1...
    """
    base = settings.API_BASE_URL.rstrip("/")
    return f"{base}/webhooks/telegram/{webhook_secret}"
