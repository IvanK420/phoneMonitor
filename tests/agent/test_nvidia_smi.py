from pathlib import Path

import pytest

from agent.hardware import parse_nvidia_smi

FIXTURES = Path(__file__).parent.parent / "fixtures" / "nvidia_smi"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_one_gpu():
    assert parse_nvidia_smi(fixture("one_gpu.csv")) == {
        "name": "NVIDIA GeForce RTX 4070",
        "percent": 12,
        "vram_used_mb": 2100,
        "temp_c": 49,
    }


def test_several_gpus_keeps_the_first():
    assert parse_nvidia_smi(fixture("two_gpus.csv"))["name"] == "NVIDIA GeForce RTX 4090"


def test_na_values_become_none():
    assert parse_nvidia_smi(fixture("na_values.csv")) == {
        "name": "NVIDIA GeForce GTX 1050",
        "percent": None,
        "vram_used_mb": 512,
        "temp_c": None,
    }


@pytest.mark.parametrize("name", ["empty.txt", "command_not_found.txt", "driver_error.txt"])
def test_unusable_output_gives_none(name):
    assert parse_nvidia_smi(fixture(name)) is None


def test_none_input_gives_none():
    assert parse_nvidia_smi(None) is None


def test_windows_line_endings_and_spaces():
    assert parse_nvidia_smi("  RTX A2000 ,  5 , 300 , 41 \r\n") == {
        "name": "RTX A2000",
        "percent": 5,
        "vram_used_mb": 300,
        "temp_c": 41,
    }
