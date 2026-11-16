"""
budget_card.py — Visual card representing a Screen-Time Budget in Notch v3.6.3.
Displays current active usage vs daily limit, dynamic color-coded progress,
milestone warnings, toggle switch, and configuration actions.
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QSizePolicy
)

from database.models import ScreenTimeBudget
from ui.theme import ThemeManager
from utils.time_format import format_duration


def _format_time_short(seconds: float) -> str:
    return format_duration(seconds, compact=True)


class BudgetCard(QFrame):
    toggled = Signal(int, bool)          # budget_id, is_enabled
    edit_requested = Signal(int)         # budget_id
    delete_requested = Signal(int)       # budget_id

    def __init__(self, budget: ScreenTimeBudget, used_s: int = 0, parent=None):
        super().__init__(parent)
        self.budget = budget
        self.used_s = used_s
        self.setObjectName("budget_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Row 1: Badges, Title, Status Pill, Action Buttons ────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Type Badge
        self._lbl_type = QLabel(self.budget.target_type.upper())
        self._lbl_type.setObjectName(f"type_badge_{self.budget.target_type}")
        top_row.addWidget(self._lbl_type)

        if self.budget.enforce_lock:
            self._lbl_enforce = QLabel("HARD LOCK")
            self._lbl_enforce.setObjectName("enforce_badge")
            top_row.addWidget(self._lbl_enforce)

        # Target Name
        name_display = self.budget.target_name
        if self.budget.target_type == "total":
            name_display = "Overall Screen Time"
        self._lbl_name = QLabel(name_display)
        self._lbl_name.setObjectName("card_title")
        top_row.addWidget(self._lbl_name)
        top_row.addStretch()

        # Status Pill
        self._lbl_status = QLabel("")
        top_row.addWidget(self._lbl_status)

        # Toggle Button
        self._btn_toggle = QPushButton("Enabled" if self.budget.is_enabled else "Disabled")
        self._btn_toggle.setObjectName("btn_toggle_active" if self.budget.is_enabled else "btn_toggle_inactive")
        self._btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_toggle.clicked.connect(self._on_toggle)
        top_row.addWidget(self._btn_toggle)

        # Edit Button
        self._btn_edit = QPushButton("Edit")
        self._btn_edit.setObjectName("btn_action")
        self._btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.budget.id or 0))
        top_row.addWidget(self._btn_edit)

        # Delete Button
        self._btn_del = QPushButton("Delete")
        self._btn_del.setObjectName("btn_delete")
        self._btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_del.clicked.connect(lambda: self.delete_requested.emit(self.budget.id or 0))
        top_row.addWidget(self._btn_del)

        layout.addLayout(top_row)

        # ── Row 2: Subtitle Caption ──────────────────────────────────────────
        self._lbl_sub = QLabel("")
        self._lbl_sub.setObjectName("card_sub")
        layout.addWidget(self._lbl_sub)

        # ── Row 3: Progress Bar & Percentage ─────────────────────────────────
        prog_row = QHBoxLayout()
        prog_row.setSpacing(12)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setFixedHeight(7)
        self._progress.setTextVisible(False)
        self._progress.setObjectName("budget_progress_bar")
        prog_row.addWidget(self._progress, 1)

        self._lbl_pct = QLabel("0%")
        self._lbl_pct.setObjectName("card_pct")
        prog_row.addWidget(self._lbl_pct)

        layout.addLayout(prog_row)

        self.update_progress(self.used_s)

    def update_progress(self, used_s: int):
        self.used_s = used_s
        budget_s = max(1, self.budget.daily_budget_seconds)
        pct = min(100.0, (used_s / budget_s) * 100.0)
        remaining_s = max(0, budget_s - used_s)

        # Progress bar & label
        self._progress.setValue(int(pct))
        self._lbl_pct.setText(f"{int(pct)}%")

        # Subtitle
        self._lbl_sub.setText(
            f"{_format_time_short(used_s)} used  /  {self.budget.budget_formatted} daily limit  ·  Resets at midnight"
        )

        # Status Pill
        if used_s >= budget_s:
            self._lbl_status.setText("Limit reached")
            self._lbl_status.setObjectName("pill_exceeded")
        elif pct >= 80:
            self._lbl_status.setText(f"80% reached • {_format_time_short(remaining_s)} left")
            self._lbl_status.setObjectName("pill_warning")
        elif pct >= 50:
            self._lbl_status.setText(f"Halfway • {_format_time_short(remaining_s)} left")
            self._lbl_status.setObjectName("pill_halfway")
        else:
            self._lbl_status.setText(f"{_format_time_short(remaining_s)} left")
            self._lbl_status.setObjectName("pill_ok")

        self._apply_theme()

    def _on_toggle(self):
        new_val = not self.budget.is_enabled
        self.budget.is_enabled = new_val
        self._btn_toggle.setText("Enabled" if new_val else "Disabled")
        self._btn_toggle.setObjectName("btn_toggle_active" if new_val else "btn_toggle_inactive")
        self._apply_theme()
        if self.budget.id:
            self.toggled.emit(self.budget.id, new_val)

    def _apply_theme(self):
        tm = ThemeManager.instance()
        card_bg = tm.color("surface_card")
        border = tm.color("border")
        border_hover = tm.color("border_hover")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        accent = tm.color("accent")
        accent_bg = tm.color("accent_primary_bg")

        # Dynamic chunk color based on percentage
        pct = (self.used_s / max(1, self.budget.daily_budget_seconds)) * 100.0
        if pct >= 100:
            chunk_col = "#EF4444"  # Red
        elif pct >= 80:
            chunk_col = "#F97316"  # Orange
        elif pct >= 50:
            chunk_col = "#F59E0B"  # Amber
        else:
            chunk_col = "#10B981"  # Emerald

        self.setStyleSheet(f"""
            QFrame#budget_card {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QFrame#budget_card:hover {{
                border-color: {border_hover};
            }}
            QLabel#card_title {{
                font-size: 15px;
                font-weight: 700;
                color: {text_main};
            }}
            QLabel#card_sub {{
                font-size: 12px;
                font-weight: 500;
                color: {text_sub};
            }}
            QLabel#card_pct {{
                font-size: 12px;
                font-weight: 700;
                color: {text_sub};
                font-family: monospace;
            }}
            QLabel#type_badge_total {{
                background-color: rgba(59, 130, 246, 0.15);
                color: #3B82F6;
                border: 1px solid #3B82F6;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
                padding: 2px 7px;
                letter-spacing: 0.5px;
            }}
            QLabel#type_badge_category {{
                background-color: rgba(16, 185, 129, 0.15);
                color: #10B981;
                border: 1px solid #10B981;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
                padding: 2px 7px;
                letter-spacing: 0.5px;
            }}
            QLabel#type_badge_app {{
                background-color: rgba(168, 85, 247, 0.15);
                color: #A855F7;
                border: 1px solid #A855F7;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
                padding: 2px 7px;
                letter-spacing: 0.5px;
            }}
            QLabel#enforce_badge {{
                background-color: rgba(239, 68, 68, 0.15);
                color: #EF4444;
                border: 1px solid #EF4444;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
                padding: 2px 7px;
                letter-spacing: 0.5px;
            }}
            QLabel#pill_ok {{
                background-color: rgba(16, 185, 129, 0.15);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 8px;
                font-size: 11px;
                font-weight: 700;
                padding: 2px 8px;
            }}
            QLabel#pill_halfway {{
                background-color: rgba(245, 158, 11, 0.15);
                color: #F59E0B;
                border: 1px solid rgba(245, 158, 11, 0.3);
                border-radius: 8px;
                font-size: 11px;
                font-weight: 700;
                padding: 2px 8px;
            }}
            QLabel#pill_warning {{
                background-color: rgba(249, 115, 22, 0.15);
                color: #F97316;
                border: 1px solid rgba(249, 115, 22, 0.3);
                border-radius: 8px;
                font-size: 11px;
                font-weight: 700;
                padding: 2px 8px;
            }}
            QLabel#pill_exceeded {{
                background-color: rgba(239, 68, 68, 0.18);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 8px;
                font-size: 11px;
                font-weight: 700;
                padding: 2px 8px;
            }}
            QProgressBar#budget_progress_bar {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 3px;
            }}
            QProgressBar#budget_progress_bar::chunk {{
                background: {chunk_col};
                border-radius: 3px;
            }}
            QPushButton#btn_toggle_active {{
                background-color: {accent_bg};
                border: 1px solid {accent};
                color: {accent};
                border-radius: 8px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton#btn_toggle_inactive {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                color: {text_sub};
                border-radius: 8px;
                padding: 5px 12px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#btn_action {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                color: {text_main};
                border-radius: 8px;
                padding: 5px 12px;
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
                padding: 5px 12px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#btn_delete:hover {{
                background-color: rgba(239, 68, 68, 0.12);
            }}
        """)
