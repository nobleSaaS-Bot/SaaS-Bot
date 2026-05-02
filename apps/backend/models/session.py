from sqlalchemy import String, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class TelegramSession(Base):
    __tablename__ = "telegram_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    telegram_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    chat_id: Mapped[str] = mapped_column(String(100), nullable=False)
    current_flow_id: Mapped[str | None] = mapped_column(String)
    current_step: Mapped[str | None] = mapped_column(String(255))
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    cart: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_activity: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    store = relationship("Store")
