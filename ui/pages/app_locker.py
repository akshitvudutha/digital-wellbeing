"""
app_locker.py (UI page) — NYW App Locker configuration page.

Navigation index: 3 (new sidebar entry between Focus and Settings).

Sections:
  1. Header + subtitle
  2. Status card — ON/OFF toggle (auth required to disable)
  3. Locked apps list — icon, name, process, remove button (auth required to remove)
  4. Add Application button
  5. Authentication settings — method + duration

All actions that modify security state require authentication first.
All colors use ThemeManager semantic tokens — works in dark AND light mode.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QMessageBox, QButtonGroup, QRadioButton, QSizePolicy
)
from PySide6.QtGui import QIcon

from protection.app_locker import AppLockerManager, AuthMethod, AuthDuration, SYSTEM_SAFE
from protection.pin import PINManager
from database.repository import Repository
from core.logger import logger


class _LockedAppRow(QFrame):
    """Single row in the locked apps list."""
    remove_requested = Signal(str, str)  # process_name, display_name

    def __init__(self, process_name: str, display_name: str, exe_path: str = "", parent=None):
        super().__init__(parent)
        self._process_name = process_name
        self._display_name = display_name
        self.setObjectName("locker_app_row")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        from utils.icon_provider import AppIconProvider
        from PySide6.QtCore import QSize
        icon_provider = AppIconProvider()
        icon = icon_provider.get_icon(self._process_name)
        
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(32, 32)
        if not icon.isNull():
            icon_lbl.setPixmap(icon.pixmap(QSize(32, 32)))
        else:
            from ui.icons import get_icon
            from ui.theme import ThemeManager
            icon_lbl.setPixmap(get_icon("lock", color=ThemeManager.instance().color('text_sub'), size=24).pixmap(32, 32))
            icon_lbl.setObjectName("locker_row_icon")
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(self.font())
        elided_name = metrics.elidedText(self._display_name, Qt.TextElideMode.ElideRight, 120)
        elided_proc = metrics.elidedText(self._process_name, Qt.TextElideMode.ElideRight, 120)
        
        name_lbl = QLabel(elided_name)
        name_lbl.setObjectName("locker_row_name")
        proc_lbl = QLabel(elided_proc)
        proc_lbl.setObjectName("locker_row_proc")
        
        name_lbl.setToolTip(self._display_name)
        proc_lbl.setToolTip(self._process_name)
        
        text_col.addWidget(name_lbl)
        text_col.addWidget(proc_lbl)
        layout.addLayout(text_col, 1)

        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("locker_remove_btn")
        remove_btn.setFixedHeight(32)
        remove_btn.clicked.connect(
            lambda: self.remove_requested.emit(self._process_name, self._display_name)
        )
        layout.addWidget(remove_btn)


class AppLockerPage(QWidget):
    """Dedicated App Locker configuration page."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo = Repository()
        self._pin_manager = PINManager(self._repo)
        self._alm = AppLockerManager.instance(self._repo)
        self._alm.state_changed.connect(self._refresh_locked_apps)

        self._setup_ui()

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    # ─── UI construction ─────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(0)

        # Page title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("App Locker")
        title.setObjectName("page_title")
        subtitle = QLabel("Protect distracting applications with Windows Hello or your NYW PIN.")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        root.addLayout(title_box)
        root.addSpacing(24)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner.setObjectName("content_area")
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(0, 0, 4, 0)
        self._inner_layout.setSpacing(20)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # 1. Status card
        self._status_card = self._make_status_card()
        self._inner_layout.addWidget(self._status_card)

        # 2. Locked apps section
        self._apps_section = self._make_apps_section()
        self._inner_layout.addWidget(self._apps_section)

        # 3. Auth settings section
        self._auth_section = self._make_auth_section()
        self._inner_layout.addWidget(self._auth_section)

        self._inner_layout.addStretch()

    def _make_section_card(self, header_text: str) -> QFrame:
        """Helper: create a themed card frame with a header label."""
        card = QFrame()
        card.setObjectName("dense_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)
        hdr = QLabel(header_text)
        hdr.setObjectName("section_header")
        layout.addWidget(hdr)
        return card

    # ── Status card ───────────────────────────────────────────────────────────

    def _make_status_card(self) -> QFrame:
        card = self._make_section_card("App Locker")

        row = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(2)
        lbl = QLabel("App Locker Protection")
        lbl.setObjectName("setting_label")
        desc = QLabel("When enabled, selected applications require authentication before use.")
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        col.addWidget(lbl)
        col.addWidget(desc)
        row.addLayout(col, 1)

        self._toggle_btn = QPushButton()
        self._toggle_btn.setObjectName("locker_toggle_btn")
        self._toggle_btn.setFixedSize(52, 28)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(self._alm.is_enabled)
        self._toggle_btn.clicked.connect(self._on_toggle_clicked)
        self._update_toggle_label()
        row.addWidget(self._toggle_btn)

        card.layout().addLayout(row)

        # Windows Hello availability badge
        from protection.windows_hello import WindowsHelloAuth, HelloAvailability
        avail = WindowsHelloAuth().check_availability()
        if avail == HelloAvailability.AVAILABLE:
            badge = QLabel("Windows Hello available on this device")
            badge.setObjectName("locker_hello_badge_ok")
        elif avail == HelloAvailability.NOT_CONFIGURED:
            badge = QLabel("Windows Hello not configured — NYW PIN fallback will be used")
            badge.setObjectName("locker_hello_badge_warn")
        else:
            badge = QLabel("Windows Hello unavailable — NYW PIN will be used for authentication")
            badge.setObjectName("locker_hello_badge_info")
        badge.setWordWrap(True)
        card.layout().addWidget(badge)

        return card

    # ── Locked apps section ───────────────────────────────────────────────────

    def _make_apps_section(self) -> QFrame:
        card = self._make_section_card("Locked Applications")

        # App rows container (FlowLayout for chips)
        from ui.widgets.flow_layout import FlowLayout
        self._apps_container = FlowLayout()
        self._apps_container.setSpacing(8)
        card.layout().addLayout(self._apps_container)

        # Empty state label
        self._empty_lbl = QLabel("No applications locked yet.\nClick \"+ Add Application\" to get started.")
        self._empty_lbl.setObjectName("locker_empty_label")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        card.layout().addWidget(self._empty_lbl)

        # Add button
        add_btn = QPushButton("  +  Add Application")
        add_btn.setObjectName("locker_add_btn")
        add_btn.setMinimumHeight(40)
        add_btn.clicked.connect(self._on_add_app)
        card.layout().addWidget(add_btn)

        # Populate with existing locked apps
        self._refresh_locked_apps()

        return card

    # ── Auth settings section ─────────────────────────────────────────────────

    def _make_auth_section(self) -> QFrame:
        card = self._make_section_card("Authentication Settings")

        # Two-column layout for Auth Method and Auth Duration
        columns = QHBoxLayout()
        columns.setSpacing(32)
        
        # Left Column: Auth Method
        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        
        method_lbl = QLabel("Authentication Method")
        method_lbl.setObjectName("setting_label")
        left_col.addWidget(method_lbl)

        self._method_bg = QButtonGroup(self)
        methods = [
            (AuthMethod.WINDOWS_HELLO,  "hello",     "Windows Hello (Face / Fingerprint / PIN)"),
            (AuthMethod.NYW_PIN,        "pin",       "NYW PIN only"),
            (AuthMethod.HELLO_THEN_PIN, "hello_pin", "Hello with PIN fallback (recommended)"),
        ]
        for method, val, label_text in methods:
            rb = QRadioButton(label_text)
            rb.setObjectName("locker_radio")
            rb.setChecked(self._alm.auth_method == method)
            rb.toggled.connect(lambda checked, m=method: self._on_method_changed(checked, m))
            self._method_bg.addButton(rb)
            left_col.addWidget(rb)
            
        left_col.addStretch()
        columns.addLayout(left_col, 1)

        # Right Column: Auth Duration
        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        
        duration_lbl = QLabel("Authentication Duration")
        duration_lbl.setObjectName("setting_label")
        right_col.addWidget(duration_lbl)

        self._duration_bg = QButtonGroup(self)
        durations = [
            (AuthDuration.EVERY_LAUNCH, "every_launch", "Every launch (most secure)"),
            (AuthDuration.FIVE_MIN,     "5_min",        "5 minutes"),
            (AuthDuration.FIFTEEN_MIN,  "15_min",       "15 minutes (recommended)"),
            (AuthDuration.UNTIL_CLOSE,  "until_close",  "Until application closes"),
        ]
        for duration, val, label_text in durations:
            rb = QRadioButton(label_text)
            rb.setObjectName("locker_radio")
            rb.setChecked(self._alm.auth_duration == duration)
            rb.toggled.connect(lambda checked, d=duration: self._on_duration_changed(checked, d))
            self._duration_bg.addButton(rb)
            right_col.addWidget(rb)
            
        right_col.addStretch()
        columns.addLayout(right_col, 1)

        card.layout().addLayout(columns)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setObjectName("locker_sep")
        card.layout().addWidget(sep2)

        # Clear all button
        clear_row = QHBoxLayout()
        clear_row.addStretch()
        clear_btn = QPushButton("Clear All Locked Apps")
        clear_btn.setObjectName("locker_danger_btn")
        clear_btn.setMinimumHeight(38)
        clear_btn.clicked.connect(self._on_clear_all)
        clear_row.addWidget(clear_btn)
        card.layout().addLayout(clear_row)

        return card

    # ─── Refresh locked apps list ─────────────────────────────────────────────

    def _refresh_locked_apps(self) -> None:
        """Rebuild the locked apps rows from DB."""
        # Clear existing rows
        while self._apps_container.count():
            item = self._apps_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        apps = self._alm.get_locked_apps()
        self._empty_lbl.setVisible(not apps)

        for app in apps:
            row = _LockedAppRow(
                app["process_name"],
                app["display_name"],
                app.get("exe_path", ""),
            )
            row.remove_requested.connect(self._on_remove_app)
            # Constrain max width for chip appearance
            row.setMaximumWidth(280)
            row.setMinimumWidth(220)
            self._apps_container.addWidget(row)
            self._apply_row_theme(row)

    # ─── Event handlers ───────────────────────────────────────────────────────

    def _on_toggle_clicked(self) -> None:
        """Toggle App Locker on/off. Disabling requires authentication."""
        if not self._toggle_btn.isChecked():
            # Trying to DISABLE — require auth
            if not self._do_auth("Disable App Locker"):
                # Auth failed or canceled — revert toggle
                self._toggle_btn.setChecked(True)
                self._update_toggle_label()
                return
            self._alm.disable()
        else:
            self._alm.enable()
        self._update_toggle_label()

    def _on_add_app(self) -> None:
        from ui.widgets.process_picker import ProcessPickerDialog
        dialog = ProcessPickerDialog(self)
        if dialog.exec():
            ok = self._alm.add_locked_app(
                dialog.selected_process_name,
                dialog.selected_display_name,
                dialog.selected_exe_path,
            )
            if not ok:
                self._show_error(
                    "Cannot add this application",
                    f"{dialog.selected_process_name} is a system-protected process and cannot be locked."
                )

    def _on_remove_app(self, process_name: str, display_name: str) -> None:
        """Remove a locked app — requires authentication."""
        if not self._do_auth(f"Remove {display_name} from App Locker"):
            return
        self._alm.remove_locked_app(process_name)

    def _on_method_changed(self, checked: bool, method: AuthMethod) -> None:
        if not checked:
            return
        if not self._do_auth("Change authentication method"):
            # Revert radio button to current setting
            self._revert_method_radio()
            return
        self._alm.set_auth_method(method)

    def _on_duration_changed(self, checked: bool, duration: AuthDuration) -> None:
        if not checked:
            return
        if not self._do_auth("Change authentication duration"):
            self._revert_duration_radio()
            return
        self._alm.set_auth_duration(duration)

    def _on_clear_all(self) -> None:
        if not self._do_auth("Clear all locked applications"):
            return
        self._alm.clear_all_locked_apps()

    # ─── Auth helper ──────────────────────────────────────────────────────────

    def _do_auth(self, action_description: str) -> bool:
        """Show authentication dialog. Returns True only if authentication succeeded."""
        from ui.widgets.auth_dialog import AppLockerAuthDialog
        dialog = AppLockerAuthDialog(
            process_name="settings",
            display_name=action_description,
            pin_manager=self._pin_manager,
            auth_method=self._alm.auth_method.value,
            parent=self,
        )
        return dialog.exec() == QDialog.DialogCode.Accepted

    # ─── UI helpers ───────────────────────────────────────────────────────────

    def _update_toggle_label(self) -> None:
        is_on = self._toggle_btn.isChecked()
        self._toggle_btn.setText("ON" if is_on else "OFF")

    def _revert_method_radio(self) -> None:
        current = self._alm.auth_method
        for btn in self._method_bg.buttons():
            text = btn.text()
            if current == AuthMethod.WINDOWS_HELLO and "Hello" in text and "fallback" not in text.lower():
                btn.setChecked(True)
                break
            elif current == AuthMethod.NYW_PIN and "NYW PIN only" in text:
                btn.setChecked(True)
                break
            elif current == AuthMethod.HELLO_THEN_PIN and "fallback" in text.lower():
                btn.setChecked(True)
                break

    def _revert_duration_radio(self) -> None:
        current = self._alm.auth_duration
        label_map = {
            AuthDuration.EVERY_LAUNCH: "Every launch",
            AuthDuration.FIVE_MIN:     "5 minutes",
            AuthDuration.FIFTEEN_MIN:  "15 minutes",
            AuthDuration.UNTIL_CLOSE:  "Until application",
        }
        target = label_map.get(current, "")
        for btn in self._duration_bg.buttons():
            if target and target in btn.text():
                btn.setChecked(True)
                break

    def _show_error(self, title: str, msg: str) -> None:
        mb = QMessageBox(self)
        mb.setWindowTitle(title)
        mb.setText(msg)
        mb.setIcon(QMessageBox.Icon.Warning)
        mb.exec()

    # ─── Theme ───────────────────────────────────────────────────────────────

    def _apply_theme(self, is_dark: bool = True) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        self.setStyleSheet(f"""
            QLabel#page_title {{
                font-size: 22px;
                font-weight: 800;
                color: {tm.color('text_main')};
            }}
            QLabel#page_subtitle {{
                font-size: 13px;
                color: {tm.color('text_sub')};
            }}
            QFrame#v2_card {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 14px;
            }}
            QLabel#section_header {{
                font-size: 15px;
                font-weight: 800;
                color: {tm.color('text_main')};
            }}
            QLabel#setting_label {{
                font-size: 13px;
                font-weight: 700;
                color: {tm.color('text_main')};
            }}
            QLabel#setting_desc {{
                font-size: 12px;
                color: {tm.color('text_sub')};
            }}
            QPushButton#locker_toggle_btn {{
                background-color: {tm.color('success_text') if self._alm.is_enabled else tm.color('border')};
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 10px;
                font-weight: 800;
            }}
            QPushButton#locker_add_btn {{
                background-color: {tm.color('accent')};
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 10px;
            }}
            QPushButton#locker_add_btn:hover {{
                background-color: {tm.color('accent_hover')};
            }}
            QPushButton#locker_danger_btn {{
                background-color: {tm.color('danger_bg')};
                color: {tm.color('danger_text')};
                border: 1px solid {tm.color('danger_border')};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 8px;
            }}
            QPushButton#locker_danger_btn:hover {{
                background-color: {tm.color('danger_text')};
                color: white;
            }}
            QFrame#locker_app_row {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
            }}
            QLabel#locker_row_icon {{
                font-size: 18px;
            }}
            QLabel#locker_row_name {{
                font-size: 13px;
                font-weight: 700;
                color: {tm.color('text_main')};
            }}
            QLabel#locker_row_proc {{
                font-size: 11px;
                color: {tm.color('text_sub')};
            }}
            QPushButton#locker_remove_btn {{
                background-color: {tm.color('danger_bg')};
                color: {tm.color('danger_text')};
                border: 1px solid {tm.color('danger_border')};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#locker_remove_btn:hover {{
                background-color: {tm.color('danger_text')};
                color: white;
            }}
            QLabel#locker_empty_label {{
                font-size: 13px;
                color: {tm.color('text_sub')};
                padding: 16px;
            }}
            QLabel#locker_hello_badge_ok {{
                font-size: 12px;
                color: {tm.color('success_text')};
                background: {tm.color('success_bg')};
                border: 1px solid {tm.color('success_border')};
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QLabel#locker_hello_badge_warn {{
                font-size: 12px;
                color: {tm.color('warning_text')};
                background: {tm.color('warning_bg')};
                border: 1px solid {tm.color('warning_border')};
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QLabel#locker_hello_badge_info {{
                font-size: 12px;
                color: {tm.color('info_text')};
                background: {tm.color('info_bg')};
                border: 1px solid {tm.color('info_border')};
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QRadioButton#locker_radio {{
                font-size: 13px;
                color: {tm.color('text_main')};
                spacing: 8px;
            }}
            QFrame#locker_sep {{
                background: {tm.color('border')};
                max-height: 1px;
            }}
        """)

        # Re-apply per-row themes
        for i in range(self._apps_container.count()):
            w = self._apps_container.itemAt(i).widget()
            if w:
                self._apply_row_theme(w)

    def _apply_row_theme(self, row: QFrame) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        row.setStyleSheet(f"""
            QFrame#locker_app_row {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
            }}
            QLabel#locker_row_name {{
                font-size: 13px;
                font-weight: 700;
                color: {tm.color('text_main')};
            }}
            QLabel#locker_row_proc {{
                font-size: 11px;
                color: {tm.color('text_sub')};
            }}
            QPushButton#locker_remove_btn {{
                background-color: {tm.color('danger_bg')};
                color: {tm.color('danger_text')};
                border: 1px solid {tm.color('danger_border')};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#locker_remove_btn:hover {{
                background-color: {tm.color('danger_text')};
                color: white;
            }}
        """)

    def on_data_changed(self) -> None:
        """Called by MainWindow refresh cycle."""
        self._refresh_locked_apps()
        self._apply_theme(True)


# Fix missing import in _do_auth
from PySide6.QtWidgets import QDialog  # noqa: E402
