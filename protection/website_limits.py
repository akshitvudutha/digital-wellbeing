from __future__ import annotations
import json
import threading
from typing import Dict, Optional
from database.repository import Repository
from core.logger import logger

class WebsiteLimitManager:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        # Format: { browser_process: { domain: rule_dict } }
        self._limits: Dict[str, Dict[str, dict]] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        with self._lock:
            data = self._repo.get_setting("website_limits") or "{}"
            try:
                self._limits = json.loads(data)
            except json.JSONDecodeError:
                logger.error("Failed to parse website_limits from DB")
                self._limits = {}

    def _save(self) -> None:
        try:
            data = json.dumps(self._limits)
            self._repo.set_setting("website_limits", data)
        except Exception as e:
            logger.error(f"Failed to save website_limits: {e}")

    def set_limit_rule(self, browser_process: str, domain: str, rule: Optional[dict]) -> None:
        """Set a limit rule for a website. Use None to remove."""
        browser_process = browser_process.lower()
        domain = domain.lower()
        
        with self._lock:
            if browser_process not in self._limits:
                self._limits[browser_process] = {}
                
            if not rule or rule.get("limit_seconds") is None or rule.get("limit_seconds") <= 0:
                if domain in self._limits[browser_process]:
                    del self._limits[browser_process][domain]
            else:
                self._limits[browser_process][domain] = rule
                
            self._save()
            logger.info(f"Set website limit rule for {browser_process} -> {domain}: {rule}")

    def get_limit(self, browser_process: str, domain: str) -> Optional[int]:
        """Return the limit in seconds IF active today, else None."""
        browser_process = browser_process.lower()
        domain = domain.lower()
        
        with self._lock:
            browser_limits = self._limits.get(browser_process, {})
            rule = browser_limits.get(domain)
            if not rule:
                return None
            
            # Check repeat days
            import datetime
            today = datetime.datetime.today().weekday()
            if today not in rule.get("repeat_days", [0, 1, 2, 3, 4, 5, 6]):
                return None
                
            return rule.get("limit_seconds")

    def get_all_limits(self, browser_process: str) -> Dict[str, dict]:
        browser_process = browser_process.lower()
        with self._lock:
            return self._limits.get(browser_process, {}).copy()
