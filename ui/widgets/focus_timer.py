"""
focus_timer.py — Immersive Focus Session / Pomodoro Timer widget with Modes, Presets, and Active State.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
    QScrollArea, QDialog, QStackedWidget, QProgressBar, QCheckBox, QSizePolicy, QLineEdit,
    QComboBox,
)
from ui.theme import ThemeManager
from ui.icons import get_icon


class ChipWidget(QFrame):
    removed = Signal(str)
    
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text_val = text
        self.setObjectName("chip")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 8, 4)
        layout.setSpacing(6)
        
        self.lbl = QLabel(text)
        self.lbl.setObjectName("chip_text")
        
        self.btn = QPushButton("×")
        self.btn.setObjectName("chip_close")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(lambda: self.removed.emit(self.text_val))
        self.btn.setFixedSize(16, 16)
        
        layout.addWidget(self.lbl)
        layout.addWidget(self.btn)
        
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())
        self._apply_theme()
        
    def _apply_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#chip {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
            }}
            QLabel#chip_text {{
                color: {tm.color('text_main')};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#chip_close {{
                background: transparent;
                border: none;
                color: {tm.color('text_sub')};
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton#chip_close:hover {{
                color: {tm.color('danger_text')};
            }}
        """)


class AddWebsiteDialog(QDialog):
    """Clean, focused modal for configuring a blocked website domain for Focus Mode."""

    def __init__(self, mode: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Add Blocked Website — {mode.title()}")
        self.setFixedSize(500, 370)
        self.setObjectName("add_website_dialog")
        self._chosen_domain: Optional[str] = None
        self._setup_ui(mode)
        self._apply_dialog_theme()

    def _setup_ui(self, mode: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)

        # Header badge
        badge = QLabel("WEBSITE RESTRICTION")
        badge.setObjectName("badge_label")
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)

        title = QLabel("Add Blocked Website")
        title.setObjectName("dialog_title")
        layout.addWidget(title)

        desc = QLabel(
            f"Enter a website domain to block during {mode.title()} Focus sessions across all browsers. "
            "Traffic to this domain and its subdomains will be safely blocked."
        )
        desc.setObjectName("dialog_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Quick Preset Buttons
        sugg_lbl = QLabel("POPULAR PRESETS:")
        sugg_lbl.setObjectName("apps_heading")
        layout.addWidget(sugg_lbl)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        quick_presets = [
            ("YouTube", "youtube.com"),
            ("Instagram", "instagram.com"),
            ("Reddit", "reddit.com"),
            ("X / Twitter", "x.com"),
            ("TikTok", "tiktok.com"),
        ]
        for label, domain in quick_presets:
            p_btn = QPushButton(label)
            p_btn.setObjectName("preset_quick_btn")
            p_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            p_btn.clicked.connect(lambda _, d=domain: self._set_input(d))
            preset_row.addWidget(p_btn)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        # Domain Input Field
        input_lbl = QLabel("DOMAIN / WEBSITE:")
        input_lbl.setObjectName("apps_heading")
        layout.addWidget(input_lbl)

        self._domain_input = QLineEdit()
        self._domain_input.setObjectName("domain_input")
        self._domain_input.setPlaceholderText("e.g. reddit.com or youtube.com")
        self._domain_input.textChanged.connect(self._validate_input)
        layout.addWidget(self._domain_input)

        # Feedback text
        self._feedback_lbl = QLabel("")
        self._feedback_lbl.setObjectName("feedback_lbl")
        layout.addWidget(self._feedback_lbl)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        self._add_btn = QPushButton("+ Add Block")
        self._add_btn.setObjectName("btn_start")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self._add_btn)
        layout.addLayout(btn_layout)

    def _set_input(self, domain: str):
        self._domain_input.setText(domain)
        self._domain_input.setFocus()

    def _validate_input(self, text: str):
        from protection.website_blocker import WebsiteBlocker
        clean = WebsiteBlocker.clean_domain(text)
        if not text.strip():
            self._feedback_lbl.setText("")
            self._add_btn.setEnabled(False)
        elif not clean:
            self._feedback_lbl.setText("Please enter a valid domain (e.g., example.com)")
            self._feedback_lbl.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 500;")
            self._add_btn.setEnabled(False)
        else:
            self._feedback_lbl.setText(f"Will block {clean} (and www.{clean})")
            self._feedback_lbl.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 500;")
            self._add_btn.setEnabled(True)

    def _on_add(self):
        from protection.website_blocker import WebsiteBlocker
        clean = WebsiteBlocker.clean_domain(self._domain_input.text())
        if clean:
            self._chosen_domain = clean
            self.accept()

    @property
    def domain(self) -> Optional[str]:
        return self._chosen_domain

    def _apply_dialog_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog#add_website_dialog {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border_strong')};
                border-radius: 14px;
            }}
            QLabel#badge_label {{
                color: #10B981;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                background: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 10px;
                padding: 3px 10px;
            }}
            QLabel#dialog_title {{
                font-size: 20px;
                font-weight: 800;
                color: {tm.color('text_main')};
                letter-spacing: -0.4px;
            }}
            QLabel#dialog_desc {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
                line-height: 1.4;
            }}
            QLabel#apps_heading {{
                font-size: 11px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                letter-spacing: 1.2px;
            }}
            QPushButton#preset_quick_btn {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                color: {tm.color('text_sub')};
                font-size: 11px;
                font-weight: 600;
                padding: 5px 10px;
            }}
            QPushButton#preset_quick_btn:hover {{
                background: {tm.color('card_hover')};
                color: {tm.color('text_main')};
                border-color: {tm.color('accent')};
            }}
            QLineEdit#domain_input {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 9px;
                color: {tm.color('text_main')};
                font-size: 13px;
                padding: 9px 12px;
            }}
            QLineEdit#domain_input:focus {{
                border: 1px solid {tm.color('accent')};
            }}
            QPushButton#btn_cancel {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 9px;
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                padding: 9px 18px;
            }}
            QPushButton#btn_cancel:hover {{
                background: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
            QPushButton#btn_start {{
                background: {tm.color('accent')};
                border: 1px solid {tm.color('accent')};
                border-radius: 9px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 9px 22px;
            }}
            QPushButton#btn_start:hover {{
                background: {tm.color('accent_hover')};
            }}
            QPushButton#btn_start:disabled {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                color: {tm.color('text_muted')};
            }}
        """)


class DeepFocusPreflightDialog(QDialog):
    """Unified modal confirming strict enforcement of applications and website blocks before starting Focus."""

    def __init__(self, mode: str, allowed_apps: List[str], blocked_websites: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Focus Preflight Review — {mode.title()}")
        self.setFixedSize(560, 470)
        self.setObjectName("preflight_dialog")
        self._mode = mode
        self._allowed_apps = allowed_apps or []
        self._blocked_websites = blocked_websites or []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)
        
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(10)
        
        badge = QLabel("FOCUS PREFLIGHT REVIEW")
        badge.setObjectName("badge_label")
        hdr_row.addWidget(badge)
        hdr_row.addStretch()
        layout.addLayout(hdr_row)

        title = QLabel(f"Start {mode.title()} Focus?")
        title.setObjectName("dialog_title")
        layout.addWidget(title)
        
        desc = QLabel(
            "Review the restrictions that will take effect immediately upon starting. "
            "Windows system processes & background infrastructure remain safe."
        )
        desc.setObjectName("dialog_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Split Content Grid: Left (Applications) & Right (Websites)
        content_grid = QHBoxLayout()
        content_grid.setSpacing(16)

        # Column 1: Applications
        apps_col = QVBoxLayout()
        apps_col.setSpacing(8)

        is_custom = (mode == "custom")
        app_subheading = "BLOCKED APPLICATIONS:" if is_custom else "ALLOWED APPLICATIONS:"
        apps_lbl = QLabel(app_subheading)
        apps_lbl.setObjectName("apps_heading")
        apps_col.addWidget(apps_lbl)

        apps_scroll = QScrollArea()
        apps_scroll.setWidgetResizable(True)
        apps_scroll.setFrameShape(QFrame.Shape.NoFrame)
        apps_scroll.setObjectName("apps_scroll")

        apps_container = QWidget()
        apps_list_layout = QVBoxLayout(apps_container)
        apps_list_layout.setContentsMargins(8, 8, 8, 8)
        apps_list_layout.setSpacing(6)

        if not self._allowed_apps:
            none_msg = "No applications blocked." if is_custom else "No user apps allowed. Standard apps will be closed."
            none_lbl = QLabel(none_msg)
            none_lbl.setObjectName("none_lbl")
            none_lbl.setWordWrap(True)
            apps_list_layout.addWidget(none_lbl)
        else:
            for a in self._allowed_apps:
                row = QHBoxLayout()
                row.setSpacing(8)
                dot = QLabel("×" if is_custom else "✓")
                dot.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 12px;" if is_custom else "color: #10B981; font-weight: bold; font-size: 12px;")
                txt = QLabel(a)
                txt.setStyleSheet("color: #F1F5F9; font-weight: 600; font-size: 12px;")
                row.addWidget(dot)
                row.addWidget(txt)
                row.addStretch()
                apps_list_layout.addLayout(row)

        apps_list_layout.addStretch()
        apps_scroll.setWidget(apps_container)
        apps_col.addWidget(apps_scroll, 1)
        content_grid.addLayout(apps_col, 1)

        # Column 2: Blocked Websites
        sites_col = QVBoxLayout()
        sites_col.setSpacing(8)

        sites_lbl = QLabel("BLOCKED WEBSITES:")
        sites_lbl.setObjectName("apps_heading")
        sites_col.addWidget(sites_lbl)

        sites_scroll = QScrollArea()
        sites_scroll.setWidgetResizable(True)
        sites_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sites_scroll.setObjectName("apps_scroll")

        sites_container = QWidget()
        sites_list_layout = QVBoxLayout(sites_container)
        sites_list_layout.setContentsMargins(8, 8, 8, 8)
        sites_list_layout.setSpacing(6)

        if not self._blocked_websites:
            none_sites = QLabel("No websites blocked for this mode.")
            none_sites.setObjectName("none_lbl")
            none_sites.setWordWrap(True)
            sites_list_layout.addWidget(none_sites)
        else:
            for site in self._blocked_websites:
                row = QHBoxLayout()
                row.setSpacing(8)
                cross = QLabel("×")
                cross.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 13px;")
                txt = QLabel(site)
                txt.setStyleSheet("color: #F1F5F9; font-weight: 600; font-size: 12px;")
                row.addWidget(cross)
                row.addWidget(txt)
                row.addStretch()
                sites_list_layout.addLayout(row)

        sites_list_layout.addStretch()
        sites_scroll.setWidget(sites_container)
        sites_col.addWidget(sites_scroll, 1)
        content_grid.addLayout(sites_col, 1)

        layout.addLayout(content_grid, 1)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        
        start_btn = QPushButton("▶  Start Focus Session")
        start_btn.setObjectName("btn_start")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(start_btn)
        layout.addLayout(btn_layout)
        
        self._apply_dialog_theme()

    def _apply_dialog_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog#preflight_dialog {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border_strong')};
                border-radius: 14px;
            }}
            QLabel#badge_label {{
                color: #10B981;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                background: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 10px;
                padding: 3px 10px;
            }}
            QLabel#dialog_title {{
                font-size: 20px;
                font-weight: 800;
                color: {tm.color('text_main')};
                letter-spacing: -0.4px;
            }}
            QLabel#dialog_desc {{
                font-size: 12px;
                font-weight: 500;
                color: {tm.color('text_sub')};
                line-height: 1.4;
            }}
            QLabel#apps_heading {{
                font-size: 11px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                letter-spacing: 1.2px;
            }}
            QLabel#none_lbl {{
                color: #F59E0B;
                font-size: 12px;
                font-style: italic;
            }}
            QScrollArea#apps_scroll {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                padding: 4px;
            }}
            QPushButton#btn_cancel {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 9px;
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                padding: 9px 18px;
            }}
            QPushButton#btn_cancel:hover {{
                background: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
            QPushButton#btn_start {{
                background: {tm.color('accent')};
                border: 1px solid {tm.color('accent')};
                border-radius: 9px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 9px 22px;
            }}
            QPushButton#btn_start:hover {{
                background: {tm.color('accent_hover')};
            }}
        """)


