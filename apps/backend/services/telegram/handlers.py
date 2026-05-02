from app.database import AsyncSessionLocal
from models.session import TelegramSession
from flow_engine import FlowEngine
from sqlalchemy import select


async def handle_message(message: dict) -> None:
    chat_id = str(message["chat"]["id"])
    user_id = str(message["from"]["id"])
    text = message.get("text", "")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramSession).where(
                TelegramSession.telegram_user_id == user_id,
                TelegramSession.is_active == True,
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            from services.telegram.ui_components import send_welcome_message
            await send_welcome_message(chat_id)
            return

        engine = FlowEngine(db)
        await engine.process_message(session, text, message)


async def handle_callback_query(callback_query: dict) -> None:
    chat_id = str(callback_query["message"]["chat"]["id"])
    user_id = str(callback_query["from"]["id"])
    data = callback_query.get("data", "")
    callback_id = callback_query["id"]

    from services.telegram.bot_service import answer_callback_query
    await answer_callback_query(callback_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramSession).where(
                TelegramSession.telegram_user_id == user_id,
                TelegramSession.is_active == True,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            return

        engine = FlowEngine(db)
        await engine.process_callback(session, data, callback_query)
