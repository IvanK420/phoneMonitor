"""Cache à durée de vie courte : on ne mesure que lorsqu'un client interroge, au plus une fois par TTL."""

import threading
import time
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")

_EMPTY = object()


class TTLCache(Generic[T]):
    def __init__(
        self,
        compute: Callable[[], T],
        ttl: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._compute = compute
        self._ttl = ttl
        self._clock = clock
        self._value: object = _EMPTY
        self._stamp = 0.0
        self._lock = threading.Lock()

    def get(self) -> T:
        with self._lock:
            now = self._clock()
            age = now - self._stamp
            if self._value is _EMPTY or not (0 <= age < self._ttl):
                self._value = self._compute()
                self._stamp = now
            return self._value  # type: ignore[return-value]

    __call__ = get
