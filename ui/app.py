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
    def __init__(self, start_minimized: bool = False) -> None:
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
        self._server_name = "DigitalWellbeingUniqueLocalServerKey"
        self._already_running = False

        import os
        is_test = os.environ.get("DW_TEST_MODE") == "1"
        is_debug = os.environ.get("DW_DEBUG_MODE") == "1"

        logger.info(f"[SINGLE_INSTANCE] Initializing single-instance check. Server name: {self._server_name}, Test Mode: {is_test}, Debug Mode: {is_debug}")

        if not is_test and not is_debug:
            socket = QLocalSocket(self._app)
            logger.info(f"[SINGLE_INSTANCE] Attempting to connect to existing server '{self._server_name}'...")
            socket.connectToServer(self._server_name)
            
            connected = socket.waitForConnected(200)
            if connected:
                logger.info(f"[SINGLE_INSTANCE] Successfully connected to existing server. Socket state: {socket.state()}")
                # An instance is already active. Notify and exit.
                socket.write(b"show_window")
                if socket.waitForBytesWritten(500):
                    logger.info("[SINGLE_INSTANCE] Successfully wrote 'show_window' request to existing instance.")
                else:
                    logger.warning("[SINGLE_INSTANCE] Failed to write to existing instance.")
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
        dark_mode = self._sm.get_bool("dark_mode", True)

        apply_theme(self._app, dark_mode)

        self._tracker = TrackingManager()
        from tracker.sleepguard import SleepGuardController
        self._sleepguard = SleepGuardController()
        self._window: Optional[MainWindow] = None
        self._tray: Optional[QSystemTrayIcon] = None

        self._setup_tray()
        
        from notifications.notifier import Notifier
        if self._tray:
            Notifier.set_tray_icon(self._tray)
            
        self._tracker.start()
        self._sleepguard.start()

        from database.repository import Repository
        from protection.core import ProtectionManager
        self._protection_manager = ProtectionManager(Repository())
        self._tracker.add_active_tick_callback(self._protection_manager.tick)

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

            def _on_update_available(info: dict) -> None:
                # Respect user's "remind me later" within 24 hours
                from time import time
                last_dismiss = self._sm.get("last_update_dismissed_ts", "0")
                try:
                    last_ts = float(last_dismiss)
                except Exception:
                    last_ts = 0.0
                if time() - last_ts < 24 * 3600:
                    logger.info("Update available but user dismissed within 24h. Skipping dialog.")
                    return

                # Never interrupt active SleepGuard countdown or focus sessions
                try:
                    sg_active = getattr(self, "_sleepguard", None) and getattr(self._sleepguard, "_idle_fired", None) and self._sleepguard._idle_fired.is_set()
                except Exception:
                    sg_active = False
                try:
                    focus_active = False
                    if hasattr(self, "_window") and self._window and hasattr(self._window, "_wellbeing_page"):
                        ft = getattr(self._window._wellbeing_page, "_focus_timer", None)
                        if ft and getattr(ft, "_is_running", False):
                            focus_active = True
                except Exception:
                    focus_active = False

                if sg_active or focus_active:
                    logger.info("Deferring update dialog due to active SleepGuard or FocusSession; will retry in 30s")
                    QTimer.singleShot(30_000, lambda: self._updater.check_for_updates())
                    return

                # Show the update dialog non-blocking
                try:
                    dlg = UpdateDialog(current_version=APP_VERSION, new_version=info.get("version"), notes=info.get("notes", ""), parent=self._window or None)

                    def _on_update_now():
                        # start download, show progress
                        self._updater.download_installer(info.get("asset_url"), info.get("asset_name"), info.get("asset_id"))

                    def _on_download_progress(pct: int):
                        try:
                            dlg.set_progress(pct)
                        except Exception:
                            pass

                    def _on_download_complete(path: str):
                        # launch installer via wrapper and exit app
                        try:
                            # Ensure cleanup to close DB handles
                            self._cleanup()
                        except Exception:
                            pass
                        self._updater.launch_installer_and_exit(path)
                        # call quit after launching wrapper
                        try:
                            self._app.quit()
                        except Exception:
                            pass

                    def _on_error(msg: str):
                        try:
                            dlg.show_error(msg)
                        except Exception:
                            logger.error("Update dialog error: %s", msg)

                    dlg.update_now.connect(_on_update_now)
                    dlg.later.connect(lambda: self._sm.set("last_update_dismissed_ts", str(time())))

                    self._updater.download_progress.connect(_on_download_progress)
                    self._updater.download_complete.connect(_on_download_complete)
                    self._updater.error.connect(_on_error)

                    dlg.show()
                except Exception as exc:
                    logger.exception("Failed to show update dialog: %s", exc)

            # Connect and schedule an initial check a few seconds after startup
            self._updater.update_available.connect(_on_update_available)
            QTimer.singleShot(5_000, lambda: self._updater.check_for_updates())
        except Exception as exc:
            logger.warning("Updater initialization failed: %s", exc)

        if os.environ.get("DW_SCREENSHOT_MODE") == "1":
            def take_screenshots():
                import time
                if self._window:
                    base_path = r"C:\Users\akshi\.gemini\antigravity-ide\brain\2a916beb-1ca0-41a9-80f8-940c213c0137\scratch"
                    
                    # Dashboard
                    self._window._navigate(0)
                    self._app.processEvents()
                    time.sleep(0.2)
                    self._window.grab().save(f"{base_path}\\real_home.png")
                    
                    # Activity
                    self._window._navigate(1)
                    self._app.processEvents()
                    time.sleep(0.2)
                    self._window.grab().save(f"{base_path}\\real_activity.png")
                    
                    # Settings
                    self._window._navigate(4)
                    self._app.processEvents()
                    time.sleep(0.2)
                    self._window.grab().save(f"{base_path}\\real_settings.png")
                    
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
            if conn.waitForReadyRead(500):
                msg = conn.readAll().data().decode("utf-8")
                if msg == "show_window":
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

        show_action = QAction("Open Not Your Wellbeing", self._app)
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
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self) -> None:
        if self._window:
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()
            self._window.setWindowState(
                self._window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive
            )

    def _toggle_tracking(self) -> None:
        if self._tracker.is_running:
            self._tracker.stop()
            self._toggle_tracking_action.setText("Resume Tracking")
            if self._tray:
                self._tray.showMessage(APP_NAME, "Tracking paused.", QSystemTrayIcon.MessageIcon.Information, 2000)
        else:
            self._tracker.start()
            self._toggle_tracking_action.setText("Pause Tracking")
            if self._tray:
                self._tray.showMessage(APP_NAME, "Tracking resumed.", QSystemTrayIcon.MessageIcon.Information, 2000)

    def _on_focus_completed(self) -> None:
        if self._tray and self._sm.get_bool("notifications_enabled", True):
            self._tray.showMessage(
                "Focus Session Complete",
                "Great job! Take a well-deserved break.",
                QSystemTrayIcon.MessageIcon.Information,
                5000,
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

        if used_min >= limit_min and self._tray:
            h = int(limit_min // 60)
            m = int(limit_min % 60)
            self._tray.showMessage(
                "Daily Limit Reached",
                f"You've used {h}h {m}m of screen time today.",
                QSystemTrayIcon.MessageIcon.Warning,
                5000,
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
            QLocalServer = type(self._server)
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
