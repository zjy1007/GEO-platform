import uuid

from app.models.evidence import EvidenceSource
from app.models.geo import GeoPrompt, GeoRun, ProviderResult
from app.models.merchant import Merchant
from app.providers.base import BaseChannel, ChannelHealth, LLMResponse
from app.services import evidence_verification_service as vs


class ScriptedChannel(BaseChannel):
    """Returns queued responses in order (split call, then verify call(s))."""

    provider_name = "deepseek"
    channel = "api"

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    async def chat(self, request) -> LLMResponse:
        content = self._responses.pop(0) if self._responses else "{}"
        return LLMResponse(provider="deepseek", channel="api", content=content, status="ok")

    async def health_check(self) -> ChannelHealth:
        return ChannelHealth(provider="deepseek", channel="api", healthy=True)


async def test_verify_answer_persists_and_rate(db_session):
    merchant = Merchant(tenant_id=uuid.uuid4(), name="核查测试医院", category="宠物医疗", city="杭州", status="active")
    db_session.add(merchant)
    await db_session.flush()
    db_session.add(EvidenceSource(
        merchant_id=merchant.id, source_type="official_website",
        content_text="本店提供宠物疫苗、绝育手术、皮肤病诊疗，营业时间 09:00-21:00。",
        trust_level=0.95, content_hash="h1",
    ))
    run = GeoRun(merchant_id=merchant.id, run_type="organic_eval", status="completed",
                 total_jobs=1, finished_jobs=1, failed_jobs=0)
    prompt = GeoPrompt(merchant_id=merchant.id, mode="organic", phase="decision", prompt_text="q")
    db_session.add_all([run, prompt])
    await db_session.flush()
    pr = ProviderResult(run_id=run.id, prompt_id=prompt.id, provider="deepseek", channel="api",
                        answer_text="核查测试医院提供宠物疫苗，营业到晚上9点。", status="ok")
    db_session.add(pr)
    await db_session.flush()

    from app.services import evidence_service as es
    evidences = await es.list_sources(db_session, merchant.id)

    # split → 2 claims; verify → supported, supported
    channel = ScriptedChannel([
        '[{"claim":"提供宠物疫苗","claim_type":"service"},{"claim":"营业到晚上9点","claim_type":"hours"}]',
        '{"status":"supported","confidence":0.9,"reason":"证据明确提到疫苗"}',
        '{"status":"supported","confidence":0.8,"reason":"营业时间到21:00"}',
    ])
    results = await vs.verify_answer(db_session, pr, merchant, evidences, channel)
    await db_session.commit()

    assert len(results) == 2
    assert all(r.verification_status == "supported" for r in results)

    statuses = await vs.fetch_run_verification_statuses(db_session, run.id)
    assert vs.compute_evidence_rate(statuses) == 1.0

    await db_session.delete(merchant)
    await db_session.commit()
