from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id: Mapped[str] = mapped_column(String, ForeignKey("businesses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    subdomain: Mapped[str | None] = mapped_column(String(100), unique=True)
    custom_domain: Mapped[str | None] = mapped_column(String(255), unique=True)
    telegram_bot_token: Mapped[str | None] = mapped_column(String(255))
    telegram_bot_username: Mapped[str | None] = mapped_column(String(100))
    logo_url: Mapped[str | None] = mapped_column(Text)
    banner_url: Mapped[str | None] = mapped_column(Text)
    theme: Mapped[dict | None] = mapped_column(JSON)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    business = relationship("Business", back_populates="stores")
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="store", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="store")
    flows = relationship("Flow", back_populates="store", cascade="all, delete-orphan")
