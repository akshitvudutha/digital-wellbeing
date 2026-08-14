"""
main_window.py — V2 Main Application Shell for Digital Wellbeing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QMainWindow, QSystemTrayIcon
)

from core.constants import APP_NAME, APP_VERSION
from tracker.manager import TrackingManager
from tracker.sleepguard import SleepGuardController
from ui.pages.activity import ActivityPage
from ui.pages.dashboard import DashboardPage
from ui.widgets.website_overlay import WebsiteLimitOverlayDialog
from ui.widgets.limit_dialog import LimitReachedDialog, PinOverrideDialog
from ui.pages.debug import DebugPage
from ui.pages.settings import SettingsPage
from ui.pages.wellbeing import WellbeingPage
from ui.widgets.animated_stacked_widget import AnimatedStackedWidget
from ui.widgets.countdown_dialog import ShutdownCountdownDialog


class DataUpdateThread(QThread):
    data_changed = Signal()

    def __init__(self, tracker: TrackingManager, parent=None) -> None:
        super().__init__(parent)
        self._tracker = tracker

    def notify(self) -> None:
        self.data_changed.emit()


from core.updater import check_for_update, UpdateInfo

class UpdateCheckWorker(QThread):
    finished_check = Signal(object)  # UpdateInfo | None

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        info = check_for_update()
        self.finished_check.emit(info)


class MainWindow(QMainWindow):
    data_changed_signal = Signal()
    quit_requested = Signal()
    focus_completed = Signal()

    def __init__(self, tracker: TrackingManager, sleepguard: Optional[SleepGuardController] = None, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._tracker = tracker
        self._protection_manager = protection_manager
        self._owns_sleepguard = sleepguard is None
        self._sleepguard = sleepguard or SleepGuardController(self)
        if self._owns_sleepguard:
            self._sleepguard.start()
        self._sleepguard.shutdown_warning_triggered.connect(self._show_shutdown_warning_dialog)
        
        if self._protection_manager:
            self._protection_manager.notifications.show_limit_dialog.connect(self._show_limit_dialog)
            self._protection_manager.notifications.show_website_limit_dialog.connect(self._show_website_limit_dialog)

        self.data_changed_signal.connect(self._refresh_current_page)
        self._active_nav_btn: Optional[QPushButton] = None
        self._navigation_history: list[int] = []
        self._active_limit_dialogs = set()
        self._active_website_dialogs = set()
        self._setup_ui()
        self._connect_tracker()
        self._setup_shortcuts()
        self._check_for_updates_auto()

    def _setup_ui(self) -> None:
        from core.constants import APP_NAME, APP_VERSION
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(1024, 720)
        self.resize(1280, 800)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        from ui.theme import ThemeManager, apply_mica
        apply_mica(int(self.winId()), ThemeManager.instance().is_dark)
        ThemeManager.instance().theme_changed.connect(lambda is_dark: apply_mica(int(self.winId()), is_dark))

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Left Sidebar Navigation Rail
        self._sidebar = self._build_sidebar()
        root_layout.addWidget(self._sidebar)

        self._stack = AnimatedStackedWidget()
        self._stack.setObjectName("content_area")

        self._dashboard_page = DashboardPage(on_global_refresh=self.refresh_all_pages, navigate_callback=self._navigate)
        
        from ui.pages.screen_time_details import ScreenTimeDetailsPage
        self._screen_time_details_page = ScreenTimeDetailsPage()
        
        from ui.pages.app_details import AppDetailsPage
        self._app_details_page = AppDetailsPage(protection_manager=self._protection_manager)
        
        self._dashboard_page.request_screen_time_details.connect(self._navigate_to_screen_time_details)
        self._dashboard_page.request_app_details.connect(self._navigate_to_app_details)
        self._dashboard_page.request_focus_session.connect(lambda: self._navigate(2))
        
        self._screen_time_details_page.request_app_details.connect(self._navigate_to_app_details)
        self._screen_time_details_page.back_requested.connect(self._navigate_back)
        
        self._app_details_page.back_requested.connect(self._navigate_back)
        
        self._activity_page = ActivityPage(protection_manager=self._protection_manager)
        self._activity_page.request_historical_details.connect(self._navigate_to_screen_time_details)
        self._wellbeing_page = WellbeingPage(sleepguard=self._sleepguard)
        self._wellbeing_page.focus_completed.connect(self.focus_completed.emit)
        self._settings_page = SettingsPage(tracker=self._tracker, protection_manager=self._protection_manager)
        self._settings_page.settings_changed.connect(self._on_settings_changed)
        self._settings_page.theme_changed_req.connect(self._animate_theme_change)
        self._settings_page.manual_update_requested.connect(self._check_for_updates_manual)
        self._debug_page = DebugPage(tracker=self._tracker)

        self._stack.addWidget(self._dashboard_page)  # 0: Home
        self._stack.addWidget(self._activity_page)   # 1: Activity & Trends
        self._stack.addWidget(self._wellbeing_page)  # 2: Focus & SleepGuard
        self._stack.addWidget(self._settings_page)   # 3: Settings & Data
        self._stack.addWidget(self._debug_page)      # 4: Dev Mode (Hidden)
        self._stack.addWidget(self._screen_time_details_page) # 5: Screen Time Details
        self._stack.addWidget(self._app_details_page)         # 6: App Details

        root_layout.addWidget(self._stack, 1)
        if self._nav_buttons:
            self._nav_buttons[0].click()

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _check_for_updates_auto(self) -> None:
        from settings.manager import SettingsManager
        from datetime import datetime, timedelta
        sm = SettingsManager()
        if not sm.auto_update_enabled:
            return

        last_check_str = sm.last_update_check
        if last_check_str:
            try:
                last_check = datetime.fromisoformat(last_check_str)
                if datetime.now() - last_check < timedelta(hours=24):
                    return
            except ValueError:
                pass

        self._run_update_check(is_manual=False)

    def _check_for_updates_manual(self) -> None:
        self._run_update_check(is_manual=True)

    def _run_update_check(self, is_manual: bool) -> None:
        if hasattr(self, '_update_worker') and self._update_worker.isRunning():
            return

        self._update_worker = UpdateCheckWorker(self)
        def on_finished(info: UpdateInfo | None):
            from settings.manager import SettingsManager
            from datetime import datetime
            from PySide6.QtWidgets import QMessageBox
            
            sm = SettingsManager()
            sm.last_update_check = datetime.now().isoformat()
            
            if info:
                if sm.notify_updates or is_manual:
                    self._show_update_dialog(info)
            elif is_manual:
                QMessageBox.information(
                    self, "No Updates", "You are on the latest stable version."
                )
                
        self._update_worker.finished_check.connect(on_finished)
        self._update_worker.start()

    def _show_update_dialog(self, info: UpdateInfo) -> None:
        from ui.widgets.update_dialog import UpdateDialog
        from core.constants import APP_VERSION
        dialog = UpdateDialog(APP_VERSION, info, self)
        
        def on_update_success():
            # Gracefully close the app so installer can overwrite files
            self.close()
            
        dialog.update_successful.connect(on_update_success)
        dialog.show()

    def _setup_shortcuts(self) -> None:
        self._dev_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        self._dev_shortcut.activated.connect(self._toggle_dev_mode)

        self._refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self._refresh_shortcut.activated.connect(self.refresh_all_pages)
        
        self._backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self)
        self._backspace_shortcut.activated.connect(self._navigate_back)
        
        self._alt_left_shortcut = QShortcut(QKeySequence("Alt+Left"), self)
        self._alt_left_shortcut.activated.connect(self._navigate_back)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.BackButton or event.button() == Qt.MouseButton.XButton1:
            self._navigate_back()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _toggle_dev_mode(self) -> None:
        from core.logger import logger
        logger.info("[DEV MODE] Hidden developer shortcut Ctrl+Shift+D activated")
        self._navigate(4)

    def _show_shutdown_warning_dialog(self, countdown_s: int, action: str = "lock") -> None:
        from core.logger import logger
        from PySide6.QtCore import QTimer
        logger.info(
            "[SLEEPGUARD_UI] _show_shutdown_warning_dialog entered. countdown_s=%d, action='%s'",
            countdown_s, action,
        )
        # Instantiate with parent=None to ensure it is a true top-level window 
        # and doesn't inherit hidden state from MainWindow when minimized to tray.
        dialog = ShutdownCountdownDialog(countdown_seconds=countdown_s, action=action, parent=None)
        dialog.shutdown_accepted.connect(self._sleepguard.execute_power_action)
        # Wrap the dialog.cancel connection to avoid recursive re-entry between UI and controller
        def _on_dialog_cancel():
            if getattr(self, "_handling_shutdown_cancel", False):
                return
            try:
                self._handling_shutdown_cancel = True
                self._sleepguard.cancel_warning()
            finally:
                self._handling_shutdown_cancel = False

        dialog.shutdown_cancelled.connect(_on_dialog_cancel)

        # Also connect sleepguard-level cancel notifications back to the dialog so programmatic cancels stop the UI
        try:
            self._sleepguard.programmatic_shutdown_cancelled.connect(dialog._on_cancel)
        except Exception:
            # defensive: if signal/slot not available, continue without UI cancel sync
            logger.warning("Failed to connect sleepguard.programmatic_shutdown_cancelled back to dialog")
        logger.info("[SLEEPGUARD_UI] Starting countdown and showing dialog...")
        # Start the dialog timer and show non-blocking so the main event loop continues.
        dialog.start_countdown()
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        logger.info("[SLEEPGUARD_UI] Dialog shown non-blocking (show + raise + activateWindow)")

        # If app is minimized to tray or hidden, also notify via tray so user can open app to cancel
        try:
            from settings.manager import SettingsManager
            sm = SettingsManager()
            minimize_to_tray = sm.get_bool("minimize_to_tray", default=False)
        except Exception:
            minimize_to_tray = False

        action_label = action.title() if action else "Action"
        if minimize_to_tray and (not self.isVisible() or self.isMinimized()):
            if hasattr(self, "_tray") and self._tray:
                try:
                    # Inform the user that a power action is imminent and they can open the app to cancel
                    self._tray.showMessage(
                        f"SleepGuard — {action_label} Warning",
                        f"{action_label} in {countdown_s}s — open the app to cancel.",
                        QSystemTrayIcon.MessageIcon.Warning,
                        7000,
                    )
                except Exception:
                    logger.warning("Failed to show tray message for SleepGuard countdown")

        # Log visibility shortly after showing
        QTimer.singleShot(200, lambda: logger.info(f"[SLEEPGUARD_UI] Post-show: dialog visible={dialog.isVisible()}"))

    def _animate_theme_change(self, new_theme: str) -> None:
        from ui.theme import ThemeManager
        from PySide6.QtWidgets import QLabel, QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation

        tm = ThemeManager.instance()
        if tm.resolve_dark_mode(new_theme) == tm.is_dark:
            return  # No change

        # Screenshot crossfade
        pixmap = self.grab()
        self._overlay = QLabel(self)
        self._overlay.setPixmap(pixmap)
        self._overlay.setGeometry(self.rect())
        self._overlay.show()
        self._overlay.raise_()

        # Instantly update theme underneath
        tm.set_theme(new_theme)
        self.refresh_all_pages()

        # Fade out old image
        effect = QGraphicsOpacityEffect(self._overlay)
        self._overlay.setGraphicsEffect(effect)
        self._anim = QPropertyAnimation(effect, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._overlay.deleteLater)
        self._anim.start()

    def _on_settings_changed(self) -> None:
        self.refresh_all_pages()

    def refresh_all_pages(self) -> None:
        from core.logger import logger
        logger.info("[REFRESH] Executing V2 global refresh for all pages...")
        pages = [
            self._dashboard_page,
            self._activity_page,
            self._wellbeing_page,
            self._settings_page,
            self._debug_page,
            self._screen_time_details_page,
            self._app_details_page,
        ]
        for page in pages:
            if hasattr(page, "on_data_changed"):
                try:
                    page.on_data_changed()
                except Exception as exc:
                    logger.warning("Error refreshing %s: %s", type(page).__name__, exc)
        logger.info("[REFRESH] Global refresh complete.")

    def _navigate_to_screen_time_details(self, target_date=None) -> None:
        from datetime import date
        if isinstance(target_date, date):
            # Need to clear history so Back button goes back to Activity Trends
            self._screen_time_details_page.refresh(target_date)
            self._navigate(5)
        else:
            self._screen_time_details_page.refresh()
            self._navigate(5)

    def _navigate_to_app_details(self, process_name: str) -> None:
        self._app_details_page.set_app(process_name)
        self._navigate(6)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Brand Header
        logo_widget = QWidget()
        logo_layout = QHBoxLayout(logo_widget)
        logo_layout.setContentsMargins(20, 32, 20, 24)
        logo_layout.setSpacing(14)

        icon_lbl = QLabel()
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "app_logo.png"
        pix = QPixmap(str(icon_path))
        if not pix.isNull():
            icon_lbl.setPixmap(pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        brand_col = QVBoxLayout()
        brand_col.setSpacing(2)
        self._logo_lbl = QLabel("Digital Wellbeing")
        self._logo_lbl.setObjectName("sidebar_logo_label")
        from core.constants import APP_VERSION
        self._subtitle_lbl = QLabel(f"VERSION {APP_VERSION}")
        self._subtitle_lbl.setObjectName("sidebar_subtitle_label")
        brand_col.addWidget(self._logo_lbl)
        brand_col.addWidget(self._subtitle_lbl)

        logo_layout.addWidget(icon_lbl)
        logo_layout.addLayout(brand_col)
        layout.addWidget(logo_widget)

        self._separator = QFrame()
        self._separator.setFrameShape(QFrame.Shape.HLine)
        self._separator.setMaximumHeight(1)
        layout.addWidget(self._separator)

        # Navigation Rail Items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 16, 0, 16)
        nav_layout.setSpacing(6)
        scroll.setWidget(nav_container)
        layout.addWidget(scroll, 1)

        self._home_btn = QPushButton("  🏠   Home")
        self._activity_btn = QPushButton("  📈   Activity Trends")
        self._focus_btn = QPushButton("  🎯   Focus")
        
        # Dev Mode button is intentionally removed from the production UI.
        # It remains accessible via Ctrl+Shift+D shortcut.
        self._debug_btn = QPushButton("  🐛   Dev Mode")
        self._debug_btn.setVisible(False)

        self._nav_buttons = [
            self._home_btn,
            self._activity_btn,
            self._focus_btn,
            self._debug_btn
        ]

        for i, btn in enumerate(self._nav_buttons):
            btn.setObjectName("nav_btn")
            btn.clicked.connect(lambda checked, idx=i: self._navigate(idx))
            nav_layout.addWidget(btn)

        nav_layout.addStretch()

        # Footer Area (Pinned to bottom)
        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 16)
        footer_layout.setSpacing(12)
        
        self._settings_btn = QPushButton("  ⚙️   Settings")
        self._settings_btn.setObjectName("nav_btn")
        self._settings_btn.clicked.connect(lambda: self._navigate(3))
        footer_layout.addWidget(self._settings_btn)
        
        # We append to _nav_buttons list but NOT the nav_layout so it can be managed for highlighting
        self._nav_buttons.insert(3, self._settings_btn)
        

        
        layout.addWidget(footer_widget)

        return sidebar

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        # OLED Black appearance with very subtle Mica bleed
        sidebar_bg = "rgba(0, 0, 0, 0.4)" if tm.is_dark else "rgba(255, 255, 255, 0.4)"
        hover_bg = "rgba(255, 255, 255, 0.05)" if tm.is_dark else "rgba(0, 0, 0, 0.04)"
        active_bg = "rgba(255, 255, 255, 0.08)" if tm.is_dark else "rgba(0, 0, 0, 0.08)"
        active_border = "rgba(255, 255, 255, 0.12)" if tm.is_dark else "rgba(0, 0, 0, 0.15)"
        
        self._sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background: {sidebar_bg};
                border-right: 1px solid {tm.color('border')};
            }}
            QPushButton#nav_btn {{
                background: transparent;
                color: {tm.color('text_sub')};
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 600;
                margin: 2px 16px;
            }}
            QPushButton#nav_btn:hover {{
                background: {hover_bg};
                color: {tm.color('text_main')};
                border: 1px solid transparent;
            }}
            QPushButton#nav_btn[active="true"] {{
                background: {active_bg};
                color: {tm.color('text_main')};
                border: 1px solid {active_border};
            }}
        """)
        
        self._logo_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {tm.color('text_main')}; letter-spacing: -0.2px;")
        self._subtitle_lbl.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {tm.color('text_sub')}; letter-spacing: 0.5px;")
        self._separator.setStyleSheet(f"background: {tm.color('border')}; margin: 0 16px;")
        
        
        # Repolish active button
        if self._active_nav_btn:
            self._active_nav_btn.style().unpolish(self._active_nav_btn)
            self._active_nav_btn.style().polish(self._active_nav_btn)

    def _navigate(self, page_idx: int) -> None:
        curr_idx = self._stack.currentIndex()
        if curr_idx == page_idx:
            return

        if page_idx < 5:
            # Main sidebar navigation, clear history
            self._navigation_history.clear()
        else:
            # Drilling down into a detail page, push current index
            self._navigation_history.append(curr_idx)

        if self._active_nav_btn:
            self._active_nav_btn.setProperty("active", False)
            self._active_nav_btn.style().unpolish(self._active_nav_btn)
            self._active_nav_btn.style().polish(self._active_nav_btn)

        # Highlight sidebar if applicable
        if 0 <= page_idx < len(self._nav_buttons):
            btn = self._nav_buttons[page_idx]
            btn.setProperty("active", True)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            self._active_nav_btn = btn

        self._stack.setCurrentIndexAnimated(page_idx)
        self._refresh_current_page()

    def _navigate_back(self) -> None:
        if self._navigation_history:
            prev_idx = self._navigation_history.pop()
            
            if self._active_nav_btn:
                self._active_nav_btn.setProperty("active", False)
                self._active_nav_btn.style().unpolish(self._active_nav_btn)
                self._active_nav_btn.style().polish(self._active_nav_btn)

            if 0 <= prev_idx < len(self._nav_buttons):
                btn = self._nav_buttons[prev_idx]
                btn.setProperty("active", True)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                self._active_nav_btn = btn
                
            self._stack.setCurrentIndexAnimated(prev_idx)

    def _show_website_limit_dialog(self, process_name: str, domain: str, limit_seconds: int) -> None:
        dialog_id = f"{process_name}_{domain}"
        if dialog_id in self._active_website_dialogs:
            return
            
        self._active_website_dialogs.add(dialog_id)
        
        dialog = WebsiteLimitOverlayDialog(process_name, domain, limit_seconds, self)
        
        def on_override_requested(p, d):
            pin_dialog = PinOverrideDialog(p, self._protection_manager.pin, self)
            def on_granted(pname, mins):
                self._protection_manager.add_website_override(d, mins)
                dialog.accept()
            pin_dialog.override_granted.connect(on_granted)
            pin_dialog.exec()
                
        dialog.override_requested.connect(on_override_requested)
        dialog.exec()
        self._active_website_dialogs.discard(dialog_id)

    def _show_limit_dialog(self, process_name: str, limit_seconds: int) -> None:
        if process_name in self._active_limit_dialogs:
            return
            
        self._active_limit_dialogs.add(process_name)
        
        if self.isHidden():
            self.show()
            self.raise_()
            self.activateWindow()
            
        dlg = LimitReachedDialog(process_name, limit_seconds, self)
        
        def on_close_app(pname: str):
            self._protection_manager.force_close(pname)
            
        def on_override(pname: str):
            pin_dlg = PinOverrideDialog(pname, self._protection_manager.pin, self)
            pin_dlg.override_granted.connect(self._protection_manager.add_override)
            pin_dlg.exec()
            
        dlg.close_app_requested.connect(on_close_app)
        dlg.override_requested.connect(on_override)
        dlg.exec()
        
        # When dialog is closed (for any reason), remove it from active set
        self._active_limit_dialogs.discard(process_name)

    def _refresh_current_page(self) -> None:
        idx = self._stack.currentIndex()
        pages = [
            self._dashboard_page,
            self._activity_page,
            self._wellbeing_page,
            self._settings_page,
            self._debug_page,
        ]
        if 0 <= idx < len(pages):
            page = pages[idx]
            if hasattr(page, "on_data_changed"):
                page.on_data_changed()

    def _connect_tracker(self) -> None:
        self._data_thread = DataUpdateThread(self._tracker, self)
        self._data_thread.data_changed.connect(self._refresh_current_page)

    def closeEvent(self, event) -> None:
        from settings.manager import SettingsManager
        sm = SettingsManager()
        if sm.get_bool("minimize_to_tray", default=False):
            event.ignore()
            self.hide()
        else:
            if self._owns_sleepguard and hasattr(self, "_sleepguard") and self._sleepguard:
                self._sleepguard.stop()
            event.accept()
            self.quit_requested.emit()
