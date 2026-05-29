"""Tests for competitor_service: by_phase split, avg_rank, gap analysis, is_target."""
from app.services import competitor_service as cs


def _rows():
    return [
        # decision phase — target mentioned rank 1, competitor A rank 2
        {"provider": "deepseek", "phase": "decision", "is_mentioned": True,
         "rank_position": 1, "sentiment": "positive",
         "mentioned_brands": [{"brand": "目标商家", "rank": 1}, {"brand": "竞品A", "rank": 2}]},
        # decision phase — target not mentioned, competitor A rank 1
        {"provider": "deepseek", "phase": "decision", "is_mentioned": False,
         "rank_position": None, "sentiment": None,
         "mentioned_brands": [{"brand": "竞品A", "rank": 1}]},
        # doubt phase — only competitor A appears (target not mentioned here)
        {"provider": "qwen", "phase": "doubt", "is_mentioned": False,
         "rank_position": None, "sentiment": None,
         "mentioned_brands": [{"brand": "竞品A", "rank": 1}]},
        # doubt phase — target mentioned rank 3
        {"provider": "qwen", "phase": "doubt", "is_mentioned": True,
         "rank_position": 3, "sentiment": "negative",
         "mentioned_brands": [{"brand": "目标商家", "rank": 3}]},
    ]


# ---------------------------------------------------------------------------
# aggregate_competitors
# ---------------------------------------------------------------------------

def test_is_target_correctly_identified():
    competitors = cs.aggregate_competitors(_rows(), ["目标商家"])
    brands = {c["brand"]: c for c in competitors}
    assert brands["目标商家"]["is_target"] is True
    assert brands["竞品A"]["is_target"] is False


def test_backward_compatible_fields_present():
    competitors = cs.aggregate_competitors(_rows(), ["目标商家"])
    for c in competitors:
        assert "brand" in c
        assert "appearances" in c
        assert "rate" in c
        assert "is_target" in c


def test_new_fields_present():
    competitors = cs.aggregate_competitors(_rows(), ["目标商家"])
    for c in competitors:
        assert "avg_rank" in c
        assert "by_phase" in c
        assert "doubt_appearances" in c


def test_by_phase_split_not_mixed():
    """decision and doubt stats must be independently computed, not collapsed."""
    competitors = cs.aggregate_competitors(_rows(), ["竞品A"])
    brands = {c["brand"]: c for c in competitors}
    comp_a = brands["竞品A"]

    decision = comp_a["by_phase"]["decision"]
    doubt = comp_a["by_phase"]["doubt"]

    # In decision phase: 竞品A appears in both rows → 2 appearances out of 2 decision rows
    assert decision["appearances"] == 2
    assert decision["rate"] == 1.0

    # In doubt phase: 竞品A appears in 1 of 2 doubt rows
    assert doubt["appearances"] == 1
    assert doubt["rate"] == 0.5


def test_avg_rank_computed_correctly():
    competitors = cs.aggregate_competitors(_rows(), ["目标商家"])
    brands = {c["brand"]: c for c in competitors}

    # 竞品A ranks: 2 (decision row 1), 1 (decision row 2), 1 (doubt row) → avg = (2+1+1)/3 = 1.33
    assert brands["竞品A"]["avg_rank"] == round((2 + 1 + 1) / 3, 2)

    # 目标商家 ranks: 1 (decision), 3 (doubt) → avg = 2.0
    assert brands["目标商家"]["avg_rank"] == 2.0


def test_doubt_appearances_shortcut():
    competitors = cs.aggregate_competitors(_rows(), ["目标商家"])
    brands = {c["brand"]: c for c in competitors}
    comp_a = brands["竞品A"]
    assert comp_a["doubt_appearances"] == comp_a["by_phase"]["doubt"]["appearances"]


def test_sorted_by_appearances_desc():
    competitors = cs.aggregate_competitors(_rows(), ["目标商家"])
    appearances = [c["appearances"] for c in competitors]
    assert appearances == sorted(appearances, reverse=True)


def test_empty_rows():
    result = cs.aggregate_competitors([], ["目标商家"])
    assert result == []


def test_no_target_in_data():
    """Target name not found in any mention → is_target stays False for all."""
    competitors = cs.aggregate_competitors(_rows(), ["不存在的品牌"])
    assert all(not c["is_target"] for c in competitors)


# ---------------------------------------------------------------------------
# build_competitor_gaps
# ---------------------------------------------------------------------------

def test_gaps_empty_when_no_target():
    competitors = cs.aggregate_competitors(_rows(), ["不存在的品牌"])
    gaps = cs.build_competitor_gaps(competitors, ["不存在的品牌"])
    assert gaps == []


def test_gaps_mention_rate_gap_sign():
    """mention_rate_gap = target_rate - competitor_rate; negative means target lags."""
    competitors = cs.aggregate_competitors(_rows(), ["目标商家"])
    gaps = cs.build_competitor_gaps(competitors, ["目标商家"])
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap["brand"] == "竞品A"
    # target has 2 appearances / 4 rows = 0.5; competitor A has 3/4 = 0.75
    assert gap["target_rate"] == 0.5
    assert gap["competitor_rate"] == 0.75
    assert gap["mention_rate_gap"] == round(0.5 - 0.75, 4)  # -0.25 → target lags


def test_gaps_avg_rank_gap():
    competitors = cs.aggregate_competitors(_rows(), ["目标商家"])
    gaps = cs.build_competitor_gaps(competitors, ["目标商家"])
    gap = gaps[0]
    # target avg_rank=2.0, competitor avg_rank=1.33 → gap = 0.67 (target rank worse)
    assert gap["avg_rank_gap"] == round(2.0 - round((2 + 1 + 1) / 3, 2), 2)


def test_gaps_by_phase_gap_not_collapsed():
    """Per-phase gap must contain both decision and doubt entries."""
    competitors = cs.aggregate_competitors(_rows(), ["目标商家"])
    gaps = cs.build_competitor_gaps(competitors, ["目标商家"])
    by_phase_gap = gaps[0]["by_phase_gap"]
    assert "decision" in by_phase_gap
    assert "doubt" in by_phase_gap
    for ph_gap in by_phase_gap.values():
        assert "rate_gap" in ph_gap
        assert "rank_gap" in ph_gap


def test_gaps_reason_is_string():
    competitors = cs.aggregate_competitors(_rows(), ["目标商家"])
    gaps = cs.build_competitor_gaps(competitors, ["目标商家"])
    assert isinstance(gaps[0]["reason"], str)
    assert len(gaps[0]["reason"]) > 0


def test_gaps_sorted_by_abs_gap_desc():
    """Gaps should be ordered by absolute mention rate gap descending."""
    # Build a scenario with two competitors: one with large gap, one with small gap
    rows = [
        {"provider": "p", "phase": "decision", "is_mentioned": True, "rank_position": 1,
         "sentiment": "positive",
         "mentioned_brands": [{"brand": "目标商家", "rank": 1}, {"brand": "竞品小", "rank": 2}]},
        *[
            {"provider": "p", "phase": "decision", "is_mentioned": False, "rank_position": None,
             "sentiment": None,
             "mentioned_brands": [{"brand": "竞品大", "rank": 1}]}
            for _ in range(4)
        ],
    ]
    competitors = cs.aggregate_competitors(rows, ["目标商家"])
    gaps = cs.build_competitor_gaps(competitors, ["目标商家"])
    abs_gaps = [abs(g["mention_rate_gap"]) for g in gaps]
    assert abs_gaps == sorted(abs_gaps, reverse=True)
