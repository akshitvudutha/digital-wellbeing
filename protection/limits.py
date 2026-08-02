from __future__ import annotations

import json
import threading
from typing import Dict, Optional

from database.repository import Repository
from core.logger import logger

class LimitManager:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._limits: Dict[str, int] = {} # process_name (lower) -> limit_seconds
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        with self._lock:
            data = self._repo.get_setting("app_limits") or "{}"
            try:
                self._limits = json.loads(data)
                # Ensure all keys are lowercase
                self._limits = {k.lower(): v for k, v in self._limits.items()}
            except json.JSONDecodeError:
                logger.error("Failed to parse app_limits from DB")
                self._limits = {}

    def _save(self) -> None:
        try:
            data = json.dumps(self._limits)
            self._repo.set_setting("app_limits", data)
        except Exception as e:
            logger.error(f"Failed to save app_limits: {e}")

    def set_limit(self, process_name: str, limit_seconds: Optional[int]) -> None:
        """Set a limit in seconds for a process. Use None to remove."""
        process_name = process_name.lower()
        with self._lock:
            if limit_seconds is None or limit_seconds <= 0:
                if process_name in self._limits:
                    del self._limits[process_name]
            else:
                self._limits[process_name] = limit_seconds
            self._save()
            logger.info(f"Set limit for {process_name}: {limit_seconds}s")

    def get_limit(self, process_name: str) -> Optional[int]:
        """Return the limit in seconds, or None if unlimited."""
        process_name = process_name.lower()
        with self._lock:
            return self._limits.get(process_name)

    def get_all_limits(self) -> Dict[str, int]:
        with self._lock:
            return self._limits.copy()
