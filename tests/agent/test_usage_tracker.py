import json
import os
from pathlib import Path

from agent.claude_usage import UsageTracker

NOW = 1795455600.0  # 2026-11-23 17:40 UTC
SINCE = NOW - 5 * 3600


def iso(ts: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def line(msg: str, ts: float, output: int = 10, req: str | None = None) -> str:
    return (
        json.dumps(
            {
                "type": "assistant",
                "timestamp": iso(ts),
                "requestId": req or f"req_{msg}",
                "message": {"id": msg, "content": [{"type": "text", "text": "x"}], "usage": {"output_tokens": output}},
            }
        )
        + "\n"
    )


def write(path: Path, *lines: str, mtime: float = NOW) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.writelines(lines)
    os.utime(path, (mtime, mtime))
    return path


def outputs(tracker: UsageTracker) -> list[int]:
    return sorted(r.output for r in tracker.refresh(since=SINCE))


def test_missing_directory_gives_nothing(tmp_path):
    assert UsageTracker(tmp_path / "absent").refresh(since=SINCE) == []


def test_reads_nested_transcripts_and_ignores_other_files(tmp_path):
    write(tmp_path / "proj-a" / "s1.jsonl", line("m1", NOW - 60, 1))
    write(tmp_path / "proj-b" / "s2" / "subagents" / "agent.jsonl", line("m2", NOW - 60, 2))
    write(tmp_path / "proj-a" / "notes.json", line("m3", NOW - 60, 3))

    assert outputs(UsageTracker(tmp_path)) == [1, 2]


def test_same_response_written_several_times_is_counted_once(tmp_path):
    write(tmp_path / "p" / "s.jsonl", line("m1", NOW - 60, 5), line("m1", NOW - 60, 5), line("m2", NOW - 50, 7))
    write(tmp_path / "p" / "copie.jsonl", line("m1", NOW - 60, 5))

    assert outputs(UsageTracker(tmp_path)) == [5, 7]


def test_appended_lines_are_picked_up_without_rereading(tmp_path):
    path = write(tmp_path / "p" / "s.jsonl", line("m1", NOW - 60, 1))
    tracker = UsageTracker(tmp_path)
    tracker.refresh(since=SINCE)

    # On abîme la partie déjà lue : si elle était relue, m1 disparaîtrait ou une erreur surviendrait.
    size = path.stat().st_size
    path.write_bytes(b"#" * (size - 1) + b"\n")
    write(path, line("m2", NOW - 10, 2))

    assert outputs(tracker) == [1, 2]


def test_line_being_written_is_read_once_complete(tmp_path):
    path = tmp_path / "p" / "s.jsonl"
    full = line("m1", NOW - 60, 1)
    write(path, full[:20])
    tracker = UsageTracker(tmp_path)

    assert outputs(tracker) == []

    write(path, full[20:])
    assert outputs(tracker) == [1]


def test_truncated_or_replaced_file_is_read_again(tmp_path):
    path = write(tmp_path / "p" / "s.jsonl", line("m1", NOW - 60, 1), line("m2", NOW - 60, 2))
    tracker = UsageTracker(tmp_path)
    tracker.refresh(since=SINCE)

    path.write_text(line("m3", NOW - 5, 3), encoding="utf-8")
    os.utime(path, (NOW, NOW))

    assert outputs(tracker) == [1, 2, 3]


def test_records_outside_the_period_are_dropped(tmp_path):
    write(tmp_path / "p" / "s.jsonl", line("old", SINCE - 1, 1), line("new", SINCE + 1, 2))
    tracker = UsageTracker(tmp_path)

    assert outputs(tracker) == [2]


def test_records_age_out_on_later_refresh(tmp_path):
    write(tmp_path / "p" / "s.jsonl", line("m1", NOW - 60, 1))
    tracker = UsageTracker(tmp_path)
    tracker.refresh(since=SINCE)

    assert tracker.refresh(since=NOW) == []


def test_old_files_are_not_opened(tmp_path, monkeypatch):
    write(tmp_path / "p" / "vieux.jsonl", line("m1", SINCE - 3600, 1), mtime=SINCE - 3600)
    write(tmp_path / "p" / "recent.jsonl", line("m2", NOW - 60, 2))
    opened = []
    real_open = Path.open

    def spy(self, *args, **kwargs):
        opened.append(self.name)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy)

    UsageTracker(tmp_path).refresh(since=SINCE)

    assert opened == ["recent.jsonl"]


def test_file_vanishing_during_refresh_is_skipped(tmp_path, monkeypatch):
    write(tmp_path / "p" / "s.jsonl", line("m1", NOW - 60, 1))
    real_open = Path.open

    def vanish(self, *args, **kwargs):
        raise FileNotFoundError(self)

    monkeypatch.setattr(Path, "open", vanish)
    assert UsageTracker(tmp_path).refresh(since=SINCE) == []
    monkeypatch.setattr(Path, "open", real_open)
