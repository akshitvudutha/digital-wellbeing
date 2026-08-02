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
from ui.pages.about import AboutPage
from ui.pages.activity import ActivityPage
from ui.pages.dashboard import DashboardPage
from ui.pages.debug import DebugPage
from ui.pages.settings import SettingsPage
from ui.pages.wellbeing import WellbeingPage
from ui.pages.history import HistoryPage
from ui.widgets.animated_stacked_widget import AnimatedStackedWidget
from ui.widgets.countdown_dialog import ShutdownCountdownDialog


class DataUpdateThread(QThread):
    data_changed = Signal()

    def __init__(self, tracker: TrackingManager, parent=None) -> None:
        super().__init__(parent)
        self._tracker = tracker

    def notify(self) -> None:
        self.data_changed.emit()


class MainWindow(QMainWindow):
    data_changed_signal = Signal()
    quit_requested = Signal()
    focus_completed = Signal()

    def __init__(self, tracker: TrackingManager, sleepguard: Optional[SleepGuardController] = None, parent=None) -> None:
        super().__init__(parent)
        self._tracker = tracker
        self._owns_sleepguard = sleepguard is None
        self._sleepguard = sleepguard or SleepGuardController(self)
        if self._owns_sleepguard:
            self._sleepguard.start()
        self._sleepguard.shutdown_warning_triggered.connect(self._show_shutdown_warning_dialog)

        self.data_changed_signal.connect(self._refresh_current_page)
        self._active_nav_btn: Optional[QPushButton] = None
        self._setup_ui()
        self._connect_tracker()
        self._setup_shortcuts()

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
        self._app_details_page = AppDetailsPage()
        
        self._dashboard_page.request_screen_time_details.connect(self._navigate_to_screen_time_details)
        self._dashboard_page.request_focus_session.connect(lambda: self._navigate(3))
        self._screen_time_details_page.request_app_details.connect(self._navigate_to_app_details)
        self._app_details_page.back_requested.connect(self._navigate_to_screen_time_details)
        
        self._activity_page = ActivityPage()
        self._history_page = HistoryPage()
        self._wellbeing_page = WellbeingPage(sleepguard=self._sleepguard)
        self._wellbeing_page.focus_completed.connect(self.focus_completed.emit)
        self._settings_page = SettingsPage(tracker=self._tracker)
        self._settings_page.settings_changed.connect(self._on_settings_changed)
        self._settings_page.theme_changed_req.connect(self._animate_theme_change)
        self._about_page = AboutPage()
        self._debug_page = DebugPage(tracker=self._tracker)

        self._stack.addWidget(self._dashboard_page)  # 0: Home
        self._stack.addWidget(self._activity_page)   # 1: Activity & Trends
        self._stack.addWidget(self._history_page)    # 2: History
        self._stack.addWidget(self._wellbeing_page)  # 3: Focus & SleepGuard
        self._stack.addWidget(self._settings_page)   # 4: Settings & Data
        self._stack.addWidget(self._about_page)      # 5: About
        self._stack.addWidget(self._debug_page)      # 6: Dev Mode (Hidden)
        self._stack.addWidget(self._screen_time_details_page) # 7: Screen Time Details
        self._stack.addWidget(self._app_details_page)         # 8: App Details

        root_layout.addWidget(self._stack, 1)
        if self._nav_buttons:
            self._nav_buttons[0].click()

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_shortcuts(self) -> None:
        self._dev_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        self._dev_shortcut.activated.connect(self._toggle_dev_mode)

        self._refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self._refresh_shortcut.activated.connect(self.refresh_all_pages)

    def _toggle_dev_mode(self) -> None:
        from core.logger import logger
        logger.info("[DEV MODE] Hidden developer shortcut Ctrl+Shift+D activated")
        self._navigate(6)

    def _show_shutdown_warning_dialog(self, countdown_s: int) -> None:
        from core.logger import logger
        from PySide6.QtCore import QTimer
        logger.info(f"[STEP 2 & 3] _show_shutdown_warning_dialog entered. Signal received with countdown_s={countdown_s}")
        dialog = ShutdownCountdownDialog(countdown_seconds=countdown_s, parent=self)
        dialog.shutdown_accepted.connect(self._sleepguard.execute_shutdown)
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
        logger.info("[STEP 8_pre] Calling dialog.start_countdown()")
        # Start the dialog timer and show non-blocking so the main event loop continues.
        dialog.start_countdown()
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.show()
        logger.info("[STEP 5_nonblocking] Shutdown dialog shown non-blocking (show())")

        # If app is minimized to tray or hidden, also notify via tray so user can open app to cancel
        try:
            from settings.manager import SettingsManager
            sm = SettingsManager()
            minimize_to_tray = sm.get_bool("minimize_to_tray", default=False)
        except Exception:
            minimize_to_tray = False

        if minimize_to_tray and (not self.isVisible() or self.isMinimized()):
            if hasattr(self, "_tray") and self._tray:
                try:
                    # Inform the user that shutdown is imminent and they can open the app to cancel
                    self._tray.showMessage(
                        "SleepGuard — Shutdown Warning",
                        f"Shutdown in {countdown_s}s — open the app to cancel.",
                        QSystemTrayIcon.MessageIcon.Warning,
                        7000,
                    )
                except Exception:
                    logger.warning("Failed to show tray message for SleepGuard countdown")

        # Log visibility shortly after showing
        QTimer.singleShot(200, lambda: logger.info(f"[STEP_POST_SHOW] is dialog visible? {dialog.isVisible()}"))

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
            self._history_page,
            self._wellbeing_page,
            self._settings_page,
            self._about_page,
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

    def _navigate_to_screen_time_details(self) -> None:
        self._screen_time_details_page.refresh()
        self._navigate(7)

    def _navigate_to_app_details(self, process_name: str) -> None:
        self._app_details_page.set_app(process_name)
        self._navigate(8)

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
        logo_layout.setContentsMargins(20, 24, 20, 16)
        logo_layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "app_logo.png"
        pix = QPixmap(str(icon_path))
        if not pix.isNull():
            icon_lbl.setPixmap(pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        brand_col = QVBoxLayout()
        brand_col.setSpacing(2)
        self._logo_lbl = QLabel("Digital Wellbeing")
        self._logo_lbl.setObjectName("sidebar_logo_label")
        self._subtitle_lbl = QLabel("VERSION 2.0")
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
        nav_layout.setContentsMargins(0, 12, 0, 12)
        nav_layout.setSpacing(4)
        scroll.setWidget(nav_container)
        layout.addWidget(scroll, 1)

        nav_items = [
            ("  🏠   Home", 0),
            ("  📊   Activity & Trends", 1),
            ("  🗓️   History", 2),
            ("  🧘   Focus & SleepGuard", 3),
            ("  ⚙️   Settings & Data", 4),
            ("  ℹ️   About", 5),
        ]

        self._nav_buttons: list[QPushButton] = []
        for label, page_idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.clicked.connect(lambda checked, idx=page_idx: self._navigate(idx))
            nav_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        nav_layout.addStretch()

        # Footer Status Capsule
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(16, 12, 16, 20)

        self._tracking_status = QLabel("● Engine Active")
        self._tracking_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_layout.addWidget(self._tracking_status)
        layout.addWidget(status_widget)

        return sidebar

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self._sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background: {tm.color('card_bg')};
                border-right: 1px solid {tm.color('border')};
            }}
            QPushButton#nav_btn {{
                background: transparent;
                color: {tm.color('text_sub')};
                border: 1px solid transparent;
                border-radius: 12px;
                padding: 12px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 600;
                margin: 0px 12px;
            }}
            QPushButton#nav_btn:hover {{
                background: {tm.color('card_hover')};
                color: {tm.color('text_main')};
                border: 1px solid {tm.color('border')};
            }}
            QPushButton#nav_btn[active="true"] {{
                background: {tm.color('info_bg')};
                color: {tm.color('info_text')};
                border: 1px solid {tm.color('info_border')};
            }}
        """)
        
        self._logo_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {tm.color('text_main')}; letter-spacing: -0.5px;")
        self._subtitle_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {tm.color('text_sub')}; letter-spacing: 0.5px;")
        self._separator.setStyleSheet(f"background: {tm.color('border')}; margin: 0 16px;")
        
        self._tracking_status.setStyleSheet(
            f"color: {tm.color('success_text')}; background-color: {tm.color('success_bg')}; "
            f"border: 1px solid {tm.color('success_border')}; border-radius: 12px; "
            "font-size: 12px; font-weight: 700; padding: 10px 12px;"
        )
        
        # Repolish active button
        if self._active_nav_btn:
            self._active_nav_btn.style().unpolish(self._active_nav_btn)
            self._active_nav_btn.style().polish(self._active_nav_btn)

    def _navigate(self, page_idx: int) -> None:
        if self._active_nav_btn:
            self._active_nav_btn.setProperty("active", False)
            self._active_nav_btn.style().unpolish(self._active_nav_btn)
            self._active_nav_btn.style().polish(self._active_nav_btn)

        if 0 <= page_idx < len(self._nav_buttons):
            btn = self._nav_buttons[page_idx]
            btn.setProperty("active", True)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            self._active_nav_btn = btn

        self._stack.setCurrentIndexAnimated(page_idx)
        self._refresh_current_page()

    def _refresh_current_page(self) -> None:
        idx = self._stack.currentIndex()
        pages = [
            self._dashboard_page,
            self._activity_page,
            self._history_page,
            self._wellbeing_page,
            self._settings_page,
            self._about_page,
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
