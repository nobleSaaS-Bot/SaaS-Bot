from services.telegram.bot_service import send_message, send_photo
from services.telegram.ui_components import build_inline_keyboard
from models.order import Order


async def send_cart_summary(chat_id: str, cart: list, currency: str = "USD") -> None:
    if not cart:
        await send_message(chat_id, "Your cart is empty.")
        return

    lines = ["<b>Your Cart:</b>\n"]
    total = 0.0

    for item in cart:
        subtotal = item["price"] * item["quantity"]
        total += subtotal
        lines.append(f"• {item['name']} x{item['quantity']} — {currency} {subtotal:.2f}")

    lines.append(f"\n<b>Total: {currency} {total:.2f}</b>")

    keyboard = build_inline_keyboard([
        [{"text": "Checkout", "callback_data": "checkout:confirm"}],
        [{"text": "Clear Cart", "callback_data": "cart:clear"}, {"text": "Continue Shopping", "callback_data": "shop:browse"}],
    ])

    await send_message(chat_id, "\n".join(lines), reply_markup=keyboard)


async def send_order_confirmation(chat_id: str, order: Order) -> None:
    text = (
        f"<b>Order Confirmed!</b>\n\n"
        f"Order ID: <code>{order.id[:8].upper()}</code>\n"
        f"Total: {order.currency} {float(order.total):.2f}\n"
        f"Status: {order.status.value.capitalize()}\n\n"
        f"We'll notify you when your order ships."
    )
    await send_message(chat_id, text)


async def send_payment_prompt(chat_id: str, order_id: str, amount: float, currency: str, providers: list[str]) -> None:
    buttons = [[{"text": p.capitalize(), "callback_data": f"pay:{p}:{order_id}"}] for p in providers]
    buttons.append([{"text": "Cancel", "callback_data": "pay:cancel"}])

    keyboard = build_inline_keyboard(buttons)
    text = f"<b>Payment Required</b>\n\nAmount: {currency} {amount:.2f}\n\nChoose your payment method:"
    await send_message(chat_id, text, reply_markup=keyboard)
