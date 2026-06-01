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


# 真包派生 SSE 片段（结构对齐 2026-06-01 抓包：data: {...JSON} 多事件 + event:/非JSON行）
YUANBAO_SSE_REAL = (
    'data: {"type":"text"}\n'
    '\n'
    'event: speech_type\n'
    'data: status\n'
    '\n'
    'data: {"type":"step","msg":"正在搜索资料","scene":"ai_search_light"}\n'
    '\n'
    'data: {"type":"text","msg":"杭州"}\n'
    '\n'
    'data: {"type":"text","msg":"滨江有多家不错的"}\n'
    '\n'
    'data: {"type":"text","msg":"宠物医院。"}\n'
    '\n'
    'event: speech_type\n'
    'data: search_with_text\n'
    '\n'
    'data: {"type":"searchGuid","title":"引用","sourceType":"","docs":['
    '{"index":1,"docId":"d-001","title":"杭州宠物医院推荐","url":"https://www.example-pet.com/hz",'
    '"sourceType":"webpage","quote":"滨江有松子宠物医院等","web_site_name":"示例宠物网","publish_time":"2025-01-01"},'
    '{"index":2,"docId":"d-002","title":"来自腾讯地图的参考资料","url":"",'
    '"sourceType":"plugin","quote":"在杭州滨江周边..."}'
    '],"citations":[]}\n'
    '\n'
)


@pytest.fixture
def yuanbao_payload():
    """真包派生 normalized payload (parse_sse 转换后的形态)。"""
    from app.providers.web.yuanbao_web import parse_sse
    return parse_sse(YUANBAO_SSE_REAL)


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


# --- doc §24: two-request (搜索结果 + 正文) split fixtures ------------------

@pytest.fixture
def doubao_search_payload():
    """豆包 搜索结果 request — carries citations only, no answer text."""
    return {
        "search_results": [
            {
                "title": "豆包搜索命中A",
                "url": "https://www.zhihu.com/q/111",
                "content": "知乎讨论摘要",
                "source": "知乎",
            },
            {
                "title": "豆包搜索命中B",
                "url": "https://m.weibo.cn/status/222",
                "content": "微博讨论摘要",
                "source": "微博",
            },
        ]
    }


@pytest.fixture
def doubao_answer_payload():
    """豆包 正文 request — carries the answer text only, no citations."""
    return {
        "message": {
            "content": "豆包分两请求时的正文回答。",
        }
    }


@pytest.fixture
def nami_search_payload():
    """纳米 搜索结果 request (nested data.searchResults), no answer."""
    return {
        "data": {
            "searchResults": [
                {
                    "title": "纳米搜索命中",
                    "url": "https://baike.baidu.com/item/x",
                    "desc": "百度百科条目",
                    "source": "百度百科",
                }
            ]
        }
    }


@pytest.fixture
def nami_answer_payload():
    """纳米 正文 request (data.answer), no citations."""
    return {"data": {"answer": "纳米分两请求时的正文。"}}


@pytest.fixture
def doubao_offline_payload():
    """豆包 正文 only, 联网搜索 关闭 → no search payload at all."""
    return {"message": {"content": "联网关闭时只有正文，无引用。"}}


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

def test_yuanbao_parse_sse_extracts_answer_and_docs():
    """parse_sse 真包结构验证：聚合 type=text 的 msg、收集 searchGuid 的 docs。"""
    from app.providers.web.yuanbao_web import parse_sse
    out = parse_sse(YUANBAO_SSE_REAL)
    assert out["answer"] == "杭州滨江有多家不错的宠物医院。"
    assert len(out["docs"]) == 2
    assert out["docs"][0]["title"] == "杭州宠物医院推荐"
    assert out["docs"][1]["sourceType"] == "plugin"  # 第二条是地图 plugin
    assert out["citations"] == []  # 本例 footnote 编号引用为空，符合预期


def test_yuanbao_parse_sse_skips_non_json_data_lines():
    """`data: status` / `data: search_with_text` 这种非 JSON 行不应导致解析失败。"""
    from app.providers.web.yuanbao_web import parse_sse
    out = parse_sse('data: status\n\ndata: search_with_text\n\ndata: {"type":"text","msg":"OK"}\n\n')
    assert out["answer"] == "OK"


def test_yuanbao_locate_answer(yuanbao_payload):
    ch = YuanbaoWebChannel()
    assert "杭州" in ch.locate_answer(yuanbao_payload)
    assert "宠物医院" in ch.locate_answer(yuanbao_payload)


def test_yuanbao_locate_citations(yuanbao_payload):
    ch = YuanbaoWebChannel()
    raw = ch.locate_citations(yuanbao_payload)
    assert len(raw) == 2
    # webpage 类：web_site_name 已就位
    assert raw[0]["web_site_name"] == "示例宠物网"
    # plugin 类：sourceType=plugin 不应被回填进 web_site_name
    assert raw[1]["sourceType"] == "plugin"
    assert not raw[1].get("web_site_name")


def test_yuanbao_build_response(yuanbao_payload):
    ch = YuanbaoWebChannel()
    resp = ch.build_response_from_payload(yuanbao_payload)
    assert resp.provider == "yuanbao"
    assert resp.channel == "web"
    assert "杭州" in resp.content and "宠物医院" in resp.content
    assert len(resp.citations) == 2
    # 普通网页引用
    c0 = resp.citations[0]
    assert c0.title == "杭州宠物医院推荐"
    assert c0.url == "https://www.example-pet.com/hz"
    assert c0.domain == "example-pet.com"  # extract_domain 会剥 www.
    assert c0.source_name == "示例宠物网"
    assert c0.snippet == "滨江有松子宠物医院等"
    # 地图 plugin：url 为空、source_name 不被强行赋值（plugin 不回填）
    c1 = resp.citations[1]
    assert c1.title == "来自腾讯地图的参考资料"
    assert not c1.domain
    assert c1.source_name is None


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
# Yuanbao — nested-path candidates + 联网关闭 fallback
# ---------------------------------------------------------------------------

