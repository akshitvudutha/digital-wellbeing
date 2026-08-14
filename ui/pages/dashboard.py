"""
dashboard.py — Premium Samsung/Apple inspired Dashboard Page for Digital Wellbeing.
Features minimal clutter, strong visual hierarchy, and large interactive cards.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from analytics.engine import AnalyticsEngine
from ui.widgets.hero_card import HeroCard
from ui.widgets.screen_time_card import ActiveScreenTimeCard
from ui.widgets.simple_category_row import ClickableCategoryCard

class ClickableCategoryRow(ClickableCategoryCard):
    clicked = Signal(str)
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        cat_name = self._category.value if hasattr(self._category, "value") else str(self._category)
        self.clicked.emit(cat_name)


class DashboardPage(QWidget):
    """Premium visual Dashboard for Digital Wellbeing."""

    request_screen_time_details = Signal()
    request_focus_session = Signal()
    request_category_details = Signal(str)
    request_app_details = Signal(str)

    def __init__(self, on_global_refresh: Optional[Callable[[], None]] = None, navigate_callback: Optional[Callable[[int], None]] = None, parent=None) -> None:
        super().__init__(parent)
        self._on_global_refresh = on_global_refresh
        self._navigate = navigate_callback
        self._engine = AnalyticsEngine()
        self._setup_ui()
        self._refresh()

        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 32, 36, 32)
        main_layout.setSpacing(0)

        # Header Row
        header = QHBoxLayout()
        header.setSpacing(24)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        from ui.widgets.fluent import FluentLabel, FluentButton, IconButton
        
        self._greeting_label = FluentLabel("Welcome Back", FluentLabel.Style.TITLE)
        self._date_label = FluentLabel("", FluentLabel.Style.SUBHEADING)
        
        title_box.addWidget(self._greeting_label)
        title_box.addWidget(self._date_label)
        header.addLayout(title_box)

        header.addStretch()

        self._refresh_btn = IconButton("↻")
        self._refresh_btn.setToolTip("Refresh Data")
        self._is_refreshing = False
        self._refresh_btn.clicked.connect(self._trigger_refresh)
        header.addWidget(self._refresh_btn, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(header)
        main_layout.addSpacing(32)

        # Scroll Container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        
        inner = QWidget()
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(28)
        scroll.setWidget(inner)
        main_layout.addWidget(scroll, 1)

        # 1. Hero Summary
        self._hero = HeroCard()
        self._hero.focus_requested.connect(self.request_focus_session.emit)
        # Clicking hero also goes to details
        self._hero.card_clicked.connect(self.request_screen_time_details.emit)
        self._inner_layout.addWidget(self._hero)

        # 2. Large Interactive Screen Time Card
        self._screen_time_card = ActiveScreenTimeCard()
        self._screen_time_card.card_clicked.connect(self.request_screen_time_details.emit)
        self._screen_time_card.app_clicked.connect(self._on_dashboard_app_clicked)
        self._inner_layout.addWidget(self._screen_time_card)

        self._inner_layout.addSpacing(16)

        # 3. Most Used Categories (Android style)
        from ui.widgets.fluent import FluentLabel
        self._cats_label = FluentLabel("Most Used Categories", FluentLabel.Style.HEADING)
        self._inner_layout.addWidget(self._cats_label)

        self._cats_container = QWidget()
        self._cats_layout = QHBoxLayout(self._cats_container)
        self._cats_layout.setContentsMargins(0, 0, 0, 0)
        self._cats_layout.setSpacing(16)
        self._cats_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._inner_layout.addWidget(self._cats_container)

        self._inner_layout.addStretch()

    def _on_dashboard_app_clicked(self, pname: str) -> None:
        print("Dashboard received signal")
        self.request_app_details.emit(pname)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        # Apply standard label styles
        # Apply standard label styles
        self.setStyleSheet(f"""
        """)

    def _trigger_refresh(self) -> None:
        if getattr(self, '_is_refreshing', False):
            return
        self._is_refreshing = True
        self._refresh_btn.set_spinning(True)
        
        if self._on_global_refresh:
            self._on_global_refresh()
        else:
            self._refresh()
            
        # Guarantee minimum rotation time for smooth UX
        QTimer.singleShot(700, self._finish_refresh)

    def _finish_refresh(self) -> None:
        self._refresh_btn.set_spinning(False)
        self._is_refreshing = False

    def _refresh(self) -> None:
        # Dynamic time-of-day greeting
        now = datetime.now()
        hour = now.hour
        if hour < 12:
            greeting = "Good Morning"
        elif hour < 17:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"
        self._greeting_label.setText(greeting)

        today = date.today()
        self._date_label.setText(today.strftime("%A, %B %d, %Y"))

        summary = self._engine.get_today_summary()
        formatted_total = self._engine.format_duration(summary.active_time_s)

        comp = self._engine.get_yesterday_comparison()
        pct = abs(comp["pct_change"])
        
        # Update Hero Card
        self._hero.set_data(
            formatted_total,
            pct,
            not comp["is_increase"],
            active_seconds=summary.active_time_s,
            category_breakdown=summary.category_breakdown,
        )

        # Update Screen Time Interactive Card
        self._screen_time_card.set_data(
            active_s=summary.active_time_s,
            category_breakdown=summary.category_breakdown,
            top_apps=summary.top_apps
        )
        
        # Update Top Categories
        while self._cats_layout.count():
            item = self._cats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        category_breakdown = summary.category_breakdown
        if not category_breakdown:
            from ui.theme import ThemeManager
            placeholder2 = QLabel("No category data recorded today.")
            placeholder2.setStyleSheet(f"color: {ThemeManager.instance().color('text_sub')}; font-size: 14px;")
            self._cats_layout.addWidget(placeholder2)
        else:
            sorted_cats2 = sorted(category_breakdown, key=lambda x: float(x.get("total_s", 0.0)), reverse=True)
            for item in sorted_cats2[:3]:
                dur = float(item.get("total_s", 0.0))
                if dur > 0:
                    row2 = ClickableCategoryRow(
                        category=item["category"],
                        duration_s=dur
                    )
                    row2.clicked.connect(self.request_category_details.emit)
                    self._cats_layout.addWidget(row2)

    def on_data_changed(self) -> None:
        self._refresh()
