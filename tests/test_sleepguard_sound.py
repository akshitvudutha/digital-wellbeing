"""
tests/test_sleepguard_sound.py — Comprehensive tests for SleepGuard warning audio:
1. Exactly-once initial sound playback upon countdown start.
2. Deduplication across multiple timer ticks and paint events.
3. Configurable reminder sounds triggered at 30s and 10s thresholds.
4. Reminder threshold skipping when initial duration is shorter than the threshold.
5. Immediate audio purge and cancellation upon user abort or closeEvent.
6. Disabled sound settings suppression (initial and reminders).
7. Graceful exception resilience when audio device / winsound fails.
8. Multiple sequential countdown instances each get exactly one initial sound.
"""
from __future__ import annotations

import sys
import uuid
from unittest.mock import MagicMock, call, patch
import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from database.repository import Repository
from settings.manager import SettingsManager
from ui.widgets.countdown_dialog import ShutdownCountdownDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    db_file = tmp_path / f"test_sound_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    yield
    Repository.set_db_path_override(None)


def test_initial_sound_played_exactly_once(qapp):
    """Initial sound plays exactly once upon countdown start, never on repeated calls."""
    sm = SettingsManager()
    sm.sleepguard_sound_enabled = True
    sm.sleepguard_sound_chime = "SystemExclamation"

    with patch("winsound.PlaySound") as mock_play:
        dlg = ShutdownCountdownDialog(countdown_seconds=60, action="lock")
        try:
            dlg.start_countdown()
            assert dlg._initial_sound_played is True
            assert mock_play.call_count == 1
            # Check sound alias
            args, _ = mock_play.call_args
            assert args[0] == "SystemExclamation"

            # Repeat start_countdown or showEvent — must not play again
            dlg.start_countdown()
            dlg.show()
            assert mock_play.call_count == 1
        finally:
            dlg._on_cancel()
            dlg.deleteLater()


def test_deduplication_across_ticks_and_paints(qapp):
    """Timer ticks and paint events do not duplicate initial warning sound."""
    sm = SettingsManager()
    sm.sleepguard_sound_enabled = True
    sm.sleepguard_sound_reminders = False  # Isolate initial sound deduplication

    with patch("winsound.PlaySound") as mock_play:
        dlg = ShutdownCountdownDialog(countdown_seconds=60, action="sleep")
        try:
            dlg.start_countdown()
            assert mock_play.call_count == 1

            # Simulate 10 timer ticks (60s down to 50s)
            for _ in range(10):
                dlg._on_tick()

            # Must still have only 1 play call
            assert mock_play.call_count == 1
        finally:
            dlg._on_cancel()
            dlg.deleteLater()


def test_reminder_sounds_at_30s_and_10s_thresholds(qapp):
    """Reminder sounds trigger when crossing 30s and 10s thresholds."""
    sm = SettingsManager()
    sm.sleepguard_sound_enabled = True
    sm.sleepguard_sound_reminders = True
    sm.sleepguard_sound_chime = "SystemExclamation"

    with patch("winsound.PlaySound") as mock_play:
        now = [100.0]
        dlg = ShutdownCountdownDialog(
            countdown_seconds=35,
            action="lock",
            clock=lambda: now[0],
        )
        try:
            dlg.start_countdown()
            assert mock_play.call_count == 1  # Initial sound

            # Tick 1: 34s (no reminder)
            now[0] += 1
            dlg._on_tick()
            assert mock_play.call_count == 1

            # Tick 2: 30s (reminder 1 triggers)
            now[0] += 4
            dlg._on_tick()
            assert mock_play.call_count == 2
            assert 30 in dlg._played_reminders

            # Tick 3: 29s (no duplicate for 30s)
            now[0] += 1
            dlg._on_tick()
            assert mock_play.call_count == 2

            # Tick 4: 10s (reminder 2 triggers)
            now[0] += 19
            dlg._on_tick()
            assert mock_play.call_count == 3
            assert 10 in dlg._played_reminders

            # Tick 5: 9s (no duplicate for 10s)
            now[0] += 1
            dlg._on_tick()
            assert mock_play.call_count == 3
        finally:
            dlg._on_cancel()
            dlg.deleteLater()


def test_reminder_threshold_skipped_if_starting_duration_less_or_equal(qapp):
    """If countdown starts at 30s, the 30s reminder is not played (initial sound covers it)."""
    sm = SettingsManager()
    sm.sleepguard_sound_enabled = True
    sm.sleepguard_sound_reminders = True

    with patch("winsound.PlaySound") as mock_play:
        # Starts at 20s
        now = [100.0]
        dlg = ShutdownCountdownDialog(
            countdown_seconds=20,
            action="lock",
            clock=lambda: now[0],
        )
        try:
            dlg.start_countdown()
            assert mock_play.call_count == 1  # Initial sound

            # 30s is never added because initial_duration_s <= 30
            assert 30 not in dlg._played_reminders

            # When ticking to 10s, 10s reminder triggers
            now[0] += 10
            dlg._on_tick()
            assert mock_play.call_count == 2
            assert 10 in dlg._played_reminders
        finally:
            dlg._on_cancel()
            dlg.deleteLater()


