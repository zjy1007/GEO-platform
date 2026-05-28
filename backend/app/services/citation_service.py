"""Citation post-processing (P2).

The account pool only needs to capture answer + citations; everything the report
shows about sources is pure aggregation over citation_sources (doc §24):
  - 引用源平台排行榜  = count by domain, desc
  - 信源投放建议      = top-N domains → percentage + priority tiers
  - GEO 优化建议(标题) = high-frequency cited article titles

Aggregation helpers are pure and unit-tested. DB helpers persist/fetch rows.
"""
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geo import CitationSource, ProviderResult
from app.providers.base import Citation

_HIGH_CUTOFF = 3   # top 3 domains → 第一优先级
_MID_CUTOFF = 7    # next → 第二优先级；其余 → 第三优先级


def _label(domain: str | None, source_name: str | None) -> str:
    return source_name or domain or "未知来源"


def aggregate_ranking(citations: list[dict]) -> list[dict]:
    """[{domain, source_name, count, rate}] sorted by count desc."""
    total = len(citations)
    if total == 0:
        return []
    counts: Counter = Counter()
    label_of: dict[str, dict] = {}
    for c in citations:
        key = (c.get("domain") or c.get("source_name") or "").strip()
        if not key:
            continue
        counts[key] += 1
        label_of.setdefault(key, {"domain": c.get("domain"), "source_name": c.get("source_name")})
    ranking = [
        {
            "domain": label_of[k]["domain"],
            "source_name": label_of[k]["source_name"],
            "label": _label(label_of[k]["domain"], label_of[k]["source_name"]),
            "count": n,
            "rate": round(n / total, 4),
        }
        for k, n in counts.most_common()
    ]
    return ranking


def build_source_investment(ranking: list[dict], top_n: int = 10) -> list[dict]:
    """Top-N domains → normalized percentage + priority tier (doc 信源投放建议)."""
    top = ranking[:top_n]
    subtotal = sum(r["count"] for r in top) or 1
    out = []
    for i, r in enumerate(top):
        priority = "high" if i < _HIGH_CUTOFF else ("medium" if i < _MID_CUTOFF else "low")
        out.append(
            {
                "label": r["label"],
                "domain": r["domain"],
                "percentage": round(r["count"] / subtotal * 100, 1),
                "priority": priority,
            }
        )
    return out


def top_article_titles(citations: list[dict], top_n: int = 10) -> list[dict]:
    counts: Counter = Counter()
    for c in citations:
        title = (c.get("title") or "").strip()
        if title:
            counts[title] += 1
    return [{"title": t, "count": n} for t, n in counts.most_common(top_n)]


def build_citation_report(citations: list[dict], top_n: int = 10) -> dict:
    ranking = aggregate_ranking(citations)
    return {
        "citation_ranking": ranking[:top_n],
        "source_investment": build_source_investment(ranking, top_n),
        "article_titles": top_article_titles(citations, top_n),
    }


# --- DB helpers ---

async def store_citations(
    session: AsyncSession, provider_result_id, citations: list[Citation]
) -> int:
    for c in citations:
        session.add(
            CitationSource(
                provider_result_id=provider_result_id,
                idx=c.index,
                title=c.title,
                url=c.url,
                domain=c.domain,
                source_name=c.source_name,
                snippet=c.snippet,
            )
        )
    await session.flush()
    return len(citations)


async def fetch_run_citations(session: AsyncSession, run_id) -> list[dict]:
    stmt = (
        select(
            CitationSource.domain,
            CitationSource.source_name,
            CitationSource.title,
            CitationSource.url,
        )
        .join(ProviderResult, CitationSource.provider_result_id == ProviderResult.id)
        .where(ProviderResult.run_id == run_id)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {"domain": r.domain, "source_name": r.source_name, "title": r.title, "url": r.url}
        for r in rows
    ]
