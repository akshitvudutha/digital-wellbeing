"""Deterministic deadline and lifecycle regression tests for Notch timers."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow

import protection.focus_manager as focus_manager_module
import ui.widgets.focus_timer as focus_timer_module
from database.repository import Repository
from protection.deep_work import DeepWorkController, DeepWorkPhase
from protection.focus_manager import FocusManager
from ui.widgets.countdown_dialog import ShutdownCountdownDialog
from ui.widgets.focus_timer import FocusTimerWidget


class FakeClock:
    def __init__(self, now: float = 1000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeRepository:
    def get_setting(self, _key: str):
        return None

    def set_setting(self, _key: str, _value: str) -> None:
        pass


class FakeWebsiteBlocker:
    def __init__(self):
        self.blocked = []

    def cleanup_orphaned_blocks(self):
        pass

    def clean_domain(self, domain: str):
        return domain.strip().lower() if domain else None

    def block_websites(self, domains):
        self.blocked = list(domains)
        return True, "test blocker"

    def unblock_all(self):
        self.blocked.clear()
        return True, "test blocker"


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def focus_clock():
    return FakeClock()


@pytest.fixture
def focus_manager(monkeypatch, focus_clock, qapp):
    monkeypatch.setattr(focus_manager_module, "WebsiteBlocker", FakeWebsiteBlocker)
    manager = FocusManager(FakeRepository())
    manager._clock = focus_clock
    manager._run_enforcement_scan = lambda: None
    yield manager
    if manager.is_active:
        manager.cancel_focus()
    manager._timer.stop()
    manager.deleteLater()
    qapp.processEvents()


def test_configured_15_minute_countdown_starts_at_900_seconds(focus_manager):
    ticks = []
    focus_manager.tick.connect(ticks.append)

    assert focus_manager.start_focus(minutes=15, strict_mode=False)
    assert focus_manager.is_active
    assert focus_manager.configured_minutes == 15
    assert focus_manager.total_duration_seconds == 900
    assert focus_manager.seconds_remaining == 900
    assert ticks == [900]


def test_15_minute_focus_chip_starts_exact_ui_configured_deadline(
    qapp, focus_manager, focus_clock, monkeypatch
):
    class AcceptedPreflight:
        def __init__(self, **_kwargs):
            pass

        def exec(self):
            return True

    monkeypatch.setattr(
        focus_timer_module, "DeepFocusPreflightDialog", AcceptedPreflight
    )
    window = QMainWindow()
    widget = FocusTimerWidget(focus_manager=focus_manager)
    window.setCentralWidget(widget)
    window.resize(900, 640)
    window.show()
    qapp.processEvents()

    fifteen_minute_chip = next(
        chip for chip in widget._chips if chip.property("minutes") == 15
    )
    QTest.mouseClick(fifteen_minute_chip, Qt.MouseButton.LeftButton)
    QTest.mouseClick(widget._start_btn, Qt.MouseButton.LeftButton)
    qapp.processEvents()

    assert widget._selected_minutes == 15
    assert focus_manager.configured_minutes == 15
    assert focus_manager.total_duration_seconds == 900
    assert focus_manager.seconds_remaining == 900
    assert focus_manager._deadline == pytest.approx(focus_clock() + 900)
    assert widget._active_time_display.text() == "15:00"

    window.close()
    qapp.processEvents()


@pytest.mark.parametrize("minutes", [15, 25, 45, 60, 90])
def test_each_focus_preset_starts_at_its_exact_configured_duration(focus_manager, minutes):
    assert focus_manager.start_focus(minutes=minutes, strict_mode=False)

    expected_seconds = minutes * 60
    assert focus_manager.configured_minutes == minutes
    assert focus_manager.total_duration_seconds == expected_seconds
    assert focus_manager.seconds_remaining == expected_seconds
    assert focus_manager._deadline == pytest.approx(
        focus_manager._clock() + expected_seconds
    )


def test_focus_service_preserves_an_exact_custom_duration(focus_manager):
    custom_seconds = 1234.5

    assert focus_manager.start_focus(
        minutes=1, duration_seconds=custom_seconds, strict_mode=False
    )

    assert focus_manager.total_duration_seconds == 1235
    assert focus_manager.seconds_remaining == 1235
    assert focus_manager._deadline == pytest.approx(
        focus_manager._clock() + custom_seconds
    )


def test_deadline_progression_does_not_lose_time_on_early_callbacks(focus_manager, focus_clock):
    assert focus_manager.start_focus(minutes=15)
    focus_clock.advance(0.4)
    focus_manager._on_tick()
    assert focus_manager.seconds_remaining == 900

    focus_clock.advance(0.4)
    focus_manager._on_tick()
    assert focus_manager.seconds_remaining == 900

    focus_clock.advance(0.2)
    focus_manager._on_tick()
    assert focus_manager.seconds_remaining == 899

    focus_clock.advance(14.0)
    focus_manager._on_tick()
    assert focus_manager.seconds_remaining == 885


def test_focus_completes_at_deadline_once_and_not_before(focus_manager, focus_clock):
    completed = []
    focus_manager.focus_completed.connect(lambda: completed.append(True))
    assert focus_manager.start_focus(minutes=15)

    focus_clock.advance(899.9)
    focus_manager._on_tick()
    assert focus_manager.is_active
    assert focus_manager.seconds_remaining == 1
    assert completed == []

    focus_clock.advance(0.1)
    focus_manager._on_tick()
    focus_manager._on_tick()
    assert not focus_manager.is_active
    assert focus_manager.seconds_remaining == 0
    assert completed == [True]


def test_pause_and_resume_preserves_fractional_remaining_time(focus_manager, focus_clock):
    assert focus_manager.start_focus(minutes=15)
    focus_clock.advance(100.4)
    assert focus_manager.pause_focus()
    assert focus_manager.is_paused
    assert focus_manager.seconds_remaining == 800
    assert focus_manager._paused_remaining_seconds == pytest.approx(799.6)

    focus_clock.advance(500)
    focus_manager._on_tick()
    assert focus_manager.seconds_remaining == 800
    assert focus_manager.resume_focus()
    assert not focus_manager.is_paused

    focus_clock.advance(799.5)
    focus_manager._on_tick()
    assert focus_manager.is_active
    assert focus_manager.seconds_remaining == 1

    focus_clock.advance(0.1)
    focus_manager._on_tick()
    assert not focus_manager.is_active


def test_reset_restores_configured_duration_in_active_and_paused_states(focus_manager, focus_clock):
    assert focus_manager.start_focus(minutes=15)
    focus_clock.advance(250.25)
    focus_manager._on_tick()
    assert focus_manager.reset_focus()
    assert focus_manager.seconds_remaining == 900

    focus_clock.advance(20.5)
    assert focus_manager.pause_focus()
    assert focus_manager.reset_focus()
    assert focus_manager.seconds_remaining == 900
    assert focus_manager._paused_remaining_seconds == 900
    assert focus_manager.resume_focus()
    assert focus_manager.seconds_remaining == 900


def test_cancellation_prevents_completion_action(focus_manager, focus_clock):
    completed = []
    cancelled = []
    focus_manager.focus_completed.connect(lambda: completed.append(True))
    focus_manager.focus_cancelled.connect(lambda: cancelled.append(True))

    assert focus_manager.start_focus(minutes=15)
    focus_clock.advance(120)
    assert focus_manager.cancel_focus()
    focus_manager._on_tick()
    assert not focus_manager.is_active
    assert completed == []
    assert cancelled == [True]


def test_duplicate_start_and_callbacks_do_not_duplicate_completion(focus_manager, focus_clock):
    completed = []
    focus_manager.focus_completed.connect(lambda: completed.append(True))
    assert focus_manager.start_focus(minutes=15)
    assert not focus_manager.start_focus(minutes=15)
    assert focus_manager._timer.interval() == 1000

    focus_clock.advance(900)
    for _ in range(5):
        focus_manager._on_tick()
    assert completed == [True]


def test_late_callback_after_event_loop_stall_completes_without_drift(focus_manager, focus_clock):
    completed = []
    focus_manager.focus_completed.connect(lambda: completed.append(True))
    assert focus_manager.start_focus(minutes=15)

    focus_clock.advance(960)
    focus_manager._on_tick()
    assert not focus_manager.is_active
    assert focus_manager.seconds_remaining == 0
    assert completed == [True]


def test_page_recreation_and_minimized_window_do_not_restart_countdown(qapp, focus_manager, focus_clock):
    window = QMainWindow()
    first_page = FocusTimerWidget(focus_manager=focus_manager)
    window.setCentralWidget(first_page)
    first_page.set_preset(15)
    window.resize(900, 640)
    window.show()
    qapp.processEvents()
    assert focus_manager.start_focus(minutes=15)

    window.takeCentralWidget()
    first_page.deleteLater()
    qapp.processEvents()
    replacement = FocusTimerWidget(focus_manager=focus_manager)
    window.setCentralWidget(replacement)
    replacement._sync_ui_state()
    window.showMinimized()
    qapp.processEvents()

    focus_clock.advance(840)
    focus_manager._on_tick()
    assert focus_manager.is_active
    assert focus_manager.seconds_remaining == 60
    assert replacement._active_time_display.text() == "01:00"

    focus_clock.advance(60)
    focus_manager._on_tick()
    assert not focus_manager.is_active
    assert replacement._time_display.text() == "15:00"
    window.close()
    qapp.processEvents()


def test_zero_remaining_boundary_completes_without_negative_time(focus_manager, focus_clock):
    completed = []
    focus_manager.focus_completed.connect(lambda: completed.append(True))
    assert focus_manager.start_focus(minutes=1)
    focus_clock.advance(60)
    focus_manager._on_tick()
    assert focus_manager.seconds_remaining == 0
    assert not focus_manager.is_active
    assert completed == [True]


@pytest.fixture
def repository(tmp_path: Path):
    Repository.set_db_path_override(tmp_path / f"deep_work_timer_{uuid.uuid4().hex}.db")
    instance = Repository()
    yield instance
    instance.close()
    Repository.set_db_path_override(None)


@pytest.fixture
def deep_work(repository):
    clock = FakeClock()
    focus = MagicMock()
    focus.is_active = False
    focus.is_paused = False
    focus.start_focus.return_value = True
    focus.stop_focus.return_value = True
    controller = DeepWorkController(
        repo=repository,
        focus_mgr=focus,
        notifier=MagicMock(),
        clock=clock,
    )
    yield controller, clock, focus
    if controller.is_active:
        controller.cancel_session()


def test_deep_work_phase_uses_deadline_and_does_not_finish_early(deep_work):
    controller, clock, _focus = deep_work
    assert controller.start_session("One interval", work_minutes=1, break_minutes=1, total_intervals=1)

    clock.advance(59.5)
    controller._on_tick()
    assert controller.phase == DeepWorkPhase.WORK
    assert controller.remaining_seconds == 1

    clock.advance(0.5)
    controller._on_tick()
    assert controller.phase == DeepWorkPhase.IDLE
    assert controller.remaining_seconds == 0


def test_deep_work_late_callback_carries_elapsed_time_across_phases_once(deep_work):
    controller, clock, _focus = deep_work
    completed = []
    controller.session_completed.connect(completed.append)
    assert controller.start_session("Two intervals", work_minutes=1, break_minutes=1, total_intervals=2)

    # One late UI callback arrives at the full 1 + 1 + 1 minute session deadline.
    clock.advance(180)
    controller._on_tick()

    assert controller.phase == DeepWorkPhase.IDLE
    assert len(completed) == 1
    assert completed[0].actual_work_s == pytest.approx(120)
    assert completed[0].actual_break_s == pytest.approx(60)
    controller._on_tick()
    assert len(completed) == 1


def test_deep_work_pause_resume_preserves_exact_remaining_time(deep_work):
    controller, clock, _focus = deep_work
    assert controller.start_session("Pause and resume", work_minutes=1)
    clock.advance(10.4)
    controller.pause_session()
    assert controller.phase == DeepWorkPhase.PAUSED_WORK
    assert controller.remaining_seconds == 50
    assert controller._phase_remaining_exact_s == pytest.approx(49.6)

    clock.advance(300)
    controller._on_tick()
    assert controller.remaining_seconds == 50
    controller.resume_session()
    assert controller._monotonic_deadline == pytest.approx(clock() + 49.6)


def test_sleepguard_countdown_is_deadline_based_and_starts_only_once(qapp, monkeypatch, focus_clock):
    class FakeSettings:
        sleepguard_sound_enabled = False
        sleepguard_sound_reminders = False
        sleepguard_sound_chime = "SystemExclamation"

    import settings.manager
    monkeypatch.setattr(settings.manager, "SettingsManager", FakeSettings)

    dialog = ShutdownCountdownDialog(
        countdown_seconds=60, action="lock", is_test=True, clock=focus_clock
    )
    dialog._stop_sound = lambda: None
    completed = []
    dialog.test_completed.connect(lambda: completed.append(True))

    assert dialog.start_countdown()
    deadline = dialog._deadline
    assert not dialog.start_countdown()
    assert dialog._deadline == deadline

    focus_clock.advance(0.5)
    dialog._on_tick()
    assert dialog._remaining_s == 60
    focus_clock.advance(59.0)
    dialog._on_tick()
    assert dialog._remaining_s == 1
    assert completed == []

    focus_clock.advance(0.5)
    dialog._on_tick()
    dialog._on_tick()
    assert dialog._completed
    assert completed == [True]
    dialog.deleteLater()
    qapp.processEvents()


def test_sleepguard_cancellation_suppresses_completion(qapp, monkeypatch, focus_clock):
    class FakeSettings:
        sleepguard_sound_enabled = False
        sleepguard_sound_reminders = False
        sleepguard_sound_chime = "SystemExclamation"

    import settings.manager
    monkeypatch.setattr(settings.manager, "SettingsManager", FakeSettings)

    dialog = ShutdownCountdownDialog(
        countdown_seconds=60, action="lock", is_test=True, clock=focus_clock
    )
    dialog._stop_sound = lambda: None
    completed = []
    cancelled = []
    dialog.test_completed.connect(lambda: completed.append(True))
    dialog.shutdown_cancelled.connect(lambda: cancelled.append(True))
    assert dialog.start_countdown()

    dialog.force_cancel()
    focus_clock.advance(60)
    dialog._on_tick()
    assert dialog._cancelled
    assert completed == []
    assert cancelled == [True]
    dialog.deleteLater()
    qapp.processEvents()
