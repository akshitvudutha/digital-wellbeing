"""
insights_card.py — Smart Digital Wellbeing Insights card with personalized suggestions and glowing One UI styling.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from analytics.engine import AnalyticsEngine
from tracker.categorizer import display_name as get_display_name


class SmartInsightsCard(QFrame):
    """Smart Digital Wellbeing Insights card with personalized health suggestions."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("v2_card")
        self._engine = AnalyticsEngine()
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        hdr = QHBoxLayout()
        self._lbl = QLabel("💡 Smart Wellbeing Insights")
        self._lbl.setObjectName("section_header")
        hdr.addWidget(self._lbl)
        hdr.addStretch()
        layout.addLayout(hdr)

        self._tips_layout = QVBoxLayout()
        self._tips_layout.setSpacing(10)
        layout.addLayout(self._tips_layout)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 1.2px; text-transform: uppercase; }}
            QLabel#insight_text {{ color: {tm.color('text_main')}; font-size: 13px; font-weight: 500; line-height: 1.4; }}
        """)
        
        # Trigger a refresh to re-render the tip colors
        if hasattr(self, "_last_stat"):
            self.refresh(self._last_stat)
        else:
            self.refresh()

    def refresh(self, stat=None) -> None:
        self._last_stat = stat
        while self._tips_layout.count():
            item = self._tips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if stat is None:
            summary = self._engine.get_today_summary()
            tips = self._generate_tips_from_summary(summary)
        else:
            tips = self._generate_tips_from_stat(stat)

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        for tip, icon, color in tips:
            row = QFrame()
            row.setStyleSheet(
                f"background-color: {tm.color('card_hover')}; "
                f"border: 1px solid {tm.color('border')}; "
                f"border-left: 4px solid {color}; "
                f"border-radius: 12px;"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 12, 14, 12)
            rl.setSpacing(12)

            # Icon circle pill
            ic_box = QLabel(icon)
            ic_box.setFixedSize(36, 36)
            ic_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic_box.setStyleSheet(
                f"background-color: {color}18; color: {color}; border: 1px solid {color}30; border-radius: 10px; font-size: 16px;"
            )

            t_lbl = QLabel(tip)
            t_lbl.setObjectName("insight_text")
            t_lbl.setWordWrap(True)

            rl.addWidget(ic_box)
            rl.addWidget(t_lbl, 1)
            self._tips_layout.addWidget(row)

    def _generate_tips_from_summary(self, summary) -> list[tuple[str, str, str]]:
        tips = []
        total_s = summary.total_screen_time_s
        active_s = summary.active_time_s
        
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        if total_s == 0:
            tips.append(("Tracking has started. Your screen time insights and personalized habits will update automatically as you use applications today.", "🌱", tm.color('accent')))
            return tips

        # Productive time ratio calculation
        productive_s = 0.0
        for item in summary.category_breakdown:
            cat_name = item["category"].lower()
            if cat_name in ("programming", "productivity", "education", "utilities"):
                productive_s += item["total_s"]

        if active_s > 0:
            prod_pct = (productive_s / active_s) * 100
            if prod_pct >= 60:
                tips.append((f"Great productivity flow today! {prod_pct:.0f}% of your screen time is focused high-value work.", "🎯", tm.color('success_text')))
            elif prod_pct < 30 and active_s > 1800:
                tips.append(("High entertainment/social load detected. Consider starting a 25-minute Pomodoro focus session to recalibrate.", "⌛", tm.color('warning_text')))

        # Screen time total threshold
        if total_s > 6 * 3600:
            tips.append(("Screen time exceeded 6 hours today. Remember to follow the 20-20-20 eye rest rule: look 20 feet away for 20 seconds.", "👀", tm.color('danger_text')))
        elif total_s < 2 * 3600:
            tips.append(("Moderate screen time today. Perfectly balanced digital routine detected.", "✨", tm.color('accent')))

        # Top app highlight
        if summary.top_apps:
            top_app_name = get_display_name(summary.top_apps[0]["process_name"])
            top_app_dur = AnalyticsEngine.format_duration_short(summary.top_apps[0]["total_s"])
            tips.append((f"Primary daily focus right now is {top_app_name} with {top_app_dur} of active engagement.", "📊", tm.color('info_text')))

        return tips[:3]

    def _generate_tips_from_stat(self, stat) -> list[tuple[str, str, str]]:
        tips = []
        total_s = stat.total_screen_time_s
        active_s = stat.active_time_s
        
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        import json
        categories = json.loads(stat.category_usage_json)
        apps = json.loads(stat.app_usage_json)

        productive_s = 0.0
        for item in categories:
            cat_name = item["category"].lower()
            if cat_name in ("programming", "productivity", "education", "utilities"):
                productive_s += item["total_s"]

        if active_s > 0:
            prod_pct = (productive_s / active_s) * 100
            if prod_pct >= 60:
                tips.append((f"Great productivity flow! {prod_pct:.0f}% of screen time was focused high-value work.", "🎯", tm.color('success_text')))
            elif prod_pct < 30 and active_s > 1800:
                tips.append(("High entertainment/social load detected on this day.", "⌛", tm.color('warning_text')))

        if total_s > 6 * 3600:
            tips.append(("Screen time exceeded 6 hours.", "👀", tm.color('danger_text')))
        elif total_s < 2 * 3600:
            tips.append(("Moderate screen time. Perfectly balanced digital routine.", "✨", tm.color('accent')))

        if apps:
            top_app_name = get_display_name(apps[0]["process_name"])
            top_app_dur = AnalyticsEngine.format_duration_short(apps[0]["total_s"])
            tips.append((f"Primary focus was {top_app_name} with {top_app_dur} of active engagement.", "📊", tm.color('info_text')))

        return tips[:3]
