"""
process_picker.py — App picker dialog for NYW App Locker.

Two tabs:
  1. Running processes — live list of running user processes (SYSTEM_SAFE filtered)
  2. Browse executable — QFileDialog to pick a .exe directly

Selecting a process populates process_name, display_name, exe_path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import psutil
from PySide6.QtCore import Qt, QSortFilterProxyModel, QTimer
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QListView, QLineEdit, QFileDialog, QFrame, QWidget,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

from protection.app_locker import SYSTEM_SAFE
from core.logger import logger


class ProcessPickerDialog(QDialog):
    """Dialog for selecting an application to add to the App Locker list.

    After exec() returns Accepted, read:
        dialog.selected_process_name   (str, lowercase e.g. 'brave.exe')
        dialog.selected_display_name   (str, e.g. 'Brave Browser')
        dialog.selected_exe_path       (str, full path or '')
    """

    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint,
        )
        self.selected_process_name: str = ""
        self.selected_display_name: str = ""
        self.selected_exe_path: str = ""

        self.setFixedSize(460, 480)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._fade_in = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._setup_ui()
        self._apply_theme()
        self._refresh_process_list()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._fade_in.start()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._bg = QFrame()
        self._bg.setObjectName("picker_bg")

        inner = QVBoxLayout(self._bg)
        inner.setContentsMargins(24, 24, 24, 20)
        inner.setSpacing(0)

        # Header
        hdr_row = QHBoxLayout()
        title = QLabel("Add Application to App Locker")
        title.setObjectName("picker_title")
        hdr_row.addWidget(title, 1)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("picker_close_btn")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(close_btn)
        inner.addLayout(hdr_row)

        inner.addSpacing(16)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setObjectName("picker_tabs")

        # ── Tab 1: Running processes ──────────────────────────────────────
        proc_tab = QWidget()
        proc_layout = QVBoxLayout(proc_tab)
        proc_layout.setContentsMargins(0, 12, 0, 0)
        proc_layout.setSpacing(8)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("🔍  Search processes…")
        self._search_box.setObjectName("picker_search")
        self._search_box.textChanged.connect(self._on_search)
        proc_layout.addWidget(self._search_box)

        self._model = QStandardItemModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterKeyColumn(0)

        self._list_view = QListView()
        self._list_view.setObjectName("picker_list")
        self._list_view.setModel(self._proxy)
        self._list_view.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self._list_view.doubleClicked.connect(self._on_list_double_click)
        self._list_view.clicked.connect(self._on_list_click)
        proc_layout.addWidget(self._list_view, 1)

        refresh_row = QHBoxLayout()
        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setObjectName("picker_refresh_btn")
        refresh_btn.clicked.connect(self._refresh_process_list)
        refresh_row.addWidget(refresh_btn)
        refresh_row.addStretch()
        proc_layout.addLayout(refresh_row)

        self._tabs.addTab(proc_tab, "Running Processes")

        # ── Tab 2: Browse executable ──────────────────────────────────────
        browse_tab = QWidget()
        browse_layout = QVBoxLayout(browse_tab)
        browse_layout.setContentsMargins(0, 20, 0, 0)
        browse_layout.setSpacing(12)

        browse_desc = QLabel("Select the application's .exe file directly.")
        browse_desc.setObjectName("picker_desc")
        browse_desc.setWordWrap(True)
        browse_layout.addWidget(browse_desc)

        self._exe_path_lbl = QLabel("No file selected.")
        self._exe_path_lbl.setObjectName("picker_exe_path")
        self._exe_path_lbl.setWordWrap(True)
        browse_layout.addWidget(self._exe_path_lbl)

        browse_btn = QPushButton("📂  Browse Executable…")
        browse_btn.setObjectName("picker_browse_btn")
        browse_btn.setMinimumHeight(40)
        browse_btn.clicked.connect(self._browse_exe)
        browse_layout.addWidget(browse_btn)
        browse_layout.addStretch()

        self._tabs.addTab(browse_tab, "Browse .exe File")

        inner.addWidget(self._tabs, 1)

        inner.addSpacing(16)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("picker_cancel_btn")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._add_btn = QPushButton("Add to App Locker")
        self._add_btn.setObjectName("picker_add_btn")
        self._add_btn.setMinimumHeight(36)
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(self._add_btn)
        inner.addLayout(btn_row)

        outer.addWidget(self._bg)

    # ─── Theme ───────────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        self.setStyleSheet(f"""
            QFrame#picker_bg {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border')};
                border-radius: 14px;
            }}
            QLabel#picker_title {{
                font-size: 15px;
                font-weight: 800;
                color: {tm.color('text_main')};
            }}
            QLabel#picker_desc, QLabel#picker_exe_path {{
                font-size: 12px;
                color: {tm.color('text_sub')};
            }}
            QPushButton#picker_close_btn {{
                background: transparent;
                color: {tm.color('text_sub')};
                border: none;
                border-radius: 14px;
                font-size: 13px;
            }}
            QPushButton#picker_close_btn:hover {{
                background: {tm.color('danger_bg')};
                color: {tm.color('danger_text')};
            }}
            QLineEdit#picker_search {{
                background-color: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 8px;
                padding: 8px 12px;
                color: {tm.color('text_main')};
                font-size: 13px;
            }}
            QLineEdit#picker_search:focus {{
                border-color: {tm.color('accent')};
            }}
            QListView#picker_list {{
                background-color: {tm.color('input_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                color: {tm.color('text_main')};
                font-size: 13px;
                outline: none;
            }}
            QListView#picker_list::item {{
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QListView#picker_list::item:hover {{
                background-color: {tm.color('card_hover')};
            }}
            QListView#picker_list::item:selected {{
                background-color: {tm.color('accent')};
                color: #ffffff;
            }}
            QPushButton#picker_refresh_btn {{
                background: transparent;
                color: {tm.color('accent')};
                border: none;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#picker_browse_btn {{
                background-color: {tm.color('surface_secondary')};
                color: {tm.color('text_main')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 16px;
            }}
            QPushButton#picker_browse_btn:hover {{
                background-color: {tm.color('card_hover')};
            }}
            QPushButton#picker_cancel_btn {{
                background: transparent;
                color: {tm.color('text_sub')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
            }}
            QPushButton#picker_cancel_btn:hover {{
                background-color: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
            QPushButton#picker_add_btn {{
                background-color: {tm.color('accent')};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#picker_add_btn:hover {{
                background-color: {tm.color('accent_hover')};
            }}
            QPushButton#picker_add_btn:disabled {{
                background-color: {tm.color('border')};
                color: {tm.color('text_muted')};
            }}
            QTabWidget#picker_tabs::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {tm.color('text_sub')};
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {tm.color('accent')};
                border-bottom: 2px solid {tm.color('accent')};
            }}
            QTabBar::tab:hover:!selected {{
                color: {tm.color('text_main')};
            }}
        """)

    # ─── Logic ───────────────────────────────────────────────────────────────

    def _refresh_process_list(self) -> None:
        self._model.clear()
        seen: set[str] = set()
        try:
            for proc in psutil.process_iter(["name", "exe", "pid"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if not name or name in SYSTEM_SAFE or name in seen:
                        continue
                    if not name.endswith(".exe"):
                        continue
                    seen.add(name)
                    exe = proc.info.get("exe") or ""
                    display = Path(exe).stem if exe else name.removesuffix(".exe")
                    display = display.replace("-", " ").replace("_", " ").title()
                    item = QStandardItem(f"{display}  ({name})")
                    item.setData(name, Qt.ItemDataRole.UserRole)            # process_name
                    item.setData(display, Qt.ItemDataRole.UserRole + 1)     # display_name
                    item.setData(exe, Qt.ItemDataRole.UserRole + 2)         # exe_path
                    self._model.appendRow(item)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as exc:
            logger.warning("process_picker refresh error: %s", exc)

    def _on_search(self, text: str) -> None:
        self._proxy.setFilterFixedString(text)

    def _on_list_click(self, index) -> None:
        src_idx = self._proxy.mapToSource(index)
        item = self._model.itemFromIndex(src_idx)
        if item:
            self.selected_process_name = item.data(Qt.ItemDataRole.UserRole)
            self.selected_display_name = item.data(Qt.ItemDataRole.UserRole + 1)
            self.selected_exe_path = item.data(Qt.ItemDataRole.UserRole + 2) or ""
            self._add_btn.setEnabled(True)

    def _on_list_double_click(self, index) -> None:
        self._on_list_click(index)
        if self.selected_process_name:
            self._on_add()

    def _browse_exe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Application", "C:/Program Files", "Executables (*.exe)"
        )
        if path:
            p = Path(path)
            self.selected_process_name = p.name.lower()
            self.selected_display_name = p.stem.replace("-", " ").replace("_", " ").title()
            self.selected_exe_path = path
            self._exe_path_lbl.setText(f"Selected: {p.name}")
            self._add_btn.setEnabled(True)

    def _on_add(self) -> None:
        if self.selected_process_name:
            self.accept()
