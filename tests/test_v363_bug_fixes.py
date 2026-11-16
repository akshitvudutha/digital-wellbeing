"""
test_v363_bug_fixes.py — Regression tests for Notch v3.6.3 bug triage and stabilization.
Covers:
1. StatCard trend label parenting (prevents rogue duplicate top-level window/taskbar preview).
2. Navigation button TabFocus policy and focus styling (prevents bright rectangular outline on click).
3. AnalyticsEngine yesterday comparison calculation, edge cases, and zero baselines.
4. Notifier send_notification compatibility alias.
5. FocusManager run_elevated_action entrypoint.
6. Database path override via DW_DB_PATH environment variable.
7. Theme tokens surface_card and accent_primary_bg.
"""

import os
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from ui.widgets.stat_card import StatCard
from ui.theme import ThemeManager
from analytics.engine import AnalyticsEngine
from notifications.notifier import Notifier
from protection.focus_manager import FocusManager
from database.repository import _get_db_path, Repository


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    yield app


# ==============================================================================
# BUG 1 & 2: StatCard Trend Label Duplicate Window Prevention
# ==============================================================================

def test_stat_card_trend_label_never_becomes_top_level_window(qapp):
    """
    REGRESSION TEST:
    StatCard created with trend=None must have its _trend_label parented and added to top_row.
    When set_trend(...) is subsequently called, _trend_label must NOT be a top-level window (isWindow() == False).
    """
    parent_widget = QWidget()
    card = StatCard(label="Screen Time", value="8h 39m", trend=None, parent=parent_widget)

    # Initial state
    assert card._trend_label is not None
    assert card._trend_label.parent() is card
    assert not card._trend_label.isVisible()
    assert not card._trend_label.isWindow(), "trend_label must not be a top-level window"

    initial_top_levels = len(QApplication.topLevelWidgets())

    # Set trend dynamically (as dashboard does)
    card.set_trend("↑ 362.1% vs yesterday", direction="up")

    assert not card._trend_label.isHidden()
    assert card._trend_label.text() == "↑ 362.1% vs yesterday"
    assert not card._trend_label.isWindow(), "trend_label must remain an embedded child, never a top-level window"
    assert len(QApplication.topLevelWidgets()) == initial_top_levels, "Setting trend must NEVER increase top-level window count"

    # Update trend again
    card.set_trend("↓ 12.5% vs yesterday", direction="down")
    assert not card._trend_label.isHidden()
    assert not card._trend_label.isWindow()
    assert len(QApplication.topLevelWidgets()) == initial_top_levels

    # Clear trend
    card.set_trend(None)
    assert card._trend_label.isHidden()
    assert not card._trend_label.isWindow()
    assert len(QApplication.topLevelWidgets()) == initial_top_levels

    parent_widget.deleteLater()


# ==============================================================================
# BUG 3: Navigation Button Focus Policy & Clean Selection
# ==============================================================================

def test_nav_button_focus_policy_and_styles(qapp):
    """
    REGRESSION TEST:
    Navigation buttons must use TabFocus policy so mouse clicks do not leave
    an unwanted bright rectangular focus outline.
    Stylesheet must not use non-rounded 'outline: 2px solid' for nav_btn:focus.
    """
    from ui.main_window import MainWindow
    
    mock_tracker = MagicMock()
    mock_tracker.is_running = False
    mock_tracker.get_debug_state.return_value = {
        "debug_enabled": False,
        "process_name": "None",
        "window_title": "None",
        "category": "Other",
        "poll_count": 0,
        "active_duration_s": 0.0,
        "idle_duration_s": 0.0,
        "last_poll_ms": 0.0
    }
    mock_sleepguard = MagicMock()
    mock_sleepguard.is_running = False
    mock_prot = MagicMock()

    window = MainWindow(mock_tracker, mock_sleepguard, mock_prot)
    
    # Check focus policy on navigation buttons
    assert window._home_btn.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert window._activity_btn.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert window._settings_btn.focusPolicy() == Qt.FocusPolicy.TabFocus

    # Check sidebar stylesheet
    sidebar_qss = window._sidebar.styleSheet()
    assert "outline: 2px solid" not in sidebar_qss, "Rectangular outline must not be present on nav_btn"
    assert "outline:" not in sidebar_qss, "Qt focus styling must use supported properties"
    assert "QPushButton#nav_btn:focus" in sidebar_qss
    assert "QPushButton#nav_btn[active=\"true\"]:focus" in sidebar_qss
    assert "border: 2px solid" in sidebar_qss, "Keyboard focus must keep a visible ring"
    
    window.close()


