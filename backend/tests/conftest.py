import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import engine as app_engine


@pytest_asyncio.fixture
async def db_session():
    """Yields a DB session, or skips the test if Postgres is unreachable.

    Uses a fresh NullPool engine per test to avoid asyncpg connections being
    reused across pytest-asyncio's per-test event loops. DB tests run inside the
    backend container (DATABASE_URL resolves 'postgres'); on a bare host without
    the stack they skip cleanly.
    """
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("Postgres not reachable; skipping DB integration test")

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()
    # Worker jobs use the module-level engine; dispose it too so its pooled asyncpg
    # connection isn't reused across pytest-asyncio's per-test event loops.
    await app_engine.dispose()
