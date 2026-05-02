from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.session import TelegramSession
from models.flow import Flow
from flow_executor import FlowExecutor


class FlowEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_flow(self, session: TelegramSession) -> Flow | None:
        if not session.current_flow_id:
            return None
        result = await self.db.execute(
            select(Flow).where(Flow.id == session.current_flow_id, Flow.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_flow_by_trigger(self, store_id: str, trigger: str) -> Flow | None:
        result = await self.db.execute(
            select(Flow).where(
                Flow.store_id == store_id,
                Flow.trigger == trigger,
                Flow.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def process_message(self, session: TelegramSession, text: str, raw_message: dict) -> None:
        flow = await self.get_active_flow(session)

        if not flow:
            trigger = self._resolve_trigger(text)
            flow = await self.get_flow_by_trigger(session.store_id, trigger)
            if flow:
                session.current_flow_id = flow.id
                session.current_step = None
                await self.db.commit()

        if flow:
            executor = FlowExecutor(self.db, session, flow)
            await executor.execute(text, raw_message)
        else:
            from services.telegram.ui_components import send_error_message
            chat_id = str(raw_message["chat"]["id"])
            await send_error_message(chat_id, "I didn't understand that. Please use the menu.")

    async def process_callback(self, session: TelegramSession, data: str, raw_callback: dict) -> None:
        action, *args = data.split(":")
        chat_id = str(raw_callback["message"]["chat"]["id"])

        if action == "shop":
            flow = await self.get_flow_by_trigger(session.store_id, "browse")
            if flow:
                session.current_flow_id = flow.id
                session.current_step = None
                await self.db.commit()
                executor = FlowExecutor(self.db, session, flow)
                await executor.execute(data, raw_callback)
        elif action == "cart":
            await self._handle_cart_action(session, args, chat_id)
        elif action == "pay":
            await self._handle_payment_action(session, args, chat_id)

    async def _handle_cart_action(self, session: TelegramSession, args: list, chat_id: str) -> None:
        from services.telegram.checkout import send_cart_summary
        action = args[0] if args else ""
        if action == "clear":
            session.cart = []
            await self.db.commit()
            await send_cart_summary(chat_id, [])
        elif action == "view":
            await send_cart_summary(chat_id, session.cart)

    async def _handle_payment_action(self, session: TelegramSession, args: list, chat_id: str) -> None:
        pass

    def _resolve_trigger(self, text: str) -> str:
        text_lower = text.lower().strip()
        if text_lower in ("/start", "start"):
            return "start"
        elif text_lower in ("browse products", "shop", "/shop"):
            return "browse"
        elif text_lower in ("my orders", "/orders"):
            return "orders"
        elif text_lower in ("cart", "/cart"):
            return "cart"
        return "default"
