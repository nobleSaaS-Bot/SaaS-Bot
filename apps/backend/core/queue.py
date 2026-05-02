from redis import Redis
from rq import Queue

from app.config import settings

redis_conn = Redis.from_url(settings.REDIS_URL)

flow_queue = Queue("flows", connection=redis_conn)
payment_queue = Queue("payments", connection=redis_conn)
subscription_queue = Queue("subscriptions", connection=redis_conn)
default_queue = Queue("default", connection=redis_conn)


def enqueue_flow_job(flow_id: str, session_id: str, payload: dict):
    return flow_queue.enqueue(
        "workers.flow_jobs.process_flow",
        flow_id=flow_id,
        session_id=session_id,
        payload=payload,
    )


def enqueue_payment_job(order_id: str, provider: str, payment_data: dict):
    return payment_queue.enqueue(
        "workers.payment_jobs.process_payment",
        order_id=order_id,
        provider=provider,
        payment_data=payment_data,
    )


def enqueue_subscription_renewal(subscription_id: str):
    return subscription_queue.enqueue(
        "workers.subscription_jobs.renew_subscription",
        subscription_id=subscription_id,
    )
