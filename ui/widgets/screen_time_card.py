"""
screen_time_card.py — Large Interactive Screen Time Card for Digital Wellbeing Dashboard.
Premium Samsung/Apple inspired design with glassmorphism.
"""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy
)

from analytics.engine import AnalyticsEngine
from tracker.categorizer import display_name as get_display_name
from core.constants import AppCategory
from ui.widgets.app_row import AppUsageRow
from ui.widgets.donut_chart import DonutChart


class ActiveScreenTimeCard(QFrame):
    """Large interactive card displaying today's screen time, donut chart, and top apps."""

    card_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("v2_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)

        # Header
        header_layout = QHBoxLayout()
        self._title = QLabel("Today's Active Screen Time")
        self._title.setObjectName("st_title")
        
        self._view_all = QLabel("View All >")
        self._view_all.setObjectName("st_view_all")
        self._view_all.setCursor(Qt.CursorShape.PointingHandCursor)
        
        header_layout.addWidget(self._title)
        header_layout.addStretch()
        header_layout.addWidget(self._view_all)
        layout.addLayout(header_layout)

        # Content Row (Donut + Top Apps)
        content_row = QHBoxLayout()
        content_row.setSpacing(48)

        # Left: Donut Chart & Total Time
        self._donut = DonutChart()
        self._donut.setMinimumSize(200, 200)
        content_row.addWidget(self._donut, 0, Qt.AlignmentFlag.AlignCenter)

        # Right: Top Apps List
        self._apps_layout = QVBoxLayout()
        self._apps_layout.setSpacing(12)
        self._apps_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_row.addLayout(self._apps_layout, 1)

        layout.addLayout(content_row)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#st_title {{ font-size: 16px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#st_view_all {{ font-size: 14px; font-weight: 600; color: {tm.color('accent')}; }}
            QLabel#st_placeholder {{ color: {tm.color('text_sub')}; font-size: 14px; }}
        """)

    def set_data(self, active_s: float, category_breakdown: List[dict], top_apps: List[dict]) -> None:
        # Convert category breakdown to segments
        from core.constants import CATEGORY_COLORS, AppCategory
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        segments = []
        if not category_breakdown or active_s <= 0:
            segments = [("Active", 1.0, tm.color('accent'))]
        else:
            sorted_cats = sorted(category_breakdown, key=lambda x: float(x.get("total_s", 0.0)), reverse=True)
            for item in sorted_cats[:5]:
                dur = float(item.get("total_s", 0.0))
                if dur > 0:
                    try:
                        cat_enum = AppCategory(item.get("category", "").lower())
                        color_hex = CATEGORY_COLORS.get(cat_enum, tm.color('accent'))
                    except ValueError:
                        color_hex = tm.color('accent')
                    segments.append((item.get("category", "").title(), dur, color_hex))
            
            remaining = sorted_cats[5:]
            if remaining:
                other_dur = sum(float(x.get("total_s", 0.0)) for x in remaining)
                if other_dur > 0:
                    segments.append(("Other", other_dur, tm.color('text_muted')))

        # Update Donut
        formatted_total = AnalyticsEngine.format_duration_short(active_s)
        self._donut.set_data(segments, center_text=formatted_total, center_subtext="Active Time")
        
        # Update Top Apps
        while self._apps_layout.count():
            item = self._apps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not top_apps:
            placeholder = QLabel("No application usage recorded today.")
            placeholder.setObjectName("st_placeholder")
            self._apps_layout.addWidget(placeholder)
            return
            
        max_dur = top_apps[0]["total_s"] if top_apps else 1.0
        
        for idx, s in enumerate(top_apps[:5]):
            row = AppUsageRow(
                rank=idx + 1,
                process_name=s["process_name"],
                display_name=get_display_name(s["process_name"]),
                category=AppCategory(s["category"]),
                duration_s=s["total_s"],
                max_duration_s=max_dur,
            )
            # Pass clicks through to the card
            row.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self._apps_layout.addWidget(row)
