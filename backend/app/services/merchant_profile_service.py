"""Merchant profile service.

Pure functions (completeness / alias / NAP) are DB-free and unit-tested.
Async functions wrap CRUD over the merchants + merchant_aliases tables.
LLM-based alias enrichment is deferred to P1.3 (once the Provider Adapter is wired);
P1.1 uses deterministic rule-based aliases.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant import Merchant, MerchantAlias
from app.schemas.merchant import CompletenessResult, MerchantCreate, MerchantUpdate, NapCheckResult

# field -> (weight, 中文名). Weights sum to 100.
_FIELD_WEIGHTS: dict[str, tuple[int, str]] = {
    "name": (10, "商家名称"),
    "category": (10, "所属行业"),
    "city": (8, "城市"),
    "district": (5, "区域"),
    "address": (12, "详细地址"),
    "phone": (10, "联系电话"),
    "website": (10, "官网"),
    "business_hours": (8, "营业时间"),
    "services": (12, "服务项目"),
    "price_range": (4, "价格区间"),
    "target_keywords": (4, "目标关键词"),
    "official_sources": (5, "权威信源链接"),
    "competitors": (2, "竞品名单"),
}


def _is_filled(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def compute_completeness(data: dict) -> CompletenessResult:
    """Weighted resource-completeness score (0-100) + missing-field suggestions."""
    filled: list[str] = []
    missing: list[str] = []
    score = 0
    for field, (weight, _label) in _FIELD_WEIGHTS.items():
        if _is_filled(data.get(field)):
            filled.append(field)
            score += weight
        else:
            missing.append(field)

    suggestions: list[str] = []
    for field in missing:
        weight, label = _FIELD_WEIGHTS[field]
        if weight >= 8:
            suggestions.append(f"补全「{label}」可显著提升 AI 可见度与资料一致性")
        else:
            suggestions.append(f"建议补充「{label}」")

    return CompletenessResult(
        score=score, filled_fields=filled, missing_fields=missing, suggestions=suggestions
    )


def generate_aliases(name: str, city: str | None = None, district: str | None = None) -> list[dict]:
    """Rule-based alias candidates (LLM enrichment comes in P1.3)."""
    aliases: list[dict] = [{"alias": name, "alias_type": "standard", "confidence": 1.0}]
    seen = {name}

    def add(text: str, alias_type: str, confidence: float) -> None:
        text = text.strip()
        if text and text not in seen:
            seen.add(text)
            aliases.append({"alias": text, "alias_type": alias_type, "confidence": confidence})

    stripped = name
    if city and stripped.startswith(city):
        stripped = stripped[len(city):]
        add(stripped, "no_city_prefix", 0.85)
    if district and stripped.startswith(district):
        stripped2 = stripped[len(district):]
        add(stripped2, "no_district_prefix", 0.8)
    if city and district and name.startswith(city + district):
        add(name[len(city) + len(district):], "no_region_prefix", 0.78)

    return aliases


def check_nap(data: dict) -> NapCheckResult:
    """NAP (Name/Address/Phone) presence check.

    P1.1 only validates the merchant's own NAP completeness. Cross-source NAP
    consistency (official site vs maps vs reviews) needs evidence data and lands in P3.
    """
    issues: list[str] = []
    for field, label in (("name", "商家名称"), ("address", "地址"), ("phone", "电话")):
        if not _is_filled(data.get(field)):
            issues.append(f"缺少 NAP 字段：{label}")
    return NapCheckResult(consistent=len(issues) == 0, issues=issues)


# --- async CRUD ---

async def create_merchant(
    session: AsyncSession, tenant_id: uuid.UUID, payload: MerchantCreate
) -> Merchant:
    merchant = Merchant(tenant_id=tenant_id, status="active", **payload.model_dump())
    session.add(merchant)
    await session.flush()
    for a in generate_aliases(merchant.name, merchant.city, merchant.district):
        session.add(MerchantAlias(merchant_id=merchant.id, **a))
    await session.commit()
    await session.refresh(merchant)
    return merchant


async def get_merchant(session: AsyncSession, tenant_id: uuid.UUID, merchant_id: uuid.UUID) -> Merchant | None:
    stmt = select(Merchant).where(Merchant.id == merchant_id, Merchant.tenant_id == tenant_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_merchants(session: AsyncSession, tenant_id: uuid.UUID, limit: int = 50, offset: int = 0) -> list[Merchant]:
    stmt = (
        select(Merchant)
        .where(Merchant.tenant_id == tenant_id)
        .order_by(Merchant.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(stmt)).scalars().all())


async def update_merchant(
    session: AsyncSession, merchant: Merchant, payload: MerchantUpdate
) -> Merchant:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(merchant, field, value)
    await session.commit()
    await session.refresh(merchant)
    return merchant


async def list_aliases(session: AsyncSession, merchant_id: uuid.UUID) -> list[MerchantAlias]:
    stmt = select(MerchantAlias).where(MerchantAlias.merchant_id == merchant_id)
    return list((await session.execute(stmt)).scalars().all())
