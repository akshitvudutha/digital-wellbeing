"""
sleepguard_page.py — SleepGuard specific page
"""

from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)
from tracker.sleepguard import SleepGuardController

class SleepGuardPage(QWidget):
    def __init__(self, sleepguard: Optional[SleepGuardController] = None, parent=None):
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
        title = QLabel("SleepGuard Protection")
        title.setObjectName("page_title")
        subtitle = QLabel("Automatically manage power state after extended inactivity to enforce bedtime")
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

        # SleepGuard Card
        sg_card = QFrame()
        sg_card.setObjectName("v2_card")
        sg_card.setMaximumWidth(600)
        sg_l = QVBoxLayout(sg_card)
        sg_l.setContentsMargins(24, 22, 24, 22)
        sg_l.setSpacing(16)

        hdr = QHBoxLayout()
        from ui.icons import get_icon
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("sleepguard", size=18).pixmap(18, 18))
        lbl = QLabel("Configuration")
        lbl.setObjectName("section_header")
        hdr.addWidget(icon_lbl)
        hdr.addWidget(lbl)
        hdr.addStretch()
        sg_l.addLayout(hdr)

        # Toggle Switch Row
        t_row = QHBoxLayout()
        t_col = QVBoxLayout()
        t_col.setSpacing(2)
        t_lbl = QLabel("Enable Protection")
        t_lbl.setObjectName("setting_label")
        t_desc = QLabel("Automatically take action after inactivity")
        t_desc.setObjectName("setting_desc")
        t_col.addWidget(t_lbl)
        t_col.addWidget(t_desc)
        t_row.addLayout(t_col, 1)

        from ui.widgets.fluent import ToggleSwitch
        self._sg_check = ToggleSwitch()
        if self._sleepguard:
            self._sg_check.setChecked(self._sleepguard.is_enabled)
        self._sg_check.toggled.connect(self._on_sg_toggle)
        t_row.addWidget(self._sg_check)
        sg_l.addLayout(t_row)

        self._line = QFrame()
        self._line.setFrameShape(QFrame.Shape.HLine)
        self._line.setMaximumHeight(1)
        sg_l.addWidget(self._line)

        # Action Dropdown Row
        act_row = QHBoxLayout()
        act_col = QVBoxLayout()
        act_col.setSpacing(2)
        act_lbl = QLabel("Timeout Action")
        act_lbl.setObjectName("setting_label")
        act_desc = QLabel("Power action to execute when countdown expires")
        act_desc.setObjectName("setting_desc")
        act_col.addWidget(act_lbl)
        act_col.addWidget(act_desc)
        act_row.addLayout(act_col, 1)

        self._action_combo = QComboBox()
        self._action_combo.addItem("Lock", "lock")
        self._action_combo.addItem("Sleep", "sleep")
        self._action_combo.addItem("Hibernate", "hibernate")
        self._action_combo.addItem("Shut down", "shutdown")
        self._action_combo.addItem("Cancel", "cancel")
        self._action_combo.setFixedWidth(130)
        self._action_combo.currentIndexChanged.connect(self._on_action_changed)
        act_row.addWidget(self._action_combo)
        sg_l.addLayout(act_row)

        # Timeout Spinbox Row
        out_row = QHBoxLayout()
        out_col = QVBoxLayout()
        out_col.setSpacing(2)
        out_lbl = QLabel("Idle Timeout")
        out_lbl.setObjectName("setting_label")
        out_desc = QLabel("Idle minutes required before triggering action")
        out_desc.setObjectName("setting_desc")
        out_col.addWidget(out_lbl)
        out_col.addWidget(out_desc)
        out_row.addLayout(out_col, 1)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 120)
        self._timeout_spin.setSuffix(" min")
        self._timeout_spin.setFixedWidth(110)
        self._timeout_spin.setValue(30)
        self._timeout_spin.valueChanged.connect(self._on_timeout_changed)
        out_row.addWidget(self._timeout_spin)
        sg_l.addLayout(out_row)

        self._line2 = QFrame()
        self._line2.setFrameShape(QFrame.Shape.HLine)
        self._line2.setMaximumHeight(1)
        sg_l.addWidget(self._line2)

        # Active Media Detection Indicator
        self._media_lbl = QLabel("Media Playback Detection: Idle / Not playing")
        self._media_lbl.setObjectName("media_lbl")
        self._media_lbl.setWordWrap(True)
        sg_l.addWidget(self._media_lbl)

        # Test Action Button
        test_btn = QPushButton("Test Warning Countdown")
        test_btn.setObjectName("test_btn")
        test_btn.clicked.connect(self._on_test_warning)
        sg_l.addWidget(test_btn)
        sg_l.addStretch()

        inner_layout.addWidget(sg_card, 0, Qt.AlignmentFlag.AlignTop)
        inner_layout.addStretch()

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 1.2px; text-transform: uppercase; }}
            QLabel#setting_label {{ font-weight: 700; color: {tm.color('text_main')}; font-size: 14px; }}
            QLabel#setting_desc {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            
            QFrame#v2_card {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
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
            QComboBox, QSpinBox {{
                background-color: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 6px;
                padding: 4px 8px;
                color: {tm.color('text_main')};
                font-size: 13px;
                font-weight: 500;
            }}
            QComboBox:hover, QSpinBox:hover {{
                border: 1px solid {tm.color('accent')};
                background-color: {tm.color('surface_elevated')};
            }}
            QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {{
                border: none;
                background: transparent;
            }}
        """)
        
        self._line.setStyleSheet(f"background: {tm.color('border')}; margin: 8px 0;")
        self._line2.setStyleSheet(f"background: {tm.color('border')}; margin: 8px 0;")
        self.on_data_changed()

    def _on_sg_toggle(self, checked: bool) -> None:
        if self._sleepguard:
            self._sleepguard.set_enabled(checked)

    def _on_action_changed(self) -> None:
        act = self._action_combo.currentData()
        if act and self._sleepguard:
            self._sleepguard._settings.sleepguard_action = act

    def _on_timeout_changed(self, val: int) -> None:
        if self._sleepguard:
            self._sleepguard._settings.idle_timeout_minutes = val

    def _on_test_warning(self) -> None:
        if self._sleepguard:
            self._sleepguard.force_trigger_idle()
        else:
            from core.logger import logger
            logger.info("SleepGuard Test: Shutdown countdown warning triggered for 30s.")

    def on_data_changed(self) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        if self._sleepguard:
            self._sg_check.setChecked(self._sleepguard.is_enabled)
            
            act = self._sleepguard._settings.sleepguard_action
            idx = self._action_combo.findData(act)
            if idx >= 0:
                self._action_combo.blockSignals(True)
                self._action_combo.setCurrentIndex(idx)
                self._action_combo.blockSignals(False)

            self._timeout_spin.blockSignals(True)
            self._timeout_spin.setValue(self._sleepguard._settings.idle_timeout_minutes)
            self._timeout_spin.blockSignals(False)

            media = self._sleepguard.current_media
            if media and media.is_playing:
                self._media_lbl.setText(f"Media Playback Active: Playing on {media.display_name}")
                self._media_lbl.setStyleSheet(f"""
                    background-color: {tm.color('success_bg')}; color: {tm.color('success_text')};
                    border: 1px solid {tm.color('success_border')}; border-radius: 8px;
                    font-size: 12px; font-weight: 600; padding: 12px;
                """)
            else:
                self._media_lbl.setText("Media Playback Detection: Idle / Not playing")
                self._media_lbl.setStyleSheet(f"""
                    background-color: {tm.color('info_bg')}; color: {tm.color('info_text')};
                    border: 1px solid {tm.color('info_border')}; border-radius: 8px;
                    font-size: 12px; font-weight: 600; padding: 12px;
                """)
