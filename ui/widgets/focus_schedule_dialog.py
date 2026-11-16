"""
focus_schedule_dialog.py — Modal dialog for creating and editing Smart Focus Schedules in Notch v3.6.3.
"""
from __future__ import annotations

from typing import List, Optional
from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QTimeEdit, QFrame
)
from database.models import FocusSchedule
from ui.theme import ThemeManager


DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class FocusScheduleDialog(QDialog):
    def __init__(self, schedule: Optional[FocusSchedule] = None, parent=None):
        super().__init__(parent)
        self._existing_schedule = schedule
        self.setWindowTitle("Edit Schedule" if schedule else "New Focus Schedule")
        self.setFixedSize(520, 560)
        self.setObjectName("focus_schedule_dialog")

        self._selected_days: set[int] = set(schedule.days_list if schedule else [0, 1, 2, 3, 4])
        self._day_buttons: List[QPushButton] = []

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Badge
        badge = QLabel("SMART FOCUS SCHEDULER")
        badge.setObjectName("badge_label")
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)

        title = QLabel("Edit Focus Schedule" if self._existing_schedule else "Create Focus Schedule")
        title.setObjectName("dialog_title")
        layout.addWidget(title)

        desc = QLabel("Configure recurring hours for Notch to automatically engage Focus Mode.")
        desc.setObjectName("dialog_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 1. Schedule Name
        lbl_name = QLabel("SCHEDULE NAME")
        lbl_name.setObjectName("section_heading")
        layout.addWidget(lbl_name)

        self._name_input = QLineEdit()
        self._name_input.setObjectName("text_input")
        self._name_input.setPlaceholderText("e.g. Morning Deep Work")
        self._name_input.setText(self._existing_schedule.name if self._existing_schedule else "Deep Work Block")
        layout.addWidget(self._name_input)

        # 2. Mode Selector
        lbl_mode = QLabel("FOCUS PROFILE")
        lbl_mode.setObjectName("section_heading")
        layout.addWidget(lbl_mode)

        self._mode_combo = QComboBox()
        self._mode_combo.setObjectName("mode_combo")
        modes = [("Work (Block Social & Entertainment)", "work"),
                 ("Study (Block distracting sites)", "study"),
                 ("Deep Focus (Strict Allowlist Only)", "deep"),
                 ("Movie (Allow entertainment, block noise)", "movie"),
                 ("Custom (Your custom blocklist)", "custom")]
        for label, val in modes:
            self._mode_combo.addItem(label, val)

        if self._existing_schedule:
            idx = self._mode_combo.findData(self._existing_schedule.mode)
            if idx >= 0:
                self._mode_combo.setCurrentIndex(idx)
        layout.addWidget(self._mode_combo)

        # 3. Days of Week
        lbl_days = QLabel("REPEAT ON")
        lbl_days.setObjectName("section_heading")
        layout.addWidget(lbl_days)

        days_row = QHBoxLayout()
        days_row.setSpacing(6)
        self._day_buttons = []
        for i, name in enumerate(DAY_NAMES):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setChecked(i in self._selected_days)
            btn.setObjectName("day_pill")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, d=i: self._toggle_day(d))
            self._day_buttons.append(btn)
            days_row.addWidget(btn)
        layout.addLayout(days_row)

        quick_days_row = QHBoxLayout()
        quick_days_row.setSpacing(8)
        btn_weekdays = QPushButton("Weekdays")
        btn_weekdays.setObjectName("quick_btn")
        btn_weekdays.clicked.connect(lambda: self._set_days({0, 1, 2, 3, 4}))
        btn_weekends = QPushButton("Weekends")
        btn_weekends.setObjectName("quick_btn")
        btn_weekends.clicked.connect(lambda: self._set_days({5, 6}))
        btn_all = QPushButton("Every Day")
        btn_all.setObjectName("quick_btn")
        btn_all.clicked.connect(lambda: self._set_days({0, 1, 2, 3, 4, 5, 6}))
        quick_days_row.addWidget(btn_weekdays)
        quick_days_row.addWidget(btn_weekends)
        quick_days_row.addWidget(btn_all)
        quick_days_row.addStretch()
        layout.addLayout(quick_days_row)

        # 4. Time Range
        lbl_time = QLabel("TIME WINDOW (START / END)")
        lbl_time.setObjectName("section_heading")
        layout.addWidget(lbl_time)

        time_row = QHBoxLayout()
        time_row.setSpacing(12)

        self._start_time = QTimeEdit()
        self._start_time.setDisplayFormat("HH:mm")
        self._start_time.setObjectName("time_edit")
        sh, sm = (9, 0)
        if self._existing_schedule:
            try:
                sh, sm = map(int, self._existing_schedule.start_time.split(":"))
            except Exception:
                pass
        self._start_time.setTime(QTime(sh, sm))

        to_lbl = QLabel("to")
        to_lbl.setObjectName("to_label")

        self._end_time = QTimeEdit()
        self._end_time.setDisplayFormat("HH:mm")
        self._end_time.setObjectName("time_edit")
        eh, em = (12, 0)
        if self._existing_schedule:
            try:
                eh, em = map(int, self._existing_schedule.end_time.split(":"))
            except Exception:
                pass
        self._end_time.setTime(QTime(eh, em))

        time_row.addWidget(self._start_time)
        time_row.addWidget(to_lbl)
        time_row.addWidget(self._end_time)
        time_row.addStretch()
        layout.addLayout(time_row)

        # 5. Strict Mode
        self._strict_check = QCheckBox("Strict Mode (Requires PIN verification to stop early)")
        self._strict_check.setObjectName("strict_check")
        if self._existing_schedule:
            self._strict_check.setChecked(self._existing_schedule.strict_mode)
        layout.addWidget(self._strict_check)

        layout.addStretch()

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("Save Schedule")
        btn_save.setObjectName("btn_primary")
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def _toggle_day(self, day_idx: int):
        if day_idx in self._selected_days:
            self._selected_days.remove(day_idx)
        else:
            self._selected_days.add(day_idx)
        self._sync_day_buttons()

    def _set_days(self, days: set[int]):
        self._selected_days = set(days)
        self._sync_day_buttons()

    def _sync_day_buttons(self):
        for i, btn in enumerate(self._day_buttons):
            btn.setChecked(i in self._selected_days)

    def _on_save(self):
        name = self._name_input.text().strip() or "Focus Schedule"
        days_str = ",".join(str(d) for d in sorted(self._selected_days))
        start_str = self._start_time.time().toString("HH:mm")
        end_str = self._end_time.time().toString("HH:mm")
        mode = self._mode_combo.currentData()
        strict = self._strict_check.isChecked()

        if self._existing_schedule:
            self._result_schedule = FocusSchedule(
                id=self._existing_schedule.id,
                name=name,
                days_of_week=days_str,
                start_time=start_str,
                end_time=end_str,
                mode=mode,
                strict_mode=strict,
                is_enabled=self._existing_schedule.is_enabled,
                created_at=self._existing_schedule.created_at,
            )
        else:
            self._result_schedule = FocusSchedule(
                name=name,
                days_of_week=days_str,
                start_time=start_str,
                end_time=end_str,
                mode=mode,
                strict_mode=strict,
                is_enabled=True,
            )
        self.accept()

    def get_schedule(self) -> FocusSchedule:
        return self._result_schedule

    def _apply_theme(self):
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        bg = "#11151C" if is_dark else "#FFFFFF"
        border = tm.color("border")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        accent = tm.color("accent")

        self.setStyleSheet(f"""
            QDialog#focus_schedule_dialog {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QLabel#badge_label {{
                font-size: 10px;
                font-weight: 800;
                color: {accent};
                letter-spacing: 1.5px;
            }}
            QLabel#dialog_title {{
                font-size: 20px;
                font-weight: 800;
                color: {text_main};
            }}
            QLabel#dialog_desc {{
                font-size: 13px;
                color: {text_sub};
            }}
            QLabel#section_heading {{
                font-size: 11px;
                font-weight: 700;
                color: {text_sub};
                letter-spacing: 0.8px;
            }}
            QLabel#to_label {{
                font-size: 13px;
                font-weight: 600;
                color: {text_sub};
            }}
            QLineEdit#text_input, QTimeEdit#time_edit, QComboBox#mode_combo {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 8px 12px;
                color: {text_main};
                font-size: 13px;
            }}
            QLineEdit#text_input:focus, QTimeEdit#time_edit:focus, QComboBox#mode_combo:focus {{
                border-color: {accent};
            }}
            QPushButton#day_pill {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px 10px;
                color: {text_sub};
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton#day_pill:checked {{
                background-color: {tm.color('accent_emerald_bg')};
                border-color: {accent};
                color: {accent};
            }}
            QPushButton#quick_btn {{
                background: transparent;
                border: none;
                color: {text_sub};
                font-size: 11px;
                font-weight: 600;
                padding: 2px 4px;
            }}
            QPushButton#quick_btn:hover {{
                color: {accent};
            }}
            QCheckBox#strict_check {{
                color: {text_main};
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton#btn_secondary {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 8px 18px;
                color: {text_main};
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#btn_secondary:hover {{
                background-color: {tm.color('surface_hover')};
            }}
            QPushButton#btn_primary {{
                background: {tm.color('primary_btn_gradient')};
                border: none;
                border-radius: 8px;
                padding: 8px 22px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
            }}
        """)
