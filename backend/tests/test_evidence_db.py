import uuid

from app.models.merchant import Merchant
from app.services import evidence_service as es


async def _merchant(db_session) -> Merchant:
    m = Merchant(tenant_id=uuid.uuid4(), name="证据测试医院", category="宠物医疗", city="杭州", status="active")
    db_session.add(m)
    await db_session.flush()
    return m


async def test_add_text_source_and_dedupe(db_session):
    m = await _merchant(db_session)

    src, created = await es.add_source(
        db_session, m.id, source_type="official_website",
        title="服务项目", text="本店提供宠物疫苗、绝育手术、皮肤病诊疗。",
    )
    await db_session.commit()
    assert created is True
    assert src.trust_level == 0.95
    assert src.content_hash and len(src.content_hash) == 64
    assert "宠物疫苗" in src.content_text

    # same content (different whitespace) → dedupe, no new row
    src2, created2 = await es.add_source(
        db_session, m.id, source_type="official_website",
        text="  本店提供宠物疫苗、绝育手术、皮肤病诊疗。  ",
    )
    await db_session.commit()
    assert created2 is False
    assert src2.id == src.id

    rows = await es.list_sources(db_session, m.id)
    assert len(rows) == 1

    await db_session.delete(m)
    await db_session.commit()


async def test_add_source_requires_content(db_session):
    m = await _merchant(db_session)
    try:
        await es.add_source(db_session, m.id, source_type="other")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError when neither url nor text provided")
    await db_session.delete(m)
    await db_session.commit()
