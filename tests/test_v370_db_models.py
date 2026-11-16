"""
tests/test_v370_db_models.py — Automated tests for Notch v3.6.3 database schema,
FocusSchedule and DeepWorkSession models, and Repository operations.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import pytest

from database.models import FocusSchedule, DeepWorkSession
from database.repository import Repository
from database.schema import ALL_DDL


@pytest.fixture
def repo(tmp_path: Path):
    """Provides an isolated repository pointing to a temporary SQLite database."""
    db_file = tmp_path / f"test_v370_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


# ============================================================================
# 1. DATACLASS UNIT TESTS
# ============================================================================

def test_focus_schedule_days_list_and_active():
    """Verify FocusSchedule parse days list and evaluates day activity."""
    sched = FocusSchedule(
        name="Weekday Focus",
        days_of_week="0, 1, 2, 3, 4",
        start_time="09:00",
        end_time="12:00",
        mode="work",
        strict_mode=True,
    )
    assert sched.days_list == [0, 1, 2, 3, 4]
    assert sched.is_active_on_day(0) is True  # Monday
    assert sched.is_active_on_day(4) is True  # Friday
    assert sched.is_active_on_day(5) is False # Saturday
    assert sched.is_active_on_day(6) is False # Sunday


def test_focus_schedule_empty_days():
    """Verify FocusSchedule handles empty or malformed days gracefully."""
    sched = FocusSchedule(
        name="Empty",
        days_of_week="",
        start_time="10:00",
        end_time="11:00",
    )
    assert sched.days_list == []
    assert sched.is_active_on_day(1) is False

    sched_bad = FocusSchedule(
        name="Bad",
        days_of_week="foo, bar",
        start_time="10:00",
        end_time="11:00",
    )
    assert sched_bad.days_list == []


def test_deep_work_session_duration_formatted():
    """Verify DeepWorkSession duration formatting."""
    now = datetime.now()
    s1 = DeepWorkSession(
        goal="Feature planning",
        preset="25/5",
        target_work_s=1500,
        actual_work_s=1500,
        actual_break_s=300,
        intervals_completed=1,
        total_intervals=1,
        status="completed",
        started_at=now - timedelta(minutes=30),
        ended_at=now,
    )
    assert s1.duration_formatted == "25m 0s"

    s2 = DeepWorkSession(
        goal="Deep Coding",
        preset="50/10",
        target_work_s=3600,
        actual_work_s=3665,
        actual_break_s=600,
        intervals_completed=2,
        total_intervals=2,
        status="completed",
        started_at=now - timedelta(hours=2),
        ended_at=now,
    )
    assert s2.duration_formatted == "1h 1m"

    s3 = DeepWorkSession(
        goal="Short Sprint",
        preset="custom",
        target_work_s=30,
        actual_work_s=45,
        actual_break_s=0,
        intervals_completed=1,
        total_intervals=1,
        status="completed",
        started_at=now - timedelta(seconds=45),
        ended_at=now,
    )
    assert s3.duration_formatted == "45s"


# ============================================================================
# 2. FOCUS SCHEDULE REPOSITORY TESTS
# ============================================================================

def test_focus_schedule_crud(repo: Repository):
    """Verify insert, get, update, toggle, and delete operations for focus schedules."""
    # 1. Insert
    sched1 = FocusSchedule(
        name="Morning Deep Work",
        days_of_week="0,1,2,3,4",
        start_time="09:00",
        end_time="11:30",
        mode="deep",
        strict_mode=True,
        is_enabled=True,
    )
    id1 = repo.save_focus_schedule(sched1)
    assert id1 > 0
    assert sched1.id == id1

    sched2 = FocusSchedule(
        name="Evening Study",
        days_of_week="1,3",
        start_time="19:00",
        end_time="21:00",
        mode="study",
        strict_mode=False,
        is_enabled=False,
    )
    id2 = repo.save_focus_schedule(sched2)
    assert id2 > id1

    # 2. Get single
    fetched1 = repo.get_focus_schedule(id1)
    assert fetched1 is not None
    assert fetched1.name == "Morning Deep Work"
    assert fetched1.days_of_week == "0,1,2,3,4"
    assert fetched1.start_time == "09:00"
    assert fetched1.end_time == "11:30"
    assert fetched1.mode == "deep"
    assert fetched1.strict_mode is True
    assert fetched1.is_enabled is True

    # 3. Get all vs enabled
    all_scheds = repo.get_focus_schedules(only_enabled=False)
    assert len(all_scheds) == 2
    assert all_scheds[0].id == id1
    assert all_scheds[1].id == id2

    enabled_scheds = repo.get_focus_schedules(only_enabled=True)
    assert len(enabled_scheds) == 1
    assert enabled_scheds[0].id == id1

    # 4. Update
    fetched1.name = "Morning Deep Work (Updated)"
    fetched1.end_time = "12:00"
    updated_id = repo.save_focus_schedule(fetched1)
    assert updated_id == id1

    refetched = repo.get_focus_schedule(id1)
    assert refetched.name == "Morning Deep Work (Updated)"
    assert refetched.end_time == "12:00"

    # 5. Toggle enabled
    ok = repo.set_focus_schedule_enabled(id2, True)
    assert ok is True
    assert repo.get_focus_schedule(id2).is_enabled is True

    # 6. Delete
    deleted = repo.delete_focus_schedule(id1)
    assert deleted is True
    assert repo.get_focus_schedule(id1) is None
    assert len(repo.get_focus_schedules()) == 1


# ============================================================================
# 3. DEEP WORK SESSIONS REPOSITORY TESTS
# ============================================================================

def test_deep_work_session_recording_and_queries(repo: Repository):
    """Verify recording deep work sessions, range filtering, and stats rollups."""
    base_date = date.today()
    t1_start = datetime.combine(base_date, datetime.min.time()) + timedelta(hours=9)
    t1_end = t1_start + timedelta(minutes=30)

    sess1 = DeepWorkSession(
        goal="Implement SQLite Migrations",
        preset="25/5",
        target_work_s=1500,
        actual_work_s=1500,
        actual_break_s=300,
        intervals_completed=1,
        total_intervals=1,
        status="completed",
        started_at=t1_start,
        ended_at=t1_end,
        notes="All migrations passed cleanly.",
    )
    id1 = repo.record_deep_work_session(sess1)
    assert id1 > 0
    assert sess1.id == id1

    t2_start = datetime.combine(base_date, datetime.min.time()) + timedelta(hours=14)
    t2_end = t2_start + timedelta(minutes=45)
    sess2 = DeepWorkSession(
        goal="Write Controller Tests",
        preset="50/10",
        target_work_s=3000,
        actual_work_s=2400,
        actual_break_s=0,
        intervals_completed=1,
        total_intervals=2,
        status="finished_early",
        started_at=t2_start,
        ended_at=t2_end,
        notes="Paused early for urgent call.",
    )
    id2 = repo.record_deep_work_session(sess2)
    assert id2 > id1

    # Query range
    today_sessions = repo.get_deep_work_sessions_for_range(base_date, base_date)
    assert len(today_sessions) == 2
    # Verify ordered by started_at DESC
    assert today_sessions[0].id == id2
    assert today_sessions[1].id == id1
    assert today_sessions[0].goal == "Write Controller Tests"
    assert today_sessions[1].goal == "Implement SQLite Migrations"

    # Verify out-of-range exclusion
    yesterday = base_date - timedelta(days=1)
    yest_sessions = repo.get_deep_work_sessions_for_range(yesterday, yesterday)
    assert len(yest_sessions) == 0

    # Query stats
    stats = repo.get_deep_work_stats(base_date, base_date)
    assert stats["total_sessions"] == 2
    assert stats["completed_sessions"] == 1
    assert stats["total_work_s"] == 1500 + 2400  # 3900.0
    assert stats["total_break_s"] == 300.0
    assert stats["avg_work_s"] == 1950.0
    assert stats["total_intervals"] == 2
    assert stats["completion_rate"] == 50.0


def test_deep_work_stats_empty(repo: Repository):
    """Verify stats returns clean zeros when no sessions exist."""
    tomorrow = date.today() + timedelta(days=1)
    stats = repo.get_deep_work_stats(tomorrow, tomorrow)
    assert stats["total_sessions"] == 0
    assert stats["completed_sessions"] == 0
    assert stats["total_work_s"] == 0.0
    assert stats["completion_rate"] == 0.0


# ============================================================================
# 4. SCREEN-TIME BUDGET TESTS
# ============================================================================

def test_screen_time_budget_formatting():
    """Verify ScreenTimeBudget formatting property."""
    from database.models import ScreenTimeBudget
    b1 = ScreenTimeBudget(target_type="total", target_name="Total", daily_budget_seconds=7200)
    assert b1.budget_formatted == "2h"

    b2 = ScreenTimeBudget(target_type="category", target_name="Gaming", daily_budget_seconds=5400)
    assert b2.budget_formatted == "1h 30m"

    b3 = ScreenTimeBudget(target_type="app", target_name="discord.exe", daily_budget_seconds=1800)
    assert b3.budget_formatted == "30m"


def test_screen_time_budget_crud(repo: Repository):
    """Verify insert, get, update, toggle, and delete operations for budgets."""
    from database.models import ScreenTimeBudget

    # 1. Insert budgets
    b_total = ScreenTimeBudget(
        target_type="total",
        target_name="Total Daily Screen Time",
        daily_budget_seconds=18000, # 5 hours
        is_enabled=True,
        enforce_lock=False,
    )
    id1 = repo.save_budget(b_total)
    assert id1 > 0
    assert b_total.id == id1

    b_cat = ScreenTimeBudget(
        target_type="category",
        target_name="Social & Messaging",
        daily_budget_seconds=3600,
        is_enabled=True,
        enforce_lock=True,
    )
    id2 = repo.save_budget(b_cat)
    assert id2 > 0

    # 2. Get list and active
    all_budgets = repo.get_budgets()
    assert len(all_budgets) == 2
    assert repo.get_budget(id1).target_name == "Total Daily Screen Time"

    # 3. Toggle enabled
    repo.set_budget_enabled(id2, False)
    active = repo.get_active_budgets()
    assert len(active) == 1
    assert active[0].id == id1

    # 4. Update
    fetched = repo.get_budget(id1)
    fetched.daily_budget_seconds = 21600 # 6 hours
    repo.save_budget(fetched)
    updated = repo.get_budget(id1)
    assert updated.daily_budget_seconds == 21600

    # 5. Delete
    assert repo.delete_budget(id2) is True
    assert repo.get_budget(id2) is None
    assert len(repo.get_budgets()) == 1


def test_budget_usage_today_aggregation(repo: Repository):
    """Verify get_budget_usage_today calculates correct seconds across total, category, and app targets."""
    from database.models import AppSession
    from core.constants import AppCategory

    today = date.today()
    now = datetime.now()

    # Seed app sessions
    # 1. VS Code: 3600s (Programming)
    s1 = AppSession(
        process_name="Code.exe",
        window_title="models.py - VSCode",
        start_time=now - timedelta(hours=3),
        end_time=now - timedelta(hours=2),
        duration_s=3600.0,
        category=AppCategory.PROGRAMMING,
        is_idle=False,
    )
    repo.insert_session(s1)

    # 2. Chrome: 1800s (Productivity / Browser)
    s2 = AppSession(
        process_name="chrome.exe",
        window_title="Documentation",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1, minutes=30),
        duration_s=1800.0,
        category=AppCategory.PRODUCTIVITY,
        is_idle=False,
    )
    repo.insert_session(s2)

    # 3. Discord: 1200s (Social & Messaging)
    s3 = AppSession(
        process_name="discord.exe",
        window_title="Chat",
        start_time=now - timedelta(minutes=45),
        end_time=now - timedelta(minutes=25),
        duration_s=1200.0,
        category=AppCategory.COMMUNICATION,
        is_idle=False,
    )
    repo.insert_session(s3)

    # 4. Idle session (should NOT count towards active budget usage)
    s4 = AppSession(
        process_name="Code.exe",
        window_title="models.py",
        start_time=now - timedelta(minutes=20),
        end_time=now - timedelta(minutes=10),
        duration_s=600.0,
        category=AppCategory.PROGRAMMING,
        is_idle=True,
    )
    repo.insert_session(s4)

    # Test Total active: 3600 + 1800 + 1200 = 6600s
    total_used = repo.get_budget_usage_today("total", "")
    assert total_used == 6600.0

    # Test Category: Communication = 1200s, Programming = 3600s
    comm_used = repo.get_budget_usage_today("category", "Communication")
    assert comm_used == 1200.0

    prog_used = repo.get_budget_usage_today("category", "Programming")
    assert prog_used == 3600.0

    # Test App: chrome.exe = 1800s, Code.exe = 3600s (excluding idle)
    chrome_used = repo.get_budget_usage_today("app", "chrome.exe")
    assert chrome_used == 1800.0

    code_used = repo.get_budget_usage_today("app", "code.exe")
    assert code_used == 3600.0

