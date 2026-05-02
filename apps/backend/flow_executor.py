from sqlalchemy.ext.asyncio import AsyncSession

from models.session import TelegramSession
from models.flow import Flow
from services.telegram.bot_service import send_message
from services.telegram.ui_components import build_inline_keyboard, build_reply_keyboard


class FlowExecutor:
    def __init__(self, db: AsyncSession, session: TelegramSession, flow: Flow):
        self.db = db
        self.session = session
        self.flow = flow

    async def execute(self, input_text: str, raw_update: dict) -> None:
        chat_id = self._get_chat_id(raw_update)
        steps = self.flow.steps

        if not steps:
            await send_message(chat_id, "This flow has no steps configured.")
            return

        current_step_id = self.session.current_step
        step = self._get_step(steps, current_step_id)

        if step is None:
            step = steps[0]

        await self._execute_step(step, chat_id, input_text, raw_update)
        next_step_id = await self._resolve_next(step, input_text)
        self.session.current_step = next_step_id
        await self.db.commit()

    async def _execute_step(self, step: dict, chat_id: str, input_text: str, raw_update: dict) -> None:
        step_type = step.get("type", "message")

        if step_type == "message":
            text = step.get("text", "")
            buttons = step.get("buttons")
            keyboard = None
            if buttons:
                keyboard = build_inline_keyboard([[{"text": b["label"], "callback_data": b["data"]} for b in row] for row in buttons])
            await send_message(chat_id, text, reply_markup=keyboard)

        elif step_type == "product_list":
            from sqlalchemy import select
            from models.product import Product
            store_id = self.session.store_id
            result = await self.db.execute(
                select(Product).where(Product.store_id == store_id, Product.is_active == True).limit(10)
            )
            products = result.scalars().all()
            if not products:
                await send_message(chat_id, "No products available right now.")
            else:
                buttons = [[{"text": p.name, "callback_data": f"product:view:{p.id}"}] for p in products]
                keyboard = build_inline_keyboard(buttons)
                await send_message(chat_id, "Browse our products:", reply_markup=keyboard)

        elif step_type == "collect_input":
            prompt = step.get("prompt", "Please enter:")
            await send_message(chat_id, prompt)

        elif step_type == "condition":
            pass

    async def _resolve_next(self, step: dict, input_text: str) -> str | None:
        return step.get("next_step")

    def _get_step(self, steps: list, step_id: str | None) -> dict | None:
        if not step_id:
            return None
        for step in steps:
            if step.get("id") == step_id:
                return step
        return None

    def _get_chat_id(self, raw_update: dict) -> str:
        if "message" in raw_update:
            return str(raw_update["message"]["chat"]["id"])
        elif "chat" in raw_update:
            return str(raw_update["chat"]["id"])
        return ""
