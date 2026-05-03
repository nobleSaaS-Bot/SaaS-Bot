"""
core/telegram_client.py

Thin async wrapper around the Telegram Bot API.
Stateless — takes a bot_token per call, so it works for any tenant's bot
without maintaining long-lived Application objects per merchant.

All methods raise TelegramAPIError on non-2xx responses so callers can
handle failures uniformly.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT = 15  # seconds


class TelegramAPIError(Exception):
    """Raised when the Telegram API returns ok=false or a non-2xx status."""

    def __init__(self, method: str, description: str, error_code: int | None = None):
        self.method = method
        self.description = description
        self.error_code = error_code
        super().__init__(f"Telegram API [{method}] error {error_code}: {description}")


# ── Shared async client (connection-pooled) ───────────────────────────────────
# Instantiated once at module level; safe for concurrent use.
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
    return _http_client


async def close_http_client() -> None:
    """Call on app shutdown to drain the connection pool."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()


# ── Core request helper ───────────────────────────────────────────────────────

async def _call(bot_token: str, method: str, **params: Any) -> dict:
    """
    POST to https://api.telegram.org/bot{token}/{method} with JSON params.
    Returns the `result` field on success, raises TelegramAPIError on failure.
    """
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/{method}"
    client = get_http_client()

    try:
        response = await client.post(url, json={k: v for k, v in params.items() if v is not None})
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise TelegramAPIError(method, str(exc), exc.response.status_code) from exc
    except httpx.RequestError as exc:
        raise TelegramAPIError(method, f"Network error: {exc}") from exc

    data = response.json()
    if not data.get("ok"):
        raise TelegramAPIError(
            method,
            data.get("description", "Unknown error"),
            data.get("error_code"),
        )

    return data["result"]


# ── Public API methods ────────────────────────────────────────────────────────

async def get_me(bot_token: str) -> dict:
    """
    Validate a bot token and return bot identity.
    Returns: { id, is_bot, first_name, username, ... }
    Raises TelegramAPIError if token is invalid.
    """
    return await _call(bot_token, "getMe")


async def set_webhook(
    bot_token: str,
    url: str,
    secret_token: str | None = None,
    allowed_updates: list[str] | None = None,
    max_connections: int = 40,
    drop_pending_updates: bool = False,
) -> bool:
    """
    Register (or re-register) the webhook URL for this bot.

    secret_token: If set, Telegram will include X-Telegram-Bot-Api-Secret-Token
                  header in every webhook POST. We use this for signature verification.
    """
    result = await _call(
        bot_token,
        "setWebhook",
        url=url,
        secret_token=secret_token,
        allowed_updates=allowed_updates or ["message", "callback_query", "pre_checkout_query"],
        max_connections=max_connections,
        drop_pending_updates=drop_pending_updates,
    )
    logger.info("setWebhook registered: %s", url)
    return bool(result)


async def delete_webhook(bot_token: str, drop_pending_updates: bool = False) -> bool:
    """Remove the webhook (useful when pausing or revoking a bot)."""
    result = await _call(
        bot_token,
        "deleteWebhook",
        drop_pending_updates=drop_pending_updates,
    )
    return bool(result)


async def get_webhook_info(bot_token: str) -> dict:
    """
    Returns current webhook status from Telegram.
    Useful for the BotSettings dashboard page.
    Fields: url, has_custom_certificate, pending_update_count, last_error_message, ...
    """
    return await _call(bot_token, "getWebhookInfo")


async def send_message(
    bot_token: str,
    chat_id: int | str,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: dict | None = None,
    disable_notification: bool = False,
) -> dict:
    return await _call(
        bot_token,
        "sendMessage",
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        disable_notification=disable_notification,
    )


async def send_photo(
    bot_token: str,
    chat_id: int | str,
    photo: str,  # URL or file_id
    caption: str | None = None,
    parse_mode: str = "HTML",
    reply_markup: dict | None = None,
) -> dict:
    return await _call(
        bot_token,
        "sendPhoto",
        chat_id=chat_id,
        photo=photo,
        caption=caption,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


async def answer_callback_query(
    bot_token: str,
    callback_query_id: str,
    text: str | None = None,
    show_alert: bool = False,
) -> bool:
    return await _call(
        bot_token,
        "answerCallbackQuery",
        callback_query_id=callback_query_id,
        text=text,
        show_alert=show_alert,
    )


async def answer_pre_checkout_query(
    bot_token: str,
    pre_checkout_query_id: str,
    ok: bool,
    error_message: str | None = None,
) -> bool:
    return await _call(
        bot_token,
        "answerPreCheckoutQuery",
        pre_checkout_query_id=pre_checkout_query_id,
        ok=ok,
        error_message=error_message,
    )
