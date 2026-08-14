from __future__ import annotations

from typing import Optional

from core.logger import logger
from PySide6.QtCore import QMetaObject, Qt, Q_ARG
from PySide6.QtWidgets import QSystemTrayIcon

class Notifier:
    _tray_icon: Optional[QSystemTrayIcon] = None

    @classmethod
    def set_tray_icon(cls, tray: QSystemTrayIcon) -> None:
        cls._tray_icon = tray

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
        
        if self.__class__._tray_icon:
            try:
                QMetaObject.invokeMethod(
                    self.__class__._tray_icon,
                    "showMessage",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, title),
                    Q_ARG(str, message),
                    Q_ARG(QSystemTrayIcon.MessageIcon, QSystemTrayIcon.MessageIcon.Information),
                    Q_ARG(int, duration * 1000)
                )
            except Exception as exc:
                logger.warning("QSystemTrayIcon notification failed: %s", exc)
                self._send_fallback(title, message)
        else:
            self._send_fallback(title, message)

    def _send_fallback(self, title: str, message: str) -> None:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, message, title, 0x40 | 0x1000
            )
        except Exception as exc:
            logger.warning("Fallback notification failed: %s", exc)
