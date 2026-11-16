"""
tests/test_budgets.py — Automated tests for Notch v3.6.3 Screen-Time Budget Manager.
Verifies milestone tracking (50%, 80%, 100%), toasts, midnight rollover, and enforcement.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock
import pytest

import sys
from PySide6.QtWidgets import QApplication
from core.constants import AppCategory
from database.models import AppSession, ScreenTimeBudget
from database.repository import Repository
from protection.budgets import BudgetManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def repo(tmp_path: Path):
    db_file = tmp_path / f"test_budgets_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


def test_budget_manager_milestones_and_signals(qapp, repo: Repository):
    """Verify 50%, 80%, and 100% milestones trigger sequentially without duplicate alerts."""
    mock_notifier = MagicMock()
    mock_pm = MagicMock()

    mgr = BudgetManager(repo=repo, notifier=mock_notifier, protection_mgr=mock_pm)
    try:
        # Create a 2-hour (7200s) budget for Development
        b = ScreenTimeBudget(
            target_type="category",
            target_name="Programming",
            daily_budget_seconds=7200,
            is_enabled=True,
            enforce_lock=False,
        )
        b_id = mgr.add_or_update_budget(b)
        assert b_id > 0

        milestones_fired = []
        mgr.milestone_reached.connect(lambda b, m: milestones_fired.append(m))
        exceeded_fired = []
        mgr.budget_exceeded.connect(lambda b: exceeded_fired.append(b.id))

        now = datetime.now()

        # Phase 1: 3000s active (41.6% - below 50%)
        repo.insert_session(AppSession(
            process_name="Code.exe",
            window_title="dev",
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1, minutes=10),
            duration_s=3000.0,
            category=AppCategory.PROGRAMMING,
            is_idle=False,
        ))
        mgr.evaluate_budgets(now)
        assert len(milestones_fired) == 0
        assert mock_notifier.send_notification.call_count == 0

        # Phase 2: Add 1000s -> Total 4000s (55.5% - crosses 50%)
        repo.insert_session(AppSession(
            process_name="Code.exe",
            window_title="dev",
            start_time=now - timedelta(minutes=50),
            end_time=now - timedelta(minutes=33),
            duration_s=1000.0,
            category=AppCategory.PROGRAMMING,
            is_idle=False,
        ))
        mgr.evaluate_budgets(now)
        assert milestones_fired == [50]
        assert mock_notifier.send_notification.call_count == 1
        assert "50%" in mock_notifier.send_notification.call_args[0][1]

        # Phase 3: Evaluate again without change -> no duplicate toast
        mgr.evaluate_budgets(now)
        assert milestones_fired == [50]
        assert mock_notifier.send_notification.call_count == 1

        # Phase 4: Add 2000s -> Total 6000s (83.3% - crosses 80%)
        repo.insert_session(AppSession(
            process_name="Code.exe",
            window_title="dev",
            start_time=now - timedelta(minutes=30),
            end_time=now,
            duration_s=2000.0,
            category=AppCategory.PROGRAMMING,
            is_idle=False,
        ))
        mgr.evaluate_budgets(now)
        assert milestones_fired == [50, 80]
        assert mock_notifier.send_notification.call_count == 2
        assert "80%" in mock_notifier.send_notification.call_args[0][1]

        # Phase 5: Add 1500s -> Total 7500s (> 100% exceeded)
        repo.insert_session(AppSession(
            process_name="Code.exe",
            window_title="dev",
            start_time=now,
            end_time=now + timedelta(minutes=25),
            duration_s=1500.0,
            category=AppCategory.PROGRAMMING,
            is_idle=False,
        ))
        mgr.evaluate_budgets(now)
        assert milestones_fired == [50, 80, 100]
        assert exceeded_fired == [b_id]
        assert mock_notifier.send_notification.call_count == 3
        assert "Exceeded" in mock_notifier.send_notification.call_args[0][0]
    finally:
        mgr.stop()


def test_budget_manager_midnight_rollover(qapp, repo: Repository):
    """Verify date rollover resets notified milestones for a fresh day."""
    mock_notifier = MagicMock()
    mgr = BudgetManager(repo=repo, notifier=mock_notifier)
    try:
        b = ScreenTimeBudget(
            target_type="total",
            target_name="Total",
            daily_budget_seconds=3600,
            is_enabled=True,
        )
        b_id = mgr.add_or_update_budget(b)

        day1 = datetime(2026, 10, 18, 14, 0, 0)
        repo.insert_session(AppSession(
            process_name="Code.exe",
            window_title="dev",
            start_time=day1 - timedelta(hours=2),
            end_time=day1 - timedelta(hours=1),
            duration_s=3600.0,
            category=AppCategory.PROGRAMMING,
            is_idle=False,
        ))
        mgr.evaluate_budgets(day1)
        assert 100 in mgr._milestones_notified[b_id]

        # Advance to day 2 (tomorrow morning)
        day2 = datetime(2026, 10, 19, 9, 0, 0)
        mgr.evaluate_budgets(day2)
        # Should be reset and empty because day 2 has no sessions yet
        assert len(mgr._milestones_notified[b_id]) == 0
    finally:
        mgr.stop()


def test_budget_manager_enforce_lock(qapp, repo: Repository):
    """Verify enforce_lock triggers app locker termination upon 100% budget exhaustion."""
    mock_notifier = MagicMock()
    mock_pm = MagicMock()
    mock_app_locker = MagicMock()
    mock_pm.app_locker = mock_app_locker

    mgr = BudgetManager(repo=repo, notifier=mock_notifier, protection_mgr=mock_pm)
    try:
        b = ScreenTimeBudget(
            target_type="app",
            target_name="steam.exe",
            daily_budget_seconds=1800, # 30 min
            is_enabled=True,
            enforce_lock=True,
        )
        mgr.add_or_update_budget(b)

        now = datetime.now()
        repo.insert_session(AppSession(
            process_name="steam.exe",
            window_title="Steam Store",
            start_time=now - timedelta(minutes=35),
            end_time=now,
            duration_s=2100.0,
            category=AppCategory.GAMING,
            is_idle=False,
        ))

        mgr.evaluate_budgets(now)
        mock_app_locker.terminate_if_running.assert_called_once_with("steam.exe")
    finally:
        mgr.stop()


def test_budget_manager_crud_and_status(qapp, repo: Repository):
    """Verify CRUD methods, status dictionary, and toggling."""
    mgr = BudgetManager(repo=repo)
    try:
        b = ScreenTimeBudget(
            target_type="category",
            target_name="Social",
            daily_budget_seconds=3600,
            is_enabled=True,
        )
        b_id = mgr.add_or_update_budget(b)
        assert b_id > 0

        status = mgr.get_budget_status(b)
        assert status["budget_seconds"] == 3600
        assert status["used_seconds"] == 0
        assert status["remaining_seconds"] == 3600
        assert status["percentage"] == 0.0
        assert status["is_exceeded"] is False

        # Toggle disable
        mgr.toggle_budget(b_id, False)
        assert repo.get_budget(b_id).is_enabled is False

        # Delete
        mgr.delete_budget(b_id)
        assert repo.get_budget(b_id) is None
    finally:
        mgr.stop()
