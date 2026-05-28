"""Builds a Channel for a (provider, channel) pair from the registry.

P1.2 implements the api channel for openai_compatible providers. The web channel
(account pool, Playwright) lands in P2 and will plug in here without touching callers.
"""
from app.providers.base import BaseChannel
from app.providers.config import ProviderConfig, get_registry
from app.providers.openai_compatible import OpenAICompatibleChannel


def build_channel(provider_name: str, channel: str = "api") -> BaseChannel:
    cfg: ProviderConfig = get_registry().get(provider_name)

    if channel not in cfg.channels:
        raise ValueError(f"provider '{provider_name}' does not support channel '{channel}'")

    if channel == "api":
        if cfg.type != "openai_compatible":
            raise NotImplementedError(
                f"api channel for provider type '{cfg.type}' not implemented yet"
            )
        if not cfg.base_url:
            raise ValueError(f"provider '{provider_name}' missing base_url")
        return OpenAICompatibleChannel(
            provider_name=provider_name,
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            default_model=cfg.default_model,
            timeout_sec=cfg.timeout_sec,
        )

    if channel == "web":
        raise NotImplementedError("web channel (account pool) is implemented in P2")

    raise ValueError(f"unknown channel '{channel}'")
