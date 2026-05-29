"""Account pool service (P2.2-b): account selection, rotation, quota tracking, risk-control cooldown.

Design constraints:
- daily_quota / used_today are tracked per-account and reset at quota_reset_at.
- Risk-control cooldown: when a request fails with a risk-control signal, the account is
  paused for COOLDOWN_HOURS before it becomes eligible again (last_used_at + COOLDOWN_HOURS).
- Selection order: prefer accounts with fewest used_today (spread load), then by last_used_at asc.
- All DB operations accept an AsyncSession; no network I/O here.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import WebAccount

COOLDOWN_HOURS = 2
_STATUS_ACTIVE = "active"
_STATUS_PAUSED = "paused"
_STATUS_NEED_RELOGIN = "need_relogin"
_STATUS_DISABLED = "disabled"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _needs_quota_reset(account: WebAccount) -> bool:
    if account.quota_reset_at is None:
        return False
    return _now() >= account.quota_reset_at


def _is_in_cooldown(account: WebAccount) -> bool:
    """Return True if account is paused AND still within the cooldown window."""
    if account.status != _STATUS_PAUSED:
        return False
    if account.last_used_at is None:
        return False
    cooldown_end = account.last_used_at + timedelta(hours=COOLDOWN_HOURS)
    return _now() < cooldown_end


async def _apply_quota_reset_if_due(session: AsyncSession, account: WebAccount) -> None:
    """Reset used_today if quota_reset_at has passed (in-place mutation + flush)."""
    if _needs_quota_reset(account):
        account.used_today = 0
        account.quota_reset_at = None
        session.add(account)
        await session.flush()


async def pick_account(
    session: AsyncSession,
    provider: str,
    *,
    auto_reset_quota: bool = True,
) -> Optional[WebAccount]:
    """Return the best available account for `provider`, or None if none available.

    Eligibility criteria (checked in this order):
    1. status == 'active'
    2. used_today < daily_quota
    3. not in cooldown (last_used_at + COOLDOWN_HOURS > now would disqualify a *paused* account,
       but we only select active accounts so this guard is a safety net)

    Among eligible accounts, prefer lowest used_today, then oldest last_used_at (round-robin).
    """
    stmt = (
        select(WebAccount)
        .where(WebAccount.provider == provider)
        .where(WebAccount.status == _STATUS_ACTIVE)
        .order_by(WebAccount.used_today.asc(), WebAccount.last_used_at.asc().nullsfirst())
    )
    rows = (await session.execute(stmt)).scalars().all()

    for acct in rows:
        if auto_reset_quota:
            await _apply_quota_reset_if_due(session, acct)
        if acct.used_today >= acct.daily_quota:
            continue
        return acct

    return None


async def record_usage(session: AsyncSession, account: WebAccount) -> None:
    """Increment used_today and update last_used_at after a successful request."""
    account.used_today += 1
    account.last_used_at = _now()
    session.add(account)
    await session.flush()


async def apply_risk_control(
    session: AsyncSession,
    account: WebAccount,
    reason: str = "risk_control_triggered",
) -> None:
    """Pause account after a risk-control signal; cooldown starts from now (via last_used_at)."""
    account.status = _STATUS_PAUSED
    account.last_used_at = _now()
    account.paused_reason = reason
    session.add(account)
    await session.flush()


async def resume_if_cooldown_expired(
    session: AsyncSession,
    account: WebAccount,
) -> bool:
    """Attempt to resume a paused account. Returns True if it was resumed."""
    if account.status != _STATUS_PAUSED:
        return False
    if _is_in_cooldown(account):
        return False
    account.status = _STATUS_ACTIVE
    account.paused_reason = None
    session.add(account)
    await session.flush()
    return True


async def resume_all_eligible(session: AsyncSession) -> int:
    """Resume all paused accounts whose cooldown has expired. Returns count resumed."""
    stmt = select(WebAccount).where(WebAccount.status == _STATUS_PAUSED)
    rows = (await session.execute(stmt)).scalars().all()
    count = 0
    for acct in rows:
        if await resume_if_cooldown_expired(session, acct):
            count += 1
    return count


async def get_pool_stats(session: AsyncSession, provider: str) -> dict:
    """Return a summary of account pool health for `provider`."""
    stmt = select(WebAccount).where(WebAccount.provider == provider)
    accounts = (await session.execute(stmt)).scalars().all()

    total = len(accounts)
    active = sum(1 for a in accounts if a.status == _STATUS_ACTIVE)
    paused = sum(1 for a in accounts if a.status == _STATUS_PAUSED)
    need_relogin = sum(1 for a in accounts if a.status == _STATUS_NEED_RELOGIN)
    disabled = sum(1 for a in accounts if a.status == _STATUS_DISABLED)
    quota_remaining = sum(
        max(a.daily_quota - a.used_today, 0)
        for a in accounts
        if a.status == _STATUS_ACTIVE
    )
    in_cooldown = sum(1 for a in accounts if _is_in_cooldown(a))

    return {
        "provider": provider,
        "total": total,
        "active": active,
        "paused": paused,
        "need_relogin": need_relogin,
        "disabled": disabled,
        "in_cooldown": in_cooldown,
        "quota_remaining": quota_remaining,
    }
