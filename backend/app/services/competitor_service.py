"""Competitor aggregation helpers (extracted from geo_scoring_service, task #1).

P4 track extensions (gap analysis, phase-level comparison) belong here —
not back in geo_scoring_service.

Key 口径（不可动摇②）: 提及率、排名、竞品对比一律按 phase (decision/doubt) 分开统计，不可混。
"""


def _is_target(brand: str, target_names: list[str]) -> bool:
    return any(t and (t == brand or t in brand or brand in t) for t in target_names if t)


def _phase_stats(occurrences_in_phase: list[dict], total_rows_in_phase: int) -> dict:
    """Compute appearances/rate/avg_rank for one brand within one phase.

    Args:
        occurrences_in_phase: list of {brand_rank: int|None} entries for this phase
        total_rows_in_phase:  total rows for this phase (denominator for rate)
    """
    appearances = len(occurrences_in_phase)
    ranks = [o["brand_rank"] for o in occurrences_in_phase if o["brand_rank"] is not None]
    return {
        "appearances": appearances,
        "rate": round(appearances / total_rows_in_phase, 4) if total_rows_in_phase else 0.0,
        "avg_rank": round(sum(ranks) / len(ranks), 2) if ranks else None,
    }


def aggregate_competitors(rows: list[dict], target_names: list[str]) -> list[dict]:
    """Return competitors sorted by total appearances desc.

    Backward-compatible: existing fields (brand, appearances, rate, is_target) are preserved.
    New fields added in this P4 extension:
        avg_rank        float|None  overall mean of the brand's per-response rank
        by_phase        dict        {decision: {appearances, rate, avg_rank},
                                     doubt:    {appearances, rate, avg_rank}}
        doubt_appearances int       shortcut == by_phase["doubt"]["appearances"]
    """
    total = len(rows)

    # Phase row-count denominators for per-phase rate
    phase_totals: dict[str, int] = {}
    for r in rows:
        ph = r.get("phase") or ""
        phase_totals[ph] = phase_totals.get(ph, 0) + 1

    # Per-brand: collect {phase, brand_rank} from every mentioned_brands entry
    brand_data: dict[str, list[dict]] = {}
    for r in rows:
        phase = r.get("phase") or ""
        for b in r.get("mentioned_brands") or []:
            name = b.get("brand") if isinstance(b, dict) else None
            if not name:
                continue
            brand_rank = b.get("rank")   # rank of *this* brand in *this* response; may be None
            brand_data.setdefault(name, []).append({"phase": phase, "brand_rank": brand_rank})

    result: list[dict] = []
    for brand, occurrences in brand_data.items():
        appearances = len(occurrences)

        # Overall avg_rank across all phases
        all_ranks = [o["brand_rank"] for o in occurrences if o["brand_rank"] is not None]
        avg_rank = round(sum(all_ranks) / len(all_ranks), 2) if all_ranks else None

        # Per-phase stats — MUST be split, never mixed (口径②)
        by_phase: dict[str, dict] = {}
        for ph in ("decision", "doubt"):
            ph_occ = [o for o in occurrences if o["phase"] == ph]
            by_phase[ph] = _phase_stats(ph_occ, phase_totals.get(ph, 0))

        result.append({
            "brand": brand,
            "appearances": appearances,
            "rate": round(appearances / total, 4) if total else 0.0,
            "avg_rank": avg_rank,
            "by_phase": by_phase,
            "doubt_appearances": by_phase["doubt"]["appearances"],
            "is_target": _is_target(brand, target_names),
        })

    return sorted(result, key=lambda x: -x["appearances"])


# ---------------------------------------------------------------------------
# Gap analysis (P4 new)
# ---------------------------------------------------------------------------

