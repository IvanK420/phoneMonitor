import hmac

import pytest
from fastapi.testclient import TestClient

from agent.auth import token_matches
from agent.main import create_app

TOKEN = "t" * 43


@pytest.fixture
def client() -> TestClient:
    app = create_app(stats=lambda: {"ts": 1}, ai=lambda include_stale: {"sessions": []}, token=TOKEN)
    return TestClient(app)


# --- 4.2 /api/* exige le jeton ------------------------------------------------------


@pytest.mark.parametrize("path", ["/api/stats", "/api/ai"])
def test_without_token_is_401(client, path):
    response = client.get(path)

    assert response.status_code == 401
    assert "ts" not in response.text


@pytest.mark.parametrize("path", ["/api/stats", "/api/ai"])
def test_wrong_token_is_401(client, path):
    assert client.get(path, headers={"X-Token": "x" * 43}).status_code == 401
    assert client.get(f"{path}?token=mauvais").status_code == 401


def test_valid_header_token_is_200(client):
    response = client.get("/api/stats", headers={"X-Token": TOKEN})

    assert response.status_code == 200
    assert response.json() == {"ts": 1}


def test_valid_query_token_is_200(client):
    assert client.get(f"/api/ai?token={TOKEN}").status_code == 200


def test_empty_header_does_not_fall_through_to_valid_query(client):
    # Un en-tête présent mais faux ne doit pas être ignoré au profit du paramètre.
    assert client.get(f"/api/stats?token={TOKEN}", headers={"X-Token": "faux"}).status_code == 401


# --- 4.3 /healthz et le panneau restent publics ------------------------------------


def test_healthz_without_token_is_200(client):
    assert client.get("/healthz").json() == {"ok": True}


def test_panel_page_without_token_is_200(client):
    # La page ne contient aucune donnée : c'est elle qui transmet ensuite le jeton.
    assert client.get("/").status_code == 200


# --- 4.4 Comparaison en temps constant --------------------------------------------


def test_token_matches():
    assert token_matches(TOKEN, TOKEN)
    assert not token_matches("faux", TOKEN)
    assert not token_matches("", TOKEN)
    assert not token_matches(None, TOKEN)
    assert not token_matches("é" * 43, TOKEN)  # non-ASCII : pas d'exception


def test_token_comparison_uses_compare_digest(monkeypatch):
    calls = []
    real = hmac.compare_digest

    def spy(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(hmac, "compare_digest", spy)

    token_matches("abc", TOKEN)

    assert calls, "hmac.compare_digest doit être utilisé"


# --- 4.6 Lecture seule ----------------------------------------------------------------


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
@pytest.mark.parametrize("path", ["/api/stats", "/api/ai"])
def test_non_get_methods_are_405(client, method, path):
    response = client.request(method.upper(), path, headers={"X-Token": TOKEN})

    assert response.status_code == 405
