"""Auth skeleton for P0.

A single shared bearer token gates the API while we build the pipeline.
Real multi-tenant auth (tenant_id / user_id scoping, KMS-encrypted keys) lands in P5;
the TenantContext shape is defined now so downstream services can depend on it early.
"""
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.core.config import settings


@dataclass
class TenantContext:
    tenant_id: str
    user_id: str | None = None


async def require_auth(authorization: str | None = Header(default=None)) -> None:
    # When no token is configured (None or empty, e.g. local dev), auth is open.
    if not settings.api_token:
        return
    expected = f"Bearer {settings.api_token}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing bearer token",
        )


async def get_tenant(_: None = Depends(require_auth)) -> TenantContext:
    # P0: every request maps to the default tenant. Replaced by real resolution in P5.
    return TenantContext(tenant_id=settings.default_tenant_id)
