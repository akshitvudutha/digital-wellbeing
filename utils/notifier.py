from __future__ import annotations

import logging
from analytics.engine import AnalyticsEngine
from core.constants import APP_NAME

logger = logging.getLogger(__name__)


class WellbeingNotifier:
    """Intelligent Windows notification generator for Screen Time & Weekly Summaries."""

    def __init__(self, tray_icon=None) -> None:
        self._tray = tray_icon
        self._engine = AnalyticsEngine()

    def set_tray_icon(self, tray_icon) -> None:
        self._tray = tray_icon

    def send_daily_summary(self) -> None:
        if not self._tray:
            return

        summary = self._engine.get_today_summary()
        tot_str = AnalyticsEngine.format_duration(summary.total_screen_time_s)
        top_app = summary.top_apps[0]["process_name"] if summary.top_apps else "None"

        title = f"{APP_NAME} — Daily Summary"
        message = f"Total Screen Time Today: {tot_str}\nTop Application: {top_app}"

        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 5000)
            logger.info("Sent daily summary notification: %s", message)
        except Exception as exc:
            logger.warning("Failed to dispatch daily summary notification: %s", exc)

    def send_weekly_summary(self) -> None:
        if not self._tray:
            return

        summary = self._engine.get_week_summary()
        trends = self._engine.get_trend_insights()

        tot_str = AnalyticsEngine.format_duration(summary.active_time_s)
        w_shift = trends["week_pct_change"]
        
        if trends.get("prev_week_was_zero", False) or w_shift == float('inf'):
            shift_text = "New activity"
        else:
            sign = "↑" if w_shift >= 0 else "↓"
            shift_text = f"{sign}{abs(w_shift):.0f}% vs last week"

        title = f"{APP_NAME} — Weekly Summary"
        message = (
            f"Screen Time This Week: {tot_str} ({shift_text})\n"
            f"Daily Average: {AnalyticsEngine.format_duration(summary.average_daily_s)}"
        )

        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 6000)
            logger.info("Sent weekly summary notification: %s", message)
        except Exception as exc:
            logger.warning("Failed to dispatch weekly summary notification: %s", exc)
