from __future__ import annotations

import pytest
from threading import Event, get_ident
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from ui.main_window import MainWindow
from ui.widgets.animated_stacked_widget import AnimatedStackedWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


def test_rapid_page_switches_follow_latest_request_without_blank_effect(qapp):
    stack = AnimatedStackedWidget()
    for _ in range(3):
        stack.addWidget(QWidget())

    stack.setCurrentIndexAnimated(1)
    stack.setCurrentIndexAnimated(2)

    assert stack.currentIndex() == 2
    assert stack.currentWidget().graphicsEffect() is None


class _FakePage:
    def __init__(self):
        self.refresh_count = 0

    def on_data_changed(self):
        self.refresh_count += 1


class _FakeStack:
    def __init__(self, pages):
        self.pages = pages
        self.index = 0

    def currentIndex(self):
        return self.index

    def count(self):
        return len(self.pages)

    def widget(self, index):
        return self.pages[index]


class _FakeWindow:
    def __init__(self, pages):
        self._stack = _FakeStack(pages)


def test_page_refresh_runs_after_navigation_and_skips_obsolete_page(qapp):
    first, second = _FakePage(), _FakePage()
    window = _FakeWindow([first, second])

    MainWindow._refresh_current_page(window, 0)
    assert first.refresh_count == 0

    window._stack.index = 1
    qapp.processEvents()
    assert first.refresh_count == 0

    MainWindow._refresh_current_page(window, 1)
    assert second.refresh_count == 0
    qapp.processEvents()
    assert second.refresh_count == 1


def test_student_workspace_is_a_primary_sidebar_route(qapp):
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    sidebar = window._build_sidebar()

    assert window._student_btn.property("page_idx") == 12
    assert window._page_to_nav_btn[12] is window._student_btn
    assert window._student_btn in window._nav_buttons

    sidebar.deleteLater()
    window.deleteLater()
    qapp.processEvents()


def test_windows_hello_availability_check_runs_off_the_ui_thread(qapp, monkeypatch):
    from protection.windows_hello import HelloAvailability, WindowsHelloAuth

    started = Event()
    release = Event()
    ui_thread_id = get_ident()

    def controlled_check():
        started.set()
        release.wait(timeout=2)
        assert get_ident() != ui_thread_id
        return HelloAvailability.AVAILABLE

    monkeypatch.setattr(
        WindowsHelloAuth, "_query_availability", staticmethod(controlled_check)
    )
    auth = WindowsHelloAuth()
    results = []
    auth.availability_ready.connect(results.append)

    assert auth.request_availability()
    assert started.wait(timeout=1)
    worker = auth._availability_thread
    assert worker is not None and worker.daemon
    assert not auth.request_availability()
    assert results == []

    release.set()
    worker.join(timeout=2)
    qapp.processEvents()

    assert not worker.is_alive()
    assert results == [int(HelloAvailability.AVAILABLE)]


def test_app_locker_page_does_not_check_hello_synchronously(qapp, monkeypatch):
    from protection.app_locker import AppLockerManager
    from protection.windows_hello import HelloAvailability, WindowsHelloAuth
    from ui.pages.app_locker import AppLockerPage

    AppLockerManager._instance = None
    requested = []
    monkeypatch.setattr(
        WindowsHelloAuth,
        "check_availability",
        lambda _self: pytest.fail("App Locker must not block on a synchronous WinRT check"),
    )
    monkeypatch.setattr(
        WindowsHelloAuth,
        "request_availability",
        lambda self: requested.append(self),
    )

    page = AppLockerPage(protection_manager=MagicMock())
    assert page._hello_badge_lbl.text() == "Checking Windows Hello availability…"
    qapp.processEvents()
    assert requested == [page._hello_auth]

    page._hello_auth.availability_ready.emit(int(HelloAvailability.UNAVAILABLE))
    qapp.processEvents()
    assert "Notch PIN will be used" in page._hello_badge_lbl.text()

    page.deleteLater()
    qapp.processEvents()
    if AppLockerManager._instance is not None:
        AppLockerManager._instance._timer.stop()
    AppLockerManager._instance = None


def test_auth_dialog_keeps_pin_fallback_while_availability_is_pending(qapp, monkeypatch):
    from protection.windows_hello import HelloAvailability, WindowsHelloAuth
    from ui.widgets.auth_dialog import AppLockerAuthDialog

    requested = []
    monkeypatch.setattr(
        WindowsHelloAuth,
        "check_availability",
        lambda _self: pytest.fail("The authentication dialog must not block on a synchronous WinRT check"),
    )
    monkeypatch.setattr(
        WindowsHelloAuth,
        "request_availability",
        lambda self: requested.append(self),
    )

    dialog = AppLockerAuthDialog(
        "sample.exe", "Sample App", MagicMock(), auth_method="hello_pin"
    )
    qapp.processEvents()

    assert requested == [dialog._hello]
    assert dialog._hello_check_pending
    assert not dialog._pin_widget.isHidden()
    assert dialog._hello_btn.isHidden()

    dialog._on_hello_availability_ready(int(HelloAvailability.AVAILABLE))
    assert dialog._hello_available
    assert not dialog._hello_btn.isHidden()
    assert not dialog._pin_toggle_btn.isHidden()
    assert dialog._pin_widget.isHidden()

    dialog._on_hello_availability_ready(int(HelloAvailability.UNAVAILABLE))
    assert not dialog._hello_available
    assert dialog._hello_btn.isHidden()
    assert not dialog._pin_widget.isHidden()
    dialog.reject()
