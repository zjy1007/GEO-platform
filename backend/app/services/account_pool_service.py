"""Account pool service (P2.2-b): account selection, rotation, quota tracking, risk-control cooldown.

Design constraints:
- daily_quota / used_today are tracked per-account and reset at quota_reset_at.
- Risk-control cooldown: when a request fails with a risk-control signal, the account is
  paused for COOLDOWN_HOURS before it becomes eligible again (last_used_at + COOLDOWN_HOURS).
- Selection order: prefer accounts with fewest used_today (spread load), then by last_used_at asc.
- All DB operations accept an AsyncSession; no network I/O here.

Lease API for the web channel (doc section 14, consumed by P2.3 #4):
- pick_idle -> reserve -> (drive session) -> release / pause / mark_need_relogin
- next_human_delay() spaces requests so the pool does not fire at machine speed.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import WebAccount

COOLDOWN_HOURS = 2
# Default human-like spacing between consecutive requests on one account (seconds).
HUMAN_DELAY_MIN = 3.0
HUMAN_DELAY_MAX = 12.0

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
    3. not in cooldown (only active accounts are selected, so this is a safety net)

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


async def pick_idle(
    session: AsyncSession,
    provider: str,
    *,
    auto_reset_quota: bool = True,
) -> Optional[WebAccount]:
    """Design-API name for selecting an available account (no mutation).

    Same selection as pick_account; reserve() is the separate claim step.
    """
    return await pick_account(session, provider, auto_reset_quota=auto_reset_quota)


async def reserve(session: AsyncSession, account: WebAccount) -> WebAccount:
    """Claim an account for one request: consume a quota slot up front and stamp
    last_used_at, so a concurrent picker sees it as used and load spreads.

    Pair every reserve() with a release(). On request failure, release(success=False)
    refunds the slot.
    """
    account.used_today += 1
    account.last_used_at = _now()
    session.add(account)
    await session.flush()
    return account


async def release(session: AsyncSession, account: WebAccount, *, success: bool = True) -> None:
    """Finish a reserved request. On failure, refund the quota slot claimed by reserve()."""
    if not success:
        account.used_today = max(account.used_today - 1, 0)
        session.add(account)
        await session.flush()


async def record_usage(session: AsyncSession, account: WebAccount) -> None:
    """Increment used_today and update last_used_at after a successful request.

    Lower-level alternative to reserve()/release() for callers that count usage in one step.
    """
    account.used_today += 1
    account.last_used_at = _now()
    session.add(account)
    await session.flush()


def next_human_delay(
    min_seconds: float = HUMAN_DELAY_MIN,
    max_seconds: float = HUMAN_DELAY_MAX,
) -> float:
    """Return a randomized human-like delay (seconds) to insert between requests.

    Anti-detection: account-pool requests must not fire back-to-back at machine speed
    (doc section 14, random sleep per question). Pure function — caller awaits
    asyncio.sleep(delay).
    """
    return random.uniform(min_seconds, max_seconds)


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


async def pause(
    session: AsyncSession,
    account: WebAccount,
    reason: str = "risk_control_triggered",
) -> None:
    """Design-API name for pausing an account (captcha / anomaly). Alias of apply_risk_control."""
    await apply_risk_control(session, account, reason=reason)


async def mark_need_relogin(
    session: AsyncSession,
    account: WebAccount,
    reason: str = "login_state_expired",
) -> None:
    """Flag an account as needing manual re-login (login state expired/invalid).

    Distinct from pause(): a need_relogin account is NOT auto-resumed by cooldown — it
    requires a human to re-scan/login before it returns to the pool.
    """
    account.status = _STATUS_NEED_RELOGIN
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
