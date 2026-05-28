import uuid

from sqlalchemy import select

from app.models.geo import GeoRun, ProviderResult
from app.models.geo import GeoPrompt
from app.models.merchant import Merchant
from app.providers.base import BaseChannel, ChannelHealth, LLMResponse
from app.services import geo_run_service as rs
from app.workers import jobs as jobs_mod


class FakeChannel(BaseChannel):
    provider_name = "deepseek"
    channel = "api"

    def __init__(self, status: str = "ok") -> None:
        self._status = status

    async def chat(self, request) -> LLMResponse:
        ok = self._status == "ok"
        return LLMResponse(
            provider="deepseek",
            channel="api",
            model="fake-model",
            content="某某宠物医院口碑不错" if ok else "",
            status=self._status,
            error_message=None if ok else "no api key",
            prompt_tokens=5,
            completion_tokens=3,
            latency_ms=12,
        )

    async def health_check(self) -> ChannelHealth:
        return ChannelHealth(provider="deepseek", channel="api", healthy=True)


async def _seed(db_session, n: int = 2) -> Merchant:
    merchant = Merchant(
        tenant_id=uuid.uuid4(), name="队列测试医院", category="宠物医疗", city="杭州", status="active"
    )
    db_session.add(merchant)
    await db_session.flush()
    for i in range(n):
        db_session.add(
            GeoPrompt(
                merchant_id=merchant.id,
                mode="organic",
                phase="decision",
                prompt_text=f"杭州宠物医院问题{i}",
                city="杭州",
                category="宠物医疗",
            )
        )
    await db_session.commit()
    return merchant


async def test_run_completes_on_success(db_session, monkeypatch):
    merchant = await _seed(db_session, 2)
    run, jobs = await rs.create_run(
        db_session,
        merchant.id,
        run_type="organic_eval",
        providers=["deepseek"],
        prompt_count=None,
        repeat_count=1,
        modes=None,
        phases=None,
    )
    assert run.total_jobs == 2
    assert len(jobs) == 2

    monkeypatch.setattr(jobs_mod, "build_channel", lambda provider, channel="api": FakeChannel("ok"))
    for job in jobs:
        await jobs_mod.run_prompt_job({}, job)

    results = (
        await db_session.execute(select(ProviderResult).where(ProviderResult.run_id == run.id))
    ).scalars().all()
    assert len(results) == 2
    assert all(r.status == "ok" and r.answer_text for r in results)
    assert all(r.prompt_tokens == 5 for r in results)

    await db_session.refresh(run)
    assert run.finished_jobs == 2
    assert run.failed_jobs == 0
    assert run.status == "completed"
    assert run.finished_at is not None

    await db_session.delete(merchant)
    await db_session.commit()


async def test_run_partial_failed_on_errors(db_session, monkeypatch):
    merchant = await _seed(db_session, 2)
    run, jobs = await rs.create_run(
        db_session,
        merchant.id,
        run_type="organic_eval",
        providers=["deepseek"],
        prompt_count=None,
        repeat_count=1,
        modes=None,
        phases=None,
    )

    monkeypatch.setattr(jobs_mod, "build_channel", lambda provider, channel="api": FakeChannel("error"))
    for job in jobs:
        await jobs_mod.run_prompt_job({}, job)

    await db_session.refresh(run)
    assert run.finished_jobs == 2
    assert run.failed_jobs == 2
    assert run.status == "partial_failed"

    await db_session.delete(merchant)
    await db_session.commit()
