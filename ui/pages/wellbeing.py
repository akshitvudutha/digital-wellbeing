"""
wellbeing.py — Unified Focus & SleepGuard Wellbeing Suite for Digital Wellbeing V2.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from tracker.sleepguard import SleepGuardController
from ui.widgets.focus_timer import FocusTimerWidget


class WellbeingPage(QWidget):
    """Unified Focus Session Timer & SleepGuard Protection Suite."""

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
        title = QLabel("Focus & SleepGuard")
        title.setObjectName("page_title")
        subtitle = QLabel("Boost productivity with focus sessions and protect bedtime with SleepGuard")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner_layout = QHBoxLayout(inner)
        inner_layout.setContentsMargins(0, 10, 0, 0)
        inner_layout.setSpacing(20)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        # 1. Left Card: Focus Timer Widget
        self._focus_timer = FocusTimerWidget()
        inner_layout.addWidget(self._focus_timer, 1)

        # 2. Right Card: SleepGuard Bedtime Protection Card
        sg_card = QFrame()
        sg_card.setObjectName("v2_card")
        sg_l = QVBoxLayout(sg_card)
        sg_l.setContentsMargins(24, 22, 24, 22)
        sg_l.setSpacing(16)

        hdr = QLabel("🌙 SleepGuard Protection")
        hdr.setObjectName("section_header")
        sg_l.addWidget(hdr)

        # Toggle Switch Row
        t_row = QHBoxLayout()
        t_col = QVBoxLayout()
        t_col.setSpacing(2)
        t_lbl = QLabel("Bedtime Protection Status")
        t_lbl.setObjectName("setting_label")
        t_desc = QLabel("Automatically power off PC after bedtime inactivity")
        t_desc.setObjectName("setting_desc")
        t_col.addWidget(t_lbl)
        t_col.addWidget(t_desc)
        t_row.addLayout(t_col, 1)

        self._sg_check = QCheckBox()
        if self._sleepguard:
            self._sg_check.setChecked(self._sleepguard.is_enabled)
        self._sg_check.toggled.connect(self._on_sg_toggle)
        t_row.addWidget(self._sg_check)
        sg_l.addLayout(t_row)

        self._line = QFrame()
        self._line.setFrameShape(QFrame.Shape.HLine)
        self._line.setMaximumHeight(1)
        sg_l.addWidget(self._line)

        # Timeout Spinbox Row
        out_row = QHBoxLayout()
        out_col = QVBoxLayout()
        out_col.setSpacing(2)
        out_lbl = QLabel("Inactivity Timeout")
        out_lbl.setObjectName("setting_label")
        out_desc = QLabel("Idle minutes before triggering shutdown warning")
        out_desc.setObjectName("setting_desc")
        out_col.addWidget(out_lbl)
        out_col.addWidget(out_desc)
        out_row.addLayout(out_col, 1)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 120)
        self._timeout_spin.setSuffix(" min")
        self._timeout_spin.setFixedWidth(110)
        self._timeout_spin.setValue(30)
        out_row.addWidget(self._timeout_spin)
        sg_l.addLayout(out_row)

        self._line2 = QFrame()
        self._line2.setFrameShape(QFrame.Shape.HLine)
        self._line2.setMaximumHeight(1)
        sg_l.addWidget(self._line2)

        # Active Media Detection Indicator
        self._media_lbl = QLabel("Media Playback Detection: Idle / Not playing")
        self._media_lbl.setObjectName("media_lbl")
        sg_l.addWidget(self._media_lbl)

        # Test Action Button
        test_btn = QPushButton("🚨 Test SleepGuard Warning")
        test_btn.setObjectName("test_btn")
        test_btn.clicked.connect(self._on_test_warning)
        sg_l.addWidget(test_btn)
        sg_l.addStretch()

        inner_layout.addWidget(sg_card, 1)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 1.2px; text-transform: uppercase; }}
            QLabel#setting_label {{ font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#setting_desc {{ color: {tm.color('text_sub')}; font-size: 11px; }}
            QPushButton#test_btn {{
                background-color: {tm.color('card_bg')};
                color: {tm.color('text_main')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                padding: 10px;
                font-weight: 600;
            }}
            QPushButton#test_btn:hover {{
                background-color: {tm.color('card_hover')};
                border-color: {tm.color('border_hover')};
            }}
        """)
        
        self._line.setStyleSheet(f"background: {tm.color('border')};")
        self._line2.setStyleSheet(f"background: {tm.color('border')};")
        self.on_data_changed()

    def _on_sg_toggle(self, checked: bool) -> None:
        if self._sleepguard:
            self._sleepguard.set_enabled(checked)

    def _on_test_warning(self) -> None:
        if self._sleepguard:
            self._sleepguard.force_trigger_idle()
        else:
            QMessageBox.information(self, "SleepGuard Test", "Shutdown countdown warning triggered for 30s.")

    def on_data_changed(self) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        if self._sleepguard:
            self._sg_check.setChecked(self._sleepguard.is_enabled)
            media = self._sleepguard.current_media
            if media and media.is_playing:
                self._media_lbl.setText(f"Media Playback Active: Playing on {media.display_name}")
                self._media_lbl.setStyleSheet(f"""
                    background-color: {tm.color('success_bg')}; color: {tm.color('success_text')};
                    border: 1px solid {tm.color('success_border')}; border-radius: 16px;
                    font-size: 11px; font-weight: 600; padding: 10px;
                """)
            else:
                self._media_lbl.setText("Media Playback Detection: Idle / Not playing")
                self._media_lbl.setStyleSheet(f"""
                    background-color: {tm.color('info_bg')}; color: {tm.color('info_text')};
                    border: 1px solid {tm.color('info_border')}; border-radius: 16px;
                    font-size: 11px; font-weight: 600; padding: 10px;
                """)
