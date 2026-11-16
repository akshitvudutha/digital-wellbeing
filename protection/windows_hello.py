"""
windows_hello.py — Windows Hello authentication bridge for NYW App Locker.

Wraps the WinRT UserConsentVerifier API so availability and verification calls
never block the Qt main thread. Callers use Qt signals for results.

Usage (Qt main thread):
    from protection.windows_hello import WindowsHelloAuth, HelloResult, HelloAvailability

    auth = WindowsHelloAuth()
    auth.availability_ready.connect(on_availability)
    auth.request_availability()                # non-blocking

    def on_result(result: HelloResult) -> None:
        if result == HelloResult.VERIFIED:
            ...

    auth.result_ready.connect(on_result)
    auth.request_verification("Unlock Brave Browser")  # non-blocking
"""
from __future__ import annotations

import asyncio
import threading
from enum import IntEnum
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from core.logger import logger


# ── Public enums ─────────────────────────────────────────────────────────────

class HelloAvailability(IntEnum):
    AVAILABLE         = 0   # Windows Hello configured and ready
    UNAVAILABLE       = 1   # No biometric hardware or Hello not set up
    NOT_CONFIGURED    = 2   # Hardware present but user hasn't enrolled
    ERROR             = 99  # Unexpected error during availability check


class HelloResult(IntEnum):
    VERIFIED          = 0   # Authentication succeeded
    CANCELED          = 1   # User canceled
    FAILED            = 2   # Authentication failed (wrong biometric/PIN)
    UNAVAILABLE       = 3   # Device not present
    NOT_CONFIGURED    = 4   # Not configured for this user
    DEVICE_BUSY       = 5   # Device busy, try again
    ERROR             = 99  # Unexpected error


# ── Internal worker ───────────────────────────────────────────────────────────

class _HelloWorker(QThread):
    """Runs a single Windows Hello verification request asynchronously.

    Emits result_ready(HelloResult) on the Qt main thread when complete.
    """
    result_ready = Signal(int)  # HelloResult value

    def __init__(self, message: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._message = message

    def run(self) -> None:
        result = HelloResult.ERROR
        try:
            from winrt.windows.security.credentials.ui import (
                UserConsentVerifier,
                UserConsentVerificationResult,
            )

            async def _verify() -> HelloResult:
                verification = await UserConsentVerifier.request_verification_async(
                    self._message
                )
                mapping = {
                    UserConsentVerificationResult.VERIFIED:              HelloResult.VERIFIED,
                    UserConsentVerificationResult.CANCELED:              HelloResult.CANCELED,
                    UserConsentVerificationResult.DEVICE_NOT_PRESENT:    HelloResult.UNAVAILABLE,
                    UserConsentVerificationResult.NOT_CONFIGURED_FOR_USER: HelloResult.NOT_CONFIGURED,
                    UserConsentVerificationResult.DISABLED_BY_POLICY:    HelloResult.UNAVAILABLE,
                    UserConsentVerificationResult.DEVICE_BUSY:           HelloResult.DEVICE_BUSY,
                    UserConsentVerificationResult.RETRIES_EXHAUSTED:     HelloResult.FAILED,
                }
                return mapping.get(verification, HelloResult.ERROR)

            result = asyncio.run(_verify())

        except ModuleNotFoundError:
            logger.warning("winrt-Windows.Security.Credentials.UI not installed; Windows Hello unavailable.")
            result = HelloResult.UNAVAILABLE
        except Exception as exc:
            logger.error("WindowsHello verification error: %s", exc)
            result = HelloResult.ERROR

        self.result_ready.emit(int(result))


# ── Public API ────────────────────────────────────────────────────────────────

class WindowsHelloAuth(QObject):
    """Thread-safe Windows Hello authentication helper.

    All public methods are safe to call from the Qt main thread.
    The ``result_ready`` signal is emitted on the Qt main thread.
    """

    result_ready = Signal(int)  # HelloResult value; connect before calling request_verification()
    availability_ready = Signal(int)  # HelloAvailability value from request_availability()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._worker: Optional[_HelloWorker] = None
        self._availability_thread: Optional[threading.Thread] = None
        self._availability_lock = threading.Lock()

    @staticmethod
    def _map_availability(availability, available_value, not_configured_value) -> HelloAvailability:
        """Translate WinRT's enum without requiring a live biometric device."""
        if availability == available_value:
            return HelloAvailability.AVAILABLE
        if availability == not_configured_value:
            return HelloAvailability.NOT_CONFIGURED
        return HelloAvailability.UNAVAILABLE

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    def check_availability(self) -> HelloAvailability:
        """Check whether Windows Hello is available on this machine.

        Runs the WinRT async call synchronously. Do not call this from the Qt UI
        thread; use request_availability() and availability_ready instead.
        """
        return self._query_availability()

    @staticmethod
    def _query_availability() -> HelloAvailability:
        try:
            from winrt.windows.security.credentials.ui import (
                UserConsentVerifier,
                UserConsentVerifierAvailability,
            )

            async def _check() -> HelloAvailability:
                avail = await UserConsentVerifier.check_availability_async()
                return WindowsHelloAuth._map_availability(
                    avail,
                    UserConsentVerifierAvailability.AVAILABLE,
                    UserConsentVerifierAvailability.NOT_CONFIGURED_FOR_USER,
                )

            return asyncio.run(_check())

        except ModuleNotFoundError:
            logger.warning("winrt-Windows.Security.Credentials.UI not installed.")
            return HelloAvailability.UNAVAILABLE
        except Exception as exc:
            logger.error("WindowsHello availability check error: %s", exc)
            return HelloAvailability.ERROR

    def request_availability(self) -> bool:
        """Start a non-blocking Windows Hello availability check.

        The result is emitted through ``availability_ready``. A daemon worker
        keeps WinRT/asyncio setup from blocking the UI and cannot hold process
        shutdown open if the platform call fails to return.
        """
        with self._availability_lock:
            if self._availability_thread and self._availability_thread.is_alive():
                return False

            self._availability_thread = threading.Thread(
                target=self._run_availability_check,
                name="WindowsHelloAvailability",
                daemon=True,
            )
            self._availability_thread.start()
            return True

    def _run_availability_check(self) -> None:
        try:
            result = self._query_availability()
        except Exception:
            logger.exception("WindowsHello availability worker failed")
            result = HelloAvailability.ERROR

        try:
            # Qt queues this signal to receivers with UI-thread affinity.
            self.availability_ready.emit(int(result))
        except RuntimeError:
            # The owning page or dialog may have closed while the check ran.
            logger.debug("WindowsHello availability result arrived after its owner closed")
        finally:
            with self._availability_lock:
                self._availability_thread = None

    # ------------------------------------------------------------------
    # Asynchronous verification (non-blocking)
    # ------------------------------------------------------------------

    def request_verification(self, message: str) -> None:
        """Show the Windows Hello prompt.  Non-blocking.

        Connect ``result_ready`` before calling this method.  The signal
        is emitted on the Qt main thread when the user completes or
        dismisses the Windows Hello dialog.

        Args:
            message: Text shown inside the Windows Hello dialog.
        """
        # Cancel any in-flight request first
        if self._worker and self._worker.isRunning():
            logger.warning("WindowsHello: previous request still running; ignoring new request.")
            return

        self._worker = _HelloWorker(message, parent=self)
        self._worker.result_ready.connect(self.result_ready)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def is_busy(self) -> bool:
        """Return True if a Windows Hello request is in progress."""
        return bool(self._worker and self._worker.isRunning())
