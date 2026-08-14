"""
update_dialog.py - UI for displaying update available and downloading.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QProgressBar, QMessageBox
)

from core.updater import UpdateInfo, download_update, verify_update, launch_installer


class DownloadWorker(QThread):
    progress_updated = Signal(int, int)
    download_complete = Signal(object)  # Path
    download_failed = Signal(str)

    def __init__(self, update_info: UpdateInfo, parent=None):
        super().__init__(parent)
        self.update_info = update_info

    def run(self):
        try:
            def progress_callback(downloaded: int, total: int):
                self.progress_updated.emit(downloaded, total)
                
            installer_path = download_update(self.update_info, progress_callback)
            self.download_complete.emit(installer_path)
        except Exception as e:
            self.download_failed.emit(str(e))


class UpdateDialog(QDialog):
    update_started = Signal()
    update_cancelled = Signal()
    update_successful = Signal()

    def __init__(self, current_version: str, update_info: UpdateInfo, parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.update_info = update_info
        self._download_worker = None
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
        new_lbl = QLabel(f"New version:\n{self.update_info.version}")
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
        self.notes_text.setPlainText(self.update_info.release_notes)
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
        self.later_btn.clicked.connect(self.reject)
        
        self.update_btn = FluentButton("Update Now", primary=True)
        self.update_btn.clicked.connect(self._start_update)

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

    def _start_update(self):
        self.update_started.emit()
        self.update_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.notes_text.setEnabled(False)
        
        self.progress_lbl.setVisible(True)
        self.progress_bar.setVisible(True)
        
        self._download_worker = DownloadWorker(self.update_info, self)
        self._download_worker.progress_updated.connect(self._update_progress)
        self._download_worker.download_complete.connect(self._on_download_complete)
        self._download_worker.download_failed.connect(self._on_download_failed)
        self._download_worker.start()

    def _update_progress(self, downloaded: int, total: int):
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            
            dl_mb = downloaded / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self.progress_lbl.setText(f"Downloading update... {dl_mb:.1f} MB / {tot_mb:.1f} MB")
        else:
            self.progress_bar.setRange(0, 0)
            dl_mb = downloaded / (1024 * 1024)
            self.progress_lbl.setText(f"Downloading update... {dl_mb:.1f} MB")

    def _on_download_complete(self, installer_path: Path):
        self.progress_lbl.setText("Verifying update...")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        
        if not verify_update(installer_path):
            self.progress_lbl.setVisible(False)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(
                self, 
                "Update Failed", 
                "Update verification failed. Your current version is still installed."
            )
            if installer_path.exists():
                installer_path.unlink(missing_ok=True)
            self.reject()
            return
            
        self.progress_lbl.setText("Launching installer...")
        if launch_installer(installer_path):
            self.update_successful.emit()
            self.accept()
        else:
            QMessageBox.critical(
                self, 
                "Update Failed", 
                "Failed to launch the installer. Your current version is still installed."
            )
            self.reject()

    def _on_download_failed(self, error: str):
        self.progress_lbl.setVisible(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(
            self, 
            "Update Failed", 
            f"Update couldn't be completed.\n{error}\nYour current version is still installed."
        )
        self.reject()
