"""
weekly_report.py — 7-Day Comparative Weekly Wellbeing Analytics Generator for Notch v3.6.3.
Calculates weekly screen-time volume, prior-week deltas, top app shifts, category allocation,
deep work session completion rates, and factual wellbeing insights.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

from database.repository import Repository
from tracker.categorizer import display_name as get_friendly_name
from utils.time_format import format_duration as _format_duration


def format_duration(seconds: float) -> str:
    return _format_duration(seconds)


def format_delta_time(seconds: float) -> str:
    sign = "+" if seconds >= 0 else "-"
    return f"{sign}{_format_duration(abs(seconds), compact=True)}"


@dataclass
class WeeklyReportData:
    start_date: date
    end_date: date
    prior_start_date: date
    prior_end_date: date

    # Totals
    curr_active_s: float
    curr_idle_s: float
    prior_active_s: float
    prior_idle_s: float
    active_delta_s: float
    active_delta_pct: Optional[float]
    daily_avg_active_s: float

    # Detailed breakdowns
    daily_breakdown: List[dict]
    top_apps_shifts: List[dict]
    category_breakdown: List[dict]
    deep_work_stats: dict
    insights: List[str]
    peak_day_name: str
    peak_day_active_s: float


class WeeklyReportGenerator:
    """Computes comprehensive 7-day comparative analytics from local SQLite activity."""

    def __init__(self, repo: Optional[Repository] = None) -> None:
        self._repo = repo or Repository()

    def generate_report(self, end_date: Optional[date] = None) -> WeeklyReportData:
        curr_end = end_date or date.today()
        curr_start = curr_end - timedelta(days=6)

        prior_end = curr_start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=6)

        # 1. Daily totals
        curr_daily_rows = self._repo.get_daily_totals_for_range(curr_start, curr_end)
        prior_daily_rows = self._repo.get_daily_totals_for_range(prior_start, prior_end)

        curr_active_s = sum(row.get("active_s", 0.0) for row in curr_daily_rows)
        curr_idle_s = sum(row.get("idle_s", 0.0) for row in curr_daily_rows)

        prior_active_s = sum(row.get("active_s", 0.0) for row in prior_daily_rows)
        prior_idle_s = sum(row.get("idle_s", 0.0) for row in prior_daily_rows)

        active_delta_s = curr_active_s - prior_active_s
        active_delta_pct = None
        if prior_active_s > 0:
            active_delta_pct = (active_delta_s / prior_active_s) * 100.0

        daily_avg_active_s = curr_active_s / 7.0

        # Construct full 7-day breakdown (filling days with 0 if no records)
        daily_map = {row["day"]: row for row in curr_daily_rows}
        daily_breakdown = []
        peak_day_name = "-"
        peak_day_active_s = 0.0

        for i in range(7):
            d = curr_start + timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            entry = daily_map.get(d_str, {"active_s": 0.0, "idle_s": 0.0})
            act = float(entry.get("active_s", 0.0))
            if act > peak_day_active_s:
                peak_day_active_s = act
                peak_day_name = d.strftime("%A")

            daily_breakdown.append({
                "date": d,
                "date_str": d_str,
                "day_name": d.strftime("%a"),
                "full_day_name": d.strftime("%A"),
                "active_s": act,
                "idle_s": float(entry.get("idle_s", 0.0)),
            })

        # 2. Top Apps Shifts
        curr_top = self._repo.get_top_apps_for_range(curr_start, curr_end, limit=8)
        prior_top = self._repo.get_top_apps_for_range(prior_start, prior_end, limit=100)
        prior_map = {item["process_name"].lower(): item["total_s"] for item in prior_top}

        top_apps_shifts = []
        for app in curr_top:
            p_name = app["process_name"]
            c_s = float(app.get("total_s", 0.0))
            p_s = float(prior_map.get(p_name.lower(), 0.0))
            d_s = c_s - p_s
            pct_chg = ((d_s / p_s) * 100.0) if p_s > 0 else None

            top_apps_shifts.append({
                "process_name": p_name,
                "display_name": get_friendly_name(p_name),
                "category": app.get("category", "Other"),
                "curr_s": c_s,
                "prior_s": p_s,
                "delta_s": d_s,
                "delta_pct": pct_chg,
                "delta_formatted": format_delta_time(d_s),
            })

        # 3. Category Breakdown
        raw_cats = self._repo.get_category_breakdown_for_range(curr_start, curr_end)
        category_breakdown = []
        for cat in raw_cats:
            cat_s = float(cat.get("total_s", 0.0))
            pct = (cat_s / max(curr_active_s, 1.0)) * 100.0
            category_breakdown.append({
                "category": cat["category"],
                "total_s": cat_s,
                "percentage": pct,
            })

        # 4. Deep Work Sessions
        deep_work_stats = self._repo.get_deep_work_stats(curr_start, curr_end)

        # 5. Fact-based Insights
        insights = self._generate_factual_insights(
            curr_active_s=curr_active_s,
            prior_active_s=prior_active_s,
            active_delta_pct=active_delta_pct,
            active_delta_s=active_delta_s,
            daily_avg_active_s=daily_avg_active_s,
            peak_day_name=peak_day_name,
            peak_day_active_s=peak_day_active_s,
            top_apps=top_apps_shifts,
            categories=category_breakdown,
            deep_work=deep_work_stats,
        )

        return WeeklyReportData(
            start_date=curr_start,
            end_date=curr_end,
            prior_start_date=prior_start,
            prior_end_date=prior_end,
            curr_active_s=curr_active_s,
            curr_idle_s=curr_idle_s,
            prior_active_s=prior_active_s,
            prior_idle_s=prior_idle_s,
            active_delta_s=active_delta_s,
            active_delta_pct=active_delta_pct,
            daily_avg_active_s=daily_avg_active_s,
            daily_breakdown=daily_breakdown,
            top_apps_shifts=top_apps_shifts,
            category_breakdown=category_breakdown,
            deep_work_stats=deep_work_stats,
            insights=insights,
            peak_day_name=peak_day_name,
            peak_day_active_s=peak_day_active_s,
        )

    def _generate_factual_insights(
        self,
        curr_active_s: float,
        prior_active_s: float,
        active_delta_pct: Optional[float],
        active_delta_s: float,
        daily_avg_active_s: float,
        peak_day_name: str,
        peak_day_active_s: float,
        top_apps: List[dict],
        categories: List[dict],
        deep_work: dict,
    ) -> List[str]:
        insights: List[str] = []

        if curr_active_s <= 0:
            return ["No active usage recorded during this 7-day period."]

        # 1. Trend comparison insight
        if active_delta_pct is not None:
            if active_delta_pct < -5.0:
                insights.append(
                    f"Active screen time decreased by {abs(active_delta_pct):.1f}% "
                    f"({format_duration(abs(active_delta_s))} less) compared to the previous week."
                )
            elif active_delta_pct > 5.0:
                insights.append(
                    f"Active screen time increased by {active_delta_pct:.1f}% "
                    f"({format_duration(active_delta_s)} more) compared to the previous week."
                )
            else:
                insights.append(
                    f"Active screen time remained consistent with the prior week (within {abs(active_delta_pct):.1f}%)."
                )
        else:
            insights.append(
                f"Recorded a baseline of {format_duration(curr_active_s)} active screen time across the 7-day period."
            )

        # 2. Daily average & peak day insight
        if peak_day_active_s > 0:
            insights.append(
                f"Daily screen time averaged {format_duration(daily_avg_active_s)}, peaking on "
                f"{peak_day_name} at {format_duration(peak_day_active_s)}."
            )

        # 3. Category focus insight
        if categories:
            top_cat = categories[0]
            insights.append(
                f"{top_cat['category']} was your primary category, accounting for "
                f"{top_cat['percentage']:.1f}% of total active screen time ({format_duration(top_cat['total_s'])})."
            )

        # 4. Deep Work session insight
        dw_count = deep_work.get("total_sessions", 0)
        dw_completed = deep_work.get("completed_sessions", 0)
        dw_work_s = deep_work.get("total_work_s", 0.0)
        if dw_count > 0:
            insights.append(
                f"Completed {dw_completed} of {dw_count} Deep Work sessions ({deep_work.get('completion_rate', 0):.0f}% completion rate) "
                f"totaling {format_duration(dw_work_s)} of dedicated focus."
            )

        # 5. Top app shift insight
        if top_apps:
            # Look for biggest shift
            shifted_apps = [a for a in top_apps if abs(a["delta_s"]) >= 1800] # at least 30m shift
            if shifted_apps:
                biggest_shift = max(shifted_apps, key=lambda a: abs(a["delta_s"]))
                direction = "increased" if biggest_shift["delta_s"] > 0 else "decreased"
                insights.append(
                    f"{biggest_shift['display_name']} saw the largest shift, {direction} by "
                    f"{format_duration(abs(biggest_shift['delta_s']))} from last week."
                )

        return insights
