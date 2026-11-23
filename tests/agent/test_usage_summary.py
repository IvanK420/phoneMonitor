from datetime import datetime

from agent.claude_usage import UsageCollector, UsageRecord, local_midnight, summarize

MIDNIGHT = 1795392000.0  # minuit (référence arbitraire pour les tests purs)
H = 3600


def rec(key: str, ts: float, input=0, output=0, cache_read=0, cache_creation=0) -> UsageRecord:
    return UsageRecord(key, ts, input, output, cache_read, cache_creation)


ZERO = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0, "total": 0}


def test_empty_day():
    assert summarize([], now=MIDNIGHT + 10 * H, midnight=MIDNIGHT) == {
        "today": ZERO,
        "window_5h": ZERO,
        "hourly": [0] * 24,
    }


def test_today_sums_every_kind_since_midnight():
    records = [
        rec("a", MIDNIGHT + 1 * H, input=1, output=10, cache_read=100, cache_creation=1000),
        rec("b", MIDNIGHT + 9 * H, output=5),
        rec("hier", MIDNIGHT - 60, output=999),
    ]

    today = summarize(records, now=MIDNIGHT + 10 * H, midnight=MIDNIGHT)["today"]

    assert today == {"input": 1, "output": 15, "cache_read": 100, "cache_creation": 1000, "total": 1116}


def test_window_is_the_last_five_hours_even_across_midnight():
    now = MIDNIGHT + 2 * H
    records = [
        rec("hier-soir", MIDNIGHT - 2 * H, output=7),  # dans la fenêtre, pas dans « aujourd'hui »
        rec("trop-vieux", now - 5 * H - 1, output=100),
        rec("ce-matin", MIDNIGHT + 1 * H, output=3),
    ]

    summary = summarize(records, now=now, midnight=MIDNIGHT)

    assert summary["window_5h"]["output"] == 10
    assert summary["today"]["output"] == 3


def test_hourly_totals_by_local_hour():
    records = [
        rec("a", MIDNIGHT + 0.5 * H, output=1),
        rec("b", MIDNIGHT + 0.9 * H, output=2),
        rec("c", MIDNIGHT + 13.2 * H, input=4),
        rec("d", MIDNIGHT + 23.99 * H, output=8),
    ]

    hourly = summarize(records, now=MIDNIGHT + 23.995 * H, midnight=MIDNIGHT)["hourly"]

    assert hourly[0] == 3
    assert hourly[13] == 4
    assert hourly[23] == 8
    assert sum(hourly) == 15


def test_hour_beyond_23_on_daylight_saving_day_goes_to_last_bucket():
    # Jour de 25 h (changement d'heure) : rien ne doit sortir du tableau.
    hourly = summarize([rec("a", MIDNIGHT + 24.5 * H, output=1)], now=MIDNIGHT + 24.6 * H, midnight=MIDNIGHT)["hourly"]

    assert len(hourly) == 24
    assert hourly[23] == 1


def test_local_midnight_is_the_start_of_the_local_day():
    now = 1795455600.0
    midnight = local_midnight(now)

    assert midnight <= now < midnight + 25 * H
    assert datetime.fromtimestamp(midnight).time().isoformat() == "00:00:00"
    assert datetime.fromtimestamp(midnight).date() == datetime.fromtimestamp(now).date()


class FakeTracker:
    def __init__(self, records):
        self.records = records
        self.since = None

    def refresh(self, since):
        self.since = since
        return [r for r in self.records if r.ts >= since]


def test_collector_reads_back_to_the_earliest_needed_moment():
    now = MIDNIGHT + 2 * H  # 2 h du matin : la fenêtre de 5 h remonte avant minuit
    tracker = FakeTracker([rec("a", MIDNIGHT - 1 * H, output=4)])

    result = UsageCollector(tracker, clock=lambda: now, midnight=lambda t: MIDNIGHT).collect()

    assert tracker.since == now - 5 * H
    assert result["window_5h"]["output"] == 4
    assert result["today"]["output"] == 0


def test_collector_in_the_afternoon_reads_since_midnight():
    now = MIDNIGHT + 15 * H
    tracker = FakeTracker([])

    UsageCollector(tracker, clock=lambda: now, midnight=lambda t: MIDNIGHT).collect()

    assert tracker.since == MIDNIGHT
