from fastapi.testclient import TestClient

from agent.main import create_app


def test_healthz_returns_ok():
    client = TestClient(create_app(stats=lambda: {}, ai=lambda include_stale: {}, token="t" * 43))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
