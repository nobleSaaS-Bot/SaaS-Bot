from services.telegram.bot_service import send_message


def build_inline_keyboard(buttons: list[list[dict]]) -> dict:
    return {"inline_keyboard": buttons}


def build_reply_keyboard(buttons: list[list[str]], one_time: bool = False, resize: bool = True) -> dict:
    keyboard = [[{"text": btn} for btn in row] for row in buttons]
    return {
        "keyboard": keyboard,
        "resize_keyboard": resize,
        "one_time_keyboard": one_time,
    }


def remove_keyboard() -> dict:
    return {"remove_keyboard": True}


async def send_welcome_message(chat_id: str, store_name: str = "Our Store") -> None:
    text = (
        f"Welcome to <b>{store_name}</b>!\n\n"
        f"Use the menu below to browse our products and place orders."
    )
    keyboard = build_reply_keyboard([
        ["Browse Products", "My Orders"],
        ["Contact Support", "Settings"],
    ])
    await send_message(chat_id, text, reply_markup=keyboard)


async def send_product_card(chat_id: str, product: dict, currency: str = "USD") -> None:
    price_text = f"{currency} {float(product['price']):.2f}"
    compare = product.get("compare_price")
    if compare:
        price_text += f" <s>{currency} {float(compare):.2f}</s>"

    text = (
        f"<b>{product['name']}</b>\n\n"
        f"{product.get('description', '')}\n\n"
        f"Price: {price_text}"
    )

    keyboard = build_inline_keyboard([
        [{"text": "Add to Cart", "callback_data": f"cart:add:{product['id']}"}],
        [{"text": "Back", "callback_data": "shop:browse"}],
    ])

    images = product.get("images") or []
    if images:
        from services.telegram.bot_service import send_photo
        await send_photo(chat_id, images[0], caption=text, reply_markup=keyboard)
    else:
        await send_message(chat_id, text, reply_markup=keyboard)


async def send_error_message(chat_id: str, error: str = "Something went wrong. Please try again.") -> None:
    await send_message(chat_id, f"<b>Error:</b> {error}")
