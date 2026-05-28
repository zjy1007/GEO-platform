from types import SimpleNamespace

from app.services import mention_extraction_service as ms


def _merchant():
    return SimpleNamespace(
        name="杭州某某宠物医院", address="滨江区xx路1号", city="杭州", district="滨江区"
    )


def test_build_prompt_includes_identity_and_answer():
    _system, user = ms.build_mention_prompt("某回答内容", _merchant(), ["某某宠物医院", "某某宠医"])
    assert "杭州某某宠物医院" in user
    assert "某某宠物医院、某某宠医" in user
    assert "滨江区xx路1号" in user
    assert "某回答内容" in user


def test_parse_full_payload():
    raw = {
        "is_mentioned": True,
        "rank_position": 3,
        "mention_text": "片段",
        "sentiment": "positive",
        "confidence": 0.8,
        "mentioned_brands": [{"brand": "A", "rank": 1}, {"brand": "目标", "rank": 3}],
    }
    out = ms.parse_mention(raw, "回答", [])
    assert out["is_mentioned"] is True
    assert out["rank_position"] == 3
    assert out["sentiment"] == "positive"
    assert out["confidence"] == 0.8
    assert out["mentioned_brands"] == [{"brand": "A", "rank": 1}, {"brand": "目标", "rank": 3}]


def test_parse_invalid_sentiment_defaults_neutral():
    out = ms.parse_mention({"is_mentioned": True, "sentiment": "好评"}, "回答", [])
    assert out["sentiment"] == "neutral"


def test_parse_invalid_rank_becomes_none():
    assert ms.parse_mention({"is_mentioned": True, "rank_position": 0}, "x", [])["rank_position"] is None
    assert ms.parse_mention({"is_mentioned": True, "rank_position": "abc"}, "x", [])["rank_position"] is None


def test_parse_brands_from_strings_get_index_rank():
    out = ms.parse_mention({"is_mentioned": True, "mentioned_brands": ["甲", "乙"]}, "x", [])
    assert out["mentioned_brands"] == [{"brand": "甲", "rank": 1}, {"brand": "乙", "rank": 2}]


def test_alias_floor_forces_mention():
    # model said not mentioned, but an exact alias appears in the answer
    answer = "我推荐某某宠物医院，服务不错"
    out = ms.parse_mention({"is_mentioned": False}, answer, ["某某宠物医院"])
    assert out["is_mentioned"] is True
    assert out["confidence"] >= 0.6


def test_not_mentioned_clears_rank():
    out = ms.parse_mention({"is_mentioned": False, "rank_position": 2}, "无关回答", [])
    assert out["is_mentioned"] is False
    assert out["rank_position"] is None


def test_parse_non_dict_returns_defaults():
    out = ms.parse_mention("garbage", "回答", [])
    assert out["is_mentioned"] is False
    assert out["mentioned_brands"] == []
