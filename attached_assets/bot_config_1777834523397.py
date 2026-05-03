"""
models/bot_config.py

Stores per-tenant Telegram bot configuration.
Each Business can register one (or more, if plan allows) Telegram bots.
The webhook_secret is the unique URL segment that Telegram posts to:

    POST /webhooks/telegram/{webhook_secret}

This is how a single FastAPI server handles N merchant bots without any
shared state in the URL path or headers.
"""

import secrets
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class BotStatus(str, PyEnum):
    PENDING = "pending"          # Token added, webhook not yet registered
    ACTIVE = "active"            # Webhook registered, bot is live
    PAUSED = "paused"            # Merchant paused the bot (no new messages processed)
    WEBHOOK_FAILED = "webhook_failed"  # setWebhook call to Telegram failed
    REVOKED = "revoked"          # Token invalid / rotated by merchant


class BotConfig(Base):
    """
    One row per merchant bot.
    Relationship: Business 1──* BotConfig (multi-bot plans allow >1)
    """
    __tablename__ = "bot_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Tenant ownership ──────────────────────────────────────────────────
    business_id = Column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Telegram credentials ──────────────────────────────────────────────
    # Stored encrypted at rest (see core/security.py encrypt_value).
    # Never logged, never returned in API responses.
    bot_token_encrypted = Column(Text, nullable=False)

    # Bot identity fetched from Telegram's getMe endpoint on registration
    bot_username = Column(String(64), nullable=False, index=True)
    bot_display_name = Column(String(128), nullable=True)
    telegram_bot_id = Column(String(32), nullable=False, unique=True)

    # ── Webhook routing ───────────────────────────────────────────────────
    # Cryptographically random secret that forms the webhook URL segment.
    # 32 bytes → 64 hex chars.  Rotatable via the /bots/{id}/rotate-secret
    # endpoint without changing the bot token.
    webhook_secret = Column(
        String(64),
        nullable=False,
        unique=True,
        default=lambda: secrets.token_hex(32),
    )

    # Full webhook URL that was registered with Telegram (for display/debug)
    registered_webhook_url = Column(Text, nullable=True)

    # ── State ─────────────────────────────────────────────────────────────
    status = Column(
        Enum(BotStatus, name="bot_status_enum"),
        nullable=False,
        default=BotStatus.PENDING,
    )
    is_primary = Column(Boolean, nullable=False, default=True)
    last_webhook_error = Column(Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    webhook_registered_at = Column(DateTime, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    business = relationship("Business", back_populates="bot_configs")

    __table_args__ = (
        # A business can't register the same Telegram bot twice
        UniqueConstraint("business_id", "telegram_bot_id", name="uq_business_telegram_bot"),
        Index("ix_bot_configs_webhook_secret", "webhook_secret"),  # hot lookup path
        Index("ix_bot_configs_business_status", "business_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<BotConfig @{self.bot_username} business={self.business_id} status={self.status}>"
