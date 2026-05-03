from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.order import Order, OrderStatus
from models.session import TelegramSession
from services.telegram.checkout import send_order_confirmation

# Architecture Addition
from routes.customers import record_order_for_customer


async def create_order_from_cart(
    db: AsyncSession,
    session: TelegramSession,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    shipping_address: dict | None = None,
    notes: str | None = None,
) -> Order:
    cart = session.cart or []
    if not cart:
        raise ValueError("Cart is empty")

    subtotal = sum(item["price"] * item["quantity"] for item in cart)
    total = subtotal

    order = Order(
        business_id=session.store.business_id if hasattr(session, "store") else "",
        store_id=session.store_id,
        customer_telegram_id=session.telegram_user_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        items=cart,
        subtotal=subtotal,
        total=total,
        shipping_address=shipping_address,
        notes=notes,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    session.cart = []
    await db.commit()

    return order


async def update_order_status(
    db: AsyncSession, order_id: str, status: OrderStatus
) -> Order:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise ValueError("Order not found")
    
    order.status = status
    
    # Architecture Addition: Record order for customer analytics when payment is confirmed
    if status == OrderStatus.PAID: # Or your specific 'completed' status
        # str(order.customer_id) assumes your Order model has a customer relationship/ID
        # If your Order model uses telegram_id, adjust accordingly
        await record_order_for_customer(db, str(order.customer_telegram_id), order.total)

    await db.commit()
    await db.refresh(order)
    return order


async def get_orders_for_store(
    db: AsyncSession,
    store_id: str,
    status: OrderStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Order]:
    query = select(Order).where(Order.store_id == store_id)
    if status:
        query = query.where(Order.status == status)
    query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())
