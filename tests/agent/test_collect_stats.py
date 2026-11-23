import pytest

from agent.hardware import StatsCollector, normalize_mount

from .fakes import FakeClock, FakeSources


def collect_twice(sources: FakeSources, clock: FakeClock, dt: float = 2.0) -> dict:
    """Premier relevé pour amorcer le débit réseau, second relevé `dt` secondes plus tard."""
    collector = StatsCollector(sources, clock=clock)
    clock.t -= dt
    collector.collect()
    clock.t += dt
    return collector.collect()


def test_stats_follow_api_schema():
    stats = collect_twice(FakeSources(), FakeClock(1731672000.4))

    assert stats == {
        "ts": 1731672000,
        "cpu": {"percent": 23.5, "temp_c": 58},
        "ram": {"used_gb": 11.2, "total_gb": 32.0, "percent": 35.1},
        "gpu": {"name": "NVIDIA GeForce RTX 4070", "percent": 12, "vram_used_mb": 2100, "temp_c": 49},
        "disks": [{"mount": "C:", "used_gb": 410.0, "total_gb": 953.0}],
        "net": {"down_kbps": 1200, "up_kbps": 85},
    }


def test_first_collect_reports_zero_network_rate():
    stats = StatsCollector(FakeSources(), clock=FakeClock()).collect()

    assert stats["net"] == {"down_kbps": 0, "up_kbps": 0}


def test_zero_total_ram_does_not_divide_by_zero():
    sources = FakeSources()
    sources.mem = (0, 0)

    stats = StatsCollector(sources, clock=FakeClock()).collect()

    assert stats["ram"]["percent"] == 0.0


@pytest.mark.parametrize(
    ("raw", "label"),
    [("C:\\", "C:"), ("D:\\", "D:"), ("/", "/"), ("/home/", "/home"), ("/mnt/data", "/mnt/data")],
)
def test_mount_labels(raw, label):
    assert normalize_mount(raw) == label
