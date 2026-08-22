"""
update_dialog.py - UI for displaying update available and downloading.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QProgressBar, QMessageBox
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

    def _setup_ui(self):
        from core.constants import APP_NAME
        self.setWindowTitle(f"{APP_NAME} Update Available")
        self.setFixedSize(500, 450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title_lbl = QLabel(f"A new version of {APP_NAME} is available.")
        title_lbl.setObjectName("page_title")
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_lbl)

        # Versions
        versions_layout = QHBoxLayout()
        cur_lbl = QLabel(f"Current version:\n{self.current_version}")
        new_lbl = QLabel(f"New version:\n{self.new_version}")
        cur_lbl.setStyleSheet("font-size: 13px; color: gray;")
        new_lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        versions_layout.addWidget(cur_lbl)
        versions_layout.addWidget(new_lbl)
        layout.addLayout(versions_layout)

        # Release Notes
        notes_lbl = QLabel("What's new:")
        notes_lbl.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(notes_lbl)

        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setPlainText(self.notes)
        layout.addWidget(self.notes_text)

        # Progress bar (hidden initially)
        self.progress_layout = QVBoxLayout()
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
        self.btn_layout.addStretch()
        
        from ui.widgets.fluent import FluentButton
        self.later_btn = FluentButton("Later", primary=False)
        self.later_btn.clicked.connect(self._on_later_clicked)
        
        self.update_btn = FluentButton("Update Now", primary=True)
        self.update_btn.clicked.connect(self._on_update_clicked)

        self.btn_layout.addWidget(self.later_btn)
        self.btn_layout.addWidget(self.update_btn)
        layout.addLayout(self.btn_layout)

    def _apply_theme(self):
        try:
            from ui.theme import ThemeManager
            tm = ThemeManager.instance()
            self.setStyleSheet(f"""
                QDialog {{ background: {tm.color('bg_main')}; }}
                QLabel {{ color: {tm.color('text_main')}; }}
                QTextEdit {{
                    background: {tm.color('card_bg')};
                    color: {tm.color('text_main')};
                    border: 1px solid {tm.color('border')};
                    border-radius: 8px;
                    padding: 8px;
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
        QMessageBox.critical(self, "Update Failed", f"Update couldn't be completed.\n{msg}")
        self.reject()
