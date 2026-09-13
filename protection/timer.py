from __future__ import annotations

from core.logger import logger
from database.repository import Repository
from protection.daily_timer import DailyTimerCache


class TimerEngine:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._cache = DailyTimerCache[str](normalize=str.lower)
        self.sync_from_db()

    def sync_from_db(self) -> None:
        """Fetch today's active time for all applications from the database."""
        from datetime import date

        today = date.today()
        top_apps = self._repo.get_top_apps_for_range(today, today, limit=1000)
        values = {app["process_name"]: app["total_s"] for app in top_apps}
        self._cache.replace(values)
        logger.info("TimerEngine synced %d applications from local storage for %s", len(values), today)

    def add_time(self, process_name: str, delta_s: float) -> None:
        """Increment the timer for the given application."""
        self._cache.add(process_name, delta_s)

    def get_time(self, process_name: str) -> float:
        """Return today's active time for the application in seconds."""
        return self._cache.get(process_name)

    def get_all_times(self) -> dict[str, float]:
        return self._cache.snapshot()
