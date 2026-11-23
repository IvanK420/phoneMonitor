import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.ai_sessions import AiSessionsCollector
from agent.main import create_app

FIXTURES = Path(__file__).parent.parent / "fixtures" / "claude_sessions"
NOW = 1731672000.0


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    claude = tmp_path / "claude"
    shutil.copytree(FIXTURES, claude)
    for p in claude.iterdir():
        os.utime(p, (NOW - 2000, NOW - 2000))
    collector = AiSessionsCollector(claude, tmp_path / "codex-absent", clock=lambda: NOW)
    return TestClient(create_app(stats=lambda: {}, ai=collector.collect))


def test_get_ai_lists_active_sessions(client):
    response = client.get("/api/ai")

    assert response.status_code == 200
    assert sorted(response.json()["sessions"], key=lambda s: s["project"]) == [
        {"tool": "claude-code", "project": "api-server", "state": "idle", "updated_at": 1731671700},
        {"tool": "claude-code", "project": "mon-projet", "state": "working", "updated_at": 1731671990},
    ]


@pytest.mark.parametrize("value", ["1", "true"])
def test_include_stale_query_parameter(client, value):
    sessions = client.get(f"/api/ai?include_stale={value}").json()["sessions"]

    assert len(sessions) == 6
    assert sum(s["state"] == "stale" for s in sessions) == 4


def test_include_stale_zero_keeps_default(client):
    assert len(client.get("/api/ai?include_stale=0").json()["sessions"]) == 2


def test_response_never_leaks_session_internals(client):
    body = client.get("/api/ai?include_stale=1").text

    for secret in ["FUITE-SECRET", "Users", "sessionId", "pipe", "Nom de session"]:
        assert secret not in body, secret
