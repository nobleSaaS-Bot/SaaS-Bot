"""
services/telegram/context.py

TenantBotContext — injected into every handler call.
Encapsulates everything a handler needs about the current tenant,
without hitting the DB again per message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.telegram_client import (
    answer_callback_query,
    answer_pre_checkout_query,
    send_message,
    send_photo,
)


@dataclass
class TenantBotContext:
    """
    Immutable per-update context object.
    Handlers receive this instead of raw bot_token strings.
    """
    bot_token: str          # Decrypted — used only for Telegram API calls
    business_id: str
    store_id: str
    store_name: str
    bot_username: str
    currency: str
    plan: str               # "starter" | "growth" | "pro" — for feature gating

    # ── Convenience wrappers (so handlers don't touch bot_token directly) ──

    async def send(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
    ) -> dict:
        return await send_message(
            self.bot_token, chat_id, text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

    async def send_image(
        self,
        chat_id: int | str,
        photo: str,
        caption: str | None = None,
        reply_markup: dict | None = None,
    ) -> dict:
        return await send_photo(
            self.bot_token, chat_id, photo,
            caption=caption,
            reply_markup=reply_markup,
        )

    async def answer_callback(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> bool:
        return await answer_callback_query(
            self.bot_token, callback_query_id, text, show_alert
        )

    async def answer_pre_checkout(
        self,
        pre_checkout_query_id: str,
        ok: bool,
        error_message: str | None = None,
    ) -> bool:
        return await answer_pre_checkout_query(
            self.bot_token, pre_checkout_query_id, ok, error_message
        )

    def has_feature(self, feature: str) -> bool:
        """Simple plan-gate check. Expand as plans/features grow."""
        plan_features = {
            "starter": {"basic_store", "catalog", "checkout"},
            "growth": {"basic_store", "catalog", "checkout", "analytics", "discounts", "custom_flows"},
            "pro": {"basic_store", "catalog", "checkout", "analytics", "discounts",
                    "custom_flows", "broadcast", "multi_bot", "ai_support"},
        }
        return feature in plan_features.get(self.plan, set())
