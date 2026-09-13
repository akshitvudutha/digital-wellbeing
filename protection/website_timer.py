from __future__ import annotations

from database.repository import Repository
from protection.daily_timer import DailyTimerCache


class WebsiteTimerEngine:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._cache = DailyTimerCache[str](
            normalize=lambda domain: domain.strip().lower(),
            load=self._repo.get_website_usage_today,
        )

    def add_time(self, domain: str, delta_s: float) -> None:
        if not domain:
            return
        self._cache.add(domain, delta_s)

    def get_time(self, domain: str) -> float:
        if not domain:
            return 0.0
        return self._cache.get(domain)

    def get_all_times(self) -> dict[str, float]:
        return self._cache.snapshot()
