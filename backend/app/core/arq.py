"""Arq Redis pool: created once in the app lifespan, used by routes to enqueue jobs."""
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import HTTPException, Request, status

from app.core.config import settings


async def create_arq_pool() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))


async def get_arq_pool(request: Request) -> ArqRedis:
    pool = getattr(request.app.state, "arq", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="task queue not available"
        )
    return pool
