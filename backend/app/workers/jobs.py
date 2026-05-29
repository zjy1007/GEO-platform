"""Arq job: run a single (prompt × provider) evaluation call.

Each job calls the provider through the adapter, stores the raw answer in
provider_results, then atomically bumps the parent geo_run counters and advances
its status machine (running → completed / partial_failed). A failed call is
recorded (status='error') rather than crashing the run.
"""
import asyncio
import logging
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.geo import GeoPrompt, GeoRun, MentionResult, ProviderResult, VerificationResult
from app.models.merchant import Merchant
from app.providers.base import LLMRequest, LLMResponse
from app.providers.factory import build_channel
from app.services import account_pool_service as pool_svc
from app.services import citation_service as citation_svc
from app.services import evidence_service as evidence_svc
from app.services import evidence_verification_service as verify_svc
from app.services import mention_extraction_service as mention_svc
from app.workers.rate_limit import limiter

log = logging.getLogger("worker.jobs")

# Max accounts to try before giving up on one web job (rotation on failure).
_WEB_MAX_ACCOUNT_TRIES = 3
# Keywords (lowercased) used to classify a web failure into a pool action.
_RELOGIN_HINTS = ("relogin", "re-login", "login", "登录", "未登录", "登陆", "storage_state", "user_data_dir")
_RISK_HINTS = ("risk", "captcha", "验证码", "风控", "blocked", "403", "429", "rate", "too many")


def _classify_web_error(err: Exception) -> str:
    """Map a web-channel exception to a pool action: 'relogin' | 'pause' | 'error'."""
    msg = str(err).lower()
    if any(h in msg for h in _RELOGIN_HINTS):
        return "relogin"
    if any(h in msg for h in _RISK_HINTS):
        return "pause"
    return "error"


async def _bump_and_maybe_finish(session: AsyncSession, run_id: UUID, ok: bool) -> None:
    await session.execute(
        update(GeoRun)
        .where(GeoRun.id == run_id)
        .values(
            finished_jobs=GeoRun.finished_jobs + 1,
            failed_jobs=GeoRun.failed_jobs + (0 if ok else 1),
            status="running",
            started_at=func.coalesce(GeoRun.started_at, func.now()),
        )
    )
    finished, total, failed = (
        await session.execute(
            select(GeoRun.finished_jobs, GeoRun.total_jobs, GeoRun.failed_jobs).where(
                GeoRun.id == run_id
            )
        )
    ).one()
    if total is not None and finished >= total:
        await session.execute(
            update(GeoRun)
            .where(GeoRun.id == run_id)
            .values(
                status="partial_failed" if failed > 0 else "completed",
                finished_at=func.now(),
            )
        )


async def _run_api_job(
    session: AsyncSession, run_id: UUID, prompt_id: UUID, provider: str, prompt: GeoPrompt
) -> dict:
    try:
        channel = build_channel(provider, "api")
        async with limiter.semaphore(provider):
            await limiter.throttle_qps(provider)
            resp = await channel.chat(
                LLMRequest(
                    provider=provider,
                    messages=[{"role": "user", "content": prompt.prompt_text or ""}],
                    temperature=0.2,
                )
            )
    except Exception as e:  # noqa: BLE001 — record and continue
        log.warning("provider call failed: %s", e)
        resp = LLMResponse(
            provider=provider, channel="api", content="", status="error", error_message=str(e)
        )

    session.add(
        ProviderResult(
            run_id=run_id,
            prompt_id=prompt_id,
            provider=provider,
            channel="api",
            model=resp.model,
            answer_text=resp.content,
            raw_response=resp.raw_response,
            latency_ms=resp.latency_ms,
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
            status=resp.status,
        )
    )
    await _bump_and_maybe_finish(session, run_id, ok=(resp.status == "ok"))
    await session.commit()
    return {"status": resp.status}


