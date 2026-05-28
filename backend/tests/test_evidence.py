from app.services import evidence_service as es


def test_trust_level_for():
    assert es.trust_level_for("official_website") == 0.95
    assert es.trust_level_for("social") == 0.6
    assert es.trust_level_for("unknown") == es.DEFAULT_TRUST
    assert es.trust_level_for(None) == es.DEFAULT_TRUST


def test_normalize_text_strips_blank_lines():
    assert es.normalize_text("  a \n\n  b  \n") == "a\nb"


def test_content_hash_is_whitespace_stable():
    h1 = es.content_hash("本店提供宠物疫苗\n绝育手术")
    h2 = es.content_hash("  本店提供宠物疫苗  \n\n  绝育手术  \n")
    assert h1 == h2
    assert h1 != es.content_hash("不同内容")
    assert len(h1) == 64  # sha256 hex
