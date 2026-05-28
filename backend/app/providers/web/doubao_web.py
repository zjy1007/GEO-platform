"""豆包联网版 web channel (P2.4).

Payload structure to be determined via DevTools packet capture against
doubao.com (web) with 联网搜索 enabled.

TODO(抓包核实): capture a live session on doubao.com to confirm field paths
for answer text and citation list before enabling in production.
Note: Doubao may split search results and main answer into two separate
requests -- both must be intercepted if so (doc P2.4).
"""
from app.providers.base import LLMRequest, LLMResponse
from app.providers.web_base import WebChannel


class DoubaoWebChannel(WebChannel):
    """豆包联网版 web channel."""

    provider_name = "doubao"

    # TODO(抓包核实): update field_map after packet capture confirms citation keys
    field_map = {
        "title": "title",
        "url": "url",
        "snippet": "content",
        "source_name": "source",
    }

    def locate_answer(self, payload: dict) -> str:
        """Extract answer text from the Doubao SSE payload.

        Suspected structure (TODO: verify via packet capture):
          {"message": {"content": "..."}} or {"choices": [{"delta": {"content": "..."}}]}
        """
        msg = payload.get("message") or {}
        if msg.get("content"):
            return msg["content"]
        choices = payload.get("choices") or []
        if choices:
            delta = choices[0].get("delta") or choices[0].get("message") or {}
            return delta.get("content") or ""
        return ""

    def locate_citations(self, payload: dict) -> list[dict]:
        """Extract raw citation list from the Doubao SSE payload.

        Suspected structure (TODO: verify via packet capture):
          {"references": [...]} or {"search_results": [...]}
        Note: may be in a separate search-phase response (intercept both).
        """
        if "references" in payload:
            return payload["references"] or []
        return payload.get("search_results") or []

    async def _drive_session(self, request: LLMRequest) -> LLMResponse:
        """Drive a Playwright session against doubao.com.

        TODO: implement after P2.4 packet capture confirms field paths.
        Note: if search results come from a separate request, merge them
        before calling build_response_from_payload.
        """
        raise NotImplementedError(
            "DoubaoWebChannel._drive_session requires a real logged-in account. "
            "Implement after P2.4 packet capture confirms field paths."
        )
