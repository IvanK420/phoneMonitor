from fastapi.testclient import TestClient

from agent.hardware import StatsCollector
from agent.main import create_app

from .fakes import FakeClock, FakeSources

TOKEN = "t" * 43


def make_client(stats) -> TestClient:
    return TestClient(create_app(stats=stats, token=TOKEN), headers={"X-Token": TOKEN})


def test_get_stats_returns_collector_json():
    collector = StatsCollector(FakeSources(), clock=FakeClock())
    client = make_client(collector.collect)

    response = client.get("/api/stats")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"ts", "cpu", "ram", "gpu", "disks", "net"}
    assert body["ts"] == 1731672000
    assert body["cpu"] == {"percent": 23.5, "temp_c": 58}
    assert body["disks"] == [{"mount": "C:", "used_gb": 410.0, "total_gb": 953.0}]
    assert body["gpu"]["name"] == "NVIDIA GeForce RTX 4070"


def test_get_stats_without_gpu_serializes_null():
    sources = FakeSources()
    sources.smi = None
    sources.temp = None
    client = make_client(StatsCollector(sources, clock=FakeClock()).collect)

    body = client.get("/api/stats").json()

    assert body["gpu"] is None
    assert body["cpu"]["temp_c"] is None


def test_each_request_asks_the_provider():
    calls = []

    def provider():
        calls.append(1)
        return {"ts": len(calls)}

    client = make_client(provider)

    client.get("/api/stats")
    client.get("/api/stats")

    assert len(calls) == 2  # le cache est la responsabilité du fournisseur (TTLCache au câblage)
