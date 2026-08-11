"""
settings.py — Settings Page for Digital Wellbeing Platform v2.0.0.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from database.repository import Repository
from settings.manager import SettingsManager
from utils.autostart import disable_autostart, enable_autostart, is_autostart_enabled
from utils.csv_exporter import CSVExporter


class SettingsPage(QWidget):
    settings_changed = Signal()
    theme_changed_req = Signal(str)

    def __init__(self, tracker=None, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._sm = SettingsManager()
        self._tracker = tracker
        self._protection_manager = protection_manager
        self._setup_ui()
        self._load_values()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Settings")
        title.setObjectName("page_title")
        subtitle = QLabel("System preferences, screen time goals, SleepGuard rules, and data management")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        layout.addLayout(title_box)
        layout.addSpacing(24)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner.setObjectName("content_area")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(20)
        self._scroll.setWidget(inner)
        layout.addWidget(self._scroll, 1)

        if self._protection_manager:
            from ui.widgets.protection_section import ProtectionSection
            
            # Privacy & Security Section
            protection_section = self._make_section("🔒 Privacy & Security")
            prot_l = protection_section.layout()
            self._protection_widget = ProtectionSection(self._protection_manager)
            prot_l.addWidget(self._protection_widget)
            inner_layout.addWidget(protection_section)

        # 1. Appearance Section
        appearance_section = self._make_section("🎨 Appearance & Theme")
        app_l = appearance_section.layout()

        theme_row = QHBoxLayout()
        theme_col = QVBoxLayout()
        theme_lbl = QLabel("Application Theme")
        theme_lbl.setObjectName("setting_label")
        theme_desc = QLabel("Select visual theme mode (System, Dark, or Light)")
        theme_desc.setObjectName("setting_desc")
        theme_col.addWidget(theme_lbl)
        theme_col.addWidget(theme_desc)
        theme_row.addLayout(theme_col, 1)

        self._theme_combo = QComboBox()
        self._theme_combo.addItem("System Default", "system")
        self._theme_combo.addItem("Dark Theme", "dark")
        self._theme_combo.addItem("Light Theme", "light")
        self._theme_combo.setFixedWidth(160)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        theme_row.addWidget(self._theme_combo)
        app_l.addLayout(theme_row)

        inner_layout.addWidget(appearance_section)

        # 2. Tracking Section
        tracking_section = self._make_section("Tracking & Startup Preferences")
        t_l = tracking_section.layout()

        idle_row = QHBoxLayout()
        idle_col = QVBoxLayout()
        idle_lbl = QLabel("Activity Idle Threshold")
        idle_lbl.setObjectName("setting_label")
        idle_desc = QLabel("Minutes of inactivity before marking status as idle")
        idle_desc.setObjectName("setting_desc")
        idle_col.addWidget(idle_lbl)
        idle_col.addWidget(idle_desc)
        idle_row.addLayout(idle_col, 1)

        self._idle_spin = QSpinBox()
        self._idle_spin.setRange(1, 60)
        self._idle_spin.setSuffix(" min")
        self._idle_spin.setFixedWidth(110)
        idle_row.addWidget(self._idle_spin)
        t_l.addLayout(idle_row)

        t_l.addWidget(self._separator())

        self._autostart_check = self._toggle_row(
            t_l,
            "Start with Windows Login",
            "Automatically launch Digital Wellbeing when Windows starts",
        )

        t_l.addWidget(self._separator())

        self._minimize_tray_check = self._toggle_row(
            t_l,
            "Minimize to Tray on Window Close",
            "Keep tracking in system tray when clicking the window X button",
        )

        t_l.addWidget(self._separator())

        self._debug_tracking_check = self._toggle_row(
            t_l,
            "Enable Tracking Diagnostics (Debug Mode)",
            "Log structured events asynchronously to tracking_debug.log and enable real-time tracking inspector",
        )
        inner_layout.addWidget(tracking_section)

        # 2. SleepGuard Rules Section
        sg_section = self._make_section("🌙 SleepGuard Protection Rules")
        sg_l = sg_section.layout()

        self._sg_enable_check = self._toggle_row(
            sg_l,
            "Enable SleepGuard Protection",
            "Monitor idle time and trigger automatic PC shutdown during bedtime",
        )

        sg_l.addWidget(self._separator())

        sg_action_row = QHBoxLayout()
        sg_action_col = QVBoxLayout()
        sg_act_lbl = QLabel("Action when timer ends")
        sg_act_lbl.setObjectName("setting_label")
        sg_act_desc = QLabel("Power action to execute when SleepGuard bedtime countdown completes")
        sg_act_desc.setObjectName("setting_desc")
        sg_action_col.addWidget(sg_act_lbl)
        sg_action_col.addWidget(sg_act_desc)
        sg_action_row.addLayout(sg_action_col, 1)

        self._sg_action_combo = QComboBox()
        self._sg_action_combo.addItem("Lock", "lock")
        self._sg_action_combo.addItem("Sleep", "sleep")
        self._sg_action_combo.addItem("Hibernate", "hibernate")
        self._sg_action_combo.addItem("Shut down", "shutdown")
        self._sg_action_combo.addItem("Cancel", "cancel")
        self._sg_action_combo.setFixedWidth(160)
        sg_action_row.addWidget(self._sg_action_combo)
        sg_l.addLayout(sg_action_row)

        sg_l.addWidget(self._separator())

        sg_mode_row = QHBoxLayout()
        sg_mode_col = QVBoxLayout()
        sg_m_lbl = QLabel("Shutdown Evaluation Mode")
        sg_m_lbl.setObjectName("setting_label")
        sg_m_desc = QLabel("Behavior when active media (YouTube/Netflix/Spotify) is playing")
        sg_m_desc.setObjectName("setting_desc")
        sg_mode_col.addWidget(sg_m_lbl)
        sg_mode_col.addWidget(sg_m_desc)
        sg_mode_row.addLayout(sg_mode_col, 1)

        self._sg_mode_combo = QComboBox()
        self._sg_mode_combo.addItem("Smart (Intelligent timeout during media playback)", "smart")
        self._sg_mode_combo.addItem("Media (Always ignore idle while media is playing)", "media")
        self._sg_mode_combo.addItem("Strict (Ignore media playback completely)", "strict")
        self._sg_mode_combo.currentIndexChanged.connect(self._on_sg_mode_changed)
        sg_mode_row.addWidget(self._sg_mode_combo)
        sg_l.addLayout(sg_mode_row)

        sg_l.addWidget(self._separator())

        sg_m_row = QHBoxLayout()
        sg_m_col = QVBoxLayout()
        sg_m_lbl = QLabel("Idle During Media After")
        sg_m_lbl.setObjectName("setting_label")
        sg_m_desc = QLabel("Inactivity threshold before triggering idle/shutdown while media is playing")
        sg_m_desc.setObjectName("setting_desc")
        sg_m_col.addWidget(sg_m_lbl)
        sg_m_col.addWidget(sg_m_desc)
        sg_m_row.addLayout(sg_m_col, 1)

        self._sg_media_timeout_combo = QComboBox()
        self._sg_media_timeout_combo.addItem("Never", -1)
        self._sg_media_timeout_combo.addItem("5 min", 5)
        self._sg_media_timeout_combo.addItem("10 min", 10)
        self._sg_media_timeout_combo.addItem("15 min", 15)
        self._sg_media_timeout_combo.addItem("30 min", 30)
        self._sg_media_timeout_combo.addItem("60 min", 60)
        self._sg_media_timeout_combo.setFixedWidth(160)
        sg_m_row.addWidget(self._sg_media_timeout_combo)
        sg_l.addLayout(sg_m_row)

        sg_l.addWidget(self._separator())

        sg_t_row = QHBoxLayout()
        sg_t_col = QVBoxLayout()
        sg_t_lbl = QLabel("SleepGuard Idle Timeout")
        sg_t_lbl.setObjectName("setting_label")
        sg_t_desc = QLabel("Minutes of inactivity before triggering shutdown countdown")
        sg_t_desc.setObjectName("setting_desc")
        sg_t_col.addWidget(sg_t_lbl)
        sg_t_col.addWidget(sg_t_desc)
        sg_t_row.addLayout(sg_t_col, 1)

        self._sg_timeout_spin = QSpinBox()
        self._sg_timeout_spin.setRange(5, 120)
        self._sg_timeout_spin.setSingleStep(5)
        self._sg_timeout_spin.setSuffix(" min")
        self._sg_timeout_spin.setFixedWidth(110)
        sg_t_row.addWidget(self._sg_timeout_spin)
        sg_l.addLayout(sg_t_row)

        inner_layout.addWidget(sg_section)

        # 3. Notifications Section
        notifications_section = self._make_section("Notifications & Daily Limits")
        notif_layout = notifications_section.layout()

        self._notif_check = self._toggle_row(
            notif_layout,
            "Enable System Notifications",
            "Receive system tray notifications for screen time milestones and summaries",
        )

        notif_layout.addWidget(self._separator())

        limit_row = QHBoxLayout()
        limit_label_col = QVBoxLayout()
        limit_lbl = QLabel("Daily Screen Time Limit Warning")
        limit_lbl.setObjectName("setting_label")
        limit_desc = QLabel("Notify when total screen time exceeds this daily limit")
        limit_desc.setObjectName("setting_desc")
        limit_label_col.addWidget(limit_lbl)
        limit_label_col.addWidget(limit_desc)
        limit_row.addLayout(limit_label_col, 1)

        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(30, 1440)
        self._limit_spin.setSingleStep(30)
        self._limit_spin.setSuffix(" min")
        self._limit_spin.setFixedWidth(110)
        limit_row.addWidget(self._limit_spin)
        notif_layout.addLayout(limit_row)
        inner_layout.addWidget(notifications_section)

        # 4. Data Management Section
        data_section = self._make_section("🗄️ Data Management")
        data_layout = data_section.layout()

        # History Retention row
        retention_row = QHBoxLayout()
        retention_col = QVBoxLayout()
        retention_lbl = QLabel("History Retention")
        retention_lbl.setObjectName("setting_label")
        retention_desc = QLabel("Automatically delete raw tracking data older than this duration (daily summaries are kept forever)")
        retention_desc.setObjectName("setting_desc")
        retention_col.addWidget(retention_lbl)
        retention_col.addWidget(retention_desc)
        retention_row.addLayout(retention_col, 1)

        self._retention_combo = QComboBox()
        self._retention_combo.addItem("30 Days", 30)
        self._retention_combo.addItem("90 Days", 90)
        self._retention_combo.addItem("1 Year", 365)
        self._retention_combo.addItem("Unlimited", -1)
        self._retention_combo.setFixedWidth(160)
        retention_row.addWidget(self._retention_combo)
        data_layout.addLayout(retention_row)

        data_layout.addWidget(self._separator())

        # CSV Export row
        export_row = QHBoxLayout()
        export_col = QVBoxLayout()
        export_lbl = QLabel("Export Data (CSV)")
        export_lbl.setObjectName("setting_label")
        export_desc = QLabel("Export session records and digital wellbeing stats to a CSV file")
        export_desc.setObjectName("setting_desc")
        export_col.addWidget(export_lbl)
        export_col.addWidget(export_desc)
        export_row.addLayout(export_col, 1)

        self._export_range_combo = QComboBox()
        self._export_range_combo.addItem("Today", 0)
        self._export_range_combo.addItem("Past 7 Days", 7)
        self._export_range_combo.addItem("Past 30 Days", 30)
        self._export_range_combo.addItem("This Month", 99)
        export_row.addWidget(self._export_range_combo)

        from ui.widgets.fluent import FluentButton
        export_btn = FluentButton("📄 Export CSV", primary=False)
        export_btn.setFixedWidth(130)
        export_btn.clicked.connect(self._on_export_csv)
        export_row.addWidget(export_btn)
        data_layout.addLayout(export_row)

        data_layout.addWidget(self._separator())

        # Backup & Restore DB row
        db_row = QHBoxLayout()
        db_col = QVBoxLayout()
        db_lbl = QLabel("Backup & Restore Database")
        db_lbl.setObjectName("setting_label")
        db_desc = QLabel("Save a backup copy of your database or restore from a previous backup")
        db_desc.setObjectName("setting_desc")
        db_col.addWidget(db_lbl)
        db_col.addWidget(db_desc)
        db_row.addLayout(db_col, 1)

        backup_btn = FluentButton("💾 Backup", primary=False)
        backup_btn.setFixedWidth(100)
        backup_btn.clicked.connect(self._on_backup_db)
        db_row.addWidget(backup_btn)

        restore_btn = FluentButton("📂 Restore", primary=False)
        restore_btn.setFixedWidth(100)
        restore_btn.clicked.connect(self._on_restore_db)
        db_row.addWidget(restore_btn)
        data_layout.addLayout(db_row)

        data_layout.addWidget(self._separator())

        # Clear History row
        clear_row = QHBoxLayout()
        clear_col = QVBoxLayout()
        clear_lbl = QLabel("Clear Tracking History")
        clear_lbl.setObjectName("setting_label")
        clear_desc = QLabel("Permanently delete all recorded application sessions")
        clear_desc.setObjectName("setting_desc")
        clear_col.addWidget(clear_lbl)
        clear_col.addWidget(clear_desc)
        clear_row.addLayout(clear_col, 1)

        self._clear_btn = FluentButton("🗑️ Clear History", primary=False)
        self._clear_btn.setObjectName("danger_btn")
        self._clear_btn.setFixedWidth(140)
        self._clear_btn.clicked.connect(self._on_clear_history)
        clear_row.addWidget(self._clear_btn)
        data_layout.addLayout(clear_row)

        self._data_status_lbl = QLabel("")
        self._data_status_lbl.setObjectName("data_status_success")
        data_layout.addWidget(self._data_status_lbl)

        inner_layout.addWidget(data_section)

        # 5. About Section
        about_section = self._make_section("ℹ️ About")
        about_layout = about_section.layout()
        
        from core.constants import APP_NAME, APP_VERSION
        app_lbl = QLabel(f"{APP_NAME} v{APP_VERSION}")
        app_lbl.setObjectName("setting_label")
        app_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        dev_lbl = QLabel("Premium Digital Wellbeing & Screen Time Tracker for Windows")
        dev_lbl.setObjectName("setting_desc")
        dev_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        about_layout.addWidget(app_lbl)
        about_layout.addWidget(dev_lbl)
        inner_layout.addWidget(about_section)

        save_row = QHBoxLayout()
        save_row.addStretch()
        save_btn = FluentButton("💾 Save Settings", primary=True)
        save_btn.setMinimumWidth(160)
        save_btn.clicked.connect(self._save)
        save_row.addWidget(save_btn)
        inner_layout.addLayout(save_row)
        inner_layout.addStretch()

    def _make_section(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("apps_container")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl = QLabel(title)
        lbl.setObjectName("section_header")
        layout.addWidget(lbl)
        layout.addWidget(self._separator())
        return frame

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        line.setMaximumHeight(1)
        return line

    def _toggle_row(
        self, parent_layout, title: str, description: str
    ):
        row = QHBoxLayout()
        label_col = QVBoxLayout()
        label_col.setSpacing(2)
        lbl = QLabel(title)
        lbl.setObjectName("setting_label")
        desc = QLabel(description)
        desc.setObjectName("setting_desc")
        label_col.addWidget(lbl)
        label_col.addWidget(desc)
        row.addLayout(label_col, 1)

        from ui.widgets.fluent import ToggleSwitch
        check = ToggleSwitch()
        row.addWidget(check)
        parent_layout.addLayout(row)
        return check

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 14px; color: {tm.color('text_sub')}; }}
            QLabel#section_header {{ font-size: 15px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 0.5px; }}
            QLabel#setting_label {{ color: {tm.color('text_main')}; font-size: 15px; font-weight: 600; }}
            QLabel#setting_desc {{ color: {tm.color('text_sub')}; font-size: 13px; }}
            QFrame#apps_container {{ background: {tm.color('card_bg')}; border-radius: 12px; border: 1px solid {tm.color('border')}; }}
            QFrame#separator {{ background: {tm.color('border')}; }}
            
            QComboBox, QSpinBox {{
                background-color: {tm.color('primary_btn_gradient')};
                border: 1px solid {tm.color('border')};
                border-radius: 6px;
                padding: 6px 12px;
                color: {tm.color('text_main')};
                font-size: 14px;
                font-weight: 500;
            }}
            QComboBox:hover, QSpinBox:hover {{
                border: 1px solid {tm.color('border_hover')};
                background-color: {tm.color('primary_btn_hover')};
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
        """)
        
        # We need to manually set these if they change dynamically
        if "✗" in self._data_status_lbl.text():
            self._data_status_lbl.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 600; font-size: 11px;")
        else:
            self._data_status_lbl.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 600; font-size: 11px;")

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
            # Temporarily disconnect to avoid triggering change animation during load
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
        else:
            self._sg_action_combo.setCurrentIndex(0)
        curr_mode = self._sm.shutdown_mode
        idx = self._sg_mode_combo.findData(curr_mode)
        if idx >= 0:
            self._sg_mode_combo.setCurrentIndex(idx)
        self._sg_timeout_spin.setValue(self._sm.idle_timeout_minutes)
        
        media_timeout = self._sm.media_idle_timeout_minutes
        idx2 = self._sg_media_timeout_combo.findData(media_timeout)
        if idx2 >= 0:
            self._sg_media_timeout_combo.setCurrentIndex(idx2)
        else:
            self._sg_media_timeout_combo.setCurrentIndex(3)  # default 15 min
            
        retention = self._sm.get_int("history_retention_days", 30)
        idx3 = self._retention_combo.findData(retention)
        if idx3 >= 0:
            self._retention_combo.setCurrentIndex(idx3)

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
            self,
            "Save Report CSV",
            str(Path.home() / "Documents" / f"digital_wellbeing_report_{start}_{end}.csv"),
            "CSV Files (*.csv)",
        )

        if file_path:
            from ui.theme import ThemeManager
            tm = ThemeManager.instance()
            try:
                exporter = CSVExporter()
                dest = exporter.export_sessions(start, end, Path(file_path))
                self._data_status_lbl.setText(f"✓ Report exported to: {dest.name}")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 600; font-size: 11px;")
            except Exception as exc:
                self._data_status_lbl.setText(f"✗ Export failed: {exc}")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 600; font-size: 11px;")

    def _on_backup_db(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Database",
            str(Path.home() / "Documents" / f"digital_wellbeing_backup_{date.today()}.db"),
            "Database Files (*.db)",
        )
        if file_path:
            from ui.theme import ThemeManager
            tm = ThemeManager.instance()
            try:
                repo = Repository()
                dest = repo.backup_database(Path(file_path))
                self._data_status_lbl.setText(f"✓ Database backed up to: {dest.name}")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 600; font-size: 11px;")
            except Exception as exc:
                self._data_status_lbl.setText(f"✗ Backup failed: {exc}")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 600; font-size: 11px;")

    def _on_restore_db(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirm Database Restore",
            "Restoring database will overwrite your current tracking data. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Database Backup",
                str(Path.home() / "Documents"),
                "Database Files (*.db)",
            )
            if file_path:
                from ui.theme import ThemeManager
                tm = ThemeManager.instance()
                try:
                    repo = Repository()
                    repo.restore_database(Path(file_path))
                    self._data_status_lbl.setText(f"✓ Database restored successfully from: {Path(file_path).name}")
                    self._data_status_lbl.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 600; font-size: 11px;")
                except Exception as exc:
                    self._data_status_lbl.setText(f"✗ Restore failed: {exc}")
                    self._data_status_lbl.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 600; font-size: 11px;")

    def _on_clear_history(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Confirm Clear History",
            "Are you sure you want to permanently delete all tracking history? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from ui.theme import ThemeManager
            tm = ThemeManager.instance()
            try:
                repo = Repository()
                count = repo.clear_all_sessions()
                self._data_status_lbl.setText(f"✓ Cleared {count} sessions from history.")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('success_text')}; font-weight: 600; font-size: 11px;")
            except Exception as exc:
                self._data_status_lbl.setText(f"✗ Clear history failed: {exc}")
                self._data_status_lbl.setStyleSheet(f"color: {tm.color('danger_text')}; font-weight: 600; font-size: 11px;")

    def _save(self) -> None:
        theme_val = self._theme_combo.currentData()
        if theme_val:
            self._sm.theme = theme_val
            # Theme change is handled dynamically now
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
        
        media_timeout_val = self._sg_media_timeout_combo.currentData()
        if media_timeout_val is not None:
            self._sm.media_idle_timeout_minutes = media_timeout_val

        ret_val = self._retention_combo.currentData()
        if ret_val is not None:
            self._sm.set_int("history_retention_days", ret_val)
            # Trigger cleanup immediately when saved
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

