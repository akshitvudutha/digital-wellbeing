"""
sleepguard.py — SleepGuard Controller Module for Digital Wellbeing Platform v2.

Integrates Win32 idle monitoring, WinRT GSMTC media playback detection,
and automated PC shutdown logic with PySide6 signals.
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
from utils.shutdown import ShutdownManager

logger = logging.getLogger(__name__)


class SleepGuardController(QObject):

    shutdown_warning_triggered = Signal(int)  # countdown_seconds
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

        self._media_engine.start()

        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            name="SleepGuardController-poll",
            daemon=True,
        )
        self._poll_thread.start()
        logger.info("SleepGuardController started (enabled=%s).", not self._paused)
        self.sleepguard_status_changed.emit(not self._paused)

    def stop(self) -> None:
        self._running = False
        self._media_engine.stop()
        if self._poll_thread and self._poll_thread.is_alive():
            # give more time for the thread to exit gracefully
            self._poll_thread.join(timeout=5.0)
            self._poll_thread = None
        logger.info("SleepGuardController stopped.")

    def set_enabled(self, enabled: bool) -> None:
        self._settings.sleepguard_enabled = enabled
        self._paused = not enabled
        if enabled:
            self._idle_fired.clear()
        logger.info("SleepGuard state set to enabled=%s", enabled)
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
        logger.info("Shutdown warning cancelled by user. Applied cooldown=%ss", cooldown)

    def execute_shutdown(self) -> bool:
        from datetime import datetime
        logger.info(f"[INSTRUMENTATION] execute_shutdown() entered at: {datetime.now().isoformat()}")
        return self._shutdown_mgr.shutdown_now()

    def force_trigger_idle(self) -> None:
        # Use an event so the polling loop sees the trigger reliably
        self._force_trigger.set()

    def _on_media_state_change(self, info: MediaInfo) -> None:
        logger.info("SleepGuard media update: playing=%s, app=%s", info.is_playing, info.display_name)
        self.media_state_changed.emit(info)

    def _poll_loop(self) -> None:
        while self._running:
            time.sleep(1.0)
            # If already triggered, paused, or not running, skip
            if not self._running or self._paused or self._idle_fired.is_set():
                continue

            idle_s = get_idle_seconds()
            timeout_s = self._settings.idle_timeout_minutes * 60
            media_timeout_s = self._settings.media_idle_timeout_minutes * 60
            mode = self._settings.shutdown_mode
            media_playing = self._media_engine.is_playing

            from tracker.idle import is_idle
            should_trigger = is_idle(
                threshold_s=timeout_s,
                current_category=None,
                is_media_playing=media_playing,
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

                logger.warning("SleepGuard idle threshold hit (idle: %.0fs, threshold: %ds). Triggering shutdown warning.", idle_s, timeout_s)
                self._idle_fired.set()

                logger.info(f"[STEP 1] About to emit shutdown_warning_triggered with countdown: {self._settings.countdown_seconds}")

                # Emit a Qt signal — the main thread will show the dialog non-blocking
                self.shutdown_warning_triggered.emit(self._settings.countdown_seconds)