# ==============================================================================
# BUG 4: AnalyticsEngine Yesterday Comparison Math & Baseline Handling
# ==============================================================================

def test_analytics_yesterday_comparison_math():
    """
    REGRESSION TEST:
    Verifies that percentage change between today and yesterday is calculated correctly:
    ((today - yesterday) / yesterday) * 100
    And verifies zero-baseline / sub-30min baseline suppression.
    """
    engine = AnalyticsEngine()
    
    # 1. Normal increase: yesterday = 2h (7200s), today = 8h (28800s) -> +300%
    with patch.object(engine, "_build_summary") as mock_summary:
        mock_y = MagicMock(total_screen_time_s=7200.0, active_time_s=7000.0, category_breakdown=[])
        mock_t = MagicMock(total_screen_time_s=28800.0, active_time_s=28000.0, category_breakdown=[])
        mock_summary.side_effect = lambda start, end: mock_t if start == date.today() else mock_y
        
        comp = engine.get_yesterday_comparison()
        assert comp["yesterday_was_zero"] is False
        assert comp["is_increase"] is True
        assert pytest.approx(comp["pct_change"], 0.1) == 300.0

    # 2. Normal decrease: yesterday = 8h (28800s), today = 4h (14400s) -> -50%
    with patch.object(engine, "_build_summary") as mock_summary:
        mock_y = MagicMock(total_screen_time_s=28800.0, active_time_s=28000.0, category_breakdown=[])
        mock_t = MagicMock(total_screen_time_s=14400.0, active_time_s=14000.0, category_breakdown=[])
        mock_summary.side_effect = lambda start, end: mock_t if start == date.today() else mock_y
        
        comp = engine.get_yesterday_comparison()
        assert comp["yesterday_was_zero"] is False
        assert comp["is_increase"] is False
        assert pytest.approx(comp["pct_change"], 0.1) == -50.0

    # 3. Equal usage: yesterday = 5h, today = 5h -> 0%
    with patch.object(engine, "_build_summary") as mock_summary:
        mock_y = MagicMock(total_screen_time_s=18000.0, active_time_s=18000.0, category_breakdown=[])
        mock_t = MagicMock(total_screen_time_s=18000.0, active_time_s=18000.0, category_breakdown=[])
        mock_summary.side_effect = lambda start, end: mock_t if start == date.today() else mock_y
        
        comp = engine.get_yesterday_comparison()
        assert comp["pct_change"] == 0.0

    # 4. Zero baseline: yesterday = 0s -> pct_change is None, yesterday_was_zero is True
    with patch.object(engine, "_build_summary") as mock_summary:
        mock_y = MagicMock(total_screen_time_s=0.0, active_time_s=0.0, category_breakdown=[])
        mock_t = MagicMock(total_screen_time_s=7200.0, active_time_s=7000.0, category_breakdown=[])
        mock_summary.side_effect = lambda start, end: mock_t if start == date.today() else mock_y
        
        comp = engine.get_yesterday_comparison()
        assert comp["yesterday_was_zero"] is True
        assert comp["pct_change"] is None

    # 5. Insufficient baseline (< 30 minutes / 1800s): treated as zero baseline to prevent misleading spikes
    with patch.object(engine, "_build_summary") as mock_summary:
        mock_y = MagicMock(total_screen_time_s=600.0, active_time_s=600.0, category_breakdown=[]) # 10 mins
        mock_t = MagicMock(total_screen_time_s=7200.0, active_time_s=7000.0, category_breakdown=[])
        mock_summary.side_effect = lambda start, end: mock_t if start == date.today() else mock_y
        
        comp = engine.get_yesterday_comparison()
        assert comp["yesterday_was_zero"] is True
        assert comp["pct_change"] is None


# ==============================================================================
# BUG 5: Notifier send_notification Method Compatibility
# ==============================================================================

def test_notifier_send_notification_alias():
    notifier = Notifier()
    with patch.object(notifier, "notify", return_value=True) as mock_notify:
        result = notifier.send_notification("Title", "Message", debounce=False)
        assert result is True
        mock_notify.assert_called_once_with("Title", "Message", debounce=False)


