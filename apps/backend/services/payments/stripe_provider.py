import stripe
from app.config import settings
from models.order import Order

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeProvider:
    async def initiate(self, order: Order, return_url: str | None = None) -> dict:
        intent = stripe.PaymentIntent.create(
            amount=int(float(order.total) * 100),
            currency=order.currency.lower(),
            metadata={"order_id": order.id, "store_id": order.store_id},
        )
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "provider": "stripe",
        }

    async def verify(self, payment_intent_id: str) -> dict:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return {
            "status": "completed" if intent.status == "succeeded" else "pending",
            "payment_intent_id": intent.id,
        }

    async def refund(self, payment_intent_id: str, amount: float | None = None) -> dict:
        params = {"payment_intent": payment_intent_id}
        if amount:
            params["amount"] = int(amount * 100)
        refund = stripe.Refund.create(**params)
        return {"refund_id": refund.id, "status": refund.status}
