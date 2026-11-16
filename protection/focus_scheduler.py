"""
focus_scheduler.py — Smart Focus Scheduler engine for Notch v3.6.3.

Automates Focus Mode activation based on weekday and custom schedules.
Reuses FocusManager and WebsiteBlocker without duplicate restriction engines.
Handles:
- Weekday-specific and custom recurrence
- Same-day and overnight (cross-midnight) schedules
- Sleep, wake, and reboot reconciliation
- Monotonic elapsed-time boundaries
- Manual override suppression (prevents immediate re-trigger if user stops early)
"""
from __future__ import annotations

import math
from datetime import date, datetime, time as dtime, timedelta
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from core.logger import logger
from database.models import FocusSchedule
from database.repository import Repository
from notifications.notifier import Notifier
from protection.focus_manager import FocusManager


class FocusScheduler(QObject):
    schedule_started = Signal(object)       # FocusSchedule
    schedule_ended = Signal(object)         # FocusSchedule
    scheduler_state_changed = Signal(bool)  # is_running
    schedules_updated = Signal()

    _instance: Optional["FocusScheduler"] = None

    @classmethod
    def instance(cls, repo: Optional[Repository] = None) -> "FocusScheduler":
        if cls._instance is None:
            if repo is None:
                repo = Repository()
            cls._instance = FocusScheduler(repo)
        return cls._instance

    def __init__(
        self,
        repo: Repository,
        focus_mgr: Optional[FocusManager] = None,
        notifier: Optional[Notifier] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._focus_mgr = focus_mgr or FocusManager.instance(repo)
        self._notifier = notifier or Notifier()

        self._is_running = False
        self._active_schedule: Optional[FocusSchedule] = None
        self._active_window_end: Optional[datetime] = None
        self._suppressed_until: Dict[int, datetime] = {}  # schedule_id -> suppression end datetime

        # 15-second evaluation loop (lightweight, non-blocking)
        self._eval_timer = QTimer(self)
        self._eval_timer.setInterval(15_000)
        self._eval_timer.timeout.connect(self._on_eval_tick)

        # Hook FocusManager state change to catch manual session terminations
        self._focus_mgr.focus_state_changed.connect(self._on_focus_state_changed)

    # ------------------------------------------------------------------
    # Properties & Lifecycle
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def active_schedule(self) -> Optional[FocusSchedule]:
        return self._active_schedule

    def start(self) -> None:
        if self._is_running:
            return
        self._is_running = True
        self._eval_timer.start()
        self.scheduler_state_changed.emit(True)
        logger.info("[SCHEDULER] Smart Focus Scheduler started.")
        # Run immediate evaluation
        self.evaluate_schedules()

    def stop(self) -> None:
        if not self._is_running:
            return
        self._is_running = False
        self._eval_timer.stop()
        self._active_schedule = None
        self.scheduler_state_changed.emit(False)
        logger.info("[SCHEDULER] Smart Focus Scheduler stopped.")

    # ------------------------------------------------------------------
    # CRUD proxy helpers
    # ------------------------------------------------------------------

    def get_schedules(self, only_enabled: bool = False) -> List[FocusSchedule]:
        return self._repo.get_focus_schedules(only_enabled=only_enabled)

    def get_schedule(self, schedule_id: int) -> Optional[FocusSchedule]:
        return self._repo.get_focus_schedule(schedule_id)

    def add_or_update_schedule(self, schedule: FocusSchedule) -> int:
        sched_id = self._repo.save_focus_schedule(schedule)
        self.schedules_updated.emit()
        self.evaluate_schedules()
        return sched_id

    def delete_schedule(self, schedule_id: int) -> bool:
        if self._active_schedule and self._active_schedule.id == schedule_id:
            self._active_schedule = None
        self._suppressed_until.pop(schedule_id, None)
        ok = self._repo.delete_focus_schedule(schedule_id)
        if ok:
            self.schedules_updated.emit()
            self.evaluate_schedules()
        return ok

    def toggle_schedule(self, schedule_id: int, is_enabled: bool) -> bool:
        ok = self._repo.set_focus_schedule_enabled(schedule_id, is_enabled)
        if ok:
            if not is_enabled and self._active_schedule and self._active_schedule.id == schedule_id:
                if self._focus_mgr.is_active:
                    self._focus_mgr.stop_focus()
                self._active_schedule = None
            self.schedules_updated.emit()
            self.evaluate_schedules()
        return ok

    # ------------------------------------------------------------------
    # Schedule Window Resolution
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_schedule_window(
        sched: FocusSchedule, now: datetime
    ) -> Tuple[bool, Optional[datetime], Optional[datetime]]:
        """
        Determines whether the given schedule is currently active for 'now'.
        Returns (is_active_now, start_dt, end_dt).
        Handles both same-day windows and cross-midnight overnight windows.
        """
        try:
            sh, sm = map(int, sched.start_time.strip().split(":"))
            eh, em = map(int, sched.end_time.strip().split(":"))
        except Exception:
            return False, None, None

        days = sched.days_list
        if not days:
            return False, None, None

        today_weekday = now.weekday()  # 0=Monday, 6=Sunday

        # Case A: Same-day schedule (e.g. 09:00 -> 12:00)
        if (sh, sm) < (eh, em):
            if today_weekday in days:
                start_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
                end_dt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
                if start_dt <= now < end_dt:
                    return True, start_dt, end_dt
            return False, None, None

        # Case B: Cross-midnight overnight schedule (e.g. 22:00 -> 02:00)
        # B.1: Started today before midnight
        if today_weekday in days and (now.hour, now.minute) >= (sh, sm):
            start_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            end_dt = (now + timedelta(days=1)).replace(hour=eh, minute=em, second=0, microsecond=0)
            if start_dt <= now < end_dt:
                return True, start_dt, end_dt

        # B.2: Started yesterday before midnight and ends today early morning
        yesterday_weekday = (today_weekday - 1) % 7
        if yesterday_weekday in days and (now.hour, now.minute) < (eh, em):
            start_dt = (now - timedelta(days=1)).replace(hour=sh, minute=sm, second=0, microsecond=0)
            end_dt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
            if start_dt <= now < end_dt:
                return True, start_dt, end_dt

        return False, None, None

    # ------------------------------------------------------------------
    # Evaluation Loop
    # ------------------------------------------------------------------

    def _on_eval_tick(self) -> None:
        self.evaluate_schedules()

    def evaluate_schedules(self, current_dt: Optional[datetime] = None) -> None:
        """
        Core evaluation engine. Matches enabled schedules against current time,
        starts scheduled focus sessions, derives remaining duration across sleep/wake,
        and cleanly terminates when schedule ends.
        """
        now = current_dt or datetime.now()

        # Clean expired suppressions
        self._suppressed_until = {k: v for k, v in self._suppressed_until.items() if v > now}

        enabled_schedules = self._repo.get_focus_schedules(only_enabled=True)

        # Check if active schedule window has naturally closed
        if self._active_schedule:
            is_active, _, end_dt = self.resolve_schedule_window(self._active_schedule, now)
            if not is_active:
                logger.info(
                    "[SCHEDULER] Scheduled window ended for '%s' (id=%s).",
                    self._active_schedule.name,
                    self._active_schedule.id,
                )
                ended_sched = self._active_schedule
                self._active_schedule = None
                if self._focus_mgr.is_active:
                    self._focus_mgr.stop_focus()
                self.schedule_ended.emit(ended_sched)

        # Evaluate candidate schedules
        for sched in enabled_schedules:
            is_active, start_dt, end_dt = self.resolve_schedule_window(sched, now)
            if not is_active or not end_dt:
                continue

            # Check if this schedule is currently suppressed for this window
            if sched.id in self._suppressed_until:
                continue

            # If Focus Mode is already running
            if self._focus_mgr.is_active:
                if self._active_schedule and self._active_schedule.id == sched.id:
                    # Already running this exact schedule
                    return
                # User is in another focus session (manual or different profile), don't interrupt
                return

            # Preserve the exact wall-clock window remainder. FocusManager uses
            # a monotonic deadline once the session starts; rounding to minutes
            # here could otherwise shorten or extend the scheduled window.
            remaining_seconds = max(0.0, (end_dt - now).total_seconds())
            if remaining_seconds <= 30:
                continue  # Skip negligible remaining seconds

            remaining_minutes = max(1, math.ceil(remaining_seconds / 60.0))

            # Activate Focus Mode via existing FocusManager
            logger.info(
                "[SCHEDULER] Activating scheduled focus '%s' (mode=%s, %d mins remaining until %s).",
                sched.name,
                sched.mode,
                remaining_minutes,
                end_dt.strftime("%H:%M"),
            )
            started = self._focus_mgr.start_focus(
                minutes=remaining_minutes,
                duration_seconds=remaining_seconds,
                strict_mode=sched.strict_mode,
                mode=sched.mode,
            )
            if started:
                self._active_schedule = sched
                self._active_window_end = end_dt
                self.schedule_started.emit(sched)
                try:
                    self._notifier.notify(
                        "Scheduled Focus Started",
                        f"{sched.name} ({sched.mode.title()}) is now active until {sched.end_time}.",
                        duration=5,
                    )
                except Exception as exc:
                    logger.debug("[SCHEDULER] Notification failed: %s", exc)
                return

    # ------------------------------------------------------------------
    # FocusManager Integration
    # ------------------------------------------------------------------

    def _on_focus_state_changed(self, is_active: bool) -> None:
        """
        Catches when Focus Mode stops. If the user manually finishes early or
        stops an active scheduled session, suppress re-triggering until the window ends.
        """
        if not is_active and self._active_schedule:
            if self._active_window_end:
                self._suppressed_until[self._active_schedule.id] = self._active_window_end
                logger.info(
                    "[SCHEDULER] User manually ended scheduled focus '%s'. Suppressing re-trigger until %s.",
                    self._active_schedule.name,
                    self._active_window_end.strftime("%H:%M"),
                )
            self._active_schedule = None
            self._active_window_end = None
