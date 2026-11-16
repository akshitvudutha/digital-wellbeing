"""
deep_work_dialog.py — Session configuration modal for launching Deep Work Sessions in Notch v3.6.3.
"""
from __future__ import annotations

from typing import Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QSpinBox, QFrame
)
from ui.theme import ThemeManager


class DeepWorkConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start Deep Work Session")
        self.setFixedSize(540, 580)
        self.setObjectName("deep_work_config_dialog")

        self._preset = "25/5"
        self._preset_buttons = []

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Badge
        badge = QLabel("STRUCTURED WORK SUITE")
        badge.setObjectName("badge_label")
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)

        title = QLabel("Start Deep Work Session")
        title.setObjectName("dialog_title")
        layout.addWidget(title)

        desc = QLabel("Set your intentional focus objective, choose an interval rhythm, and eliminate distractions.")
        desc.setObjectName("dialog_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 1. Goal Input
        lbl_goal = QLabel("SESSION OBJECTIVE / GOAL")
        lbl_goal.setObjectName("section_heading")
        layout.addWidget(lbl_goal)

        self._goal_input = QLineEdit()
        self._goal_input.setObjectName("text_input")
        self._goal_input.setPlaceholderText("e.g. Refactor API controllers & tests")
        self._goal_input.setText("Core Development")
        layout.addWidget(self._goal_input)

        # 2. Presets
        lbl_preset = QLabel("INTERVAL RHYTHM PRESET")
        lbl_preset.setObjectName("section_heading")
        layout.addWidget(lbl_preset)

        presets_row = QHBoxLayout()
        presets_row.setSpacing(8)
        self._preset_defs = [
            ("25/5 Pomodoro", "25/5", 25, 5, 4),
            ("50/10 Deep Block", "50/10", 50, 10, 2),
            ("90/15 Ultradian", "90/15", 90, 15, 2),
            ("Custom", "custom", 30, 5, 3),
        ]
        self._preset_buttons = []
        for label, p_id, wm, bm, iv in self._preset_defs:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(p_id == "25/5")
            btn.setObjectName("preset_chip")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, pid=p_id, w=wm, b=bm, i=iv: self._select_preset(pid, w, b, i))
            self._preset_buttons.append((btn, p_id))
            presets_row.addWidget(btn)
        layout.addLayout(presets_row)

        # 3. Intervals Configuration (Work / Break / Cycles)
        intervals_row = QHBoxLayout()
        intervals_row.setSpacing(16)

        # Work Mins
        work_col = QVBoxLayout()
        work_col.setSpacing(4)
        lbl_work = QLabel("Work (mins)")
        lbl_work.setObjectName("param_label")
        self._spin_work = QSpinBox()
        self._spin_work.setRange(5, 180)
        self._spin_work.setValue(25)
        self._spin_work.setObjectName("param_spin")
        work_col.addWidget(lbl_work)
        work_col.addWidget(self._spin_work)
        intervals_row.addLayout(work_col)

        # Break Mins
        break_col = QVBoxLayout()
        break_col.setSpacing(4)
        lbl_break = QLabel("Break (mins)")
        lbl_break.setObjectName("param_label")
        self._spin_break = QSpinBox()
        self._spin_break.setRange(1, 60)
        self._spin_break.setValue(5)
        self._spin_break.setObjectName("param_spin")
        break_col.addWidget(lbl_break)
        break_col.addWidget(self._spin_break)
        intervals_row.addLayout(break_col)

        # Total Cycles
        cycles_col = QVBoxLayout()
        cycles_col.setSpacing(4)
        lbl_cycles = QLabel("Cycles / Intervals")
        lbl_cycles.setObjectName("param_label")
        self._spin_cycles = QSpinBox()
        self._spin_cycles.setRange(1, 12)
        self._spin_cycles.setValue(4)
        self._spin_cycles.setObjectName("param_spin")
        cycles_col.addWidget(lbl_cycles)
        cycles_col.addWidget(self._spin_cycles)
        intervals_row.addLayout(cycles_col)

        layout.addLayout(intervals_row)

        # 4. Mode & Strict Mode
        lbl_mode = QLabel("FOCUS RESTRICTION PROFILE")
        lbl_mode.setObjectName("section_heading")
        layout.addWidget(lbl_mode)

        self._combo_mode = QComboBox()
        self._combo_mode.setObjectName("mode_combo")
        self._combo_mode.addItem("Deep Focus (Allowlist only)", "deep")
        self._combo_mode.addItem("Work (Block entertainment & social)", "work")
        self._combo_mode.addItem("Study (Block distracting sites)", "study")
        self._combo_mode.addItem("Custom (Your custom blocklist)", "custom")
        layout.addWidget(self._combo_mode)

        self._strict_check = QCheckBox("Strict Mode (Requires PIN verification to finish early or pause)")
        self._strict_check.setObjectName("strict_check")
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

        btn_start = QPushButton("Begin Deep Work")
        btn_start.setObjectName("btn_primary")
        btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(btn_start)

        layout.addLayout(btn_row)

    def _select_preset(self, pid: str, wm: int, bm: int, iv: int):
        self._preset = pid
        self._spin_work.setValue(wm)
        self._spin_break.setValue(bm)
        self._spin_cycles.setValue(iv)
        for btn, btn_pid in self._preset_buttons:
            btn.setChecked(btn_pid == pid)

    def _on_start(self):
        self._config_result = {
            "goal": self._goal_input.text().strip() or "Focused Work",
            "work_minutes": self._spin_work.value(),
            "break_minutes": self._spin_break.value(),
            "total_intervals": self._spin_cycles.value(),
            "preset": self._preset,
            "mode": self._combo_mode.currentData(),
            "strict_mode": self._strict_check.isChecked(),
        }
        self.accept()

    def get_config(self) -> Dict[str, Any]:
        return getattr(self, "_config_result", {})

    def _apply_theme(self):
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        bg = "#11151C" if is_dark else "#FFFFFF"
        border = tm.color("border")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        accent = tm.color("accent")

        self.setStyleSheet(f"""
            QDialog#deep_work_config_dialog {{
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
            QLabel#param_label {{
                font-size: 12px;
                font-weight: 600;
                color: {text_sub};
            }}
            QLineEdit#text_input, QComboBox#mode_combo, QSpinBox#param_spin {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 8px 12px;
                color: {text_main};
                font-size: 13px;
            }}
            QPushButton#preset_chip {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 8px 12px;
                color: {text_sub};
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#preset_chip:checked {{
                background-color: {tm.color('accent_emerald_bg')};
                border-color: {accent};
                color: {accent};
                font-weight: 700;
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
