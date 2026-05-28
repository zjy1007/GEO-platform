"""Arq worker entrypoint.

Run with: arq app.workers.worker.WorkerSettings
"""
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.logging import setup_logging
from app.workers.jobs import extract_mention_job, run_prompt_job, verify_claims_job


async def ping(ctx, value: str = "pong") -> str:
    return value


async def startup(ctx) -> None:
    setup_logging("INFO")


class WorkerSettings:
    functions = [run_prompt_job, extract_mention_job, verify_claims_job, ping]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = settings.worker_max_jobs
