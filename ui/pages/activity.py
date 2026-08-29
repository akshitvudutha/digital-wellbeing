"""
activity.py — Unified Activity & Trends Dashboard for Digital Wellbeing V2.
"""

from __future__ import annotations

import json
from datetime import date, timedelta, datetime
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget, QProgressBar,
    QButtonGroup, QRadioButton
)

from analytics.engine import AnalyticsEngine
from database.repository import Repository
from database.models import DailyStat
from tracker.categorizer import display_name as get_display_name
from ui.widgets.app_row import AppUsageRow
from ui.widgets.charts import DailyScreenTimeChart
from ui.widgets.donut_chart import CategoryBreakdownCard
from ui.pages.category_details import CategoryDetailsPage
from ui.pages.app_details import AppDetailsPage
from ui.widgets.insights_card import SmartInsightsCard
from settings.manager import SettingsManager
from ui.widgets.animated_stacked_widget import AnimatedStackedWidget
class ActivityPage(QWidget):
    """Interactive Analytics Dashboard."""

    request_historical_details = Signal(date)

    def __init__(self, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._protection_manager = protection_manager
        self._repo = Repository()
        self._engine = AnalyticsEngine()
        self._sm = SettingsManager()
        self._current_date = date.today()
        self._chart_end_date = date.today()
        self._time_range = 7  # Default to 7 Days
        self._setup_ui()
        self._refresh()

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self._main_stack = AnimatedStackedWidget()
        main_layout.addWidget(self._main_stack)
        
        # 0: Activity Dashboard View
        self._dashboard_widget = QWidget()
        self._build_dashboard_view()
        self._main_stack.addWidget(self._dashboard_widget)
        
        # 1: Category Details
        self._category_page = CategoryDetailsPage(on_back=self._navigate_back)
        self._category_page.request_app_details.connect(self._open_app_details)
        self._main_stack.addWidget(self._category_page)
        
        # 2: App Details
        self._app_page = AppDetailsPage(on_back=self._navigate_back, protection_manager=self._protection_manager)
        self._main_stack.addWidget(self._app_page)
        
        self._navigation_history: list[int] = []

    def _build_dashboard_view(self) -> None:
        layout = QVBoxLayout(self._dashboard_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        inner = QWidget()
        self._content_layout = QVBoxLayout(inner)
        self._content_layout.setContentsMargins(32, 28, 32, 28)
        self._content_layout.setSpacing(24)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        # Header Title
        hdr_box = QVBoxLayout()
        hdr_box.setSpacing(4)
        title = QLabel("Usage & Trends")
        title.setObjectName("page_title")
        subtitle = QLabel("Comprehensive overview of your digital habits.")
        subtitle.setObjectName("page_subtitle")
        hdr_box.addWidget(title)
        hdr_box.addWidget(subtitle)
        self._content_layout.addLayout(hdr_box)

        # 1. Time Range Toggles
        self._range_group = QButtonGroup(self)
        range_layout = QHBoxLayout()
        range_layout.setSpacing(0)
        
        self._btn_today = QPushButton("Today")
        self._btn_today.setCheckable(True)
        self._btn_today.setObjectName("segment_btn_left")
        
        self._btn_7d = QPushButton("7 Days")
        self._btn_7d.setCheckable(True)
        self._btn_7d.setChecked(True)
        self._btn_7d.setObjectName("segment_btn_mid")
        
        self._btn_30d = QPushButton("30 Days")
        self._btn_30d.setCheckable(True)
        self._btn_30d.setObjectName("segment_btn_right")
        
        self._range_group.addButton(self._btn_today, 1)
        self._range_group.addButton(self._btn_7d, 7)
        self._range_group.addButton(self._btn_30d, 30)
        
        range_layout.addWidget(self._btn_today)
        range_layout.addWidget(self._btn_7d)
        range_layout.addWidget(self._btn_30d)
        range_layout.addStretch()
        
        self._range_group.idClicked.connect(self._on_range_changed)
        self._content_layout.addLayout(range_layout)
        
        # 2. Primary Navigation Graph
        self._chart = DailyScreenTimeChart()
        self._chart.day_selected.connect(self._on_day_selected)
        self._content_layout.addWidget(self._chart)

        # 3. Category Breakdown (New)
        lbl_cat = QLabel("Category Breakdown")
        lbl_cat.setObjectName("section_header")
        self._content_layout.addWidget(lbl_cat)
        
        from ui.widgets.flow_layout import FlowLayout
        self._category_layout = FlowLayout()
        self._category_layout.setSpacing(12)
        self._content_layout.addLayout(self._category_layout)
        
        # 4. Applications List (New)
        lbl_apps = QLabel("Top Applications")
        lbl_apps.setObjectName("section_header")
        self._content_layout.addWidget(lbl_apps)
        
        self._apps_layout = QVBoxLayout()
        self._apps_layout.setSpacing(8)
        self._content_layout.addLayout(self._apps_layout)

        # 5. Long Term Analytics Layout
        self._analytics_layout = QVBoxLayout()
        self._analytics_layout.setSpacing(20)
        self._content_layout.addLayout(self._analytics_layout)

        # Build Analytics UI dynamically in _refresh or _update_day_details
        self._build_analytics_cards()

        self._content_layout.addStretch()

    def _build_analytics_cards(self) -> None:
        # Clear existing
        while self._analytics_layout.count():
            item = self._analytics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Usage Summary Row
        lbl_usage = QLabel("Usage Summary")
        lbl_usage.setObjectName("section_header")
        self._analytics_layout.addWidget(lbl_usage)
        
        usage_row = QHBoxLayout()
        usage_row.setSpacing(16)
        
        self._lbl_avg_daily = self._create_stat_card("Average Daily", "0h 0m", usage_row)
        self._lbl_avg_weekly = self._create_stat_card("Average Weekly", "0h 0m", usage_row)
        self._lbl_avg_monthly = self._create_stat_card("Average Monthly", "0h 0m", usage_row)
        self._analytics_layout.addLayout(usage_row)
        
        # Trends Row
        lbl_trends = QLabel("Trends")
        lbl_trends.setObjectName("section_header")
        self._analytics_layout.addWidget(lbl_trends)
        
        trends_row = QHBoxLayout()
        trends_row.setSpacing(16)
        
        self._lbl_productive_day = self._create_stat_card("Most Productive Day", "-", trends_row)
        self._lbl_longest_session = self._create_stat_card("Longest Focus Session", "0h 0m", trends_row)
        self._analytics_layout.addLayout(trends_row)
        
        # Goals Row
        lbl_goals = QLabel("Goal Statistics")
        lbl_goals.setObjectName("section_header")
        self._analytics_layout.addWidget(lbl_goals)
        
        goals_row = QHBoxLayout()
        goals_row.setSpacing(16)
        
        self._lbl_current_streak = self._create_stat_card("Current Streak", "0 Days", goals_row)
        self._lbl_best_streak = self._create_stat_card("Best Streak", "0 Days", goals_row)
        self._analytics_layout.addLayout(goals_row)

    def _create_stat_card(self, title: str, default_val: str, layout: QHBoxLayout) -> QLabel:
        card = QFrame()
        card.setObjectName("v2_card")
        l = QVBoxLayout(card)
        l.setContentsMargins(20, 16, 20, 16)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("metric_hdr")
        l.addWidget(lbl_title)
        
        lbl_val = QLabel(default_val)
        lbl_val.setObjectName("metric_val_success")
        l.addWidget(lbl_val)
        
        layout.addWidget(card, 1)
        return lbl_val

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
            QLabel#metric_hdr {{ color: {tm.color('text_sub')}; font-weight: 600; }}
            QLabel#metric_val_success {{ font-size: 24px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 1.2px; margin-top: 10px; }}
            
            /* Segmented Control Buttons */
            QPushButton#segment_btn_left, QPushButton#segment_btn_mid, QPushButton#segment_btn_right {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                color: {tm.color('text_sub')};
                padding: 6px 16px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#segment_btn_left {{
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
                border-right: none;
            }}
            QPushButton#segment_btn_mid {{
                border-radius: 0px;
                border-right: none;
            }}
            QPushButton#segment_btn_right {{
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }}
            QPushButton#segment_btn_left:hover, QPushButton#segment_btn_mid:hover, QPushButton#segment_btn_right:hover {{
                background: {tm.color('surface_elevated')};
                color: {tm.color('text_main')};
            }}
            QPushButton#segment_btn_left:checked, QPushButton#segment_btn_mid:checked, QPushButton#segment_btn_right:checked {{
                background: {tm.color('accent')};
                color: #FFFFFF;
                border: 1px solid {tm.color('accent')};
            }}
        """)
        
        self._refresh()

    def _refresh(self) -> None:
        if self._main_stack.currentIndex() == 0:
            self._update_chart()

    def _update_chart(self) -> None:
        end_d = self._chart_end_date
        start_d = end_d - timedelta(days=self._time_range - 1)
        daily_pts = self._engine.get_daily_chart_data(start_d, end_d)
        
        # Don't show chart if it's just "Today"
        if self._time_range == 1:
            self._chart.setVisible(False)
        else:
            self._chart.setVisible(True)
            self._chart.update_data(daily_pts)
            
        summary = self._update_lists(start_d, end_d)
        self._update_day_details(start_d, end_d, summary)
        
    def _on_range_changed(self, range_id: int) -> None:
        self._time_range = range_id
        self._chart_end_date = date.today()
        self._refresh()
        
    def _update_lists(self, start_d: date, end_d: date) -> None:
        self._clear_layout(self._category_layout)
        self._clear_layout(self._apps_layout)
        
        # We need aggregated data for the range
        summary = self._engine.get_custom_summary(start_d, end_d)
        
        # Categories
        cat_breakdown = summary.category_breakdown
        if not cat_breakdown:
            lbl = QLabel("No category data recorded.")
            self._category_layout.addWidget(lbl)
        else:
            sorted_cats = sorted(cat_breakdown, key=lambda x: float(x.get("total_s", 0)), reverse=True)
            for item in sorted_cats:
                dur = float(item.get("total_s", 0))
                if dur > 60:  # Only show > 1 min
                    from ui.widgets.simple_category_row import ClickableCategoryCard
                    row = ClickableCategoryCard(item["category"], dur)
                    self._category_layout.addWidget(row)
                    
        # Apps
        top_apps = summary.top_apps
        if not top_apps:
            lbl = QLabel("No application data recorded.")
            self._apps_layout.addWidget(lbl)
        else:
            max_dur = top_apps[0]["total_s"] if top_apps else 0
            for i, app in enumerate(top_apps[:10]):
                if app["total_s"] > 60:
                    row = AppUsageRow(
                        rank=i+1,
                        process_name=app["process_name"],
                        display_name=app.get("display_name", app["process_name"]),
                        category=app["category"],
                        duration_s=app["total_s"],
                        max_duration_s=max_dur
                    )
                    self._apps_layout.addWidget(row)
        return summary
        
    def _on_day_selected(self, date_str: str) -> None:
        selected_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        self.request_historical_details.emit(selected_dt)

    def _update_day_details(self, start_d: date, end_d: date, summary) -> None:
        # Populate Long-Term Analytics
        long_term = self._engine.get_long_term_analytics()
        
        self._lbl_avg_daily.setText(self._engine.format_duration(summary.average_daily_s))
        
        if (end_d - start_d).days == 0:
            self._lbl_avg_weekly.setText(self._engine.format_duration(summary.average_daily_s * 7))
            self._lbl_avg_monthly.setText(self._engine.format_duration(summary.average_daily_s * 30))
        else:
            self._lbl_avg_weekly.setText(self._engine.format_duration(summary.average_daily_s * 7))
            self._lbl_avg_monthly.setText(self._engine.format_duration(summary.average_daily_s * 30))
        
        best_day = long_term.get("most_productive_day")
        if best_day:
            self._lbl_productive_day.setText(best_day.strftime("%A, %b %d"))
        else:
            self._lbl_productive_day.setText("-")
            
        if summary.longest_session_app:
            self._lbl_longest_session.setText(f"{get_display_name(summary.longest_session_app)} ({self._engine.format_duration_short(summary.longest_session_s)})")
        else:
            self._lbl_longest_session.setText("-")
        
        self._lbl_current_streak.setText(f"{long_term.get('current_streak', 0)} Days")
        self._lbl_best_streak.setText(f"{long_term.get('best_streak', 0)} Days")
    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def open_category_details(self, category_name: str) -> None:
        if hasattr(self, "_current_apps_for_drilldown"):
            self._category_page.set_data(category_name, self._current_apps_for_drilldown, getattr(self, "_current_active_s", 0))
            self._navigate_to(1)

    def _on_category_card_clicked(self, event) -> None:
        self.open_category_details("All Categories")
        
    def open_app_details(self, process_name: str) -> None:
        self._app_page.set_app(process_name)
        self._navigate_to(2)
        
    def _open_app_details(self, process_name: str) -> None:
        self.open_app_details(process_name)
        
    def _navigate_to(self, index: int) -> None:
        self._navigation_history.append(self._main_stack.currentIndex())
        self._main_stack.setCurrentIndex(index)
        
    def _navigate_back(self) -> None:
        if self._navigation_history:
            prev = self._navigation_history.pop()
            self._main_stack.setCurrentIndex(prev)
            if prev == 0:
                self._refresh()

    def on_data_changed(self) -> None:
        self._refresh()
