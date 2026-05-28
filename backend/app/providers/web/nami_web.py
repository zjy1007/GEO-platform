"""纳米AI web channel (P2.4).

Payload structure to be determined via DevTools packet capture against
nano.baidu.com (or current nami domain) with 联网搜索 enabled.

TODO(抓包核实): capture a live session to confirm field paths for answer
text and citation list before enabling in production.
"""
from app.providers.base import LLMRequest, LLMResponse
from app.providers.web_base import WebChannel


class NamiWebChannel(WebChannel):
    """纳米AI web channel."""

    provider_name = "nami"

    # TODO(抓包核实): update field_map after packet capture confirms citation keys
    field_map = {
        "title": "title",
        "url": "url",
        "snippet": "desc",
        "source_name": "source",
    }

    def locate_answer(self, payload: dict) -> str:
        """Extract answer text from the Nami SSE payload.

        Suspected structure (TODO: verify via packet capture):
          {"answer": "..."} or {"data": {"answer": "..."}}
        """
        if "answer" in payload:
            return payload["answer"] or ""
        data = payload.get("data") or {}
        return data.get("answer") or ""

    def locate_citations(self, payload: dict) -> list[dict]:
        """Extract raw citation list from the Nami SSE payload.

        Suspected structure (TODO: verify via packet capture):
          {"citations": [...]} or {"data": {"citations": [...]}}
        """
        if "citations" in payload:
            return payload["citations"] or []
        data = payload.get("data") or {}
        return data.get("citations") or []

    async def _drive_session(self, request: LLMRequest) -> LLMResponse:
        """Drive a Playwright session against the Nami AI web interface.

        TODO: implement after P2.4 packet capture confirms field paths.
        """
        raise NotImplementedError(
            "NamiWebChannel._drive_session requires a real logged-in account. "
            "Implement after P2.4 packet capture confirms field paths."
        )