class FocusTimerWidget(QFrame):
    card_clicked = Signal()
    focus_completed = Signal()
    DEFAULT_FOCUS_M = 25

    def __init__(self, parent=None, focus_manager=None) -> None:
        super().__init__(parent)
        self.setObjectName("focus_cockpit_card")
        
        from protection.focus_manager import FocusManager, STUDENT_FOCUS_PROFILES
        self._fm = focus_manager or FocusManager.instance()
        self._student_focus_profiles = dict(STUDENT_FOCUS_PROFILES)
        self._fm.tick.connect(self._on_tick)
        self._fm.focus_state_changed.connect(self._on_state_changed)
        self._fm.focus_completed.connect(self._on_focus_completed_internal)
        self._fm.focus_paused.connect(self._on_focus_paused)
        self._fm.focus_resumed.connect(self._on_focus_resumed)
        self._fm.focus_reset.connect(self._on_focus_reset)
        self._fm.focus_cancelled.connect(self._on_focus_cancelled)
        self._fm.mode_changed.connect(self._on_focus_mode_changed)
        
        self._selected_minutes = self.DEFAULT_FOCUS_M
        self._session_total_seconds = self.DEFAULT_FOCUS_M * 60
        self._just_completed = False
        
        self._setup_ui()
        
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self._stack = QStackedWidget(self)
        main_layout.addWidget(self._stack)
        
        # 0: INACTIVE CONFIGURATION VIEW
        self._inactive_view = QWidget()
        self._build_inactive_view()
        self._stack.addWidget(self._inactive_view)
        
        # 1: ACTIVE FOCUS COCKPIT VIEW
        self._active_view = QWidget()
        self._build_active_view()
        self._stack.addWidget(self._active_view)
        
        # Sync Initial State
        self._site_search_query = ""
        self._sync_mode_buttons()
        self._refresh_blocklist_ui()
        self._refresh_websites_ui()
        self._sync_ui_state()

    def _build_inactive_view(self) -> None:
        layout = QVBoxLayout(self._inactive_view)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Header: Mode Selection Label & Strict Mode Checkbox
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(8)
        lbl_modes = QLabel("SELECT FOCUS MODE")
        lbl_modes.setObjectName("section_eyebrow")
        hdr_row.addWidget(lbl_modes)
        hdr_row.addStretch()

        self._strict_chk = QCheckBox("Strict Mode (PIN Required)")
        self._strict_chk.setObjectName("strict_chk")
        self._strict_chk.setToolTip("Requires security PIN to stop session early.")
        hdr_row.addWidget(self._strict_chk)
        layout.addLayout(hdr_row)

        # Mode Selector Buttons (5 Modes)
        modes_row = QHBoxLayout()
        modes_row.setSpacing(10)
        self._mode_btns = {}
        modes_def = [
            ("study", "Study", "Research & reading"),
            ("work", "Work", "Office & workflow"),
            ("movie", "Movie", "Media & full-screen"),
            ("deep", "Deep Focus", "Strict allowlist"),
            ("custom", "Custom", "Custom blocklist")
        ]
        for m, label, desc in modes_def:
            clean_desc = desc.replace("&", "&&")
            btn = QPushButton(f"{label}\n{clean_desc}")
            btn.setObjectName("mode_card_btn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            btn.clicked.connect(lambda checked, mode=m: self._set_mode(mode))
            modes_row.addWidget(btn, 1)
            self._mode_btns[m] = btn
        layout.addLayout(modes_row)

        student_profile_row = QHBoxLayout()
        student_profile_row.setSpacing(10)
        student_profile_label = QLabel("STUDENT SESSION PROFILE")
        student_profile_label.setObjectName("section_eyebrow")
        student_profile_row.addWidget(student_profile_label)
        self._student_profile_combo = QComboBox()
        self._student_profile_combo.setObjectName("student_focus_profile_combo")
        self._student_profile_combo.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._student_profile_combo.addItem("Choose a student profile…", None)
        for profile_key, profile_label in self._student_focus_profiles.items():
            self._student_profile_combo.addItem(profile_label, profile_key)
        self._student_profile_combo.currentIndexChanged.connect(self._on_student_profile_changed)
        student_profile_row.addWidget(self._student_profile_combo)
        student_profile_row.addStretch()
        layout.addLayout(student_profile_row)

        # Main Inactive Body: 2 Columns
        body_grid = QHBoxLayout()
        body_grid.setSpacing(24)

        # Left Column: Duration Readout + Presets
        left_box = QFrame()
        left_box.setObjectName("inner_frosted_box")
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(20, 18, 20, 18)
        left_layout.setSpacing(14)

        lbl_dur_hdr = QLabel("SESSION DURATION")
        lbl_dur_hdr.setObjectName("section_eyebrow")
        left_layout.addWidget(lbl_dur_hdr)

        self._time_display = QLabel(self._format_time(self._selected_minutes * 60))
        self._time_display.setObjectName("timer_display")
        self._time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self._time_display)

        self._status_lbl = QLabel("Ready to focus")
        self._status_lbl.setObjectName("timer_status")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self._status_lbl)

        # Duration Presets
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        chips_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chips = []
        for minutes in (15, 25, 45, 60, 90):
            chip = QPushButton(f"{minutes}m")
            chip.setObjectName("timer_chip")
            chip.setCheckable(True)
            chip.setProperty("minutes", minutes)
            chip.setChecked(minutes == self._selected_minutes)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            chip.clicked.connect(lambda checked, m=minutes: self.set_preset(m))
            chips_row.addWidget(chip)
            self._chips.append(chip)
        left_layout.addLayout(chips_row)
        left_layout.addStretch()

        body_grid.addWidget(left_box, 1)

        # Right Column: Configured Applications & Blocked Websites
        right_box = QFrame()
        right_box.setObjectName("inner_frosted_box")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(20, 16, 20, 16)
        right_layout.setSpacing(10)

        # Section 1: Configured Applications
        self._list_hdr = QLabel("CONFIGURED APPLICATIONS")
        self._list_hdr.setObjectName("section_eyebrow")
        right_layout.addWidget(self._list_hdr)

        self._list_sub = QLabel("Allowed during session")
        self._list_sub.setObjectName("list_subtitle")
        right_layout.addWidget(self._list_sub)

        # Scrollable chips container for apps
        self._blocklist_container = QWidget()
        self._blocklist_layout = QHBoxLayout(self._blocklist_container)
        self._blocklist_layout.setContentsMargins(0, 0, 0, 0)
        self._blocklist_layout.setSpacing(8)
        self._blocklist_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._blocklist_scroll = QScrollArea()
        self._blocklist_scroll.setWidgetResizable(True)
        self._blocklist_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._blocklist_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._blocklist_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._blocklist_scroll.setFixedHeight(44)
        self._blocklist_scroll.setWidget(self._blocklist_container)
        right_layout.addWidget(self._blocklist_scroll)

        # Add application button
        app_ctrl_row = QHBoxLayout()
        self._add_app_btn = QPushButton("+ Add Application")
        self._add_app_btn.setObjectName("action_pill_btn")
        self._add_app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_app_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._add_app_btn.clicked.connect(self._open_app_picker)
        app_ctrl_row.addWidget(self._add_app_btn)
        app_ctrl_row.addStretch()
        right_layout.addLayout(app_ctrl_row)

        # Subtle divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("focus_divider")
        right_layout.addWidget(divider)

        # Section 2: Blocked Websites
        web_hdr_row = QHBoxLayout()
        self._websites_hdr = QLabel("BLOCKED WEBSITES")
        self._websites_hdr.setObjectName("section_eyebrow")
        web_hdr_row.addWidget(self._websites_hdr)

        self._websites_count_lbl = QLabel("0 sites")
        self._websites_count_lbl.setObjectName("count_badge")
        web_hdr_row.addWidget(self._websites_count_lbl)
        web_hdr_row.addStretch()

        self._site_search_input = QLineEdit()
        self._site_search_input.setObjectName("site_search_input")
        self._site_search_input.setPlaceholderText("Filter sites...")
        self._site_search_input.setFixedWidth(130)
        self._site_search_input.textChanged.connect(self._on_search_websites)
        web_hdr_row.addWidget(self._site_search_input)
        right_layout.addLayout(web_hdr_row)

        self._websites_sub = QLabel("Blocked across all browsers (DNS & hosts level)")
        self._websites_sub.setObjectName("list_subtitle")
        right_layout.addWidget(self._websites_sub)

        # Scrollable chips container for websites
        self._websites_container = QWidget()
        self._websites_layout = QHBoxLayout(self._websites_container)
        self._websites_layout.setContentsMargins(0, 0, 0, 0)
        self._websites_layout.setSpacing(8)
        self._websites_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._websites_scroll = QScrollArea()
        self._websites_scroll.setWidgetResizable(True)
        self._websites_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._websites_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._websites_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._websites_scroll.setFixedHeight(44)
        self._websites_scroll.setWidget(self._websites_container)
        right_layout.addWidget(self._websites_scroll)

        # Add website button
        web_ctrl_row = QHBoxLayout()
        self._add_website_btn = QPushButton("+ Add Website")
        self._add_website_btn.setObjectName("action_pill_btn")
        self._add_website_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_website_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._add_website_btn.clicked.connect(self._open_website_picker)
        web_ctrl_row.addWidget(self._add_website_btn)
        web_ctrl_row.addStretch()
        right_layout.addLayout(web_ctrl_row)

        body_grid.addWidget(right_box, 1)
        layout.addLayout(body_grid)

        # Primary Start Button & Reset
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._start_btn = QPushButton("▶  Start Focus Session")
        self._start_btn.setObjectName("primary_start_btn")
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._start_btn.setMinimumHeight(46)
        self._start_btn.clicked.connect(self._toggle_timer)
        action_row.addWidget(self._start_btn, 3)

        self._reset_btn = QPushButton("↺ Reset")
        self._reset_btn.setObjectName("secondary_btn")
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._reset_btn.setMinimumHeight(46)
        self._reset_btn.clicked.connect(self._stop_timer)
        action_row.addWidget(self._reset_btn, 1)

        layout.addLayout(action_row)

    def _build_active_view(self) -> None:
        layout = QVBoxLayout(self._active_view)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Top Badge: FOCUS ACTIVE
        top_badge_row = QHBoxLayout()
        top_badge_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._active_status_pill = QLabel("●  FOCUS ACTIVE")
        self._active_status_pill.setObjectName("active_focus_pill")
        top_badge_row.addWidget(self._active_status_pill)
        layout.addLayout(top_badge_row)

        # Active Mode Name
        self._active_mode_lbl = QLabel("DEEP FOCUS MODE")
        self._active_mode_lbl.setObjectName("active_mode_title")
        self._active_mode_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._active_mode_lbl)

        # Massive Countdown Display (initialized with configured duration)
        self._active_time_display = QLabel(self._format_time(self._selected_minutes * 60))
        self._active_time_display.setObjectName("active_countdown_display")
        self._active_time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._active_time_display)

        # Progress Bar & Labels
        prog_container = QWidget()
        prog_container.setMaximumWidth(480)
        prog_layout = QVBoxLayout(prog_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(8)

        self._active_progress_bar = QProgressBar()
        self._active_progress_bar.setFixedHeight(8)
        self._active_progress_bar.setTextVisible(False)
        self._active_progress_bar.setObjectName("active_focus_progress")
        self._active_progress_bar.setValue(0)
        prog_layout.addWidget(self._active_progress_bar)

        prog_labels = QHBoxLayout()
        self._active_elapsed_lbl = QLabel("0m elapsed")
        self._active_elapsed_lbl.setObjectName("progress_subtext")
        self._active_remaining_lbl = QLabel(f"{self._selected_minutes}m remaining")
        self._active_remaining_lbl.setObjectName("progress_subtext")
        self._active_remaining_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        prog_labels.addWidget(self._active_elapsed_lbl)
        prog_labels.addStretch()
        prog_labels.addWidget(self._active_remaining_lbl)
        prog_layout.addLayout(prog_labels)

        layout.addWidget(prog_container, 0, Qt.AlignmentFlag.AlignCenter)

        # Restrictons Panel (Allowed Apps & Blocked Websites)
        apps_panel = QFrame()
        apps_panel.setObjectName("inner_frosted_box")
        apps_panel.setMaximumWidth(540)
        apps_panel_layout = QVBoxLayout(apps_panel)
        apps_panel_layout.setContentsMargins(18, 14, 18, 14)
        apps_panel_layout.setSpacing(8)

        self._active_policy_lbl = QLabel("ALLOWED APPLICATIONS")
        self._active_policy_lbl.setObjectName("section_eyebrow")
        apps_panel_layout.addWidget(self._active_policy_lbl)

        self._active_apps_summary = QLabel("All protected processes + 3 configured applications")
        self._active_apps_summary.setObjectName("active_apps_text")
        apps_panel_layout.addWidget(self._active_apps_summary)

        self._active_websites_lbl = QLabel("BLOCKED WEBSITES")
        self._active_websites_lbl.setObjectName("section_eyebrow")
        apps_panel_layout.addWidget(self._active_websites_lbl)

        self._active_websites_summary = QLabel("3 distracting websites blocked across all browsers")
        self._active_websites_summary.setObjectName("active_apps_text")
        apps_panel_layout.addWidget(self._active_websites_summary)

        layout.addWidget(apps_panel, 0, Qt.AlignmentFlag.AlignCenter)

        # End & Pause Session Controls
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._active_pause_btn = QPushButton("❚❚  Pause")
        self._active_pause_btn.setObjectName("active_pause_btn")
        self._active_pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._active_pause_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._active_pause_btn.setMinimumHeight(44)
        self._active_pause_btn.setMinimumWidth(130)
        self._active_pause_btn.clicked.connect(self._toggle_pause)
        btn_box.addWidget(self._active_pause_btn)

        self._active_stop_btn = QPushButton("■  End Focus Session")
        self._active_stop_btn.setObjectName("active_stop_btn")
        self._active_stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._active_stop_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._active_stop_btn.setMinimumHeight(44)
        self._active_stop_btn.setMinimumWidth(180)
        self._active_stop_btn.clicked.connect(self._stop_timer)
        btn_box.addWidget(self._active_stop_btn)

        layout.addLayout(btn_box)

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QFrame#focus_cockpit_card {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 16px;
            }}
            QFrame#inner_frosted_box {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QFrame#focus_divider {{
                background-color: {tm.color('border')};
                max-height: 1px;
            }}
            QLabel#section_eyebrow {{
                font-size: 11px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                letter-spacing: 1.5px;
                text-transform: uppercase;
            }}
            QLabel#list_subtitle {{
                font-size: 12px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            QLabel#empty_placeholder {{
                font-size: 12px;
                font-style: italic;
                color: {tm.color('text_muted')};
            }}
            QCheckBox#strict_chk {{
                color: {tm.color('danger_text')};
                font-size: 12px;
                font-weight: 600;
            }}
            
            /* Mode Selector Cards */
            QPushButton#mode_card_btn {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                color: {tm.color('text_sub')};
                padding: 12px 10px;
                font-size: 13px;
                font-weight: 700;
                line-height: 1.4;
                text-align: center;
            }}
            QPushButton#mode_card_btn:hover {{
                background: {tm.color('card_hover')};
                color: {tm.color('text_main')};
                border-color: {tm.color('border_hover')};
            }}
            QPushButton#mode_card_btn:checked {{
                background: {tm.color('accent_emerald_bg')};
                border: 1px solid {tm.color('accent')};
                color: {tm.color('accent')};
            }}
            
            /* Inactive Timer Readout */
            QLabel#timer_display {{
                font-size: 48px;
                font-weight: 800;
                color: {tm.color('text_main')};
                letter-spacing: -1.5px;
            }}
            QLabel#timer_status {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            
            /* Presets & Pills */
            QPushButton#timer_chip {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 600;
                padding: 6px 14px;
            }}
            QPushButton#timer_chip:hover {{
                background-color: {tm.color('card_hover')};
                color: {tm.color('text_main')};
                border-color: {tm.color('border_hover')};
            }}
            QPushButton#timer_chip:checked {{
                background-color: rgba(16, 185, 129, 0.15);
                border: 1px solid #10B981;
                color: #10B981;
                font-weight: 700;
            }}
            QPushButton#action_pill_btn {{
                background-color: {tm.color('surface')};
                border: 1px dashed {tm.color('border_hover')};
                border-radius: 8px;
                color: {tm.color('accent')};
                font-size: 12px;
                font-weight: 600;
                padding: 6px 14px;
            }}
            QPushButton#action_pill_btn:hover {{
                background-color: {tm.color('accent_emerald_bg')};
                border-color: {tm.color('accent')};
            }}
            QLineEdit#site_search_input {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 6px;
                color: {tm.color('text_main')};
                font-size: 11px;
                padding: 3px 8px;
            }}
            QLineEdit#site_search_input:focus {{
                border-color: {tm.color('accent')};
            }}
            QLabel#count_badge {{
                background: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 6px;
                color: #10B981;
                font-size: 10px;
                font-weight: 700;
                padding: 1px 6px;
            }}
            
            /* Action Buttons */
            QPushButton#primary_start_btn {{
                background-color: {tm.color('accent')};
                border: 1px solid {tm.color('accent')};
                border-radius: 10px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.3px;
                padding: 10px 20px;
            }}
            QPushButton#primary_start_btn:hover {{
                background-color: {tm.color('accent_hover')};
                border-color: {tm.color('accent_hover')};
            }}
            QPushButton#secondary_btn {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                padding: 10px 18px;
            }}
            QPushButton#secondary_btn:hover {{
                background-color: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
            
            /* Active Cockpit Styling */
            QLabel#active_focus_pill {{
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.5px;
                color: #10B981;
                background: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.30);
                border-radius: 12px;
                padding: 5px 16px;
            }}
            QLabel#active_mode_title {{
                font-size: 14px;
                font-weight: 700;
                color: {tm.color('text_sub')};
                letter-spacing: 2px;
                text-transform: uppercase;
            }}
            QLabel#active_countdown_display {{
                font-size: 72px;
                font-weight: 900;
                color: {tm.color('text_main')};
                letter-spacing: -2px;
            }}
            QProgressBar#active_focus_progress {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 4px;
            }}
            QProgressBar#active_focus_progress::chunk {{
                background: #10B981;
                border-radius: 4px;
            }}
            QLabel#progress_subtext {{
                font-size: 12px;
                font-weight: 600;
                color: {tm.color('text_muted')};
            }}
            QLabel#active_apps_text {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_main')};
            }}
            QPushButton#active_stop_btn {{
                background: rgba(239, 68, 68, 0.10);
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 10px;
                color: #EF4444;
                font-size: 13px;
                font-weight: 700;
                padding: 10px 24px;
            }}
            QPushButton#active_stop_btn:hover {{
                background: rgba(239, 68, 68, 0.20);
                border-color: #EF4444;
                color: #FFFFFF;
            }}
            QPushButton#active_stop_btn:focus {{
                border: 2px solid {tm.color('focus_ring')};
            }}
            QPushButton#active_pause_btn {{
                background: rgba(245, 158, 11, 0.12);
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 10px;
                color: #F59E0B;
                font-size: 13px;
                font-weight: 700;
                padding: 10px 20px;
            }}
            QPushButton#active_pause_btn:hover {{
                background: rgba(245, 158, 11, 0.22);
                border-color: #F59E0B;
                color: #FFFFFF;
            }}
            QPushButton#active_pause_btn:focus {{
                border: 2px solid {tm.color('focus_ring')};
            }}
            QPushButton#timer_chip:focus,
            QPushButton#mode_card_btn:focus,
            QPushButton#action_pill_btn:focus,
            QPushButton#primary_start_btn:focus,
            QPushButton#secondary_btn:focus {{
                border: 2px solid {tm.color('focus_ring')};
            }}
        """)

    def set_preset(self, minutes: int) -> None:
        if self._fm.is_active:
            return
        self._selected_minutes = minutes
        self._session_total_seconds = minutes * 60
        self._time_display.setText(self._format_time(minutes * 60))
        self._active_time_display.setText(self._format_time(minutes * 60))
        self._active_remaining_lbl.setText(f"{minutes}m remaining")
        self._status_lbl.setText(f"Session set to {minutes} minutes")
        for chip in getattr(self, "_chips", []):
            chip.setChecked(chip.property("minutes") == minutes)

    def _set_mode(self, mode: str) -> None:
        if self._fm.is_active:
            return
        self._fm.set_mode(mode)

    def _sync_mode_buttons(self) -> None:
        current = self._fm.current_mode
        for m, btn in self._mode_btns.items():
            btn.setChecked(m == current)
        combo_index = self._student_profile_combo.findData(current)
        if combo_index < 0:
            combo_index = 0
        self._student_profile_combo.blockSignals(True)
        self._student_profile_combo.setCurrentIndex(combo_index)
        self._student_profile_combo.blockSignals(False)

    def _on_student_profile_changed(self, index: int) -> None:
        profile = self._student_profile_combo.itemData(index)
        if profile:
            self._set_mode(str(profile))

    def _on_focus_mode_changed(self, mode: str) -> None:
        self._sync_mode_buttons()
        self._handle_dynamic_suggestions(mode)
        self._refresh_blocklist_ui()
        self._refresh_websites_ui()

    def _handle_dynamic_suggestions(self, mode: str) -> None:
        apps = self._fm.current_mode_apps
        if apps:
            return
            
        if mode in ("study", "work", "movie") or mode in self._student_focus_profiles:
            suggested = self._fm.ensure_mode_app_suggestions(mode)
            if suggested:
                self._status_lbl.setText(f"Suggested apps populated for {mode.title()} mode.")

    def _get_suggestions(self, mode: str) -> List[str]:
        return self._fm.suggest_mode_apps(mode)

    def _refresh_blocklist_ui(self) -> None:
        while self._blocklist_layout.count():
            item = self._blocklist_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.hide()
                w.setParent(None)
                w.deleteLater()
                
        items = self._fm.current_mode_apps
        mode = self._fm.current_mode
        
        is_custom = (mode == "custom")
        self._list_hdr.setText("BLOCKED APPLICATIONS (BLOCKLIST)" if is_custom else "ALLOWED APPLICATIONS (ALLOWLIST)")
        self._list_sub.setText("These applications will be blocked during focus" if is_custom else "Only these user apps can run during session")
        
        if not items:
            placeholder = QLabel("No applications configured.")
            placeholder.setObjectName("empty_placeholder")
            self._blocklist_layout.addWidget(placeholder)
        else:
            for text in items:
                chip = ChipWidget(text)
                chip.removed.connect(self._remove_app_item)
                self._blocklist_layout.addWidget(chip)

    def _refresh_websites_ui(self) -> None:
        while self._websites_layout.count():
            item = self._websites_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.hide()
                w.setParent(None)
                w.deleteLater()

        mode = self._fm.current_mode
        sites = self._fm.get_mode_websites(mode)
        search_q = getattr(self, "_site_search_query", "").strip().lower()

        if search_q:
            filtered_sites = [s for s in sites if search_q in s.lower()]
        else:
            filtered_sites = sites

        self._websites_count_lbl.setText(f"{len(sites)} site{'s' if len(sites) != 1 else ''}")

        if not filtered_sites:
            if search_q:
                placeholder = QLabel(f"No sites matching '{search_q}'")
            else:
                placeholder = QLabel("No websites blocked for this mode.")
            placeholder.setObjectName("empty_placeholder")
            self._websites_layout.addWidget(placeholder)
        else:
            for site in filtered_sites:
                chip = ChipWidget(site)
                chip.removed.connect(self._remove_website_item)
                self._websites_layout.addWidget(chip)

    def _on_search_websites(self, query: str) -> None:
        self._site_search_query = query
        self._refresh_websites_ui()

    def _open_website_picker(self) -> None:
        mode = self._fm.current_mode
        dlg = AddWebsiteDialog(mode, self.window())
        if dlg.exec():
            domain = dlg.domain
            if domain:
                self._fm.add_mode_website(mode, domain)
                self._refresh_websites_ui()

    def _remove_website_item(self, site: str) -> None:
        self._fm.remove_mode_website(self._fm.current_mode, site)
        self._refresh_websites_ui()
            
    def _open_app_picker(self) -> None:
        mode = self._fm.current_mode
        action = "Block Application" if mode == "custom" else "Allow Application"
        title = "Add to Blocklist" if mode == "custom" else "Add to Allowlist"
        
        from ui.widgets.process_picker import ProcessPickerDialog
        dlg = ProcessPickerDialog(self.window(), mode="focus", action_text=action, title_text=title)
        if dlg.exec():
            app = dlg.selected_process_name
            if app:
                items = self._fm.current_mode_apps
                if app not in items:
                    items.append(app)
                    self._fm.save_mode_apps(mode, items)
                    self._refresh_blocklist_ui()
                    
    def _remove_app_item(self, text: str) -> None:
        items = self._fm.current_mode_apps
        if text in items:
            items.remove(text)
            self._fm.save_mode_apps(self._fm.current_mode, items)
            self._refresh_blocklist_ui()

    def _on_tick(self, seconds: int) -> None:
        time_str = self._format_time(seconds)
        self._time_display.setText(time_str)
        self._active_time_display.setText(time_str)
        
        total = self._session_total_seconds if self._session_total_seconds > 0 else (self._selected_minutes * 60)
        elapsed = max(0, total - seconds)
        pct = int((elapsed / max(total, 1)) * 100)
        self._active_progress_bar.setValue(pct)
        self._active_elapsed_lbl.setText(f"{elapsed // 60}m elapsed")
        self._active_remaining_lbl.setText(f"{seconds // 60}m remaining")

    def _on_state_changed(self, is_active: bool) -> None:
        self._sync_ui_state()

    def _sync_ui_state(self):
        if self._fm.is_active:
            self._selected_minutes = self._fm.configured_minutes
            self._session_total_seconds = self._fm.total_duration_seconds or (self._selected_minutes * 60)
            rem_s = self._fm.seconds_remaining
            time_str = self._format_time(rem_s)
            self._active_time_display.setText(time_str)

            elapsed = max(0, self._session_total_seconds - rem_s)
            pct = int((elapsed / max(self._session_total_seconds, 1)) * 100)
            self._active_progress_bar.setValue(pct)
            self._active_elapsed_lbl.setText(f"{elapsed // 60}m elapsed")
            self._active_remaining_lbl.setText(f"{rem_s // 60}m remaining")

            if self._fm.is_paused:
                self._active_status_pill.setText("❚❚  FOCUS PAUSED")
                self._active_status_pill.setStyleSheet("color: #F59E0B; background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; padding: 5px 16px;")
                if hasattr(self, "_active_pause_btn"):
                    self._active_pause_btn.setText("▶  Resume")
            else:
                self._active_status_pill.setText("●  FOCUS ACTIVE")
                self._active_status_pill.setStyleSheet("color: #10B981; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 5px 16px;")
                if hasattr(self, "_active_pause_btn"):
                    self._active_pause_btn.setText("❚❚  Pause")

            mode = self._fm.current_mode
            self._active_mode_lbl.setText(f"{mode.upper()} FOCUS MODE")
            
            apps = self._fm.current_mode_apps
            websites = self._fm.current_mode_websites
            if mode == "custom":
                self._active_policy_lbl.setText("ACTIVE BLOCKLIST")
                self._active_apps_summary.setText(f"{len(apps)} applications blocked from running")
            else:
                self._active_policy_lbl.setText("ACTIVE ALLOWLIST")
                self._active_apps_summary.setText(f"{len(apps)} user applications permitted · Windows system safe")
            
            self._active_websites_summary.setText(f"{len(websites)} distracting websites blocked across all browsers" if websites else "No website blocks active")
            
            self._stack.setCurrentIndex(1)
        else:
            self._stack.setCurrentIndex(0)
            self._time_display.setText(self._format_time(self._selected_minutes * 60))
            if self._fm.seconds_remaining == 0 and hasattr(self, "_just_completed") and self._just_completed:
                self._status_lbl.setText("Session complete! Great work.")
            else:
                self._status_lbl.setText(f"Session set to {self._selected_minutes} minutes")

    def _toggle_timer(self) -> None:
        if not self._fm.is_active:
            if self._strict_chk.isChecked() and not self._fm._pin_manager.is_enabled():
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "PIN Required", "You must configure a PIN in Settings to use Strict Mode.")
                self._strict_chk.setChecked(False)
                return
                
            mode = self._fm.current_mode
            # Preflight review showing BOTH applications and websites for all modes
            dlg = DeepFocusPreflightDialog(
                mode=mode,
                allowed_apps=self._fm.current_mode_apps,
                blocked_websites=self._fm.get_mode_websites(mode),
                parent=self.window()
            )
            if not dlg.exec():
                return
                    
            self._session_total_seconds = self._selected_minutes * 60
            self._just_completed = False
            self._fm.start_focus(self._selected_minutes, strict_mode=self._strict_chk.isChecked())

    def _toggle_pause(self) -> None:
        if not self._fm.is_active:
            return
        if self._fm.is_paused:
            self._fm.resume_focus()
        else:
            if self._fm.is_strict:
                from ui.widgets.pin_dialog import PinDialog
                dialog = PinDialog(self._fm._pin_manager, self.window())
                if dialog.exec():
                    self._fm.pause_focus(provided_pin=dialog.get_pin())
            else:
                self._fm.pause_focus()

    def _stop_timer(self) -> None:
        if not self._fm.is_active:
            # Reset countdown display back to currently configured duration
            self._session_total_seconds = self._selected_minutes * 60
            self._time_display.setText(self._format_time(self._selected_minutes * 60))
            self._status_lbl.setText(f"Session set to {self._selected_minutes} minutes")
            return
            
        if self._fm.is_strict:
            from ui.widgets.pin_dialog import PinDialog
            dialog = PinDialog(self._fm._pin_manager, self.window())
            if dialog.exec():
                self._fm.stop_focus_after_pin_dialog()
        else:
            self._fm.cancel_focus()

    def _on_focus_completed_internal(self) -> None:
        self._just_completed = True
        self._sync_ui_state()
        self.focus_completed.emit()

    def _on_focus_paused(self) -> None:
        self._sync_ui_state()

    def _on_focus_resumed(self) -> None:
        self._sync_ui_state()

    def _on_focus_reset(self, total_seconds: int) -> None:
        self._session_total_seconds = total_seconds
        self._sync_ui_state()

    def _on_focus_cancelled(self) -> None:
        self._just_completed = False
        self._sync_ui_state()

    @staticmethod
    def _format_time(seconds: int) -> str:
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"
