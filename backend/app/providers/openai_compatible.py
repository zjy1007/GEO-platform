import time

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.providers.base import BaseChannel, ChannelHealth, LLMRequest, LLMResponse


class RetryableError(Exception):
    """Transient failure (timeout / connection / 429 / 5xx) — safe to retry."""


class OpenAICompatibleChannel(BaseChannel):
    """API channel for OpenAI-compatible vendors (DeepSeek / 通义 / 智谱 / Kimi).

    Covers timeout, bounded retry with exponential backoff, token accounting and
    raw-response capture. Errors are returned as a status='error' LLMResponse rather
    than raised, so a single failed job never crashes a whole run.
    """

    channel = "api"

    def __init__(
        self,
        provider_name: str,
        base_url: str,
        api_key: str | None,
        default_model: str | None = None,
        timeout_sec: int = 60,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self._client = client

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _post_once(self, payload: dict) -> dict:
        url = f"{self.base_url}/chat/completions"
        try:
            if self._client is not None:
                resp = await self._client.post(
                    url, json=payload, headers=self._headers(), timeout=self.timeout_sec
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                    resp = await client.post(url, json=payload, headers=self._headers())
        except (httpx.TimeoutException, httpx.TransportError) as e:
            raise RetryableError(f"transport error: {e}") from e

        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            raise RetryableError(f"HTTP {resp.status_code}")
        resp.raise_for_status()  # other 4xx -> non-retryable
        return resp.json()

    async def _post_with_retry(self, payload: dict) -> dict:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.max_retries + 1),
            wait=wait_exponential(multiplier=0.5, max=8),
            retry=retry_if_exception_type(RetryableError),
            reraise=True,
        ):
            with attempt:
                return await self._post_once(payload)
        raise RuntimeError("unreachable")

    async def chat(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        payload = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        if request.tools:
            payload["tools"] = request.tools

        start = time.perf_counter()
        try:
            data = await self._post_with_retry(payload)
        except Exception as e:  # noqa: BLE001 — surface as error response, don't crash the run
            return LLMResponse(
                provider=self.provider_name,
                channel=self.channel,
                model=model,
                content="",
                status="error",
                error_message=str(e),
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        elapsed = int((time.perf_counter() - start) * 1000)
        choices = data.get("choices") or [{}]
        content = (choices[0].get("message") or {}).get("content") or ""
        usage = data.get("usage") or {}
        return LLMResponse(
            provider=self.provider_name,
            channel=self.channel,
            model=data.get("model", model),
            content=content,
            raw_response=data,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            latency_ms=elapsed,
            status="ok",
        )

    async def health_check(self) -> ChannelHealth:
        start = time.perf_counter()
        resp = await self.chat(
            LLMRequest(
                provider=self.provider_name,
                channel=self.channel,
                model=self.default_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
        )
        latency = int((time.perf_counter() - start) * 1000)
        return ChannelHealth(
            provider=self.provider_name,
            channel=self.channel,
            healthy=resp.status == "ok",
            latency_ms=latency,
            error=resp.error_message,
        )
