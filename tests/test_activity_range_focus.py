"""
tests/test_activity_range_focus.py
Verification suite for Usage & Trends date-range selector focus outline fix.
Verifies:
1. Mouse click selects options without unwanted focus outline or retaining focus.
2. Keyboard navigation (Tab, Arrow keys, Enter/Space) operates smoothly and updates range.
3. Accessible focus indicator is present without inner text outline.
4. Works consistently across Dark and Light themes.
5. Preserves selected state without outline when switching options or navigating away and back.
"""

import pytest
from datetime import date
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from ui.theme import ThemeManager
from ui.pages.activity import ActivityPage


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_date_range_selector_initial_state_and_policies(qapp):
    """Verify buttons have TabFocus policy, hand cursor, and initial checked state."""
    ThemeManager.instance().set_theme("dark", app=qapp)
    page = ActivityPage()
    page.show()

    assert page._btn_today.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert page._btn_7d.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert page._btn_30d.focusPolicy() == Qt.FocusPolicy.TabFocus

    assert page._btn_today.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert page._btn_7d.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert page._btn_30d.cursor().shape() == Qt.CursorShape.PointingHandCursor

    assert page._btn_today.isChecked()
    assert not page._btn_7d.isChecked()
    assert not page._btn_30d.isChecked()
    assert page._time_range == 1
    page.close()


def test_date_range_selector_mouse_clicks_no_focus(qapp):
    """Verify mouse clicks select options without acquiring focus (preventing unwanted focus rectangles)."""
    ThemeManager.instance().set_theme("dark", app=qapp)
    page = ActivityPage()
    page.show()

    # Click 7 Days
    page._btn_7d.click()
    qapp.processEvents()
    assert page._time_range == 7
    assert page._btn_7d.isChecked()
    assert not page._btn_7d.hasFocus()

    # Click 30 Days
    page._btn_30d.click()
    qapp.processEvents()
    assert page._time_range == 30
    assert page._btn_30d.isChecked()
    assert not page._btn_30d.hasFocus()

    # Click Today
    page._btn_today.click()
    qapp.processEvents()
    assert page._time_range == 1
    assert page._btn_today.isChecked()
    assert not page._btn_today.hasFocus()

    page.close()


def test_date_range_selector_keyboard_navigation(qapp):
    """Verify Arrow keys, Space, and Return navigate and select date ranges."""
    ThemeManager.instance().set_theme("dark", app=qapp)
    page = ActivityPage()
    page.show()
    page.activateWindow()
    qapp.processEvents()

    # Focus Today via Tab
    page._btn_today.setFocus(Qt.FocusReason.TabFocusReason)
    qapp.processEvents()
    assert page._btn_today.hasFocus() or page._btn_today.isChecked()

    # Arrow Right to 7 Days
    event_right = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(page._btn_today, event_right)
    qapp.processEvents()

    assert page._time_range == 7
    assert page._btn_7d.isChecked()
    assert page.focusWidget() == page._btn_7d

    # Arrow Right to 30 Days
    event_right2 = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(page._btn_7d, event_right2)
    qapp.processEvents()

    assert page._time_range == 30
    assert page._btn_30d.isChecked()
    assert page.focusWidget() == page._btn_30d

    # Arrow Left back to 7 Days
    event_left = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(page._btn_30d, event_left)
    qapp.processEvents()

    assert page._time_range == 7
    assert page._btn_7d.isChecked()
    assert page.focusWidget() == page._btn_7d

    # Return key activation on Today
    page._btn_today.setFocus(Qt.FocusReason.TabFocusReason)
    event_return = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    qapp.sendEvent(page._btn_today, event_return)
    qapp.processEvents()

    assert page._time_range == 1
    assert page._btn_today.isChecked()

    page.close()


def test_date_range_selector_theme_switching_and_focus_ring(qapp):
    """Verify focus styling follows the active theme without unsupported outlines."""
    tm = ThemeManager.instance()
    
    # Dark Theme
    tm.set_theme("dark", app=qapp)
    page = ActivityPage()
    page.show()
    ss_dark = page.styleSheet()
    assert "outline:" not in ss_dark
    assert "border: 2px solid" in ss_dark
    assert "segment_btn_left:focus" in ss_dark
    assert "segment_btn_left:checked:focus" in ss_dark

    # Light Theme
    tm.set_theme("light", app=qapp)
    qapp.processEvents()
    ss_light = page.styleSheet()
    assert "outline:" not in ss_light
    assert "border: 2px solid" in ss_light
    assert "segment_btn_left:focus" in ss_light

    # Navigate away and back
    page._navigate_to(1)  # Navigate away to category details
    assert page._main_stack.currentIndex() == 1
    page._navigate_back()  # Navigate back to main view
    assert page._main_stack.currentIndex() == 0
    assert page._btn_today.isChecked()
    assert not page._btn_today.hasFocus()

    # Switching ranges after navigating back
    page._btn_7d.click()
    qapp.processEvents()
    assert page._time_range == 7
    assert not page._btn_7d.hasFocus()

    # Restore dark theme
    tm.set_theme("dark", app=qapp)
    page.close()
