"""
primary_metric_card.py — The main 'Today's Screen Time' visual for the dashboard.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QColor, QFont
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
)
from ui.theme import ThemeManager

class PrimaryMetricCard(QFrame):
    card_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("primary_metric_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(8)

        self._title_lbl = QLabel("Today's Screen Time")
        self._title_lbl.setObjectName("metric_title")
        
        self._value_lbl = QLabel("0h 0m")
        self._value_lbl.setObjectName("metric_value")
        
        # Trend / Comparison
        trend_layout = QHBoxLayout()
        trend_layout.setSpacing(6)
        
        self._trend_icon = QLabel("↓")
        self._trend_icon.setObjectName("trend_icon")
        self._trend_lbl = QLabel("0% vs yesterday")
        self._trend_lbl.setObjectName("trend_text")
        
        trend_layout.addWidget(self._trend_icon)
        trend_layout.addWidget(self._trend_lbl)
        trend_layout.addStretch()
        
        layout.addWidget(self._title_lbl)
        layout.addWidget(self._value_lbl)
        layout.addLayout(trend_layout)
        layout.addStretch()

        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())

    def _apply_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#primary_metric_card {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 16px;
            }}
            QFrame#primary_metric_card:hover {{
                background: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border_hover')};
            }}
            QLabel#metric_title {{
                color: {tm.color('text_sub')};
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            QLabel#metric_value {{
                color: {tm.color('text_main')};
                font-size: 48px;
                font-weight: 800;
                letter-spacing: -1px;
            }}
            QLabel#trend_text {{
                color: {tm.color('text_sub')};
                font-size: 14px;
                font-weight: 500;
            }}
        """)

    def set_data(self, formatted_time: str, pct_change: float, is_decrease: bool, yesterday_was_zero: bool = False):
        self._value_lbl.setText(formatted_time)
        tm = ThemeManager.instance()
        if yesterday_was_zero or pct_change is None:
            self._trend_icon.setText("•")
            self._trend_icon.setStyleSheet(f"color: {tm.color('text_sub')}; font-weight: 800;")
            self._trend_lbl.setText("No meaningful baseline")
        elif pct_change == 0:
            self._trend_icon.setText("=")
            self._trend_icon.setStyleSheet(f"color: {tm.color('text_sub')}; font-weight: 800;")
            self._trend_lbl.setText("0% vs yesterday")
        elif is_decrease:
            self._trend_icon.setText("↓")
            self._trend_icon.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 800;")
            self._trend_lbl.setText(f"{pct_change:.1f}% vs yesterday")
        else:
            self._trend_icon.setText("↑")
            self._trend_icon.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 800;")
            self._trend_lbl.setText(f"{pct_change:.1f}% vs yesterday")

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.card_clicked.emit()
