from app.database import AsyncSessionLocal
from models.session import TelegramSession
from flow_engine import FlowEngine
from sqlalchemy import select
from routes.customers import upsert_customer_from_telegram
from services.telegram.context import TenantBotContext # Import your context type

async def on_message(ctx: TenantBotContext, message: dict) -> None:
    chat_id = str(message["chat"]["id"])
    user_id = str(message["from"]["id"])
    text = message.get("text", "")

    async with AsyncSessionLocal() as db:
        # 1. Architecture Addition: Track/Update Customer using injected ctx
        customer = await upsert_customer_from_telegram(db, ctx.business_id, message["from"])

        # 2. Existing Session Logic
        result = await db.execute(
            select(TelegramSession).where(
                TelegramSession.telegram_user_id == user_id,
                TelegramSession.is_active == True,
                TelegramSession.store_id == ctx.store_id # Filter by store for multi-tenancy
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            from services.telegram.ui_components import send_welcome_message
            await send_welcome_message(ctx, chat_id) # Pass ctx to UI helpers too
            return

        engine = FlowEngine(db)
        await engine.process_message(session, text, message)

async def on_callback_query(ctx: TenantBotContext, callback_query: dict) -> None:
    chat_id = str(callback_query["message"]["chat"]["id"])
    user_id = str(callback_query["from"]["id"])
    data = callback_query.get("data", "")
    callback_id = callback_query["id"]

    from services.telegram.bot_service import answer_callback_query
    await answer_callback_query(ctx.bot_token, callback_id)

    async with AsyncSessionLocal() as db:
        # Track/Update Customer
        await upsert_customer_from_telegram(db, ctx.business_id, callback_query["from"])

        result = await db.execute(
            select(TelegramSession).where(
                TelegramSession.telegram_user_id == user_id,
                TelegramSession.is_active == True,
                TelegramSession.store_id == ctx.store_id
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            return

        engine = FlowEngine(db)
        await engine.process_callback(session, data, callback_query)

# Note: You'll also need to define on_start, on_pre_checkout_query, 
# and on_successful_payment in this file to satisfy the dispatcher imports.
