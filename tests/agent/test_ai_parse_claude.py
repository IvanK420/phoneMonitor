from pathlib import Path

import pytest

from agent.ai_sessions import parse_claude

FIXTURES = Path(__file__).parent.parent / "fixtures" / "claude_sessions"
MTIME = 1731600000.0


def parse(name: str) -> dict:
    return parse_claude((FIXTURES / name).read_text(encoding="utf-8"), mtime=MTIME)


# --- 3.2 Format réel ------------------------------------------------------------


def test_project_is_basename_of_windows_cwd():
    assert parse("busy.json")["project"] == "mon-projet"


def test_project_is_basename_of_posix_cwd_with_trailing_slash():
    assert parse("idle_posix.json")["project"] == "api-server"


def test_updated_at_converted_from_milliseconds_to_seconds():
    # updatedAt = 1731671990500 ms
    assert parse("busy.json")["updated_at"] == 1731671990


def test_explicit_status_is_kept():
    assert parse("busy.json")["status"] == "busy"
    assert parse("idle_posix.json")["status"] == "idle"


def test_status_updated_at_is_used_when_more_recent():
    text = '{"cwd": "/x/p", "updatedAt": 1000000, "statusUpdatedAt": 5000000}'

    assert parse_claude(text, mtime=MTIME)["updated_at"] == 5000


# --- 3.4 Parseur tolérant : repli sur mtime, projet « ? » ------------------------


@pytest.mark.parametrize("name", ["truncated.json", "not_an_object.json"])
def test_corrupt_json_falls_back_to_mtime(name):
    assert parse(name) == {"project": "?", "updated_at": int(MTIME), "status": None}


def test_missing_fields_fall_back_to_mtime():
    assert parse("missing_fields.json") == {"project": "?", "updated_at": int(MTIME), "status": None}


def test_wrong_types_are_ignored_field_by_field():
    assert parse("wrong_types.json") == {"project": "?", "updated_at": int(MTIME), "status": "busy"}


@pytest.mark.parametrize("cwd", ["", "/", "C:\\"])
def test_cwd_without_basename_gives_question_mark(cwd):
    text = '{"cwd": %s, "updatedAt": 1000}' % __import__("json").dumps(cwd)

    assert parse_claude(text, mtime=MTIME)["project"] == "?"
