"""
focus_timer.py — Focus Session / Pomodoro Timer widget with quick preset chips for Desktop Dashboard.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QLineEdit, QScrollArea
)
from ui.theme import ThemeManager

class ChipWidget(QFrame):
    removed = Signal(str)
    
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text_val = text
        self.setObjectName("chip")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 8, 4)
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
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())
        self._apply_theme()
        
    def _apply_theme(self):
        tm = ThemeManager.instance()
        # HARDCODE neutral colors to prevent system pink accents from leaking in
        self.setStyleSheet(f"""
            QFrame#chip {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QLabel#chip_text {{
                color: {tm.color('text_main')};
                font-size: 12px;
                font-weight: 500;
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

class FocusTimerWidget(QFrame):
    """Focus Session / Pomodoro Timer widget with quick duration chips."""

    card_clicked = Signal()
    focus_completed = Signal()

    DEFAULT_FOCUS_M = 25

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("v2_card")
        
        from protection.focus_manager import FocusManager
        self._fm = FocusManager.instance()
        self._fm.tick.connect(self._on_tick)
        self._fm.focus_state_changed.connect(self._on_state_changed)
        self._fm.focus_completed.connect(self.focus_completed.emit)
        
        self._selected_minutes = self.DEFAULT_FOCUS_M
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        hdr = QHBoxLayout()
        self._lbl = QLabel("Focus Session")
        self._lbl.setObjectName("section_header")
        hdr.addWidget(self._lbl)
        
        from PySide6.QtWidgets import QCheckBox
        self._strict_chk = QCheckBox("Strict Mode")
        self._strict_chk.setObjectName("strict_chk")
        self._strict_chk.setToolTip("Requires PIN to exit early. Restricts all apps except allowed apps.")
        hdr.addStretch()
        hdr.addWidget(self._strict_chk)
        layout.addLayout(hdr)
        
        self._desc_lbl = QLabel("Boost productivity by blocking distracting websites and apps.")
        self._desc_lbl.setObjectName("timer_desc")
        layout.addWidget(self._desc_lbl)

        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(6)

        self._time_display = QLabel(self._format_time(self._selected_minutes * 60))
        self._time_display.setObjectName("timer_display")
        self._time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._status_lbl = QLabel("Ready to focus — select preset or start")
        self._status_lbl.setObjectName("timer_status")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        center_layout.addWidget(self._time_display)
        center_layout.addWidget(self._status_lbl)
        layout.addLayout(center_layout)

        # Quick Preset Chips Row
        self._chips_row = QHBoxLayout()
        self._chips_row.setSpacing(8)
        self._chips_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._chips = []
        for minutes in (15, 25, 45, 60):
            chip = QPushButton(f"{minutes}m")
            chip.setObjectName("timer_chip")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda checked, m=minutes: self.set_preset(m))
            self._chips_row.addWidget(chip)
            self._chips.append(chip)

        layout.addLayout(self._chips_row)
        
        layout.addSpacing(12)
        
        # Blocklist Section
        allowlist_hdr = QLabel("Blocked Applications")
        allowlist_hdr.setObjectName("timer_status")
        layout.addWidget(allowlist_hdr)
        
        self._blocklist_container = QWidget()
        self._blocklist_layout = QHBoxLayout(self._blocklist_container)
        self._blocklist_layout.setContentsMargins(0, 0, 0, 0)
        self._blocklist_layout.setSpacing(8)
        self._blocklist_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Wrap in scroll area
        self._blocklist_scroll = QScrollArea()
        self._blocklist_scroll.setWidgetResizable(True)
        self._blocklist_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._blocklist_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._blocklist_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._blocklist_scroll.setFixedHeight(40)
        self._blocklist_scroll.setWidget(self._blocklist_container)
        
        layout.addWidget(self._blocklist_scroll)
        
        # Add Input
        input_row = QHBoxLayout()
        self._block_input = QLineEdit()
        self._block_input.setPlaceholderText("Enter application (e.g., discord.exe)")
        self._block_input.setObjectName("block_input")
        self._block_input.returnPressed.connect(self._add_block_item)
        
        self._add_block_btn = QPushButton("Add")
        self._add_block_btn.setObjectName("timer_chip")
        self._add_block_btn.clicked.connect(self._add_block_item)
        
        input_row.addWidget(self._block_input, 1)
        input_row.addWidget(self._add_block_btn)
        
        layout.addLayout(input_row)
        
        layout.addSpacing(16)
        
        self._refresh_blocklist_ui()

        # Controls Row
        controls = QHBoxLayout()
        controls.setSpacing(10)

        self._start_btn = QPushButton("▶ Start Focus")
        self._start_btn.setObjectName("timer_start_btn")
        self._start_btn.setMinimumHeight(40)
        self._start_btn.clicked.connect(self._toggle_timer)

        self._reset_btn = QPushButton("↺ Stop")
        self._reset_btn.setObjectName("timer_reset_btn")
        self._reset_btn.setMinimumHeight(40)
        self._reset_btn.clicked.connect(self._stop_timer)

        controls.addWidget(self._start_btn, 2)
        controls.addWidget(self._reset_btn, 1)

        layout.addLayout(controls)
        self._sync_ui_state()

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            FocusTimerWidget#v2_card:hover {{
                background-color: {tm.color('card_hover')};
                border-color: {tm.color('border_hover')};
            }}
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 1.2px; text-transform: uppercase; }}
            QLabel#timer_desc {{ color: {tm.color('text_sub')}; font-size: 13px; margin-bottom: 8px; }}
            QLabel#timer_display {{ font-size: 42px; font-weight: 900; color: {tm.color('accent')}; letter-spacing: -1.2px; }}
            QLabel#timer_status {{ color: {tm.color('text_sub')}; font-size: 12px; font-weight: 600; }}
            QCheckBox#strict_chk {{ color: {tm.color('danger_text')}; font-weight: 600; }}
            QPushButton#timer_chip {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 700;
                padding: 4px 12px;
            }}
            QPushButton#timer_chip:hover {{
                background-color: {tm.color('border')};
                border-color: {tm.color('border_strong')};
                color: {tm.color('text_main')};
            }}
            QPushButton#timer_chip:disabled {{
                background-color: transparent;
                border-color: transparent;
                color: transparent;
            }}
            QLineEdit#block_input {{
                background-color: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 6px;
                padding: 6px 12px;
                color: {tm.color('text_main')};
                font-size: 13px;
            }}
            QLineEdit#block_input:focus {{
                border-color: {tm.color('accent')};
            }}
            QPushButton#timer_start_btn {{
                background-color: {tm.color('accent')};
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border-radius: 12px;
                padding: 8px 16px;
                border: 1px solid {tm.color('border')};
            }}
            QPushButton#timer_start_btn:hover {{
                background-color: {tm.color('accent_hover')};
            }}
            QPushButton#timer_reset_btn {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                padding: 8px 14px;
            }}
            QPushButton#timer_reset_btn:hover {{
                background-color: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
        """)
        self._update_display_color()

    def _update_display_color(self) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        if not self._fm.is_active and self._time_display.text() == "00:00":
            self._time_display.setStyleSheet(f"font-size: 42px; font-weight: 900; color: {tm.color('success_text')}; letter-spacing: -1.2px;")
        elif self._fm.is_active and self._fm.is_strict:
            self._time_display.setStyleSheet(f"font-size: 42px; font-weight: 900; color: {tm.color('danger_text')}; letter-spacing: -1.2px;")
        else:
            self._time_display.setStyleSheet(f"font-size: 42px; font-weight: 900; color: {tm.color('accent')}; letter-spacing: -1.2px;")

    def set_preset(self, minutes: int) -> None:
        if self._fm.is_active: return
        self._selected_minutes = minutes
        self._time_display.setText(self._format_time(minutes * 60))
        self._status_lbl.setText(f"Preset set to {minutes} minutes")
        self._update_display_color()
        
    def _refresh_blocklist_ui(self) -> None:
        while self._blocklist_layout.count():
            item = self._blocklist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        items = self._fm.blocked_apps
        if not items:
            placeholder = QLabel("No applications blocked. Add apps you want to restrict during Focus.")
            placeholder.setStyleSheet(f"color: {ThemeManager.instance().color('text_sub')}; font-style: italic; font-size: 12px;")
            self._blocklist_layout.addWidget(placeholder)
        else:
            for text in items:
                chip = ChipWidget(text)
                chip.removed.connect(self._remove_block_item)
                self._blocklist_layout.addWidget(chip)
            
    def _add_block_item(self) -> None:
        text = self._block_input.text().strip().lower()
        if text:
            items = self._fm.blocked_apps
            if text not in items:
                items.append(text)
                self._fm.save_blocked_apps(items)
                self._refresh_blocklist_ui()
            self._block_input.clear()
            
    def _remove_block_item(self, text: str) -> None:
        items = self._fm.blocked_apps
        if text in items:
            items.remove(text)
            self._fm.save_blocked_apps(items)
            self._refresh_blocklist_ui()

    def _on_tick(self, seconds: int) -> None:
        self._time_display.setText(self._format_time(seconds))

    def _on_state_changed(self, is_active: bool) -> None:
        self._sync_ui_state()

    def _sync_ui_state(self):
        if self._fm.is_active:
            self._start_btn.hide()
            for chip in self._chips: chip.hide()
            self._strict_chk.setEnabled(False)
            self._strict_chk.setChecked(self._fm.is_strict)
            if self._fm.blocked_apps:
                self._status_lbl.setText("App blocking: ⚠ Blocklist active")
            else:
                self._status_lbl.setText("Focusing... No apps blocked.")
            self._block_input.setEnabled(False)
            self._add_block_btn.setEnabled(False)
        else:
            self._start_btn.show()
            for chip in self._chips: chip.show()
            self._strict_chk.setEnabled(True)
            self._block_input.setEnabled(True)
            self._add_block_btn.setEnabled(True)
            self._start_btn.setText("▶ Start Focus")
            self._time_display.setText(self._format_time(self._selected_minutes * 60))
            if self._time_display.text() == "00:00":
                 self._status_lbl.setText("Session complete! Take a break")
            else:
                 self._status_lbl.setText("Ready to focus — select preset or start")
        self._update_display_color()

    def _toggle_timer(self) -> None:
        if not self._fm.is_active:
            from PySide6.QtWidgets import QMessageBox
            if self._strict_chk.isChecked() and not self._fm._pin_manager.is_enabled():
                QMessageBox.warning(self, "PIN Required", "You must configure a PIN in Settings > Protection to use Strict Mode.")
                self._strict_chk.setChecked(False)
                return
            self._fm.start_focus(self._selected_minutes, strict_mode=self._strict_chk.isChecked())

    def _stop_timer(self) -> None:
        if not self._fm.is_active:
            # It's a reset action when not running
            self._selected_minutes = self.DEFAULT_FOCUS_M
            self._time_display.setText(self._format_time(self._selected_minutes * 60))
            self._status_lbl.setText("Ready to focus — select preset or start")
            self._update_display_color()
            return
            
        if self._fm.is_strict:
            from ui.widgets.pin_dialog import PinDialog
            dialog = PinDialog(self._fm._pin_manager, self.window())
            if dialog.exec():
                # PIN was already verified inside PinDialog._verify_pin().
                # Use the dedicated post-dialog stop method to avoid a bogus second validation.
                self._fm.stop_focus_after_pin_dialog()
        else:
            self._fm.stop_focus()

    @staticmethod
    def _format_time(seconds: int) -> str:
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"
