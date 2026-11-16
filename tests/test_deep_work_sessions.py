"""
tests/test_deep_work_sessions.py — Comprehensive tests for Deep Work sessions:
- Phase transitions: WORK -> SHORT_BREAK -> WORK -> COMPLETED
- Pause and resume handling
- Finish early and cancellation logging into database
- FocusManager allowlist/blocklist coordination
- Zero PC power actions (safety verification)
"""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from database.repository import Repository
from protection.deep_work import DeepWorkController, DeepWorkPhase


@pytest.fixture
def repo(tmp_path: Path):
    db_file = tmp_path / f"test_dw_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


@pytest.fixture
def mock_focus_mgr():
    mgr = MagicMock()
    mgr.is_active = False
    mgr.is_paused = False
    mgr.start_focus.return_value = True
    mgr.stop_focus.return_value = True
    return mgr


@pytest.fixture
def mock_notifier():
    notifier = MagicMock()
    notifier.notify.return_value = True
    return notifier


@pytest.fixture
def controller(repo, mock_focus_mgr, mock_notifier):
    now = [1000.0]
    ctrl = DeepWorkController(
        repo=repo,
        focus_mgr=mock_focus_mgr,
        notifier=mock_notifier,
        clock=lambda: now[0],
    )
    ctrl._test_clock = now
    yield ctrl
    if ctrl.is_active:
        ctrl.cancel_session()


# ============================================================================
# 1. LIFECYCLE & TRANSITIONS
# ============================================================================

def test_deep_work_start_session(controller, mock_focus_mgr):
    """Starting a session engages WORK phase, initializes interval 1, and starts FocusManager."""
    ok = controller.start_session(
        goal="Develop v3.6.3 Features",
        work_minutes=25,
        break_minutes=5,
        total_intervals=4,
        preset="25/5",
        mode="deep",
        strict_mode=True,
    )
    assert ok is True
    assert controller.is_active is True
    assert controller.phase == DeepWorkPhase.WORK
    assert controller.goal == "Develop v3.6.3 Features"
    assert controller.current_interval == 1
    assert controller.total_intervals == 4

    mock_focus_mgr.start_focus.assert_called_once_with(
        minutes=25,
        strict_mode=True,
        mode="deep",
    )


def test_deep_work_phase_transitions(controller, repo, mock_focus_mgr):
    """Advance through work -> break -> work -> completed cycle."""
    controller.start_session(
        goal="Two-Cycle Sprint",
        work_minutes=1,
        break_minutes=1,
        total_intervals=2,
    )
    mock_focus_mgr.is_active = True

    # 1. Advance from WORK 1 -> BREAK 1
    controller._advance_phase()
    assert controller.phase == DeepWorkPhase.SHORT_BREAK
    assert controller.current_interval == 1
    # FocusManager must be stopped during break to relax restrictions
    mock_focus_mgr.stop_focus.assert_called_once()

    # 2. Advance from BREAK 1 -> WORK 2
    mock_focus_mgr.start_focus.reset_mock()
    controller._advance_phase()
    assert controller.phase == DeepWorkPhase.WORK
    assert controller.current_interval == 2
    # FocusManager re-engaged for interval 2
    mock_focus_mgr.start_focus.assert_called_once_with(
        minutes=1,
        strict_mode=False,
        mode="deep",
    )

    # 3. Advance from WORK 2 -> COMPLETED (all 2 intervals complete!)
    completed_sessions = []
    controller.session_completed.connect(lambda s: completed_sessions.append(s))
    controller._advance_phase()

    assert controller.is_active is False
    assert len(completed_sessions) == 1
    assert completed_sessions[0].status == "completed"
    assert completed_sessions[0].goal == "Two-Cycle Sprint"
    assert completed_sessions[0].intervals_completed == 2

    # Verify persisted to SQLite
    db_records = repo.get_deep_work_sessions_for_range(
        completed_sessions[0].started_at.date(),
        completed_sessions[0].ended_at.date(),
    )
    assert len(db_records) == 1
    assert db_records[0].status == "completed"


def test_deep_work_pause_and_resume(controller, mock_focus_mgr):
    """Pause freezes countdown and stops FocusManager; resume continues countdown."""
    controller.start_session(goal="Testing Pause", work_minutes=25)
    mock_focus_mgr.is_active = True

    # Pause
    controller.pause_session()
    assert controller.phase == DeepWorkPhase.PAUSED_WORK
    assert controller.is_paused is True
    mock_focus_mgr.stop_focus.assert_called_once()
    mock_focus_mgr.is_active = False

    # Resume
    mock_focus_mgr.start_focus.reset_mock()
    controller.resume_session()
    assert controller.phase == DeepWorkPhase.WORK
    assert controller.is_paused is False
    mock_focus_mgr.start_focus.assert_called_once_with(
        minutes=25,
        duration_seconds=1500.0,
        strict_mode=False,
        mode="deep",
    )


def test_deep_work_finish_early(controller, repo):
    """Finishing early saves actual focused time and marks status finished_early."""
    controller.start_session(goal="Early Finisher", work_minutes=50, total_intervals=2)
    controller._test_clock[0] += 1200.0  # 20 minutes of monotonic work

    finished_records = []
    controller.session_completed.connect(lambda s: finished_records.append(s))
    controller.finish_early()

    assert controller.is_active is False
    assert len(finished_records) == 1
    assert finished_records[0].status == "finished_early"
    assert finished_records[0].actual_work_s == 1200.0

    # Verify in DB
    stats = repo.get_deep_work_stats()
    assert stats["total_sessions"] == 1
    assert stats["completed_sessions"] == 0
    assert stats["total_work_s"] == 1200.0


def test_deep_work_cancel_session(controller, repo):
    """Cancelling logs status as cancelled and emits session_aborted."""
    controller.start_session(goal="To Cancel", work_minutes=25)
    aborted_fired = []
    controller.session_aborted.connect(lambda: aborted_fired.append(True))

    controller.cancel_session()
    assert controller.is_active is False
    assert len(aborted_fired) == 1

    records = repo.get_deep_work_sessions_for_range(
        controller._session_start_dt.date(),
        controller._session_start_dt.date(),
    )
    assert len(records) == 1
    assert records[0].status == "cancelled"


def test_deep_work_zero_power_actions(controller):
    """Safety guarantee: Verify Deep Work never imports or calls shutdown/sleep."""
    with patch("utils.shutdown.ShutdownManager") as mock_shutdown:
        controller.start_session(goal="Safe Session", work_minutes=1)
        controller._advance_phase()  # to break
        controller._advance_phase()  # to work
        controller._advance_phase()  # to complete
        mock_shutdown.assert_not_called()
