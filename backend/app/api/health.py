from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe — no external dependencies, safe to call without a DB."""
    return {"status": "ok", "app": settings.app_name, "env": settings.env}


@router.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)) -> dict:
    """Readiness probe — verifies the database connection."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "up"}
