import httpx
import pytest

from app.providers.base import LLMRequest
from app.providers.json_utils import repair_json
from app.providers.openai_compatible import OpenAICompatibleChannel

_OK_BODY = {
    "model": "test-model",
    "choices": [{"message": {"content": "你好"}}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 2},
}


def _channel(handler, max_retries: int = 2) -> tuple[OpenAICompatibleChannel, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    ch = OpenAICompatibleChannel(
        provider_name="deepseek",
        base_url="https://api.deepseek.com",
        api_key="k",
        default_model="test-model",
        max_retries=max_retries,
        client=client,
    )
    return ch, client


def _req() -> LLMRequest:
    return LLMRequest(provider="deepseek", messages=[{"role": "user", "content": "hi"}])


async def test_chat_success_parses_content_and_tokens():
    ch, client = _channel(lambda r: httpx.Response(200, json=_OK_BODY))
    resp = await ch.chat(_req())
    await client.aclose()
    assert resp.status == "ok"
    assert resp.content == "你好"
    assert resp.prompt_tokens == 5
    assert resp.completion_tokens == 2
    assert resp.channel == "api"


async def test_chat_retries_on_5xx_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500)
        return httpx.Response(200, json=_OK_BODY)

    ch, client = _channel(handler, max_retries=2)
    resp = await ch.chat(_req())
    await client.aclose()
    assert resp.status == "ok"
    assert calls["n"] == 2


async def test_chat_does_not_retry_on_4xx():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": "bad"})

    ch, client = _channel(handler, max_retries=2)
    resp = await ch.chat(_req())
    await client.aclose()
    assert resp.status == "error"
    assert calls["n"] == 1  # 400 is non-retryable


async def test_chat_persistent_5xx_returns_error_after_retries():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    ch, client = _channel(handler, max_retries=1)
    resp = await ch.chat(_req())
    await client.aclose()
    assert resp.status == "error"
    assert calls["n"] == 2  # initial + 1 retry


# --- json repair ---

@pytest.mark.parametrize(
    "raw,expected",
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ('结果如下：{"a": [1, 2]} 完毕', {"a": [1, 2]}),
        ("[1, 2, 3]", [1, 2, 3]),
        ('{"s": "has } brace in string"}', {"s": "has } brace in string"}),
    ],
)
def test_repair_json_ok(raw, expected):
    assert repair_json(raw) == expected


def test_repair_json_raises_when_no_json():
    with pytest.raises(ValueError):
        repair_json("no json here")
