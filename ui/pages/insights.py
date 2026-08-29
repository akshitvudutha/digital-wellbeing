"""
insights.py — Smart Insights & Analytics Highlights Page
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
)
from analytics.engine import AnalyticsEngine
from ui.theme import ThemeManager
from ui.widgets.flow_layout import FlowLayout
from ui.icons import get_icon

class InsightCard(QFrame):
    def __init__(self, icon: str, title: str, highlight: str, description: str, parent=None):
        super().__init__(parent)
        self.setObjectName("insight_card")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        
        # Header Row: [Icon] TITLE
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        icon_lbl = QLabel()
        icon_lbl.setObjectName("insight_icon")
        self._icon_lbl = icon_lbl
        self._icon_name = icon
        header_layout.addWidget(icon_lbl)
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("insight_title")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Metric
        highlight_lbl = QLabel(highlight)
        highlight_lbl.setObjectName("insight_highlight")
        layout.addWidget(highlight_lbl)
        
        # Context
        desc_lbl = QLabel(description)
        desc_lbl.setObjectName("insight_desc")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)
        
        layout.addStretch()
        
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())
        self._apply_theme()
        
    def _apply_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#insight_card {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QLabel#insight_icon {{
                background-color: transparent;
            }}
            QLabel#insight_title {{
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QLabel#insight_highlight {{
                color: {tm.color('text_main')};
                font-size: 26px;
                font-weight: 800;
                letter-spacing: -0.5px;
            }}
            QLabel#insight_desc {{
                color: {tm.color('text_sub')};
                font-size: 13px;
                line-height: 1.4;
            }}
        """)
        # Update pixmap with theme color (restrained accent color)
        pix = get_icon(self._icon_name, color=tm.color('accent'), size=16).pixmap(16, 16)
        self._icon_lbl.setPixmap(pix)
        
class InsightsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = AnalyticsEngine()
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
        title = QLabel("Smart Insights")
        title.setObjectName("page_title")
        subtitle = QLabel("AI-driven observations about your digital wellbeing habits.")
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
        self._inner_layout.setSpacing(32)
        scroll.setWidget(inner)
        
        layout.addWidget(scroll)
        
        # 1. Key Insight Section
        self._key_insight_container = QVBoxLayout()
        self._key_insight_container.setSpacing(12)
        self._inner_layout.addLayout(self._key_insight_container)
        
        # 2. Today's Breakdown Section
        self._breakdown_container = QVBoxLayout()
        self._breakdown_container.setSpacing(12)
        self._inner_layout.addLayout(self._breakdown_container)
        
        # 3. Grid Section
        self._grid_container = QVBoxLayout()
        self._grid_container.setSpacing(12)
        
        # Grid content uses FlowLayout
        self._grid_content = QWidget()
        self._grid_layout = FlowLayout(self._grid_content, margin=0, hSpacing=16, vSpacing=16)
        self._grid_container.addWidget(self._grid_content)
        
        self._inner_layout.addLayout(self._grid_container)
        self._inner_layout.addStretch()
        
        # Dynamic insights
        self._build_insights()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _build_insights(self):
        # Clear existing
        self._clear_layout(self._key_insight_container)
        self._clear_layout(self._breakdown_container)
        self._clear_layout(self._grid_layout)
                
        # Generate some insights
        summary = self._engine.get_today_summary()
        long_term = self._engine.get_long_term_analytics()
        
        cats = summary.category_breakdown
        top_cat = cats[0]['category'] if cats else "Unknown"
        top_cat_dur = self._engine.format_duration(cats[0]['total_s']) if cats else "0h"
        
        # 1. Key Insight Panel
        c_key = InsightCard(
            "bar_chart", "Top Category",
            f"{top_cat}",
            f"{top_cat_dur} today. This is your most active category."
        )
        c_key.setMinimumHeight(140)
        self._key_insight_container.addWidget(c_key)
        
        # 2. Today's Breakdown
        donut_title = QLabel("Today's Breakdown")
        donut_title.setObjectName("section_title")
        self._breakdown_container.addWidget(donut_title)
        
        breakdown_row = QHBoxLayout()
        breakdown_row.setSpacing(24)
        
        from ui.widgets.donut_chart import DonutChart
        self._donut = DonutChart()
        self._donut.setFixedSize(240, 240)
        
        # Donut Chart Card
        donut_card = QFrame()
        donut_card.setObjectName("insight_card")
        donut_layout = QVBoxLayout(donut_card)
        donut_layout.setContentsMargins(16, 16, 16, 16)
        donut_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        donut_layout.addWidget(self._donut)
        
        # Build segments for donut
        segments = []
        if not cats:
            from ui.theme import ThemeManager
            segments = [("No Data", 1.0, ThemeManager.instance().color('text_muted'))]
        else:
            fluent_palette = ["#4F8CFF", "#20C997", "#00C4FF", "#9C27B0", "#FF9800"]
            for idx, item in enumerate(cats[:5]):
                dur = float(item.get("total_s", 0.0))
                if dur > 0:
                    from ui.theme import ThemeManager
                    color = fluent_palette[idx] if idx < len(fluent_palette) else ThemeManager.instance().color('text_muted')
                    segments.append((item['category'], dur, color))
                    
        total_s_dur = self._engine.format_duration_short(summary.total_screen_time_s)
        self._donut.set_data(segments, center_text=total_s_dur, center_subtext="TOTAL SCREEN TIME")
        
        breakdown_row.addWidget(donut_card)
        
        # Category Summary List
        cat_summary_card = QFrame()
        cat_summary_card.setObjectName("insight_card")
        cat_layout = QVBoxLayout(cat_summary_card)
        cat_layout.setContentsMargins(24, 20, 24, 20)
        cat_layout.setSpacing(12)
        
        cat_hdr = QLabel("Categories")
        cat_hdr.setObjectName("insight_title")
        cat_layout.addWidget(cat_hdr)
        
        if cats:
            from ui.theme import ThemeManager
            tm = ThemeManager.instance()
            for item in cats[:4]:
                dur = float(item.get("total_s", 0.0))
                if dur > 60:
                    row = QHBoxLayout()
                    lbl_name = QLabel(item['category'])
                    lbl_name.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {tm.color('text_main')};")
                    lbl_dur = QLabel(self._engine.format_duration_short(dur))
                    lbl_dur.setStyleSheet(f"font-size: 14px; font-family: monospace; color: {tm.color('text_sub')};")
                    row.addWidget(lbl_name)
                    row.addStretch()
                    row.addWidget(lbl_dur)
                    cat_layout.addLayout(row)
        else:
            cat_layout.addWidget(QLabel("No categories tracked today."))
            
        cat_layout.addStretch()
        breakdown_row.addWidget(cat_summary_card, 1)
        
        self._breakdown_container.addLayout(breakdown_row)
        
        # 3. Grid Section
        grid_title = QLabel("Additional Insights")
        grid_title.setObjectName("section_title")
        self._grid_container.insertWidget(0, grid_title)
        
        best_day = long_term.get("most_productive_day")
        best_day_str = best_day.strftime("%A") if best_day else "N/A"
        
        if best_day:
            c1 = InsightCard(
                "flame", "Productivity Pattern",
                f"{best_day_str}",
                "This is currently your strongest day based on focus duration."
            )
            c1.setFixedWidth(280)
            self._grid_layout.addWidget(c1)
        
        streak = long_term.get('current_streak', 0)
        if streak >= 3:
            c3 = InsightCard(
                "sparkles", "Goal Progress",
                f"{streak} days",
                "You are consistently keeping your idle time low."
            )
            c3.setFixedWidth(280)
            self._grid_layout.addWidget(c3)
        


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
            QLabel#section_title {{
                font-size: 16px;
                font-weight: 800;
                color: {tm.color('text_main')};
                margin-top: 12px;
                margin-bottom: 4px;
            }}
        """)
        
    def on_data_changed(self):
        self._build_insights()
