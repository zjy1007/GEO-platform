"""Web (account-pool) channel base + citation parsing (P2).

Account-pool channels drive a real App/web session (Playwright) and intercept the
network response to pull two things (doc §24): ① answer text ② citation list.
The interception/locate logic is platform-specific and must be derived by capturing
a real packet first — so concrete platform channels (DeepSeekWebChannel, ...) are
added once we have a logged-in account to 抓包 against.

This module holds only the parts that are platform-agnostic and unit-testable:
the Citation parser, domain extraction, and the payload → LLMResponse bridge.
No Playwright import at module level so importing app never requires browser deps.
"""
import time
from abc import abstractmethod
from urllib.parse import urlparse

from app.providers.base import BaseChannel, ChannelHealth, Citation, LLMRequest, LLMResponse


def extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    netloc = urlparse(url).netloc.lower()
    if not netloc:
        netloc = urlparse("http://" + url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else (netloc or None)


def parse_citations(raw_items: list, field_map: dict | None = None) -> list[Citation]:
    """Normalize an already-located list of raw citation dicts into Citation objects.

    field_map remaps platform-specific keys, e.g. {"title": "name", "url": "link"}.
    domain is always derived from the resolved url.
    """
    fm = field_map or {}
    k_title = fm.get("title", "title")
    k_url = fm.get("url", "url")
    k_snippet = fm.get("snippet", "snippet")
    k_source = fm.get("source_name", "source_name")

    out: list[Citation] = []
    idx = 0
    for it in raw_items or []:
        if not isinstance(it, dict):
            continue
        url = it.get(k_url)
        idx += 1
        out.append(
            Citation(
                index=idx,
                title=(it.get(k_title) or None),
                url=url,
                domain=extract_domain(url),
                source_name=(it.get(k_source) or None),
                snippet=(it.get(k_snippet) or None),
            )
        )
    return out


class WebChannel(BaseChannel):
    """Account-pool channel. channel == 'web'; fills LLMResponse.citations.

    Concrete subclasses must implement:
      - locate_answer(payload)   — extract answer text from the captured JSON payload
      - locate_citations(payload) — extract raw citation list from the payload
      - _drive_session(request)  — Playwright session driver (lazy-imports playwright;
                                   calls build_response_from_payload internally)

    The locate_* methods are pure functions and are the unit-testable boundary.
    _drive_session is the only place that touches a real browser; it lazy-imports
    playwright so the rest of the app has no browser dependency.
    """

    channel = "web"

    # subclasses set these
    provider_name: str = ""
    field_map: dict = {}  # remap platform-specific citation keys

    @abstractmethod
    def locate_answer(self, payload: dict) -> str:
        """Extract the full answer text from a captured (decrypted) JSON payload."""
        ...

    @abstractmethod
    def locate_citations(self, payload: dict) -> list[dict]:
        """Extract the raw citation list from a captured JSON payload."""
        ...

    def build_response_from_payload(
        self,
        payload: dict,
        account_id: str | None = None,
        latency_ms: int = 0,
    ) -> LLMResponse:
        """Build a normalized LLMResponse from a captured payload dict.

        This is the pure, unit-testable bridge: locate_* + parse_citations.
        """
        answer = self.locate_answer(payload)
        raw_cits = self.locate_citations(payload)
        citations = parse_citations(raw_cits, self.field_map)
        return LLMResponse(
            provider=self.provider_name,
            channel="web",
            model=None,
            content=answer,
            citations=citations,
            raw_response=payload,
            latency_ms=latency_ms,
            status="ok",
        )

    @abstractmethod
    async def _drive_session(self, request: LLMRequest) -> LLMResponse:
        """Drive a Playwright browser session for the given request.

        Implementations must:
          1. Open a per-account Playwright profile (user_data_dir).
          2. Ensure the platform's 联网搜索 toggle is ON.
          3. Inject page.add_init_script to wrap fetch/EventSource and pipe chunks
             back via page.expose_function.
          4. Call build_response_from_payload with the accumulated payload.

        Playwright must be imported *inside* this method (lazy import) so that
        importing app.providers.web_base never requires browser deps.
        """
        ...

    async def chat(self, request: LLMRequest) -> LLMResponse:
        return await self._drive_session(request)

    async def health_check(self) -> ChannelHealth:
        # Web channel health is checked by verifying account pool status, not
        # by making a live request. Return unknown/healthy as placeholder.
        return ChannelHealth(
            provider=self.provider_name,
            channel="web",
            healthy=True,
            latency_ms=None,
            error=None,
        )
