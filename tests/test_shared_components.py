"""
tests/test_shared_components.py — Focused tests for Batch 2 Shared Component Library:
StatCard, StatusBadge, EntityRow, and SegmentedControl.
Verifies rendering, theme switching, accessibility, callbacks, keyboard interaction, and optional fields.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QPixmap, QIcon
from PySide6.QtWidgets import QApplication, QPushButton, QLabel

from ui.theme import ThemeManager
from ui.widgets.stat_card import StatCard
from ui.widgets.status_badge import StatusBadge
from ui.widgets.entity_row import EntityRow
from ui.widgets.segmented_control import SegmentedControl


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ─── 1. StatCard Tests ────────────────────────────────────────────────────────

def test_stat_card_initialization_and_optional_fields(qapp):
    """Test StatCard creation with and without optional fields."""
    # Full card
    card_full = StatCard(
        label="Screen Time",
        value="4h 30m",
        icon="clock",
        subtext="45m less than yesterday",
        trend="-12% vs yesterday",
        trend_direction="down",
    )
    card_full.show()

    assert card_full._label_label.text() == "SCREEN TIME"
    assert card_full._value_label.text() == "4h 30m"
    assert card_full._subtext_label is not None
    assert card_full._subtext_label.text() == "45m less than yesterday"
    assert not card_full._trend_label.isHidden()
    assert card_full._trend_label.text() == "-12% vs yesterday"

    # Minimal card without icon, subtext, or trend
    card_minimal = StatCard(label="Active Sessions", value="12")
    card_minimal.show()

    assert card_minimal._label_label.text() == "ACTIVE SESSIONS"
    assert card_minimal._value_label.text() == "12"
    assert card_minimal._icon_label.isHidden()
    assert card_minimal._subtext_label is None
    assert card_minimal._trend_label.isHidden()


def test_stat_card_updates_and_theme_switching(qapp):
    """Test updating StatCard properties and dynamic theme switching."""
    tm = ThemeManager.instance()
    tm.set_theme("dark", app=qapp)

    card = StatCard(label="Focus Score", value="85%", icon="focus")
    card.show()
    assert card._value_label.text() == "85%"

    # Dynamic updates
    card.set_metric("92%")
    assert card._value_label.text() == "92%"

    card.set_title("Deep Work Score")
    assert card._label_label.text() == "DEEP WORK SCORE"

    card.set_subtext("Top 10% this week")
    assert card._subtext_label.text() == "Top 10% this week"
    assert not card._subtext_label.isHidden()

    card.set_trend("+7%", direction="up")
    assert card._trend_label.text() == "+7%"
    assert not card._trend_label.isHidden()

    # Dynamic Theme Switch to Light
    tm.set_theme("light", app=qapp)
    assert card._value_label.text() == "92%"
    assert not card._trend_label.isHidden()

    # Switch back to Dark
    tm.set_theme("dark", app=qapp)
    assert card._value_label.text() == "92%"


# ─── 2. StatusBadge Tests ─────────────────────────────────────────────────────

def test_status_badge_variants_and_theme_switching(qapp):
    """Test all 5 semantic StatusBadge variants in Dark and Light themes."""
    tm = ThemeManager.instance()

    for variant in ["active", "warning", "exceeded", "locked", "neutral"]:
        badge = StatusBadge(text=variant.upper(), variant=variant, show_dot=True)
        badge.show()

        assert badge.variant == variant
        assert badge.text() == variant.upper()
        assert not badge._dot_lbl.isHidden()

        # Dark theme check
        tm.set_theme("dark", app=qapp)
        text_d, bg_d, border_d = badge._get_colors(is_dark=True)
        assert text_d is not None and bg_d is not None and border_d is not None

        # Light theme check
        tm.set_theme("light", app=qapp)
        text_l, bg_l, border_l = badge._get_colors(is_dark=False)
        assert text_l is not None and bg_l is not None and border_l is not None


def test_status_badge_setters_and_icons(qapp):
    """Test StatusBadge text, variant, dot, and icon setters."""
    badge = StatusBadge("Initial", variant="neutral")
    badge.show()

    assert badge.text() == "Initial"
    assert badge.variant == "neutral"
    assert badge._dot_lbl.isHidden()

    badge.set_text("Active Session")
    assert badge.text() == "Active Session"

    badge.set_variant("active")
    assert badge.variant == "active"

    badge.set_dot_visible(True)
    assert not badge._dot_lbl.isHidden()

    badge.set_icon("focus")
    assert not badge._icon_lbl.isHidden()


# ─── 3. EntityRow Tests ───────────────────────────────────────────────────────

def test_entity_row_initialization_and_optional_elements(qapp):
    """Test EntityRow creation with primary/secondary text, badge, progress, actions."""
    badge = StatusBadge("ACTIVE", variant="active")
    row = EntityRow(
        primary_text="Brave Browser",
        secondary_text="Productivity • 2h 15m",
        icon="browser",
        badge=badge,
        progress=0.75,
        trailing_text="2h 15m",
        entity_id="brave.exe",
    )
    row.show()

    assert row.entity_id == "brave.exe"
    assert row._primary_lbl.text() == "Brave Browser"
    assert row._secondary_lbl.text() == "Productivity • 2h 15m"
    assert not row._progress_bar.isHidden()
    assert row._progress_bar.value() == 75
    assert row._trailing_lbl.text() == "2h 15m"
    assert row.focusPolicy() == Qt.FocusPolicy.TabFocus


def test_entity_row_keyboard_and_click_callbacks(qapp):
    """Test EntityRow mouse click and keyboard activation (Space / Enter)."""
    row = EntityRow(primary_text="Spotify", entity_id="spotify.exe")
    row.show()

    clicked_ids = []
    row.clicked.connect(lambda eid: clicked_ids.append(eid))

    # Keyboard Enter
    enter_ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    row.keyPressEvent(enter_ev)
    assert clicked_ids == ["spotify.exe"]

    # Keyboard Space
    space_ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    row.keyPressEvent(space_ev)
    assert clicked_ids == ["spotify.exe", "spotify.exe"]


def test_entity_row_actions_and_updates(qapp):
    """Test adding action buttons and updating EntityRow elements."""
    row = EntityRow(primary_text="App Locker", secondary_text="Off")
    row.show()

    btn_action = QPushButton("Configure")
    row.add_action(btn_action)
    assert row._actions_layout.count() == 1

    # Updates
    row.set_primary_text("Notion")
    assert row._primary_lbl.text() == "Notion"

    row.set_secondary_text("Work & Notes")
    assert row._secondary_lbl.text() == "Work & Notes"

    row.set_progress(0.40)
    assert not row._progress_bar.isHidden()
    assert row._progress_bar.value() == 40

    row.set_progress(None)
    assert row._progress_bar.isHidden()


# ─── 4. SegmentedControl Tests ────────────────────────────────────────────────

def test_segmented_control_selection_and_signals(qapp):
    """Test SegmentedControl selection, current index/value/text, and emitted signals."""
    segments = [
        ("Today", 1),
        ("7 Days", 7),
        ("30 Days", 30),
    ]
    control = SegmentedControl(segments, default_index=0)
    control.show()

    assert control.count() == 3
    assert control.current_index() == 0
    assert control.current_value() == 1
    assert control.current_text() == "Today"

    emitted_values = []
    emitted_indices = []
    control.selection_changed.connect(lambda v: emitted_values.append(v))
    control.index_changed.connect(lambda i: emitted_indices.append(i))

    # Programmatic index change
    control.set_current_index(1)
    assert control.current_index() == 1
    assert control.current_value() == 7
    assert control.current_text() == "7 Days"
    assert emitted_values[-1] == 7
    assert emitted_indices[-1] == 1

    # Programmatic value change
    found = control.set_current_value(30)
    assert found is True
    assert control.current_index() == 2
    assert control.current_value() == 30


def test_segmented_control_keyboard_navigation(qapp):
    """Test SegmentedControl arrow keys navigation, Home, End, and Wrap."""
    segments = ["Day", "Week", "Month", "Year"]
    control = SegmentedControl(segments, default_index=0)
    control.show()

    # Key Right -> index 1
    ev_right = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
    control.keyPressEvent(ev_right)
    assert control.current_index() == 1
    assert control.current_text() == "Week"

    # Key Right -> index 2
    control.keyPressEvent(ev_right)
    assert control.current_index() == 2
    assert control.current_text() == "Month"

    # Key End -> index 3 (Year)
    ev_end = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_End, Qt.KeyboardModifier.NoModifier)
    control.keyPressEvent(ev_end)
    assert control.current_index() == 3
    assert control.current_text() == "Year"

    # Key Right wraps to 0
    control.keyPressEvent(ev_right)
    assert control.current_index() == 0
    assert control.current_text() == "Day"

    # Key Left wraps to 3
    ev_left = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.NoModifier)
    control.keyPressEvent(ev_left)
    assert control.current_index() == 3
    assert control.current_text() == "Year"

    # Key Home -> 0
    ev_home = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Home, Qt.KeyboardModifier.NoModifier)
    control.keyPressEvent(ev_home)
    assert control.current_index() == 0


def test_segmented_control_theme_switching(qapp):
    """Test SegmentedControl survives dynamic theme switching without error."""
    tm = ThemeManager.instance()
    control = SegmentedControl(["Option A", "Option B"], default_index=0)
    control.show()

    tm.set_theme("dark", app=qapp)
    assert control.current_index() == 0

    tm.set_theme("light", app=qapp)
    assert control.current_index() == 0

    tm.set_theme("dark", app=qapp)
    assert control.current_index() == 0
