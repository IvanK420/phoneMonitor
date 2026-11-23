import json
import os
import shutil
from pathlib import Path

import pytest

from agent.ai_sessions import AiSessionsCollector, scan_claude

FIXTURES = Path(__file__).parent.parent / "fixtures" / "claude_sessions"
NOW = 1731672000.0


@pytest.fixture
def claude_dir(tmp_path: Path) -> Path:
    """Copie des fixtures ; les fichiers sans date exploitable ont un mtime vieux de 2000 s."""
    d = tmp_path / "sessions"
    shutil.copytree(FIXTURES, d)
    for p in d.iterdir():
        os.utime(p, (NOW - 2000, NOW - 2000))
    return d


def by_project(sessions: list[dict]) -> dict:
    return {s["project"]: s for s in sessions}


# --- 3.5 Seuls les *.json sont ouverts ---------------------------------------------


def test_key_files_are_never_opened(claude_dir, monkeypatch):
    opened = []
    real_read_text = Path.read_text

    def spy(self, *args, **kwargs):
        opened.append(self.name)
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)
    (claude_dir / "notes.txt").write_text("{}", encoding="utf-8")

    sessions = scan_claude(claude_dir, now=NOW)

    assert opened, "le scanner doit lire les .json"
    assert all(name.endswith(".json") for name in opened)
    assert "FUITE-SECRET" not in json.dumps(sessions)


def test_directory_named_like_json_is_ignored(claude_dir):
    (claude_dir / "piege.json").unlink(missing_ok=True)
    (claude_dir / "piege.json").mkdir()

    scan_claude(claude_dir, now=NOW)  # ne lève pas


def test_file_vanishing_during_scan_is_skipped(claude_dir, monkeypatch):
    real_read_text = Path.read_text

    def vanish(self, *args, **kwargs):
        if self.name == "busy.json":
            raise FileNotFoundError(self)  # session terminée entre le listage et la lecture
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", vanish)

    assert "mon-projet" not in by_project(scan_claude(claude_dir, now=NOW))


# --- 3.6 Dossier inexistant ------------------------------------------------------


def test_missing_directory_gives_empty_list(tmp_path):
    assert scan_claude(tmp_path / "absent", now=NOW) == []


# --- Contenu du scan ----------------------------------------------------------------


def test_scan_reports_tool_project_state_and_date(claude_dir):
    sessions = by_project(scan_claude(claude_dir, now=NOW))

    assert sessions["mon-projet"] == {
        "tool": "claude-code",
        "project": "mon-projet",
        "state": "working",
        "updated_at": 1731671990,
    }
    assert sessions["api-server"]["state"] == "idle"


def test_unparseable_files_fall_back_to_mtime(claude_dir):
    fallback = [s for s in scan_claude(claude_dir, now=NOW) if s["project"] == "?"]

    assert fallback
    assert all(s["updated_at"] == int(NOW - 2000) and s["state"] == "stale" for s in fallback)


# --- 3.7 Non-fuite ------------------------------------------------------------------


def test_output_contains_only_public_fields(claude_dir):
    sessions = scan_claude(claude_dir, now=NOW)
    dumped = json.dumps(sessions, ensure_ascii=False)

    assert all(set(s) == {"tool", "project", "state", "updated_at"} for s in sessions)
    for secret in ["Users", "demo", "sessionId", "00000000", "pipe", "fixture-socket", "Nom de session", "bridge"]:
        assert secret not in dumped, secret


# --- 3.8 stale exclu par défaut ----------------------------------------------------


def collector(claude_dir: Path, tmp_path: Path) -> AiSessionsCollector:
    return AiSessionsCollector(claude_dir=claude_dir, codex_dir=tmp_path / "pas-de-codex", clock=lambda: NOW)


def test_stale_sessions_are_hidden_by_default(claude_dir, tmp_path):
    result = collector(claude_dir, tmp_path).collect()

    assert set(result) == {"sessions"}
    assert {s["state"] for s in result["sessions"]} == {"working", "idle"}


def test_include_stale_shows_them(claude_dir, tmp_path):
    states = [s["state"] for s in collector(claude_dir, tmp_path).collect(include_stale=True)["sessions"]]

    assert "stale" in states
    assert len(states) == 6  # tous les .json des fixtures, sans le .key
