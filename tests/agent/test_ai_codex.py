import os
from pathlib import Path

from agent.ai_sessions import CODEX_MAX_SESSIONS, AiSessionsCollector, scan_codex

NOW = 1731672000.0


def touch(path: Path, age_s: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"cwd": "/home/demo/secret"}\n', encoding="utf-8")
    os.utime(path, (NOW - age_s, NOW - age_s))
    return path


def test_missing_codex_directory_gives_empty_list(tmp_path):
    assert scan_codex(tmp_path / ".codex" / "sessions", now=NOW) == []


def test_nested_session_files_are_classified_by_mtime(tmp_path):
    root = tmp_path / "sessions"
    touch(root / "2026" / "11" / "23" / "rollout-a.jsonl", age_s=3)
    touch(root / "2026" / "11" / "23" / "rollout-b.jsonl", age_s=120)
    touch(root / "2026" / "11" / "01" / "rollout-c.jsonl", age_s=90_000)

    sessions = sorted(scan_codex(root, now=NOW), key=lambda s: -s["updated_at"])

    assert sessions == [
        {"tool": "codex", "project": "?", "state": "working", "updated_at": int(NOW - 3)},
        {"tool": "codex", "project": "?", "state": "idle", "updated_at": int(NOW - 120)},
        {"tool": "codex", "project": "?", "state": "stale", "updated_at": int(NOW - 90_000)},
    ]


def test_codex_file_contents_are_never_read(tmp_path, monkeypatch):
    touch(tmp_path / "s" / "rollout.jsonl", age_s=1)

    def forbidden(self, *args, **kwargs):
        raise AssertionError(f"lecture interdite : {self}")

    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)

    assert len(scan_codex(tmp_path / "s", now=NOW)) == 1


def test_only_session_like_files_are_counted(tmp_path):
    root = tmp_path / "s"
    touch(root / "rollout.jsonl", age_s=1)
    touch(root / "index.json", age_s=1)
    touch(root / "notes.txt", age_s=1)
    touch(root / "auth.key", age_s=1)

    assert len(scan_codex(root, now=NOW)) == 2


def test_history_is_capped_to_most_recent_files(tmp_path):
    root = tmp_path / "s"
    for i in range(CODEX_MAX_SESSIONS + 15):
        touch(root / f"rollout-{i:03}.jsonl", age_s=1000 + i)

    sessions = scan_codex(root, now=NOW)

    assert len(sessions) == CODEX_MAX_SESSIONS
    assert max(NOW - s["updated_at"] for s in sessions) < 1000 + CODEX_MAX_SESSIONS


def test_collector_merges_claude_and_codex(tmp_path):
    touch(tmp_path / "codex" / "rollout.jsonl", age_s=2)
    claude = tmp_path / "claude"
    claude.mkdir()
    (claude / "1.json").write_text('{"cwd": "/p/projet-x", "status": "idle", "updatedAt": %d}' % (NOW * 1000), "utf-8")

    sessions = AiSessionsCollector(claude, tmp_path / "codex", clock=lambda: NOW).collect()["sessions"]

    assert sorted(s["tool"] for s in sessions) == ["claude-code", "codex"]
