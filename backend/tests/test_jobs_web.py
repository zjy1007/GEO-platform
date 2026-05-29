"""Unit tests for the web (account-pool) branch of run_prompt_job (task #4).

No real browser and no real DB: a fake AsyncSession records added rows and no-ops
flush/commit, the account pool + channel + counter-bump are monkeypatched. We assert
the lease lifecycle (pick_idle → reserve → release), citation persistence, the
no-idle-account retryable path, and failure classification (pause / need_relogin).
"""
import uuid

import pytest

from app.providers.base import Citation, LLMResponse
from app.workers import jobs


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeAccount:
    def __init__(self, status="active"):
        self.id = uuid.uuid4()
        self.status = status


class FakePrompt:
    def __init__(self, text="南京有哪些靠谱的医美机构？", phase="decision"):
        self.prompt_text = text
        self.phase = phase


class FakeSession:
    """Minimal AsyncSession stand-in: records added objects, no-ops persistence."""

    def __init__(self, prompt):
        self._prompt = prompt
        self.added = []

    async def get(self, model, pk):
        return self._prompt

    def add(self, obj):
        # Assign an id so store_citations / downstream code has a provider_result_id.
        if getattr(obj, "id", None) is None:
            try:
                obj.id = uuid.uuid4()
            except Exception:
                pass
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        pass


class FakePool:
    """Records pool lease/lifecycle calls and hands out a queue of accounts."""

    def __init__(self, accounts):
        self._accounts = list(accounts)
        self.calls = []

    async def pick_idle(self, session, provider):
        self.calls.append(("pick_idle", provider))
        return self._accounts.pop(0) if self._accounts else None

    async def reserve(self, session, account):
        self.calls.append(("reserve", account.id))
        return account

    async def release(self, session, account, *, success=True):
        self.calls.append(("release", account.id, success))

    async def pause(self, session, account, *args, **kwargs):
        self.calls.append(("pause", account.id))
        account.status = "paused"

    async def mark_need_relogin(self, session, account, *args, **kwargs):
        self.calls.append(("mark_need_relogin", account.id))
        account.status = "need_relogin"

    def next_human_delay(self, *a, **k):
        return 0.0


class FakeChannel:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc
        self.requests = []

    async def chat(self, request):
        self.requests.append(request)
        if self._exc is not None:
            raise self._exc
        return self._response


def _ok_response(citations=None):
    return LLMResponse(
        provider="deepseek",
        channel="web",
        content="南京某医美机构口碑良好。",
        citations=citations or [],
        raw_response={"message": {"content": "x"}},
        latency_ms=120,
        status="ok",
    )


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    async def _noop(_delay):
        return None

    monkeypatch.setattr(jobs.asyncio, "sleep", _noop)


class _FakeSessionCM:
    """async-context-manager so `async with SessionLocal() as session` yields our fake."""

    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc):
        return False


def _patch(monkeypatch, session, pool, channel):
    monkeypatch.setattr(jobs, "SessionLocal", lambda: _FakeSessionCM(session))
    monkeypatch.setattr(jobs, "pool_svc", pool)
    monkeypatch.setattr(jobs, "build_channel", lambda provider, ch: channel)
    bumps = []

    async def _fake_bump(session, run_id, ok):
        bumps.append(ok)

    monkeypatch.setattr(jobs, "_bump_and_maybe_finish", _fake_bump)
    return bumps


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_web_job_success_persists_result_and_citations(monkeypatch):
    prompt = FakePrompt()
    session = FakeSession(prompt)
    account = FakeAccount()
    pool = FakePool([account])
    cits = [Citation(index=1, title="南京医美榜", url="https://www.x.com/a", domain="x.com")]
    channel = FakeChannel(response=_ok_response(cits))
    bumps = _patch(monkeypatch, session, pool, channel)

    stored = []

    async def _fake_store(sess, pr_id, citations):
        stored.append((pr_id, list(citations)))
        return len(citations)

    monkeypatch.setattr(jobs.citation_svc, "store_citations", _fake_store)

    run_id = uuid.uuid4()
    job = {
        "run_id": str(run_id),
        "merchant_id": str(uuid.uuid4()),
        "prompt_id": str(uuid.uuid4()),
        "provider": "deepseek",
        "repeat_index": 0,
        "channel": "web",
    }
    res = await jobs.run_prompt_job({}, job)

    assert res["status"] == "ok"
    # Lease lifecycle: pick → reserve → release(success=True)
    assert ("pick_idle", "deepseek") in pool.calls
    assert ("reserve", account.id) in pool.calls
    assert ("release", account.id, True) in pool.calls
    # Persisted ProviderResult is web + carries account_id
    pr = session.added[0]
    assert pr.channel == "web"
    assert pr.account_id == account.id
    assert pr.provider == "deepseek"
    # Citations stored row-by-row
    assert stored and len(stored[0][1]) == 1
    # Counter bumped ok=True
    assert bumps == [True]
    # Request metadata carried account_id + phase
    assert channel.requests[0].metadata["account_id"] == str(account.id)
    assert channel.requests[0].metadata["phase"] == "decision"


