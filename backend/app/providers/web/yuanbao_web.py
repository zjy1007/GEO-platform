"""腾讯元宝 web channel (P2.4).

Payload structure to be determined via DevTools packet capture against
yuanbao.tencent.com after P2.1 validates the overall approach.

TODO(真抓包核实): capture a live session on yuanbao.tencent.com to confirm
field paths for answer text and citation list before enabling in production.

All concrete field locations live in FIELD_PATHS below so they can be patched
in one place once a real packet is captured. Each entry lists the candidate
paths tried in order; every path is a placeholder until verified.
"""
from app.providers.base import LLMRequest, LLMResponse
from app.providers.web_base import WebChannel

# ---------------------------------------------------------------------------
# Field paths (single source of truth for packet-derived locations).
# Each value is an ordered list of candidate key chains; locate_* walks them
# and returns the first hit. Replace these once 抓包 confirms the real shape.
# ---------------------------------------------------------------------------
FIELD_PATHS = {
    # answer text candidate paths (each is a tuple of nested keys)
    "answer": [
        ("reply",),               # TODO 真抓包核实: 顶层 reply 字段
        ("data", "content"),      # TODO 真抓包核实: data.content 形态
        ("message", "content"),   # TODO 真抓包核实: message.content 兜底
    ],
    # citation list candidate paths
    "citations": [
        ("references",),          # TODO 真抓包核实: 顶层 references
        ("data", "references"),   # TODO 真抓包核实: data.references
        ("data", "docs"),         # TODO 真抓包核实: 元宝可能用 docs 命名
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


class YuanbaoWebChannel(WebChannel):
    """腾讯元宝联网版 web channel."""

    provider_name = "yuanbao"

    # TODO 真抓包核实: update field_map after packet capture confirms citation keys
    field_map = {
        "title": "title",        # TODO 真抓包核实
        "url": "url",            # TODO 真抓包核实
        "snippet": "abstract",   # TODO 真抓包核实
        "source_name": "sourceName",  # TODO 真抓包核实
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

        Returns [] when 联网搜索 is off (no references payload present) — this
        is the intended "联网开关关闭 → citations 为空" fallback semantics.
        """
        for path in FIELD_PATHS["citations"]:
            val = _walk(payload, path)
            if isinstance(val, list):
                return val
        return []

    async def _drive_session(self, request: LLMRequest) -> LLMResponse:
        """Drive a Playwright session against yuanbao.tencent.com.

        TODO: implement after P2.4 packet capture confirms field paths.
        """
        raise NotImplementedError(
            "YuanbaoWebChannel._drive_session requires a real logged-in account. "
            "Implement after P2.4 packet capture confirms field paths."
        )
