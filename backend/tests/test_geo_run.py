import uuid

import pytest

from app.services.geo_run_service import build_jobs, validate_providers


def test_build_jobs_count_and_shape():
    rid, mid = uuid.uuid4(), uuid.uuid4()
    pids = [uuid.uuid4() for _ in range(3)]
    jobs = build_jobs(rid, mid, pids, ["deepseek", "qwen"], 2)
    assert len(jobs) == 3 * 2 * 2
    j = jobs[0]
    assert j["run_id"] == str(rid)
    assert j["merchant_id"] == str(mid)
    assert j["provider"] in {"deepseek", "qwen"}
    assert set(j.keys()) == {
        "run_id", "merchant_id", "prompt_id", "provider", "repeat_index", "channel"
    }


def test_build_jobs_defaults_channel_api():
    jobs = build_jobs(uuid.uuid4(), uuid.uuid4(), [uuid.uuid4()], ["deepseek"], 1)
    assert all(j["channel"] == "api" for j in jobs)


def test_build_jobs_web_channel_tagged():
    jobs = build_jobs(uuid.uuid4(), uuid.uuid4(), [uuid.uuid4()], ["deepseek"], 1, channel="web")
    assert all(j["channel"] == "web" for j in jobs)


def test_build_jobs_empty_prompts():
    assert build_jobs(uuid.uuid4(), uuid.uuid4(), [], ["deepseek"], 1) == []


def test_validate_providers_ok():
    validate_providers(["deepseek", "qwen"])  # should not raise


def test_validate_providers_unknown_raises():
    with pytest.raises(ValueError):
        validate_providers(["does-not-exist"])


def test_validate_providers_web_only_raises():
    with pytest.raises(ValueError):
        validate_providers(["yuanbao"])  # web-only, no api channel


def test_validate_providers_web_channel_ok():
    # yuanbao is web-only → valid on the web channel
    validate_providers(["yuanbao", "deepseek"], channel="web")  # should not raise


def test_validate_providers_api_only_on_web_raises():
    with pytest.raises(ValueError):
        validate_providers(["qwen"], channel="web")  # api-only, no web channel


def test_validate_providers_unknown_channel_raises():
    with pytest.raises(ValueError):
        validate_providers(["deepseek"], channel="bogus")
