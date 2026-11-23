"""Fausses sources matériel partagées par les tests de l'agent."""

from agent.net_rate import NetCounters

GIB = 1024**3


class FakeSources:
    def __init__(self):
        self.cpu = 23.456
        self.temp: float | None = 57.8
        self.mem = (int(11.24 * GIB), 32 * GIB)  # (utilisé, total) en octets
        self.mount_list = ["C:\\"]
        self.usage = {"C:\\": (int(410.04 * GIB), int(953.0 * GIB))}
        self.counters = [NetCounters(0, 0), NetCounters(300_000, 21_250)]
        self.smi: str | None = "NVIDIA GeForce RTX 4070, 12, 2100, 49\n"

    def cpu_percent(self) -> float:
        return self.cpu

    def cpu_temp(self) -> float | None:
        return self.temp

    def memory(self) -> tuple[int, int]:
        return self.mem

    def mounts(self) -> list[str]:
        return self.mount_list

    def disk_usage(self, mount: str) -> tuple[int, int]:
        return self.usage[mount]

    def net_counters(self) -> NetCounters:
        return self.counters.pop(0) if len(self.counters) > 1 else self.counters[0]

    def nvidia_smi(self) -> str | None:
        return self.smi


class FakeClock:
    def __init__(self, t: float = 1731672000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t
