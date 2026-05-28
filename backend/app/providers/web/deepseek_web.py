"""DeepSeek web channel (P2.1 minimum validation target).

Payload structure determined from DevTools packet capture against
DeepSeek 联网版 (chat.deepseek.com). The streamed response is SSE with
JSON chunks; the final "done" event carries the complete response object.

TODO(抓包核实): verify exact field paths against a live session before
enabling in production.
"""
from app.providers.base import LLMRequest, LLMResponse
from app.providers.web_base import WebChannel


class DeepSeekWebChannel(WebChannel):
    """DeepSeek 联网版 web channel — P2.1 primary validation target."""

    provider_name = "deepseek"

    # DeepSeek SSE uses these citation field names (TODO: verify via packet capture)
    field_map = {
        "title": "title",
        "url": "url",
        "snippet": "snippet",
        "source_name": "siteName",
    }

    def locate_answer(self, payload: dict) -> str:
        """Extract answer text from the accumulated SSE payload.

        DeepSeek SSE final chunk structure (TODO: verify field path):
          {"choices": [{"delta": {"content": "..."}}]}
        or the complete-message form:
          {"message": {"content": "..."}}
        """
        # Complete-message form (preferred when available)
        msg = payload.get("message") or {}
        if msg.get("content"):
            return msg["content"]
        # Delta-accumulation form
        choices = payload.get("choices") or []
        if choices:
            delta = choices[0].get("delta") or choices[0].get("message") or {}
            return delta.get("content") or ""
        return ""

    def locate_citations(self, payload: dict) -> list[dict]:
        """Extract raw citation list from the accumulated SSE payload.

        DeepSeek attaches search results under (TODO: verify field path):
          {"search_results": [{"title": ..., "url": ..., "snippet": ..., "siteName": ...}]}
        or nested inside the message:
          {"message": {"search_results": [...]}}
        """
        # Top-level key
        if "search_results" in payload:
            return payload["search_results"] or []
        # Nested in message
        msg = payload.get("message") or {}
        return msg.get("search_results") or []

    async def _drive_session(self, request: LLMRequest) -> LLMResponse:
        """Drive a Playwright session against chat.deepseek.com.

        Lazy-imports playwright so app import never requires browser deps.
        Requires a saved storage_state or user_data_dir for the account
        specified in request.metadata["account_id"].

        TODO: implement after P2.1 手工抓包 confirms field paths.
        """
        raise NotImplementedError(
            "DeepSeekWebChannel._drive_session requires a real logged-in account. "
            "Implement after P2.1 packet capture confirms field paths."
        )
