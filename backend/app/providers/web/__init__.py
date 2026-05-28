"""Web-channel platform implementations (account-pool, P2)."""
from app.providers.web.deepseek_web import DeepSeekWebChannel
from app.providers.web.doubao_web import DoubaoWebChannel
from app.providers.web.nami_web import NamiWebChannel
from app.providers.web.yuanbao_web import YuanbaoWebChannel

__all__ = [
    "DeepSeekWebChannel",
    "DoubaoWebChannel",
    "NamiWebChannel",
    "YuanbaoWebChannel",
]
