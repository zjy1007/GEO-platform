import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import TenantContext, get_tenant
from app.schemas.prompt import GeoPromptOut, PromptGenerateRequest, PromptGenerateResponse
from app.services import merchant_profile_service as merchant_svc
from app.services import prompt_generation_service as svc

router = APIRouter(prefix="/merchants", tags=["prompts"])


async def _load_merchant(session: AsyncSession, tenant: TenantContext, merchant_id: uuid.UUID):
    merchant = await merchant_svc.get_merchant(session, uuid.UUID(tenant.tenant_id), merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="merchant not found")
    return merchant


@router.post(
    "/{merchant_id}/prompts",
    response_model=PromptGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_prompts(
    merchant_id: uuid.UUID,
    payload: PromptGenerateRequest,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> PromptGenerateResponse:
    merchant = await _load_merchant(session, tenant, merchant_id)
    count = payload.count or svc.TIER_COUNTS[payload.tier]
    try:
        prompts = await svc.generate_and_store(
            session,
            merchant,
            count=count,
            modes=payload.modes,
            phases=payload.phases,
            provider=payload.provider,
        )
    except RuntimeError as e:
        # upstream LLM call / parsing failed (e.g. missing API key) — surface as 502
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e

    return PromptGenerateResponse(
        total=len(prompts), prompts=[GeoPromptOut.model_validate(p) for p in prompts]
    )


@router.get("/{merchant_id}/prompts", response_model=list[GeoPromptOut])
async def list_prompts(
    merchant_id: uuid.UUID,
    mode: str | None = Query(default=None),
    phase: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> list[GeoPromptOut]:
    await _load_merchant(session, tenant, merchant_id)
    rows = await svc.list_prompts(session, merchant_id, mode=mode, phase=phase)
    return [GeoPromptOut.model_validate(p) for p in rows]
