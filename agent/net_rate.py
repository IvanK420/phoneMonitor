"""Débit réseau calculé à partir de deux relevés de compteurs cumulés (octets)."""

from typing import NamedTuple


class NetCounters(NamedTuple):
    bytes_recv: int
    bytes_sent: int


def _kbps(before: int, after: int, dt: float) -> int:
    delta = after - before
    if delta <= 0:
        return 0
    return round(delta * 8 / 1000 / dt)


def net_rate(prev: NetCounters | None, cur: NetCounters, dt: float) -> dict:
    """Retourne `down_kbps` / `up_kbps` (kilobits/s, entiers, jamais négatifs)."""
    if prev is None or dt <= 0:
        return {"down_kbps": 0, "up_kbps": 0}
    return {
        "down_kbps": _kbps(prev.bytes_recv, cur.bytes_recv, dt),
        "up_kbps": _kbps(prev.bytes_sent, cur.bytes_sent, dt),
    }
