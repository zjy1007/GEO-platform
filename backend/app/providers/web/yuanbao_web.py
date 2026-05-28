"""腾讯元宝 web channel (P2.4).

Payload structure to be determined via DevTools packet capture against
yuanbao.tencent.com after P2.1 validates the overall approach.

TODO(抓包核实): capture a live session on yuanbao.tencent.com to confirm
field paths for answer text and citation list before enabling in production.
"""
from app.providers.base import LLMRequest, LLMResponse
from app.providers.web_base import WebChannel


class YuanbaoWebChannel(WebChannel):
    """腾讯元宝联网版 web channel."""

    provider_name = "yuanbao"

    # TODO(抓包核实): update field_map after packet capture confirms citation keys
    field_map = {
        "title": "title",
        "url": "url",
        "snippet": "abstract",
        "source_name": "sourceName",
    }

    def locate_answer(self, payload: dict) -> str:
        """Extract answer text from the Yuanbao SSE payload.

        Suspected structure (TODO: verify via packet capture):
          {"reply": "..."} or {"data": {"content": "..."}}
        """
        if "reply" in payload:
            return payload["reply"] or ""
        data = payload.get("data") or {}
        return data.get("content") or ""

    def locate_citations(self, payload: dict) -> list[dict]:
        """Extract raw citation list from the Yuanbao SSE payload.

        Suspected structure (TODO: verify via packet capture):
          {"references": [...]} or {"data": {"references": [...]}}
        """
        if "references" in payload:
            return payload["references"] or []
        data = payload.get("data") or {}
        return data.get("references") or []

    async def _drive_session(self, request: LLMRequest) -> LLMResponse:
        """Drive a Playwright session against yuanbao.tencent.com.

        TODO: implement after P2.4 packet capture confirms field paths.
        """
        raise NotImplementedError(
            "YuanbaoWebChannel._drive_session requires a real logged-in account. "
            "Implement after P2.4 packet capture confirms field paths."
        )
