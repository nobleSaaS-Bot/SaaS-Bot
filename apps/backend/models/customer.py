from sqlalchemy import String, Text, DateTime, ForeignKey, Numeric, Integer, Boolean, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.database import Base


class CustomerSegment(str, enum.Enum):
    new = "new"
    regular = "regular"
    vip = "vip"
    at_risk = "at_risk"
    churned = "churned"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id: Mapped[str] = mapped_column(String, ForeignKey("businesses.id"), nullable=False)
    store_id: Mapped[str | None] = mapped_column(String, ForeignKey("stores.id"), nullable=True)

    telegram_id: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    username: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(10))
    photo_url: Mapped[str | None] = mapped_column(Text)

    segment: Mapped[CustomerSegment] = mapped_column(
        Enum(CustomerSegment), default=CustomerSegment.new, nullable=False
    )
    tags: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)

    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    last_order_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    business = relationship("Business", back_populates="customers")
    store = relationship("Store", back_populates="customers")
