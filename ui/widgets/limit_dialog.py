from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit
)

class LimitReachedDialog(QDialog):
    close_app_requested = Signal(str)
    override_requested = Signal(str)
    
    def __init__(self, process_name: str, limit_seconds: int, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.process_name = process_name
        self.limit_seconds = limit_seconds
        
        self.setFixedSize(450, 220)
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
                border: 1px solid #333333;
                border-radius: 12px;
            }
            QLabel {
                color: #FFFFFF;
            }
            QLabel#title {
                font-size: 22px;
                font-weight: bold;
            }
            QLabel#subtitle {
                font-size: 14px;
                color: #A0A0A0;
                margin-top: 5px;
            }
            QPushButton {
                background-color: #2D2D2D;
                color: white;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 10px 15px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            QPushButton#primary {
                background-color: #E53935;
                border: None;
            }
            QPushButton#primary:hover {
                background-color: #F44336;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("Daily limit reached")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        display_name = process_name.replace(".exe", "").title()
        
        subtitle = QLabel(f"{display_name} has reached today's screen time limit.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_close = QPushButton("Close App")
        self.btn_close.setObjectName("primary")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self._on_close_app)
        
        self.btn_pin = QPushButton("Enter PIN")
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.clicked.connect(self._on_enter_pin)
        
        btn_layout.addWidget(self.btn_close)
        btn_layout.addWidget(self.btn_pin)
        
        layout.addLayout(btn_layout)
        
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
        
        self.setFixedSize(400, 280)
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
                border: 1px solid #333333;
                border-radius: 12px;
            }
            QLabel { color: #FFFFFF; }
            QLabel#title { font-size: 20px; font-weight: bold; }
            QLabel#error { color: #E53935; font-size: 13px; font-weight: bold; }
            QLineEdit {
                background-color: #1A1A1A;
                border: 1px solid #444444;
                border-radius: 6px;
                color: white;
                padding: 10px;
                font-size: 18px;
                letter-spacing: 5px;
            }
            QLineEdit:focus { border: 1px solid #3B82F6; }
            QPushButton {
                background-color: #2D2D2D;
                color: white;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #3D3D3D; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 25)
        
        title = QLabel("Override Limit")
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
        for text, mins in [("15m", 15), ("30m", 30), ("1h", 60), ("Unlimited", 0)]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, m=mins: self._try_override(m))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dur_layout.addWidget(btn)
        
        layout.addLayout(dur_layout)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
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
