"""
services/telegram/bot_service.py

Legacy single-bot Telegram helpers. All API calls use the global
TELEGRAM_BOT_TOKEN. For multi-tenant bots use core/telegram_client.py directly.
"""
import httpx
from app.config import settings

TELEGRAM_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


async def send_message(chat_id: str, text: str, reply_markup: dict | None = None, parse_mode: str = "HTML") -> dict:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
        return response.json()


async def send_photo(chat_id: str, photo_url: str, caption: str | None = None, reply_markup: dict | None = None) -> dict:
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{TELEGRAM_API}/sendPhoto", json=payload)
        return response.json()


async def answer_callback_query(callback_query_id: str, text: str | None = None) -> dict:
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{TELEGRAM_API}/answerCallbackQuery", json=payload)
        return response.json()


async def handle_telegram_update(update: dict) -> None:
    """Legacy single-bot update handler — delegates to handlers module."""
    # Lazy import to break the circular dependency:
    # bot_service ← handlers (which used to import answer_callback_query from here)
    from services.telegram.handlers import handle_message, handle_callback_query
    if "message" in update:
        await handle_message(update["message"])
    elif "callback_query" in update:
        await handle_callback_query(update["callback_query"])


async def set_webhook(webhook_url: str, secret: str | None = None) -> dict:
    payload = {"url": webhook_url}
    if secret:
        payload["secret_token"] = secret
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{TELEGRAM_API}/setWebhook", json=payload)
        return response.json()
