from app.services import merchant_profile_service as svc


def test_completeness_empty():
    res = svc.compute_completeness({})
    assert res.score == 0
    assert res.filled_fields == []
    assert "name" in res.missing_fields
    assert len(res.suggestions) == len(res.missing_fields)


def test_completeness_full_is_100():
    data = {
        "name": "杭州某某宠物医院",
        "category": "宠物医疗",
        "city": "杭州",
        "district": "滨江区",
        "address": "杭州市滨江区xxx路1号",
        "phone": "0571-1234567",
        "website": "https://example.com",
        "business_hours": "09:00-21:00",
        "services": ["疫苗", "绝育"],
        "price_range": "100-500",
        "target_keywords": ["杭州宠物医院"],
        "official_sources": ["https://example.com"],
        "competitors": ["竞品A"],
    }
    res = svc.compute_completeness(data)
    assert res.score == 100
    assert res.missing_fields == []


def test_completeness_partial_weights():
    # name(10) + phone(10) = 20
    res = svc.compute_completeness({"name": "x", "phone": "123"})
    assert res.score == 20
    assert set(res.filled_fields) == {"name", "phone"}


def test_empty_list_counts_as_missing():
    res = svc.compute_completeness({"name": "x", "services": []})
    assert "services" in res.missing_fields


def test_generate_aliases_strips_city_prefix():
    aliases = svc.generate_aliases("杭州某某宠物医院", city="杭州", district="滨江区")
    texts = [a["alias"] for a in aliases]
    assert "杭州某某宠物医院" in texts  # standard
    assert "某某宠物医院" in texts  # city stripped
    assert aliases[0]["alias_type"] == "standard"


def test_nap_check_flags_missing_phone():
    res = svc.check_nap({"name": "x", "address": "y"})
    assert res.consistent is False
    assert any("电话" in i for i in res.issues)
