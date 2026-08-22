from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QGraphicsOpacityEffect

class PinDialog(QDialog):
    """A dialog for validating a PIN to exit Strict Focus Mode."""
    pin_verified = Signal()
    
    def __init__(self, pin_manager, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self._pin_manager = pin_manager
        
        self.setFixedSize(360, 220)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._anim.setDuration(250)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._setup_ui()
        self._apply_theme()
        
    def showEvent(self, event):
        super().showEvent(event)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        bg_frame = QFrame()
        bg_frame.setObjectName("dialog_bg")
        
        layout = QVBoxLayout(bg_frame)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)
        
        title = QLabel("Strict Mode Active")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Enter your PIN to exit focus mode early.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        
        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("••••")
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pin_input.setMaxLength(8)
        self.pin_input.returnPressed.connect(self._verify_pin)
        layout.addWidget(self.pin_input)
        
        self.error_lbl = QLabel()
        self.error_lbl.setObjectName("error")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_lbl)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_unlock = QPushButton("Unlock")
        self.btn_unlock.setObjectName("btn_unlock")
        self.btn_unlock.clicked.connect(self._verify_pin)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_unlock)
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(bg_frame)
        
    def _apply_theme(self):
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#dialog_bg {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QLabel#title {{ font-size: 16px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#subtitle {{ font-size: 12px; color: {tm.color('text_sub')}; }}
            QLabel#error {{ color: {tm.color('danger_text')}; font-size: 11px; font-weight: 600; }}
            QLineEdit {{
                background-color: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 8px;
                padding: 10px;
                color: {tm.color('text_main')};
                font-size: 18px;
                font-weight: 800;
                letter-spacing: 4px;
            }}
            QLineEdit:focus {{
                border: 1px solid {tm.color('accent')};
            }}
            QPushButton {{
                padding: 10px;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton#btn_cancel {{
                background-color: transparent;
                border: 1px solid {tm.color('border')};
                color: {tm.color('text_main')};
            }}
            QPushButton#btn_cancel:hover {{
                background-color: {tm.color('surface_secondary')};
            }}
            QPushButton#btn_unlock {{
                background-color: {tm.color('accent')};
                border: none;
                color: #ffffff;
            }}
            QPushButton#btn_unlock:hover {{
                background-color: {tm.color('accent_hover')};
            }}
        """)
        
    def _verify_pin(self):
        pin = self.pin_input.text().strip()
        if not pin:
            self.error_lbl.setText("PIN cannot be empty")
            return
            
        if self._pin_manager.verify_pin(pin):
            self.pin_verified.emit()
            self.accept()
        else:
            self.error_lbl.setText("Incorrect PIN")
            self.pin_input.clear()
            self.pin_input.setFocus()
