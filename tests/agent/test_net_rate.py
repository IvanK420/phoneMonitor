from agent.net_rate import NetCounters, net_rate


def test_rate_in_kilobits_per_second():
    prev = NetCounters(bytes_recv=0, bytes_sent=0)
    cur = NetCounters(bytes_recv=300_000, bytes_sent=21_250)

    # 300 000 o en 2 s = 150 000 o/s = 1 200 kb/s ; 21 250 o en 2 s = 85 kb/s
    assert net_rate(prev, cur, 2.0) == {"down_kbps": 1200, "up_kbps": 85}


def test_rate_is_rounded_to_integer():
    prev = NetCounters(0, 0)
    cur = NetCounters(bytes_recv=1000, bytes_sent=10)

    rate = net_rate(prev, cur, 3.0)

    assert rate == {"down_kbps": 3, "up_kbps": 0}
    assert all(isinstance(v, int) for v in rate.values())


def test_zero_interval_gives_zero():
    c = NetCounters(1000, 1000)

    assert net_rate(c, NetCounters(5000, 5000), 0) == {"down_kbps": 0, "up_kbps": 0}


def test_negative_interval_gives_zero():
    assert net_rate(NetCounters(0, 0), NetCounters(5000, 5000), -1.0) == {
        "down_kbps": 0,
        "up_kbps": 0,
    }


def test_counter_going_backwards_is_never_negative():
    # Remise à zéro du compteur (interface réinitialisée, débordement 32 bits…)
    prev = NetCounters(bytes_recv=10_000, bytes_sent=100)
    cur = NetCounters(bytes_recv=500, bytes_sent=1100)

    assert net_rate(prev, cur, 1.0) == {"down_kbps": 0, "up_kbps": 8}


def test_missing_previous_sample_gives_zero():
    assert net_rate(None, NetCounters(5000, 5000), 1.0) == {"down_kbps": 0, "up_kbps": 0}
