"""
settings.py — Settings Page for Digital Wellbeing Platform v2.0.0.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
    QListWidget, QListWidgetItem, QStackedWidget, QSizePolicy
)

from ui.widgets.fluent import FluentButton

from database.repository import Repository
from settings.manager import SettingsManager
from utils.autostart import disable_autostart, enable_autostart, is_autostart_enabled
from utils.csv_exporter import CSVExporter
from ui.theme import ThemeManager


class SettingsPage(QWidget):
    settings_changed = Signal()
    theme_changed_req = Signal(str)
    manual_update_requested = Signal()

    def __init__(self, tracker=None, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._sm = SettingsManager()
        self._tracker = tracker
        self._protection_manager = protection_manager
        
        # Track settings state changes
        self._pending_changes = False
        
        self._setup_ui()
        self._load_values()
        
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Settings")
        title.setObjectName("page_title")
        subtitle = QLabel("Manage application preferences, tracking behavior, and data.")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Split layout for Sidebar + Stack
        split_layout = QHBoxLayout()
        split_layout.setSpacing(24)
        
        # Left Sidebar (QListWidget)
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("settings_sidebar")
        self._sidebar.setFixedWidth(240)
        self._sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        split_layout.addWidget(self._sidebar)

        # Right Stacked Widget
        self._stack = QStackedWidget()
        split_layout.addWidget(self._stack, 1)
        
        layout.addLayout(split_layout, 1)
        
        # Build Pages
        self._build_pages()
        
        # Bottom Save button row
        save_row = QHBoxLayout()
        save_row.addStretch()
        
        self._save_btn = FluentButton("Save Changes", primary=True)
        self._save_btn.clicked.connect(self._save)
        
        save_row.addWidget(self._save_btn)
        layout.addLayout(save_row)

    def _build_pages(self):
        categories = []
        
        if self._protection_manager:
            from ui.widgets.protection_section import ProtectionSection
            prot_page = QWidget()
            prot_layout = QVBoxLayout(prot_page)
            prot_layout.setContentsMargins(0, 0, 0, 0)
            prot_layout.addWidget(ProtectionSection(self._protection_manager))
            prot_layout.addStretch()
            categories.append(("Protection & PIN", "Security settings and App Locker PIN"))
            self._stack.addWidget(self._wrap_scroll(prot_page))

        # 1. Appearance & General
        app_page = QWidget()
        app_layout = QVBoxLayout(app_page)
        app_layout.setContentsMargins(0, 0, 0, 0)
        
        app_layout.addWidget(self._create_section_title("Appearance"))
        
        theme_row, self._theme_combo = self._create_combo_row(
            "Application Theme", "Select visual theme mode",
            [("System Default", "system"), ("Dark Theme", "dark"), ("Light Theme", "light")]
        )
        self._theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        app_layout.addWidget(theme_row)
        
        app_layout.addSpacing(16)
        app_layout.addWidget(self._create_section_title("Startup"))
        
        self._autostart_check, row1 = self._create_toggle_row("Start with Windows Login", "Automatically launch NYW when Windows starts")
        app_layout.addWidget(row1)
        
        self._minimize_tray_check, row2 = self._create_toggle_row("Minimize to Tray", "Keep tracking in system tray when closed")
        app_layout.addWidget(row2)

        app_layout.addStretch()
        categories.append(("General", "Theme, startup, and appearance"))
        self._stack.addWidget(self._wrap_scroll(app_page))

        # 2. Tracking & Limits
        track_page = QWidget()
        track_layout = QVBoxLayout(track_page)
        track_layout.setContentsMargins(0, 0, 0, 0)
        
        track_layout.addWidget(self._create_section_title("Tracking Behavior"))
        
        idle_row, self._idle_spin = self._create_spin_row("Activity Idle Threshold", "Minutes of inactivity before marking status as idle", 1, 60, " min")
        track_layout.addWidget(idle_row)
        
        self._debug_tracking_check, row3 = self._create_toggle_row("Enable Debug Tracking", "Log structured events asynchronously to log files")
        track_layout.addWidget(row3)
        
        track_layout.addSpacing(16)
        track_layout.addWidget(self._create_section_title("Daily Limits"))
        
        self._notif_check, row4 = self._create_toggle_row("System Notifications", "Receive system tray notifications for milestones")
        track_layout.addWidget(row4)
        
        limit_row, self._limit_spin = self._create_spin_row("Screen Time Limit Warning", "Notify when total screen time exceeds this limit", 30, 1440, " min", step=30)
        track_layout.addWidget(limit_row)
        
        track_layout.addStretch()
        categories.append(("Tracking", "Idle detection and tracking limits"))
        self._stack.addWidget(self._wrap_scroll(track_page))

        # 3. SleepGuard
        sg_page = QWidget()
        sg_layout = QVBoxLayout(sg_page)
        sg_layout.setContentsMargins(0, 0, 0, 0)
        
        sg_layout.addWidget(self._create_section_title("SleepGuard Protection"))
        
        self._sg_enable_check, r1 = self._create_toggle_row("Enable SleepGuard", "Monitor idle time and trigger PC action during bedtime")
        sg_layout.addWidget(r1)
        
        sg_a_row, self._sg_action_combo = self._create_combo_row("Action when timer ends", "Power action to execute", [("Lock", "lock"), ("Sleep", "sleep"), ("Hibernate", "hibernate"), ("Shut down", "shutdown")])
        sg_layout.addWidget(sg_a_row)
        
        sg_t_row, self._sg_timeout_spin = self._create_spin_row("Idle timeout", "Minutes of inactivity before warning", 5, 120, " min", step=5)
        sg_layout.addWidget(sg_t_row)
        
        sg_c_row, self._sg_countdown_spin = self._create_spin_row("Countdown before action", "Seconds to wait during the warning dialog", 10, 300, " sec", step=10)
        sg_layout.addWidget(sg_c_row)
        
        sg_layout.addSpacing(16)
        sg_layout.addWidget(self._create_section_title("Media Playback"))
        
        sg_m_row, self._sg_mode_combo = self._create_combo_row("Media behavior", "When active media is playing", [
            ("Smart - Trigger after media threshold", "smart"),
            ("Always Allow - Never trigger", "media"),
            ("Strict - Ignore media", "strict")
        ])
        self._sg_mode_combo.currentIndexChanged.connect(self._on_sg_mode_changed)
        sg_layout.addWidget(sg_m_row)
        
        sg_mt_row, self._sg_media_timeout_combo = self._create_combo_row("Media idle timeout", "Threshold before triggering action", [
            ("Never", -1), ("5 min", 5), ("10 min", 10), ("15 min", 15), ("30 min", 30), ("60 min", 60)
        ])
        sg_layout.addWidget(sg_mt_row)
        
        sg_layout.addSpacing(16)
        sg_layout.addWidget(self._create_section_title("Developer"))
        sg_test_row, self._sg_test_timeout_combo = self._create_combo_row("Quick Test Mode", "Override timeout for rapid testing", [
            ("Off (Production)", 0), ("10 seconds", 10), ("20 seconds", 20), ("30 seconds", 30), ("1 minute", 60)
        ])
        sg_layout.addWidget(sg_test_row)
        
        sg_layout.addStretch()
        categories.append(("SleepGuard", "Distraction blocking parameters"))
        self._stack.addWidget(self._wrap_scroll(sg_page))
        
        # 4. Data Management
        data_page = QWidget()
        data_layout = QVBoxLayout(data_page)
        data_layout.setContentsMargins(0, 0, 0, 0)
        
        data_layout.addWidget(self._create_section_title("Data Management"))
        
        ret_row, self._retention_combo = self._create_combo_row("History Retention", "Automatically delete old raw tracking data", [
            ("30 Days", 30), ("90 Days", 90), ("1 Year", 365), ("Unlimited", -1)
        ])
        data_layout.addWidget(ret_row)
        
        data_layout.addSpacing(16)
        data_layout.addWidget(self._create_section_title("Export & Backup"))
        
        from ui.widgets.fluent import FluentButton
        export_row, self._export_range_combo = self._create_combo_row("Export Data (CSV)", "Export session records", [
            ("Today", 0), ("Past 7 Days", 7), ("Past 30 Days", 30), ("This Month", 99)
        ])
        btn_exp = FluentButton("Export CSV", primary=False)
        export_row.layout().addWidget(btn_exp)
        data_layout.addWidget(export_row)
        
        db_row = QFrame()
        db_row.setObjectName("settings_card")
        db_l = QHBoxLayout(db_row)
        db_c = QVBoxLayout()
        db_lbl = QLabel("Backup & Restore Database")
        db_lbl.setObjectName("setting_label")
        db_desc = QLabel("Save or restore your tracking database")
        db_desc.setObjectName("setting_desc")
        db_desc.setWordWrap(True)
        db_c.addWidget(db_lbl)
        db_c.addWidget(db_desc)
        btn_bak = FluentButton("Backup", primary=False)
        btn_bak.clicked.connect(self._on_backup_db)
        btn_res = FluentButton("Restore", primary=False)
        btn_res.clicked.connect(self._on_restore_db)
        db_l.addWidget(btn_bak)
        db_l.addWidget(btn_res)
        data_layout.addWidget(db_row)
        
        clr_row = QFrame()
        clr_row.setObjectName("settings_card")
        clr_l = QHBoxLayout(clr_row)
        clr_c = QVBoxLayout()
        clr_lbl = QLabel("Clear Tracking History")
        clr_lbl.setObjectName("setting_label")
        clr_desc = QLabel("Permanently delete all recorded sessions")
        clr_desc.setObjectName("setting_desc")
        clr_desc.setWordWrap(True)
        clr_c.addWidget(clr_lbl)
        self._clear_btn = FluentButton("Clear History", primary=False)
        self._clear_btn.clicked.connect(self._on_clear_history)
        clr_l.addWidget(self._clear_btn)
        data_layout.addWidget(clr_row)
        
        self._data_status_lbl = QLabel("")
        self._data_status_lbl.setObjectName("data_status")
        data_layout.addWidget(self._data_status_lbl)
        
        data_layout.addStretch()
        categories.append(("Data Management", "Export, backup, and history limits"))
        self._stack.addWidget(self._wrap_scroll(data_page))
        
        # 5. Updates & About
        upd_page = QWidget()
        upd_layout = QVBoxLayout(upd_page)
        upd_layout.setContentsMargins(0, 0, 0, 0)
        
        upd_layout.addWidget(self._create_section_title("Updates"))
        
        self._auto_update_check, r_upd1 = self._create_toggle_row("Automatic Updates", "Check for new versions every 24 hours")
        upd_layout.addWidget(r_upd1)
        
        self._notify_update_check, r_upd2 = self._create_toggle_row("Update Notifications", "Show a notification when ready")
        upd_layout.addWidget(r_upd2)
        
        from core.constants import APP_VERSION, APP_NAME
        chk_row = QFrame()
        chk_row.setObjectName("settings_card")
        chk_l = QHBoxLayout(chk_row)
        chk_c = QVBoxLayout()
        chk_lbl = QLabel(f"Current version: {APP_VERSION}")
        chk_lbl.setObjectName("setting_label")
        chk_c.addWidget(chk_lbl)
        chk_l.addLayout(chk_c, 1)
        chk_btn = FluentButton("Check for Updates", primary=False)
        chk_btn.clicked.connect(lambda: self.manual_update_requested.emit())
        chk_l.addWidget(chk_btn)
        upd_layout.addWidget(chk_row)
        
        upd_layout.addSpacing(16)
        upd_layout.addWidget(self._create_section_title("About"))
        
        about_lbl = QLabel(f"{APP_NAME} v{APP_VERSION}\nPremium Screen Time Tracker for Windows")
        about_lbl.setObjectName("setting_desc")
        about_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        upd_layout.addWidget(about_lbl)
        
        upd_layout.addStretch()
        categories.append(("Updates & About", "Version info and updates"))
        self._stack.addWidget(self._wrap_scroll(upd_page))

        # Populate sidebar
        for title, desc in categories:
            item = QListWidgetItem(title)
            # You could add subtitle using a custom widget, but text is fine
            item.setToolTip(desc)
            self._sidebar.addItem(item)
            
        self._sidebar.setCurrentRow(0)

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(widget)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        return scroll

    def _create_section_title(self, title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setObjectName("section_header")
        return lbl

    def _create_toggle_row(self, title: str, description: str):
        row = QFrame()
        row.setObjectName("settings_card")
        layout = QHBoxLayout(row)
        col = QVBoxLayout()
        col.setSpacing(2)
        lbl = QLabel(title)
        lbl.setObjectName("setting_label")
        desc = QLabel(description)
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        col.addWidget(lbl)
        col.addWidget(desc)
        layout.addLayout(col, 1)
        from ui.widgets.fluent import ToggleSwitch
        check = ToggleSwitch()
        layout.addWidget(check)
        return check, row

    def _create_combo_row(self, title: str, description: str, items: list):
        row = QFrame()
        row.setObjectName("settings_card")
        layout = QHBoxLayout(row)
        col = QVBoxLayout()
        col.setSpacing(2)
        lbl = QLabel(title)
        lbl.setObjectName("setting_label")
        desc = QLabel(description)
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        col.addWidget(lbl)
        col.addWidget(desc)
        layout.addLayout(col, 1)
        combo = QComboBox()
        for text, data in items:
            combo.addItem(text, data)
        combo.setMinimumWidth(180)
        combo.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addWidget(combo)
        return row, combo

    def _create_spin_row(self, title: str, description: str, min_val: int, max_val: int, suffix: str, step: int = 1):
        row = QFrame()
        row.setObjectName("settings_card")
        layout = QHBoxLayout(row)
        col = QVBoxLayout()
        col.setSpacing(2)
        lbl = QLabel(title)
        lbl.setObjectName("setting_label")
        desc = QLabel(description)
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        col.addWidget(lbl)
        col.addWidget(desc)
        layout.addLayout(col, 1)
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        spin.setMinimumWidth(120)
        spin.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addWidget(spin)
        return row, spin

    def _on_sidebar_changed(self, index: int):
        self._stack.setCurrentIndex(index)

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 14px; color: {tm.color('text_sub')}; }}
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 0.5px; margin-top: 10px; margin-bottom: 4px; }}
            QLabel#setting_label {{ color: {tm.color('text_main')}; font-size: 14px; font-weight: 600; }}
            QLabel#setting_desc {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            
            QFrame#settings_card {{ 
                background: {tm.color('surface_elevated')}; 
                border-radius: 12px; 
                border: 1px solid {tm.color('border')}; 
                padding: 16px;
            }}
            
            QListWidget#settings_sidebar {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#settings_sidebar::item {{
                background: transparent;
                color: {tm.color('text_sub')};
                padding: 10px 16px;
                border-radius: 8px;
                margin-bottom: 4px;
                font-weight: 600;
                font-size: 14px;
            }}
            QListWidget#settings_sidebar::item:hover {{
                background: {tm.color('surface_hover')};
                color: {tm.color('text_main')};
            }}
            QListWidget#settings_sidebar::item:selected {{
                background: {tm.color('surface_elevated')};
                color: {tm.color('accent')};
                border-left: 3px solid {tm.color('accent')};
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
            }}
            
            QComboBox, QSpinBox {{
                background-color: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 6px;
                padding: 6px 12px;
                color: {tm.color('text_main')};
                font-size: 13px;
                font-weight: 500;
            }}
            QComboBox:hover, QSpinBox:hover {{
                border: 1px solid {tm.color('accent')};
            }}
            QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {{
                border: none;
                background: transparent;
            }}
            QComboBox QAbstractItemView {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                selection-background-color: {tm.color('accent')};
                selection-color: white;
                border-radius: 6px;
                outline: none;
            }}
            
            QPushButton#danger_btn {{
                background-color: {tm.color('danger_bg')};
                color: {tm.color('danger_text')};
                border: 1px solid {tm.color('danger_border')};
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
            }}
            QPushButton#danger_btn:hover {{
                background-color: {tm.color('danger_text')};
                color: white;
            }}
        """)
        
        if "✗" in self._data_status_lbl.text():
            self._data_status_lbl.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 600; font-size: 12px;")
        else:
            self._data_status_lbl.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 600; font-size: 12px;")

    def _on_theme_combo_changed(self) -> None:
        theme_val = self._theme_combo.currentData()
        if theme_val:
            self._sm.theme = theme_val
            self.theme_changed_req.emit(theme_val)

    def _on_sg_mode_changed(self) -> None:
        is_smart = self._sg_mode_combo.currentData() == "smart"
        self._sg_media_timeout_combo.setEnabled(is_smart)

    def _load_values(self) -> None:
        curr_theme = self._sm.theme
        idx = self._theme_combo.findData(curr_theme)
        if idx >= 0:
            self._theme_combo.blockSignals(True)
            self._theme_combo.setCurrentIndex(idx)
            self._theme_combo.blockSignals(False)
            
        self._idle_spin.setValue(self._sm.get_int("idle_threshold_s", 300) // 60)
        self._autostart_check.setChecked(is_autostart_enabled())
        self._minimize_tray_check.setChecked(self._sm.get_bool("minimize_to_tray", False))
        self._debug_tracking_check.setChecked(self._sm.debug_tracking)
        self._notif_check.setChecked(self._sm.get_bool("notifications_enabled", True))
        self._limit_spin.setValue(self._sm.get_int("daily_limit_minutes", 480))

        self._sg_enable_check.setChecked(self._sm.sleepguard_enabled)
        curr_action = self._sm.sleepguard_action
        idx_act = self._sg_action_combo.findData(curr_action)
        if idx_act >= 0:
            self._sg_action_combo.setCurrentIndex(idx_act)
        
        curr_mode = self._sm.shutdown_mode
        idx = self._sg_mode_combo.findData(curr_mode)
        if idx >= 0:
            self._sg_mode_combo.setCurrentIndex(idx)
            
        self._sg_timeout_spin.setValue(self._sm.idle_timeout_minutes)
        self._sg_countdown_spin.setValue(self._sm.countdown_seconds)
        
        test_timeout = self._sm.testing_idle_timeout_s
        idx_test = self._sg_test_timeout_combo.findData(test_timeout)
        if idx_test >= 0:
            self._sg_test_timeout_combo.setCurrentIndex(idx_test)
        
        media_timeout = self._sm.media_idle_timeout_minutes
        idx2 = self._sg_media_timeout_combo.findData(media_timeout)
        if idx2 >= 0:
            self._sg_media_timeout_combo.setCurrentIndex(idx2)
            
        retention = self._sm.get_int("history_retention_days", 30)
        idx3 = self._retention_combo.findData(retention)
        if idx3 >= 0:
            self._retention_combo.setCurrentIndex(idx3)

        self._auto_update_check.setChecked(self._sm.auto_update_enabled)
        self._notify_update_check.setChecked(self._sm.notify_updates)

        self._on_sg_mode_changed()

    def _on_export_csv(self) -> None:
        days = self._export_range_combo.currentData()
        end = date.today()
        if days == 0:
            start = end
        elif days == 99:
            start = end.replace(day=1)
        else:
            start = end - timedelta(days=days - 1)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report CSV", str(Path.home() / "Documents" / f"digital_wellbeing_report_{start}_{end}.csv"), "CSV Files (*.csv)",
        )

        if file_path:
            tm = ThemeManager.instance()
            try:
                exporter = CSVExporter()
                dest = exporter.export_sessions(start, end, Path(file_path))
                self._data_status_lbl.setText(f"✓ Report exported to: {dest.name}")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 600; font-size: 12px;")
            except Exception as exc:
                self._data_status_lbl.setText(f"✗ Export failed: {exc}")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 600; font-size: 12px;")

    def _on_backup_db(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", str(Path.home() / "Documents" / f"digital_wellbeing_backup_{date.today()}.db"), "Database Files (*.db)",
        )
        if file_path:
            tm = ThemeManager.instance()
            try:
                repo = Repository()
                dest = repo.backup_database(Path(file_path))
                self._data_status_lbl.setText(f"✓ Database backed up to: {dest.name}")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 600; font-size: 12px;")
            except Exception as exc:
                self._data_status_lbl.setText(f"✗ Backup failed: {exc}")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 600; font-size: 12px;")

    def _on_restore_db(self) -> None:
        reply = QMessageBox.question(
            self, "Confirm Database Restore", "Restoring database will overwrite your current tracking data. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Database Backup", str(Path.home() / "Documents"), "Database Files (*.db)",
            )
            if file_path:
                tm = ThemeManager.instance()
                try:
                    repo = Repository()
                    repo.restore_database(Path(file_path))
                    self._data_status_lbl.setText(f"✓ Database restored successfully from: {Path(file_path).name}")
                    self._data_status_lbl.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 600; font-size: 12px;")
                except Exception as exc:
                    self._data_status_lbl.setText(f"✗ Restore failed: {exc}")
                    self._data_status_lbl.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 600; font-size: 12px;")

    def _on_clear_history(self) -> None:
        reply = QMessageBox.warning(
            self, "Confirm Clear History", "Are you sure you want to permanently delete all tracking history? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            tm = ThemeManager.instance()
            try:
                repo = Repository()
                count = repo.clear_all_sessions()
                self._data_status_lbl.setText(f"✓ Cleared {count} sessions from history.")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 600; font-size: 12px;")
            except Exception as exc:
                self._data_status_lbl.setText(f"✗ Clear history failed: {exc}")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 600; font-size: 12px;")

    def _save(self) -> None:
        theme_val = self._theme_combo.currentData()
        if theme_val:
            self._sm.theme = theme_val
        self._sm.set_int("idle_threshold_s", self._idle_spin.value() * 60)
        self._sm.set_bool("notifications_enabled", self._notif_check.isChecked())
        self._sm.set_bool("minimize_to_tray", self._minimize_tray_check.isChecked())
        self._sm.debug_tracking = self._debug_tracking_check.isChecked()
        self._sm.set_int("daily_limit_minutes", self._limit_spin.value())

        self._sm.sleepguard_enabled = self._sg_enable_check.isChecked()
        act_val = self._sg_action_combo.currentData()
        if act_val:
            self._sm.sleepguard_action = act_val
        mode_val = self._sg_mode_combo.currentData()
        if mode_val:
            self._sm.shutdown_mode = mode_val
        self._sm.idle_timeout_minutes = self._sg_timeout_spin.value()
        self._sm.countdown_seconds = self._sg_countdown_spin.value()
        
        test_val = self._sg_test_timeout_combo.currentData()
        if test_val is not None:
            self._sm.testing_idle_timeout_s = test_val
        
        media_timeout_val = self._sg_media_timeout_combo.currentData()
        if media_timeout_val is not None:
            self._sm.media_idle_timeout_minutes = media_timeout_val
            
        self._sm.auto_update_enabled = self._auto_update_check.isChecked()
        self._sm.notify_updates = self._notify_update_check.isChecked()

        ret_val = self._retention_combo.currentData()
        if ret_val is not None:
            self._sm.set_int("history_retention_days", ret_val)
            if ret_val > 0:
                from analytics.engine import AnalyticsEngine
                try:
                    AnalyticsEngine().run_cleanup(ret_val)
                except Exception as e:
                    print(f"Cleanup error: {e}")

        if self._autostart_check.isChecked():
            try:
                enable_autostart()
            except Exception as exc:
                QMessageBox.warning(self, "Autostart Failed", str(exc))
        else:
            try:
                disable_autostart()
            except Exception as exc:
                QMessageBox.warning(self, "Autostart Failed", str(exc))

        if self._tracker:
            self._tracker.reload_settings()

        self.settings_changed.emit()
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
