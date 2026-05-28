import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import TenantContext, get_tenant
from app.schemas.report import GeoReportOut
from app.services import geo_run_service
from app.services import geo_scoring_service as scoring
from app.services import mention_extraction_service as mention_svc
from app.services import merchant_profile_service as merchant_svc
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


async def _load_run_and_merchant(session: AsyncSession, tenant: TenantContext, run_id: uuid.UUID):
    run = await geo_run_service.get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    merchant = await merchant_svc.get_merchant(session, uuid.UUID(tenant.tenant_id), run.merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="merchant not found")
    return run, merchant


@router.post("/{run_id}/generate", response_model=GeoReportOut, status_code=status.HTTP_201_CREATED)
async def generate_report(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant: TenantContext = Depends(get_tenant),
) -> GeoReportOut:
    run, merchant = await _load_run_and_merchant(session, tenant, run_id)
    aliases = await mention_svc.load_alias_names(session, merchant.id)
    report = await scoring.compute_and_store(session, run, merchant, aliases)
    return GeoReportOut.model_validate(report)


@router.get("/{run_id}", response_model=GeoReportOut)
async def get_report(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: TenantContext = Depends(get_tenant),
) -> GeoReportOut:
    report = await scoring.get_latest_report(session, run_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report not found; generate it first")
    return GeoReportOut.model_validate(report)


@router.get("/{run_id}/html", response_class=HTMLResponse)
async def get_report_html(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: TenantContext = Depends(get_tenant),
) -> HTMLResponse:
    report = await scoring.get_latest_report(session, run_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report not found; generate it first")
    created = report.created_at.strftime("%Y-%m-%d %H:%M") if report.created_at else ""
    html = report_service.render_html(report.report_json or {}, run_created_at=created)
    return HTMLResponse(content=html)
