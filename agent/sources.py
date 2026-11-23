"""Vraies sources matériel (psutil, nvidia-smi) — couche mince, sans logique.

Toute décision (arrondis, tolérance, schéma) est dans `hardware.py`, testé à part.
Ce module n'est vérifié que par le test « smoke » `@pytest.mark.system`.
"""

import shutil
import subprocess
import sys
from collections.abc import Callable

import psutil

from agent.cache import TTLCache
from agent.hardware import NVIDIA_SMI_QUERY, StatsCollector
from agent.net_rate import NetCounters

# Capteurs CPU par ordre de préférence (Linux) ; Windows n'expose rien via psutil.
_CPU_SENSORS = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz")
# Pseudo-systèmes de fichiers sans intérêt sur un panneau.
_IGNORED_FSTYPES = {"squashfs", "tmpfs", "devtmpfs", "overlay"}
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


class PsutilSources:
    def __init__(self):
        psutil.cpu_percent(interval=None)  # amorce : le premier appel renvoie toujours 0.0
        self._nvidia_smi = shutil.which("nvidia-smi")

    def cpu_percent(self) -> float:
        return psutil.cpu_percent(interval=None)

    def cpu_temp(self) -> float | None:
        read = getattr(psutil, "sensors_temperatures", None)
        if read is None:  # Windows
            return None
        temps = read() or {}
        for sensor in (*_CPU_SENSORS, *temps):
            entries = temps.get(sensor)
            if entries:
                return entries[0].current
        return None

    def memory(self) -> tuple[int, int]:
        vm = psutil.virtual_memory()
        return vm.total - vm.available, vm.total

    def mounts(self) -> list[str]:
        return [p.mountpoint for p in psutil.disk_partitions(all=False) if p.fstype not in _IGNORED_FSTYPES]

    def disk_usage(self, mount: str) -> tuple[int, int]:
        usage = psutil.disk_usage(mount)
        return usage.used, usage.total

    def net_counters(self) -> NetCounters:
        c = psutil.net_io_counters()
        return NetCounters(bytes_recv=c.bytes_recv, bytes_sent=c.bytes_sent)

    def nvidia_smi(self) -> str | None:
        if self._nvidia_smi is None:
            return None
        result = subprocess.run(
            [self._nvidia_smi, f"--query-gpu={NVIDIA_SMI_QUERY}", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
            creationflags=_NO_WINDOW,
        )
        return result.stdout if result.returncode == 0 else None


def build_stats_provider(ttl: float = 1.0) -> Callable[[], dict]:
    """Câblage réel : psutil → StatsCollector → cache 1 s."""
    return TTLCache(StatsCollector(PsutilSources()).collect, ttl=ttl)
