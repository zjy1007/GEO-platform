"""Loads the provider registry from YAML.

P0 only loads and validates the config; the actual Channel implementations
(OpenAICompatibleChannel / WebChannel) are built in P1.2 and P2.
"""
import os
from functools import lru_cache

import yaml
from pydantic import BaseModel

from app.core.config import settings


class ProviderConfig(BaseModel):
    name: str
    type: str
    channels: list[str] = ["api"]
    base_url: str | None = None
    api_key_env: str | None = None
    default_model: str | None = None
    timeout_sec: int = 60
    max_concurrency: int = 5
    qps: float = 2
    note: str | None = None

    @property
    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env) if self.api_key_env else None


class ProviderRegistry(BaseModel):
    providers: dict[str, ProviderConfig]
    account_quota: dict[str, dict] = {}

    def get(self, name: str) -> ProviderConfig:
        return self.providers[name]

    def with_api_channel(self) -> list[str]:
        return [n for n, p in self.providers.items() if "api" in p.channels]

    def with_web_channel(self) -> list[str]:
        return [n for n, p in self.providers.items() if "web" in p.channels]


@lru_cache
def get_registry() -> ProviderRegistry:
    with open(settings.providers_config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    providers = {
        name: ProviderConfig(name=name, **cfg) for name, cfg in raw.get("providers", {}).items()
    }
    return ProviderRegistry(providers=providers, account_quota=raw.get("account_quota", {}))
