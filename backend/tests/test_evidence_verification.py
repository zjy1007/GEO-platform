from app.services import evidence_verification_service as vs


def test_parse_claims_variants():
    raw = [{"claim": "该商家位于滨江区", "claim_type": "address"}, "提供宠物疫苗", {"text": "  "}]
    out = vs.parse_claims(raw)
    assert len(out) == 2
    assert out[0] == {"claim": "该商家位于滨江区", "claim_type": "address"}
    assert out[1]["claim"] == "提供宠物疫苗" and out[1]["claim_type"] is None


def test_parse_claims_wrapped_and_nonlist():
    assert vs.parse_claims({"claims": [{"claim": "x"}]})[0]["claim"] == "x"
    assert vs.parse_claims("garbage") == []


def test_similarity():
    assert vs.similarity("宠物疫苗接种", "宠物疫苗接种") == 1.0
    assert vs.similarity("宠物疫苗", "完全无关内容ABC") == 0.0
    assert 0 < vs.similarity("提供宠物疫苗服务", "本店提供宠物疫苗") < 1.0


def test_retrieve_evidence_threshold():
    ev = [
        {"id": 1, "content_text": "本店提供宠物疫苗、绝育手术"},
        {"id": 2, "content_text": "停车场信息与周边美食"},
    ]
    best, score = vs.retrieve_evidence("提供宠物疫苗", ev, threshold=0.3)
    assert best["id"] == 1 and score >= 0.3

    none, low = vs.retrieve_evidence("完全不相关的主题XYZ", ev, threshold=0.3)
    assert none is None


def test_parse_verification_normalizes_status():
    assert vs.parse_verification({"status": "supported", "confidence": 0.9})["status"] == "supported"
    assert vs.parse_verification({"status": "好的"})["status"] == "unsupported"
    assert vs.parse_verification({"status": "contradicted", "confidence": "x"})["confidence"] is None
    assert vs.parse_verification("garbage")["status"] == "unsupported"


def test_compute_evidence_rate():
    assert vs.compute_evidence_rate([]) is None
    assert vs.compute_evidence_rate(["supported", "supported", "unsupported", "contradicted"]) == 0.5
    assert vs.compute_evidence_rate(["unsupported"]) == 0.0
