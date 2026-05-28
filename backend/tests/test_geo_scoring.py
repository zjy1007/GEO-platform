from app.services import geo_scoring_service as s
from app.services.report_service import render_html


def test_exposure_score():
    assert s.exposure_score(1, True) == 1.0
    assert s.exposure_score(5, True) == 0.2
    assert s.exposure_score(6, True) == 0.0
    assert s.exposure_score(None, True) == 0.4
    assert s.exposure_score(3, False) == 0.0


def _rows():
    return [
        {"provider": "deepseek", "phase": "decision", "is_mentioned": True, "rank_position": 1,
         "sentiment": "positive", "mentioned_brands": [{"brand": "目标商家", "rank": 1}, {"brand": "竞品A", "rank": 2}]},
        {"provider": "deepseek", "phase": "decision", "is_mentioned": False, "rank_position": None,
         "sentiment": None, "mentioned_brands": [{"brand": "竞品A", "rank": 1}]},
        {"provider": "qwen", "phase": "doubt", "is_mentioned": True, "rank_position": 3,
         "sentiment": "negative", "mentioned_brands": [{"brand": "目标商家", "rank": 3}]},
    ]


def test_aggregate_overall_and_phase():
    m = s.aggregate_metrics(_rows(), ["目标商家"])
    o = m["overall"]
    assert o["total"] == 3
    assert o["mentioned"] == 2
    assert o["mention_rate"] == round(2 / 3, 4)
    assert o["exposure_avg"] == round((1.0 + 0.0 + 0.6) / 3, 4)
    assert 0 <= m["geo_score"] <= 100
    assert m["by_phase"]["decision"]["total"] == 2
    assert m["by_phase"]["doubt"]["mentioned"] == 1


def test_aggregate_competitors_marks_target():
    m = s.aggregate_metrics(_rows(), ["目标商家"])
    brands = {c["brand"]: c for c in m["competitors"]}
    assert brands["目标商家"]["is_target"] is True
    assert brands["竞品A"]["is_target"] is False
    assert brands["竞品A"]["appearances"] == 2


def test_aggregate_empty():
    m = s.aggregate_metrics([], ["x"])
    assert m["geo_score"] == 0.0
    assert m["overall"]["total"] == 0
    assert m["competitors"] == []


def test_build_recommendations_flags_low_mention():
    m = s.aggregate_metrics(
        [{"provider": "deepseek", "phase": "decision", "is_mentioned": False,
          "rank_position": None, "sentiment": None, "mentioned_brands": []}],
        ["x"],
    )
    recs = s.build_recommendations(m, ["补全「官网」"])
    assert any(r["priority"] == "high" for r in recs)


def test_render_html_contains_core_fields():
    report = {
        "geo_score": 63.5,
        "merchant": {"name": "测试医院", "city": "杭州", "category": "宠物医疗"},
        "overall": {"mention_rate": 0.12, "exposure_avg": 0.3, "positive_rate": 0.7},
        "completeness": 67,
        "by_provider_phase": [{"provider": "deepseek", "phase": "decision",
                               "mention_rate": 0.16, "avg_rank": 3.2, "mentioned": 4, "total": 25}],
        "by_phase": {"decision": {"mention_rate": 0.16, "exposure_avg": 0.3, "positive_rate": 0.7, "mentioned": 4, "total": 25},
                     "doubt": {"mention_rate": 0.05, "exposure_avg": 0.1, "positive_rate": 0.0, "mentioned": 1, "total": 25}},
        "competitors": [{"brand": "测试医院", "appearances": 3, "rate": 0.12, "is_target": True},
                        {"brand": "竞品A", "appearances": 10, "rate": 0.4, "is_target": False}],
        "recommendations": [{"priority": "high", "text": "补充权威信源"}],
    }
    html = render_html(report, "2026-05-28 10:00")
    assert "测试医院" in html
    assert "63.5" in html
    assert "DeepSeek" in html
    assert "竞品A" in html
    assert "补充权威信源" in html
    assert "<table" in html
