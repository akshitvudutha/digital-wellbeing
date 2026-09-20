"""
wellbeing.py — Unified Focus Suite for Digital Wellbeing V2.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QScrollArea, QVBoxLayout, QWidget,
)

from tracker.sleepguard import SleepGuardController
from ui.widgets.focus_timer import FocusTimerWidget


class WellbeingPage(QWidget):
    """Focus Session Timer."""

    focus_completed = Signal()

    def __init__(self, sleepguard: Optional[SleepGuardController] = None, parent=None) -> None:
        super().__init__(parent)
        self._sleepguard = sleepguard
        self._setup_ui()

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(36, 28, 36, 32)
        inner_layout.setSpacing(24)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Focus")
        title.setObjectName("page_title")
        subtitle = QLabel("Intentional distraction-free sessions engineered for deep concentration.")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        inner_layout.addLayout(title_box)

        # Centered Container for Cockpit
        center_box = QWidget()
        center_layout = QVBoxLayout(center_box)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_box.setMaximumWidth(1060)

        self._focus_timer = FocusTimerWidget()
        self._focus_timer.focus_completed.connect(self.focus_completed.emit)
        center_layout.addWidget(self._focus_timer)

        inner_layout.addWidget(center_box, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        inner_layout.addStretch()

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 26px; font-weight: 800; color: {tm.color('text_main')}; letter-spacing: -0.5px; }}
            QLabel#page_subtitle {{ font-size: 13px; font-weight: 500; color: {tm.color('text_sub')}; }}
        """)
        self.on_data_changed()

    def on_data_changed(self) -> None:
        pass
