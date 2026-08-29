"""
update_dialog.py - UI for displaying update available and downloading.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QProgressBar, QMessageBox, QWidget
)

class UpdateDialog(QDialog):
    update_now = Signal()
    later = Signal()

    def __init__(self, current_version: str, new_version: str, notes: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.new_version = new_version
        self.notes = notes
        self._setup_ui()
        self._apply_theme()
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        from ui.theme import ThemeManager, apply_mica
        apply_mica(int(self.winId()), ThemeManager.instance().is_dark)

    def _setup_ui(self):
        from core.constants import APP_NAME
        self.setWindowTitle("Update Available")
        self.setFixedSize(520, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        # Title Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title_lbl = QLabel(f"{APP_NAME} Update Available")
        title_lbl.setObjectName("page_title")
        title_lbl.setWordWrap(True)
        title_font = title_lbl.font()
        title_font.setPixelSize(22)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        
        subtitle_lbl = QLabel("A newer version of NYW is ready to be installed.")
        subtitle_lbl.setObjectName("subtitle")
        sub_font = subtitle_lbl.font()
        sub_font.setPixelSize(14)
        subtitle_lbl.setFont(sub_font)
        
        header_layout.addWidget(title_lbl)
        header_layout.addWidget(subtitle_lbl)
        layout.addLayout(header_layout)

        # Version Comparison Container
        version_container = QWidget()
        version_container.setObjectName("version_container")
        version_layout = QHBoxLayout(version_container)
        version_layout.setContentsMargins(16, 16, 16, 16)
        
        # Current
        cur_layout = QVBoxLayout()
        cur_layout.setSpacing(2)
        cur_title = QLabel("Current version")
        cur_title.setObjectName("version_label")
        cur_val = QLabel(self.current_version)
        cur_val.setObjectName("version_val")
        cur_layout.addWidget(cur_title, alignment=Qt.AlignmentFlag.AlignCenter)
        cur_layout.addWidget(cur_val, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Arrow
        arrow_lbl = QLabel("↓")
        arrow_lbl.setObjectName("arrow")
        arrow_font = arrow_lbl.font()
        arrow_font.setPixelSize(24)
        arrow_lbl.setFont(arrow_font)
        
        # New
        new_layout = QVBoxLayout()
        new_layout.setSpacing(2)
        new_title = QLabel("New version")
        new_title.setObjectName("version_label")
        new_val = QLabel(self.new_version)
        new_val.setObjectName("new_version_val")
        new_layout.addWidget(new_title, alignment=Qt.AlignmentFlag.AlignCenter)
        new_layout.addWidget(new_val, alignment=Qt.AlignmentFlag.AlignCenter)
        
        version_layout.addStretch()
        version_layout.addLayout(cur_layout)
        version_layout.addStretch()
        version_layout.addWidget(arrow_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        version_layout.addStretch()
        version_layout.addLayout(new_layout)
        version_layout.addStretch()
        
        layout.addWidget(version_container)

        # Release Notes
        notes_lbl = QLabel("What's New")
        notes_lbl.setObjectName("notes_title")
        notes_font = notes_lbl.font()
        notes_font.setPixelSize(14)
        notes_font.setBold(True)
        notes_lbl.setFont(notes_font)
        layout.addWidget(notes_lbl)

        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setMarkdown(self.notes)
        layout.addWidget(self.notes_text, stretch=1)

        # Progress bar (hidden initially)
        self.progress_layout = QVBoxLayout()
        self.progress_layout.setSpacing(8)
        self.progress_lbl = QLabel("Downloading update...")
        self.progress_lbl.setVisible(False)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_layout.addWidget(self.progress_lbl)
        self.progress_layout.addWidget(self.progress_bar)
        layout.addLayout(self.progress_layout)

        # Buttons
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(12)
        
        from ui.widgets.fluent import FluentButton
        self.later_btn = FluentButton("Later", primary=False)
        self.later_btn.setMinimumWidth(120)
        self.later_btn.clicked.connect(self._on_later_clicked)
        
        self.update_btn = FluentButton("Update Now", primary=True)
        self.update_btn.setMinimumWidth(120)
        self.update_btn.clicked.connect(self._on_update_clicked)

        self.btn_layout.addWidget(self.later_btn)
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.update_btn)
        layout.addLayout(self.btn_layout)

    def _apply_theme(self):
        try:
            from ui.theme import ThemeManager
            tm = ThemeManager.instance()
            self.setStyleSheet(f"""
                QDialog {{
                    background-color: {tm.color('window_bg')};
                }}
                QLabel {{ 
                    color: {tm.color('text_main')}; 
                }}
                QLabel#subtitle {{
                    color: {tm.color('text_sub')};
                }}
                QLabel#version_label {{
                    color: {tm.color('text_sub')};
                    font-size: 12px;
                }}
                QLabel#version_val {{
                    color: {tm.color('text_main')};
                    font-size: 16px;
                    font-weight: 500;
                }}
                QLabel#new_version_val {{
                    color: {tm.color('accent')};
                    font-size: 18px;
                    font-weight: bold;
                }}
                QLabel#arrow {{
                    color: {tm.color('text_sub')};
                }}
                QWidget#version_container {{
                    background-color: {tm.color('card_bg')};
                    border: 1px solid {tm.color('border')};
                    border-radius: 12px;
                }}
                QTextEdit {{
                    background-color: {tm.color('card_bg')};
                    color: {tm.color('text_main')};
                    border: 1px solid {tm.color('border')};
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 13px;
                }}
                QProgressBar {{
                    background: {tm.color('card_bg')};
                    border: 1px solid {tm.color('border')};
                    border-radius: 4px;
                    text-align: center;
                    color: {tm.color('text_main')};
                }}
                QProgressBar::chunk {{
                    background-color: {tm.color('accent')};
                    border-radius: 4px;
                }}
            """)
        except Exception:
            pass

    def _on_later_clicked(self):
        self.later.emit()
        self.reject()

    def _on_update_clicked(self):
        self.update_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.notes_text.setEnabled(False)
        
        self.progress_lbl.setVisible(True)
        self.progress_bar.setVisible(True)
        
        self.update_now.emit()

    def set_progress(self, percent: int):
        self.progress_bar.setValue(percent)
        self.progress_lbl.setText(f"Downloading update... {percent}%")

    def show_error(self, msg: str):
        self.progress_lbl.setVisible(False)
        self.progress_bar.setVisible(False)
        self.update_btn.setEnabled(True)
        self.later_btn.setEnabled(True)
        self.notes_text.setEnabled(True)
        QMessageBox.critical(self, "Update Failed", f"Update couldn't be completed.\n{msg}")
        self.reject()
