from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QProgressBar, QTextEdit
)
from core.constants import APP_NAME


class UpdateDialog(QDialog):
    update_now = Signal()
    later = Signal()

    def __init__(self, current_version: str, new_version: str, notes: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} Update Available")
        self.setModal(False)
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(560)

        self._current = current_version
        self._new = new_version
        self._notes = notes

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel(f"Version {self._new} is available.")
        title.setStyleSheet("font-size: 16px; font-weight: 800;")
        layout.addWidget(title)

        ver_label = QLabel(f"Current version: {self._current}\nNew version: {self._new}")
        ver_label.setStyleSheet("font-size: 13px; margin-top:6px; margin-bottom:10px;")
        layout.addWidget(ver_label)

        whats = QLabel("What's New:")
        whats.setStyleSheet("font-weight:700; margin-top:8px;")
        layout.addWidget(whats)

        notes_box = QTextEdit(self)
        notes_box.setReadOnly(True)
        notes_box.setText(self._notes or "N/A")
        notes_box.setMaximumHeight(160)
        layout.addWidget(notes_box)

        self._progress = QProgressBar(self)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._later_btn = QPushButton("Later")
        self._update_btn = QPushButton("Update Now")
        btn_row.addWidget(self._later_btn)
        btn_row.addWidget(self._update_btn)
        layout.addLayout(btn_row)

        self._later_btn.clicked.connect(self._on_later)
        self._update_btn.clicked.connect(self._on_update_now)

    def _on_later(self) -> None:
        self.later.emit()
        self.close()

    def _on_update_now(self) -> None:
        # UI enters download state; caller should connect to download progress signals.
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._update_btn.setEnabled(False)
        self._later_btn.setEnabled(False)
        self.update_now.emit()

    def set_progress(self, percent: int) -> None:
        self._progress.setValue(percent)

    def show_error(self, msg: str) -> None:
        # Show error inline and re-enable controls
        self._progress.setVisible(False)
        self._update_btn.setEnabled(True)
        self._later_btn.setEnabled(True)
        err = QLabel(f"Error: {msg}")
        err.setStyleSheet("color: #ff4444; font-weight: 700; margin-top: 8px;")
        self.layout().addWidget(err)
