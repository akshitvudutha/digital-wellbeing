"""
tests/test_focus_scheduler.py — Unit and integration tests for FocusScheduler.
Covers:
- Same-day and overnight schedule window resolution
- Evaluation logic and automated start_focus dispatch
- Sleep/wake remaining duration reconciliation
- Manual override suppression (preventing immediate re-trigger)
- Natural window end teardown
- Schedule CRUD and toggle proxies
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QObject

from database.models import FocusSchedule
from database.repository import Repository
from protection.focus_scheduler import FocusScheduler


@pytest.fixture
def repo(tmp_path: Path):
    db_file = tmp_path / f"test_sched_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


@pytest.fixture
def mock_focus_mgr():
    mgr = MagicMock()
    mgr.is_active = False
    mgr.start_focus.return_value = True
    mgr.stop_focus.return_value = True
    # Mock PySide signal for focus_state_changed
    class DummySignal:
        def __init__(self):
            self._callbacks = []
        def connect(self, cb):
            self._callbacks.append(cb)
        def emit(self, val):
            for cb in self._callbacks:
                cb(val)
    mgr.focus_state_changed = DummySignal()
    return mgr


@pytest.fixture
def mock_notifier():
    notifier = MagicMock()
    notifier.notify.return_value = True
    return notifier


@pytest.fixture
def scheduler(repo, mock_focus_mgr, mock_notifier):
    sched = FocusScheduler(
        repo=repo,
        focus_mgr=mock_focus_mgr,
        notifier=mock_notifier,
    )
    yield sched
    sched.stop()


# ============================================================================
# 1. WINDOW RESOLUTION TESTS
# ============================================================================

def test_resolve_schedule_window_same_day():
    """Verify same-day window resolution across matching and non-matching days/times."""
    sched = FocusSchedule(
        name="Work Sprint",
        days_of_week="0,1,2,3,4",  # Mon-Fri
        start_time="09:00",
        end_time="12:00",
        mode="work",
    )

    # Monday 10:30 (inside window)
    mon_inside = datetime(2026, 10, 19, 10, 30)  # Oct 19, 2026 is Monday
    assert mon_inside.weekday() == 0
    active, start_dt, end_dt = FocusScheduler.resolve_schedule_window(sched, mon_inside)
    assert active is True
    assert start_dt == datetime(2026, 10, 19, 9, 0)
    assert end_dt == datetime(2026, 10, 19, 12, 0)

    # Monday 08:30 (before window)
    mon_before = datetime(2026, 10, 19, 8, 30)
    active, _, _ = FocusScheduler.resolve_schedule_window(sched, mon_before)
    assert active is False

    # Monday 12:00 (boundary/after window)
    mon_after = datetime(2026, 10, 19, 12, 0)
    active, _, _ = FocusScheduler.resolve_schedule_window(sched, mon_after)
    assert active is False

    # Saturday 10:30 (day not in schedule)
    sat_time = datetime(2026, 10, 24, 10, 30)
    assert sat_time.weekday() == 5
    active, _, _ = FocusScheduler.resolve_schedule_window(sched, sat_time)
    assert active is False


def test_resolve_schedule_window_overnight():
    """Verify cross-midnight overnight window resolution."""
    sched = FocusSchedule(
        name="Night Block",
        days_of_week="0,1,2,3,4",  # Mon-Fri (starts on these nights)
        start_time="22:00",
        end_time="02:00",
        mode="deep",
    )

    # Monday 23:00 (started today before midnight)
    mon_night = datetime(2026, 10, 19, 23, 0)
    active, start_dt, end_dt = FocusScheduler.resolve_schedule_window(sched, mon_night)
    assert active is True
    assert start_dt == datetime(2026, 10, 19, 22, 0)
    assert end_dt == datetime(2026, 10, 20, 2, 0)

    # Tuesday 01:15 (started Monday night, now past midnight)
    tue_early = datetime(2026, 10, 20, 1, 15)
    active, start_dt, end_dt = FocusScheduler.resolve_schedule_window(sched, tue_early)
    assert active is True
    assert start_dt == datetime(2026, 10, 19, 22, 0)
    assert end_dt == datetime(2026, 10, 20, 2, 0)

    # Tuesday 03:00 (past overnight end)
    tue_after = datetime(2026, 10, 20, 3, 0)
    active, _, _ = FocusScheduler.resolve_schedule_window(sched, tue_after)
    assert active is False


# ============================================================================
# 2. EVALUATION & DISPATCH TESTS
# ============================================================================

def test_evaluate_schedules_activates_focus(scheduler, repo, mock_focus_mgr):
    """When inside a window, scheduler triggers start_focus with remaining minutes."""
    sched = FocusSchedule(
        name="Study Session",
        days_of_week="0,1,2,3,4",
        start_time="09:00",
        end_time="11:00",
        mode="study",
        strict_mode=True,
        is_enabled=True,
    )
    repo.save_focus_schedule(sched)

    # Evaluate at 09:30 (90 minutes remaining until 11:00)
    mon_time = datetime(2026, 10, 19, 9, 30)
    scheduler.evaluate_schedules(current_dt=mon_time)

    mock_focus_mgr.start_focus.assert_called_once_with(
        minutes=90,
        duration_seconds=90 * 60,
        strict_mode=True,
        mode="study",
    )
    assert scheduler.active_schedule is not None
    assert scheduler.active_schedule.name == "Study Session"


def test_evaluate_schedules_sleep_wake_reconciliation(scheduler, repo, mock_focus_mgr):
    """If PC wakes halfway through a schedule, derive exact remaining minutes."""
    sched = FocusSchedule(
        name="Afternoon Block",
        days_of_week="0,1,2,3,4",
        start_time="14:00",
        end_time="17:00",
        mode="work",
        strict_mode=False,
        is_enabled=True,
    )
    repo.save_focus_schedule(sched)

    # System wakes at 16:15 (45 minutes remaining)
    wake_time = datetime(2026, 10, 19, 16, 15)
    scheduler.evaluate_schedules(current_dt=wake_time)

    mock_focus_mgr.start_focus.assert_called_once_with(
        minutes=45,
        duration_seconds=45 * 60,
        strict_mode=False,
        mode="work",
    )


def test_evaluate_schedules_preserves_fractional_remaining_seconds(
    scheduler, repo, mock_focus_mgr
):
    """Sub-minute schedule remainder is passed without rounding to whole minutes."""
    sched = FocusSchedule(
        name="Short Remainder",
        days_of_week="0,1,2,3,4",
        start_time="09:00",
        end_time="11:00",
        mode="study",
        is_enabled=True,
    )
    repo.save_focus_schedule(sched)

    now = datetime(2026, 10, 19, 10, 59, 22, 500000)
    scheduler.evaluate_schedules(current_dt=now)

    mock_focus_mgr.start_focus.assert_called_once_with(
        minutes=1,
        duration_seconds=37.5,
        strict_mode=False,
        mode="study",
    )


def test_evaluate_schedules_skips_negligible_remainder(scheduler, repo, mock_focus_mgr):
    """A window with 30 seconds or less left does not start a near-instant session."""
    sched = FocusSchedule(
        name="Almost Finished",
        days_of_week="0,1,2,3,4",
        start_time="09:00",
        end_time="11:00",
        mode="study",
        is_enabled=True,
    )
    repo.save_focus_schedule(sched)

    scheduler.evaluate_schedules(current_dt=datetime(2026, 10, 19, 10, 59, 30))

    mock_focus_mgr.start_focus.assert_not_called()


def test_manual_stop_suppression(scheduler, repo, mock_focus_mgr):
    """User manually stopping scheduled focus suppresses re-triggering until window end."""
    sched = FocusSchedule(
        name="Morning Focus",
        days_of_week="0,1,2,3,4",
        start_time="09:00",
        end_time="12:00",
        mode="work",
        is_enabled=True,
    )
    sid = repo.save_focus_schedule(sched)

    # 1. Start schedule
    t1 = datetime(2026, 10, 19, 9, 15)
    scheduler.evaluate_schedules(current_dt=t1)
    assert scheduler.active_schedule is not None

    # 2. Simulate FocusManager being stopped manually by user at 09:45
    mock_focus_mgr.is_active = False
    scheduler._on_focus_state_changed(False)
    assert scheduler.active_schedule is None

    # 3. Next tick at 09:46 inside the same window must NOT re-start focus
    t2 = datetime(2026, 10, 19, 9, 46)
    mock_focus_mgr.start_focus.reset_mock()
    scheduler.evaluate_schedules(current_dt=t2)
    mock_focus_mgr.start_focus.assert_not_called()


def test_natural_window_end_stops_focus(scheduler, repo, mock_focus_mgr):
    """When schedule end time is reached, active focus is stopped."""
    sched = FocusSchedule(
        name="Quick Sprint",
        days_of_week="0,1,2,3,4",
        start_time="10:00",
        end_time="10:30",
        mode="work",
        is_enabled=True,
    )
    repo.save_focus_schedule(sched)

    # Start at 10:05
    scheduler.evaluate_schedules(current_dt=datetime(2026, 10, 19, 10, 5))
    mock_focus_mgr.is_active = True

    ended_signal_called = []
    scheduler.schedule_ended.connect(lambda s: ended_signal_called.append(s))

    # Evaluate past end at 10:31
    scheduler.evaluate_schedules(current_dt=datetime(2026, 10, 19, 10, 31))
    mock_focus_mgr.stop_focus.assert_called_once()
    assert scheduler.active_schedule is None
    assert len(ended_signal_called) == 1


# ============================================================================
# 3. CRUD & TOGGLE PROXIES
# ============================================================================

def test_scheduler_crud_proxies(scheduler):
    """Verify scheduler CRUD and toggle helper methods."""
    sched = FocusSchedule(
        name="Test Sched",
        days_of_week="0,2,4",
        start_time="08:00",
        end_time="10:00",
        mode="custom",
        is_enabled=True,
    )
    sid = scheduler.add_or_update_schedule(sched)
    assert sid > 0

    schedules = scheduler.get_schedules()
    assert len(schedules) == 1
    assert schedules[0].name == "Test Sched"

    # Toggle
    scheduler.toggle_schedule(sid, False)
    assert scheduler.get_schedule(sid).is_enabled is False

    # Delete
    ok = scheduler.delete_schedule(sid)
    assert ok is True
    assert scheduler.get_schedule(sid) is None
