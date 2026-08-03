from __future__ import annotations
import threading
from datetime import date
from typing import Dict
from database.repository import Repository
from core.logger import logger

class WebsiteTimerEngine:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._timers: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._current_date = date.today()

    def add_time(self, domain: str, delta_s: float) -> None:
        if delta_s <= 0 or not domain:
            return
            
        today = date.today()
        
        with self._lock:
            if today != self._current_date:
                self._current_date = today
                self._timers.clear()
                
            current = self._timers.get(domain, 0.0)
            # If not in cache, seed from DB
            if domain not in self._timers:
                current = self._repo.get_website_usage_today(domain)
                
            self._timers[domain] = current + delta_s

    def get_time(self, domain: str) -> float:
        if not domain:
            return 0.0
        with self._lock:
            if self._current_date != date.today():
                return 0.0
            
            if domain in self._timers:
                return self._timers[domain]
                
            db_time = self._repo.get_website_usage_today(domain)
            self._timers[domain] = db_time
            return db_time

    def get_all_times(self) -> Dict[str, float]:
        with self._lock:
            return self._timers.copy()