async def _run_web_job(
    session: AsyncSession, run_id: UUID, prompt_id: UUID, provider: str, prompt: GeoPrompt
) -> dict:
    """Drive one web (account-pool) call: lease an account, run, persist + citations.

    Rotates through up to _WEB_MAX_ACCOUNT_TRIES accounts on failure, applying the
    appropriate pool action (pause / mark_need_relogin) per failure. If no idle
    account is available, the job does NOT bump run counters and reports retryable
    so the queue can re-attempt it later.
    """
    channel = build_channel(provider, "web")
    resp: LLMResponse | None = None

    for _ in range(_WEB_MAX_ACCOUNT_TRIES):
        account = await pool_svc.pick_idle(session, provider)
        if account is None:
            # No capacity right now — leave run counters untouched, signal retry.
            await session.commit()
            return {"status": "retryable", "reason": "no idle account"}

        account_id = account.id
        await pool_svc.reserve(session, account)
        await session.flush()

        # Anti-detection: random human-like spacing before and after the request.
        await asyncio.sleep(pool_svc.next_human_delay())
        try:
            resp = await channel.chat(
                LLMRequest(
                    provider=provider,
                    channel="web",
                    messages=[{"role": "user", "content": prompt.prompt_text or ""}],
                    temperature=0.2,
                    metadata={"account_id": str(account_id), "phase": prompt.phase},
                )
            )
        except Exception as e:  # noqa: BLE001 — classify and rotate
            log.warning("web channel call failed (provider=%s): %s", provider, e)
            action = _classify_web_error(e)
            await pool_svc.release(session, account, success=False)
            if action == "relogin":
                await pool_svc.mark_need_relogin(session, account)
            elif action == "pause":
                await pool_svc.pause(session, account)
            await session.flush()
            resp = LLMResponse(
                provider=provider,
                channel="web",
                content="",
                status="error",
                error_message=str(e),
            )
            # On a transient/risk failure, try the next account; on a hard error stop.
            if action == "error":
                break
            continue

        await asyncio.sleep(pool_svc.next_human_delay())
        ok = resp.status == "ok"
        await pool_svc.release(session, account, success=ok)
        break

    # Persist the (last) result with channel='web' + account_id + raw payload.
    pr = ProviderResult(
        run_id=run_id,
        prompt_id=prompt_id,
        provider=provider,
        channel="web",
        account_id=account_id,
        model=resp.model,
        answer_text=resp.content,
        raw_response=resp.raw_response,
        latency_ms=resp.latency_ms,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
        status=resp.status,
    )
    session.add(pr)
    await session.flush()

    # Persist citations row-by-row (feeds web exposure + source ranking report blocks).
    if resp.status == "ok" and resp.citations:
        await citation_svc.store_citations(session, pr.id, resp.citations)

    await _bump_and_maybe_finish(session, run_id, ok=(resp.status == "ok"))
    await session.commit()
    return {"status": resp.status}


async def run_prompt_job(ctx: dict, job: dict) -> dict:
    run_id = UUID(job["run_id"])
    prompt_id = UUID(job["prompt_id"])
    provider = job["provider"]
    channel = job.get("channel", "api")

    async with SessionLocal() as session:
        prompt = await session.get(GeoPrompt, prompt_id)
        if prompt is None:
            await _bump_and_maybe_finish(session, run_id, ok=False)
            await session.commit()
            return {"status": "error", "reason": "prompt not found"}

        if channel == "web":
            return await _run_web_job(session, run_id, prompt_id, provider, prompt)
        return await _run_api_job(session, run_id, prompt_id, provider, prompt)


async def extract_mention_job(ctx: dict, payload: dict) -> dict:
    """Extract mention/rank/sentiment for one provider_result (P1.5)."""
    pr_id = UUID(payload["provider_result_id"])
    async with SessionLocal() as session:
        pr = await session.get(ProviderResult, pr_id)
        if pr is None or pr.status != "ok" or not pr.answer_text:
            return {"status": "skipped"}

        already = (
            await session.execute(
                select(MentionResult.id).where(MentionResult.provider_result_id == pr_id)
            )
        ).first()
        if already:
            return {"status": "exists"}

        run = await session.get(GeoRun, pr.run_id)
        merchant = await session.get(Merchant, run.merchant_id)
        aliases = await mention_svc.load_alias_names(session, merchant.id)
        try:
            channel = build_channel(settings.analysis_provider, "api")
            await mention_svc.extract_for_result(session, pr, merchant, aliases, channel)
            await session.commit()
        except Exception as e:  # noqa: BLE001 — record and continue
            log.warning("mention extraction failed for %s: %s", pr_id, e)
            return {"status": "error", "reason": str(e)}
    return {"status": "ok"}


async def verify_claims_job(ctx: dict, payload: dict) -> dict:
    """Split + verify claims for one provider_result against the merchant's evidence (P3.2)."""
    pr_id = UUID(payload["provider_result_id"])
    async with SessionLocal() as session:
        pr = await session.get(ProviderResult, pr_id)
        if pr is None or pr.status != "ok" or not pr.answer_text:
            return {"status": "skipped"}
        already = (
            await session.execute(
                select(VerificationResult.id).where(VerificationResult.provider_result_id == pr_id)
            )
        ).first()
        if already:
            return {"status": "exists"}

        run = await session.get(GeoRun, pr.run_id)
        merchant = await session.get(Merchant, run.merchant_id)
        evidences = await evidence_svc.list_sources(session, merchant.id)
        try:
            channel = build_channel(settings.analysis_provider, "api")
            await verify_svc.verify_answer(session, pr, merchant, evidences, channel)
            await session.commit()
        except Exception as e:  # noqa: BLE001 — record and continue
            log.warning("claim verification failed for %s: %s", pr_id, e)
            return {"status": "error", "reason": str(e)}
    return {"status": "ok"}
