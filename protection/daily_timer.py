from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from datetime import date
from typing import Generic, TypeVar

K = TypeVar("K")


class DailyTimerCache(Generic[K]):
    """Thread-safe daily counters with consistent rollover and lazy seeding."""

    def __init__(
        self,
        *,
        normalize: Callable[[K], K],
        load: Callable[[K], float] | None = None,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._normalize = normalize
        self._load = load
        self._today = today
        self._values: dict[K, float] = {}
        self._current_date = today()
        self._lock = threading.Lock()

    def replace(self, values: Mapping[K, float]) -> None:
        with self._lock:
            self._current_date = self._today()
            self._values = {
                self._normalize(key): float(value)
                for key, value in values.items()
            }

    def add(self, key: K, delta_s: float) -> None:
        if delta_s <= 0:
            return
        normalized = self._normalize(key)
        with self._lock:
            self._rollover_if_needed()
            current = self._seed(normalized)
            self._values[normalized] = current + delta_s

    def get(self, key: K) -> float:
        normalized = self._normalize(key)
        with self._lock:
            self._rollover_if_needed()
            return self._seed(normalized)

    def snapshot(self) -> dict[K, float]:
        with self._lock:
            self._rollover_if_needed()
            return self._values.copy()

    def _rollover_if_needed(self) -> None:
        today = self._today()
        if today != self._current_date:
            self._current_date = today
            self._values.clear()

    def _seed(self, key: K) -> float:
        if key not in self._values:
            self._values[key] = float(self._load(key)) if self._load else 0.0
        return self._values[key]
