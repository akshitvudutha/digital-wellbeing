"""
countdown_dialog.py — PySide6 Shutdown Warning Countdown Dialog for SleepGuard in Digital Wellbeing v2.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)


class ShutdownCountdownDialog(QDialog):
    """Modal countdown dialog warning the user before automatic PC shutdown."""

    shutdown_accepted = Signal()
    shutdown_cancelled = Signal()

    def __init__(self, countdown_seconds: int = 60, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SleepGuard — Automatic Shutdown Warning")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setFixedSize(440, 260)

        self._remaining_s = countdown_seconds
        
        from datetime import datetime
        import logging
        logging.getLogger(__name__).info(f"[STEP 4] ShutdownCountdownDialog constructed. countdown: {countdown_seconds}")

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
        """)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        hdr = QLabel("🌙 SleepGuard Protection Alert")
        hdr.setObjectName("hdr")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hdr)

        msg = QLabel("No user activity detected. Your PC will shut down in:")
        msg.setObjectName("msg")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        self._timer_lbl = QLabel(f"{self._remaining_s}s")
        self._timer_lbl.setObjectName("timer_display")
        self._timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._timer_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._cancel_btn = QPushButton("✋ I'm Still Awake (Cancel)")
        self._cancel_btn.setObjectName("primary_action_btn")
        self._cancel_btn.clicked.connect(self._on_cancel)

        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

    def start_countdown(self) -> None:
        self._timer.start()
        import logging
        logging.getLogger(__name__).info(f"[STEP 8] start_countdown called. Timer isActive: {self._timer.isActive()}")

    def _on_tick(self) -> None:
        from datetime import datetime
        import logging
        logging.getLogger(__name__).info(f"[STEP 9] Timer ticked. Remaining: {self._remaining_s}")
        if self._remaining_s > 0:
            self._remaining_s -= 1
            self._timer_lbl.setText(f"{self._remaining_s}s")
        else:
            self._timer.stop()
            logging.getLogger(__name__).info(f"[STEP 10] Emitting shutdown_accepted. Remaining: {self._remaining_s}")
            self.shutdown_accepted.emit()
            self.accept()

    def _on_cancel(self) -> None:
        self._timer.stop()
        self.shutdown_cancelled.emit()
        self.reject()

    def paintEvent(self, event):
        if not getattr(self, "_logged_paint", False):
            import logging
            logging.getLogger(__name__).info("[STEP 7] Dialog paintEvent triggered (painted on screen)")
            self._logged_paint = True
        super().paintEvent(event)
