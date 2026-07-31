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


class DashboardPage(QWidget):
    """Premium visual Dashboard for Digital Wellbeing."""

    request_screen_time_details = Signal()
    request_focus_session = Signal()

    def __init__(self, on_global_refresh: Optional[Callable[[], None]] = None, navigate_callback: Optional[Callable[[int], None]] = None, parent=None) -> None:
        super().__init__(parent)
        self._on_global_refresh = on_global_refresh
        self._navigate = navigate_callback
        self._engine = AnalyticsEngine()
        self._current_score = 100
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
        header.setSpacing(20)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        self._greeting_label = QLabel("Welcome Back")
        self._greeting_label.setObjectName("page_title")
        
        self._date_label = QLabel("")
        self._date_label.setObjectName("page_subtitle")
        
        title_box.addWidget(self._greeting_label)
        title_box.addWidget(self._date_label)
        header.addLayout(title_box)

        header.addStretch()

        # Dynamic Daily Wellbeing Score Badge
        self._score_badge = QLabel("🌟 85/100 · Optimal Balance")
        self._score_badge.setObjectName("score_badge")
        self._score_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self._score_badge)

        self._refresh_btn = QPushButton("⚡ Refresh")
        self._refresh_btn.setObjectName("refresh_btn")
        self._refresh_btn.setFixedWidth(120)
        self._refresh_btn.setMinimumHeight(38)
        self._refresh_btn.clicked.connect(self._trigger_refresh)
        header.addWidget(self._refresh_btn)

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
        self._inner_layout.addWidget(self._screen_time_card)

        self._inner_layout.addStretch()

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        # Apply standard label styles
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
            QPushButton#refresh_btn {{
                background-color: {tm.color('card_bg')};
                color: {tm.color('text_main')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
                font-weight: 600;
            }}
            QPushButton#refresh_btn:hover {{
                background-color: {tm.color('card_hover')};
                border-color: {tm.color('border_hover')};
            }}
        """)
        
        # Apply semantic style to score badge
        if self._current_score >= 80:
            bg, border, text = tm.color("success_bg"), tm.color("success_border"), tm.color("success_text")
        elif self._current_score >= 50:
            bg, border, text = tm.color("info_bg"), tm.color("info_border"), tm.color("info_text")
        else:
            bg, border, text = tm.color("danger_bg"), tm.color("danger_border"), tm.color("danger_text")
            
        self._score_badge.setStyleSheet(f"""
            background-color: {bg}; color: {text};
            border: 1px solid {border}; border-radius: 20px;
            font-size: 13px; font-weight: 800; padding: 8px 18px;
        """)

    def _trigger_refresh(self) -> None:
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("⚡ Refreshing...")
        if self._on_global_refresh:
            self._on_global_refresh()
        else:
            self._refresh()
        QTimer.singleShot(400, lambda: self._refresh_btn.setText("⚡ Refresh") or self._refresh_btn.setEnabled(True))

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
        formatted_total = self._engine.format_duration(summary.total_screen_time_s)

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

        # Compute Daily Wellbeing Score
        active_s = summary.active_time_s
        productive_s = 0.0
        for item in summary.category_breakdown:
            cat_str = item["category"].lower()
            if cat_str in ("programming", "productivity", "education", "utilities"):
                productive_s += item["total_s"]

        if active_s > 0:
            prod_pct = int((productive_s / active_s) * 100)
            score = min(100, max(20, int(prod_pct * 0.85 + 25)))
        else:
            score = 100

        self._current_score = score
        if score >= 80:
            self._score_badge.setText(f"🌟 {score}/100 · Optimal Balance")
        elif score >= 50:
            self._score_badge.setText(f"⚖️ {score}/100 · Moderate Habit")
        else:
            self._score_badge.setText(f"⚠️ {score}/100 · High Screen Load")

        # Re-apply theme to instantly update the semantic colors based on new score
        from ui.theme import ThemeManager
        self._apply_theme(ThemeManager.instance().is_dark)

        # Update Screen Time Interactive Card
        self._screen_time_card.set_data(
            active_s=summary.active_time_s,
            category_breakdown=summary.category_breakdown,
            top_apps=summary.top_apps
        )

    def on_data_changed(self) -> None:
        self._refresh()
