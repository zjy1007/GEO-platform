import uuid

from app.models.geo import GeoPrompt, GeoRun, MentionResult, ProviderResult
from app.models.merchant import Merchant, MerchantAlias
from app.services import geo_scoring_service as scoring
from app.services import mention_extraction_service as mention_svc
from app.services.report_service import render_html


async def test_compute_and_store_produces_report_and_html(db_session):
    merchant = Merchant(
        tenant_id=uuid.uuid4(), name="报告测试医院", category="宠物医疗", city="杭州",
        district="滨江区", address="滨江区x路", status="active",
    )
    db_session.add(merchant)
    await db_session.flush()
    db_session.add(MerchantAlias(merchant_id=merchant.id, alias="报告测试医院", confidence=1.0))

    run = GeoRun(merchant_id=merchant.id, run_type="organic_eval", status="completed",
                 total_jobs=2, finished_jobs=2, failed_jobs=0)
    db_session.add(run)
    pd = GeoPrompt(merchant_id=merchant.id, mode="organic", phase="decision", prompt_text="哪家好")
    pq = GeoPrompt(merchant_id=merchant.id, mode="organic", phase="doubt", prompt_text="哪家差")
    db_session.add_all([pd, pq])
    await db_session.flush()

    pr1 = ProviderResult(run_id=run.id, prompt_id=pd.id, provider="deepseek", channel="api",
                         answer_text="推荐报告测试医院", status="ok")
    pr2 = ProviderResult(run_id=run.id, prompt_id=pq.id, provider="qwen", channel="api",
                         answer_text="某些机构口碑差", status="ok")
    db_session.add_all([pr1, pr2])
    await db_session.flush()

    db_session.add(MentionResult(
        provider_result_id=pr1.id, merchant_id=merchant.id, is_mentioned=True, rank_position=1,
        sentiment="positive", confidence=0.9,
        mentioned_brands=[{"brand": "报告测试医院", "rank": 1}, {"brand": "竞品A", "rank": 2}],
    ))
    db_session.add(MentionResult(
        provider_result_id=pr2.id, merchant_id=merchant.id, is_mentioned=False, rank_position=None,
        sentiment=None, confidence=None, mentioned_brands=[{"brand": "竞品B", "rank": 1}],
    ))
    await db_session.commit()

    aliases = await mention_svc.load_alias_names(db_session, merchant.id)
    report = await scoring.compute_and_store(db_session, run, merchant, aliases)

    assert report.geo_score is not None and 0 <= report.geo_score <= 100
    rj = report.report_json
    assert rj["overall"]["total"] == 2
    assert rj["overall"]["mentioned"] == 1
    assert set(rj["by_phase"].keys()) == {"decision", "doubt"}
    # target marked, competitor present
    brands = {c["brand"]: c for c in rj["competitors"]}
    assert brands["报告测试医院"]["is_target"] is True
    assert "竞品A" in brands

    html = render_html(rj)
    assert "报告测试医院" in html
    assert str(report.geo_score) in html

    await db_session.delete(merchant)
    await db_session.commit()
