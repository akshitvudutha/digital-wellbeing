"""
history.py — History Page for Digital Wellbeing V2.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QStackedWidget,
    QVBoxLayout, QWidget, QGridLayout, QSizePolicy
)

from analytics.engine import AnalyticsEngine
from database.repository import Repository
from database.models import DailyStat
from ui.pages.daily_report import DailyReportPage
from ui.pages.category_details import CategoryDetailsPage
from ui.pages.app_details import AppDetailsPage


class HistoryPage(QWidget):
    """History Page for browsing past daily snapshots."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo = Repository()
        self._engine = AnalyticsEngine()
        self._setup_ui()
        self._refresh()

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)
        
        # 0: Calendar/List View
        self._list_widget = QWidget()
        self._build_list_view()
        self._stack.addWidget(self._list_widget)
        
        # 1: Daily Report
        self._daily_report_page = DailyReportPage(on_back=self._navigate_back)
        self._daily_report_page.request_category_details.connect(self._open_category_details)
        self._daily_report_page.request_app_details.connect(self._open_app_details)
        self._stack.addWidget(self._daily_report_page)
        
        # 2: Category Details
        self._category_page = CategoryDetailsPage(on_back=self._navigate_back)
        self._category_page.request_app_details.connect(self._open_app_details)
        self._stack.addWidget(self._category_page)
        
        # 3: App Details
        self._app_page = AppDetailsPage(on_back=self._navigate_back)
        self._stack.addWidget(self._app_page)
        
        self._stack.setCurrentIndex(0)
        self._navigation_history: list[int] = []

    def _build_list_view(self) -> None:
        layout = QVBoxLayout(self._list_widget)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        hdr_box = QVBoxLayout()
        hdr_box.setSpacing(4)
        title = QLabel("History")
        title.setObjectName("page_title")
        subtitle = QLabel("Browse your past daily snapshots and historical data")
        subtitle.setObjectName("page_subtitle")
        hdr_box.addWidget(title)
        hdr_box.addWidget(subtitle)
        layout.addLayout(hdr_box)

        # Summaries row
        summaries_row = QHBoxLayout()
        summaries_row.setSpacing(16)
        
        self._lbl_total_days = QLabel("Days Tracked: —")
        self._lbl_total_days.setObjectName("lbl_total_days")
        
        self._lbl_avg_time = QLabel("Average Screen Time: —")
        self._lbl_avg_time.setObjectName("lbl_avg_time")
        
        summaries_row.addWidget(self._lbl_total_days)
        summaries_row.addWidget(self._lbl_avg_time)
        summaries_row.addStretch()
        layout.addLayout(summaries_row)

        # Days list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        self._days_layout = QVBoxLayout(inner)
        self._days_layout.setContentsMargins(0, 0, 0, 0)
        self._days_layout.setSpacing(10)
        scroll.setWidget(inner)
        
        layout.addWidget(scroll, 1)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
            QLabel#lbl_total_days {{ font-size: 14px; font-weight: 600; color: {tm.color('accent')}; }}
            QLabel#lbl_avg_time {{ font-size: 14px; font-weight: 600; color: {tm.color('success_text')}; }}
            QLabel#placeholder {{ color: {tm.color('text_muted')}; padding: 24px; font-size: 14px; }}
            QLabel#lbl_date {{ font-size: 16px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#lbl_day {{ font-size: 13px; color: {tm.color('text_sub')}; }}
            QLabel#lbl_time {{ font-weight: 600; color: {tm.color('success_text')}; }}
            QLabel#lbl_unlocks {{ color: {tm.color('text_sub')}; }}
        """)

    def _refresh(self) -> None:
        if self._stack.currentIndex() == 0:
            self._refresh_list()

    def _refresh_list(self) -> None:
        stats = self._repo.get_all_daily_stats(order_desc=True)
        
        while self._days_layout.count():
            item = self._days_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not stats:
            placeholder = QLabel("No historical data found. Data will appear after the first day of tracking.")
            placeholder.setObjectName("placeholder")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._days_layout.addWidget(placeholder)
            self._lbl_total_days.setText("Days Tracked: 0")
            self._lbl_avg_time.setText("Average Screen Time: 0s")
            return
            
        total_active_s = sum(s.active_time_s for s in stats)
        avg_active = total_active_s / len(stats)
        
        self._lbl_total_days.setText(f"Days Tracked: {len(stats)}")
        self._lbl_avg_time.setText(f"Average Screen Time: {self._engine.format_duration(avg_active)}")
        
        for stat in stats:
            card = QFrame()
            card.setObjectName("v2_card")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Make card clickable
            card.mousePressEvent = lambda event, s=stat: self._open_daily_report(s)
            
            c_l = QHBoxLayout(card)
            c_l.setContentsMargins(20, 16, 20, 16)
            c_l.setSpacing(20)
            
            # Date
            d_l = QVBoxLayout()
            lbl_date = QLabel(stat.date.strftime("%B %d, %Y"))
            lbl_date.setObjectName("lbl_date")
            lbl_day = QLabel(stat.date.strftime("%A"))
            lbl_day.setObjectName("lbl_day")
            d_l.addWidget(lbl_date)
            d_l.addWidget(lbl_day)
            
            # Stats
            s_l = QVBoxLayout()
            lbl_time = QLabel(f"Active: {self._engine.format_duration(stat.active_time_s)}")
            lbl_time.setObjectName("lbl_time")
            lbl_unlocks = QLabel(f"Unlocks: {stat.unlock_count}")
            lbl_unlocks.setObjectName("lbl_unlocks")
            s_l.addWidget(lbl_time)
            s_l.addWidget(lbl_unlocks)
            
            c_l.addLayout(d_l)
            c_l.addStretch()
            c_l.addLayout(s_l)
            
            self._days_layout.addWidget(card)
            
        self._days_layout.addStretch()

    def _open_daily_report(self, stat: DailyStat) -> None:
        self._daily_report_page.set_data(stat)
        self._navigate_to(1)
        
    def _open_category_details(self, category_name: str, app_data: list, total_time_s: float) -> None:
        self._category_page.set_data(category_name, app_data, total_time_s)
        self._navigate_to(2)
        
    def _open_app_details(self, process_name: str) -> None:
        self._app_page.set_app(process_name)
        self._navigate_to(3)

    def _navigate_to(self, index: int) -> None:
        self._navigation_history.append(self._stack.currentIndex())
        self._stack.setCurrentIndex(index)
        
    def _navigate_back(self) -> None:
        if self._navigation_history:
            prev = self._navigation_history.pop()
            self._stack.setCurrentIndex(prev)
            if prev == 0:
                self._refresh_list()

    def on_data_changed(self) -> None:
        self._refresh()