async def test_web_job_no_idle_account_is_retryable(monkeypatch):
    session = FakeSession(FakePrompt())
    pool = FakePool([])  # no accounts available
    channel = FakeChannel(response=_ok_response())
    bumps = _patch(monkeypatch, session, pool, channel)

    job = {
        "run_id": str(uuid.uuid4()),
        "merchant_id": str(uuid.uuid4()),
        "prompt_id": str(uuid.uuid4()),
        "provider": "deepseek",
        "repeat_index": 0,
        "channel": "web",
    }
    res = await jobs.run_prompt_job({}, job)

    assert res["status"] == "retryable"
    # No ProviderResult persisted, counters untouched (so it can be re-run).
    assert session.added == []
    assert bumps == []


async def test_web_job_risk_failure_pauses_and_rotates(monkeypatch):
    session = FakeSession(FakePrompt())
    acc1, acc2 = FakeAccount(), FakeAccount()
    pool = FakePool([acc1, acc2])

    # First account raises a risk-control error, second would succeed; but our fake
    # channel is shared, so emulate: raise on first call, succeed on second.
    class RotatingChannel:
        def __init__(self):
            self.n = 0
            self.requests = []

        async def chat(self, request):
            self.requests.append(request)
            self.n += 1
            if self.n == 1:
                raise RuntimeError("触发风控 captcha detected")
            return _ok_response()

    channel = RotatingChannel()
    bumps = _patch(monkeypatch, session, pool, channel)
    monkeypatch.setattr(jobs.citation_svc, "store_citations", lambda *a, **k: None)

    job = {
        "run_id": str(uuid.uuid4()),
        "merchant_id": str(uuid.uuid4()),
        "prompt_id": str(uuid.uuid4()),
        "provider": "deepseek",
        "repeat_index": 0,
        "channel": "web",
    }
    res = await jobs.run_prompt_job({}, job)

    assert res["status"] == "ok"
    # First account paused + released(success=False); rotated to second.
    assert ("pause", acc1.id) in pool.calls
    assert ("release", acc1.id, False) in pool.calls
    assert ("release", acc2.id, True) in pool.calls
    assert bumps == [True]


async def test_web_job_login_failure_marks_need_relogin(monkeypatch):
    session = FakeSession(FakePrompt())
    acc1, acc2 = FakeAccount(), FakeAccount()
    pool = FakePool([acc1, acc2])

    class LoginExpiredOnce:
        def __init__(self):
            self.n = 0
            self.requests = []

        async def chat(self, request):
            self.requests.append(request)
            self.n += 1
            if self.n == 1:
                raise RuntimeError("登录状态已失效，请重新登录")
            return _ok_response()

    channel = LoginExpiredOnce()
    bumps = _patch(monkeypatch, session, pool, channel)
    monkeypatch.setattr(jobs.citation_svc, "store_citations", lambda *a, **k: None)

    job = {
        "run_id": str(uuid.uuid4()),
        "merchant_id": str(uuid.uuid4()),
        "prompt_id": str(uuid.uuid4()),
        "provider": "deepseek",
        "repeat_index": 0,
        "channel": "web",
    }
    res = await jobs.run_prompt_job({}, job)

    assert res["status"] == "ok"
    assert ("mark_need_relogin", acc1.id) in pool.calls
    assert ("release", acc1.id, False) in pool.calls


async def test_web_job_hard_error_persists_error_status(monkeypatch):
    session = FakeSession(FakePrompt())
    account = FakeAccount()
    pool = FakePool([account])
    channel = FakeChannel(exc=ValueError("unexpected parse failure"))
    bumps = _patch(monkeypatch, session, pool, channel)
    monkeypatch.setattr(jobs.citation_svc, "store_citations", lambda *a, **k: None)

    job = {
        "run_id": str(uuid.uuid4()),
        "merchant_id": str(uuid.uuid4()),
        "prompt_id": str(uuid.uuid4()),
        "provider": "deepseek",
        "repeat_index": 0,
        "channel": "web",
    }
    res = await jobs.run_prompt_job({}, job)

    assert res["status"] == "error"
    # Hard error: released(success=False), NOT paused/relogin, result persisted error.
    assert ("release", account.id, False) in pool.calls
    assert not any(c[0] in ("pause", "mark_need_relogin") for c in pool.calls)
    pr = session.added[0]
    assert pr.channel == "web"
    assert pr.status == "error"
    assert bumps == [False]


# ---------------------------------------------------------------------------
# Error classifier
# ---------------------------------------------------------------------------

def test_classify_web_error():
    assert jobs._classify_web_error(RuntimeError("captcha detected")) == "pause"
    assert jobs._classify_web_error(RuntimeError("触发风控")) == "pause"
    assert jobs._classify_web_error(RuntimeError("HTTP 429 too many requests")) == "pause"
    assert jobs._classify_web_error(RuntimeError("登录已过期")) == "relogin"
    assert jobs._classify_web_error(RuntimeError("storage_state missing")) == "relogin"
    assert jobs._classify_web_error(RuntimeError("random parse bug")) == "error"
