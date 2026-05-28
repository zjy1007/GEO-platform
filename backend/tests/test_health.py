from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "X-Trace-Id" in resp.headers


def test_provider_registry_loads():
    from app.providers.config import get_registry

    reg = get_registry()
    assert "deepseek" in reg.providers
    assert "deepseek" in reg.with_api_channel()
    assert "yuanbao" in reg.with_web_channel()
