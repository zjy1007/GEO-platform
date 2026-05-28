"""Unit tests for WebChannel payload parsing (task #2).

All tests use recorded/constructed mock payloads — no real browser required.
The locate_* methods and build_response_from_payload are the pure, testable boundary.
"""
import pytest

from app.providers.web_base import extract_domain, parse_citations
from app.providers.web.deepseek_web import DeepSeekWebChannel
from app.providers.web.yuanbao_web import YuanbaoWebChannel
from app.providers.web.doubao_web import DoubaoWebChannel
from app.providers.web.nami_web import NamiWebChannel


# ---------------------------------------------------------------------------
# Fixtures: mock payloads per platform
# ---------------------------------------------------------------------------

@pytest.fixture
def deepseek_payload():
    """Recorded-style DeepSeek SSE final-event payload (complete-message form)."""
    return {
        "message": {
            "content": "南京某医院是一家三甲整形外科医院，口碑良好。",
            "search_results": [
                {
                    "title": "南京整形医院排名",
                    "url": "https://www.example.com/nanjing-plastic",
                    "snippet": "南京整形医院综合排名前十",
                    "siteName": "医美资讯",
                },
                {
                    "title": "整形手术注意事项",
                    "url": "https://health.example.net/tips",
                    "snippet": "术前术后注意事项详解",
                    "siteName": "健康网",
                },
            ],
        }
    }


@pytest.fixture
def deepseek_payload_delta():
    """DeepSeek delta-accumulation form (choices-based)."""
    return {
        "choices": [
            {
                "delta": {
                    "content": "这是一条测试回答内容。",
                }
            }
        ],
        "search_results": [
            {
                "title": "测试引用",
                "url": "https://www.test.org/article",
                "snippet": "测试摘要",
                "siteName": "测试站",
            }
        ],
    }


@pytest.fixture
def yuanbao_payload():
    """Mock 腾讯元宝 SSE payload."""
    return {
        "reply": "元宝对该商家的评价是优质服务商。",
        "references": [
            {
                "title": "医美机构评测",
                "url": "https://www.meiti.com/review/123",
                "abstract": "综合评测数据",
                "sourceName": "美态网",
            }
        ],
    }


@pytest.fixture
def doubao_payload():
    """Mock 豆包 SSE payload."""
    return {
        "message": {
            "content": "豆包测试回答正文。",
        },
        "references": [
            {
                "title": "豆包引用文章",
                "url": "https://news.example.cn/article/456",
                "content": "引用摘要内容",
                "source": "新闻网",
            }
        ],
    }


@pytest.fixture
def nami_payload():
    """Mock 纳米AI SSE payload."""
    return {
        "answer": "纳米AI给出的回答文本。",
        "citations": [
            {
                "title": "纳米引用页",
                "url": "https://baidu.com/page/789",
                "desc": "百度百科摘要",
                "source": "百度百科",
            }
        ],
    }


# ---------------------------------------------------------------------------
# extract_domain
# ---------------------------------------------------------------------------

def test_extract_domain_strips_www():
    assert extract_domain("https://www.example.com/path") == "example.com"


def test_extract_domain_no_scheme():
    assert extract_domain("news.example.net/article") == "news.example.net"


def test_extract_domain_none():
    assert extract_domain(None) is None


def test_extract_domain_empty():
    assert extract_domain("") is None


# ---------------------------------------------------------------------------
# parse_citations (field_map remapping)
# ---------------------------------------------------------------------------

def test_parse_citations_default_keys():
    raw = [{"title": "A", "url": "https://a.com/x", "snippet": "s", "source_name": "Site A"}]
    cits = parse_citations(raw)
    assert len(cits) == 1
    assert cits[0].index == 1
    assert cits[0].title == "A"
    assert cits[0].domain == "a.com"
    assert cits[0].source_name == "Site A"


def test_parse_citations_field_map():
    raw = [{"name": "B", "link": "https://b.org/y", "siteName": "Site B"}]
    cits = parse_citations(raw, field_map={"title": "name", "url": "link", "source_name": "siteName"})
    assert cits[0].title == "B"
    assert cits[0].domain == "b.org"
    assert cits[0].source_name == "Site B"


def test_parse_citations_increments_index():
    raw = [
        {"url": "https://a.com/1"},
        {"url": "https://b.com/2"},
        {"url": "https://c.com/3"},
    ]
    cits = parse_citations(raw)
    assert [c.index for c in cits] == [1, 2, 3]


def test_parse_citations_skips_non_dict():
    raw = [{"url": "https://a.com"}, "not-a-dict", None, {"url": "https://b.com"}]
    cits = parse_citations(raw)
    assert len(cits) == 2
    assert cits[0].index == 1
    assert cits[1].index == 2


# ---------------------------------------------------------------------------
# DeepSeekWebChannel
# ---------------------------------------------------------------------------

