from app.services import prompt_generation_service as ps

MERCHANT = {
    "name": "杭州某某宠物医院",
    "category": "宠物医疗",
    "city": "杭州",
    "district": "滨江区",
    "services": ["疫苗", "绝育"],
}


def test_build_prompt_organic_excludes_merchant_name():
    _system, user = ps.build_generation_prompt(MERCHANT, "organic", "decision", 10)
    assert "10" in user
    assert "杭州某某宠物医院" not in user  # organic 必须不点名商家
    assert "品牌决策期" in user
    assert "宠物医疗" in user
    assert "疫苗、绝育" in user


def test_build_prompt_diagnostic_includes_merchant_name():
    _system, user = ps.build_generation_prompt(MERCHANT, "diagnostic", "doubt", 5)
    assert "杭州某某宠物医院" in user
    assert "负面质疑期" in user


def test_normalize_list_of_dicts_tags_mode_phase():
    raw = [{"question": "杭州滨江宠物医院推荐?", "scenario_type": "category_recommendation", "intent": "recommend"}]
    rows = ps.normalize_questions(raw, "organic", "decision", MERCHANT)
    assert len(rows) == 1
    r = rows[0]
    assert r["prompt_text"] == "杭州滨江宠物医院推荐?"
    assert r["mode"] == "organic" and r["phase"] == "decision"
    assert r["city"] == "杭州" and r["category"] == "宠物医疗"
    assert r["scenario_type"] == "category_recommendation"


def test_normalize_list_of_strings():
    rows = ps.normalize_questions(["问题1", "问题2"], "organic", "doubt", MERCHANT)
    assert [r["prompt_text"] for r in rows] == ["问题1", "问题2"]
    assert all(r["scenario_type"] is None for r in rows)


def test_normalize_wrapped_object_and_skips_blank():
    raw = {"questions": [{"question": "q1"}, {"question": "  "}, {"question": ""}, {"foo": "bar"}]}
    rows = ps.normalize_questions(raw, "organic", "decision", MERCHANT)
    assert len(rows) == 1 and rows[0]["prompt_text"] == "q1"


def test_normalize_non_list_returns_empty():
    assert ps.normalize_questions("garbage", "organic", "decision", MERCHANT) == []


def test_tier_counts():
    assert ps.TIER_COUNTS == {"basic": 20, "standard": 50, "professional": 100}
