import uuid

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.arq import get_arq_pool
from app.core.database import get_session
from app.core.security import TenantContext, get_tenant
from app.schemas.geo_run import GeoRunCreate, GeoRunOut, GeoRunProgress, ProviderResultOut
from app.schemas.mention import ExtractResponse, MentionResultOut, VerificationResultOut
from app.services import evidence_verification_service as verify_svc
from app.services import geo_run_service as svc
from app.services import mention_extraction_service as mention_svc
from app.services import merchant_profile_service as merchant_svc

router = APIRouter(prefix="/geo-runs", tags=["geo-runs"])


@router.post("", response_model=GeoRunOut, status_code=status.HTTP_201_CREATED)
async def create_geo_run(
    payload: GeoRunCreate,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
    pool: ArqRedis = Depends(get_arq_pool),
) -> GeoRunOut:
    merchant = await merchant_svc.get_merchant(
        session, uuid.UUID(tenant.tenant_id), payload.merchant_id
    )
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="merchant not found")

    try:
        run, jobs = await svc.create_run(
            session,
            payload.merchant_id,
            run_type=payload.run_type,
            providers=payload.providers,
            prompt_count=payload.prompt_count,
            repeat_count=payload.repeat_count,
            modes=payload.modes,
            phases=payload.phases,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    for job in jobs:
        await pool.enqueue_job("run_prompt_job", job)
    await svc.mark_queued(session, run)

    return GeoRunOut.model_validate(run)


@router.get("/{run_id}", response_model=GeoRunProgress)
async def get_geo_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: TenantContext = Depends(get_tenant),
) -> GeoRunProgress:
    run = await svc.get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    total = run.total_jobs or 0
    finished = run.finished_jobs or 0
    return GeoRunProgress(
        run_id=run.id,
        status=run.status,
        total_jobs=total,
        finished_jobs=finished,
        failed_jobs=run.failed_jobs or 0,
        progress=round(finished / total, 4) if total else 0.0,
    )


@router.get("/{run_id}/results", response_model=list[ProviderResultOut])
async def list_geo_run_results(
    run_id: uuid.UUID,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    _: TenantContext = Depends(get_tenant),
) -> list[ProviderResultOut]:
    if await svc.get_run(session, run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return await svc.list_results(session, run_id, limit=limit, offset=offset)


@router.post("/{run_id}/extract", response_model=ExtractResponse, status_code=status.HTTP_202_ACCEPTED)
async def extract_run_mentions(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: TenantContext = Depends(get_tenant),
    pool: ArqRedis = Depends(get_arq_pool),
) -> ExtractResponse:
    """Enqueue mention extraction for this run's successful, not-yet-extracted answers."""
    if await svc.get_run(session, run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    pending = await mention_svc.pending_result_ids(session, run_id)
    for pr_id in pending:
        await pool.enqueue_job("extract_mention_job", {"provider_result_id": str(pr_id)})
    return ExtractResponse(enqueued=len(pending))


@router.get("/{run_id}/mentions", response_model=list[MentionResultOut])
async def list_geo_run_mentions(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: TenantContext = Depends(get_tenant),
) -> list[MentionResultOut]:
    if await svc.get_run(session, run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    rows = await mention_svc.list_mentions(session, run_id)
    return [MentionResultOut.model_validate(r) for r in rows]


@router.post("/{run_id}/verify", response_model=ExtractResponse, status_code=status.HTTP_202_ACCEPTED)
async def verify_run_claims(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: TenantContext = Depends(get_tenant),
    pool: ArqRedis = Depends(get_arq_pool),
) -> ExtractResponse:
    """Enqueue claim split + evidence verification for this run's not-yet-verified answers."""
    if await svc.get_run(session, run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    pending = await verify_svc.pending_verify_result_ids(session, run_id)
    for pr_id in pending:
        await pool.enqueue_job("verify_claims_job", {"provider_result_id": str(pr_id)})
    return ExtractResponse(enqueued=len(pending))


@router.get("/{run_id}/verifications", response_model=list[VerificationResultOut])
async def list_geo_run_verifications(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: TenantContext = Depends(get_tenant),
) -> list[VerificationResultOut]:
    if await svc.get_run(session, run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    rows = await verify_svc.list_verifications(session, run_id)
    return [VerificationResultOut.model_validate(r) for r in rows]