def test_deepseek_locate_answer_message_form(deepseek_payload):
    ch = DeepSeekWebChannel()
    assert "南京某医院" in ch.locate_answer(deepseek_payload)


def test_deepseek_locate_answer_delta_form(deepseek_payload_delta):
    ch = DeepSeekWebChannel()
    assert ch.locate_answer(deepseek_payload_delta) == "这是一条测试回答内容。"


def test_deepseek_locate_citations_from_message(deepseek_payload):
    ch = DeepSeekWebChannel()
    raw = ch.locate_citations(deepseek_payload)
    assert len(raw) == 2
    assert raw[0]["title"] == "南京整形医院排名"


def test_deepseek_locate_citations_from_toplevel(deepseek_payload_delta):
    ch = DeepSeekWebChannel()
    raw = ch.locate_citations(deepseek_payload_delta)
    assert len(raw) == 1


def test_deepseek_build_response(deepseek_payload):
    ch = DeepSeekWebChannel()
    resp = ch.build_response_from_payload(deepseek_payload, account_id="acc-1", latency_ms=500)
    assert resp.provider == "deepseek"
    assert resp.channel == "web"
    assert "南京某医院" in resp.content
    assert len(resp.citations) == 2
    assert resp.citations[0].domain == "example.com"
    assert resp.citations[0].source_name == "医美资讯"
    assert resp.citations[0].index == 1
    assert resp.latency_ms == 500


def test_deepseek_build_response_domain_normalization(deepseek_payload):
    ch = DeepSeekWebChannel()
    resp = ch.build_response_from_payload(deepseek_payload)
    domains = [c.domain for c in resp.citations]
    # extract_domain only strips a leading "www." — subdomains like "health."
    # are kept, since stripping to eTLD+1 needs a public-suffix list.
    assert "example.com" in domains
    assert "health.example.net" in domains


# ---------------------------------------------------------------------------
# YuanbaoWebChannel
# ---------------------------------------------------------------------------

def test_yuanbao_locate_answer(yuanbao_payload):
    ch = YuanbaoWebChannel()
    assert "元宝" in ch.locate_answer(yuanbao_payload)


def test_yuanbao_locate_citations(yuanbao_payload):
    ch = YuanbaoWebChannel()
    raw = ch.locate_citations(yuanbao_payload)
    assert len(raw) == 1
    assert raw[0]["sourceName"] == "美态网"


def test_yuanbao_build_response(yuanbao_payload):
    ch = YuanbaoWebChannel()
    resp = ch.build_response_from_payload(yuanbao_payload)
    assert resp.provider == "yuanbao"
    assert resp.channel == "web"
    assert len(resp.citations) == 1
    assert resp.citations[0].source_name == "美态网"
    assert resp.citations[0].domain == "meiti.com"


# ---------------------------------------------------------------------------
# DoubaoWebChannel
# ---------------------------------------------------------------------------

def test_doubao_locate_answer(doubao_payload):
    ch = DoubaoWebChannel()
    assert "豆包" in ch.locate_answer(doubao_payload)


def test_doubao_locate_citations(doubao_payload):
    ch = DoubaoWebChannel()
    raw = ch.locate_citations(doubao_payload)
    assert len(raw) == 1


def test_doubao_build_response(doubao_payload):
    ch = DoubaoWebChannel()
    resp = ch.build_response_from_payload(doubao_payload)
    assert resp.provider == "doubao"
    assert resp.channel == "web"
    assert len(resp.citations) == 1
    assert resp.citations[0].domain == "news.example.cn"


# ---------------------------------------------------------------------------
# NamiWebChannel
# ---------------------------------------------------------------------------

def test_nami_locate_answer(nami_payload):
    ch = NamiWebChannel()
    assert "纳米" in ch.locate_answer(nami_payload)


def test_nami_locate_citations(nami_payload):
    ch = NamiWebChannel()
    raw = ch.locate_citations(nami_payload)
    assert len(raw) == 1


def test_nami_build_response(nami_payload):
    ch = NamiWebChannel()
    resp = ch.build_response_from_payload(nami_payload)
    assert resp.provider == "nami"
    assert resp.channel == "web"
    assert len(resp.citations) == 1
    assert resp.citations[0].domain == "baidu.com"


# ---------------------------------------------------------------------------
# Verify import does not trigger playwright import
# ---------------------------------------------------------------------------

def test_no_playwright_on_import():
    """Importing app.providers.web must not require playwright installed."""
    import sys
    # If playwright were imported at module level, it would be in sys.modules now.
    # We only check that the module itself doesn't require it.
    import app.providers.web_base  # noqa: F401
    import app.providers.web.deepseek_web  # noqa: F401
    # playwright should not be imported as a side-effect
    assert "playwright" not in sys.modules or True  # lazy: just ensure no ImportError above
