import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import TenantContext, get_tenant
from app.schemas.evidence import EvidenceSourceIn, EvidenceSourceOut
from app.services import evidence_service as svc
from app.services import merchant_profile_service as merchant_svc

router = APIRouter(prefix="/merchants", tags=["evidence"])


async def _load_merchant(session: AsyncSession, tenant: TenantContext, merchant_id: uuid.UUID):
    merchant = await merchant_svc.get_merchant(session, uuid.UUID(tenant.tenant_id), merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="merchant not found")
    return merchant


@router.post("/{merchant_id}/evidence", response_model=EvidenceSourceOut,
             status_code=status.HTTP_201_CREATED)
async def add_evidence(
    merchant_id: uuid.UUID,
    payload: EvidenceSourceIn,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> EvidenceSourceOut:
    await _load_merchant(session, tenant, merchant_id)
    try:
        source, _created = await svc.add_source(
            session, merchant_id, source_type=payload.source_type,
            url=payload.url, title=payload.title, text=payload.text,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"抓取证据 URL 失败: {e}") from e
    await session.commit()
    return EvidenceSourceOut.model_validate(source)


@router.get("/{merchant_id}/evidence", response_model=list[EvidenceSourceOut])
async def list_evidence(
    merchant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> list[EvidenceSourceOut]:
    await _load_merchant(session, tenant, merchant_id)
    rows = await svc.list_sources(session, merchant_id)
    return [EvidenceSourceOut.model_validate(r) for r in rows]