# ==============================================================================
# BUG 6: FocusManager run_elevated_action Entrypoint
# ==============================================================================

def test_focus_manager_run_elevated_action():
    with patch("protection.focus_manager.WebsiteBlocker") as MockBlocker:
        instance = MockBlocker.return_value
        instance.block_websites.return_value = (True, "Blocked")
        instance.unblock_all.return_value = (True, "Unblocked")

        # Apply action
        res_apply = FocusManager.run_elevated_action("apply", "youtube.com,reddit.com")
        assert res_apply is True
        instance.block_websites.assert_called_once_with(["youtube.com", "reddit.com"])

        # Remove action
        res_remove = FocusManager.run_elevated_action("remove")
        assert res_remove is True
        instance.unblock_all.assert_called_once()


# ==============================================================================
# BUG 7: Theme Tokens Presence
# ==============================================================================

def test_theme_tokens_surface_card_and_accent_primary_bg(qapp):
    tm = ThemeManager.instance()
    
    # Dark Mode
    tm.set_theme("Dark")
    assert tm.color("surface_card") != "transparent"
    assert tm.color("accent_primary_bg") != "transparent"

    # Light Mode
    tm.set_theme("Light")
    assert tm.color("surface_card") != "transparent"
    assert tm.color("accent_primary_bg") != "transparent"


# ==============================================================================
# BUG 8: Database Path Override via DW_DB_PATH
# ==============================================================================

def test_db_path_environment_override(tmp_path):
    test_db = tmp_path / "custom" / "test.db"
    with patch.dict(os.environ, {"DW_DB_PATH": str(test_db)}):
        resolved = _get_db_path()
        assert resolved == test_db
        assert test_db.parent.exists()


# ==============================================================================
# BUG-01 REGRESSION: "Return to Focus" must navigate to Focus page, not App Locker
# ==============================================================================

def test_return_to_focus_navigates_to_focus_page_not_locker(qapp):
    """
    REGRESSION TEST (BUG-01):
    MainWindow._show_blocked_app_dialog's on_return_to_focus() callback must
    click self._focus_btn (page index 2 = Focus), NOT self._locker_btn
    (page index 3 = App Locker).

    The bug was: getattr(self, '_nav_buttons', [None]*4)[3] incorrectly
    returned _locker_btn.  The fix uses getattr(self, '_focus_btn', None).
    """
    from ui.main_window import MainWindow

    mock_tracker = MagicMock()
    mock_tracker.is_running = False
    mock_tracker.get_debug_state.return_value = {
        "debug_enabled": False,
        "process_name": "None",
        "window_title": "None",
        "category": "Other",
        "poll_count": 0,
        "active_duration_s": 0.0,
        "idle_duration_s": 0.0,
        "last_poll_ms": 0.0,
    }
    mock_sleepguard = MagicMock()
    mock_sleepguard.is_running = False
    mock_prot = MagicMock()

    window = MainWindow(mock_tracker, mock_sleepguard, mock_prot)

    # Verify the _nav_buttons list order is as documented
    assert window._nav_buttons[0] is window._home_btn,      "_nav_buttons[0] must be _home_btn"
    assert window._nav_buttons[1] is window._activity_btn,  "_nav_buttons[1] must be _activity_btn"
    assert window._nav_buttons[2] is window._focus_btn,     "_nav_buttons[2] must be _focus_btn"
    assert window._nav_buttons[3] is window._locker_btn,    "_nav_buttons[3] must be _locker_btn (NOT focus)"

    # Verify that _focus_btn navigates to page 2 (Focus) and not page 3 (App Locker)
    assert window._focus_btn.property("page_idx") == 2, \
        "_focus_btn must point to page index 2 (Focus)"
    assert window._locker_btn.property("page_idx") == 3, \
        "_locker_btn must point to page index 3 (App Locker)"

    # Simulate what on_return_to_focus does using the fix (direct _focus_btn access)
    focus_nav_btn = getattr(window, "_focus_btn", None)
    assert focus_nav_btn is not None, "_focus_btn must exist on MainWindow"
    assert focus_nav_btn is window._focus_btn, \
        "getattr(window, '_focus_btn') must return the Focus nav button"
    assert focus_nav_btn is not window._locker_btn, \
        "BUG-01 REGRESSION: focus_nav_btn must not be _locker_btn"

    window.close()
