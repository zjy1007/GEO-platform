import uuid

from app.models.geo import GeoPrompt, GeoRun, ProviderResult
from app.models.merchant import Merchant, MerchantAlias
from app.providers.base import BaseChannel, ChannelHealth, LLMResponse
from app.services import mention_extraction_service as ms


class FakeChannel(BaseChannel):
    provider_name = "deepseek"
    channel = "api"

    def __init__(self, content: str) -> None:
        self._content = content

    async def chat(self, request) -> LLMResponse:
        return LLMResponse(provider="deepseek", channel="api", content=self._content, status="ok")

    async def health_check(self) -> ChannelHealth:
        return ChannelHealth(provider="deepseek", channel="api", healthy=True)


_PAYLOAD = (
    '{"is_mentioned":true,"matched_name":"杭州某某宠物医院","rank_position":1,'
    '"mention_text":"推荐杭州某某宠物医院","sentiment":"positive","confidence":0.9,'
    '"mentioned_brands":[{"brand":"杭州某某宠物医院","rank":1},{"brand":"竞品A","rank":2},{"brand":"竞品B","rank":3}]}'
)


async def test_extract_for_result_persists_and_dedupes(db_session):
    merchant = Merchant(
        tenant_id=uuid.uuid4(),
        name="抽取测试宠物医院",
        category="宠物医疗",
        city="杭州",
        district="滨江区",
        address="滨江区xx路",
        status="active",
    )
    db_session.add(merchant)
    await db_session.flush()
    db_session.add(MerchantAlias(merchant_id=merchant.id, alias="某某宠物医院", alias_type="x", confidence=0.9))
    prompt = GeoPrompt(merchant_id=merchant.id, mode="organic", phase="decision", prompt_text="杭州宠物医院推荐")
    db_session.add(prompt)
    run = GeoRun(
        merchant_id=merchant.id, run_type="organic_eval", status="completed",
        total_jobs=1, finished_jobs=1, failed_jobs=0,
    )
    db_session.add(run)
    await db_session.flush()
    pr = ProviderResult(
        run_id=run.id, prompt_id=prompt.id, provider="deepseek", channel="api",
        answer_text="推荐杭州某某宠物医院和竞品A、竞品B，口碑都不错。", status="ok",
    )
    db_session.add(pr)
    await db_session.commit()

    aliases = await ms.load_alias_names(db_session, merchant.id)
    assert "某某宠物医院" in aliases

    pending_before = await ms.pending_result_ids(db_session, run.id)
    assert pr.id in pending_before

    mr = await ms.extract_for_result(db_session, pr, merchant, aliases, FakeChannel(_PAYLOAD))
    await db_session.commit()

    assert mr.is_mentioned is True
    assert mr.rank_position == 1
    assert mr.sentiment == "positive"
    assert len(mr.mentioned_brands) == 3
    assert {b["brand"] for b in mr.mentioned_brands} == {"杭州某某宠物医院", "竞品A", "竞品B"}

    assert await ms.pending_result_ids(db_session, run.id) == []
    mentions = await ms.list_mentions(db_session, run.id)
    assert len(mentions) == 1

    await db_session.delete(merchant)
    await db_session.commit()
