from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Dict, Set

from database.repository import Repository
from core.logger import logger
from protection.timer import TimerEngine
from protection.limits import LimitManager
from protection.pin import PINManager
from protection.notifications import NotificationManager
from protection.process import ProcessController


class ProtectionManager:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._timer = TimerEngine(repo)
        self._limits = LimitManager(repo)
        self._pin = PINManager(repo)
        self._notifications = NotificationManager()
        
        self._overrides: Dict[str, datetime] = {}
        self._warnings_sent: Dict[str, Set[int]] = {}  # process_name -> set of warning thresholds hit (e.g. 10, 5, 1)
        self._lock = threading.Lock()

    @property
    def timer(self) -> TimerEngine:
        return self._timer

    @property
    def limits(self) -> LimitManager:
        return self._limits
        
    @property
    def pin(self) -> PINManager:
        return self._pin

    @property
    def notifications(self) -> NotificationManager:
        return self._notifications

    def tick(self, process_name: str, delta_s: float) -> None:
        """Called by TrackingManager every tick."""
        if not process_name:
            return
            
        process_name = process_name.lower()
        self._timer.add_time(process_name, delta_s)
        
        rule = self._limits.get_limit_rule(process_name)
        limit_s = self._limits.get_limit(process_name)
        if limit_s is None or not rule:
            return
            
        elapsed_s = self._timer.get_time(process_name)
        
        # Check override
        with self._lock:
            override_until = self._overrides.get(process_name)
            if override_until and datetime.now() < override_until:
                # Override active, skip enforcement
                return

        remaining_s = limit_s - elapsed_s
        
        # Check warnings
        if remaining_s > 0:
            remaining_mins = int(remaining_s // 60)
            warning_list = rule.get("notifications", [15, 10, 5, 1])
            if remaining_mins in warning_list:
                with self._lock:
                    sent = self._warnings_sent.setdefault(process_name, set())
                    if remaining_mins not in sent:
                        sent.add(remaining_mins)
                        self._notifications.send_warning(process_name, remaining_mins)
            return
            
        # Limit Reached!
        expire_action = rule.get("on_expire", "lock")
        
        with self._lock:
            # 1. Send system notification toast only once
            sent = self._warnings_sent.setdefault(process_name, set())
            if 0 not in sent:
                sent.add(0)
                self._notifications.send_warning(process_name, 0)
                
            # 2. Continuous Enforcement (Every Tick)
            # Since there is no active override, we forcefully close the app.
            # This ensures that even if the dialog is dismissed, the app remains blocked.
            self.force_close(process_name)
            
            # 3. Trigger the UI dialog (UI handles debouncing active dialogs)
            if expire_action != "close":
                self._notifications.trigger_lock_dialog(process_name, limit_s)

    def force_close(self, process_name: str) -> None:
        """Called by UI when user clicks 'Close App'"""
        ProcessController.close_process(process_name)
        
    def add_override(self, process_name: str, duration_minutes: int) -> None:
        """Called by UI when PIN is entered correctly."""
        process_name = process_name.lower()
        with self._lock:
            if duration_minutes <= 0:
                # Unlimited for today (we can just set it to end of day)
                now = datetime.now()
                end_of_day = datetime(now.year, now.month, now.day) + timedelta(days=1)
                self._overrides[process_name] = end_of_day
            else:
                self._overrides[process_name] = datetime.now() + timedelta(minutes=duration_minutes)
                
            # Clear warnings so they can re-trigger if they hit the limit again tomorrow
            # (Actually overrides extend usage, we might want to reset warnings if we want to warn them again)
            self._warnings_sent.pop(process_name, None)
            logger.info(f"ProtectionManager: Override added for {process_name} ({duration_minutes}m)")

    def has_active_override(self, process_name: str) -> bool:
        process_name = process_name.lower()
        with self._lock:
            override_until = self._overrides.get(process_name)
            if override_until and datetime.now() < override_until:
                return True
        return False
