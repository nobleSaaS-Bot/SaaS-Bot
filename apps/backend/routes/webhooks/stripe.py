from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import stripe as stripe_sdk

from app.config import settings
from core.queue import enqueue_payment_job

router = APIRouter()


@router.post("/")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
):
    body = await request.body()

    try:
        event = stripe_sdk.Webhook.construct_event(
            body, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe_sdk.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "payment_intent.succeeded":
        order_id = data.get("metadata", {}).get("order_id")
        if order_id:
            enqueue_payment_job(order_id, "stripe", {"payment_intent_id": data["id"], "status": "completed"})

    elif event_type == "payment_intent.payment_failed":
        order_id = data.get("metadata", {}).get("order_id")
        if order_id:
            enqueue_payment_job(order_id, "stripe", {"payment_intent_id": data["id"], "status": "failed"})

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        pass

    return {"received": True}
