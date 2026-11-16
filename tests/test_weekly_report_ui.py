"""
tests/test_weekly_report_ui.py — UI rendering and interaction tests for InsightsPage subtab switching
and the WeeklyReportWidget dashboard.
"""
from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
import pytest

from PySide6.QtWidgets import QApplication
from core.constants import AppCategory
from database.models import AppSession
from database.repository import Repository
from ui.pages.insights import InsightsPage
from ui.widgets.weekly_report_widget import WeeklyReportWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def repo(tmp_path: Path):
    db_file = tmp_path / f"test_ui_weekly_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


def test_insights_page_subtab_switching(qapp, repo):
    """Verify switching between Daily Insights and Weekly Wellbeing Report subtabs."""
    page = InsightsPage()
    try:
        # Default subtab is Daily Insights (index 0)
        assert page._stack.currentIndex() == 0
        assert page._btn_subtab_daily.objectName() == "subtab_active"
        assert page._btn_subtab_weekly.objectName() == "subtab_inactive"

        # Switch to Weekly Wellbeing Report (index 1)
        page._btn_subtab_weekly.click()
        assert page._stack.currentIndex() == 1
        assert page._btn_subtab_weekly.objectName() == "subtab_active"
        assert page._btn_subtab_daily.objectName() == "subtab_inactive"
        assert isinstance(page._weekly_report, WeeklyReportWidget)

        # Switch back to Daily Insights
        page._btn_subtab_daily.click()
        assert page._stack.currentIndex() == 0
    finally:
        page.deleteLater()
        QApplication.processEvents()


def test_weekly_report_widget_rendering_and_controls(qapp, repo):
    """Verify WeeklyReportWidget renders KPI metrics, app shifts, insights, and period controls."""
    now = datetime.now()

    # Seed 2 hours of Code.exe
    repo.insert_session(AppSession(
        process_name="Code.exe",
        window_title="dev",
        start_time=now - timedelta(hours=2),
        end_time=now,
        duration_s=7200.0,
        category=AppCategory.PROGRAMMING,
        is_idle=False,
    ))

    widget = WeeklyReportWidget(repo=repo)
    try:
        assert widget._card_active["val"].text() == "2h 0m"
        assert widget._apps_table.rowCount() == 1
        assert widget._apps_table.item(0, 0).text() == "Visual Studio Code"
        assert widget._apps_table.item(0, 2).text() == "2h 0m"

        # Period combo
        assert widget._period_combo.count() == 3
        # Switch to prior week (which has no data in this test DB)
        widget._period_combo.setCurrentIndex(1)
        assert widget._card_active["val"].text() == "0s"
        assert widget._insights_container.count() == len(widget._current_data.insights)
        expected_categories = len(widget._current_data.category_breakdown) or 1
        assert widget._cats_container.count() == expected_categories

        # Repeated report refreshes must replace nested rows cleanly.
        widget._period_combo.setCurrentIndex(2)
        widget._period_combo.setCurrentIndex(0)
        assert widget._insights_container.count() == len(widget._current_data.insights)
    finally:
        widget.deleteLater()
        QApplication.processEvents()