def _infer_gap_reason(
    brand: str,
    mention_rate_gap: float,
    avg_rank_gap: float | None,
    comp_doubt_more: bool,
) -> str:
    """Generate a human-readable diagnosis for the visibility gap.

    mention_rate_gap = target_rate - competitor_rate
        < 0  → target lags
        > 0  → target leads

    avg_rank_gap = target_avg_rank - competitor_avg_rank
        > 0  → target has higher rank number (worse position)
        < 0  → target ranks better
    """
    parts: list[str] = []

    if mention_rate_gap < -0.001:
        pct = abs(mention_rate_gap) * 100
        parts.append(
            f"目标商家提及率低于{brand} {pct:.0f} 个百分点，可能因权威信源覆盖不足"
        )
    elif mention_rate_gap > 0.001:
        pct = mention_rate_gap * 100
        parts.append(f"目标商家提及率领先{brand} {pct:.0f} 个百分点")
    else:
        parts.append(f"目标商家与{brand}提及率持平")

    if avg_rank_gap is not None:
        if avg_rank_gap > 0.5:
            parts.append(
                f"排名平均落后 {avg_rank_gap:.1f} 位，建议优化结构化内容与评价数量"
            )
        elif avg_rank_gap < -0.5:
            parts.append(f"排名平均领先 {abs(avg_rank_gap):.1f} 位")

    if comp_doubt_more:
        parts.append("竞品在负面质疑期出现频率更高，需关注口碑防御策略")

    return "；".join(parts) if parts else f"目标商家与{brand}可见度相当，建议持续监控"


def build_competitor_gaps(competitors: list[dict], target_names: list[str]) -> list[dict]:
    """Compute visibility gap between the target brand and each non-target competitor.

    Input: the list returned by aggregate_competitors (must include by_phase + avg_rank).
    Output: list sorted by |mention_rate_gap| desc (worst gaps first). Each entry:

        brand               str         competitor brand name
        target_rate         float       target's overall mention rate
        competitor_rate     float       competitor's overall mention rate
        mention_rate_gap    float       target_rate - competitor_rate  (neg = target lags)
        target_avg_rank     float|None  target's mean rank
        competitor_avg_rank float|None  competitor's mean rank
        avg_rank_gap        float|None  target_avg_rank - competitor_avg_rank
        by_phase_gap        dict        per-phase breakdown of rate_gap and rank_gap
        reason              str         human-readable diagnosis
    """
    target = next((c for c in competitors if c.get("is_target")), None)
    if target is None:
        return []

    target_rate: float = target["rate"]
    target_avg_rank: float | None = target.get("avg_rank")
    target_by_phase: dict = target.get("by_phase", {})

    gaps: list[dict] = []
    for comp in competitors:
        if comp.get("is_target"):
            continue

        comp_rate: float = comp["rate"]
        comp_avg_rank: float | None = comp.get("avg_rank")
        comp_by_phase: dict = comp.get("by_phase", {})

        mention_rate_gap = round(target_rate - comp_rate, 4)

        if target_avg_rank is not None and comp_avg_rank is not None:
            avg_rank_gap: float | None = round(target_avg_rank - comp_avg_rank, 2)
        else:
            avg_rank_gap = None

        # Per-phase gap — kept split (口径②), never collapsed
        by_phase_gap: dict[str, dict] = {}
        for ph in ("decision", "doubt"):
            t_ph = target_by_phase.get(ph, {})
            c_ph = comp_by_phase.get(ph, {})
            t_r = t_ph.get("rate", 0.0)
            c_r = c_ph.get("rate", 0.0)
            t_rank = t_ph.get("avg_rank")
            c_rank = c_ph.get("avg_rank")
            by_phase_gap[ph] = {
                "rate_gap": round(t_r - c_r, 4),
                "rank_gap": (
                    round(t_rank - c_rank, 2)
                    if t_rank is not None and c_rank is not None
                    else None
                ),
            }

        # Is competitor more visible in the doubt (negative) phase than target?
        comp_doubt_more = (
            comp_by_phase.get("doubt", {}).get("appearances", 0)
            > target_by_phase.get("doubt", {}).get("appearances", 0)
        )

        reason = _infer_gap_reason(comp["brand"], mention_rate_gap, avg_rank_gap, comp_doubt_more)

        gaps.append({
            "brand": comp["brand"],
            "target_rate": target_rate,
            "competitor_rate": comp_rate,
            "mention_rate_gap": mention_rate_gap,
            "target_avg_rank": target_avg_rank,
            "competitor_avg_rank": comp_avg_rank,
            "avg_rank_gap": avg_rank_gap,
            "by_phase_gap": by_phase_gap,
            "reason": reason,
        })

    # Primary sort: biggest absolute gap first; tie-break: target-lagging gaps before leading ones
    return sorted(gaps, key=lambda x: (-abs(x["mention_rate_gap"]), x["mention_rate_gap"]))
