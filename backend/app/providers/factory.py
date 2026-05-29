"""Builds a Channel for a (provider, channel) pair from the registry.

P1.2 implements the api channel for openai_compatible providers. P2.3 wires the
web channel (account pool, Playwright): each provider name maps to its concrete
WebChannel subclass below. Callers are unchanged — they still ask for (provider, channel).
"""
from app.providers.base import BaseChannel
from app.providers.config import ProviderConfig, get_registry
from app.providers.openai_compatible import OpenAICompatibleChannel
from app.providers.web import (
    DeepSeekWebChannel,
    DoubaoWebChannel,
    NamiWebChannel,
    YuanbaoWebChannel,
)

# provider name → WebChannel subclass (account-pool, P2.3).
_WEB_CHANNELS: dict[str, type[BaseChannel]] = {
    "deepseek": DeepSeekWebChannel,
    "yuanbao": YuanbaoWebChannel,
    "doubao": DoubaoWebChannel,
    "nami": NamiWebChannel,
}


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
        cls = _WEB_CHANNELS.get(provider_name)
        if cls is None:
            raise NotImplementedError(
                f"web channel for provider '{provider_name}' not implemented yet"
            )
        return cls()

    raise ValueError(f"unknown channel '{channel}'")
