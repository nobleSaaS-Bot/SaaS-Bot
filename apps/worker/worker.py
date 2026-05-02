import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from redis import Redis
from rq import Worker, Queue

from app.config import settings

redis_conn = Redis.from_url(settings.REDIS_URL)

QUEUES = ["flows", "payments", "subscriptions", "default"]

if __name__ == "__main__":
    queues = [Queue(name, connection=redis_conn) for name in QUEUES]
    worker = Worker(queues, connection=redis_conn)
    print(f"Starting RQ worker — listening on queues: {QUEUES}")
    worker.work(with_scheduler=True)
