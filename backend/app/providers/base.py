"""Unified channel abstraction (doc §6).

Business code never calls DeepSeek/Doubao/Kimi directly — it always goes through
a Channel that returns a uniform LLMResponse. The only difference between channels
is response.channel ("api" | "web") and whether citations are populated
(web channel fills them; api channel usually leaves them empty).
"""
from abc import ABC, abstractmethod

from pydantic import BaseModel


class Citation(BaseModel):
    index: int                       # 引用角标序号
    title: str | None = None         # 引用文章标题（"GEO 大模型优化建议"取标题）
    url: str | None = None
    domain: str | None = None        # 用于"引用源排行榜"按域名聚合
    source_name: str | None = None
    snippet: str | None = None


class LLMRequest(BaseModel):
    provider: str
    channel: str = "api"             # "api" | "web"
    model: str | None = None         # web 渠道可能没有模型名
    messages: list[dict]
    temperature: float = 0.2
    max_tokens: int = 2048
    stream: bool = False
    web_search: bool = True          # web 渠道必须开启联网搜索才有引用源
    tools: list[dict] | None = None
    metadata: dict = {}              # 可带 account_id / phase 等


class LLMResponse(BaseModel):
    provider: str
    channel: str                     # "api" | "web"
    model: str | None = None
    content: str
    citations: list[Citation] = []   # web 渠道填充，api 渠道通常为空
    raw_response: dict = {}
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int = 0
    status: str = "ok"               # ok | error
    error_message: str | None = None


class ChannelHealth(BaseModel):
    provider: str
    channel: str
    healthy: bool
    latency_ms: int | None = None
    error: str | None = None


class BaseChannel(ABC):
    provider_name: str
    channel: str                     # "api" | "web"

    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def health_check(self) -> ChannelHealth: ...
