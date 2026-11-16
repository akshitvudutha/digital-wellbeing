"""
deep_work.py — Structured Deep Work Sessions & Pomodoro Engine for Notch v3.6.3.

Provides:
- State machine for WORK -> BREAK -> WORK -> COMPLETED
- Preset cycles (25/5, 50/10, 90/15, custom)
- User goal tracking and persistence into deep_work_sessions table
- FocusManager enforcement during WORK phase, relaxation during BREAK phase
- Monotonic elapsed-time precision across sleep/idle
- Toast notifications and audio-friendly transition signals
- STRICT SAFETY RULE: Never executes sleep, lock, or shutdown actions.
"""
from __future__ import annotations

import enum
import json
import math
import time
from datetime import datetime, timezone
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from core.logger import logger
from database.models import DeepWorkSession
from database.repository import Repository
from notifications.notifier import Notifier
from protection.focus_manager import FocusManager


class DeepWorkPhase(enum.Enum):
    IDLE = "idle"
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    PAUSED_WORK = "paused_work"
    PAUSED_BREAK = "paused_break"
    COMPLETED = "completed"


class DeepWorkController(QObject):
    phase_changed = Signal(str)             # DeepWorkPhase.value
    tick = Signal(int, int)                 # remaining_seconds, total_phase_seconds
    interval_changed = Signal(int, int)     # current_interval, total_intervals
    session_started = Signal(str)           # goal
    session_completed = Signal(object)      # DeepWorkSession
    session_aborted = Signal()

    _instance: Optional["DeepWorkController"] = None

    @classmethod
    def instance(cls, repo: Optional[Repository] = None) -> "DeepWorkController":
        if cls._instance is None:
            if repo is None:
                repo = Repository()
            cls._instance = DeepWorkController(repo)
        return cls._instance

    def __init__(
        self,
        repo: Repository,
        focus_mgr: Optional[FocusManager] = None,
        notifier: Optional[Notifier] = None,
        parent=None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._focus_mgr = focus_mgr or FocusManager.instance(repo)
        self._notifier = notifier or Notifier()
        self._clock = clock or time.monotonic

        self._phase = DeepWorkPhase.IDLE
        self._goal = ""
        self._preset = "25/5"
        self._focus_mode = "deep"
        self._strict_mode = False

        self._work_seconds = 25 * 60
        self._break_seconds = 5 * 60
        self._total_intervals = 4
        self._current_interval = 1

        self._phase_duration_s = 0
        self._phase_remaining_s = 0
        self._phase_remaining_exact_s = 0.0
        self._monotonic_deadline = 0.0

        self._total_work_spent_s = 0.0
        self._total_break_spent_s = 0.0
        self._work_spent_before_phase = 0.0
        self._break_spent_before_phase = 0.0
        self._session_start_dt: Optional[datetime] = None
        self._subject_id: Optional[int] = None
        self._study_mode: Optional[str] = None
        self._blocked_apps: dict[str, int] = {}

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self._focus_mgr.app_blocked.connect(self._on_blocked_app)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def phase(self) -> DeepWorkPhase:
        return self._phase

    @property
    def is_active(self) -> bool:
        return self._phase not in (DeepWorkPhase.IDLE, DeepWorkPhase.COMPLETED)

    @property
    def is_paused(self) -> bool:
        return self._phase in (DeepWorkPhase.PAUSED_WORK, DeepWorkPhase.PAUSED_BREAK)

    @property
    def goal(self) -> str:
        return self._goal

    @property
    def preset(self) -> str:
        return self._preset

    @property
    def current_interval(self) -> int:
        return self._current_interval

    @property
    def total_intervals(self) -> int:
        return self._total_intervals

    @property
    def remaining_seconds(self) -> int:
        return self._phase_remaining_s

    @property
    def total_phase_seconds(self) -> int:
        return self._phase_duration_s

    @property
    def subject_id(self) -> Optional[int]:
        return self._subject_id

    @property
    def study_mode(self) -> Optional[str]:
        return self._study_mode

    @property
    def focus_manager(self) -> FocusManager:
        return self._focus_mgr

    # ------------------------------------------------------------------
    # Session Controls
    # ------------------------------------------------------------------

    def start_session(
        self,
        goal: str,
        work_minutes: int = 25,
        break_minutes: int = 5,
        total_intervals: int = 4,
        preset: str = "25/5",
        mode: str = "deep",
        strict_mode: bool = False,
        subject_id: Optional[int] = None,
        study_mode: Optional[str] = None,
    ) -> bool:
        if self.is_active:
            logger.warning("[DEEP_WORK] Cannot start: session already active.")
            return False

        if study_mode is not None and study_mode not in {
            "study", "exam_prep", "online_class", "revision", "deep_work", "reading"
        }:
            raise ValueError(f"Unsupported student study mode: {study_mode}")
        if subject_id is not None:
            subject = self._repo.get_study_subject(subject_id)
            if subject is None or not subject.is_active:
                return False

        self._goal = goal.strip() or "Focused Work"
        self._work_seconds = max(1, work_minutes) * 60
        self._break_seconds = max(1, break_minutes) * 60
        self._total_intervals = max(1, total_intervals)
        self._current_interval = 1
        self._preset = preset
        self._focus_mode = mode
        self._strict_mode = strict_mode
        self._subject_id = subject_id
        self._study_mode = study_mode
        self._blocked_apps = {}

        self._total_work_spent_s = 0.0
        self._total_break_spent_s = 0.0
        self._session_start_dt = datetime.now()

        logger.info(
            f"[DEEP_WORK] Starting session '{self._goal}' (preset={preset}, "
            f"intervals={total_intervals}, work={work_minutes}m, break={break_minutes}m)."
        )

        self.session_started.emit(self._goal)
        self._start_work_phase()
        self._timer.start()
        return True

    def pause_session(self) -> None:
        if self._phase == DeepWorkPhase.WORK:
            self._refresh_phase_clock(self._clock())
            if self._phase_remaining_exact_s <= 0:
                self._on_tick()
                return
            self._phase = DeepWorkPhase.PAUSED_WORK
            self._timer.stop()
            # Relax FocusManager while paused
            if self._focus_mgr.is_active:
                self._focus_mgr.stop_focus()
            self.phase_changed.emit(self._phase.value)
            logger.info("[DEEP_WORK] Session paused during WORK phase.")
        elif self._phase in (DeepWorkPhase.SHORT_BREAK, DeepWorkPhase.LONG_BREAK):
            self._refresh_phase_clock(self._clock())
            if self._phase_remaining_exact_s <= 0:
                self._on_tick()
                return
            self._phase = DeepWorkPhase.PAUSED_BREAK
            self._timer.stop()
            self.phase_changed.emit(self._phase.value)
            logger.info("[DEEP_WORK] Session paused during BREAK phase.")

    def resume_session(self) -> None:
        if self._phase == DeepWorkPhase.PAUSED_WORK:
            self._phase = DeepWorkPhase.WORK
            self._monotonic_deadline = self._clock() + self._phase_remaining_exact_s
            # Re-engage FocusManager
            if self._focus_mgr.is_paused:
                self._focus_mgr.resume_focus()
            elif not self._focus_mgr.is_active:
                rem_min = max(1, math.ceil(self._phase_remaining_exact_s / 60.0))
                self._focus_mgr.start_focus(
                    minutes=rem_min,
                    duration_seconds=self._phase_remaining_exact_s,
                    strict_mode=self._strict_mode,
                    mode=self._focus_mode,
                )
            self._timer.start()
            self.phase_changed.emit(self._phase.value)
            logger.info("[DEEP_WORK] Session resumed into WORK phase.")
        elif self._phase == DeepWorkPhase.PAUSED_BREAK:
            self._phase = DeepWorkPhase.SHORT_BREAK
            self._monotonic_deadline = self._clock() + self._phase_remaining_exact_s
            self._timer.start()
            self.phase_changed.emit(self._phase.value)
            logger.info("[DEEP_WORK] Session resumed into BREAK phase.")

    def finish_early(self) -> None:
        """Concludes the session gracefully, saving actual completed focused time."""
        if not self.is_active:
            return

        if not self.is_paused:
            self._refresh_phase_clock(self._clock())

        logger.info("[DEEP_WORK] Finishing session early upon user request.")
        if self._focus_mgr.is_active:
            self._focus_mgr.cancel_focus()
        self._record_session_completion(status="finished_early")
        self._teardown()

    def cancel_session(self) -> None:
        """Aborts active session without saving or saving as cancelled."""
        if not self.is_active:
            return

        if not self.is_paused:
            self._refresh_phase_clock(self._clock())

        logger.info("[DEEP_WORK] Session cancelled by user.")
        if self._focus_mgr.is_active:
            self._focus_mgr.cancel_focus()
        self._record_session_completion(status="cancelled")
        self._teardown()
        self.session_aborted.emit()

    # ------------------------------------------------------------------
    # Internal Phase Transitions
    # ------------------------------------------------------------------

    def _start_work_phase(self, start_at: Optional[float] = None) -> None:
        self._phase = DeepWorkPhase.WORK
        self._phase_duration_s = self._work_seconds
        self._phase_remaining_s = self._work_seconds
        self._phase_remaining_exact_s = float(self._work_seconds)
        self._work_spent_before_phase = self._total_work_spent_s
        self._monotonic_deadline = (self._clock() if start_at is None else start_at) + self._work_seconds

        # Activate Focus Mode
        rem_min = max(1, math.ceil(self._work_seconds / 60.0))
        self._focus_mgr.start_focus(minutes=rem_min, strict_mode=self._strict_mode, mode=self._focus_mode)

        self.phase_changed.emit(self._phase.value)
        self.interval_changed.emit(self._current_interval, self._total_intervals)
        self.tick.emit(self._phase_remaining_s, self._phase_duration_s)

        try:
            self._notifier.notify(
                f"Deep Work: Interval {self._current_interval} of {self._total_intervals}",
                f"Focus on: '{self._goal}' ({rem_min} mins). Distractions blocked.",
                duration=4,
            )
        except Exception:
            pass

    def _start_break_phase(self, start_at: Optional[float] = None) -> None:
        # Stop Focus Mode restrictions during break
        if self._focus_mgr.is_active:
            self._focus_mgr.stop_focus()

        self._phase = DeepWorkPhase.SHORT_BREAK
        self._phase_duration_s = self._break_seconds
        self._phase_remaining_s = self._break_seconds
        self._phase_remaining_exact_s = float(self._break_seconds)
        self._break_spent_before_phase = self._total_break_spent_s
        self._monotonic_deadline = (self._clock() if start_at is None else start_at) + self._break_seconds

        self.phase_changed.emit(self._phase.value)
        self.tick.emit(self._phase_remaining_s, self._phase_duration_s)

        break_min = max(1, math.ceil(self._break_seconds / 60.0))
        try:
            self._notifier.notify(
                "Work Interval Complete!",
                f"Great job on '{self._goal}'! Take a {break_min}-minute break to recharge.",
                duration=5,
            )
        except Exception:
            pass

    def _on_tick(self) -> None:
        if not self.is_active or self.is_paused:
            return

        now = self._clock()
        self._refresh_phase_clock(now)

        self.tick.emit(self._phase_remaining_s, self._phase_duration_s)

        if self._phase_remaining_s <= 0:
            self._advance_phase(completed_at=self._monotonic_deadline)
            # Carry late callback time across phase boundaries. A minimized or
            # busy UI therefore cannot extend the planned work/break sequence.
            while self.is_active and not self.is_paused and self._monotonic_deadline <= now:
                self._refresh_phase_clock(now)
                self.tick.emit(self._phase_remaining_s, self._phase_duration_s)
                self._advance_phase(completed_at=self._monotonic_deadline)

    def _refresh_phase_clock(self, now: float) -> None:
        exact_remaining = max(0.0, self._monotonic_deadline - now)
        self._phase_remaining_exact_s = exact_remaining
        self._phase_remaining_s = math.ceil(exact_remaining)
        elapsed = max(0.0, self._phase_duration_s - exact_remaining)
        if self._phase == DeepWorkPhase.WORK:
            self._total_work_spent_s = self._work_spent_before_phase + elapsed
        elif self._phase in (DeepWorkPhase.SHORT_BREAK, DeepWorkPhase.LONG_BREAK):
            self._total_break_spent_s = self._break_spent_before_phase + elapsed

    def _advance_phase(self, completed_at: Optional[float] = None) -> None:
        transition_at = self._clock() if completed_at is None else completed_at
        if self._phase == DeepWorkPhase.WORK:
            if self._current_interval >= self._total_intervals:
                # All intervals finished!
                logger.info("[DEEP_WORK] All planned intervals completed successfully.")
                self._record_session_completion(status="completed")
                self._teardown()
                try:
                    self._notifier.notify(
                        "Deep Work Session Complete!",
                        f"Congratulations! You completed all {self._total_intervals} intervals for '{self._goal}'.",
                        duration=6,
                    )
                except Exception:
                    pass
            else:
                # Transition to break
                self._start_break_phase(start_at=transition_at)
        elif self._phase in (DeepWorkPhase.SHORT_BREAK, DeepWorkPhase.LONG_BREAK):
            # Advance to next work interval
            self._current_interval += 1
            self._start_work_phase(start_at=transition_at)

    def _record_session_completion(self, status: str) -> None:
        end_dt = datetime.now()
        start_dt = self._session_start_dt or end_dt
        target_s = float(self._work_seconds * self._total_intervals)

        record = DeepWorkSession(
            goal=self._goal,
            preset=self._preset,
            target_work_s=target_s,
            actual_work_s=self._total_work_spent_s,
            actual_break_s=self._total_break_spent_s,
            intervals_completed=self._current_interval if status == "completed" else max(0, self._current_interval - 1),
            total_intervals=self._total_intervals,
            status=status,
            started_at=start_dt,
            ended_at=end_dt,
            notes=f"Mode: {self._focus_mode}, Strict: {self._strict_mode}",
            subject_id=self._subject_id,
            study_mode=self._study_mode,
            distractions_json=json.dumps(
                [
                    {"process_name": name, "count": count}
                    for name, count in sorted(self._blocked_apps.items())
                ],
                separators=(",", ":"),
            ),
        )
        try:
            sid = self._repo.record_deep_work_session(record)
            record.id = sid
            logger.info(f"[DEEP_WORK] Session logged to database with id={sid} (status={status}).")
            self.session_completed.emit(record)
        except Exception as exc:
            logger.error(f"[DEEP_WORK] Failed to record session: {exc}")

    def _on_blocked_app(self, process_name: str, _mode: str, _remaining_seconds: int) -> None:
        """Keep session-local counts for apps blocked during work intervals."""
        if self._phase != DeepWorkPhase.WORK:
            return
        process_name = (process_name or "").strip().lower()
        if process_name:
            self._blocked_apps[process_name] = self._blocked_apps.get(process_name, 0) + 1

    def _teardown(self) -> None:
        self._timer.stop()
        if self._focus_mgr.is_active:
            self._focus_mgr.stop_focus()
        self._phase = DeepWorkPhase.COMPLETED
        self.phase_changed.emit(self._phase.value)
        self._phase = DeepWorkPhase.IDLE
