"""GEO run orchestration (P1.4).

create_run selects the merchant's existing prompts (P1.3), expands them into
(prompt × provider × repeat) jobs, persists a geo_run, and returns the job specs
for the route to enqueue. build_jobs is pure and unit-tested.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geo import GeoPrompt, GeoRun, ProviderResult
from app.providers.config import get_registry
from app.schemas.geo_run import ProviderResultOut


def build_jobs(
    run_id: uuid.UUID,
    merchant_id: uuid.UUID,
    prompt_ids: list[uuid.UUID],
    providers: list[str],
    repeat_count: int,
    channel: str = "api",
) -> list[dict]:
    jobs: list[dict] = []
    for pid in prompt_ids:
        for provider in providers:
            for i in range(repeat_count):
                jobs.append(
                    {
                        "run_id": str(run_id),
                        "merchant_id": str(merchant_id),
                        "prompt_id": str(pid),
                        "provider": provider,
                        "repeat_index": i,
                        "channel": channel,
                    }
                )
    return jobs


def validate_providers(providers: list[str], channel: str = "api") -> None:
    reg = get_registry()
    if channel not in ("api", "web"):
        raise ValueError(f"未知 channel: {channel}")
    for p in providers:
        if p not in reg.providers:
            raise ValueError(f"未知 provider: {p}")
        if channel not in reg.get(p).channels:
            raise ValueError(f"provider {p} 不支持 {channel} 渠道")


async def select_prompts(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    modes: list[str] | None,
    phases: list[str] | None,
    limit: int | None,
) -> list[GeoPrompt]:
    stmt = select(GeoPrompt).where(GeoPrompt.merchant_id == merchant_id)
    if modes:
        stmt = stmt.where(GeoPrompt.mode.in_(modes))
    if phases:
        stmt = stmt.where(GeoPrompt.phase.in_(phases))
    stmt = stmt.order_by(GeoPrompt.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def create_run(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    *,
    run_type: str,
    providers: list[str],
    prompt_count: int | None,
    repeat_count: int,
    modes: list[str] | None,
    phases: list[str] | None,
    channel: str = "api",
) -> tuple[GeoRun, list[dict]]:
    validate_providers(providers, channel)
    prompts = await select_prompts(session, merchant_id, modes, phases, prompt_count)
    if not prompts:
        raise ValueError("该商家还没有可用问题，请先生成问题集（POST /api/merchants/{id}/prompts）")

    total = len(prompts) * len(providers) * repeat_count
    run = GeoRun(
        merchant_id=merchant_id,
        run_type=run_type,
        status="created",
        total_jobs=total,
        finished_jobs=0,
        failed_jobs=0,
    )
    session.add(run)
    await session.flush()
    jobs = build_jobs(
        run.id, merchant_id, [p.id for p in prompts], providers, repeat_count, channel
    )
    await session.commit()
    await session.refresh(run)
    return run, jobs


async def get_run(session: AsyncSession, run_id: uuid.UUID) -> GeoRun | None:
    return await session.get(GeoRun, run_id)


async def mark_queued(session: AsyncSession, run: GeoRun) -> None:
    run.status = "queued"
    await session.commit()


async def list_results(
    session: AsyncSession, run_id: uuid.UUID, limit: int = 200, offset: int = 0
) -> list[ProviderResultOut]:
    prompt_alias = aliased(GeoPrompt)
    stmt = (
        select(ProviderResult, prompt_alias)
        .outerjoin(prompt_alias, ProviderResult.prompt_id == prompt_alias.id)
        .where(ProviderResult.run_id == run_id)
        .order_by(ProviderResult.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    results = []
    for pr, gp in rows:
        out = ProviderResultOut.model_validate(pr)
        if gp is not None:
            out.prompt_text = gp.prompt_text
            out.prompt_phase = gp.phase
            out.prompt_mode = gp.mode
        results.append(out)
    return results
