import json

import pytest

from agent.claude_usage import UsageRecord, parse_usage_line


def assistant_line(**overrides) -> str:
    """Ligne de transcription au format réel, valeurs factices (contenu « secret » pour le test de non-fuite)."""
    entry = {
        "type": "assistant",
        "timestamp": "2026-11-23T17:38:24.500Z",
        "requestId": "req_fixture_1",
        "sessionId": "00000000-0000-4000-8000-000000000001",
        "cwd": "C:\\Users\\demo\\Projets\\secret",
        "isSidechain": False,
        "message": {
            "id": "msg_fixture_1",
            "model": "claude-opus-5-5",
            "role": "assistant",
            "content": [{"type": "text", "text": "CONTENU SECRET"}],
            "usage": {
                "input_tokens": 12,
                "output_tokens": 340,
                "cache_read_input_tokens": 51_000,
                "cache_creation_input_tokens": 1_200,
                "cache_creation": {"ephemeral_5m_input_tokens": 1_200},
                "service_tier": "standard",
            },
        },
    }
    entry.update(overrides)
    return json.dumps(entry)


def test_assistant_line_gives_usage_record():
    record = parse_usage_line(assistant_line())

    assert record == UsageRecord(
        key="msg_fixture_1/req_fixture_1",
        ts=1795455504.5,
        input=12,
        output=340,
        cache_read=51_000,
        cache_creation=1_200,
    )


def test_record_total_counts_every_token_kind():
    assert parse_usage_line(assistant_line()).total == 12 + 340 + 51_000 + 1_200


def test_record_keeps_no_conversation_data():
    record = parse_usage_line(assistant_line())

    dumped = repr(record)
    for secret in ["CONTENU SECRET", "secret", "00000000", "claude-opus"]:
        assert secret not in dumped


@pytest.mark.parametrize(
    "line",
    [
        json.dumps({"type": "user", "timestamp": "2026-11-23T17:38:24Z", "message": {"role": "user", "content": "x"}}),
        json.dumps({"type": "system", "timestamp": "2026-11-23T17:38:24Z"}),
        "",
        "{ligne tronquée",
        "[1, 2]",
    ],
)
def test_lines_without_usage_are_ignored(line):
    assert parse_usage_line(line) is None


def test_missing_timestamp_is_ignored():
    assert parse_usage_line(assistant_line(timestamp=None)) is None
    assert parse_usage_line(assistant_line(timestamp="hier")) is None


def test_missing_ids_are_ignored():
    # Sans identifiant, impossible de dédoublonner : on préfère ne pas compter que compter deux fois.
    assert parse_usage_line(assistant_line(requestId=None)) is None


def test_missing_or_invalid_token_fields_count_as_zero():
    line = json.loads(assistant_line())
    line["message"]["usage"] = {"output_tokens": 5, "input_tokens": "beaucoup", "cache_read_input_tokens": True}

    record = parse_usage_line(json.dumps(line))

    assert (record.input, record.output, record.cache_read, record.cache_creation) == (0, 5, 0, 0)


def test_timestamp_with_offset_is_converted_to_epoch():
    assert parse_usage_line(assistant_line(timestamp="2026-11-23T18:38:24.500+01:00")).ts == 1795455504.5
