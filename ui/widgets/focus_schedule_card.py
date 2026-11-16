"""
focus_schedule_card.py — Visual card widget representing a configured Focus Schedule in Notch v3.6.3.
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy
)
from database.models import FocusSchedule
from ui.theme import ThemeManager


DAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"]


class FocusScheduleCard(QFrame):
    toggled = Signal(int, bool)          # schedule_id, is_enabled
    edit_requested = Signal(int)         # schedule_id
    delete_requested = Signal(int)       # schedule_id

    def __init__(self, schedule: FocusSchedule, is_active_now: bool = False, parent=None):
        super().__init__(parent)
        self.schedule = schedule
        self.is_active_now = is_active_now
        self.setObjectName("schedule_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(18)

        # Left Column: Info
        info_col = QVBoxLayout()
        info_col.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        self._lbl_name = QLabel(self.schedule.name)
        self._lbl_name.setObjectName("card_title")
        title_row.addWidget(self._lbl_name)

        # Mode Badge
        mode_str = self.schedule.mode.upper()
        self._lbl_mode = QLabel(mode_str)
        self._lbl_mode.setObjectName("mode_badge")
        title_row.addWidget(self._lbl_mode)

        if self.schedule.strict_mode:
            lbl_strict = QLabel("STRICT")
            lbl_strict.setObjectName("strict_badge")
            title_row.addWidget(lbl_strict)

        if self.is_active_now:
            lbl_live = QLabel("ACTIVE NOW")
            lbl_live.setObjectName("live_badge")
            title_row.addWidget(lbl_live)

        title_row.addStretch()
        info_col.addLayout(title_row)

        # Sub-row: Time Window and Days
        sub_row = QHBoxLayout()
        sub_row.setSpacing(16)

        time_str = f"{self.schedule.start_time} — {self.schedule.end_time}"
        self._lbl_time = QLabel(time_str)
        self._lbl_time.setObjectName("card_time")
        sub_row.addWidget(self._lbl_time)

        # Days Indicator Pills
        days_layout = QHBoxLayout()
        days_layout.setSpacing(4)
        active_days = set(self.schedule.days_list)
        for i, dname in enumerate(DAY_LABELS):
            d_lbl = QLabel(dname)
            d_lbl.setObjectName("day_ind_active" if i in active_days else "day_ind_inactive")
            d_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            d_lbl.setFixedSize(22, 22)
            days_layout.addWidget(d_lbl)
        sub_row.addLayout(days_layout)
        sub_row.addStretch()

        info_col.addLayout(sub_row)
        layout.addLayout(info_col, 1)

        # Right Column: Controls
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        # Toggle Enable Button
        self._btn_toggle = QPushButton("Enabled" if self.schedule.is_enabled else "Disabled")
        self._btn_toggle.setCheckable(True)
        self._btn_toggle.setChecked(self.schedule.is_enabled)
        self._btn_toggle.setObjectName("btn_toggle_active" if self.schedule.is_enabled else "btn_toggle_inactive")
        self._btn_toggle.clicked.connect(self._on_toggle)
        ctrl_row.addWidget(self._btn_toggle)

        btn_edit = QPushButton("Edit")
        btn_edit.setObjectName("btn_action")
        btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.schedule.id or 0))
        ctrl_row.addWidget(btn_edit)

        btn_del = QPushButton("Delete")
        btn_del.setObjectName("btn_delete")
        btn_del.clicked.connect(lambda: self.delete_requested.emit(self.schedule.id or 0))
        ctrl_row.addWidget(btn_del)

        layout.addLayout(ctrl_row)

    def _on_toggle(self):
        new_val = self._btn_toggle.isChecked()
        self._btn_toggle.setText("Enabled" if new_val else "Disabled")
        self._btn_toggle.setObjectName("btn_toggle_active" if new_val else "btn_toggle_inactive")
        self._apply_theme()
        if self.schedule.id:
            self.toggled.emit(self.schedule.id, new_val)

    def _apply_theme(self):
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        bg = "#11151C" if is_dark else "#FFFFFF"
        border = tm.color("border")
        border_hover = tm.color("border_hover")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        accent = tm.color("accent")
        accent_bg = tm.color("accent_emerald_bg")

        self.setStyleSheet(f"""
            QFrame#schedule_card {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QFrame#schedule_card:hover {{
                border-color: {border_hover};
            }}
            QLabel#card_title {{
                font-size: 15px;
                font-weight: 700;
                color: {text_main};
            }}
            QLabel#card_time {{
                font-size: 13px;
                font-weight: 600;
                color: {text_sub};
            }}
            QLabel#mode_badge {{
                background-color: {accent_bg};
                color: {accent};
                border: 1px solid {accent};
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
                padding: 2px 7px;
                letter-spacing: 0.5px;
            }}
            QLabel#strict_badge {{
                background-color: {tm.color('accent_amber_bg')};
                color: {tm.color('accent_amber')};
                border: 1px solid {tm.color('accent_amber')};
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
                padding: 2px 7px;
                letter-spacing: 0.5px;
            }}
            QLabel#live_badge {{
                background-color: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border: 1px solid #EF4444;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
                padding: 2px 7px;
                letter-spacing: 0.5px;
            }}
            QLabel#day_ind_active {{
                background-color: {accent_bg};
                color: {accent};
                border-radius: 11px;
                font-size: 11px;
                font-weight: 700;
            }}
            QLabel#day_ind_inactive {{
                background-color: {tm.color('surface_secondary')};
                color: {tm.color('text_muted')};
                border-radius: 11px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#btn_toggle_active {{
                background-color: {accent_bg};
                border: 1px solid {accent};
                color: {accent};
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton#btn_toggle_inactive {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                color: {text_sub};
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#btn_action {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                color: {text_main};
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#btn_action:hover {{
                background-color: {tm.color('surface_hover')};
            }}
            QPushButton#btn_delete {{
                background: transparent;
                border: 1px solid rgba(239, 68, 68, 0.3);
                color: #EF4444;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#btn_delete:hover {{
                background-color: rgba(239, 68, 68, 0.12);
            }}
        """)
