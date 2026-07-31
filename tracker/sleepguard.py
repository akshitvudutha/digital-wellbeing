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
        self._idle_fired = False
        self._force_trigger = False
        self._poll_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._paused = not self._settings.sleepguard_enabled
        self._idle_fired = False

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
            self._poll_thread.join(timeout=2.0)
            self._poll_thread = None
        logger.info("SleepGuardController stopped.")

    def set_enabled(self, enabled: bool) -> None:
        self._settings.sleepguard_enabled = enabled
        self._paused = not enabled
        if enabled:
            self._idle_fired = False
        logger.info("SleepGuard state set to enabled=%s", enabled)
        self.sleepguard_status_changed.emit(enabled)

    @property
    def is_enabled(self) -> bool:
        return self._settings.sleepguard_enabled

    @property
    def current_media(self) -> MediaInfo:
        return self._media_engine.current

    def cancel_warning(self) -> None:
        self._idle_fired = False
        self._shutdown_mgr.cancel_shutdown()
        logger.info("Shutdown warning cancelled by user.")

    def execute_shutdown(self) -> bool:
        from datetime import datetime
        logger.info(f"[INSTRUMENTATION] execute_shutdown() entered at: {datetime.now().isoformat()}")
        return self._shutdown_mgr.shutdown_now()

    def force_trigger_idle(self) -> None:
        self._force_trigger = True

    def _on_media_state_change(self, info: MediaInfo) -> None:
        logger.info("SleepGuard media update: playing=%s, app=%s", info.is_playing, info.display_name)
        self.media_state_changed.emit(info)

    def _poll_loop(self) -> None:
        while self._running:
            time.sleep(1.0)
            if not self._running or self._paused or self._idle_fired:
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
            ) or self._force_trigger

            if should_trigger:
                self._force_trigger = False
                logger.warning("SleepGuard idle threshold hit (idle: %.0fs, threshold: %ds). Triggering shutdown warning.", idle_s, timeout_s)
                self._idle_fired = True
                
                logger.info(f"[STEP 1] About to emit shutdown_warning_triggered with countdown: {self._settings.countdown_seconds}")
                
                self.shutdown_warning_triggered.emit(self._settings.countdown_seconds)
