from agent.cache import TTLCache


class FakeClock:
    def __init__(self, t: float = 1000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


class CountingCompute:
    def __init__(self):
        self.calls = 0

    def __call__(self) -> int:
        self.calls += 1
        return self.calls


def test_two_calls_within_ttl_measure_once():
    clock, compute = FakeClock(), CountingCompute()
    cache = TTLCache(compute, ttl=1.0, clock=clock)

    first = cache.get()
    clock.t += 0.9
    second = cache.get()

    assert compute.calls == 1
    assert first == second == 1


def test_call_after_ttl_measures_again():
    clock, compute = FakeClock(), CountingCompute()
    cache = TTLCache(compute, ttl=1.0, clock=clock)

    cache.get()
    clock.t += 1.1
    value = cache.get()

    assert compute.calls == 2
    assert value == 2


def test_clock_going_backwards_triggers_new_measure():
    clock, compute = FakeClock(), CountingCompute()
    cache = TTLCache(compute, ttl=1.0, clock=clock)

    cache.get()
    clock.t -= 5
    cache.get()

    assert compute.calls == 2


def test_cache_is_callable_like_its_compute():
    cache = TTLCache(CountingCompute(), ttl=1.0, clock=FakeClock())

    assert cache() == 1
