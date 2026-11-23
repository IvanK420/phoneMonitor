"""Smoke test sur les vraies sources : vérifie uniquement les types. Lancé par `run-tests.ps1 -System`."""

import pytest

from agent.hardware import StatsCollector
from agent.sources import PsutilSources

pytestmark = pytest.mark.system


def test_real_sources_produce_well_typed_stats():
    collector = StatsCollector(PsutilSources())
    collector.collect()
    stats = collector.collect()

    assert isinstance(stats["ts"], int)
    assert 0 <= stats["cpu"]["percent"] <= 100
    assert stats["cpu"]["temp_c"] is None or isinstance(stats["cpu"]["temp_c"], int)
    assert stats["ram"]["total_gb"] > 0
    assert 0 < stats["ram"]["percent"] <= 100
    assert stats["gpu"] is None or isinstance(stats["gpu"]["name"], str)
    assert stats["disks"], "au moins un volume attendu"
    for disk in stats["disks"]:
        assert isinstance(disk["mount"], str) and disk["total_gb"] > 0
    assert set(stats["net"]) == {"down_kbps", "up_kbps"}
    assert all(isinstance(v, int) and v >= 0 for v in stats["net"].values())
