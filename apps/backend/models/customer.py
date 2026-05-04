"""
models/customer.py

Tracks every Telegram user who has interacted with any merchant's bot.

Design notes
────────────
- One Customer row per (telegram_user_id, business_id) pair — same Telegram
  user can be a customer of multiple merchants without data leaking across.
- Denormalised aggregate columns (total_orders, total_spent, last_order_at)
  are updated by order_service.py on every order completion so the CRM
  page never needs expensive aggregate queries.
- `segments` is a PostgreSQL ARRAY of strings — e.g. ["vip", "repeat_buyer"].
  Kept simple; no separate segment table needed at this scale.
- `notes` is a freeform text field for the merchant to annotate customers.
- `is_blocked` lets merchants block abusive users from their bot.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # ── Tenant ownership ──────────────────────────────────────────────────
    business_id = Column(
        String,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Telegram identity ─────────────────────────────────────────────────
    telegram_user_id = Column(BigInteger, nullable=False)      # Telegram's numeric user ID
    telegram_username = Column(String(64), nullable=True)       # @handle (may be absent)
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    language_code = Column(String(8), nullable=True)            # "en", "am", "sw", etc.

    # ── Derived display name (computed on write) ──────────────────────────
    display_name = Column(String(256), nullable=False, default="Unknown")

    # ── Engagement stats (denormalised, updated by order_service) ─────────
    total_orders = Column(Integer, nullable=False, default=0)
    total_spent = Column(Float, nullable=False, default=0.0)
    average_order_value = Column(Float, nullable=False, default=0.0)
    last_order_at = Column(DateTime, nullable=True)
    first_order_at = Column(DateTime, nullable=True)

    # ── CRM fields ────────────────────────────────────────────────────────
    segments = Column(ARRAY(String), nullable=False, server_default="{}")
    notes = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=False, server_default="{}")

    # ── Bot interaction ───────────────────────────────────────────────────
    is_blocked = Column(Boolean, nullable=False, default=False)
    last_seen_at = Column(DateTime, nullable=True)
    message_count = Column(Integer, nullable=False, default=0)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────────────────
    business = relationship("Business", back_populates="customers")
    orders = relationship("Order", back_populates="customer", order_by="Order.created_at.desc()")

    __table_args__ = (
        UniqueConstraint("business_id", "telegram_user_id", name="uq_customer_per_business"),
        Index("ix_customers_business_id", "business_id"),
        Index("ix_customers_telegram_user_id", "telegram_user_id"),
        Index("ix_customers_total_spent", "business_id", "total_spent"),
        Index("ix_customers_last_order_at", "business_id", "last_order_at"),
    )

    @property
    def computed_display_name(self) -> str:
        parts = [p for p in [self.first_name, self.last_name] if p]
        if parts:
            return " ".join(parts)
        if self.telegram_username:
            return f"@{self.telegram_username}"
        return f"User {self.telegram_user_id}"

    def auto_segment(self) -> list[str]:
        """
        Compute automatic segments based on behaviour.
        Called by order_service after each order update.
        """
        segs = []
        if self.total_orders >= 5:
            segs.append("repeat_buyer")
        if self.total_spent >= 500:
            segs.append("vip")
        if self.total_orders == 1:
            segs.append("new")
        if self.last_order_at:
            from datetime import timedelta
            days_since = (datetime.utcnow() - self.last_order_at).days
            if days_since > 60:
                segs.append("at_risk")
        return segs

    def __repr__(self) -> str:
        return f"<Customer {self.display_name} (tg={self.telegram_user_id}) business={self.business_id}>"
