"""Arq worker entrypoint (placeholder for P0).

The real GEO eval / evidence / report tasks land in P1.4+. For now this just
defines the WorkerSettings so `arq app.workers.worker.WorkerSettings` boots
against Redis, proving the queue wiring is in place.
"""
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.logging import setup_logging


async def ping(ctx, value: str = "pong") -> str:
    return value


async def startup(ctx) -> None:
    setup_logging("INFO")


class WorkerSettings:
    functions = [ping]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
