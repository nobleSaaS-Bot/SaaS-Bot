from rq import get_current_job
import logging

logger = logging.getLogger(__name__)


def log_task_start(task_name: str, **kwargs) -> None:
    job = get_current_job()
    job_id = job.id if job else "unknown"
    logger.info(f"[{job_id}] Starting task: {task_name}", extra=kwargs)


def log_task_complete(task_name: str, **kwargs) -> None:
    job = get_current_job()
    job_id = job.id if job else "unknown"
    logger.info(f"[{job_id}] Completed task: {task_name}", extra=kwargs)


def log_task_error(task_name: str, error: Exception, **kwargs) -> None:
    job = get_current_job()
    job_id = job.id if job else "unknown"
    logger.error(f"[{job_id}] Failed task: {task_name} — {error}", extra=kwargs)
