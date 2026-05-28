"""Per-provider rate limiting for the worker (doc §14: 每个平台单独限流).

Single-worker model: an asyncio.Semaphore bounds concurrency per provider and a
per-provider min-interval gate enforces qps. Both come from providers.yaml.
(Cross-process limiting via a Redis token bucket is a P5 concern when we scale to
multiple worker processes.)
"""
import asyncio
import time

from app.providers.config import get_registry


class ProviderRateLimiter:
    def __init__(self) -> None:
        self._sems: dict[str, asyncio.Semaphore] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._last: dict[str, float] = {}

    def semaphore(self, provider: str) -> asyncio.Semaphore:
        if provider not in self._sems:
            max_conc = get_registry().get(provider).max_concurrency
            self._sems[provider] = asyncio.Semaphore(max_conc)
        return self._sems[provider]

    async def throttle_qps(self, provider: str) -> None:
        qps = get_registry().get(provider).qps or 0
        if qps <= 0:
            return
        min_interval = 1.0 / qps
        lock = self._locks.setdefault(provider, asyncio.Lock())
        async with lock:
            wait = min_interval - (time.monotonic() - self._last.get(provider, 0.0))
            if wait > 0:
                await asyncio.sleep(wait)
            self._last[provider] = time.monotonic()


limiter = ProviderRateLimiter()
