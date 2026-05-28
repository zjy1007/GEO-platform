"""GEO scoring (P1.6).

MVP headline score (doc §七 修订口径):
    geo_score = 100 * (0.7 * 提及率 + 0.3 * 排名/曝光加权)
The 7-factor weighting (evidence/consistency/freshness…) is the long-term target;
those sub-metrics need data we don't have until P2/P3, so they stay out of the
headline for now. All aggregation is split by phase (decision/doubt).

Pure helpers (exposure_score / aggregate_metrics / build_recommendations) are unit-tested.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geo import GeoPrompt, GeoReport, GeoRun, MentionResult, ProviderResult
from app.models.merchant import Merchant
from app.services import citation_service
from app.services import competitor_service
from app.services import evidence_verification_service as verify_svc
from app.services import merchant_profile_service as merchant_svc

WEIGHT_MENTION = 0.7
WEIGHT_EXPOSURE = 0.3
MAX_RANK = 5
MENTIONED_UNRANKED_EXPOSURE = 0.4  # mentioned in prose but not in a ranked list


def exposure_score(rank: int | None, is_mentioned: bool) -> float:
    if not is_mentioned:
        return 0.0
    if rank is None:
        return MENTIONED_UNRANKED_EXPOSURE
    if rank > MAX_RANK or rank < 1:
        return 0.0
    return round((MAX_RANK - rank + 1) / MAX_RANK, 4)


def _group_metrics(rows: list[dict]) -> dict:
    total = len(rows)
    if total == 0:
        return {"total": 0, "mentioned": 0, "mention_rate": 0.0, "exposure_avg": 0.0,
                "positive_rate": 0.0, "avg_rank": None}
    mentioned = sum(1 for r in rows if r["is_mentioned"])
    exposures = [exposure_score(r["rank_position"], r["is_mentioned"]) for r in rows]
    positive = sum(1 for r in rows if r["is_mentioned"] and r["sentiment"] == "positive")
    ranks = [r["rank_position"] for r in rows if r["is_mentioned"] and r["rank_position"]]
    return {
        "total": total,
        "mentioned": mentioned,
        "mention_rate": round(mentioned / total, 4),
        "exposure_avg": round(sum(exposures) / total, 4),
        "positive_rate": round(positive / mentioned, 4) if mentioned else 0.0,
        "avg_rank": round(sum(ranks) / len(ranks), 2) if ranks else None,
    }


def aggregate_metrics(rows: list[dict], target_names: list[str]) -> dict:
    overall = _group_metrics(rows)
    geo_score = round(100 * (WEIGHT_MENTION * overall["mention_rate"]
                             + WEIGHT_EXPOSURE * overall["exposure_avg"]), 1)

    by_phase = {ph: _group_metrics([r for r in rows if r["phase"] == ph]) for ph in ("decision", "doubt")}

    buckets: dict[tuple, list[dict]] = {}
    for r in rows:
        buckets.setdefault((r["provider"], r["phase"]), []).append(r)
    by_provider_phase = [
        {"provider": p, "phase": ph, **_group_metrics(g)} for (p, ph), g in sorted(buckets.items())
    ]

    competitors = competitor_service.aggregate_competitors(rows, target_names)

    return {
        "geo_score": geo_score,
        "overall": overall,
        "by_phase": by_phase,
        "by_provider_phase": by_provider_phase,
        "competitors": competitors,
    }


def build_recommendations(metrics: dict, completeness_suggestions: list[str]) -> list[dict]:
    recs: list[dict] = []
    o = metrics["overall"]
    if o["total"] and o["mention_rate"] < 0.2:
        recs.append({"priority": "high",
                     "text": f"AI 自然提及率仅 {o['mention_rate'] * 100:.0f}%，建议补充可被 AI 引用的权威信源页与本地化内容"})
    if o["mentioned"] and o["exposure_avg"] < 0.3:
        recs.append({"priority": "high",
                     "text": "被推荐时排名靠后，建议完善服务项目页、FAQ 与第三方评价以提升推荐位次"})
    if metrics["by_phase"]["doubt"]["mentioned"] > 0:
        recs.append({"priority": "high",
                     "text": "在负面质疑期问题中被提及，需关注口碑与负面信息处理"})
    if o["mentioned"] and o["positive_rate"] < 0.6:
        recs.append({"priority": "medium",
                     "text": f"正向描述率 {o['positive_rate'] * 100:.0f}%，建议补充正面案例与资质背书"})
    for s in completeness_suggestions[:3]:
        recs.append({"priority": "medium", "text": s})
    if not recs:
        recs.append({"priority": "low", "text": "基础指标良好，可持续监控竞品动态并补充权威信源"})
    return recs


async def fetch_rows(session: AsyncSession, run_id) -> list[dict]:
    stmt = (
        select(
            ProviderResult.provider,
            GeoPrompt.phase,
            MentionResult.is_mentioned,
            MentionResult.rank_position,
            MentionResult.sentiment,
            MentionResult.mentioned_brands,
        )
        .join(ProviderResult, MentionResult.provider_result_id == ProviderResult.id)
        .join(GeoPrompt, ProviderResult.prompt_id == GeoPrompt.id)
        .where(ProviderResult.run_id == run_id)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "provider": r.provider,
            "phase": r.phase,
            "is_mentioned": bool(r.is_mentioned),
            "rank_position": r.rank_position,
            "sentiment": r.sentiment,
            "mentioned_brands": r.mentioned_brands,
        }
        for r in rows
    ]


async def compute_and_store(
    session: AsyncSession, run: GeoRun, merchant: Merchant, aliases: list[str]
) -> GeoReport:
    rows = await fetch_rows(session, run.id)
    target_names = [merchant.name, *aliases]
    metrics = aggregate_metrics(rows, target_names)

    completeness = merchant_svc.compute_completeness(
        {f: getattr(merchant, f, None) for f in merchant_svc._FIELD_WEIGHTS}
    )

    # Citation blocks come from account-pool (web channel) data; empty until P2 scraping runs.
    citations = await citation_service.fetch_run_citations(session, run.id)
    citation_report = citation_service.build_citation_report(citations)

    # Evidence verifiability (P3.2); None when no claims were verified for this run.
    statuses = await verify_svc.fetch_run_verification_statuses(session, run.id)
    evidence_rate = verify_svc.compute_evidence_rate(statuses)

    report_json = {
        **metrics,
        "merchant": {"name": merchant.name, "city": merchant.city, "category": merchant.category},
        "run_id": str(run.id),
        "completeness": completeness.score,
        "evidence_rate": evidence_rate,
        **citation_report,  # citation_ranking / source_investment / article_titles
        "recommendations": build_recommendations(metrics, completeness.suggestions),
    }

    report = GeoReport(
        run_id=run.id,
        merchant_id=merchant.id,
        geo_score=metrics["geo_score"],
        mention_rate=metrics["overall"]["mention_rate"],
        evidence_rate=evidence_rate,
        positive_rate=metrics["overall"]["positive_rate"],
        rank_score=metrics["overall"]["exposure_avg"],
        report_json=report_json,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def get_latest_report(session: AsyncSession, run_id) -> GeoReport | None:
    stmt = (
        select(GeoReport)
        .where(GeoReport.run_id == run_id)
        .order_by(GeoReport.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
