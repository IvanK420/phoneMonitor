import json

import pytest

from agent.config import ConfigError, load_config


def test_first_launch_creates_config_with_random_token(tmp_path):
    path = tmp_path / "config.json"

    config = load_config(path)

    assert path.exists()
    assert len(config["token"]) >= 32
    assert json.loads(path.read_text(encoding="utf-8"))["token"] == config["token"]


def test_second_launch_keeps_the_same_token(tmp_path):
    path = tmp_path / "config.json"

    first = load_config(path)["token"]
    second = load_config(path)["token"]

    assert first == second


def test_tokens_differ_between_installations(tmp_path):
    a = load_config(tmp_path / "a.json")["token"]
    b = load_config(tmp_path / "b.json")["token"]

    assert a != b


def test_existing_settings_are_preserved_when_token_is_added(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"oled": {"swap_minutes": 20}}), encoding="utf-8")

    config = load_config(path)

    assert config["oled"] == {"swap_minutes": 20}
    assert len(config["token"]) >= 32
    assert json.loads(path.read_text(encoding="utf-8"))["oled"] == {"swap_minutes": 20}


@pytest.mark.parametrize("token", ["", "court", 12345, None])
def test_too_short_or_invalid_token_is_replaced(tmp_path, token):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"token": token}), encoding="utf-8")

    assert len(load_config(path)["token"]) >= 32


@pytest.mark.parametrize("content", ["{pas du json", "[1, 2]"])
def test_corrupt_config_is_not_overwritten(tmp_path, content):
    # Le fichier peut contenir des réglages écrits à la main : on refuse plutôt que d'écraser.
    path = tmp_path / "config.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(path)

    assert path.read_text(encoding="utf-8") == content
