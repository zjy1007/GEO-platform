from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_merchant_routes_registered():
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/merchants" in paths
    assert "/api/merchants/{merchant_id}" in paths
    assert "/api/merchants/{merchant_id}/completeness" in paths
    assert "/api/merchants/{merchant_id}/aliases" in paths


def test_create_merchant_missing_name_returns_422():
    resp = client.post("/api/merchants", json={"category": "宠物医疗"})
    assert resp.status_code == 422


def test_create_merchant_blank_name_returns_422():
    resp = client.post("/api/merchants", json={"name": ""})
    assert resp.status_code == 422
