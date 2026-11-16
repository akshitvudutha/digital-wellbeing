"""
tests/test_dashboard_redesign.py — Comprehensive tests for the Batch 3 redesigned Dashboard.
Verifies component structure, signal contracts, navigation callbacks,
theme transitions, and zero/populated data states.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import uuid
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from analytics.engine import AnalyticsEngine
from core.constants import AppCategory
from database.models import AppSession
from database.repository import Repository
from ui.pages.dashboard import DashboardPage
from ui.theme import ThemeManager
from ui.widgets.entity_row import EntityRow
from ui.widgets.stat_card import StatCard
from ui.widgets.status_badge import StatusBadge


@pytest.fixture(autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def repo(tmp_path: Path):
    db_file = tmp_path / f"test_dashboard_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


def test_dashboard_instantiation_and_structure(repo):
    """Verify the redesigned dashboard instantiates with StatCards and structural sections."""
    page = DashboardPage()
    assert page is not None
    assert isinstance(page._screen_time_card, StatCard)
    assert isinstance(page._active_time_card, StatCard)
    assert isinstance(page._idle_time_card, StatCard)
    assert isinstance(page._focus_badge, StatusBadge)
    page.close()


def test_dashboard_signals_and_card_clicks(repo):
    """Verify signals are emitted on card clicks and interactive row clicks."""
    nav_target = []
    def on_nav(idx: int):
        nav_target.append(idx)

    page = DashboardPage(navigate_callback=on_nav)

    screen_time_emitted = []
    page.request_screen_time_details.connect(lambda: screen_time_emitted.append(True))
    page._screen_time_card.card_clicked.emit()
    assert len(screen_time_emitted) == 1

    focus_emitted = []
    page.request_focus_session.connect(lambda: focus_emitted.append(True))
    page._start_focus_btn.clicked.emit()
    assert len(focus_emitted) == 1

    # Navigation callbacks
    page._nav_to(2)
    assert nav_target == [2]

    page.close()


def test_dashboard_data_population_and_entity_rows(repo):
    """Verify populated database data displays in StatCards and EntityRows."""
    now = datetime.now()
    # Add dummy usage for today
    repo.insert_session(AppSession(
        process_name="Code.exe",
        window_title="main.py",
        start_time=now - timedelta(hours=1),
        end_time=now,
        duration_s=3600.0,
        category=AppCategory.PROGRAMMING,
        is_idle=False,
    ))
    repo.insert_session(AppSession(
        process_name="chrome.exe",
        window_title="Documentation",
        start_time=now - timedelta(minutes=30),
        end_time=now,
        duration_s=1800.0,
        category=AppCategory.BROWSER,
        is_idle=False,
    ))

    page = DashboardPage()
    page._refresh()

    # Screen time should reflect 1h 30m = 5400s
    assert "1h 30m" in page._screen_time_card.value

    # Check that Top Apps list populated EntityRows
    app_rows = page._apps_card.findChildren(EntityRow)
    assert len(app_rows) >= 2
    app_names = [row.title for row in app_rows]
    assert any("Code" in name for name in app_names)
    assert any("chrome" in name.lower() for name in app_names)

    # Check Category list populated EntityRows
    cat_rows = page._cats_card.findChildren(EntityRow)
    assert len(cat_rows) >= 2

    page.close()


def test_dashboard_empty_data_state(repo):
    """Verify empty/zero usage state is handled cleanly without exceptions or fabricated trends."""
    page = DashboardPage()
    page._refresh()

    assert page._screen_time_card.value == "0s"
    # Trend label should be empty or hidden when there is no comparison data
    assert page._screen_time_card.trend_text == "" or not page._screen_time_card._trend_label.isVisible()

    # Empty state labels should be displayed in the lists
    app_rows = page._apps_card.findChildren(EntityRow)
    assert len(app_rows) == 0

    page.close()


def test_dashboard_theme_switching(repo):
    """Verify dashboard adapts cleanly to dynamic dark and light theme switching."""
    page = DashboardPage()
    tm = ThemeManager.instance()

    # Switch to dark
    tm.set_theme(True)
    page._apply_theme(True)

    # Switch to light
    tm.set_theme(False)
    page._apply_theme(False)

    # Switch back to dark
    tm.set_theme(True)
    page._apply_theme(True)

    page.close()
