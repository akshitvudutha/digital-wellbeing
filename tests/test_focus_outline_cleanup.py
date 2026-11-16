"""Regression checks for mouse and keyboard focus styling across Notch controls."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from database.repository import Repository
from ui.pages.insights import InsightsPage
from ui.theme import FocusIndicatorStyle, ThemeManager
from ui.widgets.entity_row import EntityRow
from ui.widgets.focus_timer import FocusTimerWidget
from ui.widgets.segmented_control import SegmentedControl


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def repo(tmp_path: Path):
    Repository.set_db_path_override(tmp_path / f"focus_ui_{uuid.uuid4().hex}.db")
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


class _Signal:
    def connect(self, _slot):
        pass


class _FocusManagerStub:
    """Only supplies the signals FocusTimerWidget subscribes to during setup."""

    tick = _Signal()
    focus_state_changed = _Signal()
    focus_completed = _Signal()
    focus_paused = _Signal()
    focus_resumed = _Signal()
    focus_reset = _Signal()
    focus_cancelled = _Signal()
    mode_changed = _Signal()
    is_active = False
    is_paused = False
    is_strict = False
    seconds_remaining = 0
    current_mode = "custom"
    current_mode_apps = []
    current_mode_websites = []

    def get_mode_websites(self, _mode):
        return []


def _show(widget, qapp):
    widget.resize(900, 640)
    widget.show()
    qapp.processEvents()


def test_insights_mouse_click_clears_keyboard_ring_and_keeps_selected_state(qapp, repo):
    tm = ThemeManager.instance()
    tm.set_theme("dark", app=qapp)
    window = QMainWindow()
    page = InsightsPage(repo=repo)
    window.setCentralWidget(page)
    _show(window, qapp)

    weekly = page._btn_subtab_weekly
    weekly.setFocus(Qt.FocusReason.TabFocusReason)
    qapp.processEvents()
    assert weekly.hasFocus()

    QTest.mouseClick(weekly, Qt.MouseButton.LeftButton)
    qapp.processEvents()

    assert not weekly.hasFocus()
    assert page._stack.currentIndex() == 1
    assert weekly.objectName() == "subtab_active"
    assert "border: 2px solid" in page.styleSheet()

    window.close()
    page.deleteLater()
    qapp.processEvents()


@pytest.mark.parametrize("theme,ring", [("dark", "#10B981"), ("light", "#047857")])
def test_keyboard_focus_indicator_uses_theme_token(qapp, repo, theme, ring):
    tm = ThemeManager.instance()
    tm.set_theme(theme, app=qapp)
    window = QMainWindow()
    page = InsightsPage(repo=repo)
    window.setCentralWidget(page)
    _show(window, qapp)

    weekly = page._btn_subtab_weekly
    weekly.setFocus(Qt.FocusReason.TabFocusReason)
    qapp.processEvents()

    assert weekly.hasFocus()
    assert ring in page.styleSheet()
    assert "border: 2px solid" in page.styleSheet()
    assert "outline:" not in page.styleSheet()

    window.close()
    page.deleteLater()
    qapp.processEvents()


def test_themed_focus_ring_replaces_native_button_and_tab_rect(qapp):
    tm = ThemeManager.instance()
    tm.set_theme("dark", app=qapp)

    button = QPushButton("Action")
    tab_bar = QTabBar()
    edit = QLineEdit()

    assert isinstance(tm._focus_style, FocusIndicatorStyle)
    assert tm._focus_style.suppresses_native_focus_rect(button)
    assert tm._focus_style.suppresses_native_focus_rect(tab_bar)
    assert not tm._focus_style.suppresses_native_focus_rect(edit)


def test_theme_switches_do_not_reinstall_or_nest_focus_style(qapp):
    tm = ThemeManager.instance()

    tm.set_theme("dark", app=qapp)
    focus_style = tm._focus_style
    tm.set_theme("light", app=qapp)
    tm.set_theme("dark", app=qapp)

    assert tm._focus_style is focus_style
    assert tm._focus_app is qapp


def test_shared_filter_handles_buttons_checkboxes_and_editable_inputs(qapp):
    tm = ThemeManager.instance()
    tm.set_theme("dark", app=qapp)
    window = QMainWindow()
    body = QWidget()
    layout = QVBoxLayout(body)
    button = QPushButton("Action")
    button.setCheckable(True)
    checkbox = QCheckBox("Option")
    checkbox.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    edit = QLineEdit()
    edit.setPlaceholderText("Editable text")
    layout.addWidget(button)
    layout.addWidget(checkbox)
    layout.addWidget(edit)
    window.setCentralWidget(body)
    _show(window, qapp)

    assert button.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert checkbox.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert edit.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert "QAbstractButton:focus" in qapp.styleSheet()
    assert "QLineEdit:focus" in qapp.styleSheet()

    checkbox.setFocus(Qt.FocusReason.TabFocusReason)
    qapp.processEvents()
    assert checkbox.hasFocus()
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    qapp.processEvents()
    assert not checkbox.hasFocus()
    assert button.isChecked()
    assert not button.hasFocus()

    QTest.mouseClick(edit, Qt.MouseButton.LeftButton)
    qapp.processEvents()
    assert edit.hasFocus()

    window.close()
    qapp.processEvents()


def test_shared_clickable_widgets_retain_keyboard_focus_support(qapp):
    tm = ThemeManager.instance()
    tm.set_theme("light", app=qapp)
    window = QMainWindow()
    body = QWidget()
    layout = QVBoxLayout(body)
    row = EntityRow("Visual Studio Code", "Programming", entity_id="code")
    segments = SegmentedControl([("Day", 1), ("Week", 7)])
    layout.addWidget(row)
    layout.addWidget(segments)
    window.setCentralWidget(body)
    _show(window, qapp)

    assert row.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert segments.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert row.property("mouse_focus_clears") is True
    assert segments.property("mouse_focus_clears") is True

    row.setFocus(Qt.FocusReason.TabFocusReason)
    qapp.processEvents()
    assert row.hasFocus()
    QTest.mouseClick(row, Qt.MouseButton.LeftButton)
    qapp.processEvents()
    assert not row.hasFocus()

    segment_button = segments._buttons[1]
    segment_button.setFocus(Qt.FocusReason.TabFocusReason)
    qapp.processEvents()
    assert segment_button.hasFocus()
    QTest.mouseClick(segment_button, Qt.MouseButton.LeftButton)
    qapp.processEvents()
    assert not segment_button.hasFocus()
    assert segment_button.isChecked()

    window.close()
    qapp.processEvents()


def test_focus_timer_controls_use_keyboard_focus_policy(qapp):
    tm = ThemeManager.instance()
    tm.set_theme("dark", app=qapp)
    widget = FocusTimerWidget(focus_manager=_FocusManagerStub())
    _show(widget, qapp)

    assert widget._start_btn.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert widget._reset_btn.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert widget._active_stop_btn.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert widget._active_pause_btn.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert all(chip.focusPolicy() == Qt.FocusPolicy.TabFocus for chip in widget._chips)
    assert widget._student_profile_combo.focusPolicy() == Qt.FocusPolicy.TabFocus
    assert widget._student_profile_combo.findData("reading") > 0

    widget.close()
    widget.deleteLater()
    qapp.processEvents()
