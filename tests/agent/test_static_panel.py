from fastapi.testclient import TestClient

from agent.main import create_app


def client(tmp_path=None) -> TestClient:
    kwargs = {"panel_dir": tmp_path} if tmp_path else {}
    token = "t" * 43
    return TestClient(create_app(stats=lambda: {"ts": 1}, token=token, **kwargs), headers={"X-Token": token})


def test_root_serves_panel_index():
    response = client().get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>PhoneBox" in response.text


def test_es_modules_are_served_as_javascript():
    # Sous Windows, le registre peut associer .js à text/plain : le navigateur refuserait le module.
    response = client().get("/lib/format.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")


def test_api_routes_take_precedence_over_static_files():
    c = client()

    assert c.get("/api/stats").json() == {"ts": 1}
    assert c.get("/healthz").json() == {"ok": True}


def test_panel_directory_is_injectable(tmp_path):
    (tmp_path / "index.html").write_text("<title>PhoneBox test</title>", encoding="utf-8")

    assert "PhoneBox test" in client(tmp_path).get("/").text


def test_files_outside_panel_are_not_reachable():
    c = client()

    assert c.get("/../agent/main.py").status_code == 404
    assert c.get("/%2e%2e/agent/main.py").status_code == 404
