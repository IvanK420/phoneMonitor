"""Une source qui manque ne doit jamais faire planter /api/stats (01-architecture, « tolérance aux pannes »)."""

import pytest

from agent.hardware import StatsCollector

from .fakes import GIB, FakeClock, FakeSources


def collect(sources: FakeSources) -> dict:
    return StatsCollector(sources, clock=FakeClock()).collect()


# --- 1.5 GPU -----------------------------------------------------------------


def test_gpu_source_absent_gives_null():
    sources = FakeSources()
    sources.smi = None

    assert collect(sources)["gpu"] is None


@pytest.mark.parametrize("error", [FileNotFoundError("nvidia-smi"), OSError("boom"), RuntimeError("timeout")])
def test_gpu_source_raising_gives_null(error):
    sources = FakeSources()

    def broken():
        raise error

    sources.nvidia_smi = broken

    stats = collect(sources)

    assert stats["gpu"] is None
    assert stats["cpu"]["percent"] == 23.5


# --- 1.6 Température (Windows : psutil.sensors_temperatures n'existe pas) -----


def test_temperature_unavailable_gives_null():
    sources = FakeSources()
    sources.temp = None

    assert collect(sources)["cpu"] == {"percent": 23.5, "temp_c": None}


def test_temperature_source_raising_gives_null():
    sources = FakeSources()

    def no_sensors():
        raise AttributeError("module 'psutil' has no attribute 'sensors_temperatures'")

    sources.cpu_temp = no_sensors

    assert collect(sources)["cpu"]["temp_c"] is None


# --- 1.7 Disques ---------------------------------------------------------------


@pytest.mark.parametrize("error", [PermissionError("refusé"), OSError(21, "Le périphérique n'est pas prêt")])
def test_inaccessible_volume_is_skipped(error):
    sources = FakeSources()
    sources.mount_list = ["C:\\", "E:\\", "D:\\"]
    sources.usage["D:\\"] = (1 * GIB, 2 * GIB)

    def usage(mount):
        if mount == "E:\\":  # lecteur CD vide
            raise error
        return sources.usage[mount]

    sources.disk_usage = usage

    assert [d["mount"] for d in collect(sources)["disks"]] == ["C:", "D:"]


def test_empty_volume_of_size_zero_is_skipped():
    sources = FakeSources()
    sources.mount_list = ["C:\\", "E:\\"]
    sources.usage["E:\\"] = (0, 0)

    assert [d["mount"] for d in collect(sources)["disks"]] == ["C:"]


def test_mount_listing_failure_gives_empty_list():
    sources = FakeSources()

    def broken():
        raise OSError("boom")

    sources.mounts = broken

    assert collect(sources)["disks"] == []
