"""
countdown_dialog.py — PySide6 Power Action Warning Countdown Dialog for SleepGuard in Digital Wellbeing v2.4.

v2.4 changes:
- Displays and carries the configured action type (shutdown/sleep/hibernate/lock)
- shutdown_accepted signal now carries the action string
- Emits shutdown_cancelled on closeEvent for safety
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

logger = logging.getLogger("digital_wellbeing.ui.countdown")

# Human-readable labels for each action type
_ACTION_LABELS = {
    "shutdown": "Shut Down",
    "sleep": "Sleep",
    "hibernate": "Hibernate",
    "lock": "Lock",
    "cancel": "Cancel",
}

_ACTION_ICONS = {
    "shutdown": "⚡",
    "sleep": "💤",
    "hibernate": "🧊",
    "lock": "🔒",
    "cancel": "❌",
}


class ShutdownCountdownDialog(QDialog):
    """Modal countdown dialog warning the user before an automatic PC power action."""

    # Signal carries the action string so the handler knows what to execute
    shutdown_accepted = Signal(str)
    shutdown_cancelled = Signal()

    def __init__(self, countdown_seconds: int = 60, action: str = "lock", parent=None) -> None:
        super().__init__(parent)
        self._action = action.lower().strip() or "lock"
        self._action_label = _ACTION_LABELS.get(self._action, self._action.title())
        self._action_icon = _ACTION_ICONS.get(self._action, "🌙")

        self.setWindowTitle(f"SleepGuard — Automatic {self._action_label} Warning")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.Dialog
        )
        self.setFixedSize(440, 260)

        self._remaining_s = countdown_seconds
        self._cancelled = False

        logger.info(
            "[SLEEPGUARD_DIALOG] Constructed. countdown=%d, action='%s'",
            countdown_seconds, self._action,
        )

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {tm.color('bg_main')};
                border: 2px solid {tm.color('danger_border')};
                border-radius: 16px;
            }}
            QLabel#timer_display {{
                font-size: 52px;
                font-weight: 800;
                color: {tm.color('danger_text')};
            }}
            QLabel#hdr {{ font-size: 16px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#msg {{ color: {tm.color('text_sub')}; font-size: 12px; font-weight: 500; }}
            QPushButton#primary_action_btn {{
                background: {tm.color('accent')};
                color: #ffffff;
                padding: 12px;
                font-weight: 700;
                border-radius: 10px;
                border: none;
            }}
            QPushButton#primary_action_btn:hover {{
                background: {tm.color('accent_hover')};
            }}
            QPushButton#secondary_action_btn {{
                background: transparent;
                color: {tm.color('text_main')};
                padding: 12px;
                font-weight: 700;
                border-radius: 10px;
                border: 1px solid {tm.color('border')};
            }}
            QPushButton#secondary_action_btn:hover {{
                background: {tm.color('bg_hover')};
            }}
        """)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        hdr = QLabel(f"SleepGuard")
        hdr.setObjectName("hdr")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hdr)

        msg = QLabel(f"Your PC will {self._action_label.lower()} in")
        msg.setObjectName("msg")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        layout.addWidget(msg)
        
        m, s = divmod(self._remaining_s, 60)
        self._timer_lbl = QLabel(f"{m:02d}:{s:02d}")
        self._timer_lbl.setObjectName("timer_display")
        self._timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._timer_lbl)
        
        desc = QLabel("Your computer has been inactive.")
        desc.setObjectName("msg")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        layout.addSpacing(12)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("secondary_action_btn")
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)
        
        self._confirm_btn = QPushButton(f"{self._action_label} now")
        self._confirm_btn.setObjectName("primary_action_btn")
        self._confirm_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(self._confirm_btn)

        layout.addLayout(btn_row)

    def start_countdown(self) -> None:
        self._timer.start()
        logger.info(
            "[SLEEPGUARD_DIALOG] Countdown started. action='%s', remaining=%ds, timer_active=%s",
            self._action, self._remaining_s, self._timer.isActive(),
        )

    def _on_tick(self) -> None:
        if self._remaining_s > 0:
            self._remaining_s -= 1
            m, s = divmod(self._remaining_s, 60)
            self._timer_lbl.setText(f"{m:02d}:{s:02d}")
            logger.debug("[SLEEPGUARD_DIALOG] Tick: remaining=%ds", self._remaining_s)
        else:
            self._timer.stop()
            self._on_accept()

    def _on_accept(self) -> None:
        if self._cancelled:
            return
        logger.info(
            "[SLEEPGUARD_DIALOG] Countdown expired or action accepted. Executing action='%s'",
            self._action,
        )
        self.shutdown_accepted.emit(self._action)
        self.accept()

    def _on_cancel(self) -> None:
        self._cancelled = True
        self._timer.stop()
        logger.info("[SLEEPGUARD_DIALOG] User clicked Cancel.")
        self.shutdown_cancelled.emit()
        self.reject()

    def closeEvent(self, event) -> None:
        """Treat closing the dialog (e.g. Alt+F4) as cancellation for safety."""
        if not self._cancelled:
            self._cancelled = True
            self._timer.stop()
            logger.info("[SLEEPGUARD_DIALOG] Dialog closed via closeEvent — treating as cancel.")
            self.shutdown_cancelled.emit()
        super().closeEvent(event)

    def paintEvent(self, event):
        if not getattr(self, "_logged_paint", False):
            logger.info("[SLEEPGUARD_DIALOG] First paintEvent — dialog is visible on screen.")
            self._logged_paint = True
        super().paintEvent(event)
