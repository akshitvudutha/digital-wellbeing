"""
activity.py — Unified Activity & Trends Dashboard for Digital Wellbeing V2.
"""

from __future__ import annotations

import json
from datetime import date, timedelta, datetime
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget, QProgressBar
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

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo = Repository()
        self._engine = AnalyticsEngine()
        self._sm = SettingsManager()
        self._current_date = date.today()
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
        self._app_page = AppDetailsPage(on_back=self._navigate_back)
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
        title = QLabel("Activity & Trends")
        title.setObjectName("page_title")
        subtitle = QLabel("Interactive analytics dashboard. Click on the chart to explore historical data.")
        subtitle.setObjectName("page_subtitle")
        hdr_box.addWidget(title)
        hdr_box.addWidget(subtitle)
        self._content_layout.addLayout(hdr_box)

        # 1. Primary Navigation Graph
        self._chart = DailyScreenTimeChart()
        self._chart.day_selected.connect(self._on_day_selected)
        self._content_layout.addWidget(self._chart)
        
        # 2. Selected Day Header
        self._lbl_selected_date = QLabel()
        self._lbl_selected_date.setObjectName("selected_date_lbl")
        self._content_layout.addWidget(self._lbl_selected_date)

        # 3. Key Metrics Row
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(16)
        
        # Total Time & Goal
        time_card = QFrame()
        time_card.setObjectName("v2_card")
        tc_l = QVBoxLayout(time_card)
        tc_l.setContentsMargins(20, 16, 20, 16)
        self._lbl_total_time_hdr = QLabel("Total Screen Time")
        self._lbl_total_time_hdr.setObjectName("metric_hdr")
        tc_l.addWidget(self._lbl_total_time_hdr)
        self._lbl_total_time = QLabel()
        self._lbl_total_time.setObjectName("metric_val_success")
        tc_l.addWidget(self._lbl_total_time)
        
        self._goal_bar = QProgressBar()
        self._goal_bar.setFixedHeight(8)
        self._goal_bar.setTextVisible(False)
        tc_l.addWidget(self._goal_bar)
        
        self._lbl_goal_status = QLabel()
        self._lbl_goal_status.setObjectName("goal_status_lbl")
        tc_l.addWidget(self._lbl_goal_status)
        metrics_row.addWidget(time_card, 1)
        
        # Unlocks & Sessions
        stats_card = QFrame()
        stats_card.setObjectName("v2_card")
        sc_l = QVBoxLayout(stats_card)
        sc_l.setContentsMargins(20, 16, 20, 16)
        self._lbl_engagement_hdr = QLabel("Engagement")
        self._lbl_engagement_hdr.setObjectName("metric_hdr")
        sc_l.addWidget(self._lbl_engagement_hdr)
        
        self._lbl_unlocks = QLabel()
        self._lbl_unlocks.setObjectName("engagement_lbl")
        self._lbl_longest = QLabel()
        self._lbl_longest.setObjectName("engagement_lbl")
        self._lbl_avg = QLabel()
        self._lbl_avg.setObjectName("engagement_lbl")
        
        sc_l.addWidget(self._lbl_unlocks)
        sc_l.addWidget(self._lbl_longest)
        sc_l.addWidget(self._lbl_avg)
        sc_l.addStretch()
        metrics_row.addWidget(stats_card, 1)
        
        self._content_layout.addLayout(metrics_row)

        # 4. Smart Insights & Breakdown Row
        mid_row = QHBoxLayout()
        mid_row.setSpacing(20)
        
        self._insights_card = SmartInsightsCard()
        mid_row.addWidget(self._insights_card, 1)
        
        self._breakdown_card = CategoryBreakdownCard("🍩 Category Breakdown")
        self._breakdown_card.setCursor(Qt.CursorShape.PointingHandCursor)
        self._breakdown_card.mousePressEvent = self._on_category_card_clicked
        mid_row.addWidget(self._breakdown_card, 1)
        
        self._content_layout.addLayout(mid_row)
        
        # 5. Top Applications
        apps_hdr = QLabel("Top Applications")
        apps_hdr.setObjectName("section_header")
        self._content_layout.addWidget(apps_hdr)
        
        self._apps_layout = QVBoxLayout()
        self._apps_layout.setSpacing(8)
        self._content_layout.addLayout(self._apps_layout)
        
        

        self._content_layout.addStretch()

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
            QLabel#selected_date_lbl {{ font-size: 18px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#metric_hdr {{ color: {tm.color('text_sub')}; font-weight: 600; }}
            QLabel#metric_val_success {{ font-size: 24px; font-weight: 800; color: {tm.color('success_text')}; }}
            QLabel#goal_status_lbl {{ font-size: 12px; color: {tm.color('text_muted')}; }}
            QLabel#engagement_lbl {{ font-size: 15px; color: {tm.color('text_main')}; }}
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 1.2px; text-transform: uppercase; }}
        """)
        
        # Refresh dynamic styles (like the progress bar chunk colors)
        self._refresh()

    def _refresh(self) -> None:
        if self._main_stack.currentIndex() == 0:
            self._update_chart()
            self._update_day_details(self._current_date)

    def _update_chart(self) -> None:
        today = date.today()
        start_date = today - timedelta(days=6)
        daily_pts = self._engine.get_daily_chart_data(start_date, today)
        self._chart.update_data(daily_pts)
        
    def _on_day_selected(self, date_str: str) -> None:
        selected_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        self._current_date = selected_dt
        self._update_day_details(selected_dt)

    def _update_day_details(self, target_date: date) -> None:
        self._lbl_selected_date.setText(target_date.strftime("%A, %B %d, %Y"))
        
        is_today = target_date == date.today()
        
        if is_today:
            # Live data for today
            summary = self._engine.get_today_summary()
            total_s = summary.total_screen_time_s
            active_s = summary.active_time_s
            top_apps = summary.top_apps
            categories = summary.category_breakdown
            unlocks = self._repo.get_unlock_count_for_date(target_date)
            sessions = self._repo.get_sessions_for_date(target_date)
            
            # Serialize sessions to matching dictionary format
            timeline = []
            for s in sessions:
                timeline.append({
                    "process_name": s.process_name,
                    "window_title": s.window_title,
                    "start_time": s.start_time.isoformat(),
                    "duration_s": s.duration_s,
                    "category": s.category.value if hasattr(s.category, "value") else str(s.category)
                })
                
            self._insights_card.refresh() # Uses today summary internally
            self._current_apps_for_drilldown = top_apps
            self._current_active_s = active_s
            
        else:
            # Historical snapshot
            stat = self._repo.get_daily_stat(target_date)
            if not stat:
                # No data
                self._lbl_total_time.setText("0s")
                self._goal_bar.setValue(0)
                self._lbl_goal_status.setText("No data recorded")
                self._lbl_unlocks.setText("Device Unlocks: 0")
                self._lbl_longest.setText("Longest Session: 0s")
                self._lbl_avg.setText("Average Session: 0s")
                self._breakdown_card.set_data([], 0)
                self._clear_layout(self._apps_layout)
                self._insights_card.refresh(None) # Default empty refresh
                return
                
            total_s = stat.total_screen_time_s
            active_s = stat.active_time_s
            categories = json.loads(stat.category_usage_json)
            top_apps = json.loads(stat.app_usage_json)
            unlocks = stat.unlock_count
            timeline = json.loads(stat.timeline_json)
            
            self._insights_card.refresh(stat)
            self._current_apps_for_drilldown = top_apps
            self._current_active_s = active_s

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        # Populate Key Metrics
        self._lbl_total_time.setText(self._engine.format_duration(total_s))
        
        limit_m = self._sm.get_int("daily_limit_minutes", 480)
        limit_s = limit_m * 60
        pct = min(100, int((total_s / limit_s) * 100)) if limit_s > 0 else 0
        self._goal_bar.setValue(pct)
        if total_s > limit_s:
            self._goal_bar.setStyleSheet(f"QProgressBar {{ background-color: rgba(255, 255, 255, 0.05); border-radius: 4px; }} QProgressBar::chunk {{ background-color: {tm.color('danger_bg')}; border-radius: 4px; }}")
            self._lbl_goal_status.setText(f"Over goal by {self._engine.format_duration(total_s - limit_s)}")
        else:
            self._goal_bar.setStyleSheet(f"QProgressBar {{ background-color: rgba(255, 255, 255, 0.05); border-radius: 4px; }} QProgressBar::chunk {{ background-color: {tm.color('info_bg')}; border-radius: 4px; }}")
            self._lbl_goal_status.setText(f"{self._engine.format_duration(limit_s - total_s)} remaining today")

        self._lbl_unlocks.setText(f"📱 Device Unlocks: {unlocks}")
        
        longest = max([a.get("total_s", 0) for a in top_apps], default=0)
        self._lbl_longest.setText(f"⏳ Longest App Usage: {self._engine.format_duration(longest)}")
        
        avg = (total_s / len(timeline)) if timeline else 0
        self._lbl_avg.setText(f"⏱️ Average Session: {self._engine.format_duration(avg)}")
        
        # Populate Category Breakdown
        self._breakdown_card.set_data(categories, active_s)
        
        # Populate Top Apps
        self._clear_layout(self._apps_layout)
        for idx, app in enumerate(top_apps[:10]):
            name = app.get("process_name", "Unknown")
            disp = get_display_name(name)
            cat = app.get("category", "Other")
            row = AppUsageRow(
                rank=idx + 1,
                process_name=name,
                display_name=disp,
                category=cat,
                duration_s=app["total_s"],
                max_duration_s=longest,
            )
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.mousePressEvent = lambda event, pn=name: self._open_app_details(pn)
            self._apps_layout.addWidget(row)
            
            
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
