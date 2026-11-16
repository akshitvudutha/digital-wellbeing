"""
tests/test_wellbeing_page_scheduler.py — UI rendering and interaction tests for
WellbeingPage Smart Scheduler tab, cards, and modal dialogs.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from PySide6.QtWidgets import QApplication, QPushButton, QLabel
from database.models import FocusSchedule
from database.repository import Repository
from protection.focus_scheduler import FocusScheduler
from ui.pages.wellbeing import WellbeingPage
from ui.widgets.deep_work_cockpit import DeepWorkCockpitWidget
from ui.widgets.focus_schedule_card import FocusScheduleCard
from ui.widgets.focus_schedule_dialog import FocusScheduleDialog
from ui.theme import ThemeManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def repo(tmp_path: Path):
    db_file = tmp_path / f"test_ui_sched_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


def test_wellbeing_page_tab_switching(qapp, repo):
    """Verify switching between Focus Timer, Deep Work Sessions, and Smart Scheduler subtabs."""
    FocusScheduler._instance = None
    page = WellbeingPage()
    try:
        # Default tab is Focus Timer (index 0)
        assert page._stack.currentIndex() == 0
        assert page._btn_tab_timer.objectName() == "subtab_active"
        assert page._btn_tab_deep_work.objectName() == "subtab_inactive"
        assert page._btn_tab_scheduler.objectName() == "subtab_inactive"

        # Switch to Deep Work Sessions (index 1)
        page._btn_tab_deep_work.click()
        assert page._stack.currentIndex() == 1
        assert page._btn_tab_deep_work.objectName() == "subtab_active"
        assert page._btn_tab_timer.objectName() == "subtab_inactive"
        assert page._btn_tab_scheduler.objectName() == "subtab_inactive"
        assert isinstance(page._deep_work_cockpit, DeepWorkCockpitWidget)

        # Switch to Scheduler (index 2)
        page._btn_tab_scheduler.click()
        assert page._stack.currentIndex() == 2
        assert page._btn_tab_scheduler.objectName() == "subtab_active"
        assert page._btn_tab_deep_work.objectName() == "subtab_inactive"
        assert page._btn_tab_timer.objectName() == "subtab_inactive"

        # Switch back to Focus Timer
        page._btn_tab_timer.click()
        assert page._stack.currentIndex() == 0
    finally:
        page.deleteLater()
        FocusScheduler._instance = None
        QApplication.processEvents()


def test_wellbeing_page_empty_and_populated_schedules(qapp, repo):
    """Verify empty state renders initially, then card renders when schedule added."""
    FocusScheduler._instance = None
    scheduler = FocusScheduler.instance(repo)

    page = WellbeingPage()
    try:
        page._switch_tab(2)
        # 1. Empty state
        cards = page.findChildren(FocusScheduleCard)
        assert len(cards) == 0
        empty_lbl = page.findChild(QLabel, "empty_title")
        assert empty_lbl is not None
        assert "No Focus Schedules Configured" in empty_lbl.text()

        # 2. Add a schedule directly
        sched = FocusSchedule(
            name="Deep Sprint",
            days_of_week="0,1,2,3,4",
            start_time="09:00",
            end_time="11:00",
            mode="deep",
            strict_mode=True,
            is_enabled=True,
        )
        scheduler.add_or_update_schedule(sched)
        page._refresh_schedules()

        cards = page.findChildren(FocusScheduleCard)
        assert len(cards) == 1
        assert cards[0]._lbl_name.text() == "Deep Sprint"
        assert cards[0]._lbl_mode.text() == "DEEP"
    finally:
        page.deleteLater()
        scheduler.stop()
        FocusScheduler._instance = None
        QApplication.processEvents()


def test_focus_schedule_dialog_creation(qapp):
    """Verify FocusScheduleDialog constructs a valid FocusSchedule model."""
    dlg = FocusScheduleDialog()
    try:
        dlg._name_input.setText("Custom Coding Block")
        dlg._set_days({0, 2, 4})  # Mon, Wed, Fri
        idx = dlg._mode_combo.findData("study")
        dlg._mode_combo.setCurrentIndex(idx)
        dlg._strict_check.setChecked(True)

        dlg._on_save()
        res = dlg.get_schedule()
        assert res.name == "Custom Coding Block"
        assert res.days_list == [0, 2, 4]
        assert res.mode == "study"
        assert res.strict_mode is True
        assert res.is_enabled is True
    finally:
        dlg.deleteLater()
        QApplication.processEvents()
