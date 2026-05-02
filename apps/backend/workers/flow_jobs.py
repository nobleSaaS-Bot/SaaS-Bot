import asyncio
import logging
from workers.tasks import log_task_start, log_task_complete, log_task_error

logger = logging.getLogger(__name__)


def process_flow(flow_id: str, session_id: str, payload: dict) -> None:
    log_task_start("process_flow", flow_id=flow_id, session_id=session_id)
    try:
        asyncio.run(_process_flow_async(flow_id, session_id, payload))
        log_task_complete("process_flow", flow_id=flow_id)
    except Exception as e:
        log_task_error("process_flow", e, flow_id=flow_id)
        raise


async def _process_flow_async(flow_id: str, session_id: str, payload: dict) -> None:
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from models.flow import Flow
    from models.session import TelegramSession
    from flow_engine import FlowEngine

    async with AsyncSessionLocal() as db:
        flow_result = await db.execute(select(Flow).where(Flow.id == flow_id))
        flow = flow_result.scalar_one_or_none()
        if not flow:
            logger.warning(f"Flow {flow_id} not found")
            return

        session_result = await db.execute(select(TelegramSession).where(TelegramSession.id == session_id))
        session = session_result.scalar_one_or_none()
        if not session:
            logger.warning(f"Session {session_id} not found")
            return

        engine = FlowEngine(db)
        await engine.process_message(session, payload.get("text", ""), payload)
