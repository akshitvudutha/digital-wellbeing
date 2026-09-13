from __future__ import annotations

import unittest
from datetime import date

from protection.daily_timer import DailyTimerCache
from protection.timer import TimerEngine
from protection.website_timer import WebsiteTimerEngine


class MutableDate:
    def __init__(self, value: date) -> None:
        self.value = value

    def __call__(self) -> date:
        return self.value


class FakeRepository:
    def __init__(self) -> None:
        self.website_reads: list[str] = []

    def get_top_apps_for_range(self, start: date, end: date, limit: int) -> list[dict]:
        return [{"process_name": "Browser.EXE", "total_s": 25.0}]

    def get_website_usage_today(self, domain: str) -> float:
        self.website_reads.append(domain)
        return 12.0


class DailyTimerCacheTests(unittest.TestCase):
    def test_normalizes_and_accumulates(self) -> None:
        cache = DailyTimerCache[str](normalize=str.lower)
        cache.add("Browser.EXE", 2.5)
        cache.add("browser.exe", 1.5)
        self.assertEqual(cache.get("BROWSER.EXE"), 4.0)

    def test_lazy_loader_runs_once_per_key(self) -> None:
        reads: list[str] = []
        cache = DailyTimerCache[str](
            normalize=str.lower,
            load=lambda key: reads.append(key) or 8.0,
        )
        self.assertEqual(cache.get("Example.COM"), 8.0)
        cache.add("example.com", 2.0)
        self.assertEqual(cache.get("EXAMPLE.COM"), 10.0)
        self.assertEqual(reads, ["example.com"])

    def test_rollover_clears_values_and_reseeds(self) -> None:
        clock = MutableDate(date(2026, 9, 13))
        reads: list[str] = []
        cache = DailyTimerCache[str](
            normalize=str.lower,
            load=lambda key: reads.append(key) or 3.0,
            today=clock,
        )
        cache.add("example", 2.0)
        self.assertEqual(cache.get("example"), 5.0)
        clock.value = date(2026, 9, 14)
        self.assertEqual(cache.get("example"), 3.0)
        self.assertEqual(reads, ["example", "example"])

    def test_snapshot_is_a_copy_and_rolls_over(self) -> None:
        clock = MutableDate(date(2026, 9, 13))
        cache = DailyTimerCache[str](normalize=str.lower, today=clock)
        cache.add("app", 5.0)
        snapshot = cache.snapshot()
        snapshot["app"] = 99.0
        self.assertEqual(cache.get("app"), 5.0)
        clock.value = date(2026, 9, 14)
        self.assertEqual(cache.snapshot(), {})


class TimerEngineTests(unittest.TestCase):
    def test_app_timer_preserves_eager_database_seed(self) -> None:
        engine = TimerEngine(FakeRepository())
        self.assertEqual(engine.get_time("browser.exe"), 25.0)
        engine.add_time("BROWSER.EXE", 5.0)
        self.assertEqual(engine.get_time("browser.exe"), 30.0)

    def test_website_timer_preserves_lazy_database_seed(self) -> None:
        repo = FakeRepository()
        engine = WebsiteTimerEngine(repo)
        engine.add_time(" Example.COM ", 3.0)
        self.assertEqual(engine.get_time("example.com"), 15.0)
        self.assertEqual(repo.website_reads, ["example.com"])


if __name__ == "__main__":
    unittest.main()
