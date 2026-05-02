from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import hmac
import hashlib

from app.config import settings
from services.telegram.bot_service import handle_telegram_update

router = APIRouter()


@router.post("/")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    update = await request.json()
    await handle_telegram_update(update)
    return {"ok": True}