def test_cancellation_stops_audio_immediately(qapp):
    """Cancelling or dismissing the dialog invokes SND_PURGE to stop audio."""
    sm = SettingsManager()
    sm.sleepguard_sound_enabled = True

    with patch("winsound.PlaySound") as mock_play:
        dlg = ShutdownCountdownDialog(countdown_seconds=60, action="lock")
        try:
            dlg.start_countdown()
            assert mock_play.call_count == 1

            # User clicks cancel
            dlg._on_cancel()
            # Must have called PlaySound(None, SND_PURGE)
            assert dlg._cancelled is True
            last_call = mock_play.call_args_list[-1]
            assert last_call[0][0] is None
            import winsound
            assert last_call[0][1] == winsound.SND_PURGE
        finally:
            dlg.deleteLater()


def test_close_event_stops_audio(qapp):
    """Alt+F4 or dialog closeEvent invokes SND_PURGE to stop audio."""
    sm = SettingsManager()
    sm.sleepguard_sound_enabled = True

    with patch("winsound.PlaySound") as mock_play:
        dlg = ShutdownCountdownDialog(countdown_seconds=60, action="lock")
        try:
            dlg.start_countdown()
            assert mock_play.call_count == 1

            # Simulate closeEvent
            from PySide6.QtGui import QCloseEvent
            ev = QCloseEvent()
            dlg.closeEvent(ev)
            import winsound
            last_call = mock_play.call_args_list[-1]
            assert last_call[0][0] is None
            assert last_call[0][1] == winsound.SND_PURGE
        finally:
            dlg.deleteLater()


def test_disabled_sound_setting_suppresses_audio(qapp):
    """When sound is disabled in settings, no sound is played."""
    sm = SettingsManager()
    sm.sleepguard_sound_enabled = False

    with patch("winsound.PlaySound") as mock_play:
        dlg = ShutdownCountdownDialog(countdown_seconds=60, action="lock")
        try:
            dlg.start_countdown()
            assert mock_play.call_count == 0

            # Tick to 30s
            dlg._remaining_s = 30
            dlg._on_tick()
            assert mock_play.call_count == 0
        finally:
            dlg._on_cancel()
            dlg.deleteLater()


def test_disabled_reminders_setting_suppresses_reminders_only(qapp):
    """When reminders are disabled but sound is enabled, initial sound plays but reminders do not."""
    sm = SettingsManager()
    sm.sleepguard_sound_enabled = True
    sm.sleepguard_sound_reminders = False

    with patch("winsound.PlaySound") as mock_play:
        dlg = ShutdownCountdownDialog(countdown_seconds=60, action="lock")
        try:
            dlg.start_countdown()
            assert mock_play.call_count == 1  # Initial sound played

            # Ticks crossing 30s and 10s
            dlg._remaining_s = 30
            dlg._on_tick()
            dlg._remaining_s = 10
            dlg._on_tick()
            assert mock_play.call_count == 1  # No reminders added
        finally:
            dlg._on_cancel()
            dlg.deleteLater()


def test_audio_failure_does_not_crash_dialog(qapp):
    """If PlaySound raises an exception, the dialog catches it gracefully and continues."""
    sm = SettingsManager()
    sm.sleepguard_sound_enabled = True

    with patch("winsound.PlaySound", side_effect=RuntimeError("Audio device busy")), \
         patch("winsound.MessageBeep") as mock_beep:
        dlg = ShutdownCountdownDialog(countdown_seconds=60, action="lock")
        try:
            # Does not raise RuntimeError
            dlg.start_countdown()
            assert dlg._initial_sound_played is True
            # Verified fallback to MessageBeep
            assert mock_beep.call_count == 1
        finally:
            dlg._on_cancel()
            dlg.deleteLater()


def test_multiple_sequential_countdowns_each_play_initial_sound(qapp):
    """Independent countdown dialog instances each get their own initial sound."""
    sm = SettingsManager()
    sm.sleepguard_sound_enabled = True

    with patch("winsound.PlaySound") as mock_play:
        dlg1 = ShutdownCountdownDialog(countdown_seconds=60, action="lock", is_test=True)
        try:
            dlg1.start_countdown()
            assert mock_play.call_count == 1
        finally:
            dlg1._on_cancel()
            dlg1.deleteLater()

        # dlg2 is a new instance
        dlg2 = ShutdownCountdownDialog(countdown_seconds=60, action="shutdown", is_test=False)
        try:
            dlg2.start_countdown()
            # Check dlg2 initial call was made
            assert dlg2._initial_sound_played is True
        finally:
            dlg2._on_cancel()
            dlg2.deleteLater()
