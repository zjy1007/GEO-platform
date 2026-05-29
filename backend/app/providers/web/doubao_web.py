"""豆包联网版 web channel (P2.4).

Payload structure to be determined via DevTools packet capture against
doubao.com (web) with 联网搜索 enabled.

TODO(真抓包核实): capture a live session on doubao.com to confirm field paths
for answer text and citation list before enabling in production.

Note (doc §24): 豆包 splits 搜索结果 and 正文 into two separate requests, so BOTH
must be intercepted. Pass the two captured payloads as a list to
WebChannel.build_response_from_payload([搜索结果_payload, 正文_payload]) — the
base class merges them (answer from 正文, citations from 搜索结果) regardless of
order.

Note (方舟 API 兜底): 豆包 has no first-party 联网 API; the 方舟 (Volcengine Ark)
OpenAI-compatible API can only serve as an *analysis* fallback (no citations)
and requires a provisioned endpoint id (ep-xxxxxxxx) rather than a public model
name. The web channel here is the citation-bearing path; 方舟 is wired
separately under the api channel when an endpoint id is configured.
"""
from app.providers.base import LLMRequest, LLMResponse
from app.providers.web_base import WebChannel

# ---------------------------------------------------------------------------
# Field paths (single source of truth for packet-derived locations).
# 豆包 splits answer / search across two requests, so the answer paths target
# the 正文 payload and the citation paths target the 搜索结果 payload; both are
# resolved independently by the base-class multi-payload merge.
# ---------------------------------------------------------------------------
FIELD_PATHS = {
    # answer text candidate paths (正文 payload)
    "answer": [
        ("message", "content"),                 # TODO 真抓包核实: message.content
        ("data", "message", "content"),         # TODO 真抓包核实: data.message.content
        ("choices", 0, "delta", "content"),     # TODO 真抓包核实: SSE delta 形态
        ("choices", 0, "message", "content"),   # TODO 真抓包核实: choices.message.content
    ],
    # citation list candidate paths (搜索结果 payload)
    "citations": [
        ("references",),            # TODO 真抓包核实: 顶层 references
        ("search_results",),        # TODO 真抓包核实: 顶层 search_results
        ("data", "references"),     # TODO 真抓包核实: data.references
        ("data", "search_results"), # TODO 真抓包核实: data.search_results
    ],
}


def _walk(payload: dict, path: tuple) -> object:
    """Follow a key-chain through nested dicts/lists; return None on any miss.

    Integer keys index into lists (e.g. choices[0]); string keys index dicts.
    """
    cur: object = payload
    for key in path:
        if isinstance(key, int):
            if not isinstance(cur, list) or key >= len(cur):
                return None
            cur = cur[key]
        else:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(key)
    return cur


class DoubaoWebChannel(WebChannel):
    """豆包联网版 web channel."""

    provider_name = "doubao"

    # TODO 真抓包核实: update field_map after packet capture confirms citation keys
    field_map = {
        "title": "title",        # TODO 真抓包核实
        "url": "url",            # TODO 真抓包核实
        "snippet": "content",    # TODO 真抓包核实: 豆包引用摘要疑似放在 content
        "source_name": "source",  # TODO 真抓包核实
    }

    def locate_answer(self, payload: dict) -> str:
        """Extract answer text by walking FIELD_PATHS['answer'] candidates.

        When 豆包 splits requests, the 搜索结果 payload yields "" here and the
        base-class merge moves on to the 正文 payload.
        """
        for path in FIELD_PATHS["answer"]:
            val = _walk(payload, path)
            if isinstance(val, str) and val:
                return val
        return ""

    def locate_citations(self, payload: dict) -> list[dict]:
        """Extract raw citation list by walking FIELD_PATHS['citations'].

        Returns [] when 联网搜索 is off (no 搜索结果 payload) — intended
        "联网开关关闭 → citations 为空" fallback semantics.
        """
        for path in FIELD_PATHS["citations"]:
            val = _walk(payload, path)
            if isinstance(val, list):
                return val
        return []

    async def _drive_session(self, request: LLMRequest) -> LLMResponse:
        """Drive a Playwright session against doubao.com.

        TODO: implement after P2.4 packet capture confirms field paths.
        Note: 搜索结果 and 正文 arrive in separate requests; collect both and
        call build_response_from_payload([搜索结果_payload, 正文_payload]).
        """
        raise NotImplementedError(
            "DoubaoWebChannel._drive_session requires a real logged-in account. "
            "Implement after P2.4 packet capture confirms field paths."
        )
