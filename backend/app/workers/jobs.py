"""Arq job: run a single (prompt × provider) evaluation call.

Each job calls the provider through the adapter, stores the raw answer in
provider_results, then atomically bumps the parent geo_run counters and advances
its status machine (running → completed / partial_failed). A failed call is
recorded (status='error') rather than crashing the run.
"""
import logging
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models.geo import GeoPrompt, GeoRun, ProviderResult
from app.providers.base import LLMRequest, LLMResponse
from app.providers.factory import build_channel
from app.workers.rate_limit import limiter

log = logging.getLogger("worker.jobs")


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


async def run_prompt_job(ctx: dict, job: dict) -> dict:
    run_id = UUID(job["run_id"])
    prompt_id = UUID(job["prompt_id"])
    provider = job["provider"]

    async with SessionLocal() as session:
        prompt = await session.get(GeoPrompt, prompt_id)
        if prompt is None:
            await _bump_and_maybe_finish(session, run_id, ok=False)
            await session.commit()
            return {"status": "error", "reason": "prompt not found"}

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
