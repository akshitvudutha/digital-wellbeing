"""
tests/test_weekly_report.py — Automated tests for WeeklyReportGenerator and ReportExporter.
Verifies comparative 7-day analytics, deltas, top app shifts, factual insights, and Markdown/HTML export.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
import pytest

from core.constants import AppCategory
from database.models import AppSession, DeepWorkSession
from database.repository import Repository
from analytics.weekly_report import WeeklyReportGenerator
from analytics.report_exporter import ReportExporter


@pytest.fixture
def repo(tmp_path: Path):
    db_file = tmp_path / f"test_weekly_report_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


def test_weekly_report_generation(repo: Repository):
    """Verify 7-day report calculates volume, breakdowns, deep work, and factual insights."""
    today = date(2026, 10, 18)
    now = datetime(2026, 10, 18, 16, 0, 0)

    # 1. Insert sessions across current week
    # Day 1: 3 hours Code.exe
    repo.insert_session(AppSession(
        process_name="Code.exe",
        window_title="weekly_report.py",
        start_time=now - timedelta(days=2, hours=3),
        end_time=now - timedelta(days=2),
        duration_s=10800.0,
        category=AppCategory.PROGRAMMING,
        is_idle=False,
    ))
    # Day 2: 1 hour Chrome
    repo.insert_session(AppSession(
        process_name="chrome.exe",
        window_title="Docs",
        start_time=now - timedelta(days=1, hours=1),
        end_time=now - timedelta(days=1),
        duration_s=3600.0,
        category=AppCategory.PRODUCTIVITY,
        is_idle=False,
    ))

    # 2. Insert Deep Work session
    dw = DeepWorkSession(
        goal="Notch Expansion",
        preset="50/10",
        target_work_s=3000.0,
        actual_work_s=3000.0,
        actual_break_s=600.0,
        intervals_completed=1,
        total_intervals=1,
        status="completed",
        started_at=now - timedelta(days=2, hours=2),
        ended_at=now - timedelta(days=2, hours=1),
    )
    repo.record_deep_work_session(dw)

    # Generate Report
    generator = WeeklyReportGenerator(repo=repo)
    report = generator.generate_report(end_date=today)

    assert report.curr_active_s == 10800.0 + 3600.0  # 14400s (4 hours)
    assert report.daily_avg_active_s == 14400.0 / 7.0
    assert len(report.daily_breakdown) == 7
    assert len(report.top_apps_shifts) == 2
    assert report.top_apps_shifts[0]["process_name"] == "Code.exe"
    assert report.top_apps_shifts[0]["curr_s"] == 10800.0

    # Deep work
    assert report.deep_work_stats["total_sessions"] == 1
    assert report.deep_work_stats["completed_sessions"] == 1

    # Insights
    assert len(report.insights) >= 2
    assert any("Programming" in s for s in report.insights)
    assert any("Deep Work" in s for s in report.insights)


def test_weekly_report_delta_comparison(repo: Repository):
    """Verify comparative calculations and trend insights between current and prior weeks."""
    today = date(2026, 10, 18)
    now = datetime(2026, 10, 18, 12, 0, 0)

    # Prior week (days 8-10 ago): 20,000s active
    repo.insert_session(AppSession(
        process_name="steam.exe",
        window_title="Game",
        start_time=now - timedelta(days=9, hours=5),
        end_time=now - timedelta(days=9),
        duration_s=18000.0,
        category=AppCategory.GAMING,
        is_idle=False,
    ))
    repo.insert_session(AppSession(
        process_name="steam.exe",
        window_title="Game",
        start_time=now - timedelta(days=8, hours=1),
        end_time=now - timedelta(days=8),
        duration_s=2000.0,
        category=AppCategory.GAMING,
        is_idle=False,
    ))
    # Prior week total = 20,000s

    # Current week (days 1-2 ago): 10,000s active (50% decrease)
    repo.insert_session(AppSession(
        process_name="steam.exe",
        window_title="Game",
        start_time=now - timedelta(days=2, hours=2),
        end_time=now - timedelta(days=2),
        duration_s=10000.0,
        category=AppCategory.GAMING,
        is_idle=False,
    ))

    generator = WeeklyReportGenerator(repo=repo)
    report = generator.generate_report(end_date=today)

    assert report.prior_active_s == 20000.0
    assert report.curr_active_s == 10000.0
    assert report.active_delta_s == -10000.0
    assert report.active_delta_pct == -50.0

    # Trend insight must reflect the 50% decrease
    trend_insight = report.insights[0]
    assert "decreased by 50.0%" in trend_insight


def test_report_exporter_markdown(repo: Repository, tmp_path: Path):
    """Verify Markdown report generation and local file writing."""
    today = date(2026, 10, 18)
    now = datetime(2026, 10, 18, 12, 0, 0)

    repo.insert_session(AppSession(
        process_name="Code.exe",
        window_title="App",
        start_time=now - timedelta(hours=2),
        end_time=now,
        duration_s=7200.0,
        category=AppCategory.PROGRAMMING,
        is_idle=False,
    ))

    report = WeeklyReportGenerator(repo=repo).generate_report(end_date=today)
    dest_file = tmp_path / "exports" / "weekly_report.md"

    md_content = ReportExporter.export_markdown(report, dest_path=dest_file)

    assert dest_file.exists()
    assert "# Notch — Weekly Wellbeing Report" in md_content
    assert "Active Screen Time" in md_content
    assert "Visual Studio Code" in md_content
    assert "Zero cloud telemetry" in md_content


def test_report_exporter_html(repo: Repository, tmp_path: Path):
    """Verify self-contained, offline HTML report generation and print support."""
    today = date(2026, 10, 18)
    now = datetime(2026, 10, 18, 12, 0, 0)

    repo.insert_session(AppSession(
        process_name="Code.exe",
        window_title="App",
        start_time=now - timedelta(hours=2),
        end_time=now,
        duration_s=7200.0,
        category=AppCategory.PROGRAMMING,
        is_idle=False,
    ))

    report = WeeklyReportGenerator(repo=repo).generate_report(end_date=today)
    dest_file = tmp_path / "exports" / "weekly_report.html"

    html_content = ReportExporter.export_html(report, dest_path=dest_file)

    assert dest_file.exists()
    assert "<!DOCTYPE html>" in html_content
    assert "Weekly Wellbeing Report" in html_content
    assert "@media print" in html_content
    assert "Zero cloud telemetry" in html_content
    # Strict offline constraint: zero external http/https CDN tags
    assert "http://" not in html_content
    assert "https://" not in html_content
