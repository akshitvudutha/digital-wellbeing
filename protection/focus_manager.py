"""
focus_manager.py — Focus Mode enforcement engine for NYW.

Enforcement model:
  - ALLOWLIST + DEFAULT-DENY: every browser domain not in the allowlist is blocked.
  - Empty allowlist  → ALL browser domains blocked.
  - Scans ALL open browser windows every second (not just the foreground window).
  - One overlay per browser HWND; overlays are independent.
  - No hosts/DNS/proxy modifications.

Documented limitation:
  Pages already loaded before Focus started (or during the brief navigation moment)
  are not retroactively unloaded.  Enforcement is overlay-based, not network-level.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import threading
from typing import Dict, List, Optional

import win32gui
import win32process
import psutil

from PySide6.QtCore import QObject, Signal, QTimer
from core.logger import logger
from database.repository import Repository
from protection.pin import PINManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# FocusManager
# ---------------------------------------------------------------------------

class FocusManager(QObject):
    focus_state_changed = Signal(bool)   # is_active
    tick = Signal(int)                   # seconds remaining
    focus_completed = Signal()

    _instance: Optional["FocusManager"] = None

    @classmethod
    def instance(cls, repo: Optional[Repository] = None) -> "FocusManager":
        if cls._instance is None:
            if repo is None:
                repo = Repository()
            cls._instance = FocusManager(repo)
        return cls._instance

    def __init__(self, repo: Repository, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._pin_manager = PINManager(repo)
        self._is_active = False
        self._is_strict = False
        self._seconds_remaining = 0

        self._blocked_apps: List[str] = []
        self._app_block_response: str = "warn_close"

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        stored_apps = self._repo.get_setting("focus_blocked_apps")
        if stored_apps:
            self._blocked_apps = [a.strip().lower() for a in stored_apps.split(",") if a.strip()]

        stored_response = self._repo.get_setting("focus_app_block_response")
        if stored_response:
            self._app_block_response = stored_response

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def is_strict(self) -> bool:
        return self._is_strict

    @property
    def blocked_apps(self) -> List[str]:
        return list(self._blocked_apps)

    @property
    def app_block_response(self) -> str:
        return self._app_block_response

    @property
    def seconds_remaining(self) -> int:
        return self._seconds_remaining

    # ------------------------------------------------------------------
    # Allowlist persistence
    # ------------------------------------------------------------------

    def save_blocked_apps(self, apps: List[str]) -> None:
        self._blocked_apps = [a.strip().lower() for a in apps if a.strip()]
        self._repo.set_setting("focus_blocked_apps", ",".join(self._blocked_apps))

    def save_app_block_response(self, response: str) -> None:
        self._app_block_response = response
        self._repo.set_setting("focus_app_block_response", response)

    # ------------------------------------------------------------------
    # Session control
    # ------------------------------------------------------------------

    def start_focus(self, minutes: int, strict_mode: bool = False) -> bool:
        if self._is_active:
            return False

        if strict_mode and not self._pin_manager.is_enabled():
            logger.warning("[FOCUS] Cannot start strict mode: PIN is not configured.")
            return False

        self._is_active = True
        self._is_strict = strict_mode
        self._seconds_remaining = minutes * 60

        logger.info(
            f"[FOCUS] Session started. minutes={minutes}, strict={strict_mode}, "
            f"allowlist={self._allowlist or '(empty → all blocked)'}"
        )

        # Run an immediate enforcement scan before the first timer tick
        self._run_enforcement_scan()

        self._timer.start()
        self.focus_state_changed.emit(True)
        return True

    def stop_focus(self, provided_pin: str = "") -> bool:
        if not self._is_active:
            return True

        if self._is_strict:
            if not self._pin_manager.verify_pin(provided_pin):
                logger.warning("[FOCUS] Stop denied: Invalid PIN.")
                return False

        return self._do_stop()

    def stop_focus_after_pin_dialog(self) -> bool:
        """
        Stop unconditionally after PinDialog has already verified the PIN.
        MUST only be called from code that received QDialog.Accepted from PinDialog.
        """
        if not self._is_active:
            return True
        return self._do_stop()

    def _do_stop(self) -> bool:
        """Internal teardown — reset state."""
        self._is_active = False
        self._is_strict = False
        self._seconds_remaining = 0
        self._timer.stop()
        self.focus_state_changed.emit(False)
        logger.info("[FOCUS] Session stopped.")
        return True

    # ------------------------------------------------------------------
    # Timer tick
    # ------------------------------------------------------------------

    def _on_tick(self) -> None:
        if self._seconds_remaining > 0:
            self._seconds_remaining -= 1
            self.tick.emit(self._seconds_remaining)
            self._run_enforcement_scan()
        else:
            # Session completed naturally
            self._is_active = False
            self._is_strict = False
            self._timer.stop()
            self.focus_state_changed.emit(False)
            self.focus_completed.emit()
            logger.info("[FOCUS] Session completed naturally.")

    # ------------------------------------------------------------------
    # Enforcement scan — called every tick
    # ------------------------------------------------------------------

    def _run_enforcement_scan(self) -> None:
        """
        Scan foreground app.
        If it's in the blocked apps list (strict mode), handle it.
        """
        try:
            # Web blocking has been permanently disabled in v3.1.5 because true per-tab enforcement
            # requires a browser extension, which has been forbidden by architectural constraints.

            # App blocking (strict mode only)
            if self._is_strict:
                self._check_app_blocks()

        except Exception as exc:
            logger.debug(f"[FOCUS] Enforcement scan error: {exc}")

    def _check_app_blocks(self) -> None:
        """Block foreground apps that are in the blocked_apps list (strict mode)."""
        SYSTEM_SAFE = {
            "explorer.exe", "taskmgr.exe", "systemsettings.exe",
            "digitalwellbeing.exe", "searchapp.exe",
            "startmenuexperiencehost.exe", "dwm.exe",
        }
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return
            from tracker.foreground import _get_real_window_pid
            pid = _get_real_window_pid(hwnd)
            if not pid:
                return
            p = psutil.Process(pid)
            p_name = p.name().lower()
            if p_name in SYSTEM_SAFE:
                return
            if any(a in p_name for a in self._blocked_apps):
                self._handle_blocked_app(p, p_name)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Legacy Overlay Management (Removed)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # App blocking handler
    # ------------------------------------------------------------------

    def _handle_blocked_app(self, proc, p_name: str) -> None:
        try:
            if self._app_block_response == "close":
                logger.info(f"[FOCUS] Terminating blocked app {p_name}.")
                proc.kill()
            else:
                # warn or warn_close — just log for now (app overlay is a separate feature)
                logger.debug(f"[FOCUS] Blocked app in foreground: {p_name}")
        except Exception as exc:
            logger.warning(f"[FOCUS] Failed to handle blocked app {p_name}: {exc}")
