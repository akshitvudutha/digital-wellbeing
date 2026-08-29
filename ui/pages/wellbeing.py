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
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Focus Session")
        title.setObjectName("page_title")
        subtitle = QLabel("Boost productivity by blocking distracting websites and apps")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 10, 0, 0)
        inner_layout.setSpacing(20)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        # Focus Timer Widget
        self._focus_timer = FocusTimerWidget()
        self._focus_timer.setMaximumWidth(600)
        self._focus_timer.focus_completed.connect(self.focus_completed.emit)
        inner_layout.addWidget(self._focus_timer, 0, Qt.AlignmentFlag.AlignTop)
        
        inner_layout.addStretch()

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
        """)
        self.on_data_changed()

    def on_data_changed(self) -> None:
        # Pass down to focus timer if needed
        pass
