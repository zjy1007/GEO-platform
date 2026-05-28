from app.providers.web_base import extract_domain, parse_citations
from app.services import citation_service as cs
from app.services.report_service import render_html


def test_extract_domain():
    assert extract_domain("https://www.sina.com.cn/a/b") == "sina.com.cn"
    assert extract_domain("http://news.qq.com/x") == "news.qq.com"
    assert extract_domain("taobao.com/item") == "taobao.com"
    assert extract_domain(None) is None
    assert extract_domain("") is None


def test_parse_citations_basic_and_field_map():
    raw = [
        {"title": "南京晨报报道", "url": "https://www.njcb.com.cn/p1", "snippet": "片段"},
        {"name": "淘宝店铺", "link": "https://item.taobao.com/x"},
    ]
    # first uses default keys, second needs field_map → parse separately to show remap
    c1 = parse_citations([raw[0]])
    assert c1[0].index == 1
    assert c1[0].title == "南京晨报报道"
    assert c1[0].domain == "njcb.com.cn"
    assert c1[0].snippet == "片段"

    c2 = parse_citations([raw[1]], field_map={"title": "name", "url": "link"})
    assert c2[0].title == "淘宝店铺"
    assert c2[0].domain == "item.taobao.com"


def test_parse_citations_skips_non_dict():
    assert parse_citations(["x", 123, None]) == []
    assert parse_citations(None) == []


def _citations():
    return [
        {"domain": "sina.com.cn", "source_name": "新浪", "title": "文章A", "url": "u1"},
        {"domain": "sina.com.cn", "source_name": "新浪", "title": "文章A", "url": "u2"},
        {"domain": "sina.com.cn", "source_name": "新浪", "title": "文章B", "url": "u3"},
        {"domain": "qq.com", "source_name": "腾讯网", "title": "文章C", "url": "u4"},
        {"domain": "njcb.com.cn", "source_name": "南京晨报", "title": "文章D", "url": "u5"},
    ]


def test_aggregate_ranking():
    ranking = cs.aggregate_ranking(_citations())
    assert ranking[0]["domain"] == "sina.com.cn"
    assert ranking[0]["count"] == 3
    assert ranking[0]["rate"] == round(3 / 5, 4)
    assert ranking[0]["label"] == "新浪"
    assert {r["domain"] for r in ranking} == {"sina.com.cn", "qq.com", "njcb.com.cn"}


def test_aggregate_ranking_empty():
    assert cs.aggregate_ranking([]) == []


def test_build_source_investment_tiers_and_percentage():
    ranking = cs.aggregate_ranking(_citations())
    inv = cs.build_source_investment(ranking, top_n=10)
    # subtotal over top = 3+1+1 = 5 → 新浪 = 60%
    assert inv[0]["label"] == "新浪"
    assert inv[0]["percentage"] == 60.0
    assert inv[0]["priority"] == "high"
    assert sum(s["percentage"] for s in inv) == 100.0


def test_top_article_titles():
    titles = cs.top_article_titles(_citations())
    assert titles[0] == {"title": "文章A", "count": 2}


def test_build_citation_report_shape():
    rep = cs.build_citation_report(_citations())
    assert set(rep.keys()) == {"citation_ranking", "source_investment", "article_titles"}
    assert rep["citation_ranking"][0]["count"] == 3


def test_render_html_shows_citation_blocks_when_present():
    rep = cs.build_citation_report(_citations())
    report = {
        "geo_score": 50.0,
        "merchant": {"name": "测试商家", "city": "南京", "category": "医美"},
        "overall": {"mention_rate": 0.1, "exposure_avg": 0.2, "positive_rate": 0.5},
        "completeness": 60,
        "by_provider_phase": [],
        "by_phase": {"decision": {}, "doubt": {}},
        "competitors": [],
        "recommendations": [],
        **rep,
    }
    html = render_html(report)
    assert "引用源平台排行榜" in html
    assert "信源投放建议" in html
    assert "新浪" in html
    assert "第一优先级" in html


def test_render_html_citation_placeholder_when_empty():
    report = {
        "geo_score": 0, "merchant": {"name": "x"}, "overall": {},
        "by_provider_phase": [], "by_phase": {"decision": {}, "doubt": {}},
        "competitors": [], "recommendations": [], "citation_ranking": [], "source_investment": [],
    }
    assert "P2 账号池接入后填充" in render_html(report)
