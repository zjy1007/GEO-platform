"""Evidence ingestion & storage (P3.1).

Stores evidence sources for a merchant — user-supplied text, or fetched+extracted
from an authorized URL (official site / own pages). Content is hashed for dedupe
and tagged with a trust level by source type (doc §八). Claim verification against
this evidence (NLI → supported/contradicted) and evidence_rate land in P3.2.

trafilatura is imported lazily inside fetch_and_extract so importing the app (and
running host unit tests) never requires the crawl/browser deps.
"""
import hashlib
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import EvidenceSource

# doc §八 证据源可信等级
TRUST_LEVELS: dict[str, float] = {
    "official_website": 0.95,
    "user_upload": 0.9,
    "map": 0.88,
    "review": 0.8,
    "news": 0.75,
    "social": 0.6,
    "other": 0.5,
}
DEFAULT_TRUST = 0.5


def trust_level_for(source_type: str | None) -> float:
    return TRUST_LEVELS.get(source_type or "", DEFAULT_TRUST)


def normalize_text(text: str) -> str:
    return "\n".join(line.strip() for line in (text or "").splitlines() if line.strip()).strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


async def fetch_and_extract(url: str, timeout: int = 20) -> tuple[str | None, str]:
    """Fetch a URL and extract (title, main_text). Lazy-imports trafilatura."""
    import trafilatura  # lazy: crawl dep not needed for unit tests

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 GEO-bot"})
        resp.raise_for_status()
        html = resp.text

    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    title = None
    meta = trafilatura.extract_metadata(html)
    if meta is not None:
        title = getattr(meta, "title", None)
    return title, text


async def add_source(
    session: AsyncSession,
    merchant_id,
    *,
    source_type: str,
    url: str | None = None,
    title: str | None = None,
    text: str | None = None,
) -> tuple[EvidenceSource, bool]:
    """Add an evidence source. Returns (source, created). Dedupes by content_hash."""
    if not text and url:
        fetched_title, text = await fetch_and_extract(url)
        title = title or fetched_title
    if not text or not text.strip():
        raise ValueError("证据内容为空：请提供 text，或提供可抓取到正文的 url")

    digest = content_hash(text)
    existing = (
        await session.execute(
            select(EvidenceSource).where(
                EvidenceSource.merchant_id == merchant_id,
                EvidenceSource.content_hash == digest,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    source = EvidenceSource(
        merchant_id=merchant_id,
        source_type=source_type,
        url=url,
        title=title,
        content_text=normalize_text(text),
        trust_level=trust_level_for(source_type),
        retrieved_at=datetime.now(timezone.utc),
        content_hash=digest,
    )
    session.add(source)
    await session.flush()
    return source, True


async def list_sources(session: AsyncSession, merchant_id) -> list[EvidenceSource]:
    stmt = (
        select(EvidenceSource)
        .where(EvidenceSource.merchant_id == merchant_id)
        .order_by(EvidenceSource.retrieved_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())
