"""Collecte matériel — logique pure.

Les vraies sources (psutil, nvidia-smi) vivent dans `sources.py` ; ici on ne fait
que transformer leurs sorties en schéma `/api/stats` (voir 02-api.md).
"""

import logging
import time
from collections.abc import Callable
from typing import Protocol, TypeVar

from agent.net_rate import NetCounters, net_rate

NVIDIA_SMI_QUERY = "name,utilization.gpu,memory.used,temperature.gpu"
_NVIDIA_FIELDS = 4
_GIB = 1024**3

log = logging.getLogger(__name__)
T = TypeVar("T")


class HardwareSources(Protocol):
    """Frontière avec le système : implémentée pour de vrai dans `sources.py`."""

    def cpu_percent(self) -> float: ...
    def cpu_temp(self) -> float | None: ...
    def memory(self) -> tuple[int, int]: ...  # (utilisé, total) en octets
    def mounts(self) -> list[str]: ...
    def disk_usage(self, mount: str) -> tuple[int, int]: ...  # (utilisé, total) en octets
    def net_counters(self) -> NetCounters: ...
    def nvidia_smi(self) -> str | None: ...


def _gb(n_bytes: int) -> float:
    return round(n_bytes / _GIB, 1)


def _percent(used: int, total: int) -> float:
    return round(used / total * 100, 1) if total > 0 else 0.0


def _safe(read: Callable[[], T], default: T, what: str) -> T:
    """Une source optionnelle qui échoue donne `default` au lieu de faire tomber l'endpoint."""
    try:
        return read()
    except Exception as exc:  # noqa: BLE001 — frontière système, tout est possible
        log.debug("source %s indisponible : %r", what, exc)
        return default


def normalize_mount(mount: str) -> str:
    """`C:\\` → `C:` ; `/home/` → `/home` ; `/` reste `/`."""
    return mount.rstrip("\\/") or mount[:1]


class StatsCollector:
    """Assemble la réponse de `/api/stats`. Garde le relevé réseau précédent pour le débit."""

    def __init__(self, sources: HardwareSources, clock: Callable[[], float] = time.time):
        self._sources = sources
        self._clock = clock
        self._net_prev: tuple[float, NetCounters] | None = None

    def collect(self) -> dict:
        s = self._sources
        now = self._clock()
        return {
            "ts": int(now),
            "cpu": self._cpu(),
            "ram": self._ram(),
            "gpu": parse_nvidia_smi(_safe(s.nvidia_smi, None, "gpu")),
            "disks": self._disks(),
            "net": self._net(now),
        }

    def _cpu(self) -> dict:
        temp = _safe(self._sources.cpu_temp, None, "température")
        return {
            "percent": round(self._sources.cpu_percent(), 1),
            "temp_c": round(temp) if temp is not None else None,
        }

    def _ram(self) -> dict:
        used, total = self._sources.memory()
        return {"used_gb": _gb(used), "total_gb": _gb(total), "percent": _percent(used, total)}

    def _disks(self) -> list[dict]:
        disks = []
        for mount in _safe(self._sources.mounts, [], "volumes"):
            try:
                used, total = self._sources.disk_usage(mount)
            except OSError:  # lecteur CD vide, accès refusé…
                continue
            if total <= 0:
                continue
            disks.append({"mount": normalize_mount(mount), "used_gb": _gb(used), "total_gb": _gb(total)})
        return disks

    def _net(self, now: float) -> dict:
        cur = self._sources.net_counters()
        if self._net_prev is None:
            rate = net_rate(None, cur, 0)
        else:
            prev_t, prev = self._net_prev
            rate = net_rate(prev, cur, now - prev_t)
        self._net_prev = (now, cur)
        return rate


def _int_or_none(raw: str) -> int | None:
    try:
        return round(float(raw))
    except ValueError:  # "[N/A]", "[Not Supported]"…
        return None


def parse_nvidia_smi(text: str | None) -> dict | None:
    """Parse `nvidia-smi --query-gpu=<NVIDIA_SMI_QUERY> --format=csv,noheader,nounits`.

    Ne garde que le premier GPU. Toute sortie inexploitable (vide, erreur,
    commande absente) donne `None`.
    """
    if not text:
        return None
    for line in text.splitlines():
        fields = [f.strip() for f in line.split(",")]
        if len(fields) != _NVIDIA_FIELDS or not fields[0]:
            continue
        name, util, vram, temp = fields
        return {
            "name": name,
            "percent": _int_or_none(util),
            "vram_used_mb": _int_or_none(vram),
            "temp_c": _int_or_none(temp),
        }
    return None
