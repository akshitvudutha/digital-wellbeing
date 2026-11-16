"""
tests/test_budgets_ui.py — UI rendering and interaction tests for AppTimerPage budgets subtab,
BudgetCard widgets, and BudgetDialog modal.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from PySide6.QtWidgets import QApplication, QLabel
from database.models import ScreenTimeBudget
from database.repository import Repository
from protection.budgets import BudgetManager
from ui.pages.app_timer import AppTimerPage
from ui.widgets.budget_card import BudgetCard
from ui.widgets.budget_dialog import BudgetDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def repo(tmp_path: Path):
    db_file = tmp_path / f"test_ui_budgets_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


def test_app_timer_page_subtab_switching(qapp, repo):
    """Verify switching between App & Web Timers and Daily Budgets & Goals subtabs."""
    BudgetManager._instance = None
    page = AppTimerPage()
    try:
        # Default subtab is Timers (index 0)
        assert page._stack.currentIndex() == 0
        assert page._btn_subtab_timers.objectName() == "subtab_active"
        assert page._btn_subtab_budgets.objectName() == "subtab_inactive"

        # Switch to Budgets subtab (index 1)
        page._btn_subtab_budgets.click()
        assert page._stack.currentIndex() == 1
        assert page._btn_subtab_budgets.objectName() == "subtab_active"
        assert page._btn_subtab_timers.objectName() == "subtab_inactive"

        # Switch back to Timers
        page._btn_subtab_timers.click()
        assert page._stack.currentIndex() == 0
    finally:
        page.deleteLater()
        BudgetManager._instance = None
        QApplication.processEvents()


def test_app_timer_page_empty_and_populated_budgets(qapp, repo):
    """Verify empty state renders when no budgets exist, and BudgetCard renders when added."""
    BudgetManager._instance = None
    mgr = BudgetManager.instance(repo)

    page = AppTimerPage()
    try:
        page._switch_subtab(1)
        # 1. Empty state
        cards = page.findChildren(BudgetCard)
        assert len(cards) == 0
        assert not page._budget_empty_frame.isHidden()

        # 2. Add a budget
        b = ScreenTimeBudget(
            target_type="category",
            target_name="Social",
            daily_budget_seconds=5400,
            is_enabled=True,
            enforce_lock=True,
        )
        mgr.add_or_update_budget(b)
        page._refresh_budgets()

        cards = page.findChildren(BudgetCard)
        assert len(cards) == 1
        assert cards[0]._lbl_name.text() == "Social"
        assert cards[0]._lbl_type.text() == "CATEGORY"
        assert cards[0]._lbl_enforce.text() == "HARD LOCK"
        assert page._budget_empty_frame.isHidden() is True
    finally:
        page.deleteLater()
        mgr.stop()
        BudgetManager._instance = None
        QApplication.processEvents()


def test_budget_dialog_creation(qapp):
    """Verify BudgetDialog builds valid ScreenTimeBudget models."""
    dlg = BudgetDialog()
    try:
        # Select category type
        idx = dlg._type_combo.findData("category")
        dlg._type_combo.setCurrentIndex(idx)

        # Select Gaming
        c_idx = dlg._cat_combo.findData("Gaming")
        dlg._cat_combo.setCurrentIndex(c_idx)

        # 2 hours 30 mins
        dlg._hours_spin.setValue(2)
        dlg._mins_spin.setValue(30)
        dlg._enforce_check.setChecked(True)

        dlg._on_save()
        res = dlg.get_budget()

        assert res.target_type == "category"
        assert res.target_name == "Gaming"
        assert res.daily_budget_seconds == 9000  # 2h 30m = 9000s
        assert res.enforce_lock is True
        assert res.is_enabled is True
    finally:
        dlg.deleteLater()
        QApplication.processEvents()
