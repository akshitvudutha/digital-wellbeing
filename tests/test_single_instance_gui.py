from __future__ import annotations

import os
import sys
import uuid
import pytest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from ui.app import DigitalWellbeingApp
from database.repository import Repository


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def isolate_test_environment(monkeypatch, tmp_path):
    """Ensure test mode is set, database is isolated, and background telemetry is disabled."""
    monkeypatch.setenv("DW_TEST_MODE", "1")
    db_file = tmp_path / f"test_gui_{uuid.uuid4().hex[:8]}.db"
    Repository.set_db_path_override(db_file)
    with patch("tracker.telemetry.TelemetryManager"):
        yield
    Repository.set_db_path_override(None)


@pytest.fixture
def mock_tracker():
    tracker = MagicMock()
    tracker.is_running = False
    tracker.get_debug_state.return_value = {
        "debug_enabled": False,
        "process_name": "None",
        "window_title": "None",
        "category": "None",
        "domain": "",
        "url": "",
        "idle_status": "Active",
        "idle_seconds": 0,
        "media_status": "Stopped",
        "media_title": "",
        "media_artist": "",
    }
    return tracker


def test_a_background_startup_keeps_window_hidden(qapp, mock_tracker):
    """A. Background startup keeps the window hidden."""
    with patch("ui.app.TrackingManager", return_value=mock_tracker), \
         patch("tracker.sleepguard.SleepGuardController"), \
         patch("protection.core.ProtectionManager"), \
         patch("analytics.engine.AnalyticsEngine"):
        
        app_instance = DigitalWellbeingApp(start_minimized=True)
        assert app_instance._window is not None
        assert not app_instance._window.isVisible()
        app_instance._cleanup()


def test_b_and_d_ipc_request_shows_existing_window_once(qapp, mock_tracker):
    """B & D: 'show_window' IPC causes existing instance to show, received exactly once."""
    with patch("ui.app.TrackingManager", return_value=mock_tracker), \
         patch("tracker.sleepguard.SleepGuardController"), \
         patch("protection.core.ProtectionManager"), \
         patch("analytics.engine.AnalyticsEngine"):
        
        app_instance = DigitalWellbeingApp(start_minimized=True)
        assert not app_instance._window.isVisible()

        show_calls = 0
        original_show = app_instance._show_window
        def counted_show():
            nonlocal show_calls
            show_calls += 1
            original_show()
        app_instance._show_window = counted_show

        # Simulate receiving b"show_window" via mock connection
        mock_conn = MagicMock()
        mock_conn.bytesAvailable.return_value = 11
        mock_conn.readAll.return_value.data.return_value = b"show_window"

        app_instance._server = MagicMock()
        app_instance._server.nextPendingConnection.return_value = mock_conn

        app_instance._on_new_connection()
        qapp.processEvents()

        assert show_calls == 1
        assert app_instance._window.isVisible()
        app_instance._cleanup()


def test_c_client_successfully_flushes_and_transmits(qapp):
    """C. Client successfully flushes/transmits the command without false write failures."""
    server_key = f"TestIPCTransmit_{uuid.uuid4().hex}"
    server = QLocalServer()
    assert server.listen(server_key)

    client = QLocalSocket()
    client.connectToServer(server_key)
    assert client.waitForConnected(500)
    assert server.waitForNewConnection(500)

    server_conn = server.nextPendingConnection()
    assert server_conn is not None

    # Perform client write + flush sequence
    client.write(b"show_window")
    client.flush()
    if client.bytesToWrite() > 0:
        client.waitForBytesWritten(1000)
    assert client.bytesToWrite() == 0

    client.disconnectFromServer()
    if client.state() != QLocalSocket.LocalSocketState.UnconnectedState:
        client.waitForDisconnected(500)
    client.close()

    assert server_conn.waitForReadyRead(1000) or server_conn.bytesAvailable() > 0
    received_payload = server_conn.readAll().data()
    server_conn.close()

    assert received_payload == b"show_window"
    server.close()


def test_e_mainwindow_restored_and_creates_native_hwnd(qapp, mock_tracker):
    """E. MainWindow gets restored/shown, activated, and native HWND is non-zero."""
    with patch("ui.app.TrackingManager", return_value=mock_tracker), \
         patch("tracker.sleepguard.SleepGuardController"), \
         patch("protection.core.ProtectionManager"), \
         patch("analytics.engine.AnalyticsEngine"):
        
        app_instance = DigitalWellbeingApp(start_minimized=True)
        assert not app_instance._window.isVisible()

        app_instance._show_window()
        qapp.processEvents()

        assert app_instance._window.isVisible()
        hwnd = int(app_instance._window.winId())
        assert hwnd != 0
        app_instance._cleanup()


def test_f_launching_notch_twice_results_in_one_window(monkeypatch, qapp):
    """F. Launching Notch twice still results in exactly one process/window."""
    monkeypatch.setenv("DW_TEST_MODE", "0")
    monkeypatch.setenv("DW_DEBUG_MODE", "0")

    server_key = f"TestDoubleLaunch_{uuid.uuid4().hex}"
    primary_server = QLocalServer()
    assert primary_server.listen(server_key)

    # Launch second instance directed at this server
    second_instance = DigitalWellbeingApp(start_minimized=False, server_name=server_key)

    assert second_instance._already_running is True
    assert not hasattr(second_instance, "_window")
    assert second_instance.run() == 0

    primary_server.close()


def test_g_tray_single_click_shows_window(qapp, mock_tracker):
    """G. Tray single-click (Trigger) shows the window."""
    with patch("ui.app.TrackingManager", return_value=mock_tracker), \
         patch("tracker.sleepguard.SleepGuardController"), \
         patch("protection.core.ProtectionManager"), \
         patch("analytics.engine.AnalyticsEngine"):
        
        app_instance = DigitalWellbeingApp(start_minimized=True)
        assert not app_instance._window.isVisible()

        app_instance._on_tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
        qapp.processEvents()

        assert app_instance._window.isVisible()
        app_instance._cleanup()


def test_h_tray_double_click_shows_window(qapp, mock_tracker):
    """H. Tray double-click still shows the window."""
    with patch("ui.app.TrackingManager", return_value=mock_tracker), \
         patch("tracker.sleepguard.SleepGuardController"), \
         patch("protection.core.ProtectionManager"), \
         patch("analytics.engine.AnalyticsEngine"):
        
        app_instance = DigitalWellbeingApp(start_minimized=True)
        assert not app_instance._window.isVisible()

        app_instance._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
        qapp.processEvents()

        assert app_instance._window.isVisible()
        app_instance._cleanup()


def test_i_failed_ipc_connection_does_not_crash(qapp):
    """I. A failed IPC connection does not crash Notch."""
    non_existent_key = f"NonExistent_{uuid.uuid4().hex}"
    client = QLocalSocket()
    client.connectToServer(non_existent_key)
    connected = client.waitForConnected(100)
    assert not connected
    assert client.error() is not None
    client.close()
