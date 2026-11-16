from __future__ import annotations

from datetime import datetime

import pytest

from analytics.engine import AnalyticsEngine
from analytics.weekly_report import (
    format_delta_time,
    format_duration as format_weekly_duration,
)
from core.constants import AppCategory
from database.models import AppSession, DeepWorkSession, WebsiteSession
from utils.time_format import format_duration
from ui.pages.app_timer import _format_time_short as format_app_timer_duration
from ui.widgets.budget_card import _format_time_short as format_budget_duration


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0s"),
        (1, "1s"),
        (59, "59s"),
        (60, "1m 0s"),
        (113, "1m 53s"),
        (3599, "59m 59s"),
        (3600, "1h 0m"),
        (3665, "1h 1m"),
        (-5, "0s"),
    ],
)
def test_shared_duration_format(seconds, expected):
    assert format_duration(seconds) == expected
    assert AnalyticsEngine.format_duration(seconds) == expected
    assert format_weekly_duration(seconds) == expected
    compact = format_duration(seconds, compact=True)
    assert AnalyticsEngine.format_duration_short(seconds) == compact
    assert format_app_timer_duration(seconds) == compact
    assert format_budget_duration(seconds) == compact


def test_weekly_delta_format_keeps_short_and_remainder_seconds():
    assert format_delta_time(0) == "+0s"
    assert format_delta_time(51) == "+51s"
    assert format_delta_time(-113) == "-1m 53s"


def test_session_models_use_shared_duration_format():
    now = datetime.now()
    app_session = AppSession(
        process_name="app.exe",
        window_title="App",
        start_time=now,
        end_time=now,
        duration_s=51,
        category=AppCategory.PRODUCTIVITY,
        is_idle=False,
    )
    website_session = WebsiteSession(
        domain="example.com",
        browser_process="browser.exe",
        start_time=now,
        end_time=now,
        duration_s=113,
    )
    deep_work_session = DeepWorkSession(
        goal="Read",
        preset="custom",
        target_work_s=113,
        actual_work_s=113,
        actual_break_s=0,
        intervals_completed=1,
        total_intervals=1,
        status="completed",
        started_at=now,
        ended_at=now,
    )

    assert app_session.duration_formatted == "51s"
    assert website_session.duration_formatted == "1m 53s"
    assert deep_work_session.duration_formatted == "1m 53s"
