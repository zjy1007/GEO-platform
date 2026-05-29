"""纳米AI web channel (P2.4).

Payload structure to be determined via DevTools packet capture against
the 纳米AI（360 搜索 App）web/App interface with 联网搜索 enabled.

TODO(真抓包核实): capture a live session to confirm field paths for answer
text and citation list before enabling in production.

All concrete field locations live in FIELD_PATHS below so they can be patched
in one place once a real packet is captured. Each entry lists the candidate
paths tried in order; every path is a placeholder until verified.

Note (doc §24): 纳米AI may also split 搜索结果 and 正文 into two requests; both
are intercepted and merged via WebChannel.build_response_from_payload([...]).
"""
from app.providers.base import LLMRequest, LLMResponse
from app.providers.web_base import WebChannel

# ---------------------------------------------------------------------------
# Field paths (single source of truth for packet-derived locations).
# ---------------------------------------------------------------------------
FIELD_PATHS = {
    "answer": [
        ("answer",),             # TODO 真抓包核实: 顶层 answer
        ("data", "answer"),      # TODO 真抓包核实: data.answer
        ("data", "content"),     # TODO 真抓包核实: data.content 兜底
    ],
    "citations": [
        ("citations",),          # TODO 真抓包核实: 顶层 citations
        ("data", "citations"),   # TODO 真抓包核实: data.citations
        ("data", "searchResults"),  # TODO 真抓包核实: 360 系常用 searchResults
    ],
}


def _walk(payload: dict, path: tuple) -> object:
    """Follow a tuple key-chain through nested dicts; return None on any miss."""
    cur: object = payload
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


class NamiWebChannel(WebChannel):
    """纳米AI web channel."""

    provider_name = "nami"

    # TODO 真抓包核实: update field_map after packet capture confirms citation keys
    field_map = {
        "title": "title",       # TODO 真抓包核实
        "url": "url",           # TODO 真抓包核实
        "snippet": "desc",      # TODO 真抓包核实
        "source_name": "source",  # TODO 真抓包核实
    }

    def locate_answer(self, payload: dict) -> str:
        """Extract answer text by walking FIELD_PATHS['answer'] candidates."""
        for path in FIELD_PATHS["answer"]:
            val = _walk(payload, path)
            if isinstance(val, str) and val:
                return val
        return ""

    def locate_citations(self, payload: dict) -> list[dict]:
        """Extract raw citation list by walking FIELD_PATHS['citations'].

        Returns [] when 联网搜索 is off — intended "联网开关关闭 → citations 为空"
        fallback semantics.
        """
        for path in FIELD_PATHS["citations"]:
            val = _walk(payload, path)
            if isinstance(val, list):
                return val
        return []

    async def _drive_session(self, request: LLMRequest) -> LLMResponse:
        """Drive a Playwright session against the Nami AI web interface.

        TODO: implement after P2.4 packet capture confirms field paths.
        """
        raise NotImplementedError(
            "NamiWebChannel._drive_session requires a real logged-in account. "
            "Implement after P2.4 packet capture confirms field paths."
        )
