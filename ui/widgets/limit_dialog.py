from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFrame
)

class LimitReachedDialog(QDialog):
    close_app_requested = Signal(str)
    override_requested = Signal(str)
    
    def __init__(self, process_name: str, limit_seconds: int, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.process_name = process_name
        self.limit_seconds = limit_seconds
        
        self.setFixedSize(480, 320)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Smooth fade-in animation
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._anim.setDuration(250)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._setup_ui()
        
    def showEvent(self, event):
        super().showEvent(event)
        self._anim.start()
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        bg_frame = QFrame()
        bg_frame.setObjectName("dialog_bg")
        
        layout = QVBoxLayout(bg_frame)
        layout.setContentsMargins(32, 32, 32, 24)
        layout.setSpacing(16)
        
        # Top Header (App Icon + Name)
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(12)
        
        from utils.icon_provider import AppIconProvider
        icon_lbl = QLabel()
        icon = AppIconProvider().get_icon(self.process_name)
        if icon and not icon.isNull():
            pixmap = icon.pixmap(64, 64)
            icon_lbl.setPixmap(pixmap)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_lbl)
        
        display_name = self.process_name.replace(".exe", "").title()
        name_lbl = QLabel(display_name)
        name_lbl.setObjectName("app_name")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(name_lbl)
        
        layout.addLayout(header_layout)
        
        # Status Text
        status_lbl = QLabel("Daily limit reached")
        status_lbl.setObjectName("status_title")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_lbl)
        
        # Stats
        stats_layout = QHBoxLayout()
        stats_layout.addStretch()
        
        hrs = self.limit_seconds // 3600
        mins = (self.limit_seconds % 3600) // 60
        usage_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"
        
        usage_lbl = QLabel(f"Today's usage: <span style='color: #F0F6FC; font-weight: bold;'>{usage_str}</span>")
        usage_lbl.setObjectName("stat_text")
        
        rem_lbl = QLabel("Remaining time: <span style='color: #E53935; font-weight: bold;'>0m</span>")
        rem_lbl.setObjectName("stat_text")
        
        stats_layout.addWidget(usage_lbl)
        stats_layout.addSpacing(24)
        stats_layout.addWidget(rem_lbl)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.btn_pin = QPushButton("Override with PIN")
        self.btn_pin.setObjectName("btn_secondary")
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.clicked.connect(self._on_enter_pin)
        
        self.btn_close = QPushButton("Close App")
        self.btn_close.setObjectName("btn_primary")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self._on_close_app)
        
        btn_layout.addWidget(self.btn_pin)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        main_layout.addWidget(bg_frame)
        
        self._apply_theme()
        
    def _apply_theme(self):
        self.setStyleSheet("""
            QFrame#dialog_bg {
                background-color: #000000;
                border: 1px solid #2A2A2A;
                border-radius: 16px;
            }
            QLabel#app_name {
                font-size: 20px;
                font-weight: 800;
                color: #F0F6FC;
            }
            QLabel#status_title {
                font-size: 15px;
                font-weight: 600;
                color: #E53935;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }
            QLabel#stat_text {
                font-size: 13px;
                color: #8B949E;
            }
            QPushButton {
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#btn_secondary {
                background-color: #121212;
                color: #F0F6FC;
                border: 1px solid #2A2A2A;
            }
            QPushButton#btn_secondary:hover {
                background-color: #1E1E1E;
            }
            QPushButton#btn_primary {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
            }
            QPushButton#btn_primary:hover {
                background-color: #2563EB;
            }
        """)
        
    def _on_close_app(self) -> None:
        self.close_app_requested.emit(self.process_name)
        self.accept()
        
    def _on_enter_pin(self) -> None:
        self.override_requested.emit(self.process_name)
        self.accept()


class PinOverrideDialog(QDialog):
    override_granted = Signal(str, int)  # process_name, override_minutes
    
    def __init__(self, process_name: str, pin_manager, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.process_name = process_name
        self._pin_manager = pin_manager
        
        self.setFixedSize(400, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._anim.setDuration(250)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._setup_ui()
        
    def showEvent(self, event):
        super().showEvent(event)
        self._anim.start()
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        bg_frame = QFrame()
        bg_frame.setObjectName("dialog_bg")
        
        layout = QVBoxLayout(bg_frame)
        layout.setContentsMargins(32, 32, 32, 24)
        layout.setSpacing(16)
        
        title = QLabel("Require PIN Override")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("Enter PIN")
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.pin_input)
        
        self.error_lbl = QLabel()
        self.error_lbl.setObjectName("error")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_lbl)
        
        dur_layout = QHBoxLayout()
        dur_layout.setSpacing(8)
        for text, mins in [("15m", 15), ("30m", 30), ("1h", 60), ("Unlimited", 0)]:
            btn = QPushButton(text)
            btn.setObjectName("btn_dur")
            btn.clicked.connect(lambda _, m=mins: self._try_override(m))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dur_layout.addWidget(btn)
        
        layout.addLayout(dur_layout)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(bg_frame)
        
        self._apply_theme()
        
    def _apply_theme(self):
        self.setStyleSheet("""
            QFrame#dialog_bg {
                background-color: #000000;
                border: 1px solid #2A2A2A;
                border-radius: 16px;
            }
            QLabel#title {
                font-size: 20px;
                font-weight: 800;
                color: #F0F6FC;
            }
            QLabel#error {
                color: #E53935;
                font-size: 13px;
                font-weight: 600;
            }
            QLineEdit {
                background-color: #121212;
                border: 1px solid #2A2A2A;
                border-radius: 8px;
                color: #F0F6FC;
                padding: 12px;
                font-size: 18px;
                letter-spacing: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
            }
            QPushButton#btn_dur {
                background-color: #121212;
                color: #F0F6FC;
                border: 1px solid #2A2A2A;
                border-radius: 8px;
                padding: 8px 0;
                font-weight: 600;
            }
            QPushButton#btn_dur:hover {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
            }
            QPushButton#btn_cancel {
                background-color: transparent;
                color: #8B949E;
                border: none;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 16px;
            }
            QPushButton#btn_cancel:hover {
                color: #FFFFFF;
            }
        """)
        
    def _try_override(self, minutes: int) -> None:
        pin = self.pin_input.text().strip()
        if not pin:
            self.error_lbl.setText("PIN cannot be empty")
            return
            
        if self._pin_manager.verify_pin(pin):
            self.override_granted.emit(self.process_name, minutes)
            self.accept()
        else:
            self.error_lbl.setText("Incorrect PIN")
            self.pin_input.clear()
