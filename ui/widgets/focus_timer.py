"""
focus_timer.py — Focus Session / Pomodoro Timer widget with quick preset chips for Desktop Dashboard.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

class FocusTimerWidget(QFrame):
    """Focus Session / Pomodoro Timer widget with quick duration chips."""

    card_clicked = Signal()
    focus_completed = Signal()

    DEFAULT_FOCUS_M = 25

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("v2_card")
        self._seconds_remaining = self.DEFAULT_FOCUS_M * 60
        self._is_running = False

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        hdr = QHBoxLayout()
        self._lbl = QLabel("🧘 Focus Session Timer")
        self._lbl.setObjectName("section_header")
        hdr.addWidget(self._lbl)
        hdr.addStretch()
        layout.addLayout(hdr)

        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(6)

        self._time_display = QLabel(self._format_time(self._seconds_remaining))
        self._time_display.setObjectName("timer_display")
        self._time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._status_lbl = QLabel("Ready to focus — select preset or start")
        self._status_lbl.setObjectName("timer_status")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        center_layout.addWidget(self._time_display)
        center_layout.addWidget(self._status_lbl)
        layout.addLayout(center_layout)

        # Quick Preset Chips Row
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        chips_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for minutes in (15, 25, 45, 60):
            chip = QPushButton(f"{minutes}m")
            chip.setObjectName("timer_chip")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda checked, m=minutes: self.set_preset(m))
            chips_row.addWidget(chip)

        layout.addLayout(chips_row)

        # Controls Row
        controls = QHBoxLayout()
        controls.setSpacing(10)

        self._start_btn = QPushButton("▶ Start Focus")
        self._start_btn.setObjectName("timer_start_btn")
        self._start_btn.setMinimumHeight(40)
        self._start_btn.clicked.connect(self._toggle_timer)

        self._reset_btn = QPushButton("↺ Reset")
        self._reset_btn.setObjectName("timer_reset_btn")
        self._reset_btn.setMinimumHeight(40)
        self._reset_btn.clicked.connect(self._reset_timer)

        controls.addWidget(self._start_btn, 2)
        controls.addWidget(self._reset_btn, 1)

        layout.addLayout(controls)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            FocusTimerWidget#v2_card:hover {{
                background-color: {tm.color('card_hover')};
                border-color: {tm.color('border_hover')};
            }}
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 1.2px; text-transform: uppercase; }}
            QLabel#timer_display {{ font-size: 42px; font-weight: 900; color: {tm.color('accent')}; letter-spacing: -1.2px; }}
            QLabel#timer_status {{ color: {tm.color('text_sub')}; font-size: 12px; font-weight: 600; }}
            QPushButton#timer_chip {{
                background-color: {tm.color('border')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 700;
                padding: 4px 12px;
            }}
            QPushButton#timer_chip:hover {{
                background-color: {tm.color('accent')}33;
                border-color: {tm.color('accent')}80;
                color: {tm.color('text_main')};
            }}
            QPushButton#timer_start_btn {{
                background-color: {tm.color('accent')};
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border-radius: 12px;
                padding: 8px 16px;
                border: 1px solid {tm.color('border')};
            }}
            QPushButton#timer_start_btn:hover {{
                background-color: {tm.color('accent_hover')};
            }}
            QPushButton#timer_reset_btn {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                padding: 8px 14px;
            }}
            QPushButton#timer_reset_btn:hover {{
                background-color: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
        """)
        
        self._update_display_color()

    def _update_display_color(self) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        if self._seconds_remaining == 0 and not self._is_running:
            self._time_display.setStyleSheet(f"font-size: 42px; font-weight: 900; color: {tm.color('success_text')}; letter-spacing: -1.2px;")
        else:
            self._time_display.setStyleSheet(f"font-size: 42px; font-weight: 900; color: {tm.color('accent')}; letter-spacing: -1.2px;")

    def set_preset(self, minutes: int) -> None:
        self._timer.stop()
        self._is_running = False
        self._seconds_remaining = minutes * 60
        self._time_display.setText(self._format_time(self._seconds_remaining))
        self._start_btn.setText("▶ Start Focus")
        self._status_lbl.setText(f"Preset set to {minutes} minutes")
        self._update_display_color()

    def _on_tick(self) -> None:
        if self._seconds_remaining > 0:
            self._seconds_remaining -= 1
            self._time_display.setText(self._format_time(self._seconds_remaining))
        else:
            self._timer.stop()
            self._is_running = False
            self._start_btn.setText("▶ Start Focus")
            self._status_lbl.setText("Session complete! Take a break 🎉")
            self._update_display_color()
            self.focus_completed.emit()

    def _toggle_timer(self) -> None:
        if self._is_running:
            self._timer.stop()
            self._is_running = False
            self._start_btn.setText("▶ Resume")
            self._status_lbl.setText("Paused")
        else:
            if self._seconds_remaining == 0:
                self._seconds_remaining = self.DEFAULT_FOCUS_M * 60
            self._timer.start()
            self._is_running = True
            self._start_btn.setText("⏸ Pause")
            self._status_lbl.setText("Focusing...")
            self._update_display_color()

    def _reset_timer(self) -> None:
        self._timer.stop()
        self._is_running = False
        self._seconds_remaining = self.DEFAULT_FOCUS_M * 60
        self._time_display.setText(self._format_time(self._seconds_remaining))
        self._start_btn.setText("▶ Start Focus")
        self._status_lbl.setText("Ready to focus — select preset or start")
        self._update_display_color()

    @staticmethod
    def _format_time(seconds: int) -> str:
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"
