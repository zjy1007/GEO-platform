"""Unit tests for account_pool_service (task #3).

DB tests use a real Postgres connection (repo convention) and skip cleanly when
Postgres is unreachable. See the session fixture below.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.models import Base, WebAccount
from app.services import account_pool_service as svc


# ---------------------------------------------------------------------------
# Postgres session fixture — repo convention: real Postgres, skip if unreachable.
# Creates only web_accounts (full metadata has Postgres-only columns), drops after.
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def session():
    from sqlalchemy.pool import NullPool

    from app.core.config import settings

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("Postgres not reachable; skipping account-pool DB test")

    async with engine.begin() as conn:
        await conn.run_sync(WebAccount.__table__.create, checkfirst=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as s:
            yield s
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(WebAccount.__table__.drop, checkfirst=True)
        await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_account(
    provider: str = "deepseek",
    status: str = "active",
    daily_quota: int = 10,
    used_today: int = 0,
    last_used_at: datetime | None = None,
    paused_reason: str | None = None,
    quota_reset_at: datetime | None = None,
) -> WebAccount:
    return WebAccount(
        id=uuid.uuid4(),
        provider=provider,
        label="test-account",
        status=status,
        daily_quota=daily_quota,
        used_today=used_today,
        last_used_at=last_used_at,
        paused_reason=paused_reason,
        quota_reset_at=quota_reset_at,
    )


def _past(hours: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _future(hours: float) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours)


# ---------------------------------------------------------------------------
# pick_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pick_account_returns_active_with_quota(session: AsyncSession):
    acct = _make_account(used_today=3, daily_quota=10)
    session.add(acct)
    await session.flush()

    result = await svc.pick_account(session, "deepseek")
    assert result is not None
    assert result.id == acct.id


@pytest.mark.asyncio
async def test_pick_account_none_when_no_accounts(session: AsyncSession):
    result = await svc.pick_account(session, "deepseek")
    assert result is None


@pytest.mark.asyncio
async def test_pick_account_skips_quota_exhausted(session: AsyncSession):
    acct = _make_account(used_today=10, daily_quota=10)
    session.add(acct)
    await session.flush()

    result = await svc.pick_account(session, "deepseek")
    assert result is None


@pytest.mark.asyncio
async def test_pick_account_skips_paused(session: AsyncSession):
    acct = _make_account(status="paused")
    session.add(acct)
    await session.flush()

    result = await svc.pick_account(session, "deepseek")
    assert result is None


@pytest.mark.asyncio
async def test_pick_account_skips_disabled(session: AsyncSession):
    acct = _make_account(status="disabled")
    session.add(acct)
    await session.flush()

    result = await svc.pick_account(session, "deepseek")
    assert result is None


@pytest.mark.asyncio
async def test_pick_account_skips_need_relogin(session: AsyncSession):
    acct = _make_account(status="need_relogin")
    session.add(acct)
    await session.flush()

    result = await svc.pick_account(session, "deepseek")
    assert result is None


@pytest.mark.asyncio
async def test_pick_account_prefers_fewer_used(session: AsyncSession):
    busy = _make_account(used_today=8, daily_quota=10)
    idle = _make_account(used_today=1, daily_quota=10)
    session.add_all([busy, idle])
    await session.flush()

    result = await svc.pick_account(session, "deepseek")
    assert result.id == idle.id


@pytest.mark.asyncio
async def test_pick_account_wrong_provider(session: AsyncSession):
    acct = _make_account(provider="yuanbao")
    session.add(acct)
    await session.flush()

    result = await svc.pick_account(session, "deepseek")
    assert result is None


@pytest.mark.asyncio
async def test_pick_account_resets_quota_if_due(session: AsyncSession):
    acct = _make_account(used_today=10, daily_quota=10, quota_reset_at=_past(0.1))
    session.add(acct)
    await session.flush()

    result = await svc.pick_account(session, "deepseek", auto_reset_quota=True)
    assert result is not None
    assert result.used_today == 0


@pytest.mark.asyncio
async def test_pick_account_no_reset_when_disabled(session: AsyncSession):
    acct = _make_account(used_today=10, daily_quota=10, quota_reset_at=_past(0.1))
    session.add(acct)
    await session.flush()

    result = await svc.pick_account(session, "deepseek", auto_reset_quota=False)
    assert result is None


# ---------------------------------------------------------------------------
# record_usage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_usage_increments(session: AsyncSession):
    acct = _make_account(used_today=3)
    session.add(acct)
    await session.flush()

    await svc.record_usage(session, acct)
    assert acct.used_today == 4
    assert acct.last_used_at is not None


@pytest.mark.asyncio
async def test_record_usage_updates_last_used_at(session: AsyncSession):
    acct = _make_account(last_used_at=_past(5))
    session.add(acct)
    await session.flush()
    old_ts = acct.last_used_at

    await svc.record_usage(session, acct)
    assert acct.last_used_at > old_ts


# ---------------------------------------------------------------------------
# apply_risk_control / _is_in_cooldown
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apply_risk_control_pauses_account(session: AsyncSession):
    acct = _make_account()
    session.add(acct)
    await session.flush()

    await svc.apply_risk_control(session, acct, reason="captcha")
    assert acct.status == "paused"
    assert acct.paused_reason == "captcha"
    assert acct.last_used_at is not None


@pytest.mark.asyncio
async def test_is_in_cooldown_true_just_paused(session: AsyncSession):
    acct = _make_account(status="paused", last_used_at=_past(0.5))
    assert svc._is_in_cooldown(acct) is True


@pytest.mark.asyncio
async def test_is_in_cooldown_false_expired(session: AsyncSession):
    acct = _make_account(status="paused", last_used_at=_past(svc.COOLDOWN_HOURS + 1))
    assert svc._is_in_cooldown(acct) is False


@pytest.mark.asyncio
async def test_is_in_cooldown_false_active(session: AsyncSession):
    acct = _make_account(status="active", last_used_at=_past(0.1))
    assert svc._is_in_cooldown(acct) is False


# ---------------------------------------------------------------------------
# resume_if_cooldown_expired
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resume_when_cooldown_expired(session: AsyncSession):
    acct = _make_account(status="paused", last_used_at=_past(svc.COOLDOWN_HOURS + 1))
    session.add(acct)
    await session.flush()

    resumed = await svc.resume_if_cooldown_expired(session, acct)
    assert resumed is True
    assert acct.status == "active"
    assert acct.paused_reason is None


@pytest.mark.asyncio
async def test_no_resume_during_cooldown(session: AsyncSession):
    acct = _make_account(status="paused", last_used_at=_past(0.1))
    session.add(acct)
    await session.flush()

    resumed = await svc.resume_if_cooldown_expired(session, acct)
    assert resumed is False
    assert acct.status == "paused"


@pytest.mark.asyncio
async def test_no_resume_if_not_paused(session: AsyncSession):
    acct = _make_account(status="active")
    session.add(acct)
    await session.flush()

    resumed = await svc.resume_if_cooldown_expired(session, acct)
    assert resumed is False


# ---------------------------------------------------------------------------
# resume_all_eligible
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resume_all_eligible(session: AsyncSession):
    expired1 = _make_account(status="paused", last_used_at=_past(svc.COOLDOWN_HOURS + 2))
    expired2 = _make_account(status="paused", last_used_at=_past(svc.COOLDOWN_HOURS + 3))
    still_cooling = _make_account(status="paused", last_used_at=_past(0.5))
    active = _make_account(status="active")
    session.add_all([expired1, expired2, still_cooling, active])
    await session.flush()

    count = await svc.resume_all_eligible(session)
    assert count == 2
    assert expired1.status == "active"
    assert expired2.status == "active"
    assert still_cooling.status == "paused"


# ---------------------------------------------------------------------------
# get_pool_stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_pool_stats(session: AsyncSession):
    session.add_all([
        _make_account(status="active", daily_quota=10, used_today=3),
        _make_account(status="active", daily_quota=10, used_today=7),
        _make_account(status="paused", last_used_at=_past(0.5)),  # in cooldown
        _make_account(status="disabled"),
        _make_account(status="need_relogin"),
    ])
    await session.flush()

    stats = await svc.get_pool_stats(session, "deepseek")
    assert stats["total"] == 5
    assert stats["active"] == 2
    assert stats["paused"] == 1
    assert stats["disabled"] == 1
    assert stats["need_relogin"] == 1
    assert stats["in_cooldown"] == 1
    assert stats["quota_remaining"] == (10 - 3) + (10 - 7)


@pytest.mark.asyncio
async def test_get_pool_stats_empty(session: AsyncSession):
    stats = await svc.get_pool_stats(session, "yuanbao")
    assert stats["total"] == 0
    assert stats["quota_remaining"] == 0
