"""Web (account-pool) channel base + citation parsing (P2).

Account-pool channels drive a real App/web session (Playwright) and intercept the
network response to pull two things (doc §24): ① answer text ② citation list.
The interception/locate logic is platform-specific and must be derived by capturing
a real packet first — so concrete platform channels (DeepSeekWebChannel, ...) are
added once we have a logged-in account to 抓包 against.

This module holds only the parts that are platform-agnostic and unit-testable:
the Citation parser and domain extraction. No Playwright import here, so importing
the app never requires browser deps.
"""
from abc import abstractmethod
from urllib.parse import urlparse

from app.providers.base import BaseChannel, Citation, LLMRequest, LLMResponse


def extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    netloc = urlparse(url).netloc.lower()
    if not netloc:
        # url without scheme, e.g. "www.example.com/x"
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

    Concrete subclasses implement chat() by:
      1. opening a session in a per-account Playwright profile,
      2. ensuring the platform's 联网搜索 toggle is ON (else citations are empty),
      3. injecting an init script that wraps fetch/EventSource to capture the
         streamed JSON, and
      4. locating the answer + citation list in that payload (platform-specific),
         then calling parse_citations() to normalize.
    """

    channel = "web"

    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse: ...