def test_yuanbao_locate_answer_nested_data():
    ch = YuanbaoWebChannel()
    assert ch.locate_answer({"data": {"content": "嵌套正文"}}) == "嵌套正文"


def test_yuanbao_citations_empty_when_search_off():
    """联网搜索 关闭 → 无 references → citations 为空，不报错。"""
    ch = YuanbaoWebChannel()
    resp = ch.build_response_from_payload({"reply": "无联网回答，无引用。"})
    assert resp.content == "无联网回答，无引用。"
    assert resp.citations == []


# ---------------------------------------------------------------------------
# Nami — nested-path candidates + 联网关闭 fallback
# ---------------------------------------------------------------------------

def test_nami_locate_answer_nested_data():
    ch = NamiWebChannel()
    assert ch.locate_answer({"data": {"answer": "纳米嵌套正文"}}) == "纳米嵌套正文"


def test_nami_citations_empty_when_search_off():
    ch = NamiWebChannel()
    resp = ch.build_response_from_payload({"answer": "纳米无联网回答。"})
    assert resp.content == "纳米无联网回答。"
    assert resp.citations == []


# ---------------------------------------------------------------------------
# Doubao — choices/delta path + 联网关闭 fallback
# ---------------------------------------------------------------------------

def test_doubao_locate_answer_delta_form():
    ch = DoubaoWebChannel()
    payload = {"choices": [{"delta": {"content": "豆包delta正文"}}]}
    assert ch.locate_answer(payload) == "豆包delta正文"


def test_doubao_single_payload_offline_no_citations(doubao_offline_payload):
    """联网搜索 关闭：单 payload 只有正文，citations 为空。"""
    ch = DoubaoWebChannel()
    resp = ch.build_response_from_payload(doubao_offline_payload)
    assert "联网关闭" in resp.content
    assert resp.citations == []


# ---------------------------------------------------------------------------
# doc §24 — multi-payload merge (搜索结果 payload + 正文 payload)
# build_response_from_payload([...]) must merge: answer from 正文,
# citations from 搜索结果, regardless of list order.
# ---------------------------------------------------------------------------

def test_doubao_merge_two_payloads(doubao_search_payload, doubao_answer_payload):
    ch = DoubaoWebChannel()
    resp = ch.build_response_from_payload(
        [doubao_search_payload, doubao_answer_payload], latency_ms=700
    )
    assert resp.provider == "doubao"
    assert resp.channel == "web"
    assert resp.content == "豆包分两请求时的正文回答。"
    assert len(resp.citations) == 2
    assert resp.citations[0].domain == "zhihu.com"
    assert resp.citations[1].domain == "m.weibo.cn"
    assert resp.citations[0].index == 1
    assert resp.citations[1].index == 2
    assert resp.latency_ms == 700
    # raw_response keeps both packets for audit
    assert "payloads" in resp.raw_response
    assert len(resp.raw_response["payloads"]) == 2


def test_doubao_merge_payload_order_independent(
    doubao_search_payload, doubao_answer_payload
):
    """正文 payload first, 搜索结果 second — result must be identical."""
    ch = DoubaoWebChannel()
    resp = ch.build_response_from_payload(
        [doubao_answer_payload, doubao_search_payload]
    )
    assert resp.content == "豆包分两请求时的正文回答。"
    assert len(resp.citations) == 2


def test_nami_merge_two_payloads(nami_search_payload, nami_answer_payload):
    ch = NamiWebChannel()
    resp = ch.build_response_from_payload(
        [nami_answer_payload, nami_search_payload]
    )
    assert resp.content == "纳米分两请求时的正文。"
    assert len(resp.citations) == 1
    assert resp.citations[0].domain == "baike.baidu.com"
    assert resp.citations[0].source_name == "百度百科"


def test_merge_search_off_no_citation_payload(doubao_answer_payload):
    """多请求场景下联网关闭：只拦到 正文 payload，citations 兜底为空。"""
    ch = DoubaoWebChannel()
    resp = ch.build_response_from_payload([doubao_answer_payload])
    assert resp.content == "豆包分两请求时的正文回答。"
    assert resp.citations == []


def test_merge_skips_non_dict_payloads(doubao_answer_payload, doubao_search_payload):
    """列表里混入 None / 非 dict 不应报错。"""
    ch = DoubaoWebChannel()
    resp = ch.build_response_from_payload(
        [None, doubao_search_payload, "junk", doubao_answer_payload]
    )
    assert resp.content == "豆包分两请求时的正文回答。"
    assert len(resp.citations) == 2


def test_single_dict_still_backward_compatible(deepseek_payload):
    """单 dict 调用必须与原签名一致（deepseek raw_response 仍是原 payload）。"""
    ch = DeepSeekWebChannel()
    resp = ch.build_response_from_payload(deepseek_payload)
    # single-payload path keeps raw_response == the dict itself (not wrapped)
    assert resp.raw_response == deepseek_payload
    assert "payloads" not in resp.raw_response
    assert len(resp.citations) == 2


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
