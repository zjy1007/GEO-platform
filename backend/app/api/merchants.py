import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import TenantContext, get_tenant
from app.schemas.merchant import (
    AliasOut,
    CompletenessResult,
    MerchantCreate,
    MerchantOut,
    MerchantUpdate,
    NapCheckResult,
)
from app.services import merchant_profile_service as svc

router = APIRouter(prefix="/merchants", tags=["merchants"])


async def _load(session: AsyncSession, tenant: TenantContext, merchant_id: uuid.UUID):
    merchant = await svc.get_merchant(session, uuid.UUID(tenant.tenant_id), merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="merchant not found")
    return merchant


@router.post("", response_model=MerchantOut, status_code=status.HTTP_201_CREATED)
async def create_merchant(
    payload: MerchantCreate,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> MerchantOut:
    merchant = await svc.create_merchant(session, uuid.UUID(tenant.tenant_id), payload)
    return MerchantOut.model_validate(merchant)


@router.get("", response_model=list[MerchantOut])
async def list_merchants(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> list[MerchantOut]:
    rows = await svc.list_merchants(session, uuid.UUID(tenant.tenant_id), limit, offset)
    return [MerchantOut.model_validate(m) for m in rows]


@router.get("/{merchant_id}", response_model=MerchantOut)
async def get_merchant(
    merchant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> MerchantOut:
    return MerchantOut.model_validate(await _load(session, tenant, merchant_id))


@router.patch("/{merchant_id}", response_model=MerchantOut)
async def update_merchant(
    merchant_id: uuid.UUID,
    payload: MerchantUpdate,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> MerchantOut:
    merchant = await _load(session, tenant, merchant_id)
    return MerchantOut.model_validate(await svc.update_merchant(session, merchant, payload))


@router.get("/{merchant_id}/completeness", response_model=CompletenessResult)
async def merchant_completeness(
    merchant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> CompletenessResult:
    merchant = await _load(session, tenant, merchant_id)
    return svc.compute_completeness(_to_dict(merchant))


@router.get("/{merchant_id}/nap-check", response_model=NapCheckResult)
async def merchant_nap_check(
    merchant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> NapCheckResult:
    merchant = await _load(session, tenant, merchant_id)
    return svc.check_nap(_to_dict(merchant))


@router.get("/{merchant_id}/aliases", response_model=list[AliasOut])
async def merchant_aliases(
    merchant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> list[AliasOut]:
    await _load(session, tenant, merchant_id)
    rows = await svc.list_aliases(session, merchant_id)
    return [AliasOut.model_validate(a) for a in rows]


def _to_dict(merchant) -> dict:
    return {field: getattr(merchant, field, None) for field in svc._FIELD_WEIGHTS}
