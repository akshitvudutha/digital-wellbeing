"""
history.py — Daily History Timeline Page
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QPushButton
)
from database.repository import Repository
from analytics.engine import AnalyticsEngine
from ui.theme import ThemeManager

class HistoryTimelineItem(QFrame):
    def __init__(self, date_str: str, active_s: float, idle_s: float, top_app: str, parent=None):
        super().__init__(parent)
        self.setObjectName("timeline_item")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Left: Date
        date_lbl = QLabel(date_str)
        date_lbl.setObjectName("timeline_date")
        date_lbl.setFixedWidth(120)
        
        # Middle: Graph/Dot (Visual)
        dot = QLabel("●")
        dot.setObjectName("timeline_dot")
        
        # Right: Stats
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(4)
        
        active_lbl = QLabel(f"Active: {AnalyticsEngine.format_duration_short(active_s)}")
        active_lbl.setObjectName("timeline_stat")
        
        idle_lbl = QLabel(f"Idle: {AnalyticsEngine.format_duration_short(idle_s)}")
        idle_lbl.setObjectName("timeline_stat_sub")
        
        top_app_lbl = QLabel(f"Top App: {top_app if top_app else 'None'}")
        top_app_lbl.setObjectName("timeline_stat_sub")
        
        stats_layout.addWidget(active_lbl)
        stats_layout.addWidget(idle_lbl)
        stats_layout.addWidget(top_app_lbl)
        
        layout.addWidget(date_lbl, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(dot, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(stats_layout, 1)
        
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())
        self._apply_theme()
        
    def _apply_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#timeline_item {{
                background-color: {tm.color('surface')};
                border-left: 2px solid {tm.color('border')};
                border-bottom: 1px solid {tm.color('border')};
                margin-left: 20px;
                padding-left: 20px;
            }}
            QFrame#timeline_item:hover {{
                background-color: {tm.color('surface_elevated')};
            }}
            QLabel#timeline_date {{
                color: {tm.color('text_main')};
                font-size: 14px;
                font-weight: 700;
            }}
            QLabel#timeline_dot {{
                color: {tm.color('accent')};
                font-size: 18px;
            }}
            QLabel#timeline_stat {{
                color: {tm.color('text_main')};
                font-size: 14px;
                font-weight: 600;
            }}
            QLabel#timeline_stat_sub {{
                color: {tm.color('text_sub')};
                font-size: 12px;
            }}
        """)

class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo = Repository()
        self._setup_ui()
        
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)
        
        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("History Timeline")
        title.setObjectName("page_title")
        subtitle = QLabel("A chronological view of your daily screen time.")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        
        inner = QWidget()
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(0)
        scroll.setWidget(inner)
        
        layout.addWidget(scroll)
        
        self._build_timeline()
        self._inner_layout.addStretch()

    def _build_timeline(self):
        stats = self._repo.get_all_daily_stats()
        sorted_stats = sorted(stats, key=lambda x: x.date, reverse=True)
        
        if not sorted_stats:
            lbl = QLabel("No historical data available yet.")
            lbl.setObjectName("page_subtitle")
            self._inner_layout.addWidget(lbl)
            return
            
        for stat in sorted_stats:
            date_str = stat.date.strftime("%a, %b %d")
            item = HistoryTimelineItem(
                date_str=date_str,
                active_s=stat.active_time_s,
                idle_s=stat.idle_time_s,
                top_app=stat.top_app
            )
            self._inner_layout.insertWidget(self._inner_layout.count() - 1, item)

    def _apply_theme(self, is_dark: bool):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QLabel#page_title {{
                font-size: 28px;
                font-weight: 800;
                color: {tm.color('text_main')};
            }}
            QLabel#page_subtitle {{
                font-size: 15px;
                font-weight: 600;
                color: {tm.color('text_sub')};
            }}
        """)
        
    def on_data_changed(self):
        while self._inner_layout.count() > 1:
            item = self._inner_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._build_timeline()
