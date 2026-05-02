from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from models.payment import Payment, PaymentProvider
from models.order import Order
from core.security import get_current_user
from services.payments.payment_factory import get_payment_provider

router = APIRouter()


class InitiatePaymentRequest(BaseModel):
    order_id: str
    provider: PaymentProvider
    return_url: str | None = None


@router.post("/initiate")
async def initiate_payment(
    payload: InitiatePaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Order).where(Order.id == payload.order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    provider = get_payment_provider(payload.provider)
    payment_data = await provider.initiate(order, return_url=payload.return_url)

    payment = Payment(
        order_id=order.id,
        provider=payload.provider,
        amount=order.total,
        currency=order.currency,
        metadata=payment_data,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return {"payment_id": payment.id, **payment_data}


@router.get("/{payment_id}")
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
