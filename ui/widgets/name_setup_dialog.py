"""
name_setup_dialog.py — First-run personalized onboarding dialog for Notch.
Prompts the user for their preferred display name with Continue and Skip options.
Stored strictly locally in SQLite settings. Never transmitted externally.
"""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QGraphicsOpacityEffect
)

from settings.manager import SettingsManager
from ui.theme import ThemeManager


class NameSetupDialog(QDialog):
    """
    First-run modal asking 'What should we call you?'
    Saves display_name locally and flags name_prompt_completed = True.
    """
    name_configured = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint,
        )
        self._sm = SettingsManager()
        self.setFixedSize(460, 380)
        self.setWindowTitle("Personalize Notch")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Smooth fade-in animation
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._anim.setDuration(220)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._setup_ui()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def showEvent(self, event):
        super().showEvent(event)
        self._anim.start()
        self._name_input.setFocus()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._bg_frame = QFrame()
        self._bg_frame.setObjectName("dialog_card")
        layout = QVBoxLayout(self._bg_frame)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo / Brand Badge
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = Path(__file__).parent.parent.parent / "assets" / "icons" / "app_logo.png"
        pix = QPixmap(str(logo_path))
        if not pix.isNull():
            icon_lbl.setPixmap(pix.scaled(52, 52, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(icon_lbl)

        # Heading
        self._title_lbl = QLabel("What should we call you?")
        self._title_lbl.setObjectName("dialog_title")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_lbl)

        # Supporting text
        self._subtitle_lbl = QLabel("Your name stays on this device and is only used to personalize Notch.")
        self._subtitle_lbl.setObjectName("dialog_subtitle")
        self._subtitle_lbl.setWordWrap(True)
        self._subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._subtitle_lbl)

        layout.addSpacing(6)

        # Name Input
        self._name_input = QLineEdit()
        self._name_input.setObjectName("name_input")
        self._name_input.setPlaceholderText("Enter your name")
        self._name_input.setMaxLength(50)
        self._name_input.textChanged.connect(self._on_text_changed)
        self._name_input.returnPressed.connect(self._on_continue)
        layout.addWidget(self._name_input)

        layout.addSpacing(10)

        # Buttons Row: Skip & Continue
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.setObjectName("skip_btn")
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.clicked.connect(self._on_skip)
        btn_layout.addWidget(self._skip_btn)

        self._continue_btn = QPushButton("Continue")
        self._continue_btn.setObjectName("continue_btn")
        self._continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._continue_btn.setEnabled(False)
        self._continue_btn.clicked.connect(self._on_continue)
        btn_layout.addWidget(self._continue_btn)

        layout.addLayout(btn_layout)

        main_layout.addWidget(self._bg_frame)

    def _on_text_changed(self, text: str) -> None:
        self._continue_btn.setEnabled(len(text.strip()) > 0)

    def _on_continue(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            return
        self._sm.display_name = name
        self._sm.name_prompt_completed = True
        self.name_configured.emit(name)
        self.accept()

    def _on_skip(self) -> None:
        self._sm.display_name = ""
        self._sm.name_prompt_completed = True
        self.name_configured.emit("")
        self.reject()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._on_skip()
        else:
            super().keyPressEvent(event)

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        bg_color = "#11151C" if is_dark else "#FFFFFF"
        border_color = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        input_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.03)"
        input_border = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.15)"
        accent = tm.color("accent")
        accent_hover = tm.color("accent_hover")
        btn_secondary_bg = tm.color("surface_secondary")
        btn_secondary_hover = tm.color("surface_hover")

        self.setStyleSheet(f"""
            QFrame#dialog_card {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 20px;
            }}
            QLabel#dialog_title {{
                color: {text_main};
                font-size: 20px;
                font-weight: 800;
                letter-spacing: -0.3px;
            }}
            QLabel#dialog_subtitle {{
                color: {text_sub};
                font-size: 13px;
                line-height: 1.4;
            }}
            QLineEdit#name_input {{
                background-color: {input_bg};
                color: {text_main};
                border: 1.5px solid {input_border};
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: 500;
            }}
            QLineEdit#name_input:focus {{
                border-color: {accent};
            }}
            QPushButton#skip_btn {{
                background-color: {btn_secondary_bg};
                color: {text_sub};
                border: 1px solid {border_color};
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#skip_btn:hover {{
                background-color: {btn_secondary_hover};
                color: {text_main};
            }}
            QPushButton#continue_btn {{
                background-color: {accent};
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 10px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#continue_btn:hover {{
                background-color: {accent_hover};
            }}
            QPushButton#continue_btn:disabled {{
                background-color: {btn_secondary_bg};
                color: {tm.color('text_muted')};
                border-color: transparent;
            }}
        """)
