from __future__ import annotations

import threading
from typing import Optional

from core.logger import logger


class Notifier:
    def __init__(self) -> None:
        self._enabled = True
        self._app_id = "DigitalWellbeing"

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def notify(
        self,
        title: str,
        message: str,
        duration: int = 5,
    ) -> None:
        if not self._enabled:
            return
        threading.Thread(
            target=self._send,
            args=(title, message, duration),
            daemon=True,
        ).start()

    def _send(self, title: str, message: str, duration: int) -> None:
        try:
            from win10toast import ToastNotifier  # type: ignore
            toaster = ToastNotifier()
            import os
            from pathlib import Path
            icon_path = str(Path(__file__).parent.parent / "assets" / "icons" / "app_icon.ico")
            if not os.path.exists(icon_path):
                icon_path = None
            toaster.show_toast(title, message, icon_path=icon_path, duration=duration, threaded=False)
        except ImportError:
            self._send_fallback(title, message)
        except Exception as exc:
            logger.warning("Toast notification failed: %s", exc)
            self._send_fallback(title, message)

    def _send_fallback(self, title: str, message: str) -> None:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, message, title, 0x40 | 0x1000
            )
        except Exception as exc:
            logger.warning("Fallback notification failed: %s", exc)
