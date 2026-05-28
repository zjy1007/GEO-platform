import uuid

import pytest
from sqlalchemy import select

from app.models.geo import GeoPrompt
from app.models.merchant import Merchant
from app.providers.base import BaseChannel, ChannelHealth, LLMResponse
from app.services import prompt_generation_service as ps


class FakeChannel(BaseChannel):
    provider_name = "deepseek"
    channel = "api"

    def __init__(self, content: str, status: str = "ok") -> None:
        self._content = content
        self._status = status

    async def chat(self, request) -> LLMResponse:
        return LLMResponse(
            provider="deepseek",
            channel="api",
            content=self._content,
            status=self._status,
            error_message=None if self._status == "ok" else "no api key",
        )

    async def health_check(self) -> ChannelHealth:
        return ChannelHealth(provider="deepseek", channel="api", healthy=True)


async def test_generate_and_store_persists_tagged_prompts(db_session):
    merchant = Merchant(
        tenant_id=uuid.uuid4(),
        name="集成测试宠物医院",
        category="宠物医疗",
        city="杭州",
        district="滨江区",
        services=["疫苗"],
        status="active",
    )
    db_session.add(merchant)
    await db_session.flush()

    fake = FakeChannel(
        '[{"question":"杭州滨江哪家宠物医院好?","scenario_type":"category_recommendation","intent":"recommend"}]'
    )
    prompts = await ps.generate_and_store(
        db_session, merchant, count=2, modes=["organic"], phases=["decision", "doubt"], channel=fake
    )

    assert len(prompts) == 2
    assert {p.phase for p in prompts} == {"decision", "doubt"}
    assert all(p.mode == "organic" for p in prompts)

    rows = (
        await db_session.execute(select(GeoPrompt).where(GeoPrompt.merchant_id == merchant.id))
    ).scalars().all()
    assert len(rows) == 2

    await db_session.delete(merchant)
    await db_session.commit()


async def test_generate_raises_when_channel_errors(db_session):
    merchant = Merchant(
        tenant_id=uuid.uuid4(), name="错误用例商家", category="宠物医疗", city="杭州", status="active"
    )
    db_session.add(merchant)
    await db_session.flush()

    err_channel = FakeChannel("", status="error")
    with pytest.raises(RuntimeError):
        await ps.generate_and_store(
            db_session, merchant, count=2, modes=["organic"], phases=["decision"], channel=err_channel
        )

    await db_session.delete(merchant)
    await db_session.commit()
