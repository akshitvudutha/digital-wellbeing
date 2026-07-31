from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional

from database.models import DailyStat
from database.repository import Repository


@dataclass
class PeriodSummary:
    total_screen_time_s: float
    active_time_s: float
    idle_time_s: float
    average_daily_s: float
    longest_session_s: float
    longest_session_app: Optional[str]
    top_apps: List[dict]
    category_breakdown: List[dict]
    days_tracked: int


@dataclass
class DailyPoint:
    day: str
    active_s: float
    idle_s: float


class AnalyticsEngine:
    def __init__(self) -> None:
        self._repo = Repository()

    def get_today_summary(self) -> PeriodSummary:
        today = date.today()
        return self._build_summary(today, today)

    def get_week_summary(self) -> PeriodSummary:
        today = date.today()
        start = today - timedelta(days=today.weekday())
        return self._build_summary(start, today)

    def get_month_summary(self) -> PeriodSummary:
        today = date.today()
        start = today.replace(day=1)
        return self._build_summary(start, today)

    def get_custom_summary(self, start: date, end: date) -> PeriodSummary:
        return self._build_summary(start, end)

    def _build_summary(self, start: date, end: date) -> PeriodSummary:
        top_apps = self._repo.get_top_apps_for_range(start, end, limit=10)
        category_breakdown = self._repo.get_category_breakdown_for_range(start, end)
        daily_totals = self._repo.get_daily_totals_for_range(start, end)
        longest = self._repo.get_longest_session_for_range(start, end)

        total_active = sum(d["active_s"] for d in daily_totals)
        total_idle = sum(d["idle_s"] for d in daily_totals)
        days = (end - start).days + 1
        avg_daily = total_active / max(len(daily_totals), 1)

        return PeriodSummary(
            total_screen_time_s=total_active + total_idle,
            active_time_s=total_active,
            idle_time_s=total_idle,
            average_daily_s=avg_daily,
            longest_session_s=longest.duration_s if longest else 0.0,
            longest_session_app=longest.process_name if longest else None,
            top_apps=top_apps,
            category_breakdown=category_breakdown,
            days_tracked=len(daily_totals),
        )

    def get_daily_chart_data(self, start: date, end: date) -> List[DailyPoint]:
        rows = self._repo.get_daily_totals_for_range(start, end)
        points: List[DailyPoint] = []

        current = start
        row_map = {r["day"]: r for r in rows}
        while current <= end:
            key = current.strftime("%Y-%m-%d")
            row = row_map.get(key)
            points.append(DailyPoint(
                day=key,
                active_s=row["active_s"] if row else 0.0,
                idle_s=row["idle_s"] if row else 0.0,
            ))
            current += timedelta(days=1)
        return points

    def get_hourly_chart_data(self, target_date: date) -> List[dict]:
        rows = self._repo.get_hourly_breakdown_for_date(target_date)
        hour_map = {r["hour"]: r["total_s"] for r in rows}
        return [
            {"hour": f"{h:02d}:00", "total_s": hour_map.get(f"{h:02d}", 0.0)}
            for h in range(24)
        ]

    def get_yesterday_comparison(self) -> dict:
        today = date.today()
        yesterday = today - timedelta(days=1)

        t_summary = self._build_summary(today, today)
        y_summary = self._build_summary(yesterday, yesterday)

        t_active = t_summary.active_time_s
        y_active = y_summary.active_time_s

        if y_active > 0:
            pct_change = ((t_active - y_active) / y_active) * 100.0
        else:
            pct_change = 0.0 if t_active == 0 else 100.0

        return {
            "today_active_s": t_active,
            "yesterday_active_s": y_active,
            "pct_change": pct_change,
            "is_increase": pct_change > 0,
        }

    def get_trend_insights(self) -> dict:
        today = date.today()
        this_week_start = today - timedelta(days=today.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(days=1)

        curr_week = self._build_summary(this_week_start, today)
        prev_week = self._build_summary(last_week_start, last_week_end)

        curr_active = curr_week.active_time_s
        prev_active = prev_week.active_time_s

        if prev_active > 0:
            week_pct_change = ((curr_active - prev_active) / prev_active) * 100.0
        else:
            week_pct_change = 0.0

        # Category shifts
        curr_cats = {c["category"].lower(): c["total_s"] for c in curr_week.category_breakdown}
        prev_cats = {c["category"].lower(): c["total_s"] for c in prev_week.category_breakdown}

        prod_curr = sum(curr_cats.get(k, 0.0) for k in ("programming", "productivity", "education", "utilities"))
        prod_prev = sum(prev_cats.get(k, 0.0) for k in ("programming", "productivity", "education", "utilities"))

        ent_curr = sum(curr_cats.get(k, 0.0) for k in ("entertainment", "social", "gaming"))
        ent_prev = sum(prev_cats.get(k, 0.0) for k in ("entertainment", "social", "gaming"))

        prod_change = ((prod_curr - prod_prev) / prod_prev * 100.0) if prod_prev > 0 else 0.0
        ent_change = ((ent_curr - ent_prev) / ent_prev * 100.0) if ent_prev > 0 else 0.0

        return {
            "week_pct_change": week_pct_change,
            "prod_change_pct": prod_change,
            "ent_change_pct": ent_change,
            "curr_week_active_s": curr_active,
            "prev_week_active_s": prev_active,
        }

    @staticmethod
    def format_duration(seconds: float) -> str:
        total = int(seconds)
        h, remainder = divmod(total, 3600)
        m, s = divmod(remainder, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    @staticmethod
    def format_duration_short(seconds: float) -> str:
        total = int(seconds)
        h, m = divmod(total // 60, 60)
        if h:
            return f"{h}h {m}m"
        return f"{m}m"

    def generate_daily_snapshot(self, target_date: date) -> None:
        """Computes and saves a historical snapshot for the given date."""
        summary = self._build_summary(target_date, target_date)
        sessions = self._repo.get_sessions_for_date(target_date)
        unlocks = self._repo.get_unlock_count_for_date(target_date)
        
        # Serialize Timeline
        timeline_data = []
        for s in sessions:
            timeline_data.append({
                "process_name": s.process_name,
                "window_title": s.window_title,
                "start_time": s.start_time.isoformat(),
                "duration_s": s.duration_s,
                "category": s.category.value if hasattr(s.category, "value") else str(s.category)
            })
            
        stat = DailyStat(
            date=target_date,
            total_screen_time_s=summary.total_screen_time_s,
            active_time_s=summary.active_time_s,
            idle_time_s=summary.idle_time_s,
            top_app=summary.longest_session_app,
            session_count=len(sessions),
            unlock_count=unlocks,
            category_usage_json=json.dumps(summary.category_breakdown),
            app_usage_json=json.dumps(summary.top_apps),
            timeline_json=json.dumps(timeline_data)
        )
        self._repo.upsert_daily_stat(stat)

    def ensure_historical_snapshots(self) -> None:
        """Backfills missing snapshots for all days that have tracking data, up to yesterday."""
        today = date.today()
        # Find all distinct days with sessions
        rows = self._repo.get_daily_totals_for_range(date(2000, 1, 1), today - timedelta(days=1))
        
        # Determine which days are already snapshotted
        existing_stats = self._repo.get_all_daily_stats()
        existing_dates = {s.date for s in existing_stats}
        
        for row in rows:
            d = date.fromisoformat(row["day"])
            if d not in existing_dates and d < today:
                self.generate_daily_snapshot(d)

