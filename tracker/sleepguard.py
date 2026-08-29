"""
sleepguard.py — SleepGuard Controller Module for Digital Wellbeing Platform v2.4.

Integrates Win32 idle monitoring, WinRT GSMTC media playback detection,
and automated PC power action logic with PySide6 signals.

v2.4 changes:
- Multi-action support (shutdown/sleep/hibernate/lock/cancel)
- Safety guards preventing invalid/accidental destructive actions
- Minimum countdown floor (10 seconds)
- Structured logging throughout the expiry path
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from PySide6.QtCore import QObject, Signal

from settings.manager import SettingsManager
from tracker.idle import get_idle_seconds
from tracker.media import MediaDetectionEngine, MediaInfo
from utils.shutdown import ShutdownManager, MIN_COUNTDOWN_SECONDS, VALID_ACTIONS

logger = logging.getLogger(__name__)


class SleepGuardController(QObject):

    # Signal carries (countdown_seconds, action_type)
    shutdown_warning_triggered = Signal(int, str)
    media_state_changed = Signal(object)      # MediaInfo
    sleepguard_status_changed = Signal(bool)  # active status
    programmatic_shutdown_cancelled = Signal()  # emitted when a cancel is performed programmatically

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = SettingsManager()
        self._shutdown_mgr = ShutdownManager()

        self._media_engine = MediaDetectionEngine(
            poll_interval=2.0,
            on_state_change=self._on_media_state_change,
        )

        self._running = False
        self._paused = False
        # Use threading.Event objects for safe cross-thread signaling
        self._idle_fired = threading.Event()
        self._force_trigger = threading.Event()
        # Protects transient cancel cooldown timestamp
        self._cancel_block_until = 0.0
        self._cancel_lock = threading.Lock()
        self._poll_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._paused = not self._settings.sleepguard_enabled
        self._idle_fired.clear()
        self._force_trigger.clear()
        self._waiting_for_first_activity = True

        self._media_engine.start()

        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            name="SleepGuardController-poll",
            daemon=True,
        )
        self._poll_thread.start()
        logger.info(
            "[SLEEPGUARD] Controller started (enabled=%s, action=%s, countdown=%ds).",
            not self._paused,
            self._settings.sleepguard_action,
            self._settings.countdown_seconds,
        )
        self.sleepguard_status_changed.emit(not self._paused)

    def stop(self) -> None:
        self._running = False
        self._media_engine.stop()
        if self._poll_thread and self._poll_thread.is_alive():
            # give more time for the thread to exit gracefully
            self._poll_thread.join(timeout=5.0)
            self._poll_thread = None
        logger.info("[SLEEPGUARD] Controller stopped.")

    def set_enabled(self, enabled: bool) -> None:
        self._settings.sleepguard_enabled = enabled
        self._paused = not enabled
        if enabled:
            self._idle_fired.clear()
        logger.info("[SLEEPGUARD] State set to enabled=%s", enabled)
        self.sleepguard_status_changed.emit(enabled)

    @property
    def is_enabled(self) -> bool:
        return self._settings.sleepguard_enabled

    @property
    def current_media(self) -> MediaInfo:
        return self._media_engine.current

    def cancel_warning(self) -> None:
        # Clear the idle-fired event so the poll loop can resume normal operation
        try:
            self._idle_fired.clear()
        except Exception:
            pass
        # Prevent immediate retrigger for a short cooldown window
        cooldown = 30.0  # seconds
        try:
            with self._cancel_lock:
                self._cancel_block_until = time.time() + cooldown
        except Exception:
            pass
        self._shutdown_mgr.cancel_shutdown()
        try:
            # notify UI/dialogs that a cancel occurred so they can stop any active countdown
            self.programmatic_shutdown_cancelled.emit()
        except Exception:
            pass
        logger.info("[SLEEPGUARD] Warning cancelled by user. Applied cooldown=%ss", cooldown)
        logger.info("SLEEPGUARD_TRIGGER ACTION=CANCEL IDLE_SECONDS=0 MEDIA_STATE=%s QUICK_TEST=N/A COUNTDOWN=N/A USER_INTERRUPTION=TRUE POWER_RESULT=N/A ERROR_CODE=0 FINAL_RESULT=CANCELLED", self._media_engine.is_playing)

    def execute_power_action(self, action: str = "") -> bool:
        """Execute the configured (or specified) power action with safety validation.
        
        This is the single, authoritative entry point for all SleepGuard power actions.
        If action is empty, reads from settings.
        """
        from datetime import datetime

        if not action:
            action = self._settings.sleepguard_action

        action = action.lower().strip()
        ts = datetime.now().isoformat()

        logger.info("[SLEEPGUARD] execute_power_action() entered at %s with action='%s'", ts, action)

        # Safety guard: validate action, fallback to lock
        if not ShutdownManager.validate_action(action):
            logger.warning(
                "[SLEEPGUARD] SAFETY GUARD: Unknown or invalid action '%s'. "
                "Defaulting to 'lock' for safety.", action
            )
            action = "lock"

        # Safety guard: check if condition is still satisfied (user didn't move mouse)
        # Check standard idle timeout without media mode complexities, just to see if user is actually away.
        import os
        from tracker.idle import get_idle_seconds
        idle_s = get_idle_seconds()
        timeout_s = self._settings.idle_timeout_minutes * 60
        qt_env = os.getenv("NYW_QUICK_TEST")
        is_quick_test = bool(qt_env and qt_env.isdigit())
        if is_quick_test:
            timeout_s = int(qt_env)
            
        if idle_s < (timeout_s * 0.5): # Use a generous 50% buffer to avoid race conditions but catch recent activity
            logger.error(
                "[SLEEPGUARD] SAFETY GUARD: User became active during countdown. "
                "Current idle=%.1f, required=%d. Cancelling execution.", idle_s, timeout_s
            )
            logger.info("SLEEPGUARD_TRIGGER ACTION=%s IDLE_SECONDS=%.1f MEDIA_STATE=%s QUICK_TEST=%s COUNTDOWN=0 USER_INTERRUPTION=TRUE POWER_RESULT=N/A ERROR_CODE=0 FINAL_RESULT=CANCELLED", action, idle_s, self._media_engine.is_playing, "TRUE" if is_quick_test else "FALSE")
            return False

        # Safety guard: log the final action before execution
        logger.warning(
            "[SLEEPGUARD] EXECUTING power action '%s' at %s. "
            "Configured action: '%s'.",
            action, ts, self._settings.sleepguard_action,
        )
        
        result = self._shutdown_mgr.execute_action(action)
        logger.info("SLEEPGUARD_TRIGGER ACTION=%s IDLE_SECONDS=%.1f MEDIA_STATE=%s QUICK_TEST=%s COUNTDOWN=0 USER_INTERRUPTION=FALSE POWER_RESULT=%s ERROR_CODE=0 FINAL_RESULT=%s", action, idle_s, self._media_engine.is_playing, "TRUE" if is_quick_test else "FALSE", "SUCCESS" if result else "FAILED", "EXECUTED" if result else "FAILED")
        return result

    # Legacy backward-compatible method
    def execute_shutdown(self) -> bool:
        """Legacy method — routes through execute_power_action with configured action."""
        return self.execute_power_action()

    def force_trigger_idle(self) -> None:
        # Use an event so the polling loop sees the trigger reliably
        self._force_trigger.set()

    def _on_media_state_change(self, info: MediaInfo) -> None:
        logger.info("[SLEEPGUARD] Media update: playing=%s, app=%s", info.is_playing, info.display_name)
        self.media_state_changed.emit(info)

    def _poll_loop(self) -> None:
        import time
        start_time = time.time()
        while self._running:
            time.sleep(1.0)
            # If already triggered, paused, or not running, skip
            if not self._running or self._paused or self._idle_fired.is_set():
                continue

            # Startup grace period: do not trigger in the first 30 seconds
            if time.time() - start_time < 30.0:
                continue

            idle_s = get_idle_seconds()
            if getattr(self, "_waiting_for_first_activity", False):
                if idle_s < 2.0:
                    self._waiting_for_first_activity = False
                    logger.info("[SLEEPGUARD] User activity detected. SleepGuard is now armed.")
                else:
                    continue

            timeout_s = self._settings.idle_timeout_minutes * 60
            
            # Quick Test Override via Env Var (Developer Only)
            import os
            qt_env = os.getenv("NYW_QUICK_TEST")
            is_quick_test = False
            if qt_env and qt_env.isdigit():
                timeout_s = int(qt_env)
                is_quick_test = True
                
            media_timeout_s = self._settings.media_idle_timeout_minutes * 60
            mode = self._settings.shutdown_mode
            media_playing = self._media_engine.is_playing
            
            # Check if the current foreground app is fullscreen
            is_fullscreen = False
            try:
                from tracker.foreground import get_foreground_app
                fg = get_foreground_app()
                if fg and getattr(fg, "is_fullscreen", False):
                    is_fullscreen = True
            except Exception:
                pass

            from tracker.idle import is_idle
            should_trigger = is_idle(
                threshold_s=timeout_s,
                current_category=None,
                is_media_playing=(media_playing or is_fullscreen),
                mode=mode,
                media_timeout_s=media_timeout_s,
            ) or self._force_trigger.is_set()

            # Respect any recent user-cancel cooldown to avoid immediate retrigger
            try:
                with self._cancel_lock:
                    if time.time() < self._cancel_block_until:
                        # still in cooldown window
                        continue
            except Exception:
                pass

            if should_trigger:
                # consume force trigger if present
                if self._force_trigger.is_set():
                    self._force_trigger.clear()

                # Read configured action and countdown
                action = self._settings.sleepguard_action
                raw_countdown = self._settings.countdown_seconds

                # Safety guard: enforce minimum countdown floor
                countdown = max(raw_countdown, MIN_COUNTDOWN_SECONDS)
                if countdown != raw_countdown:
                    logger.warning(
                        "[SLEEPGUARD] Countdown %ds was below minimum floor %ds. Clamped to %ds.",
                        raw_countdown, MIN_COUNTDOWN_SECONDS, countdown,
                    )

                logger.warning(
                    "[SLEEPGUARD] Idle threshold hit (idle: %.0fs, threshold: %ds). "
                    "Triggering warning. action='%s', countdown=%ds.",
                    idle_s, timeout_s, action, countdown,
                )
                self._idle_fired.set()
                
                logger.info("SLEEPGUARD_TRIGGER ACTION=%s IDLE_SECONDS=%.1f MEDIA_STATE=%s QUICK_TEST=%s COUNTDOWN=%d USER_INTERRUPTION=FALSE POWER_RESULT=PENDING ERROR_CODE=0 FINAL_RESULT=PENDING", action, idle_s, media_playing, "TRUE" if is_quick_test else "FALSE", countdown)

                logger.info(
                    "[SLEEPGUARD] Emitting shutdown_warning_triggered(countdown=%d, action='%s')",
                    countdown, action,
                )

                # Emit a Qt signal — the main thread will show the dialog non-blocking
                self.shutdown_warning_triggered.emit(countdown, action)
