"""
budget_dialog.py — Modal dialog for creating and editing Screen-Time Budgets in Notch v3.6.3.
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QSpinBox, QFrame, QStackedWidget, QWidget
)

from database.models import ScreenTimeBudget
from ui.theme import ThemeManager

CATEGORIES = [
    "Productivity",
    "Programming",
    "Gaming",
    "Communication",
    "Entertainment",
    "Social",
    "Browser",
    "Education",
    "Finance",
    "Utilities",
    "Other",
]


class BudgetDialog(QDialog):
    def __init__(self, budget: Optional[ScreenTimeBudget] = None, parent=None):
        super().__init__(parent)
        self._existing_budget = budget
        self.setWindowTitle("Edit Screen-Time Budget" if budget else "New Screen-Time Budget")
        self.setFixedSize(520, 560)
        self.setObjectName("budget_dialog")

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Badge
        badge = QLabel("DAILY SCREEN-TIME BUDGET")
        badge.setObjectName("badge_label")
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)

        title = QLabel("Edit Screen-Time Budget" if self._existing_budget else "Create Screen-Time Budget")
        title.setObjectName("dialog_title")
        layout.addWidget(title)

        desc = QLabel(
            "Set intentional daily limits. Receive alerts at 50%, 80%, and 100% of your budget, "
            "with optional hard enforcement upon limit exhaustion."
        )
        desc.setObjectName("dialog_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 1. Target Type
        lbl_type = QLabel("BUDGET TARGET TYPE")
        lbl_type.setObjectName("section_heading")
        layout.addWidget(lbl_type)

        self._type_combo = QComboBox()
        self._type_combo.setObjectName("form_combo")
        self._type_combo.addItem("Overall Daily Screen Time", "total")
        self._type_combo.addItem("Application Category", "category")
        self._type_combo.addItem("Specific Application", "app")
        layout.addWidget(self._type_combo)

        # 2. Target Name Stack
        lbl_name = QLabel("TARGET SELECTION")
        lbl_name.setObjectName("section_heading")
        layout.addWidget(lbl_name)

        self._target_stack = QStackedWidget()

        # Page 0: Total
        lbl_total = QLabel("Applies to all active computer usage across all applications.")
        lbl_total.setObjectName("dialog_desc")
        self._target_stack.addWidget(lbl_total)

        # Page 1: Category combo
        self._cat_combo = QComboBox()
        self._cat_combo.setObjectName("form_combo")
        for cat in CATEGORIES:
            self._cat_combo.addItem(cat, cat)
        self._target_stack.addWidget(self._cat_combo)

        # Page 2: App line edit
        self._app_input = QLineEdit()
        self._app_input.setObjectName("text_input")
        self._app_input.setPlaceholderText("e.g. chrome.exe, discord.exe, steam.exe")
        self._target_stack.addWidget(self._app_input)

        layout.addWidget(self._target_stack)

        self._type_combo.currentIndexChanged.connect(self._target_stack.setCurrentIndex)

        # 3. Daily Budget Duration
        lbl_time = QLabel("DAILY TIME LIMIT")
        lbl_time.setObjectName("section_heading")
        layout.addWidget(lbl_time)

        dur_box = QHBoxLayout()
        dur_box.setSpacing(12)

        self._hours_spin = QSpinBox()
        self._hours_spin.setObjectName("spin_box")
        self._hours_spin.setRange(0, 23)
        self._hours_spin.setValue(2)
        lbl_h = QLabel("hours")
        lbl_h.setObjectName("sub_label")

        self._mins_spin = QSpinBox()
        self._mins_spin.setObjectName("spin_box")
        self._mins_spin.setRange(0, 59)
        self._mins_spin.setValue(0)
        lbl_m = QLabel("minutes")
        lbl_m.setObjectName("sub_label")

        dur_box.addWidget(self._hours_spin)
        dur_box.addWidget(lbl_h)
        dur_box.addSpacing(16)
        dur_box.addWidget(self._mins_spin)
        dur_box.addWidget(lbl_m)
        dur_box.addStretch()
        layout.addLayout(dur_box)

        # 4. Enforce Lock Checkbox
        self._enforce_check = QCheckBox("Hard enforcement: Close/block target when daily budget is exhausted")
        self._enforce_check.setObjectName("enforce_checkbox")
        self._enforce_check.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._enforce_check)

        layout.addStretch()

        # 5. Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setObjectName("btn_cancel")
        self._btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel.clicked.connect(self.reject)

        self._btn_save = QPushButton("Save Budget")
        self._btn_save.setObjectName("btn_save")
        self._btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_save.clicked.connect(self._on_save)

        btn_row.addWidget(self._btn_cancel)
        btn_row.addWidget(self._btn_save)
        layout.addLayout(btn_row)

        # Populate if editing
        if self._existing_budget:
            idx = self._type_combo.findData(self._existing_budget.target_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
                self._target_stack.setCurrentIndex(idx)

            if self._existing_budget.target_type == "category":
                c_idx = self._cat_combo.findData(self._existing_budget.target_name)
                if c_idx >= 0:
                    self._cat_combo.setCurrentIndex(c_idx)
            elif self._existing_budget.target_type == "app":
                self._app_input.setText(self._existing_budget.target_name)

            h, m = divmod(self._existing_budget.daily_budget_seconds // 60, 60)
            self._hours_spin.setValue(h)
            self._mins_spin.setValue(m)
            self._enforce_check.setChecked(self._existing_budget.enforce_lock)

    def _on_save(self):
        t_type = self._type_combo.currentData()
        if t_type == "total":
            t_name = "Overall Screen Time"
        elif t_type == "category":
            t_name = self._cat_combo.currentData()
        else:
            t_name = self._app_input.text().strip()
            if not t_name:
                t_name = "Application"

        total_s = (self._hours_spin.value() * 3600) + (self._mins_spin.value() * 60)
        if total_s <= 0:
            total_s = 60  # Minimum 1 minute

        if self._existing_budget:
            self._existing_budget.target_type = t_type
            self._existing_budget.target_name = t_name
            self._existing_budget.daily_budget_seconds = total_s
            self._existing_budget.enforce_lock = self._enforce_check.isChecked()
        else:
            self._existing_budget = ScreenTimeBudget(
                target_type=t_type,
                target_name=t_name,
                daily_budget_seconds=total_s,
                is_enabled=True,
                enforce_lock=self._enforce_check.isChecked(),
            )
        self.accept()

    def get_budget(self) -> ScreenTimeBudget:
        return self._existing_budget

    def _apply_theme(self):
        tm = ThemeManager.instance()
        bg = tm.color("surface_card")
        border = tm.color("border")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        accent = tm.color("accent")
        accent_bg = tm.color("accent_primary_bg")

        self.setStyleSheet(f"""
            QDialog#budget_dialog {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 16px;
            }}
            QLabel#badge_label {{
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1px;
                color: {accent};
                background: {accent_bg};
                border: 1px solid {accent};
                border-radius: 4px;
                padding: 3px 8px;
            }}
            QLabel#dialog_title {{
                font-size: 20px;
                font-weight: 800;
                color: {text_main};
                letter-spacing: -0.3px;
            }}
            QLabel#dialog_desc {{
                font-size: 13px;
                color: {text_sub};
                line-height: 1.4;
            }}
            QLabel#section_heading {{
                font-size: 11px;
                font-weight: 700;
                color: {text_sub};
                letter-spacing: 0.8px;
            }}
            QLabel#sub_label {{
                font-size: 13px;
                font-weight: 600;
                color: {text_main};
            }}
            QLineEdit#text_input, QComboBox#form_combo, QSpinBox#spin_box {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 8px;
                color: {text_main};
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit#text_input:focus, QComboBox#form_combo:focus, QSpinBox#spin_box:focus {{
                border-color: {accent};
            }}
            QCheckBox#enforce_checkbox {{
                font-size: 13px;
                font-weight: 600;
                color: {text_main};
                spacing: 8px;
            }}
            QPushButton#btn_cancel {{
                background-color: transparent;
                border: 1px solid {border};
                border-radius: 8px;
                color: {text_sub};
                font-weight: 600;
                font-size: 13px;
                padding: 8px 18px;
            }}
            QPushButton#btn_cancel:hover {{
                background-color: {tm.color('surface_hover')};
                color: {text_main};
            }}
            QPushButton#btn_save {{
                background: {tm.color('primary_btn_gradient')};
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 24px;
            }}
        """)
