from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from core.constants import APP_NAME, APP_VERSION
from core.logger import logger
from settings.manager import SettingsManager
from tracker.manager import TrackingManager
from ui.main_window import MainWindow
from ui.theme import apply_theme
from utils.win_utils import set_dpi_awareness


class DigitalWellbeingApp:
    def __init__(self, start_minimized: bool = False, server_name: Optional[str] = None) -> None:
        set_dpi_awareness()

        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setApplicationName(APP_NAME)
        self._app.setOrganizationName("DigitalWellbeing")
        # We manage the quit lifecycle manually — quitOnLastWindowClosed is
        # disabled so that destroying the window (via closeEvent) does not
        # trigger a second quit() call before our cleanup has finished.
        self._app.setQuitOnLastWindowClosed(False)

        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "app_icon.ico"
        if icon_path.exists():
            self._app.setWindowIcon(QIcon(str(icon_path)))

        # Guard flag: ensures _cleanup() and _quit() are idempotent and re-entrant safe.
        self._shutting_down: bool = False

        # Connect cleanup to aboutToQuit as a safety net for any unexpected exit path.
        self._app.aboutToQuit.connect(self._cleanup)

        # 1. Enforce single-instance execution via QLocalServer
        from PySide6.QtNetwork import QLocalServer, QLocalSocket, QAbstractSocket
        self._server_name = server_name or "DigitalWellbeingUniqueLocalServerKey"
        self._already_running = False

        import os
        is_test = os.environ.get("DW_TEST_MODE") == "1"
        is_debug = os.environ.get("DW_DEBUG_MODE") == "1"

        logger.info(f"[SINGLE_INSTANCE] Initializing single-instance check. Server name: {self._server_name}, Test Mode: {is_test}, Debug Mode: {is_debug}")

        if not is_test and not is_debug:
            socket = QLocalSocket(self._app)
            logger.info(f"[SINGLE_INSTANCE] Attempting to connect to existing server '{self._server_name}'...")
            socket.connectToServer(self._server_name)
            
            connected = socket.waitForConnected(500)
            if connected:
                logger.info(f"[SINGLE_INSTANCE] Successfully connected to existing server. Socket state: {socket.state()}")
                # An instance is already active. Notify and exit.
                socket.write(b"show_window")
                socket.flush()
                if socket.bytesToWrite() > 0:
                    socket.waitForBytesWritten(1000)
                if socket.bytesToWrite() == 0:
                    logger.info("[SINGLE_INSTANCE] Successfully transmitted 'show_window' request to existing instance.")
                else:
                    logger.warning("[SINGLE_INSTANCE] Failed to write to existing instance.")
                socket.disconnectFromServer()
                if socket.state() != QLocalSocket.LocalSocketState.UnconnectedState:
                    socket.waitForDisconnected(500)
                socket.close()
                self._already_running = True
                logger.info("Another active instance was detected. Sent show_window request and exiting.")
                return
            else:
                socket_err = socket.error()
                socket_err_str = socket.errorString()
                logger.info(f"[SINGLE_INSTANCE] Failed to connect to existing server. Connected: False, Error Code: {socket_err}, Error String: '{socket_err_str}'. Assuming no other instance is running.")

            # No active instance. Setup local server for this process.
            logger.info(f"[SINGLE_INSTANCE] Removing any stale server named '{self._server_name}'...")
            QLocalServer.removeServer(self._server_name)
            
            self._server = QLocalServer(self._app)
            listen_success = self._server.listen(self._server_name)
            logger.info(f"[SINGLE_INSTANCE] Starting server listen() result: {listen_success}")
            
            if not listen_success:
                logger.error("Failed to bind single-instance server listener: %s", self._server.errorString())
            else:
                self._server.newConnection.connect(self._on_new_connection)
                logger.info(f"[SINGLE_INSTANCE] Server is now listening on '{self._server_name}'")

        # 2. Standard initialization for primary process
        self._sm = SettingsManager()
        apply_theme(self._app, self._sm.theme)

        self._tracker = TrackingManager()
        from tracker.sleepguard import SleepGuardController
        self._sleepguard = SleepGuardController()
        self._window: Optional[MainWindow] = None
        self._tray: Optional[QSystemTrayIcon] = None

        self._setup_tray()
        
        from notifications.notifier import Notifier
        self._notifier = Notifier()
        if self._tray:
            Notifier.set_tray_icon(self._tray)
            
        self._tracker.start()
        self._sleepguard.start()

        from database.repository import Repository
        from protection.core import ProtectionManager
        self._protection_manager = ProtectionManager(Repository())
        self._tracker.add_active_tick_callback(self._protection_manager.tick)

        from protection.focus_scheduler import FocusScheduler
        self._focus_scheduler = FocusScheduler.instance(Repository())
        self._focus_scheduler.start()

        from protection.budgets import BudgetManager
        self._budget_manager = BudgetManager.instance(Repository(), protection_mgr=self._protection_manager)
        self._budget_manager.start()

        self._window = MainWindow(self._tracker, self._sleepguard, self._protection_manager)
        # Connect the window's quit request signal to our controlled shutdown method.
        self._window.quit_requested.connect(self._quit)
        self._window.focus_completed.connect(self._on_focus_completed)

        if not start_minimized:
            self._window.show()
        else:
            # Start minimized: don't show the main window. Tray icon remains active.
            logger.info("Starting minimized to tray; main window will not be shown")
            self._window.hide()

        from analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine()
        engine.ensure_historical_snapshots()
        from datetime import date
        self._last_checked_date = date.today()

        # Updater: check GitHub Releases for newer installers (non-blocking)
        try:
            from utils.updater import Updater
            from ui.widgets.update_dialog import UpdateDialog

            self._updater = Updater()
            self._latest_update_info = None
            self._active_update_dialog = None
            self._manual_update_check_in_progress = False
            self._has_checked_startup_update = False
            self._update_dismissed_this_session = False

            def _start_download_flow():
                if not self._latest_update_info:
                    return
                info = self._latest_update_info
                ver = info.get("version", "")
                if hasattr(self, "_window") and self._window and hasattr(self._window, "_settings_page"):
                    self._window._settings_page.set_download_progress(0, ver)

                self._updater.download_installer(
                    asset_url=info.get("asset_url"),
                    asset_name=info.get("asset_name"),
                    asset_id=info.get("asset_id"),
                    checksum_url=info.get("checksum_url"),
                    checksum_id=info.get("checksum_id"),
                    expected_sha256=info.get("expected_sha256"),
                    version=ver,
                )

            def _on_update_available(info: dict) -> None:
                self._latest_update_info = info
                is_manual = self._manual_update_check_in_progress
                self._manual_update_check_in_progress = False

                ver = info.get("version", "")
                if hasattr(self, "_window") and self._window and hasattr(self._window, "_settings_page"):
                    self._window._settings_page.set_update_available(ver)

                # If this was an automatic background check and user already dismissed it this session, skip modal dialog
                if not is_manual and self._update_dismissed_this_session:
                    logger.info("Updater: update available (%s) but dismissed for this session. Skipping modal dialog.", ver)
                    return

                # Defer if active SleepGuard countdown or active focus session
                sg_active = False
                try:
                    sg_active = getattr(self, "_sleepguard", None) and getattr(self._sleepguard, "_idle_fired", None) and self._sleepguard._idle_fired.is_set()
                except Exception:
                    pass
                focus_active = False
                try:
                    if hasattr(self, "_window") and self._window and hasattr(self._window, "_wellbeing_page"):
                        ft = getattr(self._window._wellbeing_page, "_focus_timer", None)
                        if ft and getattr(ft, "_is_running", False):
                            focus_active = True
                except Exception:
                    pass

                if sg_active or focus_active:
                    logger.info("Updater: deferring update dialog due to active session; will retry in 30s")
                    QTimer.singleShot(30_000, lambda: self._updater.check_for_updates())
                    return

                # Show update dialog
                try:
                    self._active_update_dialog = UpdateDialog(
                        current_version=APP_VERSION,
                        new_version=ver,
                        notes=info.get("notes", ""),
                        parent=self._window or None
                    )

                    self._active_update_dialog.update_now.connect(_start_download_flow)
                    self._active_update_dialog.later.connect(lambda: setattr(self, "_update_dismissed_this_session", True))
                    self._active_update_dialog.show()
                except Exception as exc:
                    logger.exception("Updater: failed to show update dialog: %s", exc)

            def _on_no_update():
                self._manual_update_check_in_progress = False
                if hasattr(self, "_window") and self._window and hasattr(self._window, "_settings_page"):
                    self._window._settings_page.set_update_status_up_to_date()

            def _on_check_error(msg: str):
                self._manual_update_check_in_progress = False
                if hasattr(self, "_window") and self._window and hasattr(self._window, "_settings_page"):
                    self._window._settings_page.set_update_error("Couldn't check for updates right now.")

            def _on_download_progress(pct: int):
                ver = self._latest_update_info.get("version", "") if self._latest_update_info else ""
                if hasattr(self, "_window") and self._window and hasattr(self._window, "_settings_page"):
                    self._window._settings_page.set_download_progress(pct, ver)
                if self._active_update_dialog:
                    try:
                        self._active_update_dialog.set_progress(pct)
                    except Exception:
                        pass

            def _on_download_complete(installer_path: str):
                ver = self._latest_update_info.get("version", "") if self._latest_update_info else ""
                if hasattr(self, "_window") and self._window and hasattr(self._window, "_settings_page"):
                    self._window._settings_page.set_installing_status(ver)
                if self._active_update_dialog:
                    try:
                        self._active_update_dialog.set_installing(ver)
                    except Exception:
                        pass

                # Launch Inno Setup installer via detached wrapper script and exit Notch cleanly
                self._updater.launch_installer_and_exit(installer_path)
                self._quit()

            def _on_download_error(msg: str):
                if hasattr(self, "_window") and self._window and hasattr(self._window, "_settings_page"):
                    self._window._settings_page.set_update_error("Couldn't check for updates right now.")
                if self._active_update_dialog:
                    try:
                        self._active_update_dialog.show_error(msg)
                    except Exception:
                        pass

            self._updater.update_available.connect(_on_update_available)
            self._updater.no_update.connect(_on_no_update)
            self._updater.error.connect(_on_check_error)
            self._updater.download_progress.connect(_on_download_progress)
            self._updater.download_complete.connect(_on_download_complete)
            self._updater.error.connect(_on_download_error)

            def _handle_manual_update_request():
                self._manual_update_check_in_progress = True
                self._updater.check_for_updates(force=True)

            self._window.manual_update_requested.connect(_handle_manual_update_request)
            self._window.update_now_requested.connect(_start_download_flow)
            self._window.update_later_requested.connect(lambda: setattr(self, "_update_dismissed_this_session", True))

            # Automatic check on startup (once per session, delayed by 5s)
            def _startup_update_check():
                if not self._has_checked_startup_update:
                    self._has_checked_startup_update = True
                    self._updater.check_for_updates()

            QTimer.singleShot(5_000, _startup_update_check)
        except Exception as exc:
            logger.warning("Updater initialization failed: %s", exc)

        # 8. Start Telemetry Heartbeat (10s delay to prevent startup blocking)
        from tracker.telemetry import TelemetryManager
        QTimer.singleShot(10000, lambda: TelemetryManager.instance().start_heartbeat())

        if os.environ.get("DW_SCREENSHOT_MODE") == "1":
            def take_screenshots():
                import time
                if self._window:
                    base_path = os.environ.get("DW_SCREENSHOT_DIR")
                    if not base_path:
                        base_path = str(Path(__file__).resolve().parents[2] / "scratch")
                    import os as _os
                    _os.makedirs(base_path, exist_ok=True)
                    
                    # Dashboard
                    self._window._navigate(0)
                    self._app.processEvents()
                    time.sleep(0.2)
                    self._window.grab().save(str(Path(base_path) / "real_home.png"))
                    
                    # Activity
                    self._window._navigate(1)
                    self._app.processEvents()
                    time.sleep(0.2)
                    self._window.grab().save(str(Path(base_path) / "real_activity.png"))
                    
                    # Settings
                    self._window._navigate(8)
                    self._app.processEvents()
                    time.sleep(0.2)
                    self._window.grab().save(str(Path(base_path) / "real_settings.png"))
                    
                self._app.quit()
            QTimer.singleShot(2000, take_screenshots)

        self._daily_check_timer = QTimer()
        self._daily_check_timer.setInterval(60_000)
        self._daily_check_timer.timeout.connect(self._on_daily_check_timer)
        self._daily_check_timer.start()

        logger.info("Application started successfully")

    def _on_new_connection(self) -> None:
        conn = self._server.nextPendingConnection()
        if conn:
            if conn.bytesAvailable() > 0 or conn.waitForReadyRead(1000):
                msg = conn.readAll().data().decode("utf-8", errors="ignore")
                logger.info("[SINGLE_INSTANCE] Server received IPC message: '%s'", msg)
                if "show_window" in msg:
                    self._show_window()
            conn.close()

    def _setup_tray(self) -> None:
        icon = self._get_tray_icon()
        self._tray = QSystemTrayIcon(icon, self._app)
        self._tray.setToolTip(APP_NAME)

        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background: #1e1e1e; color: #e8e8e8; border: 1px solid #333; border-radius: 8px; padding: 4px; }"
            "QMenu::item { padding: 8px 20px; border-radius: 6px; }"
            "QMenu::item:selected { background: #0078d4; }"
        )

        show_action = QAction("Open Notch", self._app)
        show_action.triggered.connect(self._show_window)

        toggle_tracking = QAction("Pause Tracking", self._app)
        toggle_tracking.triggered.connect(self._toggle_tracking)
        self._toggle_tracking_action = toggle_tracking

        quit_action = QAction("Quit", self._app)
        quit_action.triggered.connect(self._quit)

        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(toggle_tracking)
        menu.addSeparator()
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _get_tray_icon(self) -> QIcon:
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "app_icon.ico"
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QIcon()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show_window()

    def _show_window(self) -> None:
        if self._window:
            self._window.show()
            self._window.showNormal()
            self._window.raise_()
            self._window.activateWindow()
            hwnd = int(self._window.winId()) if self._window else 0
            logger.info("[SINGLE_INSTANCE] Restored main window (winId=%d, isVisible=%s)", hwnd, self._window.isVisible())
            try:
                if hwnd:
                    import ctypes
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception as exc:
                logger.debug("Win32 SetForegroundWindow skipped: %s", exc)

    def _toggle_tracking(self) -> None:
        if self._tracker.is_running:
            self._tracker.stop()
            self._toggle_tracking_action.setText("Resume Tracking")
            self._notifier.notify(APP_NAME, "Tracking paused.", duration=2)
        else:
            self._tracker.start()
            self._toggle_tracking_action.setText("Pause Tracking")
            self._notifier.notify(APP_NAME, "Tracking resumed.", duration=2)

    def _on_focus_completed(self) -> None:
        self._notifier.notify(
            "Focus Session Complete",
            "Great job! Take a well-deserved break.",
            duration=5,
        )

    def _on_daily_check_timer(self) -> None:
        from datetime import date
        today = date.today()
        from analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine()
        
        # Check for date change to capture historical snapshot
        if self._last_checked_date < today:
            logger.info("Date changed from %s to %s. Generating daily snapshot.", self._last_checked_date, today)
            engine.generate_daily_snapshot(self._last_checked_date)
            self._last_checked_date = today

        if not self._sm.get_bool("notifications_enabled", True):
            return

        limit_min = self._sm.get_int("daily_limit_minutes", 480)
        summary = engine.get_today_summary()
        used_min = summary.active_time_s / 60

        if used_min >= limit_min:
            h = int(limit_min // 60)
            m = int(limit_min % 60)
            self._notifier.notify(
                "Daily Limit Reached",
                f"You've used {h}h {m}m of screen time today.",
                duration=5,
            )
            self._daily_check_timer.setInterval(3_600_000)

    def _cleanup(self) -> None:
        """
        Synchronous resource cleanup. This method is idempotent — calling it
        more than once is safe. It is connected to aboutToQuit as a safety net,
        but is also called directly by _quit() before app.quit() to guarantee
        the tracking thread and tray icon are fully torn down before the process
        exits.
        """
        if self._shutting_down:
            logger.info("[LIFECYCLE] DigitalWellbeingApp._cleanup() called but _shutting_down is already True (ignoring re-entrant call)")
            return
        self._shutting_down = True

        from utils.debug_lifecycle import log_lifecycle_state
        logger.info("[LIFECYCLE] Executing clean shutdown: stopping tracker, timers, and tray...")
        log_lifecycle_state("DigitalWellbeingApp._cleanup: BEFORE cleanup operations")

        # 1. Stop the daily check timer first (no more callbacks).
        if hasattr(self, "_daily_check_timer") and self._daily_check_timer:
            logger.info("[LIFECYCLE] Stopping _daily_check_timer")
            self._daily_check_timer.stop()

        # 2. Stop the tracker and sleepguard.
        if hasattr(self, "_tracker") and self._tracker:
            logger.info("[LIFECYCLE] Stopping _tracker")
            self._tracker.stop()

        if hasattr(self, "_sleepguard") and self._sleepguard:
            logger.info("[LIFECYCLE] Stopping _sleepguard")
            self._sleepguard.stop()

        if hasattr(self, "_focus_scheduler") and self._focus_scheduler:
            logger.info("[LIFECYCLE] Stopping _focus_scheduler")
            self._focus_scheduler.stop()

        if hasattr(self, "_budget_manager") and self._budget_manager:
            logger.info("[LIFECYCLE] Stopping _budget_manager")
            self._budget_manager.stop()

        # 2b. Close repository connections for this (main) thread. Background threads
        # are responsible for closing their own thread-local connections on exit.
        try:
            from database.repository import Repository
            Repository().close()
            logger.info("Closed main-thread repository DB connection during cleanup")
        except Exception as exc:
            logger.warning("Failed to close main-thread DB connection during cleanup: %s", exc)

        # 3. Close the single-instance server so subsequent launches can connect.
        if hasattr(self, "_server") and self._server:
            logger.info("[LIFECYCLE] Closing QLocalServer")
            self._server.close()
            from PySide6.QtNetwork import QLocalServer
            QLocalServer.removeServer(self._server_name)

        # 4. Hide and destroy the tray icon immediately so it vanishes from the taskbar.
        if hasattr(self, "_tray") and self._tray:
            logger.info("[LIFECYCLE] Destroying QSystemTrayIcon")
            self._tray.hide()
            self._tray.setContextMenu(None)
            self._tray.setParent(None)
            self._tray = None

        log_lifecycle_state("DigitalWellbeingApp._cleanup: AFTER cleanup operations")
        logger.info("[LIFECYCLE] Clean shutdown complete.")

    def _quit(self) -> None:
        """
        The single, authoritative exit point for the application.
        Always call this instead of app.quit() directly to ensure resources
        are released synchronously before the Qt event loop exits.
        """
        from utils.debug_lifecycle import log_lifecycle_state
        logger.info("[LIFECYCLE] DigitalWellbeingApp._quit() CALLED")

        if self._shutting_down:
            logger.info("[LIFECYCLE] DigitalWellbeingApp._quit() called but already shutting down")
            return

        logger.info("[LIFECYCLE] Initiating controlled application shutdown...")
        self._cleanup()

        log_lifecycle_state("DigitalWellbeingApp._quit: IMMEDIATELY BEFORE QApplication.quit()")
        logger.info("[LIFECYCLE] Calling self._app.quit()")
        self._app.quit()
        logger.info("[LIFECYCLE] self._app.quit() CALLED")

    def run(self) -> int:
        if self._already_running:
            logger.info("[LIFECYCLE] App already running, returning exit code 0")
            return 0
        from utils.debug_lifecycle import log_lifecycle_state
        logger.info("[LIFECYCLE] DigitalWellbeingApp.run() entering self._app.exec()")
        log_lifecycle_state("DigitalWellbeingApp.run: BEFORE app.exec()")
        
        result = self._app.exec()
        
        logger.info("[LIFECYCLE] DigitalWellbeingApp.run() self._app.exec() RETURNED with code %d", result)
        log_lifecycle_state("DigitalWellbeingApp.run: AFTER app.exec()")
        return result
