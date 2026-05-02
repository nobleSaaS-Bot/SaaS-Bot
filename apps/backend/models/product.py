from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Numeric, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    category_id: Mapped[str | None] = mapped_column(String, ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    compare_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    sku: Mapped[str | None] = mapped_column(String(100))
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=False)
    images: Mapped[list | None] = mapped_column(JSON)
    variants: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    store = relationship("Store", back_populates="products")
    category = relationship("Category", back_populates="products")
